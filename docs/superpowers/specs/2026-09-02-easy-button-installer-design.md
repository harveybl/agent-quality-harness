# Agent Quality Harness Easy-Button Design

**Date:** 2026-09-02  
**Status:** Approved for implementation  
**Repository:** `agent-quality-harness`

## Goal

Make the tested quality treatments usable by coworkers without replacing the
native Claude Code or Codex harnesses. Everyday frontier installation must be a
small repository-local change with exact rollback. Local-model execution and
research-grade AVO experiments remain explicit optional tracks.

## Non-goals

- Do not create authentication wrappers or alternate credential homes.
- Do not require API keys, direct API billing, AWS, Bedrock, Docker, or a GPU
  for Claude Code or Codex use.
- Do not install GPU drivers, model weights, llama.cpp, or Docker.
- Do not claim that ordinary Claude or ChatGPT chat windows load coding hooks.
- Do not call the bounded native continuation an independent AVO review.
- Do not publish until the release gates in this document pass.

## Chosen product shape

Use one repository and one Python distribution with separate command groups.
The shared evaluator, hook schemas, evidence records, and documentation remain
in one source tree.

The standard installation has no optional runtime dependencies:

```bash
python -m pip install 'agent-quality-harness @ https://github.com/harveybl/agent-quality-harness/releases/download/v0.2.0/agent_quality_harness-0.2.0-py3-none-any.whl'
cd /path/to/project
aqh install
aqh doctor
```

Local-model support is an optional package extra:

```bash
python -m pip install 'agent-quality-harness[local] @ https://github.com/harveybl/agent-quality-harness/releases/download/v0.2.0/agent_quality_harness-0.2.0-py3-none-any.whl'
aqh local doctor --endpoint http://127.0.0.1:8080/v1
aqh local run --endpoint http://127.0.0.1:8080/v1
```

Research-grade independent supervision is explicit:

```bash
aqh experiment avo ...
```

It is not installed as part of the everyday hook path and is not advertised as
desktop-compatible until that exact path has product-native evidence.

## Frontier installation behavior

`aqh install` operates on the current Git repository unless `--target` is
given. It installs both Claude Code and Codex adapters by default. This avoids
false negatives from PATH detection when a desktop app or Windows shim exists.
Read-only detection belongs in `aqh doctor`.

Users may narrow the target explicitly:

```bash
aqh install --tool claude
aqh install --tool codex
aqh install --tool both
```

The command performs one deterministic operation without a sequence of
interactive questions. Before mutation it validates:

- the target resolves to a Git worktree;
- existing Claude and Codex JSON files are valid and mergeable;
- the gate configuration is valid;
- all source payloads are available from installed package resources;
- no incompatible prior harness installation is active.

The installed treatment has two native lifecycle hooks:

1. `SessionStart` supplies a short quality contract: inspect first, plan
   briefly, preserve protected paths, run deterministic checks, use failure
   evidence for focused repair, and report honestly.
2. `Stop` runs the deterministic completion gate and may request only the
   configured bounded continuation.

The contract is delivered by a hook rather than by overwriting a project's
existing `AGENTS.md` or `CLAUDE.md`. Existing instructions, account memories,
skills, plugins, MCP servers, and native client settings remain active.

Installed commands contain absolute, platform-correct interpreter and script
paths rendered at install time. They do not depend on POSIX command
substitution, a `python3` alias, the current shell, or GUI PATH inheritance.

## Transaction and rollback

Installation is transactional:

1. Read and hash every path that may change.
2. Build every proposed output in memory.
3. Write recoverable backups and a pending manifest.
4. Replace files atomically where the platform permits.
5. On any exception, restore all original bytes and remove newly created files.
6. Mark the manifest complete only after every write succeeds.

`aqh uninstall` refuses to overwrite post-install user edits unless `--force`
is explicitly supplied. Otherwise it restores pre-install bytes exactly and
removes only installer-created files and empty installer-created directories.

Repeated installation with the same inputs is idempotent. Changing selected
clients or treatment configuration uses an explicit update path; it does not
stack duplicate hook entries.

## Completion budget and evidence

The completion gate is standard-library-only and is copied from package
resources into the target. It validates argument-array commands, protected Git
paths, timeouts, and the bounded continuation budget.

The state key uses the strongest available native identity:

1. session and turn identity when both are present;
2. session identity when turn identity is absent;
3. a bounded process/event fallback when neither identity is available.

No supported payload may reset the budget indefinitely. `aqh doctor` reports
the most recent gate event, its source client when observable, pass/fail state,
checks, and continuation count without starting a model.

## Command responsibilities

### `aqh install`

- Validate, merge, install, and print a short summary.
- Default to both clients.
- Never probe authentication or start a model.
- Never change global settings.

### `aqh doctor`

- Report installed CLI versions when discoverable.
- Report desktop-app support separately from CLI discovery.
- Validate hook JSON, installed hashes, gate configuration, executable paths,
  project trust prerequisites, and the newest native hook evidence.
- Explain managed-policy restrictions without attempting to bypass them.
- Make no changes.

### `aqh verify`

