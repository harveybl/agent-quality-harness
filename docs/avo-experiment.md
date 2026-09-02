# Experimental AVO review and repair

This CLI-only experiment asks a tool-less Claude supervisor to review a native
Claude Code or Codex worker after deterministic checks fail. It is deliberately
separate from the everyday completion gate: the completion gate provides exact
failure evidence inside one native client, while AVO adds a second model call
that can redirect a bounded repair turn.

There is no measured uplift claim yet. The point of this command is to produce
matched evidence. A run may consume both personal subscriptions: Codex can be
the worker while Claude is the supervisor. There are no external paid routes;
the command refuses API-key/base-URL and hosted-provider route variables.
Desktop is not qualified for AVO because exact noninteractive session resume
and usage receipts are CLI capabilities.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "agent-quality-harness[experiment]"
```

This uses the normal logged-in `claude` and `codex` commands. It does not create
an auth home, copy credentials, disable the worker's native tools, or replace
account settings. The supervisor alone has tools and MCP disabled; it receives
only the task, Git diff, and deterministic failure evidence.

## Verify without model calls

```bash
python -m unittest discover -s tests -p "test_avo_*.py" -v
```

These scripted tests prove exact-session continuation, repair limits,
protected paths, separate usage totals, and zero automatic full-run retries.

## Run one explicit live condition

Start from a disposable clean Git worktree. Put the task in `task.md` and use
the same gate schema shown in the [frontier runbook](frontier-deploy.md). Do not
also install the completion hook unless the intentionally named experiment arm
is “hooks plus AVO.”

```bash
aqh experiment avo /absolute/path/to/candidate \
  --task-file task.md \
  --gate quality-gate.json \
  --worker codex \
  --worker-model gpt-5.6-sol \
  --worker-effort high \
  --supervisor-model fable \
  --supervisor-effort high \
  --max-review-calls 3 \
  --max-repair-turns 3
```

`--max-review-calls` limits supervisor calls; `--max-repair-turns` limits
same-session worker continuations. Values are independently bounded from 0 to
7. A worker or supervisor process failure ends the condition and is not retried.

The ledger under `.agent-quality/runs/` records terminal outcome, evaluator
evidence, actual worker client/model/session receipts, supervisor identity,
elapsed time, calls, tokens, repair counts, and `automatic_run_retries: 0`.

For a fair result, compare this against a clean native run with identical task,
starting commit, model, effort, permissions, evaluator, and time limit. One run
per arm is an observation, not a general performance conclusion.
