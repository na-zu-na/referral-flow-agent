"""Read the frozen final D5 selection. No legacy D6 file selects experiments."""
import csv
import json
from pathlib import Path

from .config import D5, REPO, ROOT


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def jsonl_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def inventory() -> list[dict]:
    rows = csv_rows(D5 / "SELECTED_5PLUS1_INVENTORY.csv")
    index = json.loads((D5 / "results" / "live" / "SELECTED_FINAL_INDEX.json").read_text(encoding="utf-8"))
    selected = index["selected_v2"] + index["prompt_control"]
    if len(rows) != 6 or {r["experiment_id"] for r in rows} != {r["experiment_id"] for r in selected}:
        raise ValueError("Frozen D5 inventory/index disagree")
    for row in rows:
        match = next(x for x in selected if x["experiment_id"] == row["experiment_id"])
        for field in ("model_id", "scope", "prompt_version", "source_commit", "runs", "unique_cases"):
            if str(row[field]) != str(match[field]):
                raise ValueError(f"Frozen D5 inventory/index differ at {row['experiment_id']}:{field}")
        if row["selected_final"].lower() != "true":
            raise ValueError("Unselected experiment in final D5 inventory")
    if index["normalization_rows"] != 278 or index["changed_score_rows"] != 0:
        raise ValueError("Unexpected frozen D5 score index")
    return rows


def score_rows() -> list[dict]:
    return csv_rows(ROOT / "D5" / "D5_NORMALIZED_SCORE_CHANGES.csv")


def load_batteries() -> dict[str, dict]:
    result = {}
    for item in inventory():
        bid = item["experiment_id"]
        base = D5 / "results" / "live" / bid
        result[bid] = {
            "inventory": item,
            "runs": csv_rows(base / "scored_reviewed" / "runs.csv"),
            "trials": csv_rows(base / "scored_reviewed" / "trials.csv"),
            "tools": csv_rows(base / "scored_reviewed" / "tool_calls.csv"),
            "raw": jsonl_rows(base / "raw_checkpoint.jsonl"),
            "manifest": json.loads((base / "battery_manifest.json").read_text(encoding="utf-8")),
            "extra_errors": jsonl_rows(base / "provider_errors.jsonl") if (base / "provider_errors.jsonl").exists() else [],
        }
        if len(result[bid]["runs"]) != int(item["runs"]):
            raise ValueError(f"D5 row count differs from inventory: {bid}")
    return result


def d2_live() -> list[dict]:
    return json.loads((REPO / "results" / "d2_live_gpt4o_mini_runs.json").read_text(encoding="utf-8"))
