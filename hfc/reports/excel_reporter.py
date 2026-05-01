"""
Excel report generator.

Output workbook structure:
  Summary       — one row per indicator: record count, flagged count, flag rate, check breakdown
  MasterSheet   — one row per flagged household across ALL indicators
  <Indicator>   — one sheet per indicator (flagged records only)
"""

import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ── Colour palette (openpyxl hex, no leading #) ───────────────────────────────
_RED    = "FFCCCC"
_ORANGE = "FFE5CC"
_YELLOW = "FFFACC"
_GREEN  = "CCFFCC"
_BLUE   = "CCE5FF"
_GREY   = "F0F0F0"
_WHITE  = "FFFFFF"
_HEADER = "1F4E79"   # dark blue for header text
_HEADER_FONT_COLOR = "FFFFFF"


class ExcelReporter:
    def __init__(self, output_path: str = "hfc_report.xlsx"):
        self.output_path = output_path

    def generate(self, results: dict[str, pd.DataFrame], raw_df: pd.DataFrame):
        """
        Parameters
        ----------
        results : dict mapping indicator name → output DataFrame from indicator.run()
        raw_df  : original full dataset (used for MasterSheet join)
        """
        with pd.ExcelWriter(self.output_path, engine="xlsxwriter") as writer:
            wb = writer.book

            # Formats
            fmt = self._make_formats(wb)

            # ── Summary sheet ─────────────────────────────────────────────────
            summary_df = self._build_summary(results)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            self._style_summary(writer.sheets["Summary"], summary_df, fmt)

            # ── MasterSheet ───────────────────────────────────────────────────
            master_df = self._build_mastersheet(results, raw_df)
            master_df.to_excel(writer, sheet_name="MasterSheet", index=False)
            self._style_sheet(writer.sheets["MasterSheet"], master_df, fmt, max_col_width=60)

            # ── Per-indicator sheets ───────────────────────────────────────────
            for name, df in results.items():
                overall_col = f"Flag_{name}_Overall"
                if overall_col not in df.columns:
                    flagged = df
                else:
                    flagged = df[df[overall_col] == 1].copy()

                sheet_name = name[:31]   # Excel limit
                if flagged.empty:
                    pd.DataFrame({"Message": [f"No flags raised for {name}"]}).to_excel(
                        writer, sheet_name=sheet_name, index=False
                    )
                else:
                    flagged.to_excel(writer, sheet_name=sheet_name, index=False)
                    self._style_sheet(writer.sheets[sheet_name], flagged, fmt)

        logger.info(f"Report written to {self.output_path}")

    # ── Summary helpers ────────────────────────────────────────────────────────

    def _build_summary(self, results: dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows = []
        for name, df in results.items():
            overall = f"Flag_{name}_Overall"
            n_total   = len(df)
            n_flagged = int((df[overall] == 1).sum()) if overall in df.columns else 0
            rate      = round(n_flagged / n_total * 100, 1) if n_total else 0

            check_cols = [c for c in df.columns
                          if c.startswith(f"Flag_{name}_")
                          and c not in (overall, f"Flag_{name}_Narrative")]
            check_summary = {c: int((df[c] == 1).sum()) for c in check_cols}
            checks_str = " | ".join(f"{c.replace(f'Flag_{name}_','')}: {v}" for c, v in check_summary.items())

            rows.append({
                "Indicator":         name,
                "Total Records":     n_total,
                "Flagged Records":   n_flagged,
                "Flag Rate (%)":     rate,
                "Check Breakdown":   checks_str,
                "Run Timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        return pd.DataFrame(rows)

    # ── MasterSheet helpers ────────────────────────────────────────────────────

    def _build_mastersheet(
        self, results: dict[str, pd.DataFrame], raw_df: pd.DataFrame
    ) -> pd.DataFrame:
        """One row per HH that has at least one flag. Columns: base + one narrative per indicator."""
        id_col = "_uuid" if "_uuid" in raw_df.columns else raw_df.columns[0]

        narrative_parts: dict = {}  # id → list of "Indicator: narrative"
        flagged_ids: set = set()

        for name, df in results.items():
            overall = f"Flag_{name}_Overall"
            narr    = f"Flag_{name}_Narrative"
            if overall not in df.columns:
                continue
            flagged_rows = df[df[overall] == 1]
            if id_col not in df.columns:
                continue
            for _, row in flagged_rows.iterrows():
                uid = row[id_col]
                flagged_ids.add(uid)
                text = row.get(narr, "")
                narrative_parts.setdefault(uid, []).append(f"[{name}] {text}")

        if not flagged_ids:
            return pd.DataFrame({"Note": ["No flagged records across all indicators"]})

        base_cols = [c for c in ["_uuid", "EnuName", "EnuSupervisorName",
                                  "ADMIN1Name", "ADMIN2Name", "today"] if c in raw_df.columns]
        master = raw_df[raw_df[id_col].isin(flagged_ids)][base_cols].copy()

        # Overall narrative
        master["Flag_All_Narrative"] = master[id_col].map(
            lambda uid: " || ".join(narrative_parts.get(uid, []))
        )

        # One column per indicator showing its narrative
        for name, df in results.items():
            narr = f"Flag_{name}_Narrative"
            overall = f"Flag_{name}_Overall"
            if id_col not in df.columns or overall not in df.columns:
                continue
            narr_map = df.set_index(id_col)[narr].to_dict() if narr in df.columns else {}
            flag_map = df.set_index(id_col)[overall].to_dict()
            master[f"{name}_Flag"] = master[id_col].map(lambda u, fm=flag_map: fm.get(u, 0))
            master[f"{name}_Issues"] = master[id_col].map(lambda u, nm=narr_map: nm.get(u, ""))

        return master.reset_index(drop=True)

    # ── Styling helpers ────────────────────────────────────────────────────────

    def _make_formats(self, wb) -> dict:
        def fmt(**kw):
            return wb.add_format(kw)

        return {
            "header":    fmt(bold=True, bg_color=_HEADER, font_color=_HEADER_FONT_COLOR,
                              border=1, text_wrap=True, valign="vcenter", align="center"),
            "flag_yes":  fmt(bg_color=_RED,    border=1),
            "flag_no":   fmt(bg_color=_GREEN,  border=1),
            "flag_na":   fmt(bg_color=_GREY,   border=1, italic=True),
            "cell":      fmt(border=1, text_wrap=True, valign="top"),
            "cell_wrap": fmt(border=1, text_wrap=True, valign="top"),
            "rate_high": fmt(bg_color=_RED,    border=1, bold=True),
            "rate_med":  fmt(bg_color=_ORANGE, border=1),
            "rate_low":  fmt(bg_color=_YELLOW, border=1),
            "rate_ok":   fmt(bg_color=_GREEN,  border=1),
        }

    def _style_summary(self, ws, df: pd.DataFrame, fmt: dict):
        for col_idx, col in enumerate(df.columns):
            ws.write(0, col_idx, col, fmt["header"])
        ws.set_row(0, 30)
        ws.set_column(0, 0, 18)
        ws.set_column(1, 3, 16)
        ws.set_column(4, 4, 80)
        ws.set_column(5, 5, 22)

        for enum_idx, (_, row) in enumerate(df.iterrows()):
            ri = enum_idx + 1
            rate = row.get("Flag Rate (%)", 0)
            rate_fmt = (fmt["rate_high"] if rate > 20
                        else fmt["rate_med"] if rate > 10
                        else fmt["rate_low"] if rate > 5
                        else fmt["rate_ok"])
            for col_idx, val in enumerate(row):
                cell_fmt = rate_fmt if df.columns[col_idx] == "Flag Rate (%)" else fmt["cell"]
                ws.write(ri, col_idx, val, cell_fmt)

    def _style_sheet(self, ws, df: pd.DataFrame, fmt: dict, max_col_width: int = 40):
        for col_idx, col in enumerate(df.columns):
            ws.write(0, col_idx, col, fmt["header"])
            width = min(max(len(str(col)) + 2, 12), max_col_width)
            ws.set_column(col_idx, col_idx, width)
        ws.set_row(0, 25)
        ws.freeze_panes(1, 0)

        for enum_idx, (_, row) in enumerate(df.iterrows()):
            ri = enum_idx + 1
            for col_idx, val in enumerate(row):
                col_name = df.columns[col_idx]
                if col_name.startswith("Flag_") and col_name.endswith(
                    ("_Missing", "_Erroneous", "_Overall",
                     "_Identical", "_Low", "_High", "_LowStaple",
                     "_ZeroWithPoorFCG", "_HighWithAcceptFCG",
                     "_HighHHSize", "_SumMismatch", "_NoAdults", "_PLWExceeds",
                     "_DisplacedOwner", "_ChildStratNoChildren", "_AllNA_PoorFood",
                     "_NonSequential", "_ManyNA", "_ZeroTotal", "_ExtremeItem",
                     "_InvalidDuration", "_ShortDuration", "_LongDuration", "_AbnormalHour",
                     "_AdultMealNoChildren",
                     )
                ):
                    if val == 1:
                        cell_fmt = fmt["flag_yes"]
                    elif val == 0:
                        cell_fmt = fmt["flag_no"]
                    else:
                        cell_fmt = fmt["flag_na"]
                else:
                    cell_fmt = fmt["cell_wrap"]
                ws.write(ri, col_idx, "" if pd.isna(val) else val, cell_fmt)
