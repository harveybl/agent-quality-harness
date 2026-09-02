# KISS AVO Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a bounded, explicit CLI-only AVO experiment from the existing supervisor core while removing campaign receipts, auth wrappers, canary generations, and approval architecture from everyday use.

**Architecture:** A tool-less Strands supervisor receives only a public task summary, worker diff, and deterministic check evidence, then emits a validated directive. A small experiment runner invokes normal installed Claude or Codex CLIs, evaluates between turns, and permits a configured number of repair cycles without restarting the worker run.

**Tech Stack:** Python 3.11+, Strands Agents, Pydantic, native Claude Code CLI, native Codex CLI, unittest

---

### Task 1: Import the minimal directive model and supervisor

**Files:**
- Modify: `pyproject.toml`
- Create: `src/agent_quality_harness/experiments/__init__.py`
- Create: `src/agent_quality_harness/experiments/directive.py`
- Create: `src/agent_quality_harness/experiments/supervisor.py`
- Create: `tests/test_avo_supervisor.py`
- Source reference: `/Users/brandonharvey/Development-Projects/agent-quality-supervisor-frontier-action-lifecycle/src/aqs/backends/strands_avo.py`

- [ ] **Step 1: Write failing directive validation tests**

Require an `experiment` optional dependency extra containing the pinned
Strands and Pydantic requirements. Require actions `continue`, `redirect`, or `stop`; nonempty strategy,
instruction, and rationale; a tool-less supervisor; persistent session state
outside the candidate; and explicit usage metrics.

- [ ] **Step 2: Run and confirm the experiment package is absent**

Run: `PYTHONPATH=src python3 -m unittest tests.test_avo_supervisor -v`  
Expected: import failure.

- [ ] **Step 3: Implement the smallest supervisor protocol**

Add the `experiment` extra without changing base dependencies. Port the
validated directive data model and Strands `Agent` call only. Exclude
route receipts, canaries, lane leases, fixture seals, provider billing policy,
and campaign scheduling. Validate that no tools are passed and that the session
root is outside the candidate workspace.

- [ ] **Step 4: Verify supervisor tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_avo_supervisor -v`  
Expected: all tests pass with a scripted Strands model and zero credentials.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/agent_quality_harness/experiments tests/test_avo_supervisor.py
git commit -m "feat: add bounded tool-less AVO supervisor"
```

### Task 2: Direct personal-plan providers

**Files:**
- Create: `src/agent_quality_harness/experiments/providers.py`
- Create: `tests/test_avo_providers.py`
- Source reference: `/Users/brandonharvey/Development-Projects/agent-quality-supervisor-frontier-action-lifecycle/src/aqs/adapters`
- Source reference: `/Users/brandonharvey/Development-Projects/agent-quality-supervisor-frontier-action-lifecycle/src/aqs/backends/claude_subscription.py`

- [ ] **Step 1: Write failing argv and parsing tests**

Assert Claude uses executable `claude` and Codex uses executable `codex` from
the current environment. Reject API-key flags, base URLs, AWS, Bedrock, and
automatic fallback flags. Parse exact model identity, session identity, token
usage, elapsed time, and final result from recorded native JSON fixtures.

- [ ] **Step 2: Run and confirm providers are missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_avo_providers -v`  
Expected: import failure.

- [ ] **Step 3: Implement direct provider commands**

Use only current documented native noninteractive and resume flags. Keep the
normal user environment and authentication. Supervisor calls disable tools but
do not replace auth homes or setting sources. Worker calls retain their native
tool harness. Every invocation returns a typed receipt with resolved client,
model, session, usage, elapsed time, exit code, and output.

- [ ] **Step 4: Verify provider fixtures and installed CLI help compatibility**

Run: `PYTHONPATH=src python3 -m unittest tests.test_avo_providers -v && claude --version && codex --version`  
Expected: fixture tests pass and both normal CLIs report versions.

- [ ] **Step 5: Commit**

```bash
git add src/agent_quality_harness/experiments/providers.py tests/test_avo_providers.py
git commit -m "feat: add direct personal-plan experiment providers"
```

### Task 3: Bounded review-and-repair runner

**Files:**
- Create: `src/agent_quality_harness/experiments/avo.py`
- Create: `tests/test_avo_runner.py`
- Modify: `src/agent_quality_harness/cli.py`

- [ ] **Step 1: Write failing lifecycle tests**

Use scripted providers and evaluator commands. Cover initial pass with zero
supervisor credit, initial failure followed by directive and resumed pass,
bounded repeated failure, supervisor failure, worker failure, protected-path
failure, no full-run retry, and separate worker/supervisor usage totals.

- [ ] **Step 2: Run and confirm the runner is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_avo_runner -v`  
Expected: import failure.

- [ ] **Step 3: Implement the explicit experiment lifecycle**

Expose an `AvoRun` configuration with workspace, task, worker, supervisor,
model identities, evaluator argument arrays, protected paths,
`max_review_calls`, and `max_repair_turns`. Evaluate after the initial worker
turn and each resumed repair. Never restart a worker run. Save a compact ledger
under `.agent-quality/runs`.

- [ ] **Step 4: Verify runner and all experiment tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_avo_supervisor tests.test_avo_providers tests.test_avo_runner -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_quality_harness/experiments/avo.py src/agent_quality_harness/cli.py tests/test_avo_runner.py
git commit -m "feat: add explicit bounded AVO experiment"
```

### Task 4: Experiment documentation and safety labels

**Files:**
- Create: `docs/avo-experiment.md`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `tests/test_docs.py`

- [ ] **Step 1: Write failing documentation-boundary tests**

Assert the docs label AVO experimental and CLI-only, distinguish it from the
default completion gate, state that it may consume both personal subscriptions,
prohibit external paid routes, describe repair limits, and avoid uplift claims.

- [ ] **Step 2: Run and confirm the boundary is undocumented**

Run: `PYTHONPATH=src python3 -m unittest tests.test_docs -v`  
Expected: AVO boundary assertion fails.

- [ ] **Step 3: Add concise experiment instructions and rollback**

Document one dry synthetic example and one explicit live example. State that
desktop support is unqualified, authentication is the user's normal CLI state,
and every real run records actual model/client identities.

- [ ] **Step 4: Verify documentation and experiment suite**

Run: `PYTHONPATH=src python3 -m unittest tests.test_docs tests.test_avo_supervisor tests.test_avo_providers tests.test_avo_runner -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add README.md SECURITY.md docs/avo-experiment.md tests/test_docs.py
git commit -m "docs: define the experimental AVO boundary"
```
