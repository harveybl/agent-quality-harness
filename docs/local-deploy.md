# Use the local-model harness

The everyday path connects AQH to a user-supplied endpoint that is already
running. AQH does not start or stop llama.cpp, manage GPU drivers, download
weights, or require a container. The endpoint must provide `GET /health` and
the OpenAI-compatible `GET /v1/models` plus chat-completions APIs.

## Step 1: Install the optional local extra

### Purpose

Install the CLI, Strands worker, OpenAI-compatible client, and schema library
without changing the model server.

### Run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install \
  "agent-quality-harness[local] @ https://github.com/harveybl/agent-quality-harness/releases/download/v0.2.0/agent_quality_harness-0.2.0-py3-none-any.whl"
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

### Expect

`aqh --help` lists `local`; the base frontier commands remain usable without
the local extra.

### If it fails

Use Python 3.11 or newer and read the first package-resolution error. Confirm
that the pinned GitHub release asset is reachable; this project is not on PyPI.
The local dependencies are intentionally pinned; do not loosen them silently.

### Verify

```bash
aqh local --help
```

### Undo

```bash
python -m pip uninstall agent-quality-harness
```

## Step 2: Supply an existing model endpoint

### Purpose

Run the model with the tool you already use. For current llama.cpp, this is a
minimal native example on macOS or Linux:

### Run

```bash
llama-server \
  --model /path/to/model.gguf \
  --alias qwen-local \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 65536 \
  --jinja
```

Choose GPU/offload settings appropriate for that machine. AQH deliberately
does not own them.

### Expect

The server stays in the foreground and advertises `qwen-local` from
`http://127.0.0.1:8080/v1/models`.

### If it fails

Resolve the server or model-loading error in llama.cpp. Do not add AQH wrappers
around the server lifecycle.

### Verify

```bash
curl --fail http://127.0.0.1:8080/health
curl --fail http://127.0.0.1:8080/v1/models
```

### Undo

Press `Ctrl-C` in the llama.cpp terminal. AQH has nothing to clean up.

## Step 3: Diagnose once, then run once

### Purpose

Confirm endpoint/model identity before giving the bounded worker a disposable
candidate. No model call occurs during `doctor`.

### Run

```bash
aqh local doctor \
  --endpoint http://127.0.0.1:8080/v1 \
  --model qwen-local

cp -R examples/hello-fix runs/hello-fix-qwen
aqh local run runs/hello-fix-qwen \
  --endpoint http://127.0.0.1:8080/v1 \
  --model qwen-local
```

Use a different `--model` only when `/v1/models` advertises that exact ID.

### Expect

Doctor reports reachability, health, exact model match, dependency state, and
containment. The run writes `runs/hello-fix-qwen/runs/ledger.json`; its
`automatic_run_retries` is `0` and `continuations` is at most the contract
limit. Planning, implementation, and repair each receive a fresh bounded
navigation allowance and stop after 32 model calls or five minutes between
model calls. A phase limit or model-context error is written as a failed ledger
instead of restarting the task.

### If it fails

Keep the ledger. Do not automatically rerun the full model condition. Correct
only the reported endpoint mismatch, missing local extra, contract issue, or a
genuine pre-model harness defect.

### Verify

```bash
python -m unittest discover -s runs/hello-fix-qwen/public_checks -v
python -m json.tool runs/hello-fix-qwen/runs/ledger.json
```

### Undo

Remove only the disposable candidate after preserving any result you intend to
compare. AQH never changes the model server.

## Step 4: Optional NVIDIA/Docker reproducibility

### Purpose

Use the repository's pinned Compose topology when reproducible NVIDIA container
isolation matters more than the two-command native path. This is optional and
Linux-specific; it is not required on macOS or Windows.

### Run

```bash
MODEL_DIR=/path/to/models MODEL_FILE=model.gguf \
docker compose -f local/docker-compose.yml up -d model

WORKSPACE_DIR=../runs/hello-fix-qwen \
docker compose -f local/docker-compose.yml run --rm harness
```

### Expect

The model binds to host loopback, weights are read-only, the harness is
non-root with a read-only root filesystem, and only the candidate mount is
writable.

### If it fails

Run `docker compose -f local/docker-compose.yml config --quiet`, then inspect
only the failing service log. NVIDIA container access is a requirement of this
optional path, not of AQH itself.

### Verify

```bash
docker compose -f local/docker-compose.yml config --quiet
docker compose -f local/docker-compose.yml ps
```

### Undo

```bash
local/scripts/down.sh
```

The native path provides native process bounds through the AQH tool policy. It
is not equivalent to the optional container's filesystem and network isolation.
