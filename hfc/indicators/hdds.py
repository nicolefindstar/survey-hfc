"""
HDDS — Household Dietary Diversity Score

Checks:
  Sequential : Missing values, Erroneous values (outside 0–1)
  Independent:
    LowHDDS  — score < low_hdds_threshold
    AllGroups — all 10 groups consumed (perfect score; flag for review)
"""

import pandas as pd

from .base import BaseIndicator


class HDDSIndicator(BaseIndicator):
    NAME = "HDDS"

    def _run_specific_checks(self):
        scored_cols = [
            c for c in self.std.get("scored_columns", [])
            if c in self.df.columns
        ]
        if not scored_cols:
            self.log.warning("No HDDS scored columns found in dataset — skipping HDDS checks")
            return

        self.df["HDDS"] = self.df[scored_cols].sum(axis=1)

        low_thr = self.std.get("low_hdds_threshold", 3)
        self._add_flag(
            "Flag_HDDS_Low",
            self.df["HDDS"] < low_thr,
            f"HDDS score very low (< {low_thr})",
        )

        self._add_flag(
            "Flag_HDDS_AllGroups",
            self.df["HDDS"] == len(scored_cols),
            "All food groups consumed — verify plausibility with enumerator",
        )
