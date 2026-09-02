# Matched ablation protocol

Use one meaningful vertical slice with deterministic acceptance checks. Hash the starting task, candidate, and evaluator before every arm.

| Arm | Native loop | Planning/budgets | Completion gate | Reviewer/repair |
| --- | --- | --- | --- | --- |
| A | Plain Claude or Codex | Off | Off | Off |
| B | Same Claude or Codex | Instruction treatment | On | Off |
| C | Same Claude or Codex | Instruction treatment | On | One bounded evidence-directed continuation |
| D | Plain local Qwen worker | Off | External evaluator only | Off |
| E | Same Qwen artifact | Anchors, budgets, safe edits | External evaluator | One bounded continuation |

Keep model, effort, task prompt, starting commit, tool permissions, time limit, evaluator, context, temperature, and account-level configuration equal within each comparison. Run each condition once before deciding whether a repeated-seed study is warranted. Never automatically retry a failed model run.

Record only:

- task pass/fail and evaluator score;
- elapsed time;
- model cycles/calls and tokens;
- human intervention;
- major failure reason;
- whether the treatment materially changed the result.

A continuation after deterministic gate failure is part of the enhanced condition. Restarting the whole model run is an automatic retry and is prohibited in this protocol.

