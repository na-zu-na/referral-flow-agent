#!/usr/bin/env python3
"""Regenerate final D5 5+1 reports using the offline normalized scorer.

Run from the complete D5 working tree. The original 52-run-only builder was
retired because it cannot handle Claude's negative-only 18-run scope and would
overwrite unified-scoring reports with historical reviewed labels.
"""

from pathlib import Path
import sys

D5_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(D5_ROOT))

from final_5plus1 import main  # noqa: E402


if __name__ == "__main__":
    main()
