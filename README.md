# Agent Quality Harness

A small, testable quality layer for native Claude Code, native Codex, and local
OpenAI-compatible models. It adds deterministic completion checks, bounded
evidence-directed continuation, and a compact run ledger without replacing the
model's native agent loop.

## Choose a track

- **Claude Code or Codex:** install the dependency-free base package and follow
  [`docs/frontier-deploy.md`](docs/frontier-deploy.md). It changes only
  repository-local hook files and supports exact rollback.
- **Existing local endpoint:** install the optional local extra and follow
  [`docs/local-deploy.md`](docs/local-deploy.md). AQH does not require Docker,
  manage a GPU, or own the model-server lifecycle.
- **AVO comparison:** only for an explicit CLI-only experiment, install the
  experiment extra and follow [`docs/avo-experiment.md`](docs/avo-experiment.md).
  It is not part of the everyday hook install.

## Quick start

Frontier clients:

```bash
python3 -m pip install agent-quality-harness
cd /path/to/your/repository
aqh install
aqh doctor
aqh verify
```

Local model against an endpoint you already run:

```bash
python3 -m pip install "agent-quality-harness[local]"
aqh local doctor --endpoint http://127.0.0.1:8080/v1 --model qwen-local
aqh local run /path/to/disposable-candidate \
  --endpoint http://127.0.0.1:8080/v1 --model qwen-local
```

## Boundaries

- Model weights are never bundled. You supply and checksum a GGUF file.
- Model names are not hard-coded: use the exact ID advertised by `/v1/models`
  for Qwen, Muse, or another compatible local model.
- The published model evidence is one development slice, not a broad benchmark or a guarantee.
- A failed gate may request one bounded continuation. The harness never automatically retries a full model run.
- No API key, Bedrock account, AWS account, or direct model billing is required for the frontier track; it uses your existing Claude Code and Codex login.
- The AVO path is experimental, may consume both personal subscriptions, uses
  no external paid routes, and has no measured uplift claim yet. Desktop is not
  qualified for AVO; use the native CLIs for auditable session receipts.

Start with [`examples/hello-fix`](examples/hello-fix), then use [`docs/ablation.md`](docs/ablation.md) to compare clean and enhanced conditions.

## Status

Release candidate under test. Nothing is published until the cross-platform,
native-client, local-model, quality-comparison, and Fable 5.1 gates pass.
