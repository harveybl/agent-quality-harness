# What the evidence says

## Decisive local result

Qwen3.8-27B Q8 passed one bounded Helios review-semantics slice: 5/5 controller units and 6/6 corrected public tests, 402.7 seconds, 47 model cycles, zero human intervention, one gate-controlled continuation, zero automatic full-run retries.

Muse v16 was initially accepted by an incomplete four-test evaluator, then correctly rescored 4/6 and reclassified as a fail. Muse v17 ran once against the corrected evaluator and failed at 1/5 controller units.

## What is proven

- The anchored-plan, bounded-navigation, syntax-safe-edit, post-write-test, and evidence-directed-continuation treatment can produce a genuine Qwen success on this slice.
- The completion gate and installers behave deterministically in synthetic tests.
- A weak evaluator can create a false pass; corrected evaluator-only rescoring is necessary when omissions are found.

## What is not proven

- No broad average uplift or statistical significance.
- No matched clean Qwen baseline in this public evidence package.
- No claim that Muse is a safe autonomous finisher.
- No claim that frontier hooks improve every task or model.

Use [`ablation.md`](ablation.md) to generate the missing matched evidence rather than treating a one-slice pass as a universal result.

