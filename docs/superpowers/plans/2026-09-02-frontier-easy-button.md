# Frontier Easy-Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a dependency-free `aqh` command that installs, diagnoses, verifies, and exactly removes repository-local Claude Code and Codex quality hooks.

**Architecture:** A small `src/agent_quality_harness` package owns hook construction, transactional file mutation, diagnostics, and CLI parsing. The completion gate and quality contract ship as package resources and are copied into each target repository. Existing `frontier/scripts` become compatibility entry points into the package.

**Tech Stack:** Python 3.11+, standard library, `unittest`, setuptools, GitHub Actions

---

### Task 1: Package and CLI skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/agent_quality_harness/__init__.py`
- Create: `src/agent_quality_harness/cli.py`
- Create: `tests/test_cli.py`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing CLI help test**

```python
class CliTests(unittest.TestCase):
    def test_help_lists_every_public_command(self) -> None:
        process = subprocess.run(
            [sys.executable, "-m", "agent_quality_harness.cli", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        for command in ("install", "doctor", "verify", "uninstall", "local", "experiment"):
            self.assertIn(command, process.stdout)
```

- [ ] **Step 2: Run the focused test and confirm the package import fails**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli -v`  
Expected: `ModuleNotFoundError` for `agent_quality_harness`.

- [ ] **Step 3: Add the minimal package metadata and argparse entry point**

Define project name `agent-quality-harness`, version `0.2.0.dev0`, Python
`>=3.11`, no base dependencies, and script `aqh = agent_quality_harness.cli:main`.
Create subparsers for the six commands. Unimplemented command handlers must
return a clear nonzero `not available in this build` result until their task is
completed; they must never silently succeed.

- [ ] **Step 4: Run the focused test and full baseline suite**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli -v && make check`  
Expected: CLI test passes and all preexisting tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/agent_quality_harness tests/test_cli.py Makefile
git commit -m "feat: add agent quality harness CLI package"
```

### Task 2: Portable hook resources and construction

**Files:**
- Create: `src/agent_quality_harness/resources/completion_gate.py`
- Create: `src/agent_quality_harness/resources/quality_context.py`
- Create: `src/agent_quality_harness/resources/quality_contract.txt`
- Create: `src/agent_quality_harness/hooks.py`
- Create: `tests/test_hooks.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write failing tests for portable commands and both events**

```python
class HookTests(unittest.TestCase):
    def test_hooks_use_absolute_paths_without_shell_substitution(self) -> None:
        hooks = build_hooks(Path("/opt/Python 3/python"), Path("/tmp/project with spaces"))
        encoded = json.dumps(hooks)
        self.assertIn("SessionStart", hooks["hooks"])
        self.assertIn("Stop", hooks["hooks"])
        self.assertNotIn("$(", encoded)
        self.assertNotIn("python3", encoded)
        self.assertIn("/tmp/project with spaces/.agent-quality/completion_gate.py", encoded)
```

- [ ] **Step 2: Run the test and confirm `build_hooks` is absent**

Run: `PYTHONPATH=src python3 -m unittest tests.test_hooks -v`  
Expected: import failure for `agent_quality_harness.hooks`.

- [ ] **Step 3: Implement resource loading and hook construction**

Use `importlib.resources.files("agent_quality_harness.resources")`. Render
commands with `subprocess.list2cmdline` on Windows and `shlex.join` on POSIX.
`quality_context.py` reads the adjacent contract and returns native-compatible
SessionStart context JSON. The session hook invokes `quality_context.py`; the
Stop hook invokes `completion_gate.py`. Both use absolute interpreter and
target paths.

- [ ] **Step 4: Verify tests and wheel resource inclusion**

Run: `PYTHONPATH=src python3 -m unittest tests.test_hooks -v && python3 -m build`  
Expected: tests pass and wheel contains all three resource files.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/agent_quality_harness/resources src/agent_quality_harness/hooks.py tests/test_hooks.py
git commit -m "feat: add portable native hook resources"
```

### Task 3: Transactional installation

**Files:**
- Create: `src/agent_quality_harness/installer.py`
- Create: `tests/test_installer.py`
- Modify: `src/agent_quality_harness/cli.py`
- Modify: `frontier/scripts/install_hooks.py`

- [ ] **Step 1: Write failing behavioral tests**

Cover fresh default installation of both clients, `--tool` narrowing, merge
preservation, same-input idempotence, malformed JSON refusal, paths containing
spaces, and failure injection after each write. The failure-injection assertion
must compare a complete target-tree byte snapshot before and after the failed
installation.

```python
def test_failure_on_second_replace_restores_entire_tree(self) -> None:
    before = snapshot(self.root)
    with mock.patch("agent_quality_harness.installer.os.replace", side_effect=[None, OSError("disk")]):
        with self.assertRaisesRegex(OSError, "disk"):
            install(self.root, tool="both")
    self.assertEqual(snapshot(self.root), before)
```

- [ ] **Step 2: Run tests and confirm transactional behavior is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_installer -v`  
Expected: import or assertion failures for the new installer API.

- [ ] **Step 3: Implement one transaction**

Expose `install(target: Path, tool: str, gate_source: Path | None) -> Manifest`.
Validate every input and construct every output before mutation. Save original
bytes, create backups and a pending manifest, replace files, and on any
exception restore original bytes and remove created paths. Mark the manifest
`complete` only after successful writes. Use a stable harness entry identifier
to merge without duplicating unrelated hooks.

