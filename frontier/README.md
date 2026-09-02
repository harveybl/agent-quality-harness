# Native Claude Code and Codex adapters

These adapters keep the normal authenticated CLI and native model loop. They add the same repository-local deterministic `Stop` gate to either tool.

```bash
aqh install --target /path/to/repository
aqh doctor --target /path/to/repository
aqh verify --target /path/to/repository
```

Then edit `<repository>/.agent-quality/gate.json`, start `claude` or `codex` normally in that repository, and review the hook once. Codex exposes review through `/hooks`; Claude Code displays its normal repository trust/hook review flow.

Rollback is exact when managed files have not been edited:

```bash
aqh uninstall --target /path/to/repository
```

The scripts under `frontier/scripts/` remain compatibility shims for older
automation. New installations should use `aqh` so they receive the same tested
transaction, diagnostics, and synthetic verification flow.

The installer never edits global account settings, memories, MCP servers, skills, authentication, or billing configuration.
