# Completion gate

`completion_gate.py` is a synchronous `Stop` hook. It runs configured argument-array commands from the repository root and returns native hook JSON.

- Passing checks allow the agent to stop.
- Failing checks return exact tail evidence and request a bounded continuation.
- `max_blocks` caps continuation; it is not a full-run retry.
- `protected_paths` must remain clean relative to Git.

Install it through `aqh install`; do not edit global Claude Code or Codex configuration.
