# How the harness works

## Frontier path

Claude Code and Codex retain their native agent loops. A repository-local synchronous `Stop` hook calls `evaluator/completion_gate.py`. The gate runs deterministic argument-array commands, checks that protected Git paths remain clean, and either allows the stop or returns exact failure evidence. `max_blocks` limits how many continuations the gate may request.

The installer changes only these target paths:

- `.agent-quality/completion_gate.py`
- `.agent-quality/quality_context.py`
- `.agent-quality/quality_contract.txt`
- `.agent-quality/gate.json`
- `.agent-quality/install-manifest.json`
- `.claude/settings.json` when Claude is selected
- `.codex/hooks.json` when Codex is selected

It does not suppress global skills, memories, MCP servers, plugins, or account configuration. In an A/B test, keep those constant so the repository-local treatment is the only changed variable.

## Local path

`aqh local doctor` reads health and model identity from an existing endpoint.
It never starts, stops, downloads, or retries a model server. `aqh local run`
then connects the enhanced worker to that endpoint and executes one controller
run against a contract-bearing disposable workspace.

The controller lifecycle is:

1. **Anchored plan:** native object containing `path`, exact `line`, `anchor`, `change`, and `acceptance_ids`.
2. **Carried context:** the controller gives implementation a ±30-line window around each validated anchor.
3. **Bounded tools:** each phase gets a fresh `navigation_budget` for reads and searches; `mutable_paths` and `protected_paths` enforce edit scope.
4. **Syntax-safe edit:** Python writes are parsed before acceptance.
5. **Tests after first write:** `public_check_argv` is unavailable until a candidate changed.
6. **Evidence-directed continuation:** only a changed failing candidate can receive the current diff and exact test evidence, at most once.
7. **Hard phase stop:** planning, implementation, and repair stop after 32 model calls or five minutes between model calls; a model/context failure is ledgered rather than retried.
8. **Score ledger:** `runs/ledger.json` records `terminal_reason`, `model_calls`, `tokens`, `tool_calls`, `first_write_at`, `changed_files`, `checks`, `continuations`, `automatic_run_retries`, timings, and environment hashes.

## Runtime topology

The simple native path relies on the controller's path allowlist, protected
paths, navigation budget, syntax checks, and bounded continuation. Those are
native process bounds, not container isolation. Keep the endpoint on loopback
when the worker runs on the same machine; a remote endpoint protects model
weights but does not isolate the worker's workspace.

The optional Compose topology is a stricter reproducibility backend. It mounts
model weights read-only, puts the non-root harness and llama.cpp on an internal
network, gives the harness a read-only root filesystem, and makes only the
disposable candidate writable. GPU access belongs to the model-server
container only.
