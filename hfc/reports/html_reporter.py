"""
HTML Report Generator — manager/supervisor summary.

Produces a single self-contained HTML file (no CDN, no internet required).
Charts are rendered as CSS-only horizontal bars.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# ── colour helpers — mirrors XLSForm Reviewer palette ─────────────────────────

def _rate_bg(rate: float) -> str:
    if rate > 20: return "#fdf0f0"
    if rate > 10: return "#fdf5ee"
    if rate > 0:  return "#fdf8e8"
    return "#e8f6f0"

def _rate_color(rate: float) -> str:
    if rate > 20: return "#cc8080"
    if rate > 10: return "#cc9470"
    if rate > 0:  return "#ccb460"
    return "#6aab90"

def _rate_label(rate: float) -> str:
    if rate > 20: return "Critical"
    if rate > 10: return "High"
    if rate > 0:  return "Medium"
    return "OK"

def _fcg_color(fcg: str) -> str:
    return {"Poor": "#cc8080", "Borderline": "#ccb460", "Acceptable": "#6aab90"}.get(fcg, "#94a3b8")

def _css_bar(pct: float, color: str = "#6a9cc8", width: int = 160) -> str:
    filled = max(0, min(100, pct))
    return (
        f'<div style="display:inline-block;vertical-align:middle;'
        f'background:#e8edf2;border-radius:4px;width:{width}px;height:10px;overflow:hidden;">'
        f'<div style="width:{filled:.1f}%;height:100%;background:{color};border-radius:4px;"></div>'
        f'</div>'
    )


# ── Flag catalogue — (indicator, check_name) → (description, action, severity) ──
# severity: "critical" | "warn" | "info"
#
# Descriptions explain *what the flag means* for a field supervisor.
# Actions give *concrete next steps*.

_FLAG_DESC: dict[tuple[str, str], tuple[str, str, str]] = {
    # ── Timing ────────────────────────────────────────────────────────────────
    ("Timing", "LongDuration"): (
        "Interview duration is unusually long (>2× median) — may indicate distraction, GPS recording left open, or a very complex household.",
        "Review the timestamp log for these surveys. Contact the enumerator to confirm whether the interview was genuinely long or the device was left running.",
        "warn",
    ),
    ("Timing", "ShortDuration"): (
        "Interview completed too quickly — responses may have been rushed, skipped, or fabricated without speaking to the household.",
        "Flag for spot-check. Re-interview a sample of these households independently to verify responses. Retrain the enumerator if confirmed.",
        "critical",
    ),
    ("Timing", "AbnormalHour"): (
        "Survey was recorded outside expected working hours (before 6 am or after 8 pm) — may indicate backdating or timestamp manipulation.",
        "Check GPS coordinates and submission timestamps. Ask the enumerator to explain; escalate if the location does not match the reported area.",
        "warn",
    ),
    ("Timing", "Identical"): (
        "Two or more surveys share an identical submission timestamp — physically impossible if interviews were conducted separately.",
        "Investigate for copy-paste duplication or batch upload without actual interviewing. Compare household IDs and response patterns.",
        "critical",
    ),
    # ── FCS ───────────────────────────────────────────────────────────────────
    ("FCS", "Low"): (
        "FCS score is very low (≤21 — 'Poor' threshold) — household is in crisis-level food consumption.",
        "Cross-check with rCSI and LCS responses to confirm severity. Verify that low scores reflect genuine food insecurity and were not caused by skip errors.",
        "warn",
    ),
    ("FCS", "LowStaple"): (
        "Cereals/staples were consumed 0 days in the past week — extremely rare and nutritionally implausible in most contexts.",
        "Confirm with the enumerator whether the household genuinely consumed no staples or whether the question was skipped in error. Retrain on FCS food group definitions.",
        "warn",
    ),
    ("FCS", "Identical"): (
        "All FCS food group frequency values are identical (e.g., all scored 3/7) — a strong sign of response anchoring or fabrication.",
        "Compare paper forms if available. Conduct an independent spot-check interview with this household and discuss the pattern with the enumerator.",
        "critical",
    ),
    ("FCS", "AllZero"): (
        "All FCS components are zero — the household reportedly consumed nothing across all food groups in the past week.",
        "Almost certainly a data entry or skip-logic error. Re-interview the household or contact the enumerator immediately.",
        "critical",
    ),
    ("FCS", "OutOfRange"): (
        "One or more FCS frequency values fall outside the valid 0–7 day range.",
        "Correct the value if the enumerator can confirm the true response; otherwise mark as missing and exclude from scoring.",
        "critical",
    ),
    ("FCS", "Missing"): (
        "One or more FCS food group fields have no response recorded.",
        "Contact the enumerator to supply the missing answer. If unrecoverable, document as missing and exclude the record from FCS analysis.",
        "warn",
    ),
    # ── rCSI ──────────────────────────────────────────────────────────────────
    ("rCSI", "AdultMealNoChildren"): (
        "The 'Restrict adults so children can eat' strategy was recorded, but the household has no children — logically inconsistent.",
        "Verify household composition in the demographic section. If the child count is wrong, correct the roster. If the strategy response is wrong, clarify with the enumerator.",
        "warn",
    ),
    ("rCSI", "ZeroWithPoorFCG"): (
        "rCSI = 0 (no coping strategies used) but the household is classified as Poor food security — a direct contradiction.",
        "Re-examine both the FCS and rCSI sections with the enumerator. One of the two is likely erroneous. This combination should not occur under normal circumstances.",
        "critical",
    ),
    ("rCSI", "Identical"): (
        "All rCSI strategy frequency values are identical — consistent with anchoring or copy-paste data entry.",
        "Conduct a spot-check re-interview. Compare against paper forms. Discuss the pattern in the next team debrief.",
        "critical",
    ),
    ("rCSI", "OutOfRange"): (
        "One or more rCSI frequency values are outside the valid 0–7 day range.",
        "Correct or mark as missing. Recheck the data entry process for this enumerator.",
        "critical",
    ),
    ("rCSI", "Missing"): (
        "One or more rCSI strategy fields have no response recorded.",
        "Contact the enumerator for the missing values. If unrecoverable, exclude the record from rCSI analysis.",
        "warn",
    ),
    # ── LCS ───────────────────────────────────────────────────────────────────
    ("LCS", "ManyNA"): (
        "≥3 LCS strategies are marked 'Not Applicable' — the enumerator may be systematically skipping strategies rather than asking each question.",
        "Review the N/A rate by enumerator in the Indicator Breakdown tab. Retrain on LCS administration: N/A should only be selected when the household genuinely has no access to the strategy. For emergency strategies (begging, migration, child labour) N/A is never valid.",
        "warn",
    ),
    ("LCS", "NonSequential"): (
        "An emergency-tier strategy is reported as applied but no stress or crisis strategy was used first — contradicts the expected progression of coping behaviour.",
        "Verify with the enumerator whether the household was actually asked all three tiers. Check ODK/KoBoToolbox skip logic to confirm the question routing is correct.",
        "warn",
    ),
    ("LCS", "AllNA_PoorFood"): (
        "All LCS strategies are marked N/A despite the household being in the Poor food consumption group — a strong contradiction.",
        "Escalate to field supervisor for immediate re-interview. This combination is highly unlikely and suggests either the FCS or LCS data is compromised.",
        "critical",
    ),
    ("LCS", "ChildStratNoChildren"): (
        "A child-specific coping strategy (e.g., child labour) is reported but the household has zero children.",
        "Check the household demographic roster for errors in child count. If the roster is correct, clarify the LCS response with the enumerator.",
        "warn",
    ),
    ("LCS", "Missing"): (
        "One or more LCS strategy fields have no response recorded.",
        "Contact the enumerator to supply missing responses. Check whether skip logic is routing questions incorrectly.",
        "warn",
    ),
    # ── Demographics ──────────────────────────────────────────────────────────
    ("Demo", "SumMismatch"): (
        "The sum of age/sex disaggregated roster members does not match the reported total household size — a very common entry error.",
        "Ask the enumerator to recount and correct the roster. Confirm whether the discrepancy is due to a missing row or a miscounted total. Retrain on household roster completion.",
        "warn",
    ),
    ("Demo", "Missing"): (
        "A required demographic field (e.g., household size, head of household sex) is missing.",
        "Contact the enumerator to complete the missing fields. Check whether the questionnaire has a mandatory response constraint.",
        "warn",
    ),
    # ── Housing ───────────────────────────────────────────────────────────────
    ("Housing", "DisplacedOwner"): (
        "Household is registered as displaced but also reports owning the dwelling — contradictory tenure status.",
        "Clarify displacement classification with the enumerator: a displaced household may own property elsewhere. Update the tenure or displacement status as appropriate.",
        "warn",
    ),
    ("Housing", "Missing"): (
        "A required housing field has no response recorded.",
        "Contact the enumerator for the missing housing response.",
        "warn",
    ),
    # ── HHExpF ────────────────────────────────────────────────────────────────
    ("HHExpF", "ExtremeItem"): (
        "A single food expenditure item is an extreme statistical outlier — likely a transcription error (e.g., missing decimal point, wrong currency unit).",
        "Contact the enumerator to verify the amount. Correct or exclude the value before computing food expenditure aggregates.",
        "warn",
    ),
    ("HHExpF", "Missing"): (
        "One or more food expenditure fields are missing.",
        "Contact the enumerator for the missing expenditure data.",
        "warn",
    ),
    # ── HDDS ──────────────────────────────────────────────────────────────────
    ("HDDS", "Low"): (
        "HDDS score is very low (≤3 food groups) — the household consumed fewer than 4 distinct food groups in the past 24 hours.",
        "Cross-check with FCS to confirm dietary diversity deprivation. Verify that the enumerator probed all food groups correctly.",
        "warn",
    ),
    ("HDDS", "Missing"): (
        "One or more HDDS food group fields are missing.",
        "Contact the enumerator for missing dietary diversity responses.",
        "warn",
    ),
    # ── HHS ───────────────────────────────────────────────────────────────────
    ("HHS", "Inconsistent"): (
        "HHS hunger frequency response is inconsistent with the derived severity category.",
        "Review HHS encoding and confirm that the correct frequency option was selected. Check ODK constraint logic.",
        "warn",
    ),
    ("HHS", "Missing"): (
        "One or more HHS hunger severity fields are missing.",
        "Contact the enumerator for missing hunger severity data.",
        "warn",
    ),
}

# Severity display config
_SEV_CONFIG = {
    "critical": {"border": "#cc8080", "bg": "#fdf0f0", "badge_bg": "#fbeaea",
                 "badge_color": "#cc8080", "icon": "🔴", "label": "Critical"},
    "warn":     {"border": "#cc9470", "bg": "#fdf5ee", "badge_bg": "#fdf0e4",
                 "badge_color": "#cc9470", "icon": "🟡", "label": "High"},
    "info":     {"border": "#6a9cc8", "bg": "#f0f6fc", "badge_bg": "#e4eef8",
                 "badge_color": "#6a9cc8", "icon": "🔵", "label": "Medium"},
}


def _lookup_flag(indicator: str, check: str) -> tuple[str, str, str]:
    """Return (description, action, severity) for a flag, with a generic fallback."""
    key = (indicator, check)
    if key in _FLAG_DESC:
        return _FLAG_DESC[key]
    # Generic fallback
    desc = f"Flag '{check}' was triggered for the {indicator} indicator."
    action = "Review flagged records in the Data Quality tab and follow up with the relevant enumerator."
    return desc, action, "info"


# ── statistics computation ─────────────────────────────────────────────────────

def compute_stats(results: dict[str, pd.DataFrame], working_df: pd.DataFrame) -> dict:
    n = len(working_df)

    # Date range
    date_col = next((c for c in ("today", "date", "SubmissionDate") if c in working_df.columns), None)
    if date_col:
        dates = pd.to_datetime(working_df[date_col], errors="coerce").dropna()
        date_min = dates.min().strftime("%d %b %Y") if not dates.empty else "N/A"
        date_max = dates.max().strftime("%d %b %Y") if not dates.empty else "N/A"
        date_range = f"{date_min} – {date_max}"
        days_active = (dates.max() - dates.min()).days + 1 if not dates.empty else 0
    else:
        date_range, days_active = "N/A", 0

    # Enumerators
    enu_col = next((c for c in ("EnuName", "enumerator", "interviewer") if c in working_df.columns), None)
    n_enumerators = working_df[enu_col].nunique() if enu_col else 0

    # Admin areas
    admin_col = next((c for c in ("ADMIN1Name", "admin1", "region") if c in working_df.columns), None)
    n_admin = working_df[admin_col].nunique() if admin_col else 0

    # Per-indicator flag summary
    flag_rows = []
    all_flagged_ids = set()
    id_col = "_uuid" if "_uuid" in working_df.columns else (working_df.columns[0] if len(working_df) else None)

    for name, res in results.items():
        overall = f"Flag_{name}_Overall"
        narr    = f"Flag_{name}_Narrative"
        if overall not in res.columns:
            continue
        flagged_mask = res[overall] == 1
        flagged_n    = int(flagged_mask.sum())
        rate         = round(flagged_n / n * 100, 1) if n else 0

        # Track individual checks
        check_cols = [c for c in res.columns
                      if c.startswith(f"Flag_{name}_")
                      and c not in (overall, narr)]
        checks = {c.replace(f"Flag_{name}_", ""): int((res[c] == 1).sum()) for c in check_cols}

        # Collect flagged IDs
        if id_col and id_col in res.columns:
            all_flagged_ids.update(res.loc[flagged_mask, id_col].tolist())

        flag_rows.append({
            "indicator": name, "total": n, "flagged": flagged_n,
            "rate": rate, "checks": checks,
        })

    # FCS distribution
    fcs_dist = {}
    if "FCG" in working_df.columns:
        vc = working_df["FCG"].value_counts()
        for label in ("Poor", "Borderline", "Acceptable"):
            fcs_dist[label] = int(vc.get(label, 0))
    fcs_mean = (round(float(pd.to_numeric(working_df["FCS"], errors="coerce").mean()), 1)
                if "FCS" in working_df.columns else None)

    # rCSI distribution (Low ≤3 / Medium 4–18 / High ≥19)
    rcsi_dist = {}
    rcsi_mean = None
    if "rCSI" in working_df.columns:
        rcsi_s = pd.to_numeric(working_df["rCSI"], errors="coerce").dropna()
        rcsi_mean = round(float(rcsi_s.mean()), 1) if not rcsi_s.empty else None
        rcsi_dist = {
            "Low (≤3)":    int((rcsi_s <= 3).sum()),
            "Medium (4–18)": int(((rcsi_s >= 4) & (rcsi_s <= 18)).sum()),
            "High (≥19)":  int((rcsi_s >= 19).sum()),
        }

    # HDDS distribution (Low ≤3 / Medium 4–6 / High ≥7)
    hdds_dist = {}
    hdds_mean = None
    if "HDDS" in working_df.columns:
        hdds_s = pd.to_numeric(working_df["HDDS"], errors="coerce").dropna()
        hdds_mean = round(float(hdds_s.mean()), 1) if not hdds_s.empty else None
        hdds_dist = {
            "Low (≤3)":    int((hdds_s <= 3).sum()),
            "Medium (4–6)": int(((hdds_s >= 4) & (hdds_s <= 6)).sum()),
            "High (≥7)":   int((hdds_s >= 7).sum()),
        }

    # Per-enumerator flag summary
    enu_rows = []
    if enu_col:
        for enu, grp in working_df.groupby(enu_col):
            enu_ids = set(grp[id_col].tolist()) if id_col else set()
            enu_flagged = len(enu_ids & all_flagged_ids)
            enu_n = len(grp)
            enu_rows.append({
                "enumerator": str(enu),
                "surveys": enu_n,
                "flagged": enu_flagged,
                "rate": round(enu_flagged / enu_n * 100, 1) if enu_n else 0,
            })
        enu_rows.sort(key=lambda r: r["rate"], reverse=True)

    # Survey timeline (records per day)
    timeline = []
    if date_col:
        daily = working_df.groupby(
            pd.to_datetime(working_df[date_col], errors="coerce").dt.date
        ).size().reset_index()
        daily.columns = ["date", "count"]
        timeline = daily.sort_values("date").to_dict("records")

    # Admin area breakdown
    admin_rows = []
    if admin_col:
        for area, grp in working_df.groupby(admin_col):
            area_ids = set(grp[id_col].tolist()) if id_col else set()
            area_flagged = len(area_ids & all_flagged_ids)
            area_n = len(grp)
            admin_rows.append({
                "area": str(area), "surveys": area_n,
                "flagged": area_flagged,
                "rate": round(area_flagged / area_n * 100, 1) if area_n else 0,
            })
        admin_rows.sort(key=lambda r: r["rate"], reverse=True)

    # Interview duration
    dur_col = "Timing_Duration_Min"
    dur_mean = (round(float(pd.to_numeric(working_df[dur_col], errors="coerce").mean()), 1)
                if dur_col in working_df.columns else None)
    dur_med  = (round(float(pd.to_numeric(working_df[dur_col], errors="coerce").median()), 1)
                if dur_col in working_df.columns else None)

    return {
        "n": n, "date_range": date_range, "days_active": days_active,
        "n_enumerators": n_enumerators, "n_admin": n_admin,
        "flag_rows": flag_rows, "enu_rows": enu_rows, "admin_rows": admin_rows,
        "fcs_dist": fcs_dist, "fcs_mean": fcs_mean,
        "rcsi_dist": rcsi_dist, "rcsi_mean": rcsi_mean,
        "hdds_dist": hdds_dist, "hdds_mean": hdds_mean,
        "timeline": timeline, "dur_mean": dur_mean, "dur_med": dur_med,
        "total_flagged": len(all_flagged_ids),
        "generated": datetime.now().strftime("%d %b %Y, %H:%M"),
    }


# ── HTML builder ───────────────────────────────────────────────────────────────

_CSS = """
/* Matches XLSForm Reviewer design language — muted palette, Tailwind slate grays */
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    font-size: 12.5px; color: #334155; background: #f8fafc; line-height: 1.55;
}
.page { max-width: 1080px; margin: 0 auto; padding: 28px 22px; }

