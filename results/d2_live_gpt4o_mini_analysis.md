# D2 Live OpenRouter Analysis

Run date: 2026-09-16  
Model: `openai/gpt-4o-mini`  
Temperature: `0.0`  
Scope: 40 core cases x 3 trials x 3 controlled variants = 360 runs

## Measured results

| Variant | Runs | Eval pass | Negative guardrail pass | Mean input tokens | Mean output tokens | Mean cost/run |
|---|---:|---:|---:|---:|---:|---:|
| v1 descriptor + v1 return, batched | 120 | 32/120 (26.67%) | 27/30 (90.00%) | 10,547.03 | 200.58 | $0.00097408 |
| v2 descriptor + v2 return, batched | 120 | 23/120 (19.17%) | 21/30 (70.00%) | 9,783.84 | 186.72 | $0.00091409 |
| v2 descriptor + v2 return, sequential | 120 | 30/120 (25.00%) | 19/30 (63.33%) | 10,417.40 | 205.42 | $0.00097138 |

All provider token fields were measured. The battery used 3,689,793 input
tokens and 71,126 output tokens, costing $0.343146 in total.

## Failure distribution

Across all variants, statuses were:

- 76 completed;
- 151 guardrail-stopped; and
- 133 invalid model outputs.

Some hostile-input guardrail stops are correct passes, so status alone is not
the evaluation grade.

Observed failure mechanisms:

- 106 runs returned a `book` final without first obtaining a successful
  `book_slot` observation.
- 132 runs called `get_clinic_slots` before successful `lookup_patient`
  evidence existed; the deterministic dependency guardrail stopped them.
- 19 model moves contained an empty `calls` array.
- Six model moves used an invalid move type.
- Two runs claimed a duplicate future appointment without supporting evidence.
- Nine completed but incorrect runs were all `REF-5671`: the model requested
  the missing test instead of applying the earlier specialty-mismatch stop.

## Interpretation

This model/run does not support a claim that the v2 descriptor improved pass
rate. The scripted 100% result proves deterministic fixture, tool, guardrail,
and grader consistency; it does not predict live model loop-control quality.
The live failures must be reported as evidence and used for the required
failure analysis rather than hidden or replaced.

Raw and aggregate evidence:

- `d2_live_gpt4o_mini_summary.csv`
- `d2_live_gpt4o_mini_tool_returns.csv`
- `d2_live_gpt4o_mini_runs.json`
- `live_smoke_REF5614.json`
