from pathlib import Path
import re


def load_registry() -> dict:
    text = (Path(__file__).parent / "pricing.yaml").read_text(encoding="utf-8")
    registry = {}
    pattern = re.compile(r"^([^#\s][^:]+): \{input_per_million: ([0-9.]+), output_per_million: ([0-9.]+)\}$")
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            registry[match.group(1)] = {"input_per_million": float(match.group(2)),
                                        "output_per_million": float(match.group(3))}
    if len(registry) != 4:
        raise ValueError("Frozen D5 diagnostic rate registry does not have four model entries")
    return registry


def verify_registry(batteries: dict, registry: dict) -> None:
    for d in batteries.values():
        for wrapper in d["raw"]:
            cfg = wrapper["record"]["config"]
            entry = registry.get(cfg["model"])
            if cfg["model"] == "anthropic/claude-opus-5" and float(cfg["price_input_per_million"]) == 0 and float(cfg["price_output_per_million"]) == 0:
                continue
            if entry is None or float(entry["input_per_million"]) != float(cfg["price_input_per_million"]) or float(entry["output_per_million"]) != float(cfg["price_output_per_million"]):
                raise ValueError(f"Price registry is not verified by D5 config: {cfg['model']}")


def recompute_list_rate_cost(run: dict, registry: dict) -> float | None:
    if not run["tokens_measured"] or run["input_tokens"] is None or run["output_tokens"] is None:
        return None
    entry = registry.get(run["model"])
    if entry is None:
        return None  # Never default missing pricing to zero.
    return (run["input_tokens"] * float(entry["input_per_million"]) + run["output_tokens"] * float(entry["output_per_million"])) / 1_000_000
