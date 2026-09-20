# PE6201 A2 — Problem B Referral Flow Agent

This repository contains the team submission for Problem B: a single-agent
ReAct controller with local data, tools, deterministic guardrails, evaluation
evidence, live-model comparisons, and cost analysis.

The design justification, seven-rung comparison, reliability calculation, and
good-run criteria are documented in
[`doc/D0_AGENT_JUSTIFICATION.md`](doc/D0_AGENT_JUSTIFICATION.md).

The default is free and offline:

```bash
python3 -m pip install -r requirements.txt
python3 main.py REF-5602 --verbose
```

Run every automated test:

```bash
python3 -m unittest discover -s tests -v
```

Show the exact v1 or v2 prompt:

```bash
python3 main.py --descriptors v2 --show-prompt
```

Controlled sequential/parallel comparison:

```bash
python3 main.py REF-5602 --call-mode sequential
python3 main.py REF-5602 --call-mode parallel
```

Run the complete D2 descriptor/return-shape and same-turn batching experiment
(40 core cases, three isolated trials per variant):

```bash
python3 experiments/run_d2_experiments.py
```

The design table, poka-yoke evidence, measurements, and experiment conclusion
are in
[`results/D2_TOOL_EVIDENCE_TEST_CONCLUSION.md`](results/D2_TOOL_EVIDENCE_TEST_CONCLUSION.md).

Run the D4 evaluation harness on the 40-case team-authored core set. Ordinary
cases run once and the six negative cases run three times, for 52 runs:

```bash
python3 run_eval.py --tier core --prompt-version v2 --descriptors v2 \
  --call-mode parallel --autonomy confirm --temperature 0 \
  --out results/member4_core_scripted
```

The scoring and judgement-review workflow is implemented in
[`evaluation/harness.py`](evaluation/harness.py), with reproducible commands
provided by [`run_eval.py`](run_eval.py). Reviewed scripted V1/V2 evidence is summarized in
[`results/d4_policy_model_summary.csv`](results/d4_policy_model_summary.csv).

The frozen final D5 5+1 evidence is integrated under [`results/d5/`](results/d5/).
Its authoritative [model comparison](results/d5/D5_COMPARISON.md),
[cost reconciliation](results/d5/D5_COST_RECONCILIATION.md),
[selected inventory](results/d5/SELECTED_5PLUS1_INVENTORY.csv),
and [scoring audit](doc/D5_SCORING_NORMALIZATION_AUDIT.md) are based on 278 saved
scored runs: four 52-run full V2 batteries, 18 Claude Opus 5 negative-only
runs, and the 52-run Qwen V1 prompt control. The V2 models span five families
and two team-selected price tiers (GPT/Qwen/Mistral/Gemini lower-price;
Claude Frontier under the Section 7 exception). This is not a claim that the
course officially maps these exact model IDs to tiers. The selected scored
provider spend is US$2.13502002. Claude has no full-battery pass rate; Llama
is not in the final selection.

For offline verification, run `python -m evaluation.d5_final --audit-only` and
`python -m unittest tests.test_d5_final -v`. These commands do not call a
model or provider. The source-run archive in [`results/live/`](results/live/)
is retained, including superseded Llama evidence; it is not the final selected
inventory. Human-facing current summaries are available in the
[`comparison`](doc/D5_COMPARISON.md) and
[`cost reconciliation`](doc/D5_COST_RECONCILIATION.md); both point back
to the frozen `results/d5/` evidence.

The frozen [D6 Cost / FinOps analysis](doc/D6_COST_ANALYSIS.md) is integrated
with the project cost package. Its [final QA review](results/d6/FINAL_QA_REVIEW.md)
records `D6_FREEZE_READY`, and the teacher-facing
[workbook](doc/PE6201_D6_Cost_Analysis_Teacher_Submission_FIXED.xlsx)
and reports are under `results/d6/`. D6 uses the frozen D5 selection, not
the historical Llama-era records. Run its offline tests and second-pass QA from
the repository root using the commands in the D6 README; no model or provider
call is required.

Reproduce the two D7 controlled failures and regenerate their evidence:

```bash
python3 -m experiments.d7_failures
```

The experiment contract and report-ready analysis are in
[`doc/D7_README.md`](doc/D7_README.md),
and [`doc/D7_REPORT_SECTION.md`](doc/D7_REPORT_SECTION.md).

Run a live OpenRouter model only when intentionally doing the model battery:

```bash
export OPENROUTER_API_KEY="your-key"
python3 main.py REF-5602 --backend live --model openai/gpt-4o-mini --verbose
```

In live `confirm` mode the controller pauses before `book_slot` unless a trusted
UI/CLI supplies an approval callback. Model text cannot approve itself.

Run the website backend (scripted mode needs no API key):

```bash
python3 -m pip install -r requirements-web.txt
python3 -m web_api.app
```

The API listens on `http://127.0.0.1:5000`. Routes and validation are defined in
[`web_api/app.py`](web_api/app.py), while result-file readers and background
run management are in [`web_api/readers.py`](web_api/readers.py) and
[`web_api/run_manager.py`](web_api/run_manager.py). Live runs read
`OPENROUTER_API_KEY` from the server environment; the key is never accepted by
or returned from an API endpoint.

Start the Vue website in a second terminal:

```bash
cd web_ui
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite forwards `/api` requests to the Flask API.
Use `npm run build` to validate and create the production bundle.
