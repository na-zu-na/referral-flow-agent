# D7 Two Reproduced Failures

Run both failures and regenerate the submitted tables with:

```bash
python3 -m experiments.d7_failures
```

Run the dedicated checks with:

```bash
python3 -m unittest tests.test_d7_failures -v
```

## Experimental contract

Both experiments use the submitted single-agent controller, real tools, real
guardrails, and deterministic Agent moves. They require no network or API key.
Each failure changes one component only.

### Failure 1 Loop control

The failure injection clears `GuardrailState.seen_actions` immediately before
each turn. This is equivalent to deleting persistent action de-duplication from
the working Agent. The backend then repeats `get_referral("REF-5602")` with new
call IDs. The broken version can only be stopped by the step cap; restoring
de-duplication stops the second logically identical action.

The script first measures the 40-case core set. It sets the recommended cap to
one turn above the worst legitimate run, rather than choosing a round number.
The same core set is also run with de-duplication deleted to show that restoring
the guard does not reduce ordinary-case pass rate.

### Failure 2 Prompt dependency ordering

The experiment deletes exactly one sentence from the working v2 system prompt:
dependent calls must wait for successful prerequisite observations from earlier
turns. The same prompt-aware deterministic backend then batches
`get_clinic_slots` with `check_referral_criteria` and `lookup_patient`. The real
guardrail stops this unsafe move with `DEPENDENCY_VIOLATION`. Restoring the
sentence makes the same backend wait and recover the correct
`no_slot_in_window` escalation for `REF-5697`.

This belongs at the prompt layer because the missing instruction controls model
planning order. The tool interface is unchanged and already defines each call;
loop control limits repetition and resource use but does not teach the model
which evidence must exist before a dependent call.

The case, descriptor version, backend implementation, controller, tools,
guardrails, call mode, and cap are held constant. The generated JSON records the
prompt character delta and these controls.

## Outputs

- `results/d7_failure_results.json`: before/after metrics and method.
- `results/d7_turn_distribution.csv`: per-case turns, tokens, cost, pass and cap status.
- `doc/D7_REPORT_SECTION.md`: report-ready English draft.
- `doc/D7_DEMO_SCRIPT_CN.md`: concise Chinese speaking script for the recorded demonstration.

The D7 token counts are labelled deterministic estimates based on the complete
prompt and transcript length. They are appropriate for zero-cost reproduction;
the D5 live API usage remains authoritative for the final deployment cost model.
