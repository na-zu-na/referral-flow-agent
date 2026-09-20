# D0 - Why an Agent

Referral coordination belongs on rung 7 because each referral determines its
path and step count. In our 40-case set, `REF-6002` required four tool turns
before guarded booking, whereas red-flag case `REF-6060` escalated after two.
Rung 1 can classify a complete referral but cannot retrieve records. Rung 2
can run fixed checks but cannot adapt the sequence or number of steps to new
evidence. Rung 3 can choose one route but cannot revise it after new evidence.
Rung 4 can parallelise independent checks but cannot select subsequent
actions. Rung 5 can allocate subtasks but adds unnecessary multi-component
complexity. Rung 6 can improve a proposed answer but cannot decide what
evidence to retrieve or when to act. Only rung 7 supplies the repeated
observe-decide-act loop. For fixed cases, a coded workflow would be cheaper,
enumerable and safer.

Both agent conditions hold: the sequence is not known in advance, and every
step receives falsifiable ground truth. Referral, specialty-criteria, patient
and slot records answer synchronously within the run; missing or contradictory
evidence requires an information request or escalation. The model selects
retrieval and may re-query. The governance cliff is `book_slot`, because
booking consumes capacity, unlike read-only retrieval. We therefore use
`confirm` autonomy: deterministic checks and human confirmation authorise the
simulated write. Without fast objective records or this gate, we would not
build an agent.

Rung 7 also makes cost variable. Gemini costs US$0.003484 in mean provider AI
cost per evaluated run, but its 39/52 pass rate produces an expected total cost
of US$2.2952 per referral after human fallback. With \(P = 0.75\) and measured
median \(T = 4\), implied per-turn reliability is
\(s = P^{1/T} = 0.931\). Holding \(s\) constant predicts whole-run success of
0.806 at three turns and 0.563 at eight. This is diagnostic, not causal:
errors are dependent, and \(P\) and \(T\) came from different backends.

The controlled `get_clinic_slots` descriptor comparison showed that a more
auditable return contract did not automatically improve pass rate and
increased prompt and observation size. Separately, the reproduced
dependency-ordering failure showed that planning instructions affect whether
the agent waits for prerequisite evidence. Action memory and a hard cap
prevent repeated calls from inflating \(T\). Outcome cases measure
correctness; separate guardrail cases test refusals, caps and gates.

## Good-run criteria

1. Every conclusion is traceable to retrieved records.
2. The outcome follows the fixed `book`, `request_information` or `escalate`
   rule.
3. Missing evidence or one escalation trigger is named; unsupported facts are
   never invented.
4. `book_slot` runs at most once, after evidence and human confirmation.
5. The run remains within documented turn and token limits and costs less than
   human handling under the stated assumptions.

These criteria are the submitted good-run standard. The current repository
history does not establish that this document was committed before the first
Agent implementation commit.
