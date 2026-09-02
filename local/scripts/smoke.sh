#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
local_dir=$(cd "$script_dir/.." && pwd)
smoke_dir=$(mktemp -d)
trap 'rm -rf "$smoke_dir"' EXIT

docker compose -f "$local_dir/docker-compose.yml" up -d --build model >/dev/null 2>&1
for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:${MODEL_PORT:-8080}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${MODEL_PORT:-8080}/health" >/dev/null
printf 'PASS model-server\n'

curl -fsS "http://127.0.0.1:${MODEL_PORT:-8080}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen-local","temperature":0,"max_tokens":256,"response_format":{"type":"json_object"},"messages":[{"role":"user","content":"Return JSON only: {\"changes\":[{\"path\":\"starter/calculator.py\",\"line\":2,\"anchor\":\"return 0\",\"change\":\"add\",\"acceptance_ids\":[\"AC-1\"]}]}"}]}' \
  >"$smoke_dir/structured.json"
python3 - "$smoke_dir/structured.json" <<'PY'
import json, sys
outer = json.load(open(sys.argv[1], encoding="utf-8"))
inner = json.loads(outer["choices"][0]["message"]["content"])
assert inner["changes"][0]["path"] == "starter/calculator.py"
PY
printf 'PASS structured-plan\n'

docker compose -f "$local_dir/docker-compose.yml" run --rm --no-deps --entrypoint python harness -c \
  'import os,socket; assert os.geteuid()!=0; assert not os.path.exists("/var/run/docker.sock"); s=socket.socket(); s.settimeout(2); ok=False
try: s.connect(("1.1.1.1",443))
except OSError: ok=True
assert ok' >/dev/null 2>&1
printf 'PASS sandbox-isolation\n'

docker compose -f "$local_dir/docker-compose.yml" run --rm --no-deps --entrypoint python harness \
  -m unittest discover -s /app/evaluator/tests -v >/dev/null 2>&1
printf 'PASS evaluator-tests\n'

