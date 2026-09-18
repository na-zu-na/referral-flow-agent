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

Run the resumable D5 live battery only after choosing five models and approving
the budget. Each battery runs 52 trials: all 40 cases once plus two additional
trials for each of the six negative cases. This exceeds the 30-case/6-negative
passing floor without claiming the recommended 40-case/8-negative shape.

```bash
python3 run_d5_battery.py --model PROVIDER/MODEL --prompt-version v2 \
  --operator "ACTUAL OPERATOR" --max-cost-usd 1.50 --out results/d5_model_v2
```

The five-model plan, one-model V1/V2 comparison, review workflow, resume rules,
and final aggregation command are documented in
[`doc/D5_RUNBOOK_CN.md`](doc/D5_RUNBOOK_CN.md).

The preserved D5 evidence contains 260 V2 runs across Qwen 3 30B, Mistral
Small 3.2, GPT-4o-mini, Llama 3.3 70B, and Gemini 2.5 Flash, plus 52 Qwen V1
runs. See [`doc/D5_COMPARISON.md`](doc/D5_COMPARISON.md) for measured performance and
[`doc/D5_COST_RECONCILIATION.md`](doc/D5_COST_RECONCILIATION.md) for the US$0.653968992
account-level cost increment. Raw and reviewed records are under
[`results/live/`](results/live/).

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
