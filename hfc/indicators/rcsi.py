"""
rCSI — Reduced Coping Strategies Index

Checks:
  Sequential : Missing values, Erroneous values (outside 0–7)
  Independent:
    Identical         — all 5 strategy values identical (non-zero)
    ZeroWithPoorFCG   — rCSI = 0 yet FCG = Poor (data inconsistency)
    HighWithAcceptFCG — high rCSI yet FCG = Acceptable
    AdultMealNbChildren — adults reduce meals for children when no children in HH
"""

import pandas as pd

from .base import BaseIndicator


class rCSIIndicator(BaseIndicator):
    NAME = "rCSI"

    _STRATEGIES = ["rCSILessQlty", "rCSIBorrow", "rCSIMealSize", "rCSIMealAdult", "rCSIMealNb"]
    _WEIGHTS    = {"rCSILessQlty": 1, "rCSIBorrow": 2, "rCSIMealSize": 1,
                   "rCSIMealAdult": 3, "rCSIMealNb": 1}

    def _run_specific_checks(self):
        available = [s for s in self._STRATEGIES if s in self.df.columns]
        w = self.std.get("weights", self._WEIGHTS)

        self.df["rCSI"] = sum(
            self.df[s] * w.get(s, self._WEIGHTS[s])
            for s in available
        )

        # ── Identical ─────────────────────────────────────────────────────────
        if self.cfg.get("flag_identical", True) and len(available) > 1:
            all_same  = self.df[available].apply(lambda r: r.nunique() == 1, axis=1)
            not_all_0 = self.df[available[0]] != 0
            self._add_flag(
                "Flag_rCSI_Identical",
                all_same & not_all_0,
                "All rCSI strategy values are identical (possible data-entry shortcut)",
            )

        # ── Cross-check with FCG (only if FCS already computed) ──────────────
        if "FCG" in self.df.columns:
            poor_fcg       = self.df["FCG"] == "Poor"
            acceptable_fcg = self.df["FCG"] == "Acceptable"

            if self.cfg.get("zero_rcsi_with_poor_fcg", True):
                self._add_flag(
                    "Flag_rCSI_ZeroWithPoorFCG",
                    poor_fcg & (self.df["rCSI"] == 0),
                    "rCSI = 0 despite Poor food consumption group (inconsistency)",
                )

            high_thr = self.cfg.get("high_rcsi_with_acceptable_fcg", 18)
            self._add_flag(
                "Flag_rCSI_HighWithAcceptFCG",
                acceptable_fcg & (self.df["rCSI"] > high_thr),
                f"rCSI > {high_thr} despite Acceptable FCG (inconsistency)",
            )

        # ── Adult meal reduction when no children ─────────────────────────────
        if "rCSIMealAdult" in self.df.columns and "Sum_Children" in self.df.columns:
            self._add_flag(
                "Flag_rCSI_AdultMealNoChildren",
                (self.df["rCSIMealAdult"] > 0) & (self.df["Sum_Children"] == 0),
                "Adults reducing meals for children, but no children in household",
            )
