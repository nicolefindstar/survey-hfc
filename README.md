# Survey High-Frequency Data Quality Checks (HFC)

A locally-run dashboard for automated data quality monitoring on food security and household survey data. Upload your dataset daily and get a structured view of enumerator behavior, flag rates, duplicate records, and actionable field feedback — before errors compound.

> **Data privacy:** Everything runs on your machine. No files or results are ever uploaded to any server.

---

## What It Does

The tool runs ten indicator modules against your survey data and surfaces issues across four review areas:

### 1. Sequential Checks
Catches structural impossibilities that make a record invalid before any other check runs:
- All required fields missing for an indicator (entire module skipped by respondent)
- Values outside the valid range for the question type (negative expenditure, impossible dates)
- End timestamp before start timestamp

### 2. Indicator-Level Checks
Flags implausible or inconsistent values within each module:

| Module | Key flags |
|---|---|
| **Demographics** | Household size exceeds maximum; age-sex subgroup totals do not match reported total; no adult present; pregnant/lactating women exceed eligible female count |
| **FCS** | All food groups identical (anchoring); staple foods consumed ≤1 day; score below low threshold or at theoretical maximum |
| **HDDS** | All groups zero; score out of range |
| **rCSI** | Zero coping score with Poor food security; high coping score with Acceptable food security; adult meal sacrifice reported with no children in household |
| **Housing** | Missing or invalid housing status codes |
| **LCS** | Child-specific strategy applied with no children; all strategies marked N/A despite Poor food security; emergency strategy applied without any stress or crisis strategy first |
| **Food Expenditure** | All food sources zero; single item below minimum meaningful price; single item above maximum plausible value |
| **Non-food Expenditure (1-month)** | Item below minimum meaningful price; item above maximum plausible value |
| **Non-food Expenditure (6-month)** | Item below minimum meaningful price; item above maximum plausible value |
| **Timing** | Interview shorter than minimum duration; interview longer than maximum duration; start hour outside expected working hours |

### 3. Cross-Indicator Checks
Detects logical contradictions across indicators using FEWS NET illogicality pairs — combinations that cannot coexist under standard food security frameworks (e.g. Poor FCS with zero coping strategies, Acceptable FCS with extreme coping).

### 4. Enumerator Monitoring
Surfaces patterns that suggest coaching, rushing, or fabrication:
- Per-enumerator flag rates vs. overall average
- Enumerator means on key indicators (FCS, rCSI, HDDS, HH size, duration) flagged when they deviate more than 1.5 standard deviations from the dataset mean
- Daily submission heatmap by enumerator
- Missing data rate by indicator and enumerator

---

## Outputs

| Output | Description |
|---|---|
| **Survey Status tab** | Cumulative and daily submission counts, progress vs. target, estimated days to completion, priority action items, enumerator and area completion tables |
| **Enumerator Behavior tab** | Flag rates per enumerator, indicator means comparison table, daily submission heatmap |
| **Data Quality tab** | Duplicate HHID detection, flag rates by indicator, FCS and rCSI distributions, FEWS NET illogicality matrix, missing data heatmap by indicator × enumerator |
| **Flag Details tab** | Full flagged record tables per indicator with plain-language narrative explanations |
| **HTML report** | Self-contained manager report — print to PDF via browser, no internet required |
| **Excel error log** | Colour-coded workbook with one sheet per indicator, ready for field team review |
| **Enumerator feedback Excel** | One sheet per enumerator showing only their flagged records, with a summary sheet |

---

## Requirements

- Python 3.9 or higher
- Internet connection on first run (to install packages)

---

## Quick Start

### Option A — One-click launcher (recommended)

| Platform | File |
|---|---|
| Windows | Double-click `Run HFC Checks.bat` |
| macOS | Double-click `Run HFC Checks.command` |

The launcher will automatically create a virtual environment, install all dependencies, and open the app in your browser. No terminal knowledge required.

> **macOS note:** On first run, right-click `Run HFC Checks.command` → Open → Open, to allow execution.

### Option B — Manual setup

**Requirements:** Python 3.9 or higher

