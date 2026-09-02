# Research report boundary

The long-form two-week field report remains preserved on the companion Site under `/research`, with the earlier frontier baseline report under `/frontier-baseline`.

This repository is the implementation source of truth. Its concise claims are limited to sanitized artifacts in [`evidence`](../evidence), the exact deployment paths in [`local-deploy.md`](local-deploy.md) and [`frontier-deploy.md`](frontier-deploy.md), and the matched protocol in [`ablation.md`](ablation.md).

The current hard-task result is in
[`2026-09-02-inventory-matrix`](../evidence/2026-09-02-inventory-matrix/summary.md).
Its conclusion is deliberately narrow: native hooks enforced the process but
did not improve held-out quality, while opt-in AVO repaired both frontier arms
to 5/5 when its supervisor received stronger evaluator evidence. Structured
local control remains useful, but Qwen and Muse did not complete the same hard
application task.
