"""
Household Expenditure checks — three modules:
  HHExpF    : Food expenditure (7-day recall)
  HHExpNF1M : Non-food expenditure (1-month recall)
  HHExpNF6M : Non-food expenditure (6-month recall)

All checks share the same base logic; only the category list and
recall period differ.

Checks (per module):
  Sequential : Missing on ALL items, Erroneous (negative values)
  Independent:
    ZeroTotal     — all expenditure values = 0 (flag if enabled)
    BelowMinPrice — any item > 0 but < min_item_price (implausibly small)
    ExtremeItem   — any single item > max threshold
"""

import pandas as pd
import numpy as np

from .base import BaseIndicator


class _HHExpBase(BaseIndicator):
    """Shared expenditure check logic."""

    _MODULE_KEY: str = ""     # e.g. 'food_7d' — key in hhexp.yaml standard config
    _MAX_CFG_KEY: str = ""    # key in configurable config for max single item

    def _get_expense_cols(self) -> list[str]:
        """Build full column names: category + source suffix."""
        exp_cfg = self.std.get(self._MODULE_KEY, {})
        cats    = exp_cfg.get("categories", [])
        sources = exp_cfg.get("sources", ["_Purch_MN_7D"])
        cols = [f"{cat}{src}" for cat in cats for src in sources]
        return [c for c in cols if c in self.df.columns]

    def _check_missing(self):
        """Override: flag only when ALL expenditure cols are missing (partial is OK)."""
        cols = self._get_expense_cols()
        if not cols:
            self.df[self._f_missing] = 0
            return
        all_missing = self.df[cols].isnull().all(axis=1)
        self.df[self._f_missing] = all_missing.astype(int)
        for idx in self.df.index[all_missing]:
            self._append_narrative(idx, f"All {self.NAME} expenditure columns are missing")

    def _check_erroneous(self):
        """Flag any negative expenditure value."""
        cols = self._get_expense_cols()
        if not cols:
            self.df[self._f_erroneous] = 0
            return
        not_missing = self.df[self._f_missing] == 0
        has_negative = (self.df[cols] < 0).any(axis=1)
        self.df[self._f_erroneous] = np.nan
        self.df.loc[not_missing, self._f_erroneous] = has_negative[not_missing].astype(int)
        for idx in self.df.index[has_negative & not_missing]:
            neg_cols = [c for c in cols if self.df.at[idx, c] < 0]
            self._append_narrative(idx, f"Negative expenditure: {', '.join(neg_cols)}")

    def _run_specific_checks(self):
        cols = self._get_expense_cols()
        if not cols:
            self.log.warning(f"No {self.NAME} columns found in dataset — skipping")
            return

        # ── Zero total expenditure ────────────────────────────────────────────
        if self.cfg.get("flag_zero_total_food", True):
            zero_total = (self.df[cols].fillna(0) == 0).all(axis=1)
            self._add_flag(
                f"Flag_{self.NAME}_ZeroTotal",
                zero_total,
                f"All {self.NAME} expenditure values are zero",
            )

        # ── Below minimum meaningful price ────────────────────────────────────
        min_price = self.cfg.get("min_item_price", 0)
        if min_price > 0:
            num_df = self.df[cols].apply(pd.to_numeric, errors="coerce")
            below_min = ((num_df > 0) & (num_df < min_price)).any(axis=1)
            self._add_flag(
                f"Flag_{self.NAME}_BelowMinPrice",
                below_min,
                f"At least one {self.NAME} item is > 0 but < {min_price:,} "
                f"(below minimum meaningful price — possible entry error)",
            )
            # Narrative: name the specific offending column(s) and value(s)
            good_rows = (self.df[self._f_missing] == 0) & (self.df[self._f_erroneous] == 0)
            for idx in self.df.index[below_min & good_rows]:
                bad = {
                    c: round(float(num_df.at[idx, c]), 2)
                    for c in cols
                    if 0 < num_df.at[idx, c] < min_price
                }
                detail = ", ".join(f"{c}={v:,}" for c, v in bad.items())
                self._append_narrative(
                    idx,
                    f"Item(s) below min price ({min_price:,}): {detail}",
                )

        # ── Extreme single item ───────────────────────────────────────────────
        max_val = self.cfg.get(self._MAX_CFG_KEY, 1_000_000)
        extreme = (self.df[cols] > max_val).any(axis=1)
        self._add_flag(
            f"Flag_{self.NAME}_ExtremeItem",
            extreme,
            f"At least one {self.NAME} item > {max_val:,} (possible entry error)",
        )


class HHExpFIndicator(_HHExpBase):
    NAME = "HHExpF"
    _MODULE_KEY = "food_7d"
    _MAX_CFG_KEY = "max_single_item_food_7d"


class HHExpNF1MIndicator(_HHExpBase):
    NAME = "HHExpNF1M"
    _MODULE_KEY = "nonfood_1m"
    _MAX_CFG_KEY = "max_single_item_nonfood_1m"


class HHExpNF6MIndicator(_HHExpBase):
    NAME = "HHExpNF6M"
    _MODULE_KEY = "nonfood_6m"
    _MAX_CFG_KEY = "max_single_item_nonfood_6m"
