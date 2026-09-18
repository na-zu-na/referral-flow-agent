from collections import defaultdict
from statistics import mean

from .config import FAILURE_COST_USD, FIXED_MONTHLY_COST_USD, MONTHLY_REFERRALS


def failure_cost() -> float:
    return float(FAILURE_COST_USD)


def value_of_one_success_pp_monthly() -> float:
    return 0.01 * failure_cost() * MONTHLY_REFERRALS


def pass_rates(rows: list[dict]) -> tuple[float, float]:
    if not rows:
        raise ValueError("No formal runs")
    trial_weighted = sum(r["passed"] for r in rows) / len(rows)
    cases = defaultdict(list)
    for r in rows:
        cases[r["case_id"]].append(r["passed"])
    case_balanced = mean(mean(xs) for xs in cases.values())
    return trial_weighted, case_balanced


def case_balanced_mean(rows: list[dict], field) -> tuple[float, int, int]:
    """Average within case first, then give every observed case equal weight.

    A case whose metric is entirely unavailable is excluded from this metric's
    mean (not imputed) and exposed in the returned coverage numerator.
    """
    if not rows:
        raise ValueError("No formal runs")
    get = field if callable(field) else lambda row: row[field]
    cases = defaultdict(list)
    for row in rows:
        cases[row["case_id"]].append(get(row))
    observed = [mean(x for x in values if x is not None)
                for values in cases.values() if any(x is not None for x in values)]
    if not observed:
        raise ValueError("No measured cases for metric")
    return mean(observed), len(observed), len(cases)


def fallback_cost(pass_rate: float) -> float:
    if not 0 <= pass_rate <= 1:
        raise ValueError("pass_rate must be within [0,1]")
    return (1 - pass_rate) * failure_cost()


def monthly_cost(ai_cost: float, pass_rate: float, fixed: float = float(FIXED_MONTHLY_COST_USD)) -> float:
    return MONTHLY_REFERRALS * (ai_cost + fallback_cost(pass_rate)) + fixed


def sensitivity_rates(base: float) -> dict[str, float]:
    return {"LOW": max(0.0, base - 0.10), "BASE": base, "HIGH": min(1.0, base + 0.10)}


def break_even(candidate_ai_cost: float, benchmark_total_cost: float) -> tuple[float, float]:
    raw = 1 - (benchmark_total_cost - candidate_ai_cost) / failure_cost()
    return raw, min(1.0, max(0.0, raw))
