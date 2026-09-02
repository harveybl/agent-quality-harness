# Security

This project executes repository-defined test commands and lets a model edit an explicitly mounted candidate workspace. Review configuration before use.

- Never mount a home directory, credential directory, Docker socket, SSH key, or production checkout into the local worker.
- Keep model files read-only and candidate files disposable or version controlled.
- The native local path enforces tool and path bounds; it is not container isolation. Run it only against a disposable or version-controlled candidate with no secrets.
- AQH probes and uses a user-supplied endpoint but never starts, stops, downloads, or retries the model server.
- Prefer loopback for a model on the same machine. A LAN endpoint sends prompts and task context to that host, so treat it as a separate trust boundary.
- Review and trust repository hooks once in Claude Code or Codex. A changed hook hash must be reviewed again.
- Report vulnerabilities privately through GitHub's security advisory flow.
