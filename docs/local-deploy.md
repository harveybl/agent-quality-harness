# Deploy the local Qwen harness

Supported reproducible path: Ubuntu 24.04, NVIDIA GPU/driver, NVIDIA Container Toolkit, Docker Compose, the pinned llama.cpp server image, and the exact Qwen3.8-27B Q8 artifact in `models.lock.example`. The 29.05 GB model plus a 65,536-token context generally requires a high-memory GPU; the tested machine used an RTX 5090. Muse is not a deployable path in this release.

## Step 1: Confirm the supported host

### Purpose

Stop before downloads if the host cannot expose an NVIDIA GPU to containers.

### Run

```bash
grep 'VERSION_ID="24.04"' /etc/os-release
nvidia-smi
docker version
docker compose version
```

### Expect

Ubuntu 24.04, one visible NVIDIA GPU, and working Docker/Compose clients and daemon.

### If it fails

Install the NVIDIA driver, Docker Engine, Compose plugin, and NVIDIA Container Toolkit from their vendor instructions; then reboot if the driver changed.

### Verify

```bash
docker run --rm --gpus all ubuntu:24.04 nvidia-smi
```

### Undo

No mutation in this step.

## Step 2: Clone the exact release

### Purpose

Use the audited repository state instead of moving `main`.

### Run

```bash
git clone https://github.com/harveybl/agent-quality-harness.git
cd agent-quality-harness
git checkout v0.1.0
```

### Expect

`git describe --tags --exact-match` prints `v0.1.0`.

### If it fails

Run `git fetch --tags` and verify that GitHub is reachable.

### Verify

```bash
git status --short
git describe --tags --exact-match
```

### Undo

Leave the directory; delete the clone only if you no longer need it.

## Step 3: Download the tested Qwen artifact

### Purpose

Acquire the exact Q8 bytes used by the published result without bundling model weights in Git.

### Run

```bash
mkdir -p local/models
curl -L --fail --continue-at - \
  --output local/models/Qwen3.8-27B-Q8_0.gguf \
  'https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/resolve/f1bfb127c64f7072bdd2cad55f258b9c8b2910fe/Qwen3.8-27B-Q8_0.gguf'
```

### Expect

A 29,047,086,048-byte file. Review the upstream Apache-2.0 model card and applicable terms before use.

### If it fails

Check free disk space and retry the same resumable command. Do not substitute a differently named Q8 file and assume equivalence.

### Verify

```bash
stat --format='%s' local/models/Qwen3.8-27B-Q8_0.gguf
```

### Undo

```bash
rm -f local/models/Qwen3.8-27B-Q8_0.gguf
```

## Step 4: Verify the model lock

### Purpose

Bind the run to the tested filename, size, and SHA-256 before loading 29 GB into GPU memory.

### Run

```bash
python3 local/scripts/verify_model.py local/models/Qwen3.8-27B-Q8_0.gguf
```

### Expect

One `PASS` line ending in `a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348`.

### If it fails

Do not run the model. Resume the download or remove the mismatched file and fetch it again.

### Verify

```bash
sha256sum local/models/Qwen3.8-27B-Q8_0.gguf
```

### Undo

No mutation in this step.

## Step 5: Run the host preflight

### Purpose

Check every named runtime dependency in one place.

### Run

```bash
local/scripts/check_env.sh
```

### Expect

Five `PASS` lines: Ubuntu, driver, Docker, Compose, and NVIDIA container runtime.

### If it fails

Fix only the named failing prerequisite; do not add wrappers or change model configuration.

### Verify

```bash
docker info --format '{{json .Runtimes}}'
```

### Undo

No mutation in this step.

## Step 6: Build the sandbox image

### Purpose

Materialize the pinned Python/Strands controller without putting tools on the host Python installation.

### Run

```bash
docker compose -f local/docker-compose.yml build harness
```

### Expect

An image named `local-harness`; dependency resolution must include Strands 1.54.0 and OpenAI Python 2.54.0.

### If it fails

Read the first resolver or Dockerfile error. Do not loosen dependency versions; `make check` must still pass after any correction.

### Verify

