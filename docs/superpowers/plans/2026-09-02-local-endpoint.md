# Local Endpoint UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a simple optional `aqh local doctor|run` path for an existing llama.cpp-compatible endpoint without requiring Docker or GPU management.

**Architecture:** A standard-library endpoint probe validates health and model identity. The existing Strands controller remains the enhanced worker and is loaded only when the `local` extra is installed. Docker/NVIDIA files remain an optional reproducibility backend with explicit isolation differences.

**Tech Stack:** Python 3.11+, urllib, Strands Agents, OpenAI compatibility client, Pydantic, llama.cpp server

---

### Task 1: Optional dependency boundary

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_packaging.py`

- [ ] **Step 1: Write failing metadata tests**

Build a wheel, inspect `METADATA`, and assert base `Requires-Dist` is empty while
the `local` extra contains the pinned Strands, OpenAI, and Pydantic packages.

- [ ] **Step 2: Run and confirm the package has no local extra**

Run: `PYTHONPATH=src python3 -m unittest tests.test_packaging -v`  
Expected: missing `local` extra assertion failure.

- [ ] **Step 3: Add the pinned local extra and package local harness modules**

Use the existing versions from `local/requirements.lock`. Keep all imports of
optional packages inside worker construction so `aqh install`, `doctor`,
`verify`, and `uninstall` run from a base-only installation.

- [ ] **Step 4: Verify base and extra metadata**

Run: `PYTHONPATH=src python3 -m unittest tests.test_packaging -v`  
Expected: metadata tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/test_packaging.py
git commit -m "build: isolate local model dependencies"
```

### Task 2: Endpoint doctor

**Files:**
- Create: `src/agent_quality_harness/local_endpoint.py`
- Create: `tests/test_local_endpoint.py`
- Modify: `src/agent_quality_harness/cli.py`

- [ ] **Step 1: Write failing real-HTTP fixture tests**

Use `http.server.ThreadingHTTPServer` in the test process to serve `/health`
and `/v1/models`. Assert healthy identity, connection refusal, invalid JSON,
unexpected model, and a read-only result.

```python
report = diagnose_endpoint("http://127.0.0.1:PORT/v1", expected_model="qwen-local")
self.assertTrue(report.healthy)
self.assertEqual(report.model_ids, ("qwen-local",))
```

- [ ] **Step 2: Run and confirm the endpoint module is absent**

Run: `PYTHONPATH=src python3 -m unittest tests.test_local_endpoint -v`  
Expected: import failure.

- [ ] **Step 3: Implement bounded standard-library probes**

Normalize a `/v1` endpoint, probe server health with a five-second timeout,
parse model IDs, and return a typed immutable report. Never start or stop a
server. `aqh local doctor` prints endpoint, reachability, model match,
containment mode, and missing optional dependencies.

- [ ] **Step 4: Verify all endpoint tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_local_endpoint -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_quality_harness/local_endpoint.py src/agent_quality_harness/cli.py tests/test_local_endpoint.py
git commit -m "feat: diagnose existing local model endpoints"
```

### Task 3: Local run adapter

**Files:**
- Create: `src/agent_quality_harness/local_runner.py`
- Create: `tests/test_local_runner.py`
- Modify: `src/agent_quality_harness/cli.py`
- Modify: `local/harness/controller.py`

- [ ] **Step 1: Write failing command and no-retry tests**

Use a fake Worker with exact plan, implementation, and repair metrics. Assert
the public `run_local` adapter returns the ledger, uses the supplied endpoint
and model, performs at most the contract continuation count, and records
`automatic_run_retries == 0`.

- [ ] **Step 2: Run and confirm the adapter is missing**

Run: `PYTHONPATH=src python3 -m unittest tests.test_local_runner -v`  
Expected: import failure.

- [ ] **Step 3: Implement the adapter and CLI**

Expose `run_local(workspace, endpoint, model)`. Validate endpoint first, lazily
construct `StrandsWorker`, run the existing `Controller`, print the ledger, and
map a nonpassing terminal reason to exit code 1. Do not add server lifecycle or
automatic retry behavior.

- [ ] **Step 4: Verify runner and existing controller tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_local_runner local.tests.test_controller -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agent_quality_harness/local_runner.py src/agent_quality_harness/cli.py local/harness/controller.py tests/test_local_runner.py
git commit -m "feat: run enhanced local worker against an endpoint"
```

### Task 4: Honest native and Docker documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/local-deploy.md`
- Modify: `docs/how-it-works.md`
- Modify: `SECURITY.md`
- Modify: `tests/test_docs.py`
- Modify: `scripts/lint_steps.py`

- [ ] **Step 1: Replace the fixed-step test with failing UX assertions**

Assert the docs contain the two-command native path, say the server is
user-supplied, distinguish native path bounding from Docker isolation, and keep
the optional NVIDIA Compose commands.

- [ ] **Step 2: Run and confirm the old eleven-step runbook fails the new UX test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_docs -v`  
Expected: missing simple-path or isolation-language assertion failure.

- [ ] **Step 3: Rewrite the entry path and retain the reproducibility appendix**

Lead with install, server start outside AQH, `local doctor`, and `local run`.
Move Ubuntu/NVIDIA/Docker material into an optional reproducibility section.
Remove the exact eleven-step count requirement from the linter and tests.

- [ ] **Step 4: Verify docs and complete local unit suite**

Run: `PYTHONPATH=src python3 -m unittest tests.test_docs tests.test_local_endpoint tests.test_local_runner local.tests.test_contracts local.tests.test_controller local.tests.test_file_tools local.tests.test_runtime_files -v`  
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add README.md SECURITY.md docs/local-deploy.md docs/how-it-works.md tests/test_docs.py scripts/lint_steps.py
git commit -m "docs: make native local endpoint the simple path"
```

