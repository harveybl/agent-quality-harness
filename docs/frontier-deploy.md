# Add the completion gate to Claude Code and Codex

This path preserves the normal authenticated personal-plan CLI. It does not create auth wrappers, copy credentials, use API keys, change billing, or edit global memories, skills, MCP servers, plugins, or account settings. Account-level behavior is therefore not ignored; it remains identical across baseline and enhanced arms. The experimental treatment is repository-local.

## Step 1: Pin this installer and name the target

### Purpose

Keep the harness source and the application under test separate.

### Run

```bash
git clone https://github.com/harveybl/agent-quality-harness.git
cd agent-quality-harness
git checkout v0.1.0
export TARGET_REPO=/absolute/path/to/a/disposable-git-worktree
git -C "$TARGET_REPO" status --short
```

### Expect

The harness prints tag `v0.1.0`; the target is a Git repository with a known clean or intentionally recorded state.

### If it fails

Use an absolute target path and create a disposable Git worktree before proceeding.

### Verify

```bash
git describe --tags --exact-match
git -C "$TARGET_REPO" rev-parse --show-toplevel
```

### Undo

No target mutation in this step.

## Step 2: Define deterministic completion checks

### Purpose

Make “done” a repository-owned test/build contract rather than a model assertion.

### Run

```bash
cp evaluator/gate.example.json /tmp/agent-quality-gate.json
python3 -m json.tool /tmp/agent-quality-gate.json
```

Edit only `commands`, `protected_paths`, and `max_blocks`. Keep each command as an argument array. Start with `max_blocks: 1`.

### Expect

Every command already passes on the untouched target, and protected paths include evaluator files the agent must not change.

### If it fails

Fix the target's pre-existing test environment before installing a gate. A broken baseline cannot measure the treatment.

### Verify

Run each configured `argv` manually from `$TARGET_REPO` and record its exit code.

### Undo

```bash
rm -f /tmp/agent-quality-gate.json
```

## Step 3: Install one or both repository-local adapters

### Purpose

Merge the shared Stop gate without overwriting unrelated Claude Code or Codex hooks.

### Run

```bash
python3 frontier/scripts/install_hooks.py \
  --target "$TARGET_REPO" \
  --tool both \
  --gate /tmp/agent-quality-gate.json
```

### Expect

The target gains `.agent-quality`, one Stop entry in `.claude/settings.json`, one in `.codex/hooks.json`, and a rollback manifest. Existing keys and hook arrays remain.

### If it fails

Malformed JSON is rejected before mutation. If a previous install exists, uninstall it rather than stacking another generation.

### Verify

```bash
python3 -m json.tool "$TARGET_REPO/.agent-quality/install-manifest.json"
python3 -m json.tool "$TARGET_REPO/.claude/settings.json"
python3 -m json.tool "$TARGET_REPO/.codex/hooks.json"
```

### Undo

```bash
python3 frontier/scripts/uninstall_hooks.py --target "$TARGET_REPO"
```

## Step 4: Synthetic verification

### Purpose

Prove merge, block, pass, idempotence, and byte-exact rollback without spending model tokens.

### Run

```bash
python3 -m unittest discover -s frontier/tests -v
python3 -m unittest discover -s evaluator/tests -v
```

### Expect

All synthetic installer and completion-gate tests pass, including a failing fixture that blocks and a repaired fixture that passes.

### If it fails

Do not open a model session. Resolve the exact failing test in the harness checkout first.

### Verify

```bash
git status --short
```

Only the documented target installation should be new.

### Undo

No additional target mutation in this step.

## Step 5: Product-native verification in Claude Code

### Purpose

Confirm Claude Code itself loaded the repository-local treatment through the normal login and native harness.

### Run

```bash
cd "$TARGET_REPO"
claude
```

Inside Claude Code, review the repository and Stop hook when prompted, inspect hooks with `/hooks`, then ask Claude to run the configured checks and finish without changing code.

### Expect

Claude Code starts already authenticated, displays the installed Stop command as repository-local, and surfaces `completion gate passed` when it finishes.

### If it fails

Check the exact hook command and current working directory. Do not create a second auth home, wrapper, or login flow.

### Verify

Inspect `/hooks` and the final native hook event. This is Product-native verification; the Python synthetic test alone is not proof Claude loaded it.

### Undo

Exit Claude Code. Use the uninstaller in Step 7 if you want to remove the treatment.

## Step 6: Product-native verification in Codex

### Purpose

Confirm Codex loaded the same gate while preserving the normal ChatGPT/Codex login and native agent loop.

### Run

```bash
cd "$TARGET_REPO"
codex
```

Inside Codex, run `/hooks`, review and trust the exact repository hook hash once, then ask Codex to run the configured checks and finish without changing code.

### Expect

Codex lists `.codex/hooks.json` as the source and surfaces `completion gate passed`. A changed hook hash requires review again by design.

### If it fails

Confirm the project is trusted and hooks are enabled. Do not bypass normal authentication or add API billing.

### Verify

Use `/hooks` and the native Stop event. This is Product-native verification and is distinct from Step 4.

### Undo

Exit Codex. Use the uninstaller in Step 7 if you want to remove the treatment.

## Step 7: Compare, inspect, and roll back

### Purpose

Run a fair baseline/enhanced pair and leave the target exactly as it was.

### Run

For the baseline, uninstall the adapter and run `claude` or `codex` normally. For the enhanced arm, reinstall the same tag and gate. Keep model, task prompt, starting commit, account configuration, permissions, effort, time limit, evaluator, and sampling equal. Run each arm once; do not automatically retry.

Then roll back:

```bash
python3 frontier/scripts/uninstall_hooks.py --target "$TARGET_REPO"
```

### Expect

The comparison records pass/fail, evaluator score, elapsed time, model cycles/calls when available, tokens, human intervention, and failure reason. The uninstaller restores preexisting JSON byte-for-byte and removes installer-created files.

### If it fails

If a managed file changed after installation, inspect the diff. Use `--force` only when you intentionally want the manifest backup to replace that post-install edit.

### Verify

```bash
git -C "$TARGET_REPO" status --short
test ! -e "$TARGET_REPO/.agent-quality/install-manifest.json"
```

### Undo

Reinstall with Step 3 if you decide to keep the gate.
