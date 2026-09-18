"""Lossless conversion of whitelisted model-trace fields to JSON values."""
import math
import numbers


def json_safe(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, numbers.Real):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite audit value')
        return number
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise TypeError('Audit keys must be strings')
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if hasattr(value, 'model_dump'):
        return json_safe(value.model_dump(mode='json'))
    raise TypeError('Unsupported audit value type: ' + type(value).__name__)
