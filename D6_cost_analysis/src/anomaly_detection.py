from collections import defaultdict


def p95(values: list[float]) -> float:
    if not values:
        raise ValueError("empty distribution")
    ordered = sorted(values)
    i = (len(ordered)-1) * 0.95
    lo = int(i)
    return ordered[lo] + (ordered[min(lo+1, len(ordered)-1)] - ordered[lo]) * (i-lo)


def thresholds(rows: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[r["experiment_id"]].append(r)
    return {bid: {
        "input_tokens": p95([r["input_tokens"] for r in group if r["input_tokens"] is not None]),
        "output_tokens": p95([r["output_tokens"] for r in group if r["output_tokens"] is not None]),
        "turns": p95([r["turns"] for r in group]),
        "provider_cost_usd": p95([r["provider_cost_usd"] for r in group if r["provider_cost_usd"] is not None]),
    } for bid, group in groups.items()}


def anomaly_rows(runs: list[dict], batteries: dict, limits: dict) -> list[dict]:
    raw = {x["record"]["run_id"]: x["record"] for d in batteries.values() for x in d["raw"]}
    out = []
    for r in runs:
        lim = limits[r["experiment_id"]]
        flags = []
        for field, name in [("input_tokens","HIGH_INPUT_TOKENS"),("output_tokens","HIGH_OUTPUT_TOKENS"),
                            ("turns","HIGH_TURNS"),("provider_cost_usd","HIGH_COST")]:
            if r[field] is not None and r[field] > lim[field]:
                flags.append(name)
        if not r["tokens_measured"]:
            flags.append("UNMEASURED_USAGE")
        rec = raw[r["run_id"]]
        calls = [(x.get("name"), str(x.get("arguments"))) for x in rec.get("tool_calls", [])]
        if r["turns"] >= int(rec["config"].get("max_turns", 8)) or any(calls[i] == calls[i-1] for i in range(1, len(calls))):
            flags.append("POSSIBLE_LOOP")
        out.append({"experiment_id": r["experiment_id"], "run_id": r["run_id"],
                    "case_id": r["case_id"], "trial": r["trial"], "status": r["status"],
                    "passed": r["passed"], "anomaly_flags": ";".join(flags),
                    "anomaly_count": len(flags), "rule": "strictly above within-battery p95; loop=max_turns or adjacent identical tool/args; missing usage flagged separately",
                    "note": "Provider versus config list-rate differences are reconciliation diagnostics, not operational anomalies"})
    return out
