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
# Muted, warm tones instead of harsh reds/oranges

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

    # rCSI mean
    rcsi_mean = (round(float(pd.to_numeric(working_df["rCSI"], errors="coerce").mean()), 1)
                 if "rCSI" in working_df.columns else None)

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
        "fcs_dist": fcs_dist, "fcs_mean": fcs_mean, "rcsi_mean": rcsi_mean,
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

/* header — muted blue, not harsh navy */
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

/* issues list */
.issues { list-style: none; }
.issues li { background: #fff; border: 1px solid #e2e8f0;
    border-left: 3px solid #6a9cc8;
    border-radius: 0 6px 6px 0; margin-bottom: 7px; padding: 8px 12px;
    box-shadow: 0 1px 2px rgba(0,0,0,.04); font-size: 12px; }
.issues li .indicator { font-weight: 700; color: #6a9cc8; margin-right: 5px; }
.issues li .count { float: right; font-weight: 700; color: #64748b;
    font-size: 11px; background: #f1f5f9; padding: .1rem .5rem;
    border-radius: 10px; }

/* footer */
.footer { margin-top: 36px; padding-top: 14px; border-top: 1px solid #e2e8f0;
    font-size: 10.5px; color: #94a3b8; text-align: center; }

@media print {
    body { background: #fff; }
    .page { padding: 0; }
    .card { break-inside: avoid; }
    table { break-inside: auto; }
    h2 { break-after: avoid; }
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
    rows_html = ""
    for r in enu_rows:
        rate = r["rate"]
        bg   = _rate_bg(rate)
        col  = _rate_color(rate)
        bar  = _css_bar(rate, col)
        rows_html += (
            f"<tr>"
            f"<td>{html.escape(r['enumerator'])}</td>"
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
        "<thead><tr><th>Enumerator</th><th>Surveys</th><th>Flagged</th><th>Flag Rate</th></tr></thead>"
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


def _fcs_section(stats: dict) -> str:
    d    = stats["fcs_dist"]
    mean = stats["fcs_mean"]
    if not d and mean is None:
        return "<p style='color:#888'>FCS data not available.</p>"

    total = sum(d.values()) or 1
    parts = []
    labels = []
    for label in ("Poor", "Borderline", "Acceptable"):
        n   = d.get(label, 0)
        pct = round(n / total * 100, 1)
        col = _fcg_color(label)
        parts.append(f'<div class="fcg-seg" style="flex:{pct};background:{col}">{pct:.0f}%</div>')
        labels.append(f'<span class="badge" style="background:{_rate_bg(100 if label=="Poor" else 15 if label=="Borderline" else 0)};color:{col}">{label}: {n:,} ({pct:.1f}%)</span>')

    mean_str = f"<p style='margin-top:10px;font-size:12px'>Mean FCS: <b>{mean}</b></p>" if mean else ""
    return (
        f'<div class="fcg-bar">{"".join(parts)}</div>'
        f'<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">{"".join(labels)}</div>'
        + mean_str
    )


def _top_issues(flag_rows: list) -> str:
    issues = []
    for r in flag_rows:
        for check, count in r["checks"].items():
            if count > 0:
                issues.append((r["indicator"], check, count))
    issues.sort(key=lambda x: x[2], reverse=True)
    if not issues:
        return "<p style='color:#1e8449;font-weight:600'>✓ No issues detected across all indicators.</p>"

    items = ""
    for ind, check, count in issues[:15]:
        items += (
            f"<li>"
            f"<span class='indicator'>[{html.escape(ind)}]</span>"
            f"{html.escape(check.replace('_', ' '))}"
            f"<span class='count'>{count:,} records</span>"
            f"</li>"
        )
    return f"<ul class='issues'>{items}</ul>"


def _recommendations(stats: dict, flag_rows: list) -> str:
    recs = []
    for r in flag_rows:
        if r["rate"] > 20:
            recs.append(f"<b>{r['indicator']}</b> has a high flag rate ({r['rate']:.1f}%) — immediate field follow-up recommended.")
    if stats.get("fcs_dist"):
        poor = stats["fcs_dist"].get("Poor", 0)
        pct  = round(poor / stats["n"] * 100, 1) if stats["n"] else 0
        if pct > 30:
            recs.append(f"<b>{pct:.1f}%</b> of households are in the Poor food consumption group — verify with field teams.")
    if stats.get("enu_rows"):
        high_enu = [r for r in stats["enu_rows"] if r["rate"] > 30]
        if high_enu:
            names = ", ".join(r["enumerator"] for r in high_enu[:3])
            recs.append(f"Enumerators with >30% flag rate require supervisor attention: <b>{names}</b>.")
    if not recs:
        recs.append("Data quality appears acceptable. Continue routine monitoring.")
    return "<ul style='padding-left:18px;line-height:2'>" + "".join(f"<li>{r}</li>" for r in recs) + "</ul>"


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
  {_top_issues(stats['flag_rows'])}

  <!-- ── Section 4: Recommendations ───────────────────────────────────── -->
  <h2>4. Recommendations</h2>
  {_recommendations(stats, stats['flag_rows'])}

  <!-- ── Section 5: Food Security Highlights ───────────────────────────── -->
  <h2>5. Food Security Indicators</h2>
  <h3>Food Consumption Group Distribution</h3>
  {_fcs_section(stats)}

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
