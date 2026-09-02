# Native Claude Code and Codex adapters

These adapters keep the normal authenticated CLI and native model loop. They add the same repository-local deterministic `Stop` gate to either tool.

```bash
python3 frontier/scripts/install_hooks.py --target /path/to/repository --tool both
```

Then edit `<repository>/.agent-quality/gate.json`, start `claude` or `codex` normally in that repository, and review the hook once. Codex exposes review through `/hooks`; Claude Code displays its normal repository trust/hook review flow.

Rollback is exact when managed files have not been edited:

```bash
python3 frontier/scripts/uninstall_hooks.py --target /path/to/repository
```

The installer never edits global account settings, memories, MCP servers, skills, authentication, or billing configuration.

