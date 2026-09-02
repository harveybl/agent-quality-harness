# Agent Quality Harness

A small, testable quality layer for native Claude Code, native Codex, and a local Qwen coding worker. It adds deterministic completion checks, bounded evidence-directed continuation, and a compact run ledger without replacing the model's native agent loop.

## Choose a track

- **Local Qwen on Ubuntu/NVIDIA:** follow [`docs/local-deploy.md`](docs/local-deploy.md). The reproducible path is Ubuntu 24.04, Docker Compose, NVIDIA Container Toolkit, llama.cpp, and Qwen3.8-27B Q8.
- **Claude Code or Codex:** follow [`docs/frontier-deploy.md`](docs/frontier-deploy.md). The installer changes only repository-local hook files and supports exact rollback.

## Boundaries

- Model weights are never bundled. You supply and checksum a GGUF file.
- Muse is evidence-only until its public weights and redistribution terms can be verified.
- The published model evidence is one development slice, not a broad benchmark or a guarantee.
- A failed gate may request one bounded continuation. The harness never automatically retries a full model run.
- No API key, Bedrock account, AWS account, or direct model billing is required for the frontier track; it uses your existing Claude Code and Codex login.

Start with [`examples/hello-fix`](examples/hello-fix), then use [`docs/ablation.md`](docs/ablation.md) to compare clean and enhanced conditions.

## Status

Release target: `v0.1.0`. Verified 2026-09-02.

