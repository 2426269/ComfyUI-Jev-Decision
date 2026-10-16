# Semantic Judge Rewrite Implementation Plan

> **For agentic workers:** Execute task-by-task with tests first. Read AGENTS.md, STATUS.md, DESIGN.md, ACCEPTANCE.md and DEC-004 before changing code. The previous P0 implementation is frozen; do not preserve its public node graph at the cost of the new contract.

**Goal:** Replace the experimental four-node Noul workflow with one ComfyUI V3 `JevSemanticJudge` node supporting Noul, Choice and Score with fixed BOOLEAN/FLOAT/INT/STRING/details_json outputs.

**Architecture:** A pure semantic layer parses options, builds one Jev question, validates the typed answer and maps it to five outputs. A thin backend interface wraps the existing TypeSafe transport. A bounded content-addressed LRU caches only validated backend responses. The ComfyUI node is a schema and execution adapter over these pure pieces.

**Tech Stack:** Python 3.12, standard-library unittest, aiohttp, ComfyUI 0.34.0, `comfy_api.v0_0_2` V3 API.

## Global constraints

- Do not call TypeSafe from automated tests.
- Do not read or copy `local-runtime/.env.local` into code, fixtures, logs or manifests.
- Keep only TypeSafe as a runtime backend; fake backends are test dependencies, not UI choices.
- Do not add Router, action, graph-inspection, resource-loader or local-model nodes.
- Preserve the archive in `records/artifacts` byte-for-byte.
- New public behavior must map to ACCEPTANCE SJ01–SJ18.

### Task 1: Pure options and output contract

**Files:**
- Modify: `plugin/ComfyUI-Jev-Decision/decision_protocol.py`
- Replace: `plugin/ComfyUI-Jev-Decision/tests/test_protocol.py`

- [x] Write failing tests for SJ02–SJ08: options grammar, limits, Unicode/order, Noul boundaries, Choice confidence/index mapping, Score normalization/half-up mapping and details_json redaction.
- [x] Run `python -m unittest tests.test_protocol -v` and record the expected failures.
- [x] Implement immutable request/options/result values and exact v1 mappings from DESIGN sections 3–5.
- [x] Re-run the focused suite; all cases must pass without importing ComfyUI.

### Task 2: Backend abstraction and bounded LRU

**Files:**
- Create: `plugin/ComfyUI-Jev-Decision/backend.py`
- Modify: `plugin/ComfyUI-Jev-Decision/provider.py`
- Replace: `plugin/ComfyUI-Jev-Decision/tests/test_provider.py`

- [x] Write failing async tests for SJ09–SJ13, including call counts, threshold exclusion, refresh changes, error non-caching, capacity eviction and concurrent identical requests.
- [x] Define a small backend protocol returning validated provider/model/answer/usage metadata.
- [x] Adapt the existing aiohttp TypeSafe transport; retain timeout, redirect, credential and error behavior.
- [x] Implement a lock-protected LRU with capacity 256. Cache only successful validated backend responses; keep threshold outside the key and refresh inside it.
- [x] Re-run focused tests and confirm no network access.

### Task 3: Single ComfyUI V3 node

**Files:**
- Replace: `plugin/ComfyUI-Jev-Decision/decision_nodes.py`
- Modify: `plugin/ComfyUI-Jev-Decision/__init__.py`
- Replace: `plugin/ComfyUI-Jev-Decision/tests/test_nodes.py`

- [x] Write schema tests asserting only `JevSemanticJudge` is registered and all five output positions/types remain fixed for every mode.
- [x] Implement inputs exactly as DESIGN 3.1 and outputs exactly as DESIGN 4.
- [x] Keep execution thin: validate → cache/backend → strict response → local mapping → NodeOutput.
- [x] Remove old node classes from the entrypoint. Do not leave two public product models registered.
- [x] Run node tests under `PYTHONPATH=E:\comfyui\ComfyUI-NAI`.

### Task 4: Real ComfyUI executor and cache proof

**Files:**
- Replace: `plugin/ComfyUI-Jev-Decision/tests/test_comfy_execution.py`
- Create: `plugin/ComfyUI-Jev-Decision/examples/semantic-judge-noul.api.json`
- Create: `plugin/ComfyUI-Jev-Decision/examples/semantic-judge-choice.api.json`
- Create: `plugin/ComfyUI-Jev-Decision/examples/semantic-judge-score.api.json`

- [x] Execute all three modes through real `validate_prompt` and `PromptExecutor` with an injected fake backend.
- [x] Prove identical evaluation calls once, threshold-only changes reuse the backend response, and refresh changes call again.
- [x] Verify all five outputs are consumable through simple registered sink nodes.
- [x] Validate all example API JSON files and confirm no credentials or machine secrets are embedded.

### Task 5: Migration and documentation

**Files:**
- Rewrite: `plugin/ComfyUI-Jev-Decision/README.md`
- Modify: `README.md`, `STATUS.md`, `AGENTS.md`, `examples/README.md`
- Append: `TASK_LOG.md`, `DECISIONS.md` only if implementation changes the accepted design

- [x] Mark old node IDs removed and provide a concise manual migration from old Noul graph to one Semantic Judge.
- [x] Document the mode/output matrix beside every workflow example.
- [x] Identify locally installed BOOLEAN/FLOAT/INT/STRING consumers and validate only combinations that exist; record exact class_type values.
- [x] Do not add compatibility nodes to compensate for missing community consumers.

### Task 6: Final validation and optional live smoke

**Files:**
- Modify or replace: `tools/real_smoke.py`
- Create: `records/SJ-P0-<date>-validation.json`
- Update: `manifest.json` after preserving the previous manifest

- [x] Run the full unittest suite, compileall, JSON parsing, Markdown link check, secret scan, registration probe and manifest self-check.
- [x] Run frontend save/restore verification if an interactive browser session is available; otherwise mark SJ15 unverified. (No browser run; recorded unverified.)
- [x] With existing user authorization and local credential, make at most one minimal new-node Noul smoke request, with no automatic retry. Choice/Score live tests remain optional.
- [x] Record exact request count, actual model, usage and latency without prompt or credential text.
- [x] Mark SJ-P0 complete only when ACCEPTANCE permits it; keep semantic accuracy explicitly separate.

## Expected public migration

```text
Old: Ask Noul → Evaluate Text → Read Noul / Inspect Result
New: Runtime STRING → Semantic Judge → BOOLEAN/FLOAT/INT/STRING/details_json
```

No automatic workflow rewrite is planned because the old nodes were an unpublished experiment.
