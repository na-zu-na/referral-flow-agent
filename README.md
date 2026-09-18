# PE6201 A2 — Problem B Referral Flow Agent

This repository combines the existing Problem B data, tools, and deterministic
guardrails with the complete Member 1 single-agent ReAct controller.

The default is free and offline:

```bash
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

The design table, poka-yoke evidence, measurements, and live reproduction
command are in [`D2_TOOL_EVIDENCE.md`](D2_TOOL_EVIDENCE.md).

Run the D4 evaluation harness on the 40-case team-authored core set. Ordinary
cases run once and the six negative cases run three times, for 52 runs:

```bash
python3 run_eval.py --tier core --prompt-version v2 --descriptors v2 \
  --call-mode parallel --autonomy confirm --temperature 0 \
  --out results/member4_core_scripted
```

The scoring and judgement-review workflow is documented in
[`doc/MEMBER4_EVALUATION_README.md`](doc/MEMBER4_EVALUATION_README.md).
Reviewed scripted V1/V2 evidence is summarized in
[`results/d4_policy_model_summary.csv`](results/d4_policy_model_summary.csv).

The frozen final D5 5+1 selection is in [`D5/`](D5/FINAL_5PLUS1_QA.md).
Its authoritative [model comparison](D5/outputs/D5_MINIMAL_GITHUB_PACKAGE/D5_COMPARISON.md),
[cost reconciliation](D5/outputs/D5_MINIMAL_GITHUB_PACKAGE/D5_COST_RECONCILIATION.md),
[selected inventory](D5/outputs/D5_MINIMAL_GITHUB_PACKAGE/SELECTED_5PLUS1_INVENTORY.csv),
and [scoring audit](D5/SCORING_NORMALIZATION_AUDIT.md) are based on 278 saved
scored runs: four 52-run full V2 batteries, 18 Claude Opus 5 negative-only
runs, and the 52-run Qwen V1 prompt control. The V2 models span five families
and two team-selected price tiers (GPT/Qwen/Mistral/Gemini lower-price;
Claude Frontier under the Section 7 exception). This is not a claim that the
course officially maps these exact model IDs to tiers. The selected scored
provider spend is US$2.13502002. Claude has no full-battery pass rate; Llama
is not in the final selection.

For offline verification, run `python D5/final_5plus1.py --audit-only` and
`python -m unittest discover -s D5/tests -v`. These commands do not call a
model or provider. The source-run archive in [`results/live/`](results/live/)
is retained, including superseded Llama evidence; it is not the final selected
inventory. The older [`D5 runbook`](doc/D5_RUNBOOK_CN.md),
[`comparison`](doc/D5_COMPARISON.md), and
[`cost report`](doc/D5_COST_RECONCILIATION.md) document that historical
Llama-era selection and must not be used as the final D5 result.

Reproduce the two D7 controlled failures and regenerate their evidence:

```bash
python3 -m experiments.d7_failures
```

The experiment contract, report-ready analysis, and Chinese demo script are in
[`doc/D7_README.md`](doc/D7_README.md),
[`doc/D7_REPORT_SECTION.md`](doc/D7_REPORT_SECTION.md), and
[`doc/D7_DEMO_SCRIPT_CN.md`](doc/D7_DEMO_SCRIPT_CN.md).

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

The API listens on `http://127.0.0.1:5000`. Its request and response contract is
documented in [`doc/WEB_API_SPEC_CN.md`](doc/WEB_API_SPEC_CN.md). Live runs read
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

See `MEMBER1_IMPLEMENTATION_GUIDE_CN.md` for the detailed Chinese walkthrough.
