"""
Survey HFC — Streamlit web interface.
Three outputs:
  Tab 1 · Dashboard  — live charts and survey statistics
  Tab 2 · Details    — flagged records per indicator
  Tab 3 · Downloads  — HTML manager report + Excel field-team error log
"""

import io
import logging
import math
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Survey HFC",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design system — matches XLSForm Reviewer, Open Sans font ─────────────────
st.markdown("""
<style>
  /* ── Open Sans via Google Fonts ─────────────────────────────────────────── */
  @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700;800&display=swap');

  /* Apply Open Sans to the app shell — inherits naturally downward.
     Do NOT use !important here so Streamlit's icon font rules can still win. */
  html, body { font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

  /* Target only genuine text-bearing elements with !important */
  p, h1, h2, h3, h4, h5, h6, li, td, th, caption,
  label, button, input, textarea, select,
  [data-testid="stMarkdownContainer"],
  [data-testid="stText"],
  [data-testid="stCaptionContainer"],
  [data-testid="stMetricLabel"],
  [data-testid="stMetricValue"],
  [class*="css"] {
    font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  }

  /* ── Global type scale ───────────────────────────────────────────────────── */
  html, body, [class*="css"] { font-size: .875rem; }
  h1 { font-size: 1.6rem !important; font-weight: 800 !important;
       color: #1e293b !important; letter-spacing: -.3px; margin-bottom: .1rem; }
  h2 { font-size: .875rem !important; font-weight: 700 !important; color: #334155 !important; }
  h3 { font-size: .84rem  !important; font-weight: 600 !important; color: #475569 !important; }
  p, li, div { font-size: .84rem; }

  /* hide the sidebar toggle arrow entirely */
  [data-testid="stSidebarCollapsedControl"] { display: none !important; }

  /* ── Threshold card on main page ─────────────────────────────────────────── */
  .thr-card {
    background: white; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: .85rem 1rem; margin-bottom: .85rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
  }
  .thr-title {
    font-size: .69rem; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: .07em;
    margin-bottom: .5rem; padding-bottom: .28rem;
    border-bottom: 1px solid #f0f2f5;
  }
  /* compact number inputs */
  [data-testid="stNumberInput"] input {
    font-size: .81rem !important; padding: .27rem .5rem !important; }
  [data-testid="stNumberInput"] label { font-size: .75rem !important; color: #64748b; }
  [data-testid="stNumberInput"] { margin-bottom: -.25rem !important; }

  /* ── Metric cards ────────────────────────────────────────────────────────── */
  [data-testid="metric-container"] {
    background: white; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: .55rem .8rem !important; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
  [data-testid="metric-container"] label {
    font-size: .64rem !important; color: #64748b !important;
    text-transform: uppercase; letter-spacing: .05em; font-weight: 600 !important; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.2rem !important; font-weight: 800 !important; color: #1e293b !important; }
  [data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: .69rem !important; }

  /* ── Buttons ─────────────────────────────────────────────────────────────── */
  [data-testid="stDownloadButton"] button,
  [data-testid="stBaseButton-primary"] {
    background: #6a9cc8 !important; color: white !important; border: none !important;
    font-weight: 600 !important; font-size: .84rem !important;
    border-radius: 8px !important; padding: .5rem 1rem !important; }
  [data-testid="stDownloadButton"] button:hover,
  [data-testid="stBaseButton-primary"]:hover { background: #5a8cb8 !important; }
  [data-testid="stBaseButton-secondary"] {
    border-color: #cbd5e1 !important; color: #475569 !important;
    font-size: .84rem !important; border-radius: 8px !important; }

  /* ── Tabs ────────────────────────────────────────────────────────────────── */
  [data-baseweb="tab-list"] { gap: 4px; border-bottom: 2px solid #e2e8f0; }
  [data-baseweb="tab"] { font-size: .82rem !important; padding: .4rem .85rem !important;
    color: #64748b !important; border-radius: 6px 6px 0 0 !important; }
  [data-baseweb="tab"][aria-selected="true"] {
    color: #6a9cc8 !important; font-weight: 700 !important;
    border-bottom: 2px solid #6a9cc8 !important; }

  /* ── File uploader ───────────────────────────────────────────────────────── */
  [data-testid="stFileUploader"] { margin-bottom: .5rem; }
  [data-testid="stFileUploaderDropzoneInstructions"] { font-size: .8rem !important; }

  /* ── Misc ────────────────────────────────────────────────────────────────── */
  [data-testid="stAlert"]  { font-size: .82rem !important; border-radius: 8px; }
  [data-testid="stAlert"] p { font-size: .82rem !important; }
  [data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 8px; }
  [data-testid="stProgressBar"] > div { background: #6a9cc8 !important; }
  [data-testid="stCaptionContainer"] p { font-size: .72rem !important; color: #94a3b8; }
  hr { border-color: #e2e8f0 !important; margin: .55rem 0 !important; }
  [data-testid="stExpander"] { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }

  /* ── Priority action items ───────────────────────────────────────────────── */
  .prio-critical { color:#dc2626; font-weight:600; font-size:.82rem; margin:.18rem 0; }
  .prio-warning  { color:#d97706; font-weight:600; font-size:.82rem; margin:.18rem 0; }
  .prio-ok       { color:#16a34a; font-weight:600; font-size:.82rem; margin:.18rem 0; }

  /* ── HFC inline table ────────────────────────────────────────────────────── */
  .hfc-table { width:100%; border-collapse:collapse; font-size:.81rem; margin-top:.3rem; text-align:center; }
  .hfc-table th { background:#f1f5f9; text-align:center; padding:.38rem .7rem;
    font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:.04em;
    font-size:.67rem; border-bottom:2px solid #e2e8f0; }
  .hfc-table td { padding:.52rem .7rem; border-bottom:1px solid #f0f2f5; vertical-align:middle; text-align:center; }
  .hfc-table tr:last-child td { border-bottom:none; }
  .hfc-table tr:hover td { background:#f8fafc; }
</style>
""", unsafe_allow_html=True)

logging.getLogger("hfc").setLevel(logging.WARNING)

from hfc.utils.config_handler import ConfigHandler
from hfc.reports.excel_reporter import ExcelReporter
from hfc.reports.html_reporter import compute_stats, generate_html
from hfc.indicators import get_indicator_class

TOOL_DIR = Path(__file__).parent
CFG_DIR  = TOOL_DIR / "config"

ALL_INDICATORS = [
    "Demo", "FCS", "HDDS", "rCSI", "Housing",
    "LCS", "HHExpF", "HHExpNF1M", "HHExpNF6M", "Timing",
]

INDICATOR_DESC = {
    "Demo":      "Household composition by age/sex group — checks size plausibility, age-sex sum consistency, and presence of adults",
    "FCS":       "Food Consumption Score — weighted dietary diversity over 7-day recall (max 112). Poor ≤21, Borderline 21.5–35, Acceptable >35",
    "HDDS":      "Household Dietary Diversity Score — count of food groups consumed in the past 24h (0–12 groups, no weighting)",
    "rCSI":      "Reduced Coping Strategies Index — 5 weighted strategies over 7-day recall (max 56). Score ≥19 indicates crisis-level food insecurity",
    "Housing":   "Housing tenure and dwelling type — checks for implausible or missing housing status responses",
    "LCS":       "Livelihood Coping Strategies (Food Security) — stress / crisis / emergency asset-depletion behaviours over 30-day recall",
    "HHExpF":    "Food expenditure — all food sources (purchased + gift/aid + own production) over 7-day recall, annualised for FES calculation",
    "HHExpNF1M": "Short-term non-food expenditure — hygiene, transport, fuel, water, communication, etc. over 30-day recall",
    "HHExpNF6M": "Long-term non-food expenditure — health, education, clothing, rent, furniture over 6-month recall (converted to monthly)",
    "Timing":    "Interview timing — flags suspiciously short/long interviews, end-before-start errors, and abnormal start hours",
}