- Exercise the installed hooks synthetically with passing and failing events.
- Verify merge shape, bounded continuation, protected paths, and state writing.
- Spend no model tokens.

### `aqh uninstall`

- Restore exact prior bytes.
- Refuse silent overwrite of later user edits.
- Support explicit `--force` recovery.

## Local-model boundary

The default local path connects to an existing OpenAI-compatible endpoint. It
does not manage the model server lifecycle.

`aqh local doctor` checks:

- endpoint reachability and health;
- model identity and optional artifact lock;
- structured-output support needed by the controller;
- workspace and evaluator configuration;
- whether containment is native path-bounding or the optional Docker sandbox.

`aqh local run` uses the existing anchored-plan, bounded-navigation,
syntax-safe-edit, deterministic-check, and evidence-directed continuation
controller. Automatic full-run retries remain disabled.

Native llama.cpp is the everyday cross-platform path. It does not provide the
Docker backend's read-only root filesystem, internal network, non-root user,
capability drop, or socket isolation. Documentation and evidence must state
that difference. NVIDIA Docker remains an optional reproducibility profile for
the Linux/5090 host.

Strands, OpenAI compatibility libraries, and Pydantic are packaged only in the
`local` or experiment extras, never in the dependency-free frontier install.

## Independent AVO experiment boundary

The older supervisor worktree contains a real tool-less Strands supervisor and
personal-plan Claude provider, but its live path is coupled to campaign
receipts, canaries, lane admission, sanitized environments, and preparation
generations.

The public experiment command may reuse only the smallest validated core:

- controller-sanitized public progress;
- structured supervisor directive;
- explicit review-call and repair-turn budgets;
- native personal-plan CLI invocation;
- separate worker and supervisor usage accounting;
- no supervisor file, shell, browser, evaluator, or credential tools;
- no automatic full-run retry.

The everyday installer does not depend on this experiment. Initial AVO support
is CLI-only. Claude Code and Codex workers/providers must be labeled by their
actual resolved model and client versions. Direct API-key, AWS, Bedrock, and
external metered routes remain unsupported.

## Repository cleanup

The existing hook fragments duplicate generated installer content and use a
non-portable command. Remove them when generated hook construction is covered
by tests.

The existing `frontier/AGENTS.md` and `frontier/CLAUDE.md` contain the quality
contract but are not installed. Replace them with one package resource used by
the `SessionStart` hook and test that both clients receive identical semantic
content. Do not modify target repositories' instruction files.

Replace documentation tests that require a fixed eleven-step runbook with
tests for actionable commands, supported platforms, rollback, verification,
and honest backend boundaries.

## Verification matrix

### Deterministic tests

- Fresh install for Claude, Codex, and both.
- Merge with unrelated settings and hooks.
- Same-input idempotence and explicit update behavior.
- Malformed JSON refusal without mutation.
- Failure on each write position with complete automatic rollback.
- Exact uninstall restoration and post-install-edit refusal.
- Paths containing spaces and platform-specific command rendering.
- Gate pass, failure, timeout, protected-path change, budget exhaustion, and
  payloads missing turn or session fields.
- `doctor` and `verify` remain read-only except documented temporary evidence.
- Local endpoint contract and controller tests without a GPU.

### Packaging and platform tests

- Build sdist and wheel.
- Install the wheel in a clean virtual environment.
- Run the command suite from outside the source checkout.
- CI on current supported Python versions for Ubuntu, macOS, and Windows.
- Validate that the base wheel does not install local/Strands dependencies.
- Validate the optional local extra independently.

### Product-native tests

- Normal authenticated Claude Code CLI loads both hooks and records a native
  event.
- Normal authenticated Codex CLI trusts and loads both hooks and records a
  native event.
- Claude Code Desktop local session loads the repository treatment.
- Codex desktop local session loads the repository treatment.
- General Claude and ChatGPT chats are not represented as supported hook
  clients.
- Managed-policy denial is reported rather than bypassed.

Authenticated tests use existing personal plans, are run once per condition,
and are excluded from public CI because they spend subscription tokens.

### Local runtime tests

- Native macOS endpoint smoke test.
- Linux/5090 native or direct llama.cpp endpoint smoke test.
- Optional NVIDIA Docker reproducibility smoke test.
- One bounded Qwen task with real ledger evidence.
- Muse is run only when the installed model/runtime can be identified and its
  use is permitted; otherwise it remains explicitly unqualified.

## Independent review and publication gates

After implementation and all available tests:

1. Run an independent read-only review with the normal authenticated
   `claude --model fable` route.
2. Capture and report the resolved model ID. The design review resolved to
   `claude-fable-5-1` with no API-key source.
3. Fix every confirmed correctness, portability, rollback, or documentation
   finding, then rerun affected tests.
4. Review the final diff and evidence once more.
5. Publish only if the worktree is intentional, deterministic tests pass,
   package installation passes, native treatment delivery is evidenced, and
   unsupported paths are clearly labeled.

Publishing means updating the public GitHub repository, release artifacts, and
companion Site only after these gates. No release or deployment occurs during
implementation merely because unit tests pass.
