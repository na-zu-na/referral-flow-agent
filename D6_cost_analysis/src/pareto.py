def dominated(candidate: dict, alternatives: list[dict]) -> bool:
    c = candidate["cost"]
    p = candidate["pass_rate"]
    return any((other is not candidate and other["cost"] <= c and other["pass_rate"] >= p
                and (other["cost"] < c or other["pass_rate"] > p)) for other in alternatives)


def pareto_status(rows: list[dict]) -> dict[str, str]:
    return {r["experiment_id"]: "DOMINATED" if dominated(r, rows) else "PARETO_EFFICIENT" for r in rows}

