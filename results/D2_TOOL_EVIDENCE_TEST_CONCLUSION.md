# D2 Tool Design Evidence

This file is the repository evidence for D2(a)-D2(c). The deterministic
baseline below was generated on the 40 core cases, three isolated trials per
case. Live-model results must be generated with the same script before final
submission; they are not fabricated when an API key is unavailable.

## D2(a) Tool necessity and prompt cost

The cost column is the v2 descriptor's serialized character count divided by
four. It estimates tokens retransmitted in the system prompt on every model
call even when the tool is never called. Live runs also record provider token
usage.

| Exposed tool | Does the task fail without it? | Could the model confuse it? | Never-called prefix cost (estimated tokens/model call) | Decision |
|---|---|---:|---:|---|
| `get_referral` | Yes: it is the authoritative case, patient, specialty, and test source. | Medium: referral id can be confused with patient id. | 234 | Keep; must run first and alone. |
| `check_referral_criteria` | Yes: deterministic red flags, department fit, required tests, urgency, and legal window would be lost. | High: urgency is not a red flag and missing tests require exact codes. | 460 | Keep; returns facts, never the final decision. |
| `lookup_patient` | Yes: future same-specialty duplicates and contact evidence would be lost. | High: past and other-specialty appointments are not duplicates. | 256 | Keep; can batch with criteria after referral. |
| `get_clinic_slots` | Yes: availability, band, window, capacity, and earliest slot cannot be invented. | High: band and window widening are unsafe. | 531 | Keep; bounded to 20 results and exact assessed constraints. |
| `book_slot` | Yes: a `book` decision needs a gated, auditable state change. | High: model text must not count as approval or evidence. | 661 | Keep; call last and alone through the controller gate. |

`get_system_date` was evaluated and removed from the exposed tool set. No
authored run called it, and `check_referral_criteria` already returns the
trusted window derived from the fixed fixture clock. Removing it saves about
145 estimated prompt tokens per model call without losing a required fact.

Every retained descriptor in `tools/registry.py` contains, without exception:

- name and typed signature;
- what the tool does and when it is safe to use;
- every input's type, required/default status, constraints, and bad-value behaviour;
- the successful return shape and an explicit size bound;
- named failure conditions; and
- irreversible yes/no plus the gate when the answer is yes.

`tests/test_tool_descriptors.py` checks descriptor completeness, argument/name
alignment with the Python functions, JSON serializability, size bounds, and
the actual v1/v2 return-shape difference.

## Poka-yoke moves

| Move | Before | After | Error made impossible or fail-closed | Evidence |
|---|---|---|---|---|
| Slot search contract | v1 says only to find slots and returns `result + slots`. | v2 requires the exact specialty, assessed urgency band, legal ISO window, and limit 1-20; the return echoes `requested_window` and contains only sorted positive-capacity slots. | An out-of-range limit, unknown band, or widened/invalid window cannot silently return a plausible slot; it produces a named error. | `test_slot_v1_and_v2_return_shapes_are_really_different`, `test_invalid_or_extended_window_is_rejected`, and `test_slots_filter_band_capacity_window_and_limit`. |
| Booking authorization | A weak interface could accept model-supplied `confirmed=true` or a booking unsupported by observations. | Public arguments contain only booking facts. Hidden `_state` and `_call_id` come from the controller; the gate requires matching referral, criteria, patient and slot evidence plus autonomy/confirmation. | The model cannot approve itself, add safety flags, book an unobserved slot, or bypass the evidence gate. | `test_model_cannot_supply_safety_or_confirmation_flags`, `test_book_slot_executes_only_through_authorized_call_tool`, and `test_final_booking_without_booking_evidence_is_rejected`. |

## D2(b) Descriptor and return-shape comparison

The controlled variable is `get_clinic_slots`:

- v1: short descriptor; successful data is `{result, slots}`.
- v2: tight descriptor; successful data is
  `{result, requested_window, slots}`, with argument behaviour and size bounds
  stated explicitly.
- Both use the same underlying fixtures, validation, cases, call mode, and
  deterministic authored decisions.

| Variant | Runs | Eval pass | Negative guardrail pass | Prompt tokens/call (estimated) | Mean tool-return tokens/call (estimated) |
|---|---:|---:|---:|---:|---:|
| v1 descriptor + v1 return, batched | 120 | 120/120 (100%) | 30/30 (100%) | 2,736 | 66.7709 |
| v2 descriptor + v2 return, batched | 120 | 120/120 (100%) | 30/30 (100%) | 2,887 | 69.4078 |

For `get_clinic_slots` alone, the observed mean return estimate changes from
57.3226 tokens in v1 to 72.5484 tokens in v2. The deterministic baseline shows
that the stricter contract preserves correctness while making the requested
window auditable, at a cost of about 151 prompt tokens per model call and 15.2
slot-observation tokens per slot call. These are character/4 estimates, not
provider-token claims.

## D2(c) Same-turn batching comparison

Dependency rule: a call may share a model turn only when all of its
prerequisites were completed in earlier turns. Therefore `get_referral` runs
alone; `check_referral_criteria` and `lookup_patient` may batch; slot search
waits for both; and irreversible `book_slot` runs last and alone. The guardrail
rejects dependent calls placed in the same turn.

The project's `parallel` label means logical same-turn batching. Read tools are
executed deterministically one after another inside that turn; no wall-clock
concurrency claim is made.

| v2 mode | Runs | Eval pass | Negative guardrail pass | Mean tool turns | Mean model iterations | Mean retransmitted prompt tokens (estimated) |
|---|---:|---:|---:|---:|---:|---:|
| Sequential | 120 | 120/120 (100%) | 30/30 (100%) | 4.475 | 5.425 | 15,661.975 |
| Same-turn batched | 120 | 120/120 (100%) | 30/30 (100%) | 3.525 | 4.475 | 12,919.325 |

Correctness is identical in the scripted control. Batching saves 0.95 tool
turns and 0.95 model iterations per run on average, reducing estimated prompt
retransmission by about 17.5%. Scripted cost is $0 because it uses no provider;
live cost is recorded from OpenRouter usage when available.

## Reproduction

```bash
python -m unittest discover -s tests -v
python experiments/run_d2_experiments.py
```

The experiment writes:

- `results/d2_experiment_summary.csv` - report-ready aggregate table;
- `results/d2_experiment_tool_returns.csv` - return tokens per tool and variant;
- `results/d2_experiment_runs.json` - compact per-run audit records.

For a controlled live run, keep temperature at zero and provide one fixed
model. The evaluator supplies trusted approval only for the simulated booking
gate:

```bash
export OPENROUTER_API_KEY="..."
python experiments/run_d2_experiments.py --backend live --model PROVIDER/MODEL
```

Repeat `--model` for the three-model D5 battery. Do not commit the API key.