# ── WFP methodology reference — shown in Details tab and Methodology tab ───────
INDICATOR_METHODOLOGY = {
    "FCS": {
        "full_name": "Food Consumption Score (FCS)",
        "source": "WFP VAM — vamresources.manuals.wfp.org",
        "recall": "7 days",
        "formula": "FCS = (FCSStap×2) + (FCSPulse×3) + (FCSDairy×4) + (FCSPr×4) + (FCSVeg×1) + (FCSFruit×1) + (FCSFat×0.5) + (FCSSugar×0.5)",
        "range": "0–112",
        "thresholds": "Poor ≤21 | Borderline 21.5–35 | Acceptable >35  (use 28/42 in high sugar-oil contexts)",
        "groups": [
            ("FCSStap",  "Cereals / Starchy staples", "×2", "Maize, rice, bread, sorghum, cassava, potatoes"),
            ("FCSPulse", "Pulses / Legumes / Nuts",   "×3", "Beans, lentils, peas, groundnuts, soy"),
            ("FCSDairy", "Dairy products",             "×4", "Milk, yogurt, cheese"),
            ("FCSPr",    "Meat / Fish / Eggs",         "×4", "Beef, goat, poultry, fish, eggs"),
            ("FCSVeg",   "Vegetables",                 "×1", "All vegetables incl. dark leafy greens"),
            ("FCSFruit", "Fruits",                     "×1", "Mango, banana, citrus, papaya"),
            ("FCSFat",   "Oil / Fat",                  "×0.5", "Vegetable oil, butter, palm oil"),
            ("FCSSugar", "Sugar / Sweets",             "×0.5", "Sugar, honey, jam, pastries"),
            ("FCSCond",  "Condiments (not scored)",    "—", "Salt, spices, tea, coffee — recorded for plausibility only"),
        ],
        "quality_flags": {
            "Identical":        "All 8 food group values are identical — possible enumerator fabrication or rushing",
            "LowStaple":        "Staple foods (FCSStap) consumed ≤1 day — highly suspicious; cereals are near-universally consumed daily",
            "LowFCS":           "FCS below the configured low threshold — verify Poor FCG classification is expected",
            "HighFCS":          "FCS near or at the theoretical maximum (112) — all groups consumed every day; warrants verification",
        },
    },
    "rCSI": {
        "full_name": "Reduced Coping Strategies Index (rCSI)",
        "source": "WFP VAM — vamresources.manuals.wfp.org",
        "recall": "7 days",
        "formula": "rCSI = (rCSILessQlty×1) + (rCSIBorrow×2) + (rCSIMealNb×1) + (rCSIMealSize×1) + (rCSIMealAdult×3)",
        "range": "0–56",
        "thresholds": "Minimal 0–3 | Moderate 4–18 | Severe (crisis) ≥19 | Extreme ≥43",
        "groups": [
            ("rCSILessQlty",  "Relied on less preferred / cheaper food",              "×1", "Lowest severity — dietary quality reduction"),
            ("rCSIBorrow",    "Borrowed food or relied on help from relatives/friends","×2", "Social cost — external dependency"),
            ("rCSIMealNb",    "Reduced number of meals per day",                      "×1", "Frequency reduction"),
            ("rCSIMealSize",  "Restricted portion sizes at mealtimes",                "×1", "Quantity reduction"),
            ("rCSIMealAdult", "Adults restricted intake so children could eat",        "×3", "Highest severity — intra-HH sacrifice"),
        ],
        "quality_flags": {
            "Identical":               "All 5 strategy values are identical — possible rushing",
            "ZeroWithPoorFCG":         "rCSI = 0 (no coping) but FCS is Poor — contradiction; a household in food crisis should be coping",
            "HighWithAcceptFCG":       f"High rCSI (≥19) combined with Acceptable FCS — severe coping inconsistent with adequate diet; warrants field follow-up",
            "AdultMealNoChildren":     "rCSIMealAdult > 0 but household has no children — adults cannot restrict intake 'for children' if none present",
        },
    },
    "HDDS": {
        "full_name": "Household Dietary Diversity Score (HDDS)",
        "source": "WFP VAM / FANTA — vamresources.manuals.wfp.org",
        "recall": "24 hours",
        "formula": "HDDS = sum of 12 binary food-group flags (0 or 1 each) — no weighting",
        "range": "0–12",
        "thresholds": "Severely food insecure 0–3 | Moderately food insecure 4–5 | Food secure 6–12",
        "groups": [
            ("HDDSStapCer",  "Cereals",             "Binary", "Maize, rice, bread, sorghum, millet"),
            ("HDDSStapRoot", "Roots & Tubers",       "Binary", "Cassava, sweet potato, yam, potato"),
            ("HDDSPulse",    "Pulses / Legumes",     "Binary", "Beans, lentils, peas, cowpeas, soy"),
            ("HDDSDairy",    "Dairy",                "Binary", "Milk, yogurt, cheese"),
            ("HDDSPrMeat",   "Meat / Poultry",       "Binary", "Beef, goat, chicken, organ meats"),
            ("HDDSPrEggs",   "Eggs",                 "Binary", "Eggs (any type)"),
            ("HDDSPrFish",   "Fish / Seafood",       "Binary", "Fresh or canned fish, shellfish"),
            ("HDDSVeg",      "Vegetables",           "Binary", "All vegetables, dark leafy greens"),
            ("HDDSFruit",    "Fruits",               "Binary", "Fresh or dried fruits"),
            ("HDDSFat",      "Oil / Fat",            "Binary", "Vegetable oil, butter, lard"),
            ("HDDSSugar",    "Sugar / Honey",        "Binary", "Sugar, honey, sweets, jam"),
            ("HDDSCond",     "Misc / Condiments",    "Binary", "Salt, spices, tea, coffee"),
        ],
        "quality_flags": {
            "Identical": "All 12 binary food group values are identical (all 0 or all 1)",
            "LowHDDS":   "HDDS ≤2 — extremely limited diet; only 1–2 food groups consumed in 24h",
            "HighHDDS":  "HDDS ≥10 — 10+ distinct food groups in a single day; plausible only in food-secure contexts",
        },
    },
    "Demo": {
        "full_name": "Demographics — Household Composition",
        "source": "WFP FSNA Standard Questionnaire",
        "recall": "Current household roster",
        "formula": "Sum checks: Sum_M + Sum_F = HHSize; Sum_Adults + Sum_Children = HHSize",
        "range": "HH size typically 1–20; context-dependent",
        "thresholds": "Flag HH size >30 (configurable); flag zero adults; flag PLW count exceeding reproductive-age women",
        "groups": [
            ("HHSize",     "Total household size",                  "—", "Sum of all age-sex groups"),
            ("HHSizeM",    "Males (total)",                         "—", "Sum across male age groups"),
            ("HHSizeF",    "Females (total)",                       "—", "Sum across female age groups"),
            ("PLW",        "Pregnant / Lactating Women",            "—", "Cannot exceed females aged 12–59"),
        ],
        "quality_flags": {
            "HighHHSize":   "Household size exceeds the configured maximum — verify it is not a data entry error",
            "SumMismatch":  "Sum of age-sex sub-groups does not match the reported total HH size",
            "NoAdults":     "No adults (18+) in the household — logically implausible for an interviewed household",
            "PLWExceeds":   "Pregnant/lactating women count exceeds the number of women of reproductive age (12–59)",
        },
    },
    "LCS": {
        "full_name": "Livelihood Coping Strategies — Food Security (LCS-FS)",
        "source": "WFP VAM — vamresources.manuals.wfp.org",
        "recall": "30 days (active); 12 months (exhausted)",
        "formula": "Hierarchical: max severity reached → 1=No coping | 2=Stress | 3=Crisis | 4=Emergency",
        "range": "4 severity categories",
        "thresholds": "Stress: reversible asset drawdown | Crisis: productive asset loss, school withdrawal | Emergency: land sale, begging, illegal acts",
        "groups": [
            ("Lcs_stress_DomAsset",  "Sold household assets (radio, furniture, jewellery)", "Stress",    "Reduces resilience to future shocks"),
            ("Lcs_stress_BorrowCash","Borrowed money due to food shortage",                  "Stress",    "Increases debt burden"),
            ("Lcs_stress_Saving",    "Spent savings due to food shortage",                   "Stress",    "Depletes safety net"),
            ("Lcs_stress_EatOut",    "Sent members to eat elsewhere",                        "Stress",    "Loss of household cohesion"),
            ("Lcs_crisis_ProdAssets","Sold productive assets or transport",                  "Crisis",    "Reduces future income capacity — difficult to reverse"),
            ("Lcs_crisis_Health",    "Reduced health / medicine expenditure",                "Crisis",    "Human capital degradation"),
            ("Lcs_crisis_OutSchool", "Withdrew children from school",                        "Crisis",    "Long-term human capital loss"),
            ("Lcs_em_ResAsset",      "Sold or mortgaged house / land",                       "Emergency", "Loss of residence — extremely difficult to reverse"),
            ("Lcs_em_Begged",        "Begged or scavenged for food",                         "Emergency", "Dignity and safety risk"),
            ("Lcs_em_IllegalAct",    "Engaged in illegal / high-risk income activities",     "Emergency", "Life-threatening; deepest crisis indicator"),
        ],
        "quality_flags": {
            "Identical":             "All strategy responses are identical across the module",
            "ChildStratNoChildren":  "Child-related strategy (school withdrawal) answered Yes/No when no school-age children in household",
            "AllNotApplicable":      "Nearly all strategies coded N/A — possible enumerator shortcut; verify context",
        },
    },
    "HHExpF": {
        "full_name": "Food Expenditure (7-day recall)",
        "source": "WFP FSNA — used for Food Expenditure Share (FES) calculation",
        "recall": "7 days (multiplied by 30/7 to get monthly equivalent)",
        "formula": "MonthlyFoodExp = (Purchased + GiftAid + OwnProduction) × 30/7",
        "range": "≥0; zero food expenditure across all sources is implausible",
        "thresholds": "FES = TotalFoodExp / TotalExpenditure: Low <50% | Medium 50–65% | High 65–75% | Very High >75%",
        "groups": [
            ("HHExpFCer",  "Cereals & grains",           "7-day", "Maize, rice, sorghum, wheat flour"),
            ("HHExpFPuls", "Pulses & legumes",            "7-day", "Beans, lentils, peas"),
            ("HHExpFVeg",  "Vegetables",                  "7-day", "All fresh/dried vegetables"),
            ("HHExpFFrt",  "Fruits",                      "7-day", "Fresh or dried fruits"),
            ("HHExpFAniml","Meat / Fish / Eggs / Dairy",  "7-day", "All animal-source foods"),
            ("HHExpFOil",  "Oil & fats",                  "7-day", "Cooking oil, butter, margarine"),
            ("HHExpFSugar","Sugar & confectionery",       "7-day", "Sugar, honey, sweets"),
            ("HHExpFCond", "Condiments & beverages",      "7-day", "Salt, spices, tea, coffee"),
            ("HHExpFOut",  "Meals outside / snacks",      "7-day", "Street food, restaurant meals"),
        ],
        "quality_flags": {
            "AllMissing":    "All food expenditure items are missing — entire module not completed",
            "NegativeValue": "One or more expenditure items have a negative value — impossible; likely data entry error",
            "BelowMinPrice": "At least one item is non-zero but below the minimum meaningful price — possible digit-drop entry error (e.g. '5' entered instead of '500')",
            "ExtremeItem":   "At least one item exceeds the maximum plausible single-item threshold — possible extra digit or unit confusion",
            "ZeroTotal":     "All food expenditure sources are zero — implausible unless fully subsistence or aid-dependent; verify with field team",
        },
    },
    "HHExpNF1M": {
        "full_name": "Short-term Non-Food Expenditure (30-day recall)",
        "source": "WFP FSNA — component of FES denominator",
        "recall": "30 days",
        "formula": "Monthly non-food (short-term) = sum of all short-term NF items over 30 days",
        "range": "≥0",
        "thresholds": "Included in total expenditure denominator for FES",
        "groups": [
            ("HHExpNFHyg",  "Hygiene / personal care",   "30-day", "Soap, shampoo, sanitary items"),
            ("HHExpNFTrans","Transport",                   "30-day", "Bus, fuel for vehicles"),
            ("HHExpNFFuel", "Cooking fuel",               "30-day", "Firewood, charcoal, kerosene, gas"),
            ("HHExpNFWat",  "Water",                      "30-day", "Purchased drinking/domestic water"),
            ("HHExpNFElec", "Electricity / lighting",     "30-day", "Grid, generator, solar, candles"),
            ("HHExpNFComm", "Communication",              "30-day", "Mobile airtime, internet"),
        ],
        "quality_flags": {
            "AllMissing":    "All short-term non-food items are missing",
            "NegativeValue": "One or more items have a negative value",
            "BelowMinPrice": "At least one item is non-zero but below the minimum meaningful price — possible digit-drop entry error",
            "ExtremeItem":   "At least one item exceeds the maximum plausible single-item threshold",
        },
    },
    "HHExpNF6M": {
        "full_name": "Long-term Non-Food Expenditure (6-month recall)",
        "source": "WFP FSNA — component of FES denominator (divided by 6 for monthly equivalent)",
        "recall": "6 months (÷6 to convert to monthly)",
        "formula": "Monthly non-food (long-term) = sum of 6-month NF items ÷ 6",
        "range": "≥0",
        "thresholds": "Included in total expenditure denominator for FES",
        "groups": [
            ("HHExpNFHealth","Health services / medicines",  "6-month", "Doctor visits, medications, hospital"),
            ("HHExpNFEduc",  "Education",                    "6-month", "School fees, uniforms, books"),
            ("HHExpNFCloth", "Clothing & footwear",          "6-month", "All clothing for household members"),
            ("HHExpNFRent",  "Rent / accommodation",         "6-month", "If not owner-occupied"),
            ("HHExpNFFurn",  "Furniture / utensils",         "6-month", "Pots, mats, bedding, household goods"),
        ],
        "quality_flags": {
            "AllMissing":    "All long-term non-food items are missing",
            "NegativeValue": "One or more items have a negative value",
            "BelowMinPrice": "At least one item is non-zero but below the minimum meaningful price — possible digit-drop entry error",
            "ExtremeItem":   "At least one item exceeds the maximum plausible single-item threshold",
        },
    },
    "Housing": {
        "full_name": "Housing Status & Tenure Type",
        "source": "WFP FSNA Standard Questionnaire",
        "recall": "Current status",
        "formula": "Categorical checks against valid choice list",
        "range": "Defined choice list per country questionnaire",
        "thresholds": "Flags missing/invalid codes and implausible combinations",
        "groups": [],
        "quality_flags": {
            "Missing":  "Housing tenure or dwelling type response is missing",
            "Erroneous":"Housing response is outside the valid choice list",
        },
    },
    "Timing": {
        "full_name": "Interview Timing & Duration",
        "source": "ODK / SurveyCTO metadata",
        "recall": "Device-recorded start and end timestamps",
        "formula": "Duration (min) = (EndTime − StartTime) in minutes",
        "range": "Typical full food security questionnaire: 30–90 minutes",
        "thresholds": "Short <10 min (configurable) | Long >120 min (configurable) | Flag before 07:00 or after 19:00",
        "groups": [
            ("starttime", "Interview start timestamp", "—", "Device-recorded; check for abnormal hours"),
            ("endtime",   "Interview end timestamp",   "—", "Must be after start time"),
        ],
        "quality_flags": {
            "InvalidDuration": "End time is before or equal to start time — device clock error or data entry mistake",
            "ShortDuration":   "Interview completed below the minimum plausible duration — possible enumerator fabrication or skipping questions",
            "LongDuration":    "Interview exceeded the maximum plausible duration — possible pause, device left on, or data entry error",
            "AbnormalHour":    "Interview started before 07:00 or after 19:00 — unlikely working hours; verify with field team",
        },
    },
}

# ── Design tokens ─────────────────────────────────────────────────────────────
_C = {
    "primary": "#6a9cc8", "purple": "#9888c8", "teal": "#6ab0c8",
    "crit_fg": "#cc8080", "crit_bg": "#fdf0f0",
    "high_fg": "#cc9470", "high_bg": "#fdf5ee",
    "med_fg":  "#ccb460", "med_bg":  "#fdf8e8",
    "ok_fg":   "#6aab90", "ok_bg":   "#e8f6f0",
    "poor": "#cc8080", "border": "#ccb460", "accept": "#6aab90",
    "slate7": "#64748b", "slate5": "#94a3b8", "line": "#e2e8f0",
}
_PLOTLY_CFG = {"displayModeBar": False}


# ── Column auto-detection ─────────────────────────────────────────────────────

