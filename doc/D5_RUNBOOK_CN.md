# D5 最终证据与复核说明

当前 D5 已经冻结，不需要为了生成报告重新调用模型。最终事实来源是：

- `results/d5/live/SELECTED_FINAL_INDEX.json`
- `results/d5/SELECTED_5PLUS1_INVENTORY.csv`
- 各 selected experiment 的 `scored_reviewed/` 逐次记录
- `results/d5/D5_COMPARISON.md`
- `results/d5/D5_COST_RECONCILIATION.md`
- `doc/D5_FINAL_QA.md`
- `doc/D5_SCORING_NORMALIZATION_AUDIT.md`

`results/live/` 是历史 source-run archive，其中包括已经被替代的 Llama
证据；它不是最终 selected inventory，也不能用于替换 `results/d5/`。

## 最终 5+1 设计

| Operator | Experiment | Scope |
|---|---|---|
| FAN YANXI | GPT-4o-mini V2 | 40 cases / 52 runs |
| HOU YUXUAN | Qwen 3 30B V2 | 40 cases / 52 runs |
| LIN SIYUAN | Mistral Small 3.2 V2 | 40 cases / 52 runs |
| WEN HAO | Gemini 2.5 Flash V2 | 40 cases / 52 runs |
| CHEN CHANG | Claude Opus 5 V2 | 6 negative cases / 18 runs |
| ZHOU YU | Qwen 3 30B V1 prompt control | 40 cases / 52 runs |

四个完整 V2 batteries 使用 34 个普通案例各一次、六个 negative cases
各三次。Claude 按 Frontier exception 只运行相同的 18 个 negative trials，
不能报告完整案例通过率。Qwen V1 与 V2 使用相同 model 和 52 个匹配 keys。

## 离线复核

以下命令不会调用 OpenRouter，也不会产生模型费用：

```bash
python -m evaluation.d5_final --audit-only
python -m unittest tests.test_d5_final -v
```

最终规模为 278 个 selected scored runs，278/278 有 provider cost。Selected
scored-run spend 为 US$2.13502002；计入额外 Mistral provider-error charge 后
为 US$2.13533847。

## 仅在明确要求新实验时运行 live battery

现有最终报告不需要重跑。若将来明确要求新增实验，应使用新目录，不能覆盖
冻结证据：

```bash
python run_d5_battery.py \
  --model 'PROVIDER/MODEL' \
  --prompt-version v2 \
  --operator 'ACTUAL OPERATOR' \
  --max-cost-usd 10.00 \
  --out results/live/NEW_EXPERIMENT
```

Frontier negative-only 实验增加 `--negative-only`。中断后只有在 model、
prompt、operator、source commit 和输出目录完全一致时才能使用 `--resume`。
API key 必须从 `OPENROUTER_API_KEY` 环境变量读取，不得写入仓库。

逐次保存文件包括 manifest、checkpoint、progress、reviewed claims、summary、
runs、trials 和 tool calls。Judgement review 只对已保存 trace 复评分，不应
再次调用模型，也不得修改原始 model output、token 或 provider charge。
