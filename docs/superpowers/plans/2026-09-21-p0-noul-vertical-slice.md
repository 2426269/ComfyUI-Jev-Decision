# P0 Noul Vertical Slice Implementation Plan

> **Superseded baseline:** This plan was completed and frozen as the four-node P0 probe. DEC-004 replaces its public architecture with the single-node Semantic Judge design. Preserve it as implementation evidence; do not continue its later-node expansion.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. In this session the user already requested inline execution; those sub-skills are not installed, so the primary agent executes the same test-first steps directly and records evidence in `TASK_LOG.md`.

**Goal:** Deliver a locally runnable ComfyUI V3 nodepack that can define one or more Noul questions, call TypeSafe through an injectable transport, preserve a validated result, read a Noul probability, and display the result.

**Architecture:** Pure protocol values and validators live outside ComfyUI. The provider module owns the only network path. V3 nodes are thin wrappers over those modules and use custom socket types. Tests first exercise the pure layer, then load the nodepack against the user's real ComfyUI executor with a mocked provider.

**Tech Stack:** Python 3.12, standard-library `unittest`, `aiohttp`, ComfyUI 0.34.0, `comfy_api.v0_0_2` V3 API.

## Global Constraints

- Work under `E:\comfyui\Jev-Decision-Design`; use `E:\comfyui\ComfyUI-NAI` only as the authorized local compatibility environment.
- Keep Context/Choice/Score/Range/Lazy Select/batch outside this vertical slice.
- Evaluate performs no thresholding or routing.
- API credentials come from environment profiles and never enter workflow inputs or logs.
- No real paid request is required for acceptance; mock transport and the real ComfyUI executor are required.
- Preserve all unrelated changes already present in `E:\comfyui\ComfyUI-NAI`.
- Use `comfy_api.v0_0_2`, immutable content-based protocol wrappers, and no mutable node instance state.

---

### Task 1: Nodepack skeleton and protocol tests

**Files:**
- Create: `plugin/ComfyUI-Jev-Decision/pyproject.toml`
- Create: `plugin/ComfyUI-Jev-Decision/__init__.py`
- Create: `plugin/ComfyUI-Jev-Decision/decision_protocol.py`
- Create: `plugin/ComfyUI-Jev-Decision/tests/test_protocol.py`

**Interfaces:**
- Produces: frozen `QuestionsValue(json_text: str)` and `ResultValue(json_text: str)`; `add_noul_question(...)`; `validate_questions_document(...)`; `build_result(...)`; `read_noul(...)`; `strict_loads(...)`; `canonical_dumps(...)`.

- [x] **Step 1: Write failing protocol tests**

Cover duplicate JSON keys, question ID duplication, partial Noul criteria, immutability-by-copy, invalid/extra/missing answers, probability bounds, and Unicode/newline canonical round trip.

- [x] **Step 2: Run the focused tests and observe missing-module failure**

Run from the plugin directory:

```powershell
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' -m unittest tests.test_protocol -v
```

Expected before implementation: import or symbol failure. Expected after implementation: all tests pass.

- [x] **Step 3: Implement strict immutable protocol values**

Use canonical JSON strings as the stored payload. Parse on access, reject duplicate keys and non-finite constants, require exact v1 envelopes, and never expose a mutable internal object. The module is named `decision_protocol.py` so it cannot shadow ComfyUI core's top-level `protocol` module when the nodepack directory is on `sys.path`.

- [x] **Step 4: Re-run tests**

Expected: exit code 0 and every `test_protocol` case reports `ok`.

### Task 2: TypeSafe provider boundary

**Files:**
- Create: `plugin/ComfyUI-Jev-Decision/provider.py`
- Create: `plugin/ComfyUI-Jev-Decision/tests/test_provider.py`

**Interfaces:**
- Consumes: plain JSON-compatible state and validated questions map.
- Produces: `async evaluate(state, questions, model, connection_profile) -> dict`.

- [x] **Step 1: Write async tests**

Use `unittest.IsolatedAsyncioTestCase` and mock the internal request helper. Verify profile-to-environment-name mapping, empty credentials, payload shape, timeout/error classification, no redirects, and that error strings never contain keys.

- [x] **Step 2: Run and observe failure**

```powershell
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' -m unittest tests.test_provider -v
```

- [x] **Step 3: Implement the single outbound path**

Use `aiohttp.ClientSession` with a 60-second total timeout and `allow_redirects=False`. Support `default -> TYPESAFE_API_KEY` and validated named profiles -> `TYPESAFE_API_KEY_<PROFILE>`. Do not automatically retry ambiguous timeouts.

- [x] **Step 4: Re-run tests**

