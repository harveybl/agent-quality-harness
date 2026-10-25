# Agent Quality Harness (AQH) — repository index

Plain-markdown orientation for humans and coding agents. **This repository is PUBLIC**: this file contains only information already present in the repo. Based on `main` at `3c642c1` (2026-09-02), package version 0.2.0. `README.md` is authoritative.

## Purpose
A small, testable quality layer for native Claude Code, native Codex and local OpenAI-compatible models: deterministic completion checks, bounded evidence-directed continuation, and a compact run ledger, without replacing the model's own agent loop (README). Apache-2.0.

## Structure
| Path | What |
|---|---|
| `src/agent_quality_harness/` | The Python package (CLI entry point `aqh = agent_quality_harness.cli:main`) |
| `evaluator/` | Completion gate (`completion_gate.py`, `gate.example.json`) and tests |
| `frontier/` | Claude Code / Codex hook track: scripts and tests |
| `local/` | Local-endpoint track: harness, Dockerfile.sandbox, docker-compose.yml, config/model lock examples, tests |
| `examples/` | `hello-fix`, `helios-review-semantics` |
| `evidence/` | Recorded evaluation runs and inventory matrix |
| `tests/` | Package tests (CLI, doctor, hooks, installer, local runner, AVO, docs, packaging, verifier) |
| `scripts/lint_steps.py` | Step-document linter |
| `docs/` | `frontier-deploy.md`, `local-deploy.md`, `avo-experiment.md`, `how-it-works.md`, `evidence.md`, `ablation.md`, `research-report.md`, `superpowers/` |
| `Makefile`, `pyproject.toml`, `CHANGELOG.md`, `SECURITY.md`, `LICENSE` | Project metadata |

## Build and test
Python >= 3.11. From the repo `Makefile` (`make check`):
```bash
PYTHONPATH=src python3 scripts/lint_steps.py
PYTHONPATH=src python3 -m unittest discover -s evaluator/tests -v
PYTHONPATH=src python3 -m unittest discover -s frontier/tests -v
PYTHONPATH=src python3 -m unittest discover -s local/tests -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
Usage (README): `aqh install`, `aqh doctor`, `aqh verify`; local track `aqh local doctor --endpoint … --model …`, `aqh local run …`.

## CI/CD
GitHub Actions `.github/workflows/ci.yml`, triggered on push and pull_request: job `portable-base` (ubuntu/macos/windows, Python 3.12: build + install wheel, then the same lint and unittest steps as above), `optional-integrations` (installs `.[local,experiment]`, runs local and AVO adapter tests without model calls), `optional-linux-containers` (validates the Compose file, builds the sandbox image without starting a model).

## Recent notable changes (git log, 2026-09-02)
Portable Windows release checks; install from a pinned release artifact; qualified matrix guidance published; AVO uplift claims qualified; bounded local model execution phases and navigation reset by phase.
