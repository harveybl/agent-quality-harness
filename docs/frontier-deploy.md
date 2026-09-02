# Add the completion gate to Claude Code and Codex

This is the everyday frontier path: one package, one repository-local install,
and the normal `claude` and `codex` applications. AQH does not create a second
login, change global memories or skills, replace MCP configuration, or add API
billing. The account environment remains the same in clean and enhanced runs.

## Step 1: Install the small base package

### Purpose

Put the `aqh` command in an isolated Python environment. The base package has
no runtime dependencies.

### Run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install \
  "agent-quality-harness @ https://github.com/harveybl/agent-quality-harness/releases/download/v0.2.0/agent_quality_harness-0.2.0-py3-none-any.whl"
aqh --help
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

### Expect

Help lists `install`, `doctor`, `verify`, and `uninstall`.

### If it fails

Use Python 3.11 or newer and confirm that the pinned GitHub release asset is
reachable. The project is distributed through its GitHub release, not PyPI.

### Verify

```bash
aqh --help
```

### Undo

```bash
python -m pip uninstall agent-quality-harness
```

## Step 2: Install and verify one repository-local gate

This step includes **Synthetic verification** before any model tokens are used.

### Purpose

Add the same deterministic completion contract to Claude Code and Codex while
preserving unrelated repository settings.

### Run

Create `quality-gate.json` in the target repository and replace the example
test command with one that already passes before the experiment:

```json
{
  "schema_version": 1,
  "max_blocks": 2,
  "protected_paths": ["tests", "quality-gate.json"],
  "commands": [
    {"name": "tests", "argv": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"], "timeout_seconds": 900}
  ]
}
```

Then run:

```bash
aqh install --target /absolute/path/to/repository --tool both --gate /absolute/path/to/repository/quality-gate.json
aqh doctor --target /absolute/path/to/repository
aqh verify --target /absolute/path/to/repository
```

### Expect

`doctor` reports both clients and a custom gate. `verify` reports pass, bounded
failure, and exact rollback checks without making a model call.

### If it fails

Fix a pre-existing test failure or the reported JSON/path issue. Do not create
an authentication wrapper or bypass client security.

### Verify

```bash
python -m json.tool /absolute/path/to/repository/.agent-quality/install-manifest.json
aqh doctor --target /absolute/path/to/repository
```

### Undo

```bash
aqh uninstall --target /absolute/path/to/repository
```

## Step 3: Product-native verification

### Purpose

Prove each native client loaded the installed hook; synthetic verification is
necessary but is not evidence that a product consumed it.

### Run

```bash
cd /absolute/path/to/repository
claude
```

In Claude Code, inspect `/hooks`, then ask it to run the configured checks and
finish. Repeat with an interactive `codex` session and inspect `/hooks`.
Repository hooks are not loaded by `codex exec`; use the interactive CLI for a
Codex hook treatment. If a gate command needs environment variables, export
them before starting `claude` or `codex` so the Stop-hook subprocess inherits
them. If using a supported desktop client, open this exact repository and
perform the same check there as a separate qualification.

### Expect

Each tested client identifies the repository-local hook and surfaces
`completion gate passed`. Normal existing authentication is used.

### If it fails

Confirm the exact repository is open, trust the displayed hook hash if you
recognize it, inspect `aqh doctor`, and confirm any variables required by the
test command were present when the native client started. After changing hook
configuration, start a new native session because clients may snapshot hook
commands at launch. Do not add a second login flow.

### Verify

Record the client/version, `/hooks` source, and native Stop event. Label CLI and
desktop observations separately.

### Undo

Exit the client. The hook remains local to the repository until Step 4.

## Step 4: Compare once and roll back exactly

### Purpose

Measure the treatment fairly, then restore the repository's prior files.

### Run

Run the clean condition after `aqh uninstall`, reset a disposable candidate to
the recorded starting commit, then run the enhanced condition after the Step 2
install. Keep task, model, effort, permissions, time limit, evaluator, and
starting files equal. Run each condition once; never automatically retry a full
model run.

Finally:

```bash
aqh uninstall --target /absolute/path/to/repository
```

### Expect

The comparison records pass/fail, score, elapsed time, model calls, tokens when
reported, human intervention, and major failure reason. Uninstall restores
pre-existing managed files byte-for-byte.

### If it fails

If a managed file changed after installation, inspect it. Use `--force` only
when you intentionally want the saved pre-install bytes to replace that edit.

### Verify

```bash
git -C /absolute/path/to/repository status --short
```

Compare this output with the state recorded before installation.

### Undo

Re-run Step 2 only if you choose to keep the completion gate.