Expected: exit code 0.

### Task 3: V3 nodes for the Noul path

**Files:**
- Create: `plugin/ComfyUI-Jev-Decision/decision_nodes.py`
- Create: `plugin/ComfyUI-Jev-Decision/tests/test_nodes.py`
- Modify: `plugin/ComfyUI-Jev-Decision/__init__.py`

**Interfaces:**
- Produces node IDs `JevDecisionAskNoul`, `JevDecisionEvaluateText`, `JevDecisionReadNoul`, `JevDecisionInspectResult`.
- Custom sockets: `JEV_QUESTIONS` and `JEV_RESULT`.

- [x] **Step 1: Write node-level tests**

Validate each schema, append two Noul questions, patch `provider.evaluate`, assert one request and exact state/questions, read the probability as FLOAT, and assert Inspect returns PreviewText UI data.

- [x] **Step 2: Run and observe failure**

```powershell
$env:PYTHONPATH='E:\comfyui\ComfyUI-NAI'
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' -m unittest tests.test_nodes -v
```

- [x] **Step 3: Implement thin V3 node wrappers**

Ask Noul accepts optional existing Questions. Evaluate accepts text, Questions, model, connection profile and refresh; it validates before and after the provider. Read Noul returns a float. Inspect is an output node and returns `ui.PreviewText` without changing the result.

Keep root Python module names distinct from ComfyUI's top-level `nodes` and `protocol` modules. Use `decision_nodes.py` and `decision_protocol.py`; the real ComfyUI import path is part of acceptance.

- [x] **Step 4: Run node tests**

Expected: exit code 0.

### Task 4: Real ComfyUI executor integration

**Files:**
- Create: `plugin/ComfyUI-Jev-Decision/tests/test_comfy_execution.py`

**Interfaces:**
- Consumes the registered V3 nodes through ComfyUI's `validate_prompt` and `PromptExecutor`.
- Produces evidence for ACCEPTANCE P06, P08, P10 and the cache-count portion of section 3.

- [x] **Step 1: Write an executable API graph test**

Register the extension classes in `nodes.NODE_CLASS_MAPPINGS`, patch the provider, execute Ask Noul → Evaluate → Read Noul → Inspect, and assert success plus probability `0.8`.

- [x] **Step 2: Add cache count test**

Execute the same graph twice, then change only the Inspect-side formatting input if present. Assert provider count remains one; change Evaluate refresh and assert it becomes two.

- [x] **Step 3: Run integration tests**

```powershell
$env:PYTHONPATH='E:\comfyui\ComfyUI-NAI'
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' -m unittest tests.test_comfy_execution -v
```

Expected: graph validation and execution succeed with the CPU environment; no external request occurs.

### Task 5: Documentation, local install, and registration probe

**Files:**
- Create: `plugin/ComfyUI-Jev-Decision/README.md`
- Create: `plugin/ComfyUI-Jev-Decision/examples/noul-preservation.api.json`
- Modify: `README.md`
- Modify: `STATUS.md`
- Append: `TASK_LOG.md`
- Update: `manifest.json` after preserving its prior version under `records/`

**Interfaces:**
- Produces a user-readable setup path, an API workflow fixture, and auditable evidence.

- [x] **Step 1: Document the exact supported slice and environment variables**

State that this is an experimental P0 slice, list missing nodes explicitly, and avoid calling mock results real Jev output.

- [x] **Step 2: Run the complete local suite**

```powershell
$env:PYTHONPATH='E:\comfyui\ComfyUI-NAI'
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

- [x] **Step 3: Link the plugin into the authorized ComfyUI custom_nodes folder**

Create a directory junction only if the destination does not exist, from `E:\comfyui\ComfyUI-NAI\custom_nodes\ComfyUI-Jev-Decision` to the plugin directory. Do not restart a running server automatically.

- [x] **Step 4: Probe extension registration without a real API call**

Load the entrypoint using the ComfyUI Python environment and assert the four node IDs are present and schemas validate.

- [x] **Step 5: Record evidence and refresh the manifest**

Append CHECKPOINT and END with exact commands, exit codes and limits. Mark this slice complete only if all checks pass; keep the overall plugin status partial.

## Self-review

- Spec coverage: this plan covers only the approved first vertical slice, with explicit later-phase omissions. Every deliverable maps to DESIGN and ACCEPTANCE items named in the task log.
- Placeholder scan: no implementation step depends on TBD behavior. Later phases are declared out of scope rather than placeholders.
- Type consistency: QuestionsValue flows Ask Noul → Evaluate; ResultValue flows Evaluate → Read/Inspect; provider returns a plain response that `build_result` validates.