def _find_col(df, *candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def _find_col_pat(df, *patterns):
    for pat in patterns:
        for c in df.columns:
            if pat.lower() in c.lower():
                return c
    return None

def _ctx(df):
    """Return dict of auto-detected context columns."""
    hhid = _find_col(df, "HHID","hhid","_uuid","uuid","instanceID","ID")
    enu  = (_find_col(df, "EnuName","enumerator_name","enum_name","EnuID","enumerator")
            or _find_col_pat(df, "enumerat"))
    sup  = (_find_col(df, "EnuSupervisorName","supervisor_name","supervisor")
            or _find_col_pat(df, "supervis"))
    area = (_find_col(df, "ID02","ID01","admin2","admin1","district","region","woreda","county")
            or _find_col_pat(df, "admin2","admin1","district","region","area"))
    date = _find_col(df, "SvyDate","today","_submission_time","submission_time","SubmissionDate","date")
    return {"hhid": hhid, "enu": enu, "sup": sup, "area": area, "date": date}


def _duplicate_check(working_df: pd.DataFrame, ctx: dict):
    """Return (n_dupe_ids, dupe_df) — dupe_df includes key demographics for side-by-side comparison."""
    hhid_col = ctx.get("hhid")
    if not hhid_col or hhid_col not in working_df.columns:
        return 0, pd.DataFrame()
    counts = working_df[hhid_col].value_counts()
    dupes  = counts[counts > 1]
    if dupes.empty:
        return 0, pd.DataFrame()
    # Core ID + context columns
    id_cols  = [c for c in [hhid_col, ctx.get("enu"), ctx.get("area"), ctx.get("date")] if c]
    # Key demographics for comparison
    demo_cols = [c for c in ["HHSize", "HHStatus", "FCS", "FCG", "rCSI",
                              "Timing_Duration_Min"] if c in working_df.columns]
    show_cols = list(dict.fromkeys(id_cols + demo_cols))  # preserve order, no dupes
    dupe_df = (working_df[working_df[hhid_col].isin(dupes.index)][show_cols]
               .sort_values(hhid_col).reset_index(drop=True))
    # Round numeric demo cols for readability
    for col in ["FCS", "rCSI", "Timing_Duration_Min"]:
        if col in dupe_df.columns:
            dupe_df[col] = pd.to_numeric(dupe_df[col], errors="coerce").round(1)
    return len(dupes), dupe_df


def _show_table(df, styler=None, max_rows: int = 200):
    """Render a dataframe: center-aligned, no empty rows, smart number formatting.

    Formatting rules applied per column dtype:
      • Flag_* float columns  → integer (0 / 1)
      • Other float columns   → 1 decimal place
      • NaN / None            → "—"
    """
    n = min(len(df), max_rows)
    h = (n + 1) * 35 + 3           # header ~35 px + 35 px per row + border
    base = df.head(n)

    # Build column-level format dict
    fmt: dict = {}
    for col in base.columns:
        if pd.api.types.is_float_dtype(base[col]):
            fmt[col] = "{:.0f}" if col.startswith("Flag_") else "{:.1f}"

    if styler is not None:
        # Apply format + alignment on top of the caller's styler
        styler = (styler
                  .format(fmt, na_rep="—")
                  .set_properties(**{"text-align": "center"})
                  .set_properties(subset=[base.columns[0]], **{"text-align": "left"}))
        st.dataframe(styler, use_container_width=True, height=h)
    else:
        styled = (base.style
                  .format(fmt, na_rep="—")
                  .set_properties(**{"text-align": "center"})
                  .set_properties(subset=[base.columns[0]], **{"text-align": "left"}))
        st.dataframe(styled, use_container_width=True, height=h)


def _flag_style(rate: float) -> tuple[str, str]:
    if rate > 20: return _C["crit_fg"], _C["crit_bg"]
    if rate > 10: return _C["high_fg"], _C["high_bg"]
    if rate > 0:  return _C["med_fg"],  _C["med_bg"]
    return _C["ok_fg"], _C["ok_bg"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def run_checks(df: pd.DataFrame, enabled: list, cfg_overrides: dict):
    cfg_handler = ConfigHandler(str(CFG_DIR))
    base_cfg    = cfg_handler.load_configurable_config("base")
    priority    = ["Demo","FCS","HDDS","rCSI","Housing","LCS",
                   "HHExpF","HHExpNF1M","HHExpNF6M","Timing"]
    ordered = [n for n in priority if n in enabled]

    results: dict[str, pd.DataFrame] = {}
    working_df = df.copy()
    progress = st.progress(0, text="Running checks…")
    for i, name in enumerate(ordered):
        progress.progress((i + 1) / len(ordered), text=f"Checking {name}…")
        try:
            cls     = get_indicator_class(name)
            std_cfg = cfg_handler.load_standard_config(name)
            c_cfg   = cfg_handler.load_configurable_config(name)
            if name in ("HHExpF","HHExpNF1M","HHExpNF6M"):
                std_cfg = cfg_handler.load_standard_config("hhexp")
                c_cfg   = cfg_handler.load_configurable_config("hhexp")
            c_cfg.update(cfg_overrides.get(name, {}))
            ind = cls(df=working_df, std_config=std_cfg, cfg_config=c_cfg, base_config=base_cfg)
            result_df = ind.run()
            results[name] = result_df
            for col in ind.df.columns:
                if col not in working_df.columns:
                    working_df[col] = ind.df[col]
        except Exception as exc:
            st.warning(f"⚠ {name}: {exc}")
    progress.empty()
    return results, working_df


def _build_excel_bytes(results, raw_df):
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
    ExcelReporter(output_path=tmp_path).generate(results, raw_df)
    data = Path(tmp_path).read_bytes()
    Path(tmp_path).unlink(missing_ok=True)
    return data


def _build_html_bytes(results, working_df, name):
    return generate_html(results, working_df, survey_name=name).encode("utf-8")



# ── Config panel (main page) ──────────────────────────────────────────────────

def render_config():
    """Renders the indicators + thresholds config panel. Returns (enabled, overrides)."""

    st.markdown('<div class="thr-card">', unsafe_allow_html=True)

    col_ind, col_thr = st.columns([2, 3], gap="large")

    # ── Left: Sample target + Indicators ─────────────────────────────────────
    with col_ind:
        st.markdown('<div class="thr-title">Survey Progress</div>', unsafe_allow_html=True)
        sample_target = st.number_input(
            "Designed sample size (leave 0 to skip progress tracking)",
            value=0, min_value=0, step=50, key="sample_target",
            help="Total number of households planned for this survey. Used to track completion % on the Survey Status tab.",
        )
        st.markdown("<hr style='margin:.4rem 0 .6rem;border-color:#f0f2f5'>", unsafe_allow_html=True)
        st.markdown('<div class="thr-title">Indicators to run</div>', unsafe_allow_html=True)
        enabled = []
        left, right = st.columns(2, gap="small")
        for i, name in enumerate(ALL_INDICATORS):
            col = left if i % 2 == 0 else right
            with col:
                if st.checkbox(name, value=True, help=INDICATOR_DESC[name], key=f"ind_{name}"):
                    enabled.append(name)

    # ── Right: Thresholds ─────────────────────────────────────────────────────
    with col_thr:
        st.markdown('<div class="thr-title">Thresholds</div>', unsafe_allow_html=True)
        overrides: dict[str, dict] = {}

        # FCS
        with st.expander("🌾  FCS — Food Consumption Score", expanded=False):
            st.caption(
                "Weighted sum of 8 food group frequencies over a 7-day recall. "
                "Formula: (Stap×2)+(Pulse×3)+(Dairy×4)+(Protein×4)+(Veg×1)+(Fruit×1)+(Fat×0.5)+(Sugar×0.5). "
                "Max = 112. WFP standard thresholds: **Poor ≤21 | Borderline 21.5–35 | Acceptable >35** "
                "(use 28/42 cut-offs in high sugar-oil contexts)."
            )
            a, b, c = st.columns(3)
            overrides["FCS"] = {
                "low_fcs_threshold":    a.number_input("Low FCS flag (<)",         value=10,  min_value=0,  max_value=112, key="fcs_low",
                                                        help="Flag households with suspiciously low FCS. WFP flags FCS = 0 as implausible in non-famine contexts."),
                "high_fcs_threshold":   b.number_input("High FCS flag (>)",        value=100, min_value=0,  max_value=112, key="fcs_high",
                                                        help="Flag near-maximum scores (theoretical max is 112). Scores >100 require all groups consumed every day."),
                "low_staple_threshold": c.number_input("Low staple days (<)",      value=2,   min_value=0,  max_value=7,   key="fcs_staple",
                                                        help="Flag when FCSStap ≤ this value. Cereals/staples are consumed daily in most contexts; ≤1 day is highly suspicious."),
            }

        # rCSI
        with st.expander("🤲  rCSI — Coping Strategies Index", expanded=False):
            st.caption(
                "Sum of 5 weighted coping strategies over 7-day recall. "
                "Weights: LessQlty×1, Borrow×2, MealNb×1, MealSize×1, MealAdult×3. Max = 56. "
                "WFP thresholds: **Minimal 0–3 | Moderate 4–18 | Crisis ≥19 | Extreme ≥43**. "
                "In CARI, rCSI ≥4 elevates an Acceptable FCS household from food-secure to marginally food-secure."
            )
            a, _ = st.columns([1, 2])
            overrides["rCSI"] = {
                "high_rcsi_with_acceptable_fcg": a.number_input(
                    "High rCSI + Acceptable FCG (>)", value=18, min_value=0, max_value=56, key="rcsi_high",
                    help="Flag households with Acceptable FCS but rCSI above this threshold. Default 18 = top of the 'Moderate' band; ≥19 is crisis level per WFP/IPC alignment."),
            }

        # Timing
        with st.expander("⏱  Timing — Interview duration", expanded=False):
            st.caption(
                "Derived from ODK/SurveyCTO device timestamps. A complete WFP food security questionnaire "
                "typically takes **30–90 minutes**. Surveys under 20 minutes should be reviewed for question skipping. "
                "End-before-start errors indicate device clock problems."
            )
            a, b, c = st.columns(3)
            d, e, _ = st.columns(3)
            overrides["Timing"] = {
                "short_duration_min":         a.number_input("Short interview (<) min", value=20,  min_value=1,   max_value=60,  key="t_short",
                                                              help="Interviews shorter than this are flagged. A full FSNA questionnaire typically takes ≥30 min."),
                "long_duration_min":          b.number_input("Long interview (>) min",  value=120, min_value=30,  max_value=600, key="t_long",
                                                              help="Interviews longer than this are flagged. May indicate device left running or respondent unavailability."),
                "utc_offset_hours":           c.number_input("UTC offset (hours)",      value=0,   min_value=-12, max_value=14,  key="t_utc",
                                                              help="Local timezone offset from UTC. Used to convert timestamps to local time for start-hour checks."),
                "abnormal_early_morning_end": d.number_input("Flag before hour",        value=7,   min_value=0,   max_value=12,  key="t_early",
                                                              help="Flag interviews starting before this hour (24h). Interviews before 07:00 are unusual."),
                "abnormal_evening_start":     e.number_input("Flag after hour",         value=19,  min_value=12,  max_value=24,  key="t_late",
                                                              help="Flag interviews starting after this hour (24h). Interviews after 19:00 are unusual."),
            }

        # Demographics
        with st.expander("👥  Demographics — Household size", expanded=False):
            st.caption(
                "Checks household composition consistency: sum of age-sex sub-groups must match the reported total; "
                "at least one adult (18+) must be present; pregnant/lactating women (PLW) cannot exceed females aged 12–59. "
                "Large household sizes should be verified — extended family compounds can be legitimately large in some contexts."
            )
            a, _ = st.columns([1, 2])
            overrides["Demo"] = {
                "high_hhsize_threshold": a.number_input("Max household size", value=30, min_value=5, max_value=99, key="demo_hhsize",
                                                         help="Flag households exceeding this size. WFP surveys commonly flag >20; adjust for contexts with large extended family compounds."),
            }

        # Expenditure
        with st.expander("💰  Expenditure — Price plausibility", expanded=False):
            st.caption(
                "Applies to all expenditure modules (food 7-day, non-food 1-month, non-food 6-month). "
                "**Minimum meaningful price** is the smallest plausible non-zero spend in local currency — "
                "think of it as the price of a loaf of bread or a small market purchase. "
                "Any item recorded as non-zero but below this floor is flagged as a likely entry error (e.g. a respondent "
                "entered '5' when they meant '500'). Leave at 0 to disable."
            )
            a, b, c = st.columns(3)
            exp_overrides = {
                "min_item_price":           a.number_input(
                    "Min item price (local currency)", value=0, min_value=0, step=10, key="exp_min_price",
                    help="Flag any non-zero expenditure item below this value. Set to the price of the cheapest meaningful "
                         "local purchase (e.g. price of bread or a bus token). Leave 0 to disable."),
                "max_single_item_food_7d":   b.number_input(
                    "Max food item — 7-day (local currency)", value=1000000, min_value=0, step=10000, key="exp_max_food",
                    help="Flag any single food expenditure item above this value. Adjust for local price levels."),
                "max_single_item_nonfood_1m": c.number_input(
                    "Max non-food item — 1-month (local currency)", value=1000000, min_value=0, step=10000, key="exp_max_nf1m",
                    help="Flag any single short-term non-food expenditure item above this value."),
            }
            d, _, _ = st.columns(3)
            exp_overrides["max_single_item_nonfood_6m"] = d.number_input(
                "Max non-food item — 6-month (local currency)", value=5000000, min_value=0, step=10000, key="exp_max_nf6m",
                help="Flag any single long-term non-food expenditure item above this value (health, education, rent, etc.).",
            )
            # All three expenditure modules share the same configurable block
            for exp_name in ("HHExpF", "HHExpNF1M", "HHExpNF6M"):
                overrides[exp_name] = exp_overrides

    st.markdown('</div>', unsafe_allow_html=True)
    return enabled, overrides, sample_target


# ── Shared chart layout ───────────────────────────────────────────────────────

def _chart_layout(**kw) -> dict:
    base = dict(
        height=kw.pop("height", 270),
        margin=dict(l=8, r=36, t=8, b=28),
        plot_bgcolor="#fafafa", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Open Sans,-apple-system,sans-serif", size=11, color="#475569"),
        xaxis=dict(gridcolor="#f0f2f5", linecolor="#e2e8f0", tickfont_size=10),
        yaxis=dict(gridcolor="#f0f2f5", linecolor="#e2e8f0", tickfont_size=10),
        hoverlabel=dict(bgcolor="white", font_size=11, bordercolor="#e2e8f0"),
    )
    base.update(kw)
    return base


def _section(title):
    st.markdown(
        f'<div style="font-size:.69rem;font-weight:700;color:#64748b;text-transform:uppercase;'
        f'letter-spacing:.07em;margin:.9rem 0 .35rem">{title}</div>',
        unsafe_allow_html=True,
    )


# ── Tab 1: Survey Status ──────────────────────────────────────────────────────

def tab_survey_status(stats: dict, working_df: pd.DataFrame, sample_target: int):
    ctx = _ctx(working_df)
    n   = stats["n"]

    # ── Top KPIs ──────────────────────────────────────────────────────────────
    days_active = stats.get("days_active", 0) or 0
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Completed Surveys", f"{n:,}")
    if sample_target > 0:
        pct = round(n / sample_target * 100, 1)
        remaining = max(sample_target - n, 0)
        c2.metric("Sample Target", f"{sample_target:,}", delta=f"{pct:.0f}% done")
        c3.metric("Remaining", f"{remaining:,}")
    else:
        c2.metric("Survey Period", stats["date_range"])
        c3.metric("Days Active", str(days_active))
    c4.metric("Enumerators Active", str(stats["n_enumerators"]))
    c5.metric("Areas Covered",      str(stats["n_admin"]))

    # ── Pace projection ───────────────────────────────────────────────────────
    if sample_target > 0 and days_active > 0:
        avg_per_day = n / days_active
        remaining   = max(sample_target - n, 0)
        if avg_per_day > 0 and remaining > 0:
            days_to_finish = math.ceil(remaining / avg_per_day)
            finish_str = f"~{days_to_finish} days"
        elif remaining == 0:
            finish_str = "Complete ✓"
        else:
            finish_str = "—"
        p1, p2 = st.columns(2)
        p1.metric("Avg Surveys / Day",     f"{avg_per_day:.1f}")
        p2.metric("Est. Days to Complete", finish_str)

    # ── Sample completion progress bar (bar only — label already in KPI row) ──
    if sample_target > 0:
        pct_f = min(n / sample_target, 1.0)
        color = _C["ok_fg"] if pct_f >= 0.9 else (_C["med_fg"] if pct_f >= 0.5 else _C["crit_fg"])
        st.markdown(
            f'<div style="background:#f0f2f5;border-radius:6px;height:8px;overflow:hidden;margin:.4rem 0 .6rem">'
            f'<div style="background:{color};width:{pct_f*100:.1f}%;height:8px;border-radius:6px;'
            f'transition:width .4s"></div></div>',
            unsafe_allow_html=True,
        )

    # ── Priority Action Items panel ────────────────────────────────────────────
    with st.expander("🚨  Priority Action Items", expanded=True):
        issues = []
        total_flagged = stats.get("total_flagged", 0)
        overall_rate  = round(total_flagged / n * 100, 1) if n else 0
        n_dupes, _ = _duplicate_check(working_df, ctx)
        if n_dupes > 0:
            issues.append(("critical", f"{n_dupes} duplicate household ID(s) detected — must resolve before analysis"))
        if overall_rate > 20:
            issues.append(("critical", f"Overall flag rate is {overall_rate:.1f}% — exceeds 20% warning threshold"))
        for row in stats.get("enu_rows", []):
            if row["rate"] > 30:
                issues.append(("warning", f"Enumerator '{row['enumerator']}' has a {row['rate']:.1f}% flag rate"))
        for row in stats.get("admin_rows", []):
            if row["rate"] > 30:
                issues.append(("warning", f"Area '{row['area']}' has a {row['rate']:.1f}% flag rate"))
        # Straight-lining check (FCS food groups)
        fcs_cols_chk = [c for c in ["FCSStap","FCSPulse","FCSDairy","FCSPr","FCSVeg","FCSFruit","FCSFat","FCSSugar"]
                        if c in working_df.columns]
        if fcs_cols_chk:
            fcs_num_chk = working_df[fcs_cols_chk].apply(pd.to_numeric, errors="coerce")
            sl_total_chk = int((fcs_num_chk.std(axis=1) == 0).sum())
            if sl_total_chk > 0:
                issues.append(("warning", f"{sl_total_chk} straight-line FCS record(s) — all food groups identical"))
        if not issues:
            st.markdown('<div class="prio-ok">✅ No critical issues detected in this dataset</div>',
                        unsafe_allow_html=True)
        else:
            for level, msg in issues[:12]:
                css_cls = "prio-critical" if level == "critical" else "prio-warning"
                icon    = "🔴" if level == "critical" else "🟡"
                st.markdown(f'<div class="{css_cls}">{icon} {msg}</div>', unsafe_allow_html=True)

    st.divider()

    # ── Timeline + Area breakdown ─────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        _section("Daily & Cumulative Survey Collection")
        tl = stats.get("timeline", [])
        if tl:
            tdf = pd.DataFrame(tl)
            tdf["date"]       = pd.to_datetime(tdf["date"])
            tdf["cumulative"] = tdf["count"].cumsum()
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=tdf["date"], y=tdf["count"], name="Daily",
                marker_color=_C["primary"], opacity=0.75,
                hovertemplate="%{x|%b %d}: %{y} surveys<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=tdf["date"], y=tdf["cumulative"], name="Cumulative",
                yaxis="y2", mode="lines+markers",
                line=dict(color="#1e293b", width=2),
                marker=dict(size=4),
                hovertemplate="%{x|%b %d} cumulative: %{y}<extra></extra>",
            ))
            if sample_target > 0:
                # Expected-pace line on right (cumulative) axis only — no hline annotations
                n_days = max(len(tl), 1)
                fig.add_trace(go.Scatter(
                    x=tdf["date"],
                    y=[sample_target / n_days * (i + 1) for i in range(len(tdf))],
                    name="Expected pace", yaxis="y2", mode="lines",
                    line=dict(color=_C["med_fg"], dash="dot", width=1.5),
                    hovertemplate="Expected: %{y:.0f}<extra></extra>",
                ))
                # Single horizontal target line on right axis
                fig.add_hline(
                    y=sample_target, line_dash="dash", line_color=_C["ok_fg"],
                    annotation_text=f"Target ({sample_target:,})",
                    annotation_font_size=9, annotation_position="top right",
                    yref="y2",
                )
            layout = _chart_layout(xaxis_title=None, showlegend=True)
            layout.update({
                "yaxis2": dict(
                    overlaying="y", side="right", showgrid=False,
                    tickfont=dict(size=9), title="Cumulative",
                ),
                "legend": dict(orientation="h", yanchor="bottom", y=1.02,
                               xanchor="right", x=1, font=dict(size=9)),
            })
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        else:
            st.caption("No date column detected.")

    with col_b:
        _section("Surveys by Area")
        area_col = ctx["area"]
        if area_col:
            area_cnt = (working_df[area_col].value_counts()
                        .reset_index().rename(columns={"index": "area", area_col: "count"}))
            area_cnt.columns = ["area", "count"]
            area_cnt = area_cnt.sort_values("count")
            fig = go.Figure(go.Bar(
                x=area_cnt["count"], y=area_cnt["area"].astype(str), orientation="h",
                marker_color=_C["primary"],
                text=area_cnt["count"], textposition="outside", textfont_size=10,
                hovertemplate="%{y}: %{x} surveys<extra></extra>",
            ))
            fig.update_layout(**_chart_layout(
                height=max(240, len(area_cnt)*26+50),
                xaxis_title="Surveys", yaxis_title=None,
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        else:
            st.caption("No area/admin column detected.")

    # ── Enumerator completion table ───────────────────────────────────────────
    enu_col = ctx["enu"]
    if enu_col:
        _section("Enumerator Completion Status")
        enu_cnt = working_df[enu_col].value_counts().reset_index()
        enu_cnt.columns = ["Enumerator", "Completed"]
        if sample_target > 0 and stats["n_enumerators"] > 0:
            target_each = round(sample_target / stats["n_enumerators"])
            enu_cnt["Target"] = target_each
            enu_cnt["% Done"] = (enu_cnt["Completed"] / target_each * 100).round(1)
            enu_cnt["Remaining"] = (enu_cnt["Target"] - enu_cnt["Completed"]).clip(lower=0)
            enu_cnt["Status"] = enu_cnt["% Done"].apply(
                lambda p: "🟢 On track" if p >= 80 else ("🟡 Behind" if p >= 50 else "🔴 Critical"))
        enu_cnt = enu_cnt.sort_values("Completed", ascending=False).reset_index(drop=True)
        _show_table(enu_cnt)
    else:
        st.caption("No enumerator column detected.")

    # ── Area completion table ─────────────────────────────────────────────────
    area_col_s = ctx["area"]
    if area_col_s and sample_target > 0:
        _section("Area Completion Status")
        area_cnt = working_df[area_col_s].value_counts().reset_index()
        area_cnt.columns = ["Area", "Completed"]
        n_areas = max(len(area_cnt), 1)
        area_target = round(sample_target / n_areas)
        area_cnt["Target"]    = area_target
        area_cnt["% Done"]    = (area_cnt["Completed"] / area_target * 100).round(1)
        area_cnt["Remaining"] = (area_cnt["Target"] - area_cnt["Completed"]).clip(lower=0)
        area_cnt["Status"]    = area_cnt["% Done"].apply(
            lambda p: "🟢 On track" if p >= 80 else ("🟡 Behind" if p >= 50 else "🔴 Critical"))
        area_cnt = area_cnt.sort_values("% Done").reset_index(drop=True)
        _show_table(area_cnt)


# ── Tab 2: Enumerator Behavior ────────────────────────────────────────────────

def tab_enumerator_behavior(stats: dict, working_df: pd.DataFrame, results: dict):
    ctx     = _ctx(working_df)
    enu_col = ctx["enu"]
    sup_col = ctx["sup"]
    n       = stats["n"]

    if not enu_col:
        st.info("No enumerator column detected in the dataset. Common column names: EnuName, enumerator_name, EnuID.")
        return

    # ── Build per-enumerator summary ──────────────────────────────────────────
    enu_rows = stats.get("enu_rows", [])
    enu_base = pd.DataFrame(enu_rows) if enu_rows else pd.DataFrame()

    # Straight-lining: all FCS food group values identical within a record
    fcs_cols = [c for c in ["FCSStap","FCSPulse","FCSDairy","FCSPr","FCSVeg","FCSFruit","FCSFat","FCSSugar"]
                if c in working_df.columns]
    if fcs_cols:
        fcs_num = working_df[fcs_cols].apply(pd.to_numeric, errors="coerce")
        sl_mask = fcs_num.std(axis=1) == 0
        sl_df   = working_df.loc[sl_mask, [enu_col]].copy()
        sl_cnt  = sl_df[enu_col].value_counts().rename("straight_line_count")
    else:
        sl_cnt = pd.Series(dtype=int, name="straight_line_count")

    # Missing rate: % of key indicator columns missing per enumerator
    key_cols = [c for c in ["FCSStap","rCSILessQlty","HHSize"] if c in working_df.columns]
    if key_cols:
        miss_rate = (working_df.groupby(enu_col)[key_cols]
                     .apply(lambda g: g.isnull().mean().mean() * 100)
                     .round(1).rename("missing_pct"))
    else:
        miss_rate = pd.Series(dtype=float, name="missing_pct")

    # Duration by enumerator
    dur_by_enu = pd.DataFrame()
    if "Timing_Duration_Min" in working_df.columns:
        dur_by_enu = (working_df[[enu_col, "Timing_Duration_Min"]]
                      .assign(dur=lambda d: pd.to_numeric(d["Timing_Duration_Min"], errors="coerce"))
                      .dropna(subset=["dur"])
                      .query("dur > 0 and dur < 300"))

    # ── KPI row ───────────────────────────────────────────────────────────────
    sl_total = int(sl_mask.sum()) if fcs_cols else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Enumerators",          str(stats["n_enumerators"]))
    c2.metric("Surveys per Enumerator", f"{n/max(stats['n_enumerators'],1):.1f} avg")
    c3.metric("Straight-line Surveys", str(sl_total),
              help="Records where all FCS food groups have identical values — possible fabrication or rushing")
    avg_dur = stats.get("dur_mean")
    c4.metric("Avg Interview Duration", f"{avg_dur} min" if avg_dur else "—")

    st.divider()

    # ── Charts row 1: Flag rate + Duration box plot ───────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        _section("Flag Rate by Enumerator (top 20)")
        if enu_rows:
            edf = pd.DataFrame(enu_rows).sort_values("rate", ascending=True).tail(20)
            colors = [_flag_style(r)[0] for r in edf["rate"]]
            fig = go.Figure(go.Bar(
                x=edf["rate"], y=edf["enumerator"].astype(str), orientation="h",
                marker_color=colors,
                text=edf["rate"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside", textfont_size=10,
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            ))
            fig.update_layout(**_chart_layout(
                height=max(240, len(edf)*28+50),
                xaxis_range=[0, max(edf["rate"].max()*1.3, 6)],
                xaxis_title=None, yaxis_title=None, xaxis_ticksuffix="%",
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)

    with col_b:
        _section("Interview Duration by Enumerator")
        if not dur_by_enu.empty:
            fig = px.box(dur_by_enu, x=enu_col, y="dur",
                         color=enu_col,
                         points="outliers",
                         labels={enu_col: "Enumerator", "dur": "Duration (min)"},
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_traces(marker_size=5)
            fig.update_layout(**_chart_layout(
                height=320, showlegend=False,
                xaxis_title=None, xaxis_tickangle=-30,
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        else:
            st.caption("Timing not run.")

    # ── Charts row 2: Straight-lining + Survey start hour ────────────────────
    col_c, col_d = st.columns(2)
    with col_c:
        _section("Straight-lining Detected (identical FCS responses)")
        if fcs_cols and not sl_cnt.empty:
            sl_plot = sl_cnt.reset_index()
            sl_plot.columns = ["Enumerator", "Count"]
            sl_plot = sl_plot.sort_values("Count", ascending=True)
            fig = go.Figure(go.Bar(
                x=sl_plot["Count"], y=sl_plot["Enumerator"].astype(str), orientation="h",
                marker_color=_C["crit_fg"],
                text=sl_plot["Count"], textposition="outside", textfont_size=10,
                hovertemplate="%{y}: %{x} straight-line records<extra></extra>",
            ))
            fig.update_layout(**_chart_layout(
                height=max(200, len(sl_plot)*26+50),
                xaxis_title="# of records", yaxis_title=None,
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        elif not fcs_cols:
            st.caption("FCS module not run — straight-lining check not available.")
        else:
            st.success("✅ No straight-lining detected across FCS responses.")

    with col_d:
        _section("Survey Start Hour Distribution")
        if "Timing_StartHour" in working_df.columns and enu_col:
            sh = working_df[[enu_col, "Timing_StartHour"]].copy()
            sh["Hour"] = pd.to_numeric(sh["Timing_StartHour"], errors="coerce")
            sh = sh.dropna(subset=["Hour"])
            if not sh.empty:
                fig = px.histogram(sh, x="Hour", color=enu_col, nbins=24,
                                   labels={"Hour": "Start hour (local)", "count": "Surveys"},
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.add_vrect(x0=0, x1=7,  fillcolor=_C["crit_bg"], opacity=0.3, line_width=0,
                              annotation_text="Before 07:00", annotation_font_size=9)
                fig.add_vrect(x0=19, x1=24, fillcolor=_C["crit_bg"], opacity=0.3, line_width=0,
                              annotation_text="After 19:00", annotation_font_size=9)
                fig.update_layout(**_chart_layout(showlegend=False, xaxis_title="Hour", xaxis_dtick=2))
                st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
            else:
                st.caption("No valid start hour data.")
        else:
            st.caption("Timing not run or start hour not computed.")

    # ── Enumerator summary table ──────────────────────────────────────────────
    _section("Per-Enumerator Summary Table")
    if enu_rows:
        tbl = pd.DataFrame(enu_rows)[["enumerator","surveys","flagged","rate"]].copy()
        tbl.columns = ["Enumerator","Surveys","Flagged","Flag Rate %"]
        tbl["Enumerator"] = tbl["Enumerator"].astype(str)

        def _merge_str(left, right_series, col_name):
            """Merge right_series (indexed by enu_col) into left on 'Enumerator', casting to str."""
            r = right_series.reset_index()
            r.columns = ["Enumerator", col_name]
            r["Enumerator"] = r["Enumerator"].astype(str)
            return left.merge(r, on="Enumerator", how="left")

        if sup_col:
            sup_map = working_df.groupby(enu_col)[sup_col].first()
            tbl = _merge_str(tbl, sup_map.rename("Supervisor"), "Supervisor")
        if not sl_cnt.empty:
            tbl = _merge_str(tbl, sl_cnt.rename("Straight-line"), "Straight-line")
        if not miss_rate.empty:
            tbl = _merge_str(tbl, miss_rate.rename("Missing %"), "Missing %")
        if not dur_by_enu.empty:
            dur_avg = dur_by_enu.groupby(enu_col)["dur"].mean().round(1)
            tbl = _merge_str(tbl, dur_avg.rename("Avg Duration (min)"), "Avg Duration (min)")

        tbl = tbl.sort_values("Flag Rate %", ascending=False).reset_index(drop=True)
        _show_table(tbl)

    st.divider()

    # ── Enumerator Key Indicator Means (vs. overall) ──────────────────────────
    _section("Enumerator Indicator Averages vs. Overall Mean")
    st.caption(
        "Cells highlighted red deviate >1.5 SD from the overall mean — "
        "possible anchoring, interview coaching, or data fabrication."
    )
    numeric_map = {
        "FCS":           "FCS",
        "rCSI":          "rCSI",
        "HDDS":          "HDDS",
        "HH Size":       "HHSize",
        "Duration (min)":"Timing_Duration_Min",
    }
    avail = {lbl: col for lbl, col in numeric_map.items() if col in working_df.columns}
    if avail and enu_col:
        overall_means = {}
        overall_stds  = {}
        for lbl, col in avail.items():
            s = pd.to_numeric(working_df[col], errors="coerce")
            overall_means[lbl] = s.mean()
            overall_stds[lbl]  = s.std()

        means_df = (
            working_df.groupby(enu_col)
            .apply(lambda g: pd.Series({
                lbl: round(pd.to_numeric(g[col], errors="coerce").mean(), 2)
                for lbl, col in avail.items()
            }))
            .reset_index()
            .rename(columns={enu_col: "Enumerator"})
        )

        def _highlight_deviation(col_series):
            lbl = col_series.name
            if lbl not in overall_means or overall_stds.get(lbl, 0) == 0:
                return [""] * len(col_series)
            return [
                "background-color:#fee2e2;color:#dc2626"
                if (not pd.isna(v) and abs(v - overall_means[lbl]) > 1.5 * overall_stds[lbl])
                else ""
                for v in col_series
            ]

        numeric_cols_only = [c for c in means_df.columns if c != "Enumerator"]
        styled = (means_df.style
                  .apply(_highlight_deviation, axis=0, subset=numeric_cols_only)
                  .set_properties(**{"text-align": "center"})
                  .set_properties(subset=["Enumerator"], **{"text-align": "left"}))
        _show_table(means_df, styler=styled)
        overall_str = "  |  ".join(
            f"{lbl}: {overall_means[lbl]:.1f}" for lbl in avail
            if not pd.isna(overall_means[lbl])
        )
        st.caption(f"Dataset overall means — {overall_str}")
    else:
        st.caption("No numeric indicator columns detected for comparison.")

    st.divider()

    # ── Daily Submission Heatmap by Enumerator ────────────────────────────────
    _section("Daily Submissions by Enumerator")
    st.caption("Shows which enumerators collected data on which days — gaps indicate missed collection days.")
    date_col_e = ctx["date"]
    if date_col_e and date_col_e in working_df.columns and enu_col:
        hm_df = working_df[[enu_col, date_col_e]].copy()
        hm_df["_date"] = pd.to_datetime(hm_df[date_col_e], errors="coerce").dt.date
        hm_df = hm_df.dropna(subset=["_date"])
        if not hm_df.empty:
            pivot = pd.crosstab(hm_df[enu_col].astype(str), hm_df["_date"])
            pivot.columns = [str(c) for c in pivot.columns]
            fig = px.imshow(
                pivot, color_continuous_scale="Blues", aspect="auto",
                labels={"x": "Date", "y": "Enumerator", "color": "Surveys"},
                text_auto=True,
            )
            fig.update_traces(textfont_size=9)
            fig.update_layout(**_chart_layout(
                height=max(220, len(pivot) * 26 + 70),
                xaxis_title=None, yaxis_title=None,
                xaxis_tickangle=-40,
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        else:
            st.caption("No valid date data found.")
    else:
        st.caption("Enumerator or date column not detected.")


# ── Tab 3: Indicator Breakdown ────────────────────────────────────────────────

def tab_indicator_breakdown(working_df: pd.DataFrame):
    ctx      = _ctx(working_df)
    area_col = ctx["area"]
    enu_col  = ctx["enu"]
    date_col = ctx["date"]

    # ── Helper: stacked % bar ─────────────────────────────────────────────────
    def _stacked_pct_bar(df, group_col, value_col, cats, colors, height=280, top_n=None):
        """Return a stacked-100% go.Figure grouped by group_col."""
        grp = (df[[group_col, value_col]].dropna()
               .groupby(group_col)[value_col]
               .value_counts(normalize=True).mul(100).round(1)
               .reset_index(name="pct"))
        pivot = (grp.pivot(index=group_col, columns=value_col, values="pct")
                 .fillna(0).reset_index())
        if top_n:
            counts = df[group_col].value_counts().head(top_n).index
            pivot  = pivot[pivot[group_col].isin(counts)]
        fig = go.Figure()
        for cat, color in zip(cats, colors):
            if cat not in pivot.columns:
                pivot[cat] = 0.0
            fig.add_trace(go.Bar(
                name=cat,
                x=pivot[group_col],
                y=pivot[cat],
                marker_color=color,
                text=pivot[cat].map(lambda v: f"{v:.0f}%" if v >= 5 else ""),
                textposition="inside",
                hovertemplate=f"<b>%{{x}}</b><br>{cat}: %{{y:.1f}}%<extra></extra>",
            ))
        layout = _chart_layout(height=height, barmode="stack",
                               bargap=0.45,          # narrower bars
                               margin=dict(l=8, r=8, t=8, b=52))
        layout["yaxis"].update(range=[0, 100], ticksuffix="%")
        # Legend below the chart — avoids overlap with bars
        layout["legend"] = dict(
            orientation="h", x=0.5, y=-0.18,
            xanchor="center", yanchor="top",
            font=dict(size=10),
        )
        fig.update_layout(**layout)
        return fig

    # ── Helper: mean score trend line ────────────────────────────────────────
    def _trend_line(df, date_col, score_col, color, label):
        tmp = df[[date_col, score_col]].copy()
        tmp["_d"] = pd.to_datetime(tmp[date_col], errors="coerce").dt.date
        daily = tmp.groupby("_d")[score_col].mean().round(2).reset_index()
        daily.columns = ["date", "mean"]
        fig = go.Figure(go.Scatter(
            x=daily["date"], y=daily["mean"],
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5),
            name=label,
            hovertemplate="<b>%{x}</b><br>Mean: %{y:.1f}<extra></extra>",
        ))
        fig.update_layout(**_chart_layout(height=220))
        return fig

    # ── Helper: mean score horizontal bar ────────────────────────────────────
    def _mean_hbar(df, group_col, score_col, color, top_n=25):
        tmp = (df[[group_col, score_col]].dropna()
               .groupby(group_col)[score_col].mean().round(2)
               .sort_values(ascending=True).tail(top_n).reset_index())
        tmp.columns = ["group", "mean"]
        fig = go.Figure(go.Bar(
            x=tmp["mean"], y=tmp["group"],
            orientation="h",
            marker_color=color,
            hovertemplate="<b>%{y}</b><br>Mean: %{x:.1f}<extra></extra>",
        ))
        fig.update_layout(**_chart_layout(
            height=max(200, len(tmp) * 26 + 60),
            xaxis_title="Mean score", yaxis_title=None,
        ))
        return fig

    # ══════════════════════════════════════════════════════════════════════════
    # A — FOOD CONSUMPTION SCORE
    # ══════════════════════════════════════════════════════════════════════════
    fcs_ok = "FCG" in working_df.columns and "FCS" in working_df.columns

    with st.expander("🍽️  Food Consumption Score (FCS)", expanded=True):
        if not fcs_ok:
            st.caption("No data — FCS columns not detected in this dataset.")
        else:
            # WFP standard FCS colors
            fcs_cats   = ["Poor", "Borderline", "Acceptable"]
            fcs_colors = ["#D70000", "#E67536", "#ECE1B1"]

            ca, cb = st.columns(2)
            with ca:
                if area_col and area_col in working_df.columns:
                    _section("By Area")
                    st.plotly_chart(
                        _stacked_pct_bar(working_df, area_col, "FCG", fcs_cats, fcs_colors),
                        use_container_width=True, config=_PLOTLY_CFG,
                    )
                else:
                    _section("By Area")
                    st.caption("No area column detected.")

            with cb:
                if enu_col and enu_col in working_df.columns:
                    _section("By Enumerator  (top 20)")
                    st.plotly_chart(
                        _stacked_pct_bar(working_df, enu_col, "FCG", fcs_cats, fcs_colors, top_n=20),
                        use_container_width=True, config=_PLOTLY_CFG,
                    )
                else:
                    _section("By Enumerator")
                    st.caption("No enumerator column detected.")

            # -- Trend over time --
            if date_col and date_col in working_df.columns:
                st.divider()
                _section("Mean FCS Over Time")
                st.plotly_chart(
                    _trend_line(working_df, date_col, "FCS", _C["primary"], "Mean FCS"),
                    use_container_width=True, config=_PLOTLY_CFG,
                )
            else:
                st.caption("No date column detected — skipping time trend.")

    # ══════════════════════════════════════════════════════════════════════════
    # B — rCSI
    # ══════════════════════════════════════════════════════════════════════════
    rcsi_ok = "rCSI" in working_df.columns

    with st.expander("🔄  Reduced Coping Strategies Index (rCSI)", expanded=True):
        if not rcsi_ok:
            st.caption("No data — rCSI columns not detected in this dataset.")
        else:
            # Compute severity category on the fly
            df_r = working_df.copy()
            df_r["rCSI_Cat"] = pd.cut(
                pd.to_numeric(df_r["rCSI"], errors="coerce"),
                bins=[-1, 3, 18, 9999],
                labels=["Low  (≤ 3)", "Medium  (4–18)", "High  (≥ 19)"],
            ).astype(str).replace("nan", pd.NA)

            # Mirror WFP FCS palette: low=acceptable cream, medium=borderline orange, high=poor red
            rcsi_cats   = ["Low  (≤ 3)", "Medium  (4–18)", "High  (≥ 19)"]
            rcsi_colors = ["#ECE1B1", "#E67536", "#D70000"]

            ca, cb = st.columns(2)
            with ca:
                if area_col and area_col in working_df.columns:
                    _section("By Area")
                    st.plotly_chart(
                        _stacked_pct_bar(df_r, area_col, "rCSI_Cat", rcsi_cats, rcsi_colors),
                        use_container_width=True, config=_PLOTLY_CFG,
                    )
                else:
                    _section("By Area")
                    st.caption("No area column detected.")

            with cb:
                if enu_col and enu_col in working_df.columns:
                    _section("By Enumerator  (top 20)")
                    st.plotly_chart(
                        _stacked_pct_bar(df_r, enu_col, "rCSI_Cat", rcsi_cats, rcsi_colors, top_n=20),
                        use_container_width=True, config=_PLOTLY_CFG,
                    )
                else:
                    _section("By Enumerator")
                    st.caption("No enumerator column detected.")

            # -- Trend over time --
            if date_col and date_col in working_df.columns:
                st.divider()
                _section("Mean rCSI Over Time")
                st.plotly_chart(
                    _trend_line(working_df, date_col, "rCSI", _C["teal"], "Mean rCSI"),
                    use_container_width=True, config=_PLOTLY_CFG,
                )
            else:
                st.caption("No date column detected — skipping time trend.")

    # ══════════════════════════════════════════════════════════════════════════
    # C — HDDS
    # ══════════════════════════════════════════════════════════════════════════
    hdds_ok = "HDDS" in working_df.columns

    with st.expander("🥗  Household Dietary Diversity Score (HDDS)", expanded=True):
        if not hdds_ok:
            st.caption("No data — HDDS columns not detected in this dataset.")
        else:
            ca, cb = st.columns(2)

            # -- By area --
            with ca:
                if area_col and area_col in working_df.columns:
                    _section("Mean HDDS by Area")
                    st.plotly_chart(
                        _mean_hbar(working_df, area_col, "HDDS", _C["primary"]),
                        use_container_width=True, config=_PLOTLY_CFG,
                    )
                else:
                    _section("Mean HDDS by Area")
                    st.caption("No area column detected.")

            # -- By enumerator --
            with cb:
                if enu_col and enu_col in working_df.columns:
                    _section("Mean HDDS by Enumerator  (top 25)")
                    st.plotly_chart(
                        _mean_hbar(working_df, enu_col, "HDDS", _C["teal"]),
                        use_container_width=True, config=_PLOTLY_CFG,
                    )
                else:
                    _section("Mean HDDS by Enumerator")
                    st.caption("No enumerator column detected.")

            # -- Trend over time --
            if date_col and date_col in working_df.columns:
                st.divider()
                _section("Mean HDDS Over Time")
                st.plotly_chart(
                    _trend_line(working_df, date_col, "HDDS", _C["purple"], "Mean HDDS"),
                    use_container_width=True, config=_PLOTLY_CFG,
                )

    # ══════════════════════════════════════════════════════════════════════════
    # D — LCS
    # ══════════════════════════════════════════════════════════════════════════

    # Standard WFP LCS columns → human-readable label (VAM codebook / HFC guidance)
    # Ordered Stress → Crisis → Emergency (increasing severity)
    _LCS_LABELS = {
        # Stress — asset-light, reversible
        "LcsStressMore":      "Sold more animals / crops than usual",
        "LcsStressLessExp":   "Reduced non-food expenditure",
        "LcsStressBorrow":    "Borrowed money, food, or relied on help",
        "LcsStressSavings":   "Spent savings",
        # Crisis — asset-depleting, harder to reverse
        "LcsCrisisLiquid":    "Sold household assets (radio, bicycle…)",
        "LcsCrisisProd":      "Sold productive assets or transport",
        "LcsCrisisHealth":    "Reduced health / education spending",
        # Emergency — irreversible, last resort
        "LcsEmergBegged":     "Begged for food or money",
        "LcsEmergMigrate":    "Migrated or relocated",
        "LcsEmergChildMarry": "Child marriage (early marriage)",
        "LcsEmergChildWork":  "Child labour / school dropout",
    }
    # Tier assignment per column
    _LCS_TIER = {}
    for _c in ["LcsStressMore", "LcsStressLessExp", "LcsStressBorrow", "LcsStressSavings"]:
        _LCS_TIER[_c] = "Stress"
    for _c in ["LcsCrisisLiquid", "LcsCrisisProd", "LcsCrisisHealth"]:
        _LCS_TIER[_c] = "Crisis"
    for _c in ["LcsEmergBegged", "LcsEmergMigrate", "LcsEmergChildMarry", "LcsEmergChildWork"]:
        _LCS_TIER[_c] = "Emergency"

    # Response-code → display label (N/A first, then least → most serious)
    _LCS_CODES = [
        (9999, "Not applicable (N/A)"),
        (20,   "Not needed"),
        (10,   "Applied"),
        (30,   "Exhausted / no longer an option"),
    ]
    # PPT-matched response colors
    _LCS_COLORS = {
        9999: "#BFBFBF",   # N/A        — neutral gray
        20:   "#ECE1B1",   # Not needed — WFP cream
        10:   "#E67536",   # Applied    — WFP orange
        30:   "#D70000",   # Exhausted  — WFP red
    }
    # Tier visual styling
    _TIER_COLOR = {"Stress": "#0070BA", "Crisis": "#E67536", "Emergency": "#D70000"}
    _TIER_BG    = {
        "Stress":    "rgba(0,112,186,0.07)",
        "Crisis":    "rgba(230,117,54,0.07)",
        "Emergency": "rgba(215,0,0,0.07)",
    }

    lcs_cols_present = [c for c in _LCS_LABELS if c in working_df.columns]

    with st.expander("🏠  Livelihood Coping Strategies (LCS)", expanded=True):
        if not lcs_cols_present:
            st.caption("No data — LCS columns not detected in this dataset.")
        else:
            n_rows = len(working_df)

            # ── Build long-format percentage table ────────────────────────────
            records = []
            for col in lcs_cols_present:
                series = pd.to_numeric(working_df[col], errors="coerce")
                for code, resp_label in _LCS_CODES:
                    cnt = int((series == code).sum())
                    records.append({
                        "col":      col,
                        "label":    _LCS_LABELS[col],
                        "tier":     _LCS_TIER.get(col, ""),
                        "code":     code,
                        "response": resp_label,
                        "count":    cnt,
                        "pct":      round(cnt / n_rows * 100, 1) if n_rows else 0,
                    })
            lcs_long = pd.DataFrame(records)

            # ── Chart A: 100% stacked bar — response share per strategy ───────
            _section("Response Distribution per Strategy")
            st.caption(
                "% of households per response option. Strategies are grouped by severity tier "
                "(Stress → Crisis → Emergency). "
                "Gray (N/A) — high rates may indicate interviewer skipping."
            )

            bar_height = max(340, len(lcs_cols_present) * 44 + 120)
            fig = go.Figure()
            for code, resp_label in _LCS_CODES:
                sub = lcs_long[lcs_long["code"] == code].copy()
                sub["_order"] = sub["col"].map({c: i for i, c in enumerate(lcs_cols_present)})
                sub = sub.sort_values("_order")
                fig.add_trace(go.Bar(
                    name=resp_label,
                    y=sub["label"],
                    x=sub["pct"],
                    orientation="h",
                    marker_color=_LCS_COLORS[code],
                    text=sub["pct"].map(lambda v: f"{v:.0f}%" if v >= 5 else ""),
                    textposition="inside",
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        + resp_label
                        + ": %{x:.1f}% (%{customdata:,} hh)<extra></extra>"
                    ),
                    customdata=sub["count"],
                ))

            # Tier grouping: colored background bands + left-margin labels
            # Background bands use yref="y" with category-name strings
            tier_shapes      = []
            tier_annotations = []
            for tier in ["Stress", "Crisis", "Emergency"]:
                tier_cols_here = [c for c in lcs_cols_present if _LCS_TIER.get(c) == tier]
                if not tier_cols_here:
                    continue
                t_labels = [_LCS_LABELS[c] for c in tier_cols_here]

                # Shaded band spanning the tier's categories
                tier_shapes.append(dict(
                    type="rect", xref="paper", yref="y",
                    x0=0, x1=1,
                    y0=t_labels[0], y1=t_labels[-1],
                    fillcolor=_TIER_BG[tier],
                    line=dict(color=_TIER_COLOR[tier], width=0.6),
                    layer="below",
                ))
                # Tier label: placed right of the 100% bar using data coords
                mid_lbl = t_labels[len(t_labels) // 2]
                tier_annotations.append(dict(
                    xref="x", yref="y",
                    x=101, y=mid_lbl,
                    text=f"<b>{tier}</b>",
                    showarrow=False,
                    xanchor="left", yanchor="middle",
                    font=dict(size=10, color=_TIER_COLOR[tier]),
                ))

            layout = _chart_layout(height=bar_height, barmode="stack",
                                   margin=dict(l=248, r=70, t=8, b=72))
            layout["xaxis"].update(
                ticksuffix="%", range=[0, 114],
                title=dict(text="% of households", standoff=36),
            )
            layout["yaxis"].update(autorange="reversed")
            layout["legend"] = dict(
                orientation="h", x=0.5, y=-0.09,
                xanchor="center", yanchor="top", font=dict(size=10),
                tracegroupgap=0,
            )
            layout["shapes"]      = tier_shapes
            layout["annotations"] = tier_annotations
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)

            # ── Chart B+C: N/A rate by area and enumerator (side by side) ─────
            st.divider()
            _section("N/A Rate by Area and Enumerator")
            st.caption(
                "Average % of N/A responses across all LCS strategies per group. "
                "High rates suggest systematic skipping — flag for supervisor follow-up."
            )

            # Compute per-row % N/A across all present LCS columns
            lcs_numeric = working_df[lcs_cols_present].apply(pd.to_numeric, errors="coerce")
            working_df2 = working_df.copy()
            working_df2["_lcs_na_pct"] = (lcs_numeric == 9999).mean(axis=1) * 100

            col_na_area, col_na_enu = st.columns(2)

            with col_na_area:
                _section("By Area")
                if area_col and area_col in working_df2.columns:
                    na_area = (working_df2.groupby(area_col)["_lcs_na_pct"]
                               .mean().round(1).sort_values(ascending=True)
                               .reset_index())
                    na_area.columns = ["area", "na_pct"]
                    fig_a = go.Figure(go.Bar(
                        y=na_area["area"], x=na_area["na_pct"],
                        orientation="h",
                        marker_color="#BFBFBF",
                        marker_line=dict(color="#888", width=0.5),
                        text=na_area["na_pct"].map(lambda v: f"{v:.1f}%"),
                        textposition="outside",
                        hovertemplate="<b>%{y}</b><br>Avg N/A: %{x:.1f}%<extra></extra>",
                    ))
                    la = _chart_layout(height=max(220, len(na_area) * 28 + 60),
                                       margin=dict(l=8, r=50, t=8, b=28))
                    la["xaxis"].update(ticksuffix="%", range=[0, 105])
                    fig_a.update_layout(**la)
                    st.plotly_chart(fig_a, use_container_width=True, config=_PLOTLY_CFG)
                else:
                    st.caption("No area column detected.")

            with col_na_enu:
                _section("By Enumerator  (top 20)")
                if enu_col and enu_col in working_df2.columns:
                    top_enus = (working_df2[enu_col].value_counts().head(20).index)
                    na_enu = (working_df2[working_df2[enu_col].isin(top_enus)]
                              .groupby(enu_col)["_lcs_na_pct"]
                              .mean().round(1).sort_values(ascending=True)
                              .reset_index())
                    na_enu.columns = ["enu", "na_pct"]
                    fig_e = go.Figure(go.Bar(
                        y=na_enu["enu"], x=na_enu["na_pct"],
                        orientation="h",
                        marker_color="#BFBFBF",
                        marker_line=dict(color="#888", width=0.5),
                        text=na_enu["na_pct"].map(lambda v: f"{v:.1f}%"),
                        textposition="outside",
                        hovertemplate="<b>%{y}</b><br>Avg N/A: %{x:.1f}%<extra></extra>",
                    ))
                    le = _chart_layout(height=max(220, len(na_enu) * 28 + 60),
                                       margin=dict(l=8, r=50, t=8, b=28))
                    le["xaxis"].update(ticksuffix="%", range=[0, 105])
                    fig_e.update_layout(**le)
                    st.plotly_chart(fig_e, use_container_width=True, config=_PLOTLY_CFG)
                else:
                    st.caption("No enumerator column detected.")


# ── Tab 4: Data Quality ───────────────────────────────────────────────────────

def tab_data_quality(stats: dict, working_df: pd.DataFrame, results: dict):
    ctx      = _ctx(working_df)
    enu_col  = ctx["enu"]
    area_col = ctx["area"]
    hhid_col = ctx["hhid"]
    n        = stats["n"]

    # Common hover fields
    def _hover_cols():
        cols = {}
        if hhid_col:  cols[hhid_col]  = True
        if area_col:  cols[area_col]  = True
        if enu_col:   cols[enu_col]   = True
        return cols

    # ── Duplicate HHID check ──────────────────────────────────────────────────
    _section("Duplicate Household IDs")
    n_dupes, dupe_df = _duplicate_check(working_df, ctx)
    if n_dupes == 0:
        st.success("✅ No duplicate household IDs found — all records have unique IDs")
    else:
        st.error(f"⚠️ {n_dupes} duplicate household ID(s) found across {len(dupe_df)} records. "
                 f"Resolve before analysis — duplicates distort all flag rates and distributions.")
        st.caption("Common causes: form re-submission, data entry error, or deliberate fabrication. "
                   "Key demographics shown for side-by-side comparison.")
        _show_table(dupe_df)

    st.divider()

    # ── KPI row ───────────────────────────────────────────────────────────────
    total_flagged = stats["total_flagged"]
    overall_rate  = round(total_flagged / n * 100, 1) if n else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Flag Rate",  f"{overall_rate:.1f}%")
    c2.metric("Flagged Households", f"{total_flagged:,}")
    fcs_m = stats.get("fcs_mean"); c3.metric("Mean FCS",  str(fcs_m)  if fcs_m  else "—")
    rcs_m = stats.get("rcsi_mean"); c4.metric("Mean rCSI", str(rcs_m) if rcs_m else "—")

    st.divider()

    # ── Row 1: Flag rate by indicator + FCG distribution ─────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        _section("Flag Rate by Indicator")
        rows = stats["flag_rows"]
        if rows:
            idf = pd.DataFrame(rows)[["indicator","rate"]].sort_values("rate")
            fig = go.Figure(go.Bar(
                x=idf["rate"], y=idf["indicator"], orientation="h",
                marker_color=[_flag_style(r)[0] for r in idf["rate"]],
                text=idf["rate"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside", textfont_size=10,
            ))
            fig.update_layout(**_chart_layout(
                height=max(220, len(rows)*36+50),
                xaxis_title=None, yaxis_title=None,
                xaxis_range=[0, max(idf["rate"].max()*1.3, 6)],
                xaxis_ticksuffix="%",
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)

    with col_b:
        _section("Food Consumption Group Distribution")
        d = stats.get("fcs_dist", {})
        if d and n:
            fcg_map = {"Poor": _C["poor"], "Borderline": _C["border"], "Acceptable": _C["accept"]}
            fcg_df = pd.DataFrame([
                {"FCG": k, "Count": v, "Pct": round(v/n*100,1)}
                for k, v in d.items() if k in fcg_map
            ])
            fig = px.bar(fcg_df, x="FCG", y="Count",
                         text=fcg_df["Pct"].apply(lambda p: f"{p:.1f}%"),
                         color="FCG", color_discrete_map=fcg_map,
                         labels={"Count": "Households"},
                         category_orders={"FCG":["Poor","Borderline","Acceptable"]})
            fig.update_traces(textposition="outside", textfont_size=10)
            fig.update_layout(**_chart_layout(showlegend=False, xaxis_title=None))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        else:
            st.caption("FCS not run.")

    # ── Row 2: FCS box plot ───────────────────────────────────────────────────
    _section("FCS Distribution — Outliers by Area & Enumerator")
    if "FCS" in working_df.columns:
        bp_df = working_df.copy()
        bp_df["_FCS"] = pd.to_numeric(bp_df["FCS"], errors="coerce")
        group_col = area_col or enu_col
        if group_col:
            bp_df["_group"] = bp_df[group_col].astype(str)
            hover = {c: True for c in [hhid_col, enu_col, area_col] if c and c in bp_df.columns}
            fig = px.box(bp_df, x="_group", y="_FCS",
                         color="_group",
                         points="outliers",
                         color_discrete_sequence=px.colors.qualitative.Pastel,
                         hover_data=hover,
                         labels={"_group": area_col or enu_col, "_FCS": "FCS"})
            # WFP threshold lines
            fig.add_hline(y=21,  line_dash="dot", line_color=_C["poor"],
                          annotation_text="Poor threshold (21)", annotation_font_size=9,
                          annotation_font_color=_C["poor"])
            fig.add_hline(y=35,  line_dash="dot", line_color=_C["border"],
                          annotation_text="Borderline threshold (35)", annotation_font_size=9,
                          annotation_font_color=_C["border"])
            fig.update_traces(marker_size=6, marker_opacity=0.7)
            fig.update_layout(**_chart_layout(
                height=360, showlegend=False,
                xaxis_title=area_col or enu_col, yaxis_title="FCS Score",
                xaxis_tickangle=-30,
                yaxis_range=[-2, 115],
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        else:
            fcs_num = pd.to_numeric(working_df["FCS"], errors="coerce").dropna()
            fig = px.histogram(fcs_num, nbins=40, color_discrete_sequence=[_C["primary"]],
                               labels={"value": "FCS", "count": "Households"})
            fig.add_vline(x=21, line_dash="dot", line_color=_C["poor"])
            fig.add_vline(x=35, line_dash="dot", line_color=_C["border"])
            fig.update_layout(**_chart_layout(showlegend=False))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        fcs_s_iqr = pd.to_numeric(working_df["FCS"], errors="coerce").dropna()
        if len(fcs_s_iqr) >= 4:
            q1f, q3f = fcs_s_iqr.quantile(0.25), fcs_s_iqr.quantile(0.75)
            iqrf = q3f - q1f
            n_out_f = int(((fcs_s_iqr < q1f - 1.5 * iqrf) | (fcs_s_iqr > q3f + 1.5 * iqrf)).sum())
            st.caption(f"IQR: [{q1f:.1f}, {q3f:.1f}]  ·  Statistical outliers (±1.5×IQR): **{n_out_f}** records")
    else:
        st.caption("FCS not run.")

    # ── Row 3: rCSI box plot ──────────────────────────────────────────────────
    _section("rCSI Distribution — Outliers by Area & Enumerator")
    if "rCSI" in working_df.columns:
        bp_df = working_df.copy()
        bp_df["_rCSI"] = pd.to_numeric(bp_df["rCSI"], errors="coerce")
        group_col = area_col or enu_col
        if group_col:
            bp_df["_group"] = bp_df[group_col].astype(str)
            hover = {c: True for c in [hhid_col, enu_col, area_col] if c and c in bp_df.columns}
            fig = px.box(bp_df, x="_group", y="_rCSI",
                         color="_group",
                         points="outliers",
                         color_discrete_sequence=px.colors.qualitative.Pastel2,
                         hover_data=hover,
                         labels={"_group": area_col or enu_col, "_rCSI": "rCSI"})
            fig.add_hline(y=19, line_dash="dot", line_color=_C["high_fg"],
                          annotation_text="Crisis threshold (19)", annotation_font_size=9,
                          annotation_font_color=_C["high_fg"])
            fig.add_hline(y=42, line_dash="dot", line_color=_C["crit_fg"],
                          annotation_text="Extreme threshold (42)", annotation_font_size=9,
                          annotation_font_color=_C["crit_fg"])
            fig.update_traces(marker_size=6, marker_opacity=0.7)
            fig.update_layout(**_chart_layout(
                height=360, showlegend=False,
                xaxis_title=area_col or enu_col, yaxis_title="rCSI Score",
                xaxis_tickangle=-30,
                yaxis_range=[-1, 58],
            ))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        else:
            rcsi_num = pd.to_numeric(working_df["rCSI"], errors="coerce").dropna()
            fig = px.histogram(rcsi_num, nbins=30, color_discrete_sequence=[_C["purple"]],
                               labels={"value": "rCSI", "count": "Households"})
            fig.update_layout(**_chart_layout(showlegend=False))
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
        rcsi_s_iqr = pd.to_numeric(working_df["rCSI"], errors="coerce").dropna()
        if len(rcsi_s_iqr) >= 4:
            q1r, q3r = rcsi_s_iqr.quantile(0.25), rcsi_s_iqr.quantile(0.75)
            iqrr = q3r - q1r
            n_out_r = int(((rcsi_s_iqr < q1r - 1.5 * iqrr) | (rcsi_s_iqr > q3r + 1.5 * iqrr)).sum())
            st.caption(f"IQR: [{q1r:.1f}, {q3r:.1f}]  ·  Statistical outliers (±1.5×IQR): **{n_out_r}** records")
    else:
        st.caption("rCSI not run.")

    # ── Row 4: FEWS NET illogicality matrix ───────────────────────────────────
    _section("FEWS NET Cross-Indicator Consistency Matrix (HHS × FCG × rCSI)")
    hhs_cols = [c for c in ["HHBedHunger","HHNoFood","HHNotEat"] if c in working_df.columns]
    if hhs_cols and "FCG" in working_df.columns and "rCSI" in working_df.columns:
        mx = working_df.copy()
        for hc in hhs_cols:
            mx[hc] = pd.to_numeric(mx[hc], errors="coerce")
        mx["HHS"] = mx[hhs_cols].sum(axis=1)
        mx["HHS_cat"] = pd.cut(mx["HHS"], bins=[-1,0,1,3,4,6],
                                labels=["0","1","2–3","4","5–6"])
        mx["rCSI_num"] = pd.to_numeric(mx["rCSI"], errors="coerce")
        mx["rCSI_cat"] = pd.cut(mx["rCSI_num"], bins=[-1,3,18,56],
                                 labels=["<4 (Minimal)","4–18 (Moderate)",">18 (Crisis)"])
        mx["FCG"] = mx["FCG"].astype(str)

        pivot = (mx.groupby(["HHS_cat","rCSI_cat","FCG"], observed=True)
                   .size().reset_index(name="n"))
        total = len(mx.dropna(subset=["HHS_cat","rCSI_cat","FCG"]))

        # Build 5×9 matrix display
        hhs_order  = ["0","1","2–3","4","5–6"]
        rcsi_order = ["<4 (Minimal)","4–18 (Moderate)",">18 (Crisis)"]
        fcg_order  = ["Acceptable","Borderline","Poor"]

        rows_html = ""
        illogical_total = 0
        for hhs in hhs_order:
            row = f'<tr><td style="font-weight:700">{hhs}</td>'
            for rcsi in rcsi_order:
                for fcg in fcg_order:
                    match = pivot[(pivot["HHS_cat"]==hhs)&(pivot["rCSI_cat"]==rcsi)&(pivot["FCG"]==fcg)]
                    cnt = int(match["n"].sum()) if not match.empty else 0
                    pct = round(cnt/total*100,1) if total else 0
                    # Illogical: high HHS + good FCS + low coping
                    is_illogical = (hhs in ["2–3","4","5–6"] and
                                    fcg in ["Acceptable","Borderline"] and
                                    rcsi == "<4 (Minimal)")
                    if is_illogical and cnt > 0:
                        illogical_total += cnt
                    bg = (_C["crit_bg"] if is_illogical and cnt > 0
                          else "#f8fafc" if cnt == 0 else "white")
                    fw = "700" if cnt > 0 else "400"
                    color = (_C["crit_fg"] if is_illogical and cnt > 0
                             else "#94a3b8" if cnt == 0 else "#334155")
                    pct_span = (f'<br><span style="font-size:.65rem;font-weight:400;'
                                f'color:#94a3b8">{pct}%</span>') if cnt > 0 else ""
                    warn     = "⚠ " if is_illogical and cnt > 0 else ""
                    row += (f'<td style="text-align:center;background:{bg};color:{color};'
                            f'font-weight:{fw};font-size:.75rem">'
                            f'{warn}{cnt}{pct_span}</td>')
            row += "</tr>"
            rows_html += row

        illogical_pct = round(illogical_total / total * 100, 2) if total else 0
        header = ("".join(
            f'<th colspan="3" style="text-align:center;background:#f1f5f9;'
            f'border-bottom:2px solid #e2e8f0;padding:.4rem">{r}</th>'
            for r in rcsi_order))
        sub = "".join(
            f'<th style="background:#f8fafc;font-size:.65rem;text-align:center;'
            f'color:{_C["poor"] if f=="Poor" else _C["border"] if f=="Borderline" else _C["accept"]}'
            f'">{f}</th>'
            for _ in rcsi_order for f in fcg_order)

        st.markdown(
            f'<div style="font-size:.76rem;color:#475569;margin-bottom:.5rem">'
            f'Illogical combinations (high hunger + adequate diet + no coping): '
            f'<b style="color:{_C["crit_fg"]}">{illogical_total} households ({illogical_pct}%)</b> — '
            f'WFP target: &lt;0.5%. Shaded cells indicate logically inconsistent responses.</div>'
            f'<div style="overflow-x:auto"><table class="hfc-table" style="min-width:600px">'
            f'<thead><tr><th rowspan="2" style="background:#f1f5f9">HHS</th>{header}</tr>'
            f'<tr>{sub}</tr></thead><tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("FEWS NET matrix requires HHS columns (HHBedHunger, HHNoFood, HHNotEat), FCG, and rCSI.")

    # ── Row 5: Expenditure outliers (bottom 5 / top 5) ───────────────────────
    exp_cols = [c for c in working_df.columns
                if c.startswith("HHExpF") and c.endswith(("_7D","_1M","_6M","_MN_7D"))]
    if exp_cols:
        _section("Expenditure Outlier Review (Bottom 5 / Top 5 per Variable)")
        sel_cols = exp_cols[:8]  # limit to first 8 for readability
        exp_df   = working_df[sel_cols].apply(pd.to_numeric, errors="coerce")
        rows_html = ""
        for col in sel_cols:
            s = exp_df[col].dropna().sort_values()
            if s.empty: continue
            bot5 = " · ".join(f"{v:,.0f}" for v in s.head(5))
            top5 = " · ".join(f"{v:,.0f}" for v in s.tail(5))
            med  = f"{s.median():,.0f}"
            rows_html += (f'<tr><td><code style="font-size:.71rem;background:#f1f5f9;'
                          f'padding:.1rem .3rem;border-radius:3px">{col}</code></td>'
                          f'<td style="color:{_C["crit_fg"]};font-size:.75rem">{bot5}</td>'
                          f'<td style="color:#64748b;font-size:.75rem">{med}</td>'
                          f'<td style="color:{_C["high_fg"]};font-size:.75rem">{top5}</td></tr>')
        if rows_html:
            st.markdown(
                f'<table class="hfc-table" style="width:100%">'
                f'<thead><tr><th>Variable</th>'
                f'<th style="color:{_C["crit_fg"]}">Bottom 5 values</th>'
                f'<th>Median</th>'
                f'<th style="color:{_C["high_fg"]}">Top 5 values</th></tr></thead>'
                f'<tbody>{rows_html}</tbody></table>',
                unsafe_allow_html=True,
            )

    # ── Missing rate heatmap by Indicator × Enumerator ───────────────────────
    if enu_col:
        # Build merged results df with all Flag_*_Missing columns
        missing_frames = []
        for ind_name, res_df in results.items():
            miss_col = f"Flag_{ind_name}_Missing"
            if miss_col in res_df.columns and enu_col in res_df.columns:
                tmp = res_df[[enu_col, miss_col]].copy()
                tmp[miss_col] = pd.to_numeric(tmp[miss_col], errors="coerce")
                missing_frames.append(tmp.set_index(enu_col)[miss_col])

        if missing_frames:
            _section("Missing Data Rate by Indicator × Enumerator")
            st.caption("% of surveys per enumerator where each indicator's required fields were missing (0% = perfect, 100% = fully missing).")
            miss_wide = pd.concat(missing_frames, axis=1).fillna(0)
            miss_wide.columns = [c.replace("Flag_","").replace("_Missing","")
                                  for c in miss_wide.columns]
            miss_pct = (miss_wide.groupby(level=0).mean() * 100).round(1)
            if not miss_pct.empty and miss_pct.values.max() > 0:
                fig = px.imshow(
                    miss_pct,
                    color_continuous_scale="Reds",
                    aspect="auto",
                    zmin=0, zmax=100,
                    labels={"x": "Indicator", "y": "Enumerator", "color": "% Missing"},
                    text_auto=True,
                )
                fig.update_traces(textfont_size=9)
                fig.update_layout(**_chart_layout(
                    height=max(220, len(miss_pct) * 26 + 70),
                    xaxis_title=None, yaxis_title=None,
                ))
                st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)
            else:
                st.success("✅ No missing data detected across any indicator for any enumerator.")


# ── Tab 2: Details ────────────────────────────────────────────────────────────

def tab_details(results: dict):
    labels = [f"{n}  ({int((res[f'Flag_{n}_Overall']==1).sum()) if f'Flag_{n}_Overall' in res.columns else 0})"
              for n, res in results.items()]
    tabs = st.tabs(labels)
    for tab, (name, res) in zip(tabs, results.items()):
        with tab:
            overall = f"Flag_{name}_Overall"
            narr    = f"Flag_{name}_Narrative"
            meta    = INDICATOR_METHODOLOGY.get(name, {})

            # ── Indicator summary strip ───────────────────────────────────────
            if meta:
                st.markdown(
                    f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
                    f'padding:.55rem .85rem;margin-bottom:.6rem;font-size:.78rem;color:#475569;line-height:1.7">'
                    f'<b>{meta.get("full_name","")}</b> &nbsp;·&nbsp; '
                    f'Recall: <b>{meta.get("recall","—")}</b> &nbsp;·&nbsp; '
                    f'Range: <b>{meta.get("range","—")}</b><br>'
                    f'<span style="color:#64748b">{meta.get("formula","")}</span><br>'
                    f'<span style="color:#6aab90;font-weight:600">▎</span>&nbsp;'
                    f'{meta.get("thresholds","")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # ── Flag summary table with descriptions ──────────────────────────
            ck_data = [
                {"Check": c.replace(f"Flag_{name}_",""), "Flagged": int((res[c]==1).sum())}
                for c in res.columns
                if c.startswith(f"Flag_{name}_") and c not in (overall, narr) and (res[c]==1).any()
            ]
            if ck_data:
                ck_df = pd.DataFrame(ck_data).sort_values("Flagged", ascending=False)
                flag_info = meta.get("quality_flags", {})
                rows_html = "".join(
                    f'<tr>'
                    f'<td style="font-weight:600">{r["Check"]}</td>'
                    f'<td style="color:#64748b;font-size:.76rem">{flag_info.get(r["Check"], "")}</td>'
                    f'<td style="text-align:right;font-weight:700;color:{_flag_style(r["Flagged"])[0]};white-space:nowrap">'
                    f'{r["Flagged"]:,}</td></tr>'
                    for _, r in ck_df.iterrows()
                )
                st.markdown(
                    f'<table class="hfc-table" style="width:100%">'
                    f'<thead><tr><th>Check</th><th>What it means</th><th>Flagged</th></tr></thead>'
                    f'<tbody>{rows_html}</tbody></table>',
                    unsafe_allow_html=True,
                )
                st.write("")

            flagged = (res[res[overall]==1].reset_index(drop=True)
                       if overall in res.columns else res.reset_index(drop=True))
            if flagged.empty:
                st.success(f"✅ No flags raised for {name}.")
            else:
                display_cols = ([narr] if narr in flagged.columns else []) + \
                               [c for c in flagged.columns if c != narr]
                _show_table(flagged[display_cols], max_rows=300)


# ── Tab 4: Methodology ────────────────────────────────────────────────────────

def tab_methodology():
    st.markdown(
        '<div style="background:#f0f6fb;border:1px solid #c8dced;border-radius:8px;'
        'padding:.7rem 1rem;margin-bottom:.85rem;font-size:.81rem;color:#334155;line-height:1.7">'
        '📚 <b>Reference:</b> All indicators follow WFP VAM standard methodology. '
        'Source: <a href="https://vamresources.manuals.wfp.org/" target="_blank" '
        'style="color:#6a9cc8">vamresources.manuals.wfp.org</a> &nbsp;·&nbsp; '
        'Column naming follows the WFP VAM data dictionary (FCSStap, rCSIBorrow, HHSize1859M, …).'
        '</div>',
        unsafe_allow_html=True,
    )

    for name, meta in INDICATOR_METHODOLOGY.items():
        with st.expander(f"**{meta['full_name']}**", expanded=False):
            c1, c2 = st.columns([1, 1], gap="large")

            with c1:
                st.markdown(
                    f'<div style="font-size:.76rem;color:#64748b;line-height:1.8">'
                    f'<b>Recall period:</b> {meta["recall"]}<br>'
                    f'<b>Score range:</b> {meta["range"]}<br>'
                    f'<b>WFP thresholds:</b> {meta["thresholds"]}<br><br>'
                    f'<b>Calculation:</b><br>'
                    f'<code style="background:#f1f5f9;padding:.2rem .4rem;border-radius:4px;font-size:.73rem">'
                    f'{meta["formula"]}</code>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if meta.get("quality_flags"):
                    st.markdown('<div style="margin-top:.7rem;font-size:.73rem;font-weight:700;color:#64748b;'
                                'text-transform:uppercase;letter-spacing:.05em">Quality Flags</div>',
                                unsafe_allow_html=True)
                    for flag, desc in meta["quality_flags"].items():
                        st.markdown(
                            f'<div style="font-size:.76rem;color:#475569;line-height:1.6;margin-bottom:.2rem">'
                            f'<span style="font-weight:600;color:#cc9470">{flag}</span> — {desc}</div>',
                            unsafe_allow_html=True,
                        )

            with c2:
                if meta.get("groups"):
                    rows = "".join(
                        f'<tr><td><code style="font-size:.7rem;background:#f1f5f9;padding:.1rem .3rem;'
                        f'border-radius:3px">{var}</code></td>'
                        f'<td>{grp}</td>'
                        f'<td style="text-align:center;font-weight:700;color:#6a9cc8">{wt}</td>'
                        f'<td style="color:#94a3b8;font-size:.73rem">{ex}</td></tr>'
                        for var, grp, wt, ex in meta["groups"]
                    )
                    st.markdown(
                        f'<table class="hfc-table" style="width:100%">'
                        f'<thead><tr><th>Variable</th><th>Food Group / Strategy</th>'
                        f'<th style="text-align:center">Weight</th><th>Examples</th></tr></thead>'
                        f'<tbody>{rows}</tbody></table>',
                        unsafe_allow_html=True,
                    )


# ── Tab 3: Downloads ──────────────────────────────────────────────────────────

def tab_downloads(results, raw_df, working_df, filename_stem, survey_name):
    st.markdown("**Three outputs for three audiences**")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            '<p style="font-size:.8rem;color:#64748b;margin-bottom:.25rem">'
            '📗 <b>Excel Error Log</b> — Field teams</p>'
            '<p style="font-size:.76rem;color:#94a3b8;line-height:1.55">'
            'Colour-coded flagged records per indicator. Share with field supervisors '
            'to guide data correction and clarification.</p>',
            unsafe_allow_html=True,
        )
        with st.spinner("Building Excel…"):
            excel_bytes = _build_excel_bytes(results, raw_df)
        st.download_button(
            "Download Excel Error Log", data=excel_bytes,
            file_name=f"{filename_stem}_HFC_ErrorLog.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        n_flagged = sum(int((res[f"Flag_{n}_Overall"]==1).sum())
                        for n, res in results.items() if f"Flag_{n}_Overall" in res.columns)
        st.caption(f"Summary · MasterSheet · {len(results)} indicator sheets · {n_flagged} entries")

    with col2:
        st.markdown(
            '<p style="font-size:.8rem;color:#64748b;margin-bottom:.25rem">'
            '📄 <b>HTML Summary Report</b> — Managers</p>'
            '<p style="font-size:.76rem;color:#94a3b8;line-height:1.55">'
            'Standalone HTML with flag rates, enumerator performance, food security '
            'highlights, and recommendations. No internet required.</p>',
            unsafe_allow_html=True,
        )
        with st.spinner("Building HTML…"):
            html_bytes = _build_html_bytes(results, working_df, survey_name)
        st.download_button(
            "Download HTML Report", data=html_bytes,
            file_name=f"{filename_stem}_HFC_Report.html",
            mime="text/html", use_container_width=True,
        )
        st.caption("Self-contained · Print to PDF via browser · No internet needed")

    with col3:
        st.markdown(
            '<p style="font-size:.8rem;color:#64748b;margin-bottom:.25rem">'
            '📊 <b>Live Dashboard</b> — Data quality officers</p>'
            '<p style="font-size:.76rem;color:#94a3b8;line-height:1.55">'
            'The Dashboard tab is your live view — charts update instantly when you '
            're-upload or adjust thresholds. Use browser Print → Save as PDF.</p>',
            unsafe_allow_html=True,
        )
        st.info("Switch to the **Survey Status**, **Enumerator Behavior**, or **Data Quality** tabs to view live charts.", icon="ℹ️")

    st.divider()

    # ── Per-enumerator feedback Excel ─────────────────────────────────────────
    st.markdown("**📤  Per-Enumerator Feedback Report**")
    st.caption(
        "Generates a multi-sheet Excel with one sheet per enumerator showing only their flagged records. "
        "Share with field supervisors so each enumerator receives targeted, personalised feedback."
    )
    ctx_dl    = _ctx(working_df)
    enu_col_dl = ctx_dl["enu"]
    if enu_col_dl:
        if st.button("Generate Enumerator Feedback Excel", key="btn_enu_excel"):
            # Merge all results into one wide dataframe
            overall_flag_cols = [f"Flag_{n}_Overall" for n in results if f"Flag_{n}_Overall"
                                 in results[n].columns]
            all_flags = []
            for ind_name, res_df in results.items():
                flag_cols = [c for c in res_df.columns if c.startswith(f"Flag_{ind_name}")]
                if enu_col_dl in res_df.columns:
                    all_flags.append(res_df[flag_cols])
            if all_flags:
                merged_dl = pd.concat([working_df] + all_flags, axis=1)
                # Determine which rows are flagged at all
                overall_cols_avail = [c for c in merged_dl.columns
                                      if c.startswith("Flag_") and c.endswith("_Overall")]
                if overall_cols_avail:
                    flagged_mask = (
                        merged_dl[overall_cols_avail]
                        .apply(pd.to_numeric, errors="coerce")
                        .fillna(0)
                        .any(axis=1)
                    )
                else:
                    flagged_mask = pd.Series([True] * len(merged_dl))

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                    # Summary sheet
                    summary_rows = []
                    for enu_name, grp in merged_dl.groupby(enu_col_dl):
                        n_surveys  = len(grp)
                        n_flagged  = int(flagged_mask[grp.index].sum()) if overall_cols_avail else 0
                        flag_rate  = round(n_flagged / n_surveys * 100, 1) if n_surveys else 0
                        summary_rows.append({
                            "Enumerator": enu_name,
                            "Total Surveys": n_surveys,
                            "Flagged Records": n_flagged,
                            "Flag Rate %": flag_rate,
                        })
                    summary_df = pd.DataFrame(summary_rows).sort_values("Flag Rate %", ascending=False)
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)
                    # Per-enumerator sheets
                    for enu_name, grp in merged_dl.groupby(enu_col_dl):
                        sheet_name    = str(enu_name)[:31]
                        flagged_grp   = grp[flagged_mask[grp.index]]
                        if flagged_grp.empty:
                            flagged_grp = grp.head(0)  # empty sheet with headers
                        flagged_grp.to_excel(writer, sheet_name=sheet_name, index=False)
                buf.seek(0)
                st.download_button(
                    "⬇️  Download Enumerator Feedback Excel",
                    data=buf,
                    file_name=f"{filename_stem}_EnumeratorFeedback.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_enu_feedback",
                    use_container_width=True,
                )
            else:
                st.warning("No flag data available to build feedback sheets.")
    else:
        st.info("No enumerator column detected — per-enumerator feedback requires an enumerator column.")

    st.divider()
    with st.expander("Preview raw data (first 5 rows)"):
        st.dataframe(raw_df.head(), use_container_width=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Page header ───────────────────────────────────────────────────────────
    col_title, col_meta = st.columns([5, 1], gap="small")
    with col_title:
        st.title("📋  Survey — High-Frequency Data Quality Checks")
        st.caption("Configure checks below · upload your data · click Run Checks")
    with col_meta:
        st.markdown(
            '<div style="text-align:right;padding-top:.5rem;line-height:1.7">'
            '<span style="font-size:.72rem;color:#94a3b8">VAM naming conventions required</span><br>'
            '<span style="font-size:.68rem;color:#cbd5e1">v1.0.0</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Upload ────────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "📂  Upload Survey Data",
        type=["csv", "xlsx", "xls", "dta", "sav"],
        help="CSV, Excel (.xlsx/.xls), Stata (.dta), or SPSS (.sav). Column names must follow WFP VAM naming conventions.",
    )

    if uploaded is None:
        for k in ("results","working_df","raw_df","filename_stem","survey_name"):
            st.session_state.pop(k, None)
        return

    try:
        name = uploaded.name
        if name.endswith(".csv"):
            raw_df = pd.read_csv(uploaded, low_memory=False)
        elif name.endswith((".xlsx", ".xls")):
            raw_df = pd.read_excel(uploaded)
        elif name.endswith(".dta"):
            try:
                raw_df = pd.read_stata(uploaded)
            except ValueError:
                # Stata value labels not unique — read numeric codes directly
                uploaded.seek(0)
                raw_df = pd.read_stata(uploaded, convert_categoricals=False)
                st.info("ℹ️ Duplicate Stata value labels detected — loaded numeric codes instead of label strings. This does not affect the checks.", icon="ℹ️")
        elif name.endswith(".sav"):
            import pyreadstat
            import tempfile, os
            # pyreadstat needs a real file path, not a buffer
            with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            try:
                raw_df, _ = pyreadstat.read_sav(tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            st.error("Unsupported file format.")
            return
    except Exception as exc:
        st.error(f"Could not read file: {exc}")
        return

    filename_stem = Path(uploaded.name).stem
    survey_name   = filename_stem.replace("_"," ").replace("-"," ").title()

    st.success(
        f"**{len(raw_df):,} records** × **{len(raw_df.columns)} columns** — `{uploaded.name}`"
    )

    # ── Configuration panel ───────────────────────────────────────────────────
    enabled, overrides, sample_target = render_config()

    if not enabled:
        st.warning("No indicators selected — enable at least one above.")
        return

    if st.button("▶  Run Checks", type="primary", use_container_width=True):
        results, working_df = run_checks(raw_df, enabled, overrides)
        if not results:
            st.error("No results produced. Check that column names match WFP VAM conventions.")
            return
        st.session_state.update({
            "results": results, "working_df": working_df,
            "raw_df": raw_df, "filename_stem": filename_stem, "survey_name": survey_name,
        })

    if "results" not in st.session_state:
        return

    results    = st.session_state["results"]
    working_df = st.session_state["working_df"]
    raw_cached = st.session_state["raw_df"]
    fstem      = st.session_state["filename_stem"]
    sname      = st.session_state["survey_name"]
    # widget writes its own value to session_state automatically
    stored_target = int(st.session_state.get("sample_target", 0))

    stats = compute_stats(results, working_df)

    st.divider()
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📋  Survey Status",
        "👤  Enumerator Behavior",
        "📊  Indicator Breakdown",
        "🔍  Data Quality",
        "📑  Flag Details",
        "⬇️  Downloads",
        "📖  Methodology",
    ])
    with t1: tab_survey_status(stats, working_df, stored_target)
    with t2: tab_enumerator_behavior(stats, working_df, results)
    with t3: tab_indicator_breakdown(working_df)
    with t4: tab_data_quality(stats, working_df, results)
    with t5: tab_details(results)
    with t6: tab_downloads(results, raw_cached, working_df, fstem, sname)
    with t7: tab_methodology()


if __name__ == "__main__":
    main()
