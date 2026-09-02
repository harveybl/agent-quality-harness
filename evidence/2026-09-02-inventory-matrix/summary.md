# Inventory fulfillment matrix

This is one hard task, not a broad benchmark. Every frontier candidate began
from the same frozen starter and used the same visible and held-out evaluators.
No condition automatically restarted a failed full model run.

| Condition | Visible | Held out | Final | Model time | Calls | Intervention |
| --- | --- | --- | --- | ---: | ---: | --- |
| Claude Sonnet clean | Pass | 3/5 | Fail | 615.8 s | 1 worker | No |
| Claude Sonnet + native hooks | Pass | 3/5 | Fail | 500.4 s | 1 worker | No |
| Claude Sonnet + Fable AVO | Pass | 3/5 to 5/5 | Pass | 855.0 s | 3 worker + 2 review | Parser recovery |
| Codex Luna clean | Pass | 4/5 | Fail | 473.2 s | 1 worker | No |
| Codex Luna + native hooks | Pass | 3/5 | Fail | 733 s to first answer | 1 worker | Setup stop |
| Codex Luna + Fable AVO | Pass | 3/5 to 5/5 | Pass | 1004.9 s | 2 worker + 1 review | No |

The native hook was genuinely delivered in both hook conditions. It improved
Claude time and output-token use on this task, but it did not improve held-out
quality. That is expected once the evidence is examined: the hook's visible
gate already passed and therefore had no signal about the hidden defects.

AVO materially improved final quality in both supervised arms because Fable
received the stronger evaluator failures and returned narrow repair directives
to the same worker session. The tradeoff was substantial extra time and model
usage. Use AVO for consequential tasks with discriminating tests, not as an
always-on loop.

The local path is not ready for this application-sized task. Muse failed before
producing a plan. Qwen's final harness completed a small real edit in 10.6
seconds, but on the hard task it exceeded a 32K endpoint context and scored 1/5
held-out. The released controller now bounds and ledgers that failure instead
of hanging, but containment is not capability.

## Decision

- Keep the reversible native completion gate for deterministic tests and
  protected paths.
- Keep structured local planning, exact anchors, per-phase navigation budgets,
  one evidence-directed continuation, and hard phase limits.
- Keep Fable AVO opt-in for high-value work with a stronger evaluator.
- Do not require Docker, GPU access, authentication wrappers, or AVO for normal
  frontier development.
- Do not claim local frontier replacement from smoke-task success.
