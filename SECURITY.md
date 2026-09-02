# Security

This project executes repository-defined test commands and lets a model edit an explicitly mounted candidate workspace. Review configuration before use.

- Never mount a home directory, credential directory, Docker socket, SSH key, or production checkout into the local worker.
- Keep model files read-only and candidate files disposable or version controlled.
- Review and trust repository hooks once in Claude Code or Codex. A changed hook hash must be reviewed again.
- Report vulnerabilities privately through GitHub's security advisory flow.