```bash
# 1. Clone the repository
git clone https://github.com/nicolefindstar/survey-hfc.git
cd survey-hfc

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Usage

1. Launch the app using either method above
2. Upload your survey file — CSV, Excel (`.xlsx` / `.xls`), Stata (`.dta`), or SPSS (`.sav`)
3. Set your designed sample size if you want progress tracking
4. Select the indicators present in your questionnaire and adjust thresholds if needed
5. Click **▶ Run Checks**
6. Review results across the tabs and download the reports for field teams

A detailed setup guide (including troubleshooting and FAQ) is available in [`SETUP.md`](SETUP.md).

---

## Column Naming

Column names must follow the VAM standard naming convention. The tool auto-detects context columns (HHID, enumerator, area, date) by matching against a list of accepted names. Indicator columns are matched by exact name.

See [`SETUP.md`](SETUP.md) for the full column reference tables.

---

## Configuration

All thresholds can be adjusted in the app UI without touching any files. To set permanent defaults for a specific deployment, edit the YAML files in `config/configurable/`.

The key parameter unique to this tool is **minimum meaningful price** (`min_item_price` in `config/configurable/hhexp.yaml`): set it to the price of the cheapest plausible local purchase (e.g. a loaf of bread or a bus token) and any expenditure item recorded as non-zero but below this floor will be flagged as a likely digit-drop entry error.

---

## File Structure

```
survey-hfc/
├── app.py                        # Streamlit web interface
├── main.py                       # Command-line entry point
├── requirements.txt              # Python dependencies
├── Run HFC Checks.bat            # One-click launcher for Windows
├── Run HFC Checks.command        # One-click launcher for macOS
├── SETUP.md                      # Setup guide
│
├── config/
│   ├── main_config.yaml          # Indicator enable/disable list
│   ├── configurable/             # Editable thresholds — one file per indicator
│   └── standard/                 # Column definitions and valid ranges (do not edit)
│
└── hfc/
    ├── indicators/               # One class per indicator module
    │   ├── base.py               # Shared flag and narrative logic
    │   ├── demo.py
    │   ├── fcs.py
    │   ├── hdds.py
    │   ├── hhexp.py              # Food and non-food expenditure
    │   ├── housing.py
    │   ├── lcs.py
    │   ├── rcsi.py
    │   └── timing.py
    ├── reports/
    │   ├── excel_reporter.py     # Colour-coded Excel output
    │   └── html_reporter.py      # Self-contained HTML manager report
    └── utils/
        ├── config_handler.py
        └── data_loader.py
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `streamlit >= 1.32` | Web interface |
| `pandas >= 1.5` | Data loading and manipulation |
| `numpy >= 1.23` | Numerical operations |
| `plotly >= 5.18` | Charts and heatmaps |
| `openpyxl >= 3.0` | Reading and writing Excel files |
| `xlsxwriter >= 3.0` | Formatted Excel output |
| `pyyaml >= 6.0` | Configuration files |
| `pyreadstat >= 1.2` | Reading Stata and SPSS files |

---

## Command-Line Interface

For batch processing without the UI:

```bash
python main.py --input data.csv
python main.py --input data.xlsx --output report.xlsx
python main.py --input data.csv --skip LCS,Timing
python main.py --input data.csv --only FCS,rCSI --verbose
```

| Argument | Default | Description |
|---|---|---|
| `--input` / `-i` | *(required)* | Path to survey data file |
| `--output` / `-o` | `hfc_report.xlsx` | Output Excel report path |
| `--config` / `-c` | `./config` | Config directory |
| `--sheet` / `-s` | `0` | Excel sheet name or index |
| `--skip` | — | Comma-separated indicators to skip |
| `--only` | — | Run only these indicators |
| `--verbose` / `-v` | — | Enable debug logging |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `python3: command not found` | Install Python 3.9+ from [python.org](https://www.python.org/downloads/) |
| `ModuleNotFoundError: streamlit` | Activate the virtual environment first |
| No flags generated after upload | Column names must match VAM convention exactly — see [`SETUP.md`](SETUP.md) |
| Timing checks produce no output | Ensure `start` and `end` are timezone-aware ISO 8601 timestamps (ODK/SurveyCTO default) |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` |
| macOS: launcher blocked | Right-click → Open → Open to bypass Gatekeeper |
| Windows: activation policy error | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell as Administrator |

For the full troubleshooting guide and column reference, see [`SETUP.md`](SETUP.md).

---

## License

This project is intended for research use. Please contact the author before redistribution.
