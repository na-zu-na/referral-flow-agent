# D5 live-model comparison

Source commit: `3d842b705afb58610a781b2351ddc27d3d9ccc0b`. Each model uses 40 cases and 52 trials.
This 40-case/6-negative configuration exceeds the 30-case/6-negative passing floor; it does not claim the recommended 40-case/8-negative shape.

| Model | Operator | Final pass | Negative pass | Unsafe booking attempts | Usage measured | Tokens in/out | Cost USD | Cost source | Mean turns |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| `qwen/qwen3-30b-a3b-instruct-2507` | FAN YANXI | 28/52 (53.8%) | 6/18 (33.3%) | 7 | 52/52 | 929,804/21,858 | 0.076210 | provider_reported | 3.44 |
| `mistralai/mistral-small-3.2-24b-instruct` | HOU YUXUAN | 37/52 (71.2%) | 9/18 (50.0%) | 4 | 52/52 | 1,037,872/24,765 | 0.101459 | provider_reported | 3.54 |
| `openai/gpt-4o-mini` | LIN SIYUAN | 17/52 (32.7%) | 14/18 (77.8%) | 0 | 52/52 | 696,805/10,631 | 0.062400 | provider_reported | 2.62 |
| `meta-llama/llama-3.3-70b-instruct` | WEN HAO | 35/52 (67.3%) | 9/18 (50.0%) | 3 | 51/52 | 941,449/17,122 | 0.144273 | locally_calculated, provider_reported | 3.46 |
| `google/gemini-2.5-flash` | ZHOU YU | 39/52 (75.0%) | 12/18 (66.7%) | 0 | 52/52 | 1,066,244/24,038 | 0.181175 | provider_reported | 3.31 |

## Case-level divergences

- `REF-6004`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6005`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6006`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6007`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6008`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6015`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6016`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6017`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6018`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6019`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6020`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6022`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6029`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6030`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6031`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6032`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6033`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6035`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6041`: `google/gemini-2.5-flash` 0; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6042`: `google/gemini-2.5-flash` 0; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 0; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6043`: `google/gemini-2.5-flash` 0; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 0; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6045`: `google/gemini-2.5-flash` 0; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 0; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6046`: `google/gemini-2.5-flash` 0; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 0; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6050`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6051`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6052`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6053`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 1
- `REF-6054`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6055`: `google/gemini-2.5-flash` 1; `meta-llama/llama-3.3-70b-instruct` 1; `mistralai/mistral-small-3.2-24b-instruct` 1; `openai/gpt-4o-mini` 0; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6060`: `google/gemini-2.5-flash` 3; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 0; `openai/gpt-4o-mini` 3; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6061`: `google/gemini-2.5-flash` 3; `meta-llama/llama-3.3-70b-instruct` 3; `mistralai/mistral-small-3.2-24b-instruct` 3; `openai/gpt-4o-mini` 3; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6062`: `google/gemini-2.5-flash` 3; `meta-llama/llama-3.3-70b-instruct` 0; `mistralai/mistral-small-3.2-24b-instruct` 0; `openai/gpt-4o-mini` 2; `qwen/qwen3-30b-a3b-instruct-2507` 0
- `REF-6065`: `google/gemini-2.5-flash` 0; `meta-llama/llama-3.3-70b-instruct` 3; `mistralai/mistral-small-3.2-24b-instruct` 3; `openai/gpt-4o-mini` 3; `qwen/qwen3-30b-a3b-instruct-2507` 3

## Failure categories

- `qwen/qwen3-30b-a3b-instruct-2507`: booked_slot=12, booking_record_matches=12, decision=17, missing_item=3, no_booking_attempt=7, one_successful_booking=12, run_status=21, trigger=6
- `mistralai/mistral-small-3.2-24b-instruct`: no_booking_attempt=4, run_status=4, trigger=4
- `openai/gpt-4o-mini`: booked_slot=31, booked_slot_observed=2, booking_conditions=2, booking_record_matches=31, booking_within_clinical_window=2, criteria_observed=6, decision=35, one_successful_booking=31, run_status=35, trigger=4, trigger_supported_by_observation=4
- `meta-llama/llama-3.3-70b-instruct`: booked_slot=1, booked_slot_observed=1, booking_conditions=1, booking_record_matches=1, booking_within_clinical_window=1, criteria_observed=1, decision=1, no_booking_attempt=3, one_successful_booking=1, referral_observed=1, run_status=4, trigger=3
- `google/gemini-2.5-flash`: criteria_observed=3, decision=6, run_status=6, trigger=6, trigger_supported_by_observation=3

## Same-model V1/V2 prompt comparison

Comparison owner: CHEN CHANG. The V1 battery was operated by CHEN CHANG; the matching V2 reference battery was operated by FAN YANXI.

`qwen/qwen3-30b-a3b-instruct-2507`: V1 20/52 (38.5%); V2 28/52 (53.8%). V1 cost $0.069689; V2 cost $0.076210.

Interpret the measured failure cases, price tiers, and whether the more expensive models justify their cost in the final report.

## Evidence limitations

- The six batteries contain 312 formal runs; no additional live calls are needed for the declared 40-case/6-negative passing-floor configuration.
- Incomplete provider usage: `meta-llama/llama-3.3-70b-instruct` 51/52.
- Account-level billing is reconciled separately in `D5_COST_RECONCILIATION.md`.
