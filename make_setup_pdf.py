"""
Generate SETUP.pdf — Survey High-Frequency Data Quality Checks
Includes a tool introduction section followed by the technical setup manual.
Font: Open Sans (Regular, SemiBold, Bold, Italic, BoldItalic)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUTPUT    = "SETUP.pdf"
FONT_DIR  = "/Users/nicolewu/Library/Fonts/OpenSans-Static"
PAGE_W, PAGE_H = A4
MARGIN    = 22 * mm

# ── Register Open Sans ────────────────────────────────────────────────────────
pdfmetrics.registerFont(TTFont("OpenSans",         f"{FONT_DIR}/OpenSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("OpenSans-Bold",    f"{FONT_DIR}/OpenSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("OpenSans-Semi",    f"{FONT_DIR}/OpenSans-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont("OpenSans-Italic",  f"{FONT_DIR}/OpenSans-Italic.ttf"))
pdfmetrics.registerFont(TTFont("OpenSans-BoldIt",  f"{FONT_DIR}/OpenSans-BoldItalic.ttf"))
pdfmetrics.registerFontFamily(
    "OpenSans",
    normal    = "OpenSans",
    bold      = "OpenSans-Bold",
    italic    = "OpenSans-Italic",
    boldItalic= "OpenSans-BoldIt",
)

# ── Colour palette ────────────────────────────────────────────────────────────
C_PRIMARY    = colors.HexColor("#3a6ea8")
C_PRIMARY_LT = colors.HexColor("#d8eaf8")
C_PRIMARY_MD = colors.HexColor("#b0cfe8")
C_MAC        = colors.HexColor("#4a7c7e")
C_WIN        = colors.HexColor("#6a5aaa")
C_CODE_BG    = colors.HexColor("#f1f5f9")
C_CODE_FG    = colors.HexColor("#1e293b")
C_MUTED      = colors.HexColor("#64748b")
C_WARN_BG    = colors.HexColor("#fdf5ee")
C_WARN_FG    = colors.HexColor("#b87050")
C_TBL_HEAD   = colors.HexColor("#e8f2fc")
C_TBL_ALT    = colors.HexColor("#f8fafc")
C_WHITE      = colors.white
C_BLACK      = colors.HexColor("#1e293b")
C_BORDER     = colors.HexColor("#e2e8f0")


# ── Styles ────────────────────────────────────────────────────────────────────
def build_styles():
    def S(name, **kw):
        kw.setdefault("fontName", "OpenSans")
        kw.setdefault("textColor", C_BLACK)
        return ParagraphStyle(name, **kw)

    return {
        # Cover
        "cover_title":  S("cover_title",
                           fontName="OpenSans-Bold", fontSize=26,
                           textColor=C_WHITE, leading=32, spaceAfter=6),
        "cover_sub":    S("cover_sub",
                           fontName="OpenSans-Italic", fontSize=13,
                           textColor=colors.HexColor("#c8dff2"), leading=18, spaceAfter=0),
        "cover_tag":    S("cover_tag",
                           fontName="OpenSans", fontSize=9,
                           textColor=colors.HexColor("#a8c8e8"), leading=13),

        # Document headings
        "doc_title":    S("doc_title",
                           fontName="OpenSans-Bold", fontSize=20,
                           textColor=C_PRIMARY,
                           spaceBefore=0, spaceAfter=4, leading=26),
        "doc_sub":      S("doc_sub",
                           fontName="OpenSans-Italic", fontSize=11,
                           textColor=C_MUTED,
                           spaceBefore=0, spaceAfter=8, leading=16),
        "h1":           S("h1",
                           fontName="OpenSans-Bold", fontSize=15,
                           textColor=C_PRIMARY,
                           spaceBefore=16, spaceAfter=6, leading=20),
        "h2":           S("h2",
                           fontName="OpenSans-Semi", fontSize=12,
                           textColor=C_PRIMARY,
                           spaceBefore=14, spaceAfter=5, leading=17),
        "h3":           S("h3",
                           fontName="OpenSans-Semi", fontSize=10.5,
                           textColor=C_BLACK,
                           spaceBefore=10, spaceAfter=4, leading=15),
        "h_step":       S("h_step",
                           fontName="OpenSans-Semi", fontSize=10.5,
                           textColor=C_BLACK,
                           spaceBefore=0, spaceAfter=3, leading=15),
        "h_os":         S("h_os",
                           fontName="OpenSans-Bold", fontSize=13,
                           textColor=C_WHITE,
                           spaceBefore=0, spaceAfter=0, leading=18),

        # Body
        "body":         S("body",
                           fontName="OpenSans", fontSize=9.5,
                           textColor=C_BLACK,
                           spaceBefore=3, spaceAfter=5, leading=15),
        "body_j":       S("body_j",
                           fontName="OpenSans", fontSize=9.5,
                           textColor=C_BLACK, alignment=TA_JUSTIFY,
                           spaceBefore=3, spaceAfter=6, leading=15),
        "bullet":       S("bullet",
                           fontName="OpenSans", fontSize=9.5,
                           textColor=C_BLACK,
                           spaceBefore=2, spaceAfter=2, leading=14,
                           leftIndent=14, firstLineIndent=-8),
        "note":         S("note",
                           fontName="OpenSans-Italic", fontSize=9,
                           textColor=C_WARN_FG,
                           spaceBefore=3, spaceAfter=3, leading=13,
                           leftIndent=10),
        "caption":      S("caption",
                           fontName="OpenSans-Italic", fontSize=8.5,
                           textColor=C_MUTED,
                           spaceBefore=2, spaceAfter=4, leading=12),

        # Code
        "code_line":    S("code_line",
                           fontName="Courier", fontSize=8.5,
                           textColor=C_CODE_FG,
                           spaceBefore=0, spaceAfter=0, leading=12),

        # Feature card
        "feat_title":   S("feat_title",
                           fontName="OpenSans-Semi", fontSize=9.5,
                           textColor=C_PRIMARY,
                           spaceBefore=0, spaceAfter=2, leading=13),
        "feat_body":    S("feat_body",
                           fontName="OpenSans", fontSize=8.8,
                           textColor=C_BLACK,
                           spaceBefore=0, spaceAfter=0, leading=13),

        # FAQ
        "faq_q":        S("faq_q",
                           fontName="OpenSans-Semi", fontSize=9.5,
                           textColor=C_PRIMARY,
                           spaceBefore=9, spaceAfter=2, leading=14),
        "faq_a":        S("faq_a",
                           fontName="OpenSans", fontSize=9.5,
                           textColor=C_BLACK,
                           spaceBefore=0, spaceAfter=3, leading=14),

        # Table cells
        "tbl_hdr":      S("tbl_hdr",
                           fontName="OpenSans-Semi", fontSize=8.5,
                           textColor=C_PRIMARY,
                           spaceBefore=0, spaceAfter=0, leading=12),
        "tbl_cell":     S("tbl_cell",
                           fontName="OpenSans", fontSize=8.5,
                           textColor=C_BLACK,
                           spaceBefore=0, spaceAfter=0, leading=12),

        # Footer
        "footer":       S("footer",
                           fontName="OpenSans", fontSize=7.5,
                           textColor=C_MUTED, alignment=TA_CENTER,
                           spaceBefore=0, spaceAfter=0, leading=11),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
def hr(color=C_BORDER, thickness=0.5, sb=6, sa=10):
    return HRFlowable(width="100%", thickness=thickness,
                      color=color, spaceBefore=sb, spaceAfter=sa)

def sp(h=6):
    return Spacer(1, h)


def code_block(lines, styles):
    rows = [[Paragraph(l, styles["code_line"])] for l in lines]
    tbl  = Table(rows, colWidths=[PAGE_W - 2 * MARGIN - 10 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_CODE_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("LINEABOVE",     (0, 0), (-1, 0),  0.5, C_BORDER),
        ("LINEBELOW",     (0, -1),(-1, -1), 0.5, C_BORDER),
    ]))
    return tbl


def os_banner(text, color, styles):
    p   = Paragraph(text, styles["h_os"])
    tbl = Table([[p]], colWidths=[PAGE_W - 2 * MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    return tbl


def step_row(num, title, color, styles):
    badge = Paragraph(
        f'<font color="white"><b>Step {num}</b></font>',
        ParagraphStyle("sb", fontName="OpenSans-Bold", fontSize=8.5,
                       textColor=C_WHITE, alignment=TA_CENTER, leading=12)
    )
    heading   = Paragraph(title, styles["h_step"])
    badge_tbl = Table([[badge]], colWidths=[16 * mm])
    badge_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    row = Table([[badge_tbl, heading]],
                colWidths=[18 * mm, PAGE_W - 2 * MARGIN - 18 * mm])
    row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return row


def shortcut_box(lines, styles):
    header    = Paragraph("Returning users — quick launch",
                           ParagraphStyle("shh", fontName="OpenSans-Semi", fontSize=9,
                                          textColor=C_PRIMARY, leading=13))
    code_rows = [[Paragraph(l, styles["code_line"])] for l in lines]
    inner     = Table(code_rows, colWidths=[PAGE_W - 2 * MARGIN - 28 * mm])
    inner.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
    ]))
    tbl = Table([[header], [inner]], colWidths=[PAGE_W - 2 * MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_PRIMARY_LT),
        ("TOPPADDING",    (0, 0), (0, 0),  9),
        ("BOTTOMPADDING", (0, -1),(-1, -1), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 13),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 13),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
    ]))
    return tbl


def data_table(headers, rows, col_widths, styles, alt=True):
    import re
    def fmt(txt, hdr=False):
        s = styles["tbl_hdr"] if hdr else styles["tbl_cell"]
        txt = re.sub(r"`([^`]+)`",
                     lambda m: f'<font name="Courier" size="7.8">{m.group(1)}</font>', txt)
        return Paragraph(txt, s)

    tdata = [[fmt(h, True) for h in headers]]
    for row in rows:
        tdata.append([fmt(c) for c in row])

    tbl = Table(tdata, colWidths=col_widths, repeatRows=1)
    ts  = [
        ("BACKGROUND",    (0, 0), (-1, 0),  C_TBL_HEAD),
        ("LINEBELOW",     (0, 0), (-1, 0),  1,   C_PRIMARY),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.4, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]
    if alt:
        for i in range(2, len(tdata), 2):
            ts.append(("BACKGROUND", (0, i), (-1, i), C_TBL_ALT))
    tbl.setStyle(TableStyle(ts))
    return tbl


def feature_card(icon, title, body, styles, color=C_PRIMARY_LT):
    title_p = Paragraph(f"{icon}  {title}", styles["feat_title"])
    body_p  = Paragraph(body, styles["feat_body"])
    tbl = Table([[title_p], [body_p]], colWidths=[PAGE_W / 2 - MARGIN - 4 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 11),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 11),
        ("TOPPADDING",    (0, 1), (-1, -1), 3),
        ("LINEABOVE",     (0, 0), (-1, 0),  2, color),
    ]))
    return tbl


# ── Page header / footer ──────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - 13 * mm, PAGE_W - MARGIN, PAGE_H - 13 * mm)
    canvas.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)
    canvas.setFont("OpenSans", 7.5)
    canvas.setFillColor(C_MUTED)
    canvas.drawCentredString(
        PAGE_W / 2, 8 * mm,
        f"Survey HFC  ·  Setup & Introduction Guide  ·  Page {doc.page}"
    )
    canvas.restoreState()


def on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#2a5298"))
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.restoreState()


# ── Build document ────────────────────────────────────────────────────────────
def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Survey HFC — Setup & Introduction Guide",
        author="Survey HFC",
        subject="Tool introduction and local installation instructions",
    )

    styles = build_styles()
    story  = []

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 52 * mm))

    cover_title = Table(
        [[Paragraph("Survey High-Frequency Data Quality Checks", styles["cover_title"])],
         [Paragraph("Setup &amp; Introduction Guide", styles["cover_sub"])],
         [sp(8)],
         [Paragraph(
             "Automated enumerator monitoring and indicator quality control for food security surveys",
             styles["cover_tag"]
         )]],
        colWidths=[PAGE_W - 2 * MARGIN]
    )
    cover_title.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    story.append(cover_title)
    story.append(Spacer(1, 60 * mm))

    meta_rows = [
        ["Standards", "World Bank DIME iehfc  ·  SurveyCTO HFC framework"],
        ["Mode",      "Local installation — data never leaves your machine"],
        ["Formats",   "CSV  ·  Excel  ·  Stata (.dta)  ·  SPSS (.sav)"],
        ["Requires",  "Python 3.9 or higher"],
    ]
    C_META_KEY = colors.HexColor("#8ab4d8")
    C_META_VAL = colors.HexColor("#e8f2fc")
    C_META_DIV = colors.HexColor("#3a5a80")

    meta_tbl = Table(
        [[Paragraph(r[0], ParagraphStyle("mk", fontName="OpenSans-Semi", fontSize=8.5,
                                          textColor=C_META_KEY, leading=12)),
          Paragraph(r[1], ParagraphStyle("mv", fontName="OpenSans", fontSize=9,
                                          textColor=C_META_VAL, leading=13))]
         for r in meta_rows],
        colWidths=[32 * mm, PAGE_W - 2 * MARGIN - 32 * mm]
    )
    meta_tbl.setStyle(TableStyle([
        ("LINEABOVE",     (0, 0), (-1, 0),  0.5, C_META_DIV),
        ("LINEBELOW",     (0, -1),(-1, -1), 0.5, C_META_DIV),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.4, C_META_DIV),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_tbl)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — INTRODUCTION
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Introduction", styles["h1"]))
    story.append(hr(C_PRIMARY, thickness=1.2, sb=2, sa=10))

    story.append(Paragraph("What is Survey HFC?", styles["h2"]))
    story.append(Paragraph(
        "Survey High-Frequency Data Quality Checks (HFC) is a locally-run dashboard for "
        "automated data quality monitoring on food security and household survey data. "
        "Upload your dataset daily and get a structured view of enumerator behaviour, "
        "flag rates, duplicate records, and actionable field feedback — before errors compound.",
        styles["body_j"]
    ))
    story.append(Paragraph(
        "The tool runs ten indicator modules against your survey data and surfaces issues across "
        "four review areas: <b>sequential checks</b> that catch structural impossibilities before "
        "other checks run; <b>indicator-level checks</b> that flag implausible or inconsistent "
        "values within each module; <b>cross-indicator checks</b> that detect logical contradictions "
        "across indicators using FEWS NET illogicality pairs; and <b>enumerator monitoring</b> that "
        "surfaces patterns suggesting coaching, rushing, or data fabrication.",
        styles["body_j"]
    ))
    story.append(sp(4))

    # — Key features grid
    story.append(Paragraph("Key Features", styles["h2"]))
    story.append(sp(4))

    CARD_W = (PAGE_W - 2 * MARGIN - 6 * mm) / 2

    features = [
        ("📋", "Ten Indicator Modules",
         "Demographics, FCS, HDDS, rCSI, Housing, LCS, Food Expenditure, "
         "Non-food Expenditure (1-month), Non-food Expenditure (6-month), and Interview Timing — "
         "all configurable from the app UI without touching any files."),
        ("👥", "Enumerator Monitoring",
         "Per-enumerator flag rates vs. overall average, indicator means comparison with "
         "1.5 SD outlier highlighting, daily submission heatmap by enumerator, and "
         "missing data rate by indicator and enumerator."),
        ("📊", "Survey Progress Tracking",
         "Cumulative and daily submission charts with a target line, pace projections "
         "(average surveys per day, estimated days to completion), and an area completion "
         "table with status indicators."),
        ("🔍", "Cross-Indicator Logic Checks",
         "Detects contradictions across indicators using FEWS NET illogicality pairs — "
         "combinations that cannot coexist under standard food security frameworks, "
         "such as Poor FCS with zero coping strategies."),
        ("📤", "Three Export Formats",
         "Colour-coded Excel error log (one sheet per indicator), self-contained HTML "
         "manager report (print to PDF via browser), and per-enumerator feedback Excel "
         "(one sheet per enumerator with only their flagged records)."),
        ("🔒", "Local & Offline Operation",
         "The application runs entirely on the user's machine. No survey data, results, "
         "or any other information is transmitted to any external server at any point."),
    ]

    for i in range(0, len(features), 2):
        left  = feature_card(*features[i],   styles, C_PRIMARY_LT)
        right = feature_card(*features[i+1], styles, colors.HexColor("#f5f2fd"))
        row_tbl = Table([[left, sp(6), right]],
                        colWidths=[CARD_W, 6 * mm, CARD_W])
        row_tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(row_tbl)
        story.append(sp(6))

    story.append(sp(2))

    # — Outputs
    story.append(Paragraph("Dashboard Outputs", styles["h2"]))
    story.append(data_table(
        ["Tab / Output", "Description"],
        [
            ["Survey Status",
             "Cumulative and daily submission counts, progress vs. target, pace projections, "
             "priority action items, enumerator and area completion tables"],
            ["Enumerator Behavior",
             "Flag rates per enumerator, indicator means comparison table with outlier highlighting, "
             "daily submission heatmap"],
            ["Data Quality",
             "Duplicate HHID detection, flag rates by indicator, FCS and rCSI distributions, "
             "FEWS NET illogicality matrix, missing data heatmap"],
            ["Flag Details",
             "Full flagged record tables per indicator with plain-language narrative explanations"],
            ["HTML Report",
             "Self-contained manager report — print to PDF via browser, no internet required"],
            ["Excel Error Log",
             "Colour-coded workbook with one sheet per indicator, ready for field team review"],
            ["Enumerator Feedback Excel",
             "One sheet per enumerator showing only their flagged records, with a summary sheet"],
        ],
        [44 * mm, PAGE_W - 2 * MARGIN - 44 * mm],
        styles,
    ))
    story.append(sp(4))

    # — How to use it
    story.append(Paragraph("How to Use the Tool", styles["h2"]))
    steps_intro = [
        ("1", "Install the application",
         "Follow the platform-specific setup instructions in this guide. "
         "Installation is required only once; subsequent launches use the provided "
         "one-click launcher script."),
        ("2", "Launch and upload your data",
         "Start the app and upload your survey file (CSV, Excel, Stata .dta, or SPSS .sav). "
         "The tool auto-detects context columns — HHID, enumerator, area, and date."),
        ("3", "Select indicators and adjust thresholds",
         "Enable the indicator modules present in your questionnaire. "
         "All thresholds (FCS cut-offs, timing limits, expenditure ceilings, minimum price) "
         "can be adjusted in the app UI without editing any files."),
        ("4", "Run Checks and review results",
         "Click ▶ Run Checks. Navigate the tabs to review flag rates by indicator and "
         "enumerator, logical contradictions, duplicates, and submission progress."),
        ("5", "Download field team reports",
         "Generate the Excel error log and per-enumerator feedback files. "
         "Share with supervisors or enumerators for daily field review."),
    ]
    for num, title, desc in steps_intro:
        row = Table(
            [[Paragraph(num, ParagraphStyle("sn", fontName="OpenSans-Bold", fontSize=11,
                                             textColor=C_WHITE, alignment=TA_CENTER, leading=14)),
              Paragraph(f"<b>{title}</b>", styles["h3"]),
            ]],
            colWidths=[9 * mm, PAGE_W - 2 * MARGIN - 9 * mm]
        )
        row.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, 0), C_PRIMARY),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (0, 0),  0),
            ("RIGHTPADDING",  (0, 0), (0, 0),  0),
            ("LEFTPADDING",   (1, 0), (1, 0),  10),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(KeepTogether([
            row,
            Paragraph(desc, ParagraphStyle("idesc", fontName="OpenSans", fontSize=9.5,
                                            textColor=C_MUTED, leading=14,
                                            leftIndent=19 * mm, spaceAfter=6, spaceBefore=2)),
        ]))

    story.append(sp(4))

    # — Data safety box
    safety_tbl = Table(
        [[Paragraph(
            "&#128274;  <b>Data Privacy Statement</b><br/>"
            "Survey HFC processes all data locally on the user's machine. "
            "No survey data, results, or any other information is transmitted "
            "to any external server, cloud service, or third party at any point during use.",
            ParagraphStyle("sp", fontName="OpenSans", fontSize=9.5,
                           textColor=C_PRIMARY, leading=15)
        )]],
        colWidths=[PAGE_W - 2 * MARGIN]
    )
    safety_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_PRIMARY_LT),
        ("LINEABOVE",     (0, 0), (-1, 0),  2, C_PRIMARY),
        ("TOPPADDING",    (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ("LEFTPADDING",   (0, 0), (-1, -1), 13),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 13),
    ]))
    story.append(safety_tbl)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — SETUP GUIDE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Local Installation Guide", styles["h1"]))
    story.append(hr(C_PRIMARY, thickness=1.2, sb=2, sa=10))

    story.append(Paragraph("What You Need", styles["h2"]))
    story.append(Paragraph(
        "Confirm you have the project folder and place it anywhere on your computer "
        "(for example, your Desktop). The folder should contain:",
        styles["body"]
    ))
    story.append(sp(4))
    story.append(data_table(
        ["File / Folder", "Purpose"],
        [
            ["`app.py`",                    "The application"],
            ["`requirements.txt`",           "List of software dependencies"],
            ["`config/`",                    "Threshold and column definition files"],
            ["`hfc/`",                       "Indicator check modules"],
            ["`Run HFC Checks.bat`",         "One-click launcher for Windows"],
            ["`Run HFC Checks.command`",     "One-click launcher for macOS"],
        ],
        [52 * mm, PAGE_W - 2 * MARGIN - 52 * mm],
        styles,
    ))
    story.append(sp(6))
    story.append(hr())

    # ── Shared render helper ───────────────────────────────────────────────────
    def render_os(banner_text, color, steps, shortcut_lines, stop_terminal):
        out = [sp(4), os_banner(banner_text, color, styles), sp(8)]
        for num, heading, code_lines, body_paras, note in steps:
            block = [step_row(num, heading, color, styles)]
            for p in body_paras:
                block.append(Paragraph(p, styles["body"]))
            if code_lines:
                block.append(sp(3))
                block.append(code_block(code_lines, styles))
            if note:
                block.append(sp(3))
                block.append(Paragraph(f"<i>{note}</i>", styles["note"]))
            block.append(sp(4))
            out.append(KeepTogether(block))
        out += [sp(4), shortcut_box(shortcut_lines, styles), sp(6),
                Paragraph(
                    f"To <b>stop the app</b>, press "
                    f'<font name="Courier" size="8.5">Ctrl + C</font> in {stop_terminal}.',
                    styles["body"]
                )]
        return out

    # ── macOS ─────────────────────────────────────────────────────────────────
    mac_steps = [
        (1, "Check Python is installed",
         ["python3 --version"],
         ["Open <b>Terminal</b> (&#8984; + Space, type <i>Terminal</i>, press Enter) "
          "and run the command above. You should see <b>Python 3.9.x</b> or higher.",
          "<b>If Python is not found:</b> download the latest 3.11.x installer "
          "from <i>python.org/downloads</i> and follow the prompts."], None),
        (2, "Navigate to the app folder",
         ['cd ~/Desktop/survey-hfc'],
         ['Run <font name="Courier" size="8.5">ls</font> to confirm '
          '<font name="Courier" size="8.5">app.py</font> and '
          '<font name="Courier" size="8.5">requirements.txt</font> are listed.'], None),
        (3, "One-click launch (recommended)",
         [],
         ['Double-click <b>Run HFC Checks.command</b>. On first run, macOS may block the file — '
          'right-click → Open → Open to allow execution. You only need to do this once. '
          'The script creates a virtual environment, installs all dependencies, and opens the app '
          'in your browser at '
          '<font name="Courier" size="8.5">http://localhost:8501</font>.'],
         None),
    ]

    mac_manual_steps = [
        (4, "Manual launch (alternative) — Create virtual environment",
         ["python3 -m venv venv"],
         ["Creates an isolated Python environment. First time only."], None),
        (5, "Activate the virtual environment",
         ["source venv/bin/activate"],
         ['The terminal prompt will show '
          '<font name="Courier" size="8.5">(venv)</font> when active.'], None),
        (6, "Install dependencies",
         ["pip install -r requirements.txt"],
         ["Downloads all required packages. This may take 1–2 minutes on first run."], None),
        (7, "Launch the application",
         ["streamlit run app.py"],
         ['A browser window will open at '
          '<font name="Courier" size="8.5">http://localhost:8501</font>. '
          "If it does not open automatically, paste that address into any browser."], None),
    ]

    story.extend(render_os(
        "macOS Instructions", C_MAC,
        mac_steps + mac_manual_steps,
        ["cd ~/Desktop/survey-hfc", "source venv/bin/activate", "streamlit run app.py"],
        "Terminal"
    ))
    story.append(hr())

    # ── Windows ───────────────────────────────────────────────────────────────
    win_steps = [
        (1, "Check Python is installed",
         ["python --version"],
         ["Open <b>Command Prompt</b> (Win + R, type <i>cmd</i>, press Enter). "
          "You should see <b>Python 3.9.x</b> or higher.",
          "<b>If Python is not found:</b> download the 3.11.x 64-bit installer from "
          "<i>python.org/downloads/windows</i>. On the first screen, tick "
          "<b>\"Add Python to PATH\"</b> before clicking Install Now."], None),
        (2, "Navigate to the app folder",
         [r'cd %USERPROFILE%\Desktop\survey-hfc'],
         ['Run <font name="Courier" size="8.5">dir</font> to confirm '
          '<font name="Courier" size="8.5">app.py</font> and '
          '<font name="Courier" size="8.5">requirements.txt</font> are listed.'], None),
        (3, "One-click launch (recommended)",
         [],
         ['Double-click <b>Run HFC Checks.bat</b>. If Windows Defender SmartScreen blocks it, '
          'click <b>More info</b> → <b>Run anyway</b>. '
          'The script creates a virtual environment on first run, installs all dependencies, '
          'and opens the app in your browser at '
          '<font name="Courier" size="8.5">http://localhost:8501</font>.'],
         None),
    ]

    win_manual_steps = [
        (4, "Manual launch (alternative) — Create virtual environment",
         ["python -m venv venv"], [], None),
        (5, "Activate the virtual environment",
         [r"venv\Scripts\activate"],
         ['The prompt will show <font name="Courier" size="8.5">(venv)</font>.'],
         "If activation is blocked by an execution policy error, open PowerShell as "
         "Administrator and run:  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser  "
         "Then return to Command Prompt and try again."),
        (6, "Install dependencies",
         ["pip install -r requirements.txt"], [], None),
        (7, "Launch the application",
         ["streamlit run app.py"],
         ['A browser window will open at '
          '<font name="Courier" size="8.5">http://localhost:8501</font>.'], None),
    ]

    story.extend(render_os(
        "Windows Instructions", C_WIN,
        win_steps + win_manual_steps,
        [r'cd %USERPROFILE%\Desktop\survey-hfc',
         r"venv\Scripts\activate", "streamlit run app.py"],
        "Command Prompt"
    ))
    story.append(hr())
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — COLUMN NAMING REFERENCE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Column Naming Reference", styles["h1"]))
    story.append(hr(C_PRIMARY, thickness=1.2, sb=2, sa=10))
    story.append(Paragraph(
        "Column names must match the VAM convention exactly (case-sensitive). "
        "The tool auto-detects context columns and matches indicator columns by name.",
        styles["body"]
    ))
    story.append(sp(6))

    story.append(Paragraph("Context Columns (auto-detected)", styles["h2"]))
    story.append(data_table(
        ["Purpose", "Accepted column names"],
        [
            ["Household ID",
             "`HHID`  `hhid`  `_uuid`  `uuid`  `instanceID`  `ID`"],
            ["Enumerator",
             "`EnuName`  `enumerator_name`  `enum_name`  `EnuID`  `enumerator` "
             "— or any column containing <i>enumerat</i>"],
            ["Supervisor",
             "`EnuSupervisorName`  `supervisor_name`  `supervisor` "
             "— or any column containing <i>supervis</i>"],
            ["Admin area",
             "`ID02`  `ID01`  `admin2`  `admin1`  `district`  `region`  `woreda`  `county`"],
            ["Survey date",
             "`SvyDate`  `today`  `_submission_time`  `SubmissionDate`  `date`"],
        ],
        [34 * mm, PAGE_W - 2 * MARGIN - 34 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Food Consumption Score (FCS)", styles["h2"]))
    story.append(Paragraph(
        "Values = days of consumption in the past 7 days (0–7). "
        "FCS = sum of weighted values (max 112). "
        "Classification: Poor ≤21  ·  Borderline 21.5–35  ·  Acceptable >35.",
        styles["body"]
    ))
    story.append(sp(4))
    story.append(data_table(
        ["Column", "Food group", "Weight"],
        [
            ["`FCSStap`",   "Cereals and starchy staples",  "×2"],
            ["`FCSPulse`",  "Pulses, legumes and nuts",     "×3"],
            ["`FCSDairy`",  "Dairy products",               "×4"],
            ["`FCSPr`",     "Meat, fish and eggs",          "×4"],
            ["`FCSVeg`",    "Vegetables",                   "×1"],
            ["`FCSFruit`",  "Fruits",                       "×1"],
            ["`FCSFat`",    "Oil and fats",                 "×0.5"],
            ["`FCSSugar`",  "Sugar and sweets",             "×0.5"],
        ],
        [34 * mm, PAGE_W - 2 * MARGIN - 60 * mm, 26 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Reduced Coping Strategies Index (rCSI)", styles["h2"]))
    story.append(Paragraph(
        "Values = days the strategy was used in the past 7 days (0–7). "
        "rCSI = sum of weighted values (max 56). Crisis threshold: ≥19.",
        styles["body"]
    ))
    story.append(sp(4))
    story.append(data_table(
        ["Column", "Strategy", "Weight"],
        [
            ["`rCSILessQlty`",  "Relied on less preferred or cheaper food",         "×1"],
            ["`rCSIBorrow`",    "Borrowed food or relied on help from others",       "×2"],
            ["`rCSIMealNb`",    "Reduced number of meals per day",                  "×1"],
            ["`rCSIMealSize`",  "Restricted portion sizes at mealtimes",            "×1"],
            ["`rCSIMealAdult`", "Adults restricted intake so children could eat",   "×3"],
        ],
        [34 * mm, PAGE_W - 2 * MARGIN - 60 * mm, 26 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Timing", styles["h2"]))
    story.append(data_table(
        ["Column", "Description"],
        [
            ["`start`", "Interview start timestamp — timezone-aware ISO 8601 (ODK / SurveyCTO device time)"],
            ["`end`",   "Interview end timestamp — must be after start"],
        ],
        [22 * mm, PAGE_W - 2 * MARGIN - 22 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Livelihood Coping Strategies (LCS)", styles["h2"]))
    story.append(data_table(
        ["Value", "Meaning"],
        [
            ["`10`",   "Strategy applied"],
            ["`20`",   "Not needed (household has enough food)"],
            ["`30`",   "Exhausted — no longer an option"],
            ["`9999`", "Not applicable to this household"],
        ],
        [22 * mm, PAGE_W - 2 * MARGIN - 22 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Expenditure Column Pattern", styles["h2"]))
    story.append(Paragraph(
        "Columns follow the pattern <font name='Courier' size='8.5'>{Category}{Source}</font>, "
        "for example <font name='Courier' size='8.5'>HHExpFCer_Purch_MN_7D</font>.",
        styles["body"]
    ))
    story.append(sp(4))
    story.append(data_table(
        ["Recall period", "Sources", "Food category prefixes"],
        [
            ["Food — 7-day",
             "`_Purch_MN_7D`  `_GiftAid_MN_7D`  `_OwnProd_MN_7D`",
             "`HHExpFCer`  `HHExpFTub`  `HHExpFPulse`  `HHExpFVeg`  `HHExpFFruit`  "
             "`HHExpFMeat`  `HHExpFFish`  `HHExpFDairy`  `HHExpFEgg`  `HHExpFOil`  "
             "`HHExpFSugar`  `HHExpFCond`  `HHExpFBev`  `HHExpFOther`"],
            ["Non-food — 1-month",
             "`_Purch_MN_1M`  `_GiftAid_MN_1M`",
             "`HHExpNFHyg`  `HHExpNFTrans`  `HHExpNFFuel`  `HHExpNFWat`  "
             "`HHExpNFComm`  `HHExpNFMed`  `HHExpNFEduc`  `HHExpNFOther`"],
            ["Non-food — 6-month",
             "`_Purch_MN_6M`  `_GiftAid_MN_6M`",
             "`HHExpNFCloth`  `HHExpNFRent`  `HHExpNFDurable`  `HHExpNFCerem`  `HHExpNFDebt`"],
        ],
        [28 * mm, 44 * mm, PAGE_W - 2 * MARGIN - 72 * mm],
        styles,
    ))
    story.append(hr())
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — CONFIGURATION REFERENCE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Configuration Reference", styles["h1"]))
    story.append(hr(C_PRIMARY, thickness=1.2, sb=2, sa=10))
    story.append(Paragraph(
        "All thresholds can be adjusted in the app UI without touching any files. "
        "To make changes permanent for a specific deployment, edit the YAML files "
        "in <font name='Courier' size='8.5'>config/configurable/</font>.",
        styles["body"]
    ))
    story.append(sp(6))

    story.append(Paragraph("FCS — config/configurable/fcs.yaml", styles["h2"]))
    story.append(data_table(
        ["Parameter", "Default", "Description"],
        [
            ["`low_fcs_threshold`",       "10",  "Flag FCS below this value"],
            ["`high_fcs_threshold`",      "100", "Flag FCS above this value"],
            ["`low_staple_threshold`",    "2",   "Flag FCSStap at or below this value"],
            ["`fcg_poor_threshold`",      "21",  "FCS Poor classification cut-off"],
            ["`fcg_borderline_threshold`","35",  "FCS Borderline classification cut-off"],
        ],
        [54 * mm, 20 * mm, PAGE_W - 2 * MARGIN - 74 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("rCSI — config/configurable/rcsi.yaml", styles["h2"]))
    story.append(data_table(
        ["Parameter", "Default", "Description"],
        [
            ["`high_rcsi_with_acceptable_fcg`", "18",
             "Flag high rCSI combined with Acceptable FCS category"],
        ],
        [64 * mm, 20 * mm, PAGE_W - 2 * MARGIN - 84 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Timing — config/configurable/timing.yaml", styles["h2"]))
    story.append(data_table(
        ["Parameter", "Default", "Description"],
        [
            ["`short_duration_min`",         "20",  "Flag interviews shorter than this many minutes"],
            ["`long_duration_min`",          "120", "Flag interviews longer than this many minutes"],
            ["`utc_offset_hours`",           "0",   "Local timezone offset from UTC"],
            ["`abnormal_early_morning_end`", "7",   "Flag interviews starting before this hour (24h)"],
            ["`abnormal_evening_start`",     "19",  "Flag interviews starting after this hour (24h)"],
        ],
        [54 * mm, 20 * mm, PAGE_W - 2 * MARGIN - 74 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Expenditure — config/configurable/hhexp.yaml", styles["h2"]))
    story.append(data_table(
        ["Parameter", "Default", "Description"],
        [
            ["`min_item_price`",              "0",
             "Minimum meaningful price in local currency. Any non-zero item below this value is "
             "flagged as implausibly small. Set to the price of a basic local purchase "
             "(e.g. bread, bus token). Leave at 0 to disable."],
            ["`max_single_item_food_7d`",     "1,000,000", "Flag food items above this value"],
            ["`max_single_item_nonfood_1m`",  "1,000,000", "Flag short-term non-food items above this value"],
            ["`max_single_item_nonfood_6m`",  "5,000,000", "Flag long-term non-food items above this value"],
            ["`flag_zero_total_food`",        "true",      "Flag households where all food expenditure is zero"],
        ],
        [54 * mm, 22 * mm, PAGE_W - 2 * MARGIN - 76 * mm],
        styles,
    ))
    story.append(sp(8))

    story.append(Paragraph("Demographics — config/configurable/demo.yaml", styles["h2"]))
    story.append(data_table(
        ["Parameter", "Default", "Description"],
        [
            ["`high_hhsize_threshold`", "30", "Flag households larger than this size"],
        ],
        [54 * mm, 20 * mm, PAGE_W - 2 * MARGIN - 74 * mm],
        styles,
    ))
    story.append(hr())

    # ── Troubleshooting ────────────────────────────────────────────────────────
    story.append(Paragraph("Troubleshooting", styles["h2"]))
    story.append(data_table(
        ["Problem", "Likely Cause", "Solution"],
        [
            ["`python3: command not found`",
             "Python is not installed",
             "Follow Step 1 for your operating system"],
            ["`pip: command not found`",
             "pip not on PATH",
             "Use `python3 -m pip install -r requirements.txt`"],
            ["`ModuleNotFoundError: No module named 'streamlit'`",
             "Virtual environment not active",
             "Run the activate command before launching"],
            ["No flags generated after upload",
             "Column names do not match convention",
             "Check names against the column reference — matching is case-sensitive"],
            ["Timing module produces no output",
             "Timestamps not timezone-aware",
             "Ensure `start` and `end` are in ODK/SurveyCTO default ISO 8601 format"],
            ["Browser does not open automatically",
             "Streamlit cannot detect browser",
             "Navigate manually to `http://localhost:8501`"],
            ["Port 8501 already in use",
             "Another Streamlit instance is running",
             "Stop it with Ctrl + C, or use `--server.port 8502`"],
            ["Windows: `activate` execution policy error",
             "PowerShell security setting",
             "Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell as Administrator"],
            ["macOS: launcher blocked",
             "Gatekeeper security setting",
             "Right-click → Open → Open"],
            ["Stata file fails to load",
             "Duplicate value labels",
             "The tool will retry automatically with numeric codes and show an info message"],
        ],
        [48 * mm, 40 * mm, PAGE_W - 2 * MARGIN - 88 * mm],
        styles,
    ))
    story.append(hr())

    # ── FAQ ────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Frequently Asked Questions", styles["h2"]))
    faqs = [
        ("Is my data safe?",
         "Yes. The application runs entirely on your local machine. No survey data, results, "
         "or any other information is transmitted to any external server at any point."),
        ("Can I run this without an internet connection?",
         "Yes. Once dependencies are installed the app runs fully offline. An internet connection "
         "is only needed the first time, to install packages."),
        ("Can I use data that does not follow the VAM column naming?",
         "The indicator modules require exact column name matches. You can rename columns in your "
         "data export, or adjust the column lists in config/standard/<indicator>.yaml to match "
         "your own naming convention."),
        ("How do I add a new country or context?",
         "Adjust the thresholds in config/configurable/ for the specific context (currency scale, "
         "working hours, household size norms). No code changes are needed."),
        ("What is the minimum meaningful price parameter?",
         "Set min_item_price in config/configurable/hhexp.yaml to the price of the cheapest "
         "plausible local purchase (e.g. a loaf of bread or a bus token). Any expenditure item "
         "recorded as non-zero but below this floor will be flagged as a likely digit-drop entry error. "
         "Leave at 0 to disable."),
        ("Where are downloaded reports saved?",
         "Reports are saved to your browser's default download folder."),
        ("How do I update the app when a new version is available?",
         "Replace the project files with the new version. Re-run pip install -r requirements.txt "
         "with the virtual environment active to update any changed dependencies."),
    ]
    for q, a in faqs:
        story.append(KeepTogether([
            Paragraph(q, styles["faq_q"]),
            Paragraph(a, styles["faq_a"]),
        ]))

    story.append(sp(12))
    story.append(hr(C_PRIMARY, thickness=1, sb=4, sa=6))
    story.append(Paragraph(
        "Survey HFC  ·  Aligned with iehfc (World Bank DIME) and SurveyCTO HFC frameworks",
        styles["footer"]
    ))

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
    print(f"PDF saved: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
