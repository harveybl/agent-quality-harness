# E2E Quality and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the installer and harness work end to end, measure quality effects on multiple matched tasks, obtain Fable 5.1 review, and publish only after the complete release audit passes.

**Architecture:** Deterministic CI and packaging checks run first. Authenticated native smoke tests and local-model trials run separately with exact treatment-delivery evidence. Matched baseline/enhanced ledgers feed one concise report and the public documentation.

**Tech Stack:** GitHub Actions, Python unittest, build/twine, Claude Code CLI/Desktop, Codex CLI/Desktop, llama.cpp, Linux RTX 5090, JSON ledgers

---

### Task 1: Cross-platform build and CI matrix

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `scripts/verify_wheel.py`
- Create: `tests/test_ci_contract.py`
- Modify: `Makefile`

- [ ] **Step 1: Write failing CI-contract tests**

Assert Ubuntu, macOS, and Windows jobs exist; Python 3.11 through the current
supported release are covered; a wheel is installed outside the checkout; base
dependencies are checked; Docker validation is Ubuntu-only and optional.

- [ ] **Step 2: Run and confirm current CI is Ubuntu-only**

Run: `PYTHONPATH=src python3 -m unittest tests.test_ci_contract -v`  
Expected: platform matrix assertions fail.

- [ ] **Step 3: Implement the matrix and clean-wheel verifier**

The verifier builds a wheel, creates a temporary virtual environment, installs
the wheel, runs `aqh --help`, installs into a temporary Git repository, runs
`aqh verify`, uninstalls, and confirms exact target restoration.

- [ ] **Step 4: Run local equivalents**

Run: `PYTHONPATH=src python3 -m unittest tests.test_ci_contract -v && python3 scripts/verify_wheel.py && make check`  
Expected: all commands exit zero.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml scripts/verify_wheel.py tests/test_ci_contract.py Makefile
git commit -m "ci: verify cross-platform easy-button packaging"
```

### Task 2: Native CLI and desktop treatment-delivery runbook

**Files:**
- Create: `docs/e2e-native.md`
- Create: `scripts/record_native_e2e.py`
- Create: `tests/test_native_e2e_recorder.py`

- [ ] **Step 1: Write failing evidence-recorder tests**

Require client, resolved model, client version, surface (`cli` or `desktop`),
hook source, SessionStart evidence, Stop evidence, checks, elapsed time, usage,
and human intervention. Reject a result without exact hook delivery.

- [ ] **Step 2: Run and confirm the recorder is absent**

Run: `PYTHONPATH=src python3 -m unittest tests.test_native_e2e_recorder -v`  
Expected: import failure.

- [ ] **Step 3: Implement recorder and concise runbook**

The recorder consumes native JSON/ledger artifacts and writes a sanitized
record. The runbook uses normal `claude` and `codex` commands, `/hooks` trust,
and local desktop sessions. It never creates an auth home or bypasses managed
policy.

- [ ] **Step 4: Verify recorder tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_native_e2e_recorder -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/e2e-native.md scripts/record_native_e2e.py tests/test_native_e2e_recorder.py
git commit -m "test: add native treatment delivery evidence"
```

### Task 3: Matched multi-task fixtures and ledger aggregation

**Files:**
- Create: `benchmarks/tasks.json`
- Create: `benchmarks/README.md`
- Create: `scripts/summarize_benchmarks.py`
- Create: `tests/test_benchmark_contract.py`
- Import sanitized fixtures under: `benchmarks/fixtures/`

- [ ] **Step 1: Write failing fixture-contract tests**

Require at least three tasks of different failure modes, immutable start hashes,
argument-array evaluators, protected paths, task difficulty rationale, and no
private paths or credentials. Require matched arm fields for model, effort,
prompt, permissions, time, and evaluator.

- [ ] **Step 2: Run and confirm benchmark files are absent**

Run: `PYTHONPATH=src python3 -m unittest tests.test_benchmark_contract -v`  
Expected: missing benchmark manifest failure.

- [ ] **Step 3: Add sanitized, repeatable fixtures**

Use one integration-repair task, one stateful/recovery task, and one
cross-file feature task. Do not use repositories under active development.
The summary script reports pass/fail, score, elapsed time, calls, tokens, human
intervention, failure reason, and material improvement without pooling unmatched
conditions.

- [ ] **Step 4: Verify fixture hashes and synthetic evaluators**

Run: `PYTHONPATH=src python3 -m unittest tests.test_benchmark_contract -v && python3 scripts/summarize_benchmarks.py --validate-only benchmarks/tasks.json`  
Expected: all fixtures and evaluators validate.

- [ ] **Step 5: Commit**

```bash
git add benchmarks scripts/summarize_benchmarks.py tests/test_benchmark_contract.py
git commit -m "test: add matched multi-task benchmark fixtures"
```

### Task 4: Authenticated frontier E2E observations

