"""Validated TypeSafe System One HTTP adapter (https://docs.typesafe.ai/api).

Construction never calls the service. Injected ``transport(payload) -> dict``
is always marked mock and never receives an API key. Real HTTP sends credentials
only to the fixed official HTTPS endpoint and refuses redirects.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from numbers import Real
import os
import re
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from pgc.decision import DecisionBackend, DecisionRequest, DecisionResponse
from pgc.evaluation import validate_distribution
from pgc.ir import PrimitiveType


class JevAPIError(RuntimeError):
    """Safe request failure with accounting available to experiment runners."""

    def __init__(self, message, *, status_code=None, latency_ms=0.0,
                 tokens_used=None, metadata=None, raw_response=None):
        super().__init__(message)
        self.status_code = status_code
        self.latency_ms = latency_ms
        self.tokens_used = tokens_used
        self.metadata = metadata or {}
        self.raw_response = raw_response


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # urllib raises HTTPError without forwarding credentials.


class JevRealBackend(DecisionBackend):
    API_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
    JEV_VERSION = "jev-1.13.0"
    RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504, 529})

    def __init__(self, api_key: Optional[str] = None, *, model=JEV_VERSION,
                 transport=None, timeout=30.0, max_retries=2,
                 backoff_seconds=0.5, max_backoff_seconds=8.0, sleep=time.sleep):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("A nonempty model identifier is required")
        if type(max_retries) is not int or not 0 <= max_retries <= 5:
            raise ValueError("max_retries must be an integer from 0 to 5")
        for name, value in (("timeout", timeout), ("backoff_seconds", backoff_seconds),
                            ("max_backoff_seconds", max_backoff_seconds)):
            if (isinstance(value, bool) or not isinstance(value, Real)
                    or not math.isfinite(value) or value < 0 or (name == "timeout" and value == 0)):
                raise ValueError(name + " must be finite and nonnegative (timeout must be positive)")
        if transport is not None and not callable(transport):
            raise ValueError("transport must be callable")
        # Injected mocks never consult environment credentials.
        self._api_key = api_key if api_key is not None else (
            os.environ.get("TYPESAFE_API_KEY") if transport is None else None)
        if self._api_key is not None and not isinstance(self._api_key, str):
            raise ValueError("API key must be a string")
        self.model, self._transport, self.timeout = model, transport, timeout
        self.max_retries = max_retries
        self.backoff_seconds, self.max_backoff_seconds = backoff_seconds, max_backoff_seconds
        self._sleep = sleep
        self.execution_mode = "mock" if transport is not None else "real"
        self.available = transport is not None or bool(self._api_key)
        self.call_count = self.request_count = self.retry_count = self.success_count = 0
        self.total_input_tokens = self.total_output_tokens = 0
        self._opener = urllib.request.build_opener(_NoRedirects())

    def name(self) -> str:
        return "jev-typesafe"

    def version(self) -> str:
        return self.model

    def _safe_error(self, error):
        message = str(error)
        if self._api_key:
            message = message.replace(self._api_key, "[REDACTED]")
        message = re.sub(r"(?i)\bBearer\s+[^\s\"',;}]+", "Bearer [REDACTED]", message)
        message = re.sub(r"(?im)^.*(?:authorization|api[-_ ]?key)\s*[:=].*$",
                         "[credential field redacted]", message)
        return message[:2000]

    def _safe_response(self, value):
        """Retain provider failure evidence without auth/header material."""
        if isinstance(value, dict):
            sensitive = {"authorization", "headers", "request_headers", "response_headers",
                         "api_key", "apikey", "access_token", "password", "secret"}
            return {key: "[REDACTED]" if str(key).lower() in sensitive else self._safe_response(item)
                    for key, item in value.items()}
        if isinstance(value, list):
            return [self._safe_response(item) for item in value]
        if isinstance(value, str):
            if self._api_key:
                value = value.replace(self._api_key, "[REDACTED]")
            return re.sub(r"(?i)\bBearer\s+[^\s\"',;}]+", "Bearer [REDACTED]", value)
        return deepcopy(value)

    @staticmethod
    def _probability(value, field):
        if (isinstance(value, bool) or not isinstance(value, Real)
                or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError(field + " must be a finite probability in [0, 1]")
        return float(value)

    @staticmethod
    def _validate_questions(state, questions):
        if not isinstance(state, (str, dict, list)):
            raise ValueError("state must be a string, object, or array")
        if not isinstance(questions, dict) or not questions:
            raise ValueError("questions must be a nonempty mapping")
        for question_id, question in questions.items():
            if not isinstance(question_id, str) or not question_id:
                raise ValueError("Question IDs must be nonempty strings")
            if not isinstance(question, dict) or set(question) - {"type", "instructions", "criteria"}:
                raise ValueError("Questions allow only type, instructions, and criteria")
            if not isinstance(question.get("instructions"), (str, dict, list)) or not question["instructions"]:
                raise ValueError("Question instructions must contain the actual question")
            primitive, criteria = question.get("type"), question.get("criteria")
            if primitive == "choice":
                if (not isinstance(criteria, dict) or not 1 <= len(criteria) <= 255
                        or any(not isinstance(k, str) or not k for k in criteria)):
                    raise ValueError("Choice criteria must map 1 to 255 explicit option names to descriptions")
                if any(value is not None and not isinstance(value, (str, dict, list)) for value in criteria.values()):
                    raise ValueError("Choice descriptions must be text, structured instructions, or null")
            elif primitive == "score":
                if not isinstance(criteria, list) or not 2 <= len(criteria) <= 10:
                    raise ValueError("Score criteria must contain 2 to 10 ordered level descriptions")
                if any(not isinstance(value, (str, dict, list)) for value in criteria):
                    raise ValueError("Score levels must contain text or structured instructions")
            elif primitive == "noul":
                if "criteria" in question and (not isinstance(criteria, dict) or set(criteria) != {"true", "false"}):
                    raise ValueError("Noul criteria must declare true and false descriptions")
                if criteria is not None and any(not isinstance(value, str) for value in criteria.values()):
                    raise ValueError("Noul descriptions must be strings")
            else:
                raise ValueError("Unsupported question type")

    def _validate_response(self, response, questions):
        if not isinstance(response, dict):
            raise ValueError("API response must be an object")
        if "error" in response:
            raise ValueError("API returned an error: " + self._safe_error(response["error"]))
        if response.get("model") != self.model:
            raise ValueError("Returned model does not match requested model")
        answers = response.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise ValueError("Answer IDs must exactly match question IDs")
        for question_id, question in questions.items():
            answer = answers[question_id]
            if not isinstance(answer, dict) or answer.get("type") != question["type"]:
                raise ValueError("Answer type does not match question type: " + question_id)
            primitive = question["type"]
            if primitive == "noul":
                self._probability(answer.get("noul"), "noul")
                continue
            labels = list(question["criteria"]) if primitive == "choice" else [str(i) for i in range(len(question["criteria"]))]
            probabilities = validate_distribution(answer.get("probabilities"), labels)
            self._probability(answer.get("confidence"), "confidence")
            if primitive == "choice":
                choice = answer.get("choice")
                if not isinstance(choice, str) or choice not in probabilities:
                    raise ValueError("choice must name an option in probabilities")
                if probabilities[choice] != max(probabilities.values()):
                    raise ValueError("choice must be a highest-probability option")
            else:
                score = answer.get("score")
                if (isinstance(score, bool) or not isinstance(score, Real)
                        or not math.isfinite(score) or not 0 <= score <= len(labels) - 1):
                    raise ValueError("score must be finite and within the declared levels")
                legend = answer.get("legend")
                if not isinstance(legend, dict) or set(legend) != set(labels):
                    raise ValueError("Score legend indices must match the declared levels")
                # Service expectation may be rounded; retain it separately from
                # the distribution and its independently calculated expectation.

    @staticmethod
    def _usage(response):
        usage = response.get("usage") if isinstance(response, dict) else None
        if not isinstance(usage, dict):
            raise ValueError("API response must include token usage")
        result = {}
        for source, target in (("input_tokens", "input"), ("output_tokens", "output")):
            value = usage.get(source)
            if type(value) is not int or value < 0:
                raise ValueError("Token usage must contain nonnegative integers")
            result[target] = value
        return result

    def _http_transport(self, payload):
        if self.API_ENDPOINT != "https://api.typesafe.ai/v1/systemone":
            raise ValueError("Credentials may only be sent to the official HTTPS endpoint")
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        request = urllib.request.Request(
            self.API_ENDPOINT, data=body, method="POST",
            headers={"Authorization": "Bearer " + self._api_key, "Content-Type": "application/json"})
        with self._opener.open(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def send_payload(self, state, questions):
        """Send arbitrary IDs; return response, latency_ms, tokens_used, metadata.

        Also returns execution_mode. Metadata records requested/returned model,
        canonical request SHA256, and attempts. Failures raise JevAPIError with
        accounting and optional status_code; probabilities are never invented.
        Retries apply only to explicit transient HTTP statuses.
        """
        start = time.perf_counter()
        tokens = None
        response = None
        metadata = {"requested_model": self.model, "returned_model": None,
                    "attempts": 0, "attempt_log": [], "execution_mode": self.execution_mode}
        self.request_count += 1
        try:
            self._validate_questions(state, questions)
            payload = {"state": deepcopy(state), "model": self.model, "questions": deepcopy(questions)}
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                 allow_nan=False).encode("utf-8")
            metadata["request_sha256"] = hashlib.sha256(encoded).hexdigest()
            if not self.available:
                raise ValueError("TYPESAFE_API_KEY is required for actual Jev requests")
            for attempt in range(self.max_retries + 1):
                self.call_count += 1
                metadata["attempts"] += 1
                attempt_start = time.perf_counter()
                attempt_record = {"started_at": datetime.now(timezone.utc).isoformat(),
                                  "status": None, "error_kind": None, "known_usage": None}
                metadata["attempt_log"].append(attempt_record)
                response = None  # A later network failure must not inherit an earlier HTTP body.
                try:
                    response = (self._transport(deepcopy(payload)) if self._transport is not None
                                else self._http_transport(payload))
                    attempt_record["status"] = "response_received"
                    break
                except urllib.error.HTTPError as error:
                    status = error.code
                    attempt_record.update({"status": status, "error_kind": "HTTPError"})
                    retry_after = error.headers.get("Retry-After") if error.headers else None
                    try:
                        detail = error.read(8192).decode("utf-8", errors="replace")
                    finally:
                        error.close()
                    try:
                        response = json.loads(detail)
                    except (ValueError, TypeError):
                        response = {"http_error_text": self._safe_error(detail)}
                    if status not in self.RETRYABLE_STATUSES or attempt == self.max_retries:
                        raise JevAPIError("HTTP " + str(status) + ": " + self._safe_error(detail),
                                          status_code=status) from None
                    delay = self.backoff_seconds * 2 ** attempt
                    try:
                        retry_seconds = float(retry_after)
                        if math.isfinite(retry_seconds) and retry_seconds >= 0:
                            delay = max(delay, retry_seconds)
                    except (TypeError, ValueError):
                        pass
                    self.retry_count += 1
                    attempt_record["latency_ms"] = (time.perf_counter() - attempt_start) * 1000
                    attempt_record["retry_delay_seconds"] = min(delay, self.max_backoff_seconds)
                    self._sleep(attempt_record["retry_delay_seconds"])
                except Exception as error:
                    attempt_record.update({"status": "transport_error", "error_kind": type(error).__name__})
                    raise
                finally:
                    attempt_record.setdefault("latency_ms", (time.perf_counter() - attempt_start) * 1000)
            metadata["returned_model"] = self._safe_response(response.get("model")) if isinstance(response, dict) else None
            if isinstance(response, dict) and "error" in response and "usage" not in response:
                raise ValueError("API returned an error: " + self._safe_error(response["error"]))
            tokens = self._usage(response)
            metadata["attempt_log"][-1]["known_usage"] = dict(tokens)
            # Sole counter update: usage belongs to the whole HTTP request,
            # including requests whose answers subsequently fail validation.
            self.total_input_tokens += tokens["input"]
            self.total_output_tokens += tokens["output"]
            self._validate_response(response, questions)
            self.success_count += 1
            return {"response": response, "latency_ms": (time.perf_counter() - start) * 1000,
                    "tokens_used": tokens, "metadata": metadata, "execution_mode": self.execution_mode}
        except Exception as error:
            raise JevAPIError(self._safe_error(error), status_code=getattr(error, "status_code", None),
                              latency_ms=(time.perf_counter() - start) * 1000,
                              tokens_used=tokens, metadata=metadata,
                              raw_response=self._safe_response(response)) from None

    @staticmethod
    def _labels(request):
        labels = request.labels if request.labels is not None else request.options
        if (not isinstance(labels, (list, tuple)) or not labels
                or any(not isinstance(label, str) or not label for label in labels)
                or len(set(labels)) != len(labels)):
            raise ValueError("Decision requires explicit unique string labels or options")
        return list(labels)

    def _binary_labels(self, request):
        labels = self._labels(request)
        if len(labels) != 2:
            raise ValueError("Noul requires exactly two declared labels")
        positive, negative = request.payload.get("positive_label"), request.payload.get("negative_label")
        if positive is not None or negative is not None:
            if positive == negative or set((positive, negative)) != set(labels):
                raise ValueError("Noul positive_label and negative_label must match declared labels")
            return positive, negative
        for positive, negative in (("same", "different"), ("true", "false"), ("yes", "no")):
            if set(labels) == {positive, negative}:
                return positive, negative
        raise ValueError("Custom Noul labels require explicit positive_label and negative_label")

    def _format_questions(self, request):
        labels = self._labels(request)
        context = {key: value for key, value in request.payload.items()
                   if key not in {"instructions", "criteria", "positive_label", "negative_label", "evidence"}}
        instructions = request.payload.get("instructions", request.question)
        if "instructions" not in request.payload and context:
            instructions = {"question": request.question, "context": context}
        question = {"type": request.primitive.value, "instructions": instructions}
        if request.primitive == PrimitiveType.CHOICE:
            descriptions = {
                "SUPPORTS": "The provided evidence supports the claim.",
                "REFUTES": "The provided evidence contradicts the claim.",
                "NOT_ENOUGH_INFO": "The evidence is insufficient to support or refute the claim.",
                "same": "Both mentions identify the same real-world entity.",
                "different": "The mentions identify different real-world entities.",
            }
            if request.options and set(request.options) != set(labels):
                if len(request.options) != len(labels):
                    raise ValueError("Choice options descriptions must align with declared labels")
                criteria = dict(zip(labels, request.options))
            else:
                criteria = {label: descriptions.get(label, label) for label in labels}
            question["criteria"] = request.payload.get("criteria", criteria)
            if not isinstance(question["criteria"], dict) or set(question["criteria"]) != set(labels):
                raise ValueError("Choice criteria keys must exactly match declared labels")
        elif request.primitive == PrimitiveType.NOUL:
            positive, negative = self._binary_labels(request)
            question["criteria"] = request.payload.get("criteria", {"true": positive, "false": negative})
        elif request.primitive == PrimitiveType.SCORE:
            question["criteria"] = request.payload.get("criteria", request.rubric)
            if not isinstance(question["criteria"], list) or len(question["criteria"]) != len(labels):
                raise ValueError("Score criteria and declared labels must align by index")
        else:
            raise ValueError("Unsupported decision primitive")
        return {"q1": question}

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        return self._batch_with_shared_state([request])[0]

    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        if not requests:
            return []
        if all(request.state == requests[0].state for request in requests):
            return self._batch_with_shared_state(requests)
        return [self.decide(request) for request in requests]

    @staticmethod
    def _allocate_usage(tokens, index, count):
        if tokens is None:
            return None
        return {key: value // count + int(index < value % count) for key, value in tokens.items()}

    def _batch_with_shared_state(self, requests):
        try:
            questions = {"q" + str(i + 1): self._format_questions(request)["q1"]
                         for i, request in enumerate(requests)}
            result = self.send_payload(requests[0].state, questions)
        except Exception as error:
            metadata = getattr(error, "metadata", {"requested_model": self.model, "attempts": 0})
            return [DecisionResponse(
                request.request_id, {}, error=self._safe_error(error),
                raw_output=getattr(error, "raw_response", None),
                latency_ms=getattr(error, "latency_ms", 0.0) / len(requests),
                tokens_used=self._allocate_usage(getattr(error, "tokens_used", None), i, len(requests)),
                execution_mode="mock" if self.execution_mode == "mock" else "unavailable",
                metadata={**metadata, "status_code": getattr(error, "status_code", None),
                          "batch_size": len(requests), "usage_allocation": "equal_integer_remainder"})
                for i, request in enumerate(requests)]
        responses = []
        for i, request in enumerate(requests):
            question_id = "q" + str(i + 1)
            answer = result["response"]["answers"][question_id]
            metadata = {**result["metadata"], "question_id": question_id, "batch_size": len(requests),
                        "batch_latency_ms": result["latency_ms"], "usage_allocation": "equal_integer_remainder"}
            labels = self._labels(request)
            if request.primitive == PrimitiveType.NOUL:
                positive, negative = self._binary_labels(request)
                distribution = {positive: float(answer["noul"]), negative: 1.0 - answer["noul"]}
                metadata.update({"positive_label": positive, "negative_label": negative})
                confidence = None  # Noul has no separate service confidence.
            elif request.primitive == PrimitiveType.SCORE:
                distribution = {label: answer["probabilities"][str(index)] for index, label in enumerate(labels)}
                metadata.update({"score_expectation": answer["score"],
                                 "score_expectation_from_probabilities": sum(
                                     index * distribution[label] for index, label in enumerate(labels))})
                confidence = answer["confidence"]
            else:
                distribution = {label: answer["probabilities"][label] for label in labels}
                confidence = answer["confidence"]
            responses.append(DecisionResponse(
                request.request_id, distribution, confidence=confidence, raw_output=deepcopy(answer),
                latency_ms=result["latency_ms"] / len(requests),
                tokens_used=self._allocate_usage(result["tokens_used"], i, len(requests)),
                execution_mode=result["execution_mode"], metadata=metadata))
        return responses

    def estimate_cost(self, requests: List[DecisionRequest]) -> Dict[str, Any]:
        return {"tokens": None, "estimated_cost_usd": None,
                "note": "Use returned token usage and a separately verified current price."}

    def get_stats(self) -> Dict[str, Any]:
        return {"calls_made": self.call_count, "requests_made": self.request_count,
                "retries": self.retry_count, "successful_requests": self.success_count,
                "total_input_tokens": self.total_input_tokens, "total_output_tokens": self.total_output_tokens,
                "execution_mode": self.execution_mode, "requested_model": self.model}
