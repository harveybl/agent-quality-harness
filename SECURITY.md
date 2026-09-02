# Security

This project executes repository-defined test commands and lets a model edit an explicitly mounted candidate workspace. Review configuration before use.

- Never mount a home directory, credential directory, Docker socket, SSH key, or production checkout into the local worker.
- Keep model files read-only and candidate files disposable or version controlled.
- The native local path enforces tool and path bounds; it is not container isolation. Run it only against a disposable or version-controlled candidate with no secrets.
- AQH probes and uses a user-supplied endpoint but never starts, stops, downloads, or retries the model server.
- Prefer loopback for a model on the same machine. A LAN endpoint sends prompts and task context to that host, so treat it as a separate trust boundary.
- Review and trust repository hooks once in Claude Code or Codex. A changed hook hash must be reviewed again.
- Installed hook commands contain machine-local absolute paths. Do not commit
  AQH-generated hook/config changes for coworkers; install them separately in
  each checkout and uninstall before sharing the code diff.
- The experimental CLI-only AVO command permits only bounded
  `--max-review-calls` and `--max-repair-turns`, refuses external paid route
  variables, and may consume both personal subscriptions. One hard-task
  observation measured uplift when a stronger evaluator was supplied; it is
  not a broad benchmark. Its Codex worker uses `danger-full-access` inside the
  explicitly supplied disposable worktree; never point it at credentials,
  production data, or a non-disposable checkout. The Fable supervisor remains
  tool-less. Desktop is not qualified for this experiment.
- Report vulnerabilities privately through GitHub's security advisory flow.