**Files:**
- Create runtime evidence under: `evidence/2026-09-frontier-e2e/`
- Modify: `docs/evidence.md`

- [ ] **Step 1: Verify synthetic and packaging gates before model calls**

Run: `python3 scripts/verify_wheel.py && make check`  
Expected: zero failures.

- [ ] **Step 2: Run each planned native and enhanced condition once**

For selected Claude and Codex models, use identical task checkout, prompt,
effort, permissions, evaluator, and time. Baseline has no AQH files. Enhanced
uses `aqh install` and records both native hook events. Do not automatically
retry a failed run.

- [ ] **Step 3: Run bounded AVO conditions only after the corresponding native observation**

Use the explicit CLI experiment, identical worker settings, and configured
review/repair limits. Record worker and supervisor usage separately.

- [ ] **Step 4: Validate and summarize frontier evidence**

Run: `python3 scripts/summarize_benchmarks.py evidence/2026-09-frontier-e2e/*.json`  
Expected: every row has treatment delivery and matched-condition validation.

- [ ] **Step 5: Commit sanitized evidence and honest conclusions**

```bash
git add evidence/2026-09-frontier-e2e docs/evidence.md
git commit -m "evidence: record frontier easy-button observations"
```

### Task 5: Local macOS and Linux/5090 E2E observations

**Files:**
- Create runtime evidence under: `evidence/2026-09-local-e2e/`
- Modify: `docs/evidence.md`

- [ ] **Step 1: Run local doctor against the exact endpoint on each host**

Record OS, hardware, endpoint, server version, model identity, artifact hash
when available, context, sampling settings, and containment mode.

- [ ] **Step 2: Run plain and enhanced Qwen arms once per fixture**

Keep model artifact, task, start, prompt, context, sampling, evaluator, and time
equal. Baseline uses a plain coding loop. Enhanced uses anchored planning,
bounded tools, syntax-safe edits, checks, and configured continuation. No
automatic full-run retries.

- [ ] **Step 3: Run Muse only if identity and permitted runtime are verified**

If unavailable, write one explicit unqualified record rather than substituting
another model or fabricating a comparison.

- [ ] **Step 4: Validate and summarize local evidence**

Run: `python3 scripts/summarize_benchmarks.py evidence/2026-09-local-e2e/*.json`  
Expected: matched rows report all required metrics and host/backend differences.

- [ ] **Step 5: Commit sanitized evidence and conclusions**

```bash
git add evidence/2026-09-local-e2e docs/evidence.md
git commit -m "evidence: record local endpoint quality observations"
```

### Task 6: Fable 5.1 review and corrections

**Files:**
- Create: `evidence/2026-09-fable-review/summary.md`
- Modify files identified by confirmed review findings

- [ ] **Step 1: Run final deterministic verification and record commit SHA**

Run: `git status --short && git rev-parse HEAD && python3 scripts/verify_wheel.py && make check`  
Expected: intentional worktree state and zero verification failures.

- [ ] **Step 2: Request read-only Fable review through the normal CLI**

Run `claude --model fable` with a prompt to inspect the approved design,
implementation diff, tests, packaging, native/local evidence, UX, rollback, and
claims. Capture the structured init event and confirm model
`claude-fable-5-1`, normal personal-plan authentication, and no permission
denials.

- [ ] **Step 3: Classify and reproduce every finding**

For each correctness finding, write a failing regression test before changing
production code. For documentation-only findings, update the exact assertion or
runbook and run the documentation suite.

- [ ] **Step 4: Rerun affected suites and the full release verification**

Run: `python3 scripts/verify_wheel.py && make check`  
Expected: zero failures after corrections.

- [ ] **Step 5: Commit sanitized review evidence and fixes**

```bash
git add -A
git commit -m "fix: address Fable 5.1 release review"
```

### Task 7: Final audit and publication

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: companion Site deployment artifacts

- [ ] **Step 1: Audit every design requirement against current evidence**

Record one authoritative file, command result, or runtime artifact for each
frontier command, rollback invariant, platform, native client surface, local
backend, quality comparison, AVO boundary, and unsupported path.

- [ ] **Step 2: Run the complete release command set fresh**

Run: `git diff --check && python3 scripts/verify_wheel.py && make check`  
Expected: zero failures.

- [ ] **Step 3: Review public docs and release diff**

Ensure two-command installation leads the README, local and AVO are visibly
optional, links resolve on the release tag, and quality claims match the actual
multi-task evidence.

- [ ] **Step 4: Publish only after all prior checkboxes have evidence**

Push the reviewed branch, create the release artifacts and tag, wait for CI,
then update and publish the companion Site. If any gate is missing, leave the
release unpublished and continue verification.

- [ ] **Step 5: Verify public state**

Open the tagged repository links, install from the published artifact in a
clean environment, confirm the release workflow is green, and verify the live
Site links and concise deployment instructions.

