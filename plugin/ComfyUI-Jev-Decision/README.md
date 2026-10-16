# ComfyUI Semantic Judge

Turn semantic uncertainty into native ComfyUI signals.

This nodepack exposes one ComfyUI V3 node, `Semantic Judge`. It evaluates one runtime JSON-compatible state with TypeSafe Jev in Noul, Choice or Score mode and always returns five fixed outputs:

> **Before use:** a TypeSafe API key is required. The connected `context` and the full `instructions` are sent to TypeSafe's cloud API, requests may incur charges, and a missing key or provider error stops the workflow instead of returning `false`.

1. `BOOLEAN decision`
2. `FLOAT value`
3. `INT index`
4. `STRING label`
5. `STRING details_json`

It does not load models or LoRAs, modify prompts, inspect the graph, or route arbitrary ComfyUI objects. Connect its native outputs to the control nodes already used by your workflow.

## Inputs

- **context**: one required multitype socket accepting `STRING`, `DICT`, `ARRAY`, `BOOLEAN`, `INT`, or `FLOAT`.
- **instructions**: one complete judgment instruction.
- **mode**: `Noul`, `Choice`, or `Score`.
- **options**: Choice/Score only, one ordered option per line.
- **threshold**: local BOOLEAN threshold from 0 to 1.
- **model**: defaults to `jev-latest`.
- **connection_profile**: selects an environment variable credential.
- **refresh**: cache-key namespace salt. Change to a value not used with the same semantic inputs to request a fresh evaluation; changing back may reuse the older cached response.

Options use:

```text
stable_id | optional description
```

Choice accepts 2–255 options. Score accepts 2–10 ordered levels. Noul requires an empty options field.

STRING is trimmed and sent as text. DICT and ARRAY are copied, validated as finite JSON, and sent as native structured state. BOOLEAN, INT, and FLOAT are wrapped as `{"value": value}`. Empty states, non-string object keys, cycles, non-finite numbers, IMAGE, LATENT, MODEL, VAE, tensors, and arbitrary Python objects fail before any provider request. Convert resource objects to descriptions or JSON metadata upstream. Use ordinary ComfyUI logic for deterministic checks; scalar support exists so a value can participate in a larger semantic context without adding adapter-specific judge nodes.

## Output meanings

| mode | BOOLEAN | FLOAT | INT | STRING |
| --- | --- | --- | --- | --- |
| Noul | probability >= threshold | probability of true | 0 or 1 | `false` or `true` |
| Choice | confidence >= threshold | API confidence | selected 0-based index | selected stable ID |
| Score | normalized score >= threshold | score divided by max level | nearest level index | nearest level ID |

`details_json` preserves the complete validated answer, distributions, actual model, usage, timing and cache status. It stores SHA-256 fingerprints instead of the context and instructions text.

Choice `confidence` is a provider field distinct from the selected option's probability. It is not documented here as accuracy or as the winning probability. The complete probabilities and confidence are both available in `details_json`; conservative downstream policies may inspect both.

Changing only threshold reuses the validated backend response. `refresh` participates in the cache key; it does not delete prior entries. The in-memory cache currently has no TTL and is cleared when ComfyUI restarts. For a production workflow, prefer a pinned model ID over `jev-latest`, and increase refresh when a new evaluation is required.

## Credentials

The default profile reads:

```text
TYPESAFE_API_KEY
```

A profile such as `work-station` reads `TYPESAFE_API_KEY_WORK_STATION`. API keys never enter node inputs or workflow JSON.

The node sends `context`, `instructions`, mode-specific criteria, and the requested model to TypeSafe. A request adds roughly one network round trip to the execution path; observed project smoke/evaluation requests were commonly about 0.8–1.4 seconds, but this is not a latency guarantee. Put the judge before expensive branches and rely on a downstream lazy selector when the unselected branch must not execute. Keep deterministic checks outside the cloud call.

There are no automatic retries or built-in batch rate limiter. A 429, timeout, or provider error stops the node. Once an HTTP request has been sent, cancelling the ComfyUI queue may not cancel the shared background request, so it may still finish and consume provider credit.

The local development project provides:

```text
E:\comfyui\Jev-Decision-Design\local-runtime\run_comfyui_with_jev.cmd
```

It loads the ignored local credential file only into the launched ComfyUI process.

## Examples

- `examples/semantic-judge-noul.api.json`
- `examples/semantic-judge-choice.api.json`
- `examples/semantic-judge-score.api.json`
- `examples/semantic-judge-multitype.api.json`
- `examples/semantic-judge-multitype.workflow.json`
- `examples/semantic-judge-interop.api.json`
- `examples/semantic-judge-interop.workflow.json`
- `examples/prompt-preservation-tristate.api.json`
- `examples/prompt-preservation-tristate.workflow.json`

The first three API examples use bundled `PreviewAny` nodes to show all five outputs. The multitype pair demonstrates a bundled BOOLEAN primitive connected to the same context socket; it is a connection/serialization example rather than a reason to replace deterministic boolean logic with a model call. The interop pair connects BOOLEAN, FLOAT, INT, label and details_json to the locally installed easy-use condition, comparison, index and display nodes. The tri-state recipe combines independent original/candidate STRING inputs with the bundled `StringConcatenate` node, then labels `p >= 0.80` as adopt, `0.50 <= p < 0.80` as review and `p < 0.50` as reject. Its automatic output uses the candidate only for adopt; review and reject fall back to the original. These are demonstration thresholds, not production calibration. Queuing any example that contains `JevSemanticJudge` requires a configured TypeSafe key.

## Migration from the archived probe

The experimental IDs `JevDecisionAskNoul`, `JevDecisionEvaluateText`, `JevDecisionReadNoul`, and `JevDecisionInspectResult` have been removed from registration. Replace the old chain manually:

```text
Old: Ask Noul -> Evaluate Text -> Read Noul / Inspect Result
New: JSON-compatible runtime state -> JevSemanticJudge -> native outputs / PreviewAny
```

Copy the old question instruction into `instructions`, connect the previous runtime state to `context`, select `Noul`, and leave `options` empty. No compatibility aliases are registered because the old graph was an unpublished experiment.

## Development validation

Tested development environment:

- ComfyUI 0.34.0 at `E:\comfyui\ComfyUI-NAI`
- Python 3.12.10
- `comfy_api.v0_0_2`
- aiohttp 3.14.3
- CPU torch 2.13.0

Run the automated suite:

```powershell
Set-Location -LiteralPath 'E:\comfyui\Jev-Decision-Design\plugin\ComfyUI-Jev-Decision'
$env:PYTHONPATH = 'E:\comfyui\ComfyUI-NAI'
& 'E:\comfyui\ComfyUI-NAI\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

Automated tests inject fake responses and make no paid request. Live smoke tests are separate and must never print or persist the API key.

The suite currently contains 47 tests. It executes STRING, DICT, ARRAY and scalar contexts through the real `PromptExecutor`. Its easy-use integration tests load the actual local node classes, assert that `easy ifElse` does not execute an unselected lazy branch, and exercise adopt/review/reject routing with safe fallback.