- [ ] **Step 4: Run focused and compatibility tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_installer frontier.tests.test_hook_installers -v`  
Expected: all installer and compatibility tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_quality_harness/installer.py src/agent_quality_harness/cli.py frontier/scripts/install_hooks.py tests/test_installer.py frontier/tests/test_hook_installers.py
git commit -m "feat: install native hooks transactionally"
```

### Task 4: Exact uninstall and explicit update behavior

**Files:**
- Create: `src/agent_quality_harness/uninstaller.py`
- Modify: `src/agent_quality_harness/installer.py`
- Modify: `src/agent_quality_harness/cli.py`
- Modify: `frontier/scripts/uninstall_hooks.py`
- Modify: `tests/test_installer.py`

- [ ] **Step 1: Write failing tests for exact restore and post-install edits**

```python
def test_uninstall_restores_original_bytes(self) -> None:
    original = b'{"custom":true,"hooks":{}}\n'
    self.settings.write_bytes(original)
    install(self.root, tool="both")
    uninstall(self.root)
    self.assertEqual(self.settings.read_bytes(), original)

def test_uninstall_refuses_later_user_edit(self) -> None:
    install(self.root, tool="both")
    self.settings.write_text("{}\n", encoding="utf-8")
    with self.assertRaisesRegex(RuntimeError, "changed after installation"):
        uninstall(self.root)
```

- [ ] **Step 2: Confirm the focused tests fail for the missing package API**

Run: `PYTHONPATH=src python3 -m unittest tests.test_installer -v`  
Expected: uninstall-related tests fail.

- [ ] **Step 3: Implement exact uninstall and explicit update**

Expose `uninstall(target: Path, force: bool = False)`. Verify installed hashes,
restore backup bytes, remove only created files, and prune only empty created
directories. An installation with different selected clients or gate hash must
raise with an instruction to run `aqh uninstall` or explicit `aqh install
--update`; `--update` itself performs an uninstall/install transaction.

- [ ] **Step 4: Verify all installer tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_installer frontier.tests.test_hook_installers -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_quality_harness/uninstaller.py src/agent_quality_harness/installer.py src/agent_quality_harness/cli.py frontier/scripts/uninstall_hooks.py tests/test_installer.py
git commit -m "feat: add exact harness rollback"
```

### Task 5: Repair-budget regression and native evidence

**Files:**
- Modify: `evaluator/completion_gate.py`
- Modify: `src/agent_quality_harness/resources/completion_gate.py`
- Modify: `evaluator/tests/test_completion_gate.py`
- Create: `src/agent_quality_harness/doctor.py`
- Create: `tests/test_doctor.py`

- [ ] **Step 1: Write failing payload and evidence tests**

Add one test that invokes the same failing Stop payload twice with a session ID
but no turn ID and no `stop_hook_active`; the second invocation must exhaust a
one-block budget. Add one payload with no IDs and require a deterministic
bounded fallback. Add a doctor test reading the newest state file and reporting
outcome, blocks, and check count.

- [ ] **Step 2: Run focused tests and observe the current reset defect**

Run: `PYTHONPATH=src python3 -m unittest evaluator.tests.test_completion_gate tests.test_doctor -v`  
Expected: the missing-field budget test blocks twice or doctor import fails.

- [ ] **Step 3: Implement stable fallback state and doctor diagnostics**

Always load an existing state path when present. Derive the key from workspace,
session fallback, and turn fallback; include `cwd`, `session_id`, `turn_id`,
`outcome`, `invocations`, `blocks`, and summarized checks in saved evidence.
Doctor validates installed files and executable paths without authentication or
model calls.

- [ ] **Step 4: Verify resource parity and tests**

Run: `cmp evaluator/completion_gate.py src/agent_quality_harness/resources/completion_gate.py && PYTHONPATH=src python3 -m unittest evaluator.tests.test_completion_gate tests.test_doctor -v`  
Expected: files match and tests pass.

- [ ] **Step 5: Commit**

```bash
git add evaluator/completion_gate.py evaluator/tests/test_completion_gate.py src/agent_quality_harness/resources/completion_gate.py src/agent_quality_harness/doctor.py tests/test_doctor.py
git commit -m "fix: bound native repair state across hook payloads"
```

### Task 6: Synthetic verification command and cleanup

**Files:**
- Create: `src/agent_quality_harness/verifier.py`
- Create: `tests/test_verifier.py`
- Modify: `src/agent_quality_harness/cli.py`
- Delete: `frontier/hooks/claude/settings.fragment.json`
- Delete: `frontier/hooks/codex/hooks.fragment.json`
- Delete: `frontier/AGENTS.md`
- Delete: `frontier/CLAUDE.md`
- Modify: `frontier/README.md`

- [ ] **Step 1: Write a failing end-user verification test**

Install into a temporary Git repository, run `verify`, assert one synthetic pass
and one bounded fail/repair cycle, then assert the target's application files
are unchanged.

- [ ] **Step 2: Confirm the verifier is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_verifier -v`  
Expected: import failure for `agent_quality_harness.verifier`.

- [ ] **Step 3: Implement verifier and remove duplicated resources**

The verifier calls installed scripts with synthetic JSON through stdin and
uses a temporary fixture command. It prints a compact PASS/FAIL line for hook
shape, passing event, bounded failing event, and target immutability. Remove
only files now replaced by tested package resources.

- [ ] **Step 4: Run the complete frontier suite**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli tests.test_hooks tests.test_installer tests.test_doctor tests.test_verifier evaluator.tests.test_completion_gate frontier.tests.test_hook_installers -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add -A src tests evaluator frontier
git commit -m "feat: add synthetic harness verification"
```
