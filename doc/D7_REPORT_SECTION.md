# Section 5 The Two Failures

We reproduced both failures as controlled deletions from the working agent and replayed deterministic model moves through the submitted controller, tools and guardrails. Offline token values are reproducible estimates based on the complete prompt and transcript length; the D5 live usage remains the authoritative deployment-cost measurement.

## Failure 1: loop control

We deleted persistent action de-duplication and used the same backend to repeat `get_referral("REF-5602")` with fresh call IDs. Across the complete 40-case core set, the median and worst legitimate run were both four tool turns, all 40 cases passed, and there were no cap hits. We therefore set the cap to five, one turn above the observed maximum. Without de-duplication, the repeated action survived until the cap. Restoring de-duplication stopped the second equivalent action immediately. De-duplication is the primary catcher, the step cap is the final backstop, and the token ceiling would react later. The ordinary core-set pass rate remained 40/40 with or without de-duplication, so the fix did not regress legitimate paths.

| Variant | Turns | Input/output tokens | Estimated cost | D7 criterion | Catch |
|---|---:|---:|---:|---|---|
| De-duplication deleted | 5 | 27,103 / 252 | US$0.0028111 | Fail | `STEP_LIMIT_REACHED` |
| Working agent | 1 | 8,351 / 84 | US$0.0008687 | Pass | `DUPLICATE_ACTION_BLOCKED` |

The restored protection reduced estimated cost by 69.1% and prevented four unnecessary completed tool turns.

## Failure 2: prompt dependency ordering

We deleted exactly one 87-character sentence from the working v2 system prompt: “A dependent call must wait for successful prerequisite observations from earlier turns.” The case (`REF-5697`), v2 descriptors, prompt-aware deterministic backend implementation, controller, tools, guardrails, call mode and cap were unchanged. Without the rule, the policy batched `get_clinic_slots` with its prerequisite checks, so the real guardrail stopped the run loudly with `DEPENDENCY_VIOLATION`. Restoring the sentence caused the same policy to wait, perform the slot query only after both prerequisites succeeded, and return the expected `no_slot_in_window` escalation.

| Variant | Turns | Input/output tokens | Estimated cost | Case pass | Outcome |
|---|---:|---:|---:|---|---|
| Dependency sentence deleted | 1 | 8,309 / 163 | US$0.0008961 | Fail | `DEPENDENCY_VIOLATION` |
| Working agent | 3 | 17,609 / 239 | US$0.0018565 | Pass | `no_slot_in_window` |

This fix belongs at the prompt layer because the missing text controls the model's planning order. Changing the tool interface would be wrong because the call schemas and return meanings were not ambiguous; changing loop control would be wrong because the failure involved premature dependency use, not repetition or budget exhaustion. The correct run costs more only because it safely completes the required evidence-gathering work instead of failing early.
