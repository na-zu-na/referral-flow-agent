from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D6 = ROOT / "D6_cost_analysis"
OUT = D6 / "outputs"
D5 = ROOT / "D5" / "outputs" / "D5_MINIMAL_GITHUB_PACKAGE"
REPO = ROOT if (ROOT / "evaluation").is_dir() else ROOT / "referral-flow-agent"

MONTHLY_REFERRALS = 4000
NURSE_HOURLY_COST_USD = Decimal("55")
HUMAN_MINUTES_PER_FAILURE = Decimal("10")
FAILURE_COST_USD = NURSE_HOURLY_COST_USD * HUMAN_MINUTES_PER_FAILURE / Decimal("60")
VALUE_OF_ONE_SUCCESS_PP_MONTHLY = Decimal("0.01") * FAILURE_COST_USD * MONTHLY_REFERRALS
FIXED_MONTHLY_COST_USD = Decimal("0")  # ASSUMED_BASELINE, not deployment evidence.
BOOTSTRAP_ITERATIONS = 5000
BOOTSTRAP_SEED = 6201
