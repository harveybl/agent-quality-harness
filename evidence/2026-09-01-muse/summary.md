# Muse results

Muse showed useful planning/editing progress but did not produce a trustworthy accepted implementation on the corrected contract.

| Run | Result | Time | Model cycles | Main issue |
| --- | --- | ---: | ---: | --- |
| v16, old evaluator | Corrected fail, 4/6 | 186.9 s | 38 | Old evaluator omitted two regressions and produced a false pass. |
| v17, corrected evaluator | Fail, 1/5 controller | 306.5 s | 48 | Candidate caused endpoint errors; one continuation did not improve it. |

Both were single runs with zero automatic retries and zero human intervention during the counted run. Muse remains evidence-only here because a public, redistributable weight artifact was not verified for this package.

