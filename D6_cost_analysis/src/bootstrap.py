from collections import defaultdict
from statistics import mean

import numpy as np

from .config import BOOTSTRAP_ITERATIONS, BOOTSTRAP_SEED, MONTHLY_REFERRALS
from .cost_engine import fallback_cost


def cluster_sample(rows: list[dict], rng: np.random.Generator) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["case_id"]].append(row)
    ids = sorted(groups)
    sampled = rng.choice(ids, size=len(ids), replace=True)
    return [r for cid in sampled for r in groups[cid]]


def bootstrap_metrics(rows: list[dict], iterations: int = BOOTSTRAP_ITERATIONS, seed: int = BOOTSTRAP_SEED) -> dict:
    rng = np.random.default_rng(seed)
    samples = {k: [] for k in ("trial_weighted_pass_rate", "ai_cost", "fallback_cost", "expected_cost_per_referral", "monthly_cost")}
    for _ in range(iterations):
        draw = cluster_sample(rows, rng)
        p = sum(r["passed"] for r in draw) / len(draw)
        costs = [r["provider_cost_usd"] for r in draw if r["provider_cost_usd"] is not None]
        ai = mean(costs) if costs else float("nan")
        fall = fallback_cost(p)
        samples["trial_weighted_pass_rate"].append(p)
        samples["ai_cost"].append(ai)
        samples["fallback_cost"].append(fall)
        samples["expected_cost_per_referral"].append(ai + fall)
        samples["monthly_cost"].append((ai + fall) * MONTHLY_REFERRALS)
    result = {}
    for metric, values in samples.items():
        arr = np.asarray(values, dtype=float)
        result[metric] = {
            "median": float(np.nanmedian(arr)),
            "p2_5": float(np.nanpercentile(arr, 2.5)),
            "p97_5": float(np.nanpercentile(arr, 97.5)),
        }
    return result

