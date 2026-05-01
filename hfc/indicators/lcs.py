"""
LCS — Livelihood Coping Strategies

Encoding: 10=Applied, 20=Not needed, 30=Exhausted, 9999=Not applicable

Checks:
  Sequential : Missing values, Erroneous values (invalid choice codes)
  Independent:
    ChildStratNoChildren   — child-specific strategy applied but no children
    AllNA_PoorFood         — all strategies marked N/A but poor food security
    NonSequential          — emergency strategy applied without stress/crisis first
    ManyNotApplicable      — ≥ 3 N/A responses (may indicate skipping)
"""

import pandas as pd

from .base import BaseIndicator


_APPLIED = 10
_NOT_NEEDED = 20
_EXHAUSTED = 30
_NA = 9999


class LCSIndicator(BaseIndicator):
    NAME = "LCS"

    def _run_specific_checks(self):
        std = self.std
        stress_cols   = [c for c in std.get("stress_cols",    []) if c in self.df.columns]
        crisis_cols   = [c for c in std.get("crisis_cols",    []) if c in self.df.columns]
        emerg_cols    = [c for c in std.get("emergency_cols", []) if c in self.df.columns]
        child_strats  = [c for c in std.get("child_strategies", []) if c in self.df.columns]
        all_lcs       = stress_cols + crisis_cols + emerg_cols

        if not all_lcs:
            self.log.warning("No LCS columns found in dataset — skipping LCS checks")
            return

        # ── Child strategy with no children ───────────────────────────────────
        if child_strats and "Sum_Children" in self.df.columns:
            no_children = self.df["Sum_Children"] == 0
            child_applied = self.df[child_strats].isin([_APPLIED, _EXHAUSTED]).any(axis=1)
            self._add_flag(
                "Flag_LCS_ChildStratNoChildren",
                no_children & child_applied,
                "Child-specific coping strategy applied but no children in household",
            )

        # ── All N/A with poor food security ───────────────────────────────────
        if "FCG" in self.df.columns:
            all_na     = (self.df[all_lcs] == _NA).all(axis=1)
            poor_food  = self.df["FCG"] == "Poor"
            self._add_flag(
                "Flag_LCS_AllNA_PoorFood",
                all_na & poor_food,
                "All LCS strategies marked N/A despite Poor food security",
            )

        # ── Non-sequential application: emergency used without stress/crisis ──
        if stress_cols and crisis_cols and emerg_cols:
            stress_applied = self.df[stress_cols].isin([_APPLIED, _EXHAUSTED]).any(axis=1)
            crisis_applied = self.df[crisis_cols].isin([_APPLIED, _EXHAUSTED]).any(axis=1)
            emerg_applied  = self.df[emerg_cols].isin([_APPLIED, _EXHAUSTED]).any(axis=1)
            self._add_flag(
                "Flag_LCS_NonSequential",
                emerg_applied & ~(stress_applied | crisis_applied),
                "Emergency coping applied without any stress or crisis strategy (skip logic)",
            )

        # ── Many N/A responses ────────────────────────────────────────────────
        na_count = (self.df[all_lcs] == _NA).sum(axis=1)
        self._add_flag(
            "Flag_LCS_ManyNA",
            na_count >= 3,
            "≥ 3 LCS strategies marked Not Applicable (possible interviewer skip)",
        )