```bash
docker image inspect local-harness --format '{{.Id}}'
```

### Undo

```bash
docker image rm local-harness
```

## Step 7: Create a disposable candidate

### Purpose

Give the model a writable copy while keeping the shipped failing fixture unchanged.

### Run

```bash
mkdir -p runs
cp -R examples/hello-fix runs/hello-fix-01
```

### Expect

`runs/hello-fix-01` contains `task.md`, `contract.json`, `starter`, and `public_checks`.

### If it fails

Check that you are at the repository root and the tagged example exists.

### Verify

```bash
python3 -m unittest discover -s runs/hello-fix-01/public_checks -v
```

The verification must fail before the model runs; that is the known starter state.

### Undo

```bash
rm -rf runs/hello-fix-01
```

## Step 8: Smoke-test server, structure, isolation, and gate

### Purpose

Prove the GPU server, native JSON plan response, internal-only sandbox network, and evaluator before a counted run.

### Run

```bash
local/scripts/smoke.sh
```

### Expect

Exactly four lines: `PASS model-server`, `PASS structured-plan`, `PASS sandbox-isolation`, and `PASS evaluator-tests`.

### If it fails

Inspect `docker compose -f local/docker-compose.yml logs model`; fix the reported layer only. The smoke request is a preflight, not a counted model result.

### Verify

```bash
curl -fsS http://127.0.0.1:8080/health
docker compose -f local/docker-compose.yml config --quiet
```

### Undo

```bash
local/scripts/down.sh
```

## Step 9: Run one local coding condition

### Purpose

Execute one plan, one implementation, deterministic checks, and at most one evidence-directed continuation.

### Run

```bash
WORKSPACE_DIR=../runs/hello-fix-01 \
docker compose -f local/docker-compose.yml run --rm harness
```

### Expect

Exit `0` with `terminal_reason` equal to `passed` or `passed-after-continuation`; `automatic_run_retries` remains `0`.

### If it fails

Read `runs/hello-fix-01/runs/ledger.json`. Keep the failed result; do not automatically rerun it. Correct only a genuine pre-model harness bug.

### Verify

```bash
python3 -m unittest discover -s runs/hello-fix-01/public_checks -v
jq '{terminal_reason,model_calls,tool_calls,continuations,automatic_run_retries,changed_files}' \
  runs/hello-fix-01/runs/ledger.json
```

### Undo

Restore the disposable candidate by removing it and repeating Step 7; do not overwrite a result you intend to count.

## Step 10: Run a matched ablation

### Purpose

Measure the harness instead of merely demonstrating that one enhanced run can pass.

### Run

```bash
cp -R examples/hello-fix runs/hello-fix-baseline
cp -R examples/hello-fix runs/hello-fix-enhanced
```

Run each condition once with the same model artifact, task, starting files, context, temperature, permissions, evaluator, and time limit. For the baseline, use a plain OpenAI-compatible coding loop without anchored-plan, navigation-budget, syntax-gate, or continuation treatment; preserve its ledger separately.

### Expect

Two immutable ledgers that differ only in the treatment and disclose pass/fail, score, time, model cycles, tokens, intervention, and failure reason.

### If it fails

Discard the pair if starting hashes or limits differ. Do not “fix” one arm after seeing its result.

### Verify

```bash
sha256sum runs/hello-fix-baseline/task.md runs/hello-fix-enhanced/task.md
sha256sum runs/hello-fix-baseline/contract.json runs/hello-fix-enhanced/contract.json
```

### Undo

Archive wanted ledgers, then remove only the two disposable candidate directories.

## Step 11: Shut down and cleanly uninstall

### Purpose

Release GPU memory and remove containers without touching model weights or evidence.

### Run

```bash
local/scripts/down.sh
```

### Expect

No Compose containers remain and `nvidia-smi` shows no llama.cpp process.

### If it fails

Run `docker compose -f local/docker-compose.yml ps -a` and stop only containers in this Compose project.

### Verify

```bash
docker compose -f local/docker-compose.yml ps -a
nvidia-smi
```

### Undo

Restart only the model service with `docker compose -f local/docker-compose.yml up -d model`.

