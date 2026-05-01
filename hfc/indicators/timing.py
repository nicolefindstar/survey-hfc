"""
Timing — Interview duration and start-time plausibility

Checks:
  Sequential : Missing start/end, end < start (erroneous)
  Independent:
    InvalidDuration — duration ≤ 0 min
    ShortDuration   — duration < short_duration_min
    LongDuration    — duration > long_duration_min
    AbnormalStart   — interview started before early-morning threshold or after evening threshold
"""

import pandas as pd
import numpy as np

from .base import BaseIndicator


class TimingIndicator(BaseIndicator):
    NAME = "Timing"

    def _check_erroneous(self):
        """Flag records where end is before start (overrides generic range check)."""
        not_missing = self.df[self._f_missing] == 0
        self.df[self._f_erroneous] = np.nan

        if "start" not in self.df.columns or "end" not in self.df.columns:
            self.df.loc[not_missing, self._f_erroneous] = 0
            return

        bad_order = self.df["end"] < self.df["start"]
        self.df.loc[not_missing, self._f_erroneous] = bad_order[not_missing].astype(int)
        for idx in self.df.index[bad_order & not_missing]:
            self._append_narrative(idx, "Interview end timestamp is before start timestamp")

    def _run_specific_checks(self):
        if "start" not in self.df.columns or "end" not in self.df.columns:
            self.log.warning("start/end columns not found — skipping timing checks")
            return

        cfg = self.cfg
        utc_offset = cfg.get("utc_offset_hours", 0)

        # Duration in minutes
        self.df["Timing_Duration_Min"] = (
            (self.df["end"] - self.df["start"]).dt.total_seconds() / 60
        )

        # Local start hour
        self.df["Timing_StartHour"] = (
            self.df["start"].dt.tz_convert("UTC").dt.hour + utc_offset
        ) % 24

        # ── Invalid duration (≤ 0) ────────────────────────────────────────────
        invalid_min = cfg.get("invalid_duration_min", 0)
        self._add_flag(
            "Flag_Timing_InvalidDuration",
            self.df["Timing_Duration_Min"] <= invalid_min,
            f"Duration ≤ {invalid_min} minutes (invalid)",
        )

        # ── Short duration ────────────────────────────────────────────────────
        short_min = cfg.get("short_duration_min", 10)
        eligible_short = self.df["Timing_Duration_Min"] > invalid_min
        self.df["Flag_Timing_ShortDuration"] = np.nan
        good_rows = (self.df[self._f_missing] == 0) & (self.df[self._f_erroneous] == 0)
        mask = good_rows & eligible_short & (self.df["Timing_Duration_Min"] < short_min)
        self.df.loc[good_rows & eligible_short, "Flag_Timing_ShortDuration"] = 0
        self.df.loc[mask, "Flag_Timing_ShortDuration"] = 1
        for idx in self.df.index[mask]:
            dur = round(self.df.at[idx, "Timing_Duration_Min"], 1)
            self._append_narrative(idx, f"Short interview: {dur} min (< {short_min} min)")

        # ── Long duration ─────────────────────────────────────────────────────
        long_min = cfg.get("long_duration_min", 120)
        self._add_flag(
            "Flag_Timing_LongDuration",
            self.df["Timing_Duration_Min"] > long_min,
            f"Long interview: > {long_min} minutes",
        )

        # ── Abnormal start hour ───────────────────────────────────────────────
        early_end = cfg.get("abnormal_early_morning_end", 7)
        evening_start = cfg.get("abnormal_evening_start", 19)
        h = self.df["Timing_StartHour"]
        abnormal = (h < early_end) | (h >= evening_start)
        self._add_flag(
            "Flag_Timing_AbnormalHour",
            abnormal,
            f"Interview started at abnormal hour (before {early_end}:00 or after {evening_start}:00)",
        )
