"""Run the offline Phase B cost analysis from any working directory."""
from src.pipeline import run_pipeline


if __name__ == "__main__":
    report=run_pipeline()
    print("Selected scored runs:",report["selected_scored_run_count"])
    print("Provider-cost coverage:",report["provider_cost_coverage"])
    print("Selected scored-run spend USD:",report["evaluation_spend"]["selected_scored_run_spend"])
    print("Outputs: D6_cost_analysis/outputs")
