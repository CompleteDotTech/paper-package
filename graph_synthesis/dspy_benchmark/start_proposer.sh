#!/usr/bin/env bash
set -euo pipefail
TOOLS="${RUNNER_TEMP:?}/dspy-proposer"
mkdir -p "$TOOLS"
curl -fL --retry 2 --max-time 600 'https://github.com/ggml-org/llama.cpp/releases/download/b10964/llama-b10964-bin-ubuntu-x64.tar.gz' -o "$TOOLS/llama.tar.gz"
printf '%s  %s\n' '9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443' "$TOOLS/llama.tar.gz" | sha256sum -c -
tar -xzf "$TOOLS/llama.tar.gz" -C "$TOOLS" --no-same-owner
curl -fL --retry 2 --max-time 900 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf' -o "$TOOLS/proposer.gguf"
printf '%s  %s\n' '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e' "$TOOLS/proposer.gguf" | sha256sum -c -
SERVER="$(find "$TOOLS" -type f -name llama-server | head -1)"
test -n "$SERVER"
export LD_LIBRARY_PATH="$(dirname "$SERVER"):${LD_LIBRARY_PATH:-}"
"$SERVER" -m "$TOOLS/proposer.gguf" --host 127.0.0.1 --port 8080 --parallel 1 --threads 4 --ctx-size 8192 --n-gpu-layers 0 --jinja > "$TOOLS/server.log" 2>&1 &
echo "$!" > "$TOOLS/server.pid"
for i in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8080/health > /dev/null; then exit 0; fi
  sleep 2
done
tail -40 "$TOOLS/server.log"
exit 1
