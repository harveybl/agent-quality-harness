# How the harness works

## Frontier path

Claude Code and Codex retain their native agent loops. A repository-local synchronous `Stop` hook calls `evaluator/completion_gate.py`. The gate runs deterministic argument-array commands, checks that protected Git paths remain clean, and either allows the stop or returns exact failure evidence. `max_blocks` limits how many continuations the gate may request.

The installer changes only these target paths:

- `.agent-quality/completion_gate.py`
- `.agent-quality/gate.json`
- `.agent-quality/install-manifest.json`
- `.claude/settings.json` when Claude is selected
- `.codex/hooks.json` when Codex is selected

It does not suppress global skills, memories, MCP servers, plugins, or account configuration. In an A/B test, keep those constant so the repository-local treatment is the only changed variable.

## Local path

The controller lifecycle is:

1. **Anchored plan:** native object containing `path`, exact `line`, `anchor`, `change`, and `acceptance_ids`.
2. **Carried context:** the controller gives implementation a ±30-line window around each validated anchor.
3. **Bounded tools:** `navigation_budget` caps reads/searches; `mutable_paths` and `protected_paths` enforce edit scope.
4. **Syntax-safe edit:** Python writes are parsed before acceptance.
5. **Tests after first write:** `public_check_argv` is unavailable until a candidate changed.
6. **Evidence-directed continuation:** only a changed failing candidate can receive the current diff and exact test evidence, at most once.
7. **Score ledger:** `runs/ledger.json` records `terminal_reason`, `model_calls`, `tokens`, `tool_calls`, `first_write_at`, `changed_files`, `checks`, `continuations`, `automatic_run_retries`, timings, and environment hashes.

## Runtime topology

The host publishes llama.cpp only on `127.0.0.1`. Model weights are mounted read-only. The model server and non-root harness share one Compose network marked `internal: true`, so the harness can reach `http://model:8080/v1` but has no external egress. Only the disposable candidate mount is writable; the sandbox root filesystem and application code are read-only.

