"""
Demo — Household Demographics

Derived columns added to df (available to later indicators):
  Sum_M, Sum_F, Sum_All, Sum_Adults, Sum_Children, Sum_F1259

Checks:
  Sequential : Missing values, Erroneous values (< 0 or > per-column max)
  Independent:
    HighHHSize    — HHSize > threshold
    SumMismatch   — |sum(age-gender groups) − HHSize| > tolerance
    NoAdults      — zero adults in household
    PLWExceeds    — pregnant/lactating women > females aged 12–59
"""

import pandas as pd

from .base import BaseIndicator


class DemoIndicator(BaseIndicator):
    NAME = "Demo"

    def _run_specific_checks(self):
        std = self.std
        cfg = self.cfg

        male_cols     = [c for c in std.get("male_cols",      []) if c in self.df.columns]
        female_cols   = [c for c in std.get("female_cols",    []) if c in self.df.columns]
        adult_cols    = [c for c in std.get("adult_cols",     []) if c in self.df.columns]
        child_cols    = [c for c in std.get("child_cols",     []) if c in self.df.columns]
        f1259_cols    = [c for c in std.get("females_1259_cols", []) if c in self.df.columns]
        all_ag_cols   = list(dict.fromkeys(male_cols + female_cols))

        # Derived aggregates (made available for rCSI cross-check)
        if male_cols:
            self.df["Sum_M"]        = self.df[male_cols].sum(axis=1)
        if female_cols:
            self.df["Sum_F"]        = self.df[female_cols].sum(axis=1)
        if all_ag_cols:
            self.df["Sum_All"]      = self.df[all_ag_cols].sum(axis=1)
        if adult_cols:
            self.df["Sum_Adults"]   = self.df[adult_cols].sum(axis=1)
        if child_cols:
            self.df["Sum_Children"] = self.df[child_cols].sum(axis=1)
        if f1259_cols:
            self.df["Sum_F1259"]    = self.df[f1259_cols].sum(axis=1)

        # ── High HH size ──────────────────────────────────────────────────────
        if "HHSize" in self.df.columns:
            thr = cfg.get("high_hhsize_threshold", 30)
            self._add_flag(
                "Flag_Demo_HighHHSize",
                self.df["HHSize"] > thr,
                f"Household size > {thr} (HHSize={thr})",
            )

            # ── Sum mismatch ──────────────────────────────────────────────────
            if all_ag_cols:
                tol = cfg.get("hhsize_sum_tolerance", 1)
                mismatch = (self.df["Sum_All"] - self.df["HHSize"]).abs() > tol
                self._add_flag(
                    "Flag_Demo_SumMismatch",
                    mismatch,
                    f"Sum of age/gender groups differs from HHSize by > {tol}",
                )

        # ── No adults ─────────────────────────────────────────────────────────
        if "Sum_Adults" in self.df.columns:
            self._add_flag(
                "Flag_Demo_NoAdults",
                self.df["Sum_Adults"] == 0,
                "No adults (18+) reported in household",
            )

        # ── PLW exceeds female 12–59 ──────────────────────────────────────────
        if "HHPregLactNb" in self.df.columns and "Sum_F1259" in self.df.columns:
            self._add_flag(
                "Flag_Demo_PLWExceeds",
                self.df["HHPregLactNb"] > self.df["Sum_F1259"],
                "Pregnant/lactating women > females aged 12–59",
            )