/* header */
.hdr { background: linear-gradient(135deg, #6a9cc8 0%, #4a7aaa 100%);
    color: #fff; padding: 22px 28px; border-radius: 10px; margin-bottom: 24px; }
.hdr h1 { font-size: 18px; font-weight: 700; letter-spacing: -.2px; }
.hdr .meta { font-size: 11px; opacity: 0.85; margin-top: 5px; color: #e8f0f8; }

/* sections */
h2 { font-size: 13px; font-weight: 700; color: #475569;
    border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; margin: 28px 0 12px;
    text-transform: uppercase; letter-spacing: .05em; }
h3 { font-size: 12px; font-weight: 600; color: #64748b; margin: 14px 0 6px; }

/* metric cards */
.cards { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
.card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 14px 18px; flex: 1 1 140px; text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.card .num { font-size: 24px; font-weight: 800; color: #6a9cc8; }
.card .lbl { font-size: 10px; color: #94a3b8; text-transform: uppercase;
    letter-spacing: .06em; margin-top: 2px; font-weight: 600; }
.card.warn .num { color: #cc9470; }
.card.bad  .num { color: #cc8080; }
.card.ok   .num { color: #6aab90; }

/* tables */
table { width: 100%; border-collapse: collapse; background: #fff;
    border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,.04); }
th { background: #f1f5f9; color: #64748b; font-size: 10.5px; font-weight: 600;
    text-transform: uppercase; letter-spacing: .05em; padding: 8px 12px;
    text-align: left; border-bottom: 2px solid #e2e8f0; }
td { padding: 7px 12px; border-bottom: 1px solid #f0f2f5; vertical-align: middle;
    font-size: 12px; color: #334155; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8fafc; }
.badge {
    display: inline-block; padding: .15rem .55rem; border-radius: 20px;
    font-size: 10.5px; font-weight: 700; white-space: nowrap;
}

/* fcg bar */
.fcg-bar { display: flex; height: 18px; border-radius: 6px; overflow: hidden;
    gap: 2px; margin-top: 6px; }
.fcg-seg { display: flex; align-items: center; justify-content: center;
    font-size: 9.5px; font-weight: 700; color: #fff; }

/* ── Issue cards ─────────────────────────────────────────────────────────── */
.issue-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-left-width: 4px;
    border-radius: 0 8px 8px 0;
    margin-bottom: 10px;
    padding: 11px 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.issue-header {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 5px;
}
.issue-ind-badge {
    font-size: 10px;
    font-weight: 700;
    padding: .15rem .5rem;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
}
.issue-check-name {
    font-weight: 700;
    font-size: 12.5px;
    color: #334155;
    flex: 1;
}
.issue-count-badge {
    font-size: 10.5px;
    font-weight: 700;
    background: #f1f5f9;
    color: #64748b;
    padding: .15rem .55rem;
    border-radius: 10px;
    white-space: nowrap;
    flex-shrink: 0;
}
.issue-pct {
    font-size: 10px;
    color: #94a3b8;
    margin-left: 4px;
}
.issue-desc {
    font-size: 11.5px;
    color: #475569;
    margin-bottom: 6px;
    line-height: 1.5;
}
.issue-action {
    font-size: 11px;
    color: #64748b;
    background: #f8fafc;
    border-left: 2px solid #cbd5e1;
    padding: 5px 9px;
    border-radius: 0 4px 4px 0;
    line-height: 1.5;
}
.issue-action::before {
    content: "▶ Action: ";
    font-weight: 700;
    color: #475569;
}

/* ── Recommendations ─────────────────────────────────────────────────────── */
.rec-list { list-style: none; }
.rec-item {
    display: flex;
    gap: 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(0,0,0,.04);
    line-height: 1.55;
    font-size: 12px;
}
.rec-icon {
    font-size: 16px;
    flex-shrink: 0;
    padding-top: 1px;
}
.rec-body {}
.rec-title {
    font-weight: 700;
    color: #334155;
    margin-bottom: 2px;
}
.rec-detail {
    color: #64748b;
    font-size: 11.5px;
}
.rec-ok {
    background: #e8f6f0;
    border-color: #b7e0cf;
    color: #1e6e4a;
    padding: 10px 14px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 12px;
}

/* footer */
.footer { margin-top: 36px; padding-top: 14px; border-top: 1px solid #e2e8f0;
    font-size: 10.5px; color: #94a3b8; text-align: center; }

@media print {
    body { background: #fff; }
    .page { padding: 0; }
    .card { break-inside: avoid; }
    table { break-inside: auto; }
    h2 { break-after: avoid; }
    .issue-card { break-inside: avoid; }
    .rec-item { break-inside: avoid; }
}
"""


def _indicator_table(flag_rows: list) -> str:
    rows_html = ""
    for r in flag_rows:
        rate = r["rate"]
        bg   = _rate_bg(rate)
        col  = _rate_color(rate)
        lbl  = _rate_label(rate)
        bar  = _css_bar(rate, col)
        checks_str = ", ".join(
            f"<b>{k}</b>: {v}" for k, v in r["checks"].items() if v > 0
        ) or "—"
        rows_html += (
            f"<tr>"
            f"<td><b>{html.escape(r['indicator'])}</b></td>"
            f"<td style='text-align:right'>{r['total']:,}</td>"
            f"<td style='text-align:right'>{r['flagged']:,}</td>"
            f"<td style='background:{bg}'>"
            f"  {bar}&nbsp;"
            f"  <span class='badge' style='background:{bg};color:{col}'>"
            f"    {rate:.1f}% {lbl}"
            f"  </span>"
            f"</td>"
            f"<td style='font-size:11px;color:#555'>{checks_str}</td>"
            f"</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Indicator</th><th>Total</th><th>Flagged</th>"
        "<th>Flag Rate</th><th>Issues Detected</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )


def _enumerator_table(enu_rows: list) -> str:
    if not enu_rows:
        return "<p style='color:#888'>Enumerator column not found in dataset.</p>"
    total_surveys = sum(r["surveys"] for r in enu_rows) or 1
    rows_html = ""
    for r in enu_rows:
        rate        = r["rate"]
        bg          = _rate_bg(rate)
        col         = _rate_color(rate)
        flag_bar    = _css_bar(rate, col, width=120)
        share_pct   = round(r["surveys"] / total_surveys * 100, 1)
        share_bar   = _css_bar(share_pct, "#6a9cc8", width=100)
        rows_html += (
            f"<tr>"
            f"<td>{html.escape(r['enumerator'])}</td>"
            f"<td>"
            f"  {share_bar}&nbsp;"
            f"  <span style='font-size:11px;color:#64748b'>{r['surveys']:,}"
            f"  <span style='color:#94a3b8;font-size:10px'>({share_pct:.1f}%)</span></span>"
            f"</td>"
            f"<td style='text-align:right'>{r['flagged']:,}</td>"
            f"<td style='background:{bg}'>"
            f"  {flag_bar}&nbsp;"
            f"  <span class='badge' style='background:{bg};color:{col}'>{rate:.1f}%</span>"
            f"</td>"
            f"</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Enumerator</th><th>Surveys Collected</th>"
        "<th>Flagged</th><th>Flag Rate</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )


def _admin_table(admin_rows: list) -> str:
    if not admin_rows:
        return "<p style='color:#888'>Admin area column not found in dataset.</p>"
    rows_html = ""
    for r in admin_rows:
        rate = r["rate"]
        bg   = _rate_bg(rate)
        col  = _rate_color(rate)
        bar  = _css_bar(rate, col)
        rows_html += (
            f"<tr>"
            f"<td>{html.escape(r['area'])}</td>"
            f"<td style='text-align:right'>{r['surveys']:,}</td>"
            f"<td style='text-align:right'>{r['flagged']:,}</td>"
            f"<td style='background:{bg}'>"
            f"  {bar}&nbsp;"
            f"  <span class='badge' style='background:{bg};color:{col}'>{rate:.1f}%</span>"
            f"</td>"
            f"</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Admin Area</th><th>Surveys</th><th>Flagged</th><th>Flag Rate</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )


def _dist_bar(segments: list[tuple[str, int, str]], mean_label: str | None = None) -> str:
    """
    Render a horizontal stacked distribution bar.
    segments: list of (label, count, hex_color)
    """
    total = sum(c for _, c, _ in segments) or 1
    bar_parts, badge_parts = [], []
    for label, count, color in segments:
        pct = round(count / total * 100, 1)
        bar_parts.append(
            f'<div class="fcg-seg" style="flex:{max(pct, 0.5)};background:{color}">'
            f'{"" if pct < 6 else f"{pct:.0f}%"}</div>'
        )
        badge_parts.append(
            f'<span class="badge" style="background:{color}22;color:{color};border:1px solid {color}55;">'
            f'{label}: {count:,} ({pct:.1f}%)</span>'
        )
    mean_str = (
        f"<p style='margin-top:8px;font-size:12px;color:#475569'>"
        f"Mean: <b>{mean_label}</b></p>"
    ) if mean_label else ""
    return (
        f'<div class="fcg-bar">{"".join(bar_parts)}</div>'
        f'<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">{"".join(badge_parts)}</div>'
        + mean_str
    )


def _fcs_section(stats: dict) -> str:
    d    = stats["fcs_dist"]
    mean = stats["fcs_mean"]
    if not d and mean is None:
        return "<p style='color:#888'>FCS data not available.</p>"
    total = sum(d.values()) or 1
    segments = [
        ("Poor",       d.get("Poor", 0),       "#cc8080"),
        ("Borderline", d.get("Borderline", 0),  "#ccb460"),
        ("Acceptable", d.get("Acceptable", 0),  "#6aab90"),
    ]
    return _dist_bar(segments, mean_label=str(mean) if mean else None)


def _rcsi_section(stats: dict) -> str:
    d    = stats.get("rcsi_dist", {})
    mean = stats.get("rcsi_mean")
    if not d and mean is None:
        return "<p style='color:#888'>rCSI data not available.</p>"
    segments = [
        ("Low (≤3)",     d.get("Low (≤3)", 0),      "#6aab90"),
        ("Medium (4–18)", d.get("Medium (4–18)", 0), "#ccb460"),
        ("High (≥19)",   d.get("High (≥19)", 0),    "#cc8080"),
    ]
    return _dist_bar(segments, mean_label=str(mean) if mean else None)


def _hdds_section(stats: dict) -> str:
    d    = stats.get("hdds_dist", {})
    mean = stats.get("hdds_mean")
    if not d and mean is None:
        return "<p style='color:#888'>HDDS data not available.</p>"
    segments = [
        ("Low (≤3)",    d.get("Low (≤3)", 0),    "#cc8080"),
        ("Medium (4–6)", d.get("Medium (4–6)", 0), "#ccb460"),
        ("High (≥7)",   d.get("High (≥7)", 0),   "#6aab90"),
    ]
    return _dist_bar(segments, mean_label=str(mean) if mean else None)


def _top_issues(flag_rows: list, n_total: int) -> str:
    """
    Render enriched issue cards — sorted by count (most frequent first).
    Each card shows: indicator badge, check name, count + %, description, action.
    """
    issues = []
    for r in flag_rows:
        for check, count in r["checks"].items():
            if count > 0:
                desc, action, severity = _lookup_flag(r["indicator"], check)
                issues.append({
                    "indicator": r["indicator"],
                    "check":     check,
                    "count":     count,
                    "pct":       round(count / n_total * 100, 1) if n_total else 0,
                    "desc":      desc,
                    "action":    action,
                    "severity":  severity,
                })

    # Sort: critical first, then by count descending
    _sev_order = {"critical": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda x: (_sev_order.get(x["severity"], 9), -x["count"]))

    if not issues:
        return "<p style='color:#1e8449;font-weight:600'>✓ No issues detected across all indicators.</p>"

    cards = ""
    for iss in issues[:20]:   # cap at 20 cards
        cfg  = _SEV_CONFIG.get(iss["severity"], _SEV_CONFIG["info"])
        # readable check name: insert spaces before capitals, replace underscores
        readable_check = iss["check"].replace("_", " ")

        cards += f"""
        <div class="issue-card" style="border-left-color:{cfg['border']};background:{cfg['bg']};">
          <div class="issue-header">
            <span class="issue-ind-badge"
                  style="background:{cfg['badge_bg']};color:{cfg['badge_color']};">
              {html.escape(iss['indicator'])}
            </span>
            <span class="issue-check-name">{html.escape(readable_check)}</span>
            <span class="issue-count-badge">
              {iss['count']:,} records
              <span class="issue-pct">({iss['pct']:.1f}%)</span>
            </span>
          </div>
          <p class="issue-desc">{html.escape(iss['desc'])}</p>
          <div class="issue-action">{html.escape(iss['action'])}</div>
        </div>"""

    return cards


def _recommendations(stats: dict, flag_rows: list) -> str:
    """
    Generate specific, actionable recommendations based on the data.
    Each rec has an icon, a bold title, and a detail sentence.
    """
    n = stats.get("n", 1) or 1
    recs = []   # list of (icon, title, detail)

    # ── Overall flag rate ──────────────────────────────────────────────────────
    overall_rate = round(stats["total_flagged"] / n * 100, 1)
    if overall_rate > 20:
        recs.append((
            "🚨",
            f"Immediate field follow-up required — overall flag rate is {overall_rate:.1f}%",
            "WFP HFC guidelines recommend investigating when the overall flag rate exceeds 20%. "
            "Hold a data quality debrief with all enumerators and field supervisors before the next collection day.",
        ))
    elif overall_rate > 10:
        recs.append((
            "⚠️",
            f"Elevated flag rate ({overall_rate:.1f}%) — enhanced monitoring recommended",
            "Schedule a mid-survey quality debrief. Identify the top-flagging enumerators and "
            "conduct accompanied interviews or phone spot-checks.",
        ))

    # ── Enumerators with high flag rates ──────────────────────────────────────
    critical_enu = [r for r in stats.get("enu_rows", []) if r["rate"] > 30]
    warn_enu     = [r for r in stats.get("enu_rows", []) if 15 < r["rate"] <= 30]

    if critical_enu:
        names = ", ".join(f"<b>{html.escape(r['enumerator'])}</b> ({r['rate']:.0f}%)" for r in critical_enu[:4])
        recs.append((
            "👤",
            f"{len(critical_enu)} enumerator(s) exceed 30% flag rate",
            f"Priority for supervisor review: {names}. "
            "Pull the flagged records for each and conduct a line-by-line review. "
            "Consider suspending data collection for these enumerators until issues are resolved.",
        ))
    if warn_enu:
        names = ", ".join(f"<b>{html.escape(r['enumerator'])}</b> ({r['rate']:.0f}%)" for r in warn_enu[:3])
        recs.append((
            "👁️",
            f"{len(warn_enu)} enumerator(s) have flag rates between 15–30%",
            f"Monitor closely: {names}. Schedule an accompanied re-interview for at least 2 of their "
            "recent surveys to check for systematic response patterns.",
        ))

    # ── Food security ─────────────────────────────────────────────────────────
    if stats.get("fcs_dist"):
        poor_n = stats["fcs_dist"].get("Poor", 0)
        poor_pct = round(poor_n / n * 100, 1)
        if poor_pct > 30:
            recs.append((
                "🍽️",
                f"{poor_pct:.1f}% of households are in the 'Poor' food consumption group",
                "Verify that Poor FCS scores are genuine and not artefacts of skip errors or misrecorded "
                "frequencies. Cross-check against rCSI and LCS data: households with Poor FCS should "
                "generally show elevated coping strategy use.",
            ))

    # ── Specific high-impact checks ───────────────────────────────────────────
    check_map: dict[tuple[str, str], int] = {}
    for r in flag_rows:
        for check, count in r["checks"].items():
            if count > 0:
                check_map[(r["indicator"], check)] = count

    # Timing: short duration is the most serious fabrication signal
    short_dur = check_map.get(("Timing", "ShortDuration"), 0)
    if short_dur > 0:
        recs.append((
            "⏱️",
            f"{short_dur} survey(s) completed in suspiciously short time",
            "Short-duration interviews are the strongest indicator of data fabrication. "
            "Re-interview these households independently, without involvement of the original enumerator. "
            "If fabrication is confirmed, escalate per your organisation's data integrity policy.",
        ))

    # LCS: many N/A
    lcs_manyNA = check_map.get(("LCS", "ManyNA"), 0)
    if lcs_manyNA > 0:
        pct_lcs = round(lcs_manyNA / n * 100, 1)
        recs.append((
            "📋",
            f"{lcs_manyNA} records ({pct_lcs:.1f}%) have ≥3 LCS strategies marked N/A",
            "This is likely caused by enumerators skipping LCS questions when they perceive the household "
            "as wealthy. Retrain all enumerators: N/A should only be selected when the strategy is "
            "genuinely unavailable to the household (e.g., no livestock to sell). "
            "For emergency strategies (begging, migration, child labour), N/A is never valid per WFP guidance.",
        ))

    # Demo: sum mismatch
    demo_mismatch = check_map.get(("Demo", "SumMismatch"), 0)
    if demo_mismatch > 0:
        recs.append((
            "👨‍👩‍👧",
            f"{demo_mismatch} households have a household size / roster mismatch",
            "This is the most common data entry error in demographic modules. "
            "Retrain enumerators to recount the roster total after completing each row. "
            "Correct the roster before finalising the dataset.",
        ))

    # rCSI: zero with poor FCG
    rcsi_zero = check_map.get(("rCSI", "ZeroWithPoorFCG"), 0)
    if rcsi_zero > 0:
        recs.append((
            "🔄",
            f"{rcsi_zero} households report no coping strategies but Poor food security",
            "This internal contradiction suggests either the FCS module or the rCSI module contains "
            "an error. Review both sections with the enumerator. Most likely cause: the household "
            "scored low on FCS due to a recording error rather than true food insecurity.",
        ))

    # FCS: identical responses
    fcs_identical = check_map.get(("FCS", "Identical"), 0)
    if fcs_identical > 0:
        recs.append((
            "🔁",
            f"{fcs_identical} FCS record(s) have all food group frequencies identical",
            "Identical responses across all food groups are a strong signal of anchoring or fabrication. "
            "Pull the paper forms for these records and compare. Discuss at the next team debrief.",
        ))

    # ── Geographic outliers ───────────────────────────────────────────────────
    if stats.get("admin_rows"):
        high_areas = [r for r in stats["admin_rows"] if r["rate"] > 30]
        if high_areas:
            names = ", ".join(f"<b>{html.escape(r['area'])}</b> ({r['rate']:.0f}%)" for r in high_areas[:3])
            recs.append((
                "📍",
                f"High flag rates in {len(high_areas)} geographic area(s)",
                f"Areas to investigate: {names}. High geographic concentration of flags may indicate "
                "a local training gap, translation issue, or a specific enumerator assigned to that area.",
            ))

    # ── Positive signal if things look OK ────────────────────────────────────
    if not recs:
        return (
            '<div class="rec-ok">'
            '✅ Data quality appears acceptable across all indicators. '
            'Continue routine monitoring and spot-checking (aim for ≥5% of surveys per enumerator per week).'
            '</div>'
        )

    items = ""
    for icon, title, detail in recs:
        items += f"""
        <li class="rec-item">
          <span class="rec-icon">{icon}</span>
          <div class="rec-body">
            <div class="rec-title">{html.escape(title)}</div>
            <div class="rec-detail">{detail}</div>
          </div>
        </li>"""

    return f"<ul class='rec-list'>{items}</ul>"


def generate_html(results: dict[str, pd.DataFrame], working_df: pd.DataFrame,
                  survey_name: str = "Survey") -> str:
    stats = compute_stats(results, working_df)
    n     = stats["n"]
    total_flagged = stats["total_flagged"]
    overall_rate  = round(total_flagged / n * 100, 1) if n else 0

    overall_card_class = "bad" if overall_rate > 20 else "warn" if overall_rate > 10 else "ok"

    # FCS/rCSI cards
    fcs_card = (
        f'<div class="card"><div class="num">{stats["fcs_mean"]}</div>'
        f'<div class="lbl">Mean FCS</div></div>'
    ) if stats["fcs_mean"] else ""
    rcsi_card = (
        f'<div class="card warn"><div class="num">{stats["rcsi_mean"]}</div>'
        f'<div class="lbl">Mean rCSI</div></div>'
    ) if stats["rcsi_mean"] else ""
    dur_card = (
        f'<div class="card"><div class="num">{stats["dur_mean"]}</div>'
        f'<div class="lbl">Avg Duration (min)</div></div>'
    ) if stats["dur_mean"] else ""

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WFP HFC Report — {html.escape(survey_name)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">

  <div class="hdr">
    <h1>WFP Survey — Data Quality Report</h1>
    <div class="meta">
      {html.escape(survey_name)} &nbsp;|&nbsp;
      Generated: {stats['generated']} &nbsp;|&nbsp;
      Survey period: {stats['date_range']}
    </div>
  </div>

  <!-- ── Section 1: Survey Overview ────────────────────────────────────── -->
  <h2>1. Survey Overview</h2>
  <div class="cards">
    <div class="card">
      <div class="num">{n:,}</div>
      <div class="lbl">Total Households</div>
    </div>
    <div class="card {overall_card_class}">
      <div class="num">{total_flagged:,}</div>
      <div class="lbl">Flagged Records</div>
    </div>
    <div class="card {overall_card_class}">
      <div class="num">{overall_rate:.1f}%</div>
      <div class="lbl">Overall Flag Rate</div>
    </div>
    <div class="card">
      <div class="num">{stats['n_enumerators']:,}</div>
      <div class="lbl">Enumerators</div>
    </div>
    <div class="card">
      <div class="num">{stats['days_active'] or '—'}</div>
      <div class="lbl">Days Active</div>
    </div>
    {fcs_card}
    {rcsi_card}
    {dur_card}
  </div>

  <!-- ── Section 2: Data Quality Summary ───────────────────────────────── -->
  <h2>2. Data Quality Summary by Indicator</h2>
  {_indicator_table(stats['flag_rows'])}

  <!-- ── Section 3: Key Issues ─────────────────────────────────────────── -->
  <h2>3. Key Issues Detected</h2>
  <p style="font-size:11.5px;color:#64748b;margin-bottom:12px;">
    Issues are sorted by severity then by number of affected records.
    <span style="display:inline-block;margin-left:8px;">
      <span style="background:#fdf0f0;border-left:3px solid #cc8080;padding:1px 6px;border-radius:0 3px 3px 0;font-size:10px;font-weight:700;color:#cc8080;">Critical</span>
      &nbsp;likely data fabrication or severe error &nbsp;·&nbsp;
      <span style="background:#fdf5ee;border-left:3px solid #cc9470;padding:1px 6px;border-radius:0 3px 3px 0;font-size:10px;font-weight:700;color:#cc9470;">High</span>
      &nbsp;needs follow-up &nbsp;·&nbsp;
      <span style="background:#f0f6fc;border-left:3px solid #6a9cc8;padding:1px 6px;border-radius:0 3px 3px 0;font-size:10px;font-weight:700;color:#6a9cc8;">Medium</span>
      &nbsp;monitor
    </span>
  </p>
  {_top_issues(stats['flag_rows'], n)}

  <!-- ── Section 4: Recommendations ───────────────────────────────────── -->
  <h2>4. Recommendations</h2>
  {_recommendations(stats, stats['flag_rows'])}

  <!-- ── Section 5: Food Security Highlights ───────────────────────────── -->
  <h2>5. Food Security Indicators</h2>
  <h3>Food Consumption Score (FCS) — Food Group Distribution</h3>
  <p style="font-size:11px;color:#94a3b8;margin-bottom:6px;">
    Thresholds: Poor &lt;28 · Borderline 28–42 · Acceptable &gt;42
  </p>
  {_fcs_section(stats)}

  <h3 style="margin-top:20px;">Reduced Coping Strategy Index (rCSI) — Severity Distribution</h3>
  <p style="font-size:11px;color:#94a3b8;margin-bottom:6px;">
    Thresholds: Low ≤3 · Medium 4–18 · High ≥19 &nbsp;|&nbsp; Higher scores indicate greater food insecurity coping pressure.
  </p>
  {_rcsi_section(stats)}

  <h3 style="margin-top:20px;">Household Dietary Diversity Score (HDDS) — Diversity Distribution</h3>
  <p style="font-size:11px;color:#94a3b8;margin-bottom:6px;">
    Thresholds: Low ≤3 food groups · Medium 4–6 · High ≥7 &nbsp;|&nbsp; Higher scores indicate greater dietary diversity.
  </p>
  {_hdds_section(stats)}

  <!-- ── Section 6: Enumerator Performance ────────────────────────────── -->
  <h2>6. Enumerator Performance</h2>
  {_enumerator_table(stats['enu_rows'])}

  <!-- ── Section 7: Admin Area Breakdown ──────────────────────────────── -->
  <h2>7. Geographic Breakdown</h2>
  {_admin_table(stats['admin_rows'])}

  <div class="footer">
    WFP Survey High-Frequency Data Quality Checks &nbsp;·&nbsp;
    This report was auto-generated and should be reviewed by a data quality officer.
  </div>

</div>
</body>
</html>"""
    return body


def save_html(results: dict, working_df: pd.DataFrame,
              output_path: str, survey_name: str = "Survey") -> None:
    content = generate_html(results, working_df, survey_name)
    Path(output_path).write_text(content, encoding="utf-8")
