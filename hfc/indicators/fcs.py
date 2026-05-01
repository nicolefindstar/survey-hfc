"""
FCS — Food Consumption Score

Checks:
  Sequential : Missing values, Erroneous values (outside 0–7)
  Independent:
    Identical     — all 8 food groups have the same non-zero value
    LowStaple     — staple consumption < threshold (default 1 day)
    LowFCS        — FCS < low_fcs_threshold
    HighFCS       — FCS > high_fcs_threshold
"""

import numpy as np
import pandas as pd

from .base import BaseIndicator


class FCSIndicator(BaseIndicator):
    NAME = "FCS"

    _GROUPS = ["FCSStap", "FCSPulse", "FCSDairy", "FCSPr", "FCSVeg", "FCSFruit", "FCSFat", "FCSSugar"]
    _WEIGHTS = {"FCSStap": 2, "FCSPulse": 3, "FCSDairy": 4, "FCSPr": 4,
                "FCSVeg": 1, "FCSFruit": 1, "FCSFat": 0.5, "FCSSugar": 0.5}

    def _run_specific_checks(self):
        # ── derive FCS score and FCG ──────────────────────────────────────────
        available = [g for g in self._GROUPS if g in self.df.columns]
        w = self.std.get("weights", self._WEIGHTS)

        self.df["FCS"] = sum(
            self.df[g] * w.get(g, self._WEIGHTS[g])
            for g in available
        )

        poor_cut = self.std.get("fcg_poor_threshold", 21)
        bord_cut = self.std.get("fcg_borderline_threshold", 35)
        # Allow configurable override
        poor_cut = self.cfg.get("fcg_poor_threshold", poor_cut)
        bord_cut = self.cfg.get("fcg_borderline_threshold", bord_cut)

        self.df["FCG"] = pd.cut(
            self.df["FCS"],
            bins=[-np.inf, poor_cut, bord_cut, np.inf],
            labels=["Poor", "Borderline", "Acceptable"],
            right=False,
        )

        # ── Identical values ──────────────────────────────────────────────────
        if len(available) > 1:
            first_col = self.df[available[0]]
            all_same = self.df[available].apply(lambda r: r.nunique() == 1, axis=1)
            not_all_zero = first_col != 0
            self._add_flag(
                "Flag_FCS_Identical",
                all_same & not_all_zero,
                "All 8 food-group values are identical (possible data-entry shortcut)",
            )

        # ── Low staple ────────────────────────────────────────────────────────
        if "FCSStap" in self.df.columns:
            thr = self.cfg.get("low_staple_threshold", 1)
            self._add_flag(
                "Flag_FCS_LowStaple",
                self.df["FCSStap"] < thr,
                f"Staple consumption < {thr} days (FCSStap={thr})",
            )

        # ── Low FCS ───────────────────────────────────────────────────────────
        low = self.cfg.get("low_fcs_threshold", 10)
        self._add_flag(
            "Flag_FCS_Low",
            self.df["FCS"] < low,
            f"FCS score is very low (< {low})",
        )

        # ── High FCS ──────────────────────────────────────────────────────────
        high = self.cfg.get("high_fcs_threshold", 112)
        self._add_flag(
            "Flag_FCS_High",
            self.df["FCS"] > high,
            f"FCS score suspiciously high (> {high})",
        )
