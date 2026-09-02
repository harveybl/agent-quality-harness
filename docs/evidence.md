# What the evidence says

## Current hard-task matrix

On one frozen inventory-fulfillment task, native hooks were delivered but did
not improve held-out quality. Claude and Codex hook arms scored 3/5, compared
with clean scores of 3/5 and 4/5 respectively. Their visible gates had already
passed, so the hooks had no evidence about the hidden defects.

The opt-in Fable AVO treatment improved both frontier workers from an initial
3/5 to 5/5 by giving the supervisor stronger evaluator failures and resuming
the same worker session. It required substantially more time and model usage;
the Claude arm also required one harness parser recovery. See the
[full qualified matrix](../evidence/2026-09-02-inventory-matrix/summary.md).

The local harness completed a real Qwen smoke edit in 10.6 seconds. It did not
make the same local model hard-task ready: Qwen hit the endpoint's 32K context
limit and scored 1/5, while Muse reached its generation ceiling before returning
a valid plan. Both failed conditions were bounded and ledgered without a full-run retry.

## Prior local slice

Qwen3.8-27B Q8 previously passed one bounded Helios review-semantics slice: 5/5
controller units and 6/6 corrected public tests, 402.7 seconds, 47 model cycles,
zero human intervention, one gate-controlled continuation, and zero automatic
full-run retries. Muse failed the corrected replay. This shows task-specific
capability, not broad local-model parity.

## What is proven

- Strong, discriminating evaluator evidence plus bounded AVO repair can improve a failed frontier result on this task.
- The local anchored-plan, bounded-navigation, syntax-safe-edit, post-write-test, and evidence-directed-continuation treatment can produce a genuine Qwen success on a small slice.
- The completion gate and installers behave deterministically in synthetic tests.
- A weak evaluator can create a false pass; corrected evaluator-only rescoring is necessary when omissions are found.

## What is not proven

- No broad average uplift or statistical significance.
- No claim that native hooks improve quality when their configured checks do not expose the defect.
- No claim that the local Qwen or Muse configuration is ready for application-sized autonomous development.
- No claim that Muse is a safe autonomous finisher.
- No claim that frontier hooks improve every task or model.

Use [`ablation.md`](ablation.md) to extend this one-task matrix rather than
treating either the supervised frontier pass or the small local pass as universal.
