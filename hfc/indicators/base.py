"""
BaseIndicator — shared scaffolding for every WFP food-security check.

Check execution order (matches IPA / DataQualityChecks-main convention):
  1. Sequential — missing values          → sets Flag_<X>_Missing
  2. Sequential — erroneous values        → sets Flag_<X>_Erroneous
  3. Independent — indicator-specific     → sets Flag_<X>_<CheckName>
     (steps 1-2 must both be 0 for step 3 to evaluate; otherwise NaN)
  4. Overall rollup                        → sets Flag_<X>_Overall = 1 if any flag == 1
  5. Narrative                             → human-readable summary
"""

import logging
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class BaseIndicator(ABC):
    NAME: str = ""  # Override in subclasses (e.g. 'FCS')

    def __init__(
        self,
        df: pd.DataFrame,
        std_config: dict,
        cfg_config: dict,
        base_config: dict,
    ):
        self.df = df.copy()
        self.std = std_config
        self.cfg = cfg_config
        self.base_cols = base_config.get("base_columns", [])
        self.log = logging.getLogger(f"hfc.{self.NAME}")

        self._f_missing   = f"Flag_{self.NAME}_Missing"
        self._f_erroneous = f"Flag_{self.NAME}_Erroneous"
        self._f_overall   = f"Flag_{self.NAME}_Overall"
        self._f_narrative = f"Flag_{self.NAME}_Narrative"

        self.df[self._f_narrative] = ""

    # ── public entry-point ─────────────────────────────────────────────────────

    def run(self) -> pd.DataFrame:
        self._parse_columns()
        self._check_missing()
        self._check_erroneous()
        self._run_specific_checks()
        self._compute_overall()
        self._finalise_narrative()
        return self._build_output()

    # ── sequential checks ──────────────────────────────────────────────────────

    def _parse_columns(self):
        for col, spec in self.std.get("columns", {}).items():
            if col not in self.df.columns:
                continue
            dtype = spec.get("type", "float")
            try:
                if dtype in ("int", "integer", "float"):
                    self.df[col] = pd.to_numeric(self.df[col], errors="coerce")
                elif dtype == "str":
                    self.df[col] = self.df[col].astype(str).replace("nan", np.nan)
                elif dtype == "datetime":
                    self.df[col] = pd.to_datetime(self.df[col], errors="coerce", utc=True)
                elif dtype == "date":
                    self.df[col] = pd.to_datetime(self.df[col], errors="coerce").dt.date
            except Exception as exc:
                self.log.warning(f"Cannot parse {col} as {dtype}: {exc}")

    def _check_missing(self):
        col_specs = self.std.get("columns", {})
        required = [
            c for c, s in col_specs.items()
            if s.get("required", True) and c in self.df.columns
        ]

        if not required:
            self.df[self._f_missing] = 0
            return

        is_missing = self.df[required].isnull().any(axis=1)
        self.df[self._f_missing] = is_missing.astype(int)

        for idx in self.df.index[is_missing]:
            cols = [c for c in required if pd.isnull(self.df.at[idx, c])]
            self._append_narrative(idx, f"Missing: {', '.join(cols)}")

    def _check_erroneous(self):
        col_specs = self.std.get("columns", {})
        not_missing = self.df[self._f_missing] == 0

        erroneous = pd.Series(False, index=self.df.index)
        details: dict[int, list[str]] = {i: [] for i in self.df.index}

        for col, spec in col_specs.items():
            if col not in self.df.columns:
                continue
            col_bad = pd.Series(False, index=self.df.index)
            if "min" in spec:
                col_bad |= self.df[col] < spec["min"]
            if "max" in spec:
                col_bad |= self.df[col] > spec["max"]
            if "choices" in spec:
                col_bad |= ~self.df[col].isin(spec["choices"]) & self.df[col].notna()

            col_bad = col_bad & not_missing
            erroneous |= col_bad
            for idx in self.df.index[col_bad]:
                details[idx].append(f"{col}={self.df.at[idx, col]}")

        self.df[self._f_erroneous] = np.nan
        self.df.loc[not_missing, self._f_erroneous] = erroneous[not_missing].astype(int)

        for idx in self.df.index[erroneous & not_missing]:
            self._append_narrative(idx, f"Erroneous: {', '.join(details[idx])}")

    # ── independent specific checks (override in subclasses) ──────────────────

    @abstractmethod
    def _run_specific_checks(self):
        pass

    # ── helper for adding named check flags ───────────────────────────────────

    def _add_flag(self, flag_col: str, condition: pd.Series, message: str):
        """
        Register a named check flag.  Only evaluated for rows that passed
        both sequential checks (missing=0 AND erroneous=0).
        """
        eligible = (self.df[self._f_missing] == 0) & (self.df[self._f_erroneous] == 0)
        self.df[flag_col] = np.nan
        self.df.loc[eligible, flag_col] = condition[eligible].astype(int)
        for idx in self.df.index[eligible & condition]:
            self._append_narrative(idx, message)

    def _append_narrative(self, idx, text: str):
        existing = self.df.at[idx, self._f_narrative]
        self.df.at[idx, self._f_narrative] = (existing + text + "; ") if existing else (text + "; ")

    # ── rollup ─────────────────────────────────────────────────────────────────

    def _compute_overall(self):
        flag_cols = [
            c for c in self.df.columns
            if c.startswith(f"Flag_{self.NAME}_")
            and c not in (self._f_overall, self._f_narrative)
        ]
        any_flag = pd.Series(False, index=self.df.index)
        for c in flag_cols:
            any_flag |= self.df[c] == 1
        self.df[self._f_overall] = any_flag.astype(int)

    def _finalise_narrative(self):
        clean = self.df[self._f_narrative].str.rstrip("; ")
        self.df[self._f_narrative] = clean.where(clean != "", "No issues detected")

    # ── output assembly ────────────────────────────────────────────────────────

    def _build_output(self) -> pd.DataFrame:
        flag_cols = [c for c in self.df.columns if c.startswith(f"Flag_{self.NAME}_")]
        computed = [c for c in self.df.columns if c.startswith(f"{self.NAME}_") or c in ("FCS", "FCG", "rCSI", "HDDS")]
        base = [c for c in self.base_cols if c in self.df.columns]
        cols = base + sorted(set(computed), key=lambda x: self.df.columns.get_loc(x)) + flag_cols
        # deduplicate while preserving order
        seen, out = set(), []
        for c in cols:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return self.df[out].copy()
