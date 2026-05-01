# Survey HFC — Setup Guide

This tool runs entirely on your computer. No data is uploaded to any server.
Your survey files are processed locally and never leave your machine.

---

## What You Need

Before starting, make sure you have the project folder containing:

| File / Folder | Purpose |
|---|---|
| `app.py` | The application |
| `requirements.txt` | List of software dependencies |
| `config/` | Threshold and column definition files |
| `hfc/` | Indicator check modules |
| `Run HFC Checks.bat` | One-click launcher for Windows |
| `Run HFC Checks.command` | One-click launcher for macOS |

Place the folder anywhere on your computer (e.g. your Desktop).

---

## Windows Instructions

### Step 1 — Check Python is installed

Open **Command Prompt** (press `Win + R`, type `cmd`, press Enter) and run:

```cmd
python --version
```

You should see something like `Python 3.10.x` or `Python 3.11.x`.

- **If Python is not found or the version is below 3.9:**
  1. Go to [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
  2. Download the latest **3.11.x** Windows installer (64-bit version)
  3. Run the installer — on the first screen, tick **"Add Python to PATH"** before clicking Install Now
  4. Close and reopen Command Prompt, then run `python --version` again to confirm

---

### Step 2 — Navigate to the app folder

In Command Prompt, type (adjust the path if your folder is elsewhere):

```cmd
cd %USERPROFILE%\Desktop\survey-hfc
```

To confirm you are in the right place, run `dir` — you should see `app.py` and `requirements.txt` listed.

---

### Step 3 — One-click launch (recommended)

Double-click **`Run HFC Checks.bat`**.

The script will create a virtual environment on first run, install all dependencies, and open the app in your browser at `http://localhost:8501`. Subsequent runs skip setup and launch immediately.

> If Windows Defender SmartScreen blocks the file, click **More info** → **Run anyway**.

---

### Step 3 (alternative) — Manual launch

**Create a virtual environment** *(first time only)*:

```cmd
python -m venv venv
```

**Activate the virtual environment**:

```cmd
venv\Scripts\activate
```

Your prompt will change to show `(venv)` at the beginning.

> **If you see an error about script execution being disabled**, run the following in PowerShell (right-click Start → Windows PowerShell as Administrator):
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then close PowerShell and return to Command Prompt.

**Install dependencies** *(first time only)*:

```cmd
pip install -r requirements.txt
```

**Launch the app**:

```cmd
streamlit run app.py
```

---

### Every subsequent time (returning users — Windows)

Double-click `Run HFC Checks.bat`, or run manually:

```cmd
cd %USERPROFILE%\Desktop\survey-hfc
venv\Scripts\activate
streamlit run app.py
```

### To stop the app

Press `Ctrl + C` in Command Prompt, or close the window.

---

---

## macOS Instructions

### Step 1 — Check Python is installed

Open **Terminal** (press `⌘ + Space`, type `Terminal`, press Enter) and run:

```bash
python3 --version
```

You should see something like `Python 3.10.x` or `Python 3.11.x`.

- **If Python is not found:** Download and install it from [https://www.python.org/downloads/](https://www.python.org/downloads/). Select the latest **3.11.x** release for macOS.
- **If the version is below 3.9:** Install 3.11 alongside your current version — both can coexist.

---

### Step 2 — Navigate to the app folder

```bash
cd ~/Desktop/survey-hfc
```

To confirm you are in the right place, run `ls` — you should see `app.py` and `requirements.txt` listed.

---

### Step 3 — One-click launch (recommended)

Double-click **`Run HFC Checks.command`**.

> On first run, macOS may block the file. Right-click → Open → Open to allow execution. You only need to do this once.

The script will create a virtual environment, install all dependencies, and open the app in your browser at `http://localhost:8501`.

---

### Step 3 (alternative) — Manual launch

**Create a virtual environment** *(first time only)*:

```bash
python3 -m venv venv
```

**Activate the virtual environment**:

```bash
source venv/bin/activate
```

Your prompt will change to show `(venv)` at the beginning.

**Install dependencies** *(first time only)*:

```bash
pip install -r requirements.txt
```

This may take 1–2 minutes on first run.

**Launch the app**:

```bash
streamlit run app.py
```

A browser window will open automatically at `http://localhost:8501`. If it does not open, paste that address into any browser manually.

---

### Every subsequent time (returning users — macOS)

Double-click `Run HFC Checks.command`, or run manually:

```bash
cd ~/Desktop/survey-hfc
source venv/bin/activate
streamlit run app.py
```

### To stop the app

Press `Ctrl + C` in Terminal.

---

---

## Column Naming Reference

Column names must match the VAM convention exactly (case-sensitive). The tool auto-detects context columns and matches indicator columns by name.

### Context columns (auto-detected)

| Purpose | Accepted column names |
|---|---|
| Household ID | `HHID`, `hhid`, `_uuid`, `uuid`, `instanceID`, `ID` |
| Enumerator | `EnuName`, `enumerator_name`, `enum_name`, `EnuID`, `enumerator` — or any column containing `enumerat` |
| Supervisor | `EnuSupervisorName`, `supervisor_name`, `supervisor` — or any column containing `supervis` |
| Admin area | `ID02`, `ID01`, `admin2`, `admin1`, `district`, `region`, `woreda`, `county` |
| Survey date | `SvyDate`, `today`, `_submission_time`, `SubmissionDate`, `date` |

### Demographics

| Column | Description | Range |
|---|---|---|
| `HHSize` | Total household size | 1–99 |
| `HHSize01M` / `HHSize01F` | Children 0–1 months, male / female | 0–30 |
| `HHSize24M` / `HHSize24F` | Children 2–4 months, male / female | 0–30 |
| `HHSize511M` / `HHSize511F` | Children 5–11 months, male / female | 0–30 |
| `HHSize1217M` / `HHSize1217F` | Children 12–17 months, male / female | 0–30 |
| `HHSize1859M` / `HHSize1859F` | Adults 18–59, male / female | 0–30 |
| `HHSize60AboveM` / `HHSize60AboveF` | Elderly 60+, male / female | 0–30 |
| `HHPregLactNb` | Pregnant or lactating women | 0–20 |

### Food Consumption Score (FCS)

Values = days of consumption in the past 7 days (0–7).

| Column | Food group | Weight |
|---|---|---|
| `FCSStap` | Cereals and starchy staples | ×2 |
| `FCSPulse` | Pulses, legumes and nuts | ×3 |
| `FCSDairy` | Dairy products | ×4 |
| `FCSPr` | Meat, fish and eggs | ×4 |
| `FCSVeg` | Vegetables | ×1 |
| `FCSFruit` | Fruits | ×1 |
| `FCSFat` | Oil and fats | ×0.5 |
| `FCSSugar` | Sugar and sweets | ×0.5 |

FCS = sum of weighted values (max 112). Classification thresholds: **Poor ≤21 · Borderline 21.5–35 · Acceptable >35** (use 28/42 in high sugar-oil contexts).

### Reduced Coping Strategies Index (rCSI)

Values = days the strategy was used in the past 7 days (0–7).

| Column | Strategy | Weight |
|---|---|---|
| `rCSILessQlty` | Relied on less preferred or cheaper food | ×1 |
| `rCSIBorrow` | Borrowed food or relied on help | ×2 |
| `rCSIMealNb` | Reduced number of meals per day | ×1 |
| `rCSIMealSize` | Restricted portion sizes | ×1 |
| `rCSIMealAdult` | Adults restricted intake so children could eat | ×3 |

rCSI = sum of weighted values (max 56). Crisis threshold: **≥19**.

### Household Dietary Diversity Score (HDDS)

Binary columns — 0 (not consumed) or 1 (consumed in the past 24 hours). The 12 food groups are defined in `config/standard/hdds.yaml`.

### Livelihood Coping Strategies (LCS)

| Value | Meaning |
|---|---|
| `10` | Applied |
| `20` | Not needed |
| `30` | Exhausted — no longer an option |
| `9999` | Not applicable |

Stress, crisis, and emergency strategy column lists are configured in `config/standard/lcs.yaml`.

### Expenditure

Column pattern: `{Category}{Source}` — for example `HHExpFCer_Purch_MN_7D`.

**Food — 7-day recall** (sources: `_Purch_MN_7D`, `_GiftAid_MN_7D`, `_OwnProd_MN_7D`):

`HHExpFCer` · `HHExpFTub` · `HHExpFPulse` · `HHExpFVeg` · `HHExpFFruit` · `HHExpFMeat` · `HHExpFFish` · `HHExpFDairy` · `HHExpFEgg` · `HHExpFOil` · `HHExpFSugar` · `HHExpFCond` · `HHExpFBev` · `HHExpFOther`

**Non-food — 1-month recall** (sources: `_Purch_MN_1M`, `_GiftAid_MN_1M`):

`HHExpNFHyg` · `HHExpNFTrans` · `HHExpNFFuel` · `HHExpNFWat` · `HHExpNFComm` · `HHExpNFMed` · `HHExpNFEduc` · `HHExpNFOther`

**Non-food — 6-month recall** (sources: `_Purch_MN_6M`, `_GiftAid_MN_6M`):

`HHExpNFCloth` · `HHExpNFRent` · `HHExpNFDurable` · `HHExpNFCerem` · `HHExpNFDebt`

### Timing

| Column | Description |
|---|---|
| `start` | Interview start timestamp — timezone-aware ISO 8601 (ODK / SurveyCTO device time) |
| `end` | Interview end timestamp — must be after `start` |

---

## Configuration Reference

All thresholds can be changed in the app UI. To make changes permanent, edit the files in `config/configurable/`.

### `config/configurable/fcs.yaml`

| Parameter | Default | Description |
|---|---|---|
| `low_fcs_threshold` | 10 | Flag FCS below this value |
| `high_fcs_threshold` | 100 | Flag FCS above this value |
| `low_staple_threshold` | 2 | Flag FCSStap at or below this value |
| `fcg_poor_threshold` | 21 | FCS Poor classification cut-off |
| `fcg_borderline_threshold` | 35 | FCS Borderline classification cut-off |

### `config/configurable/rcsi.yaml`

| Parameter | Default | Description |
|---|---|---|
| `high_rcsi_with_acceptable_fcg` | 18 | Flag high rCSI combined with Acceptable FCS |

### `config/configurable/timing.yaml`

| Parameter | Default | Description |
|---|---|---|
| `short_duration_min` | 20 | Flag interviews shorter than this many minutes |
| `long_duration_min` | 120 | Flag interviews longer than this many minutes |
| `utc_offset_hours` | 0 | Local timezone offset from UTC |
| `abnormal_early_morning_end` | 7 | Flag interviews starting before this hour (24h) |
| `abnormal_evening_start` | 19 | Flag interviews starting after this hour (24h) |

### `config/configurable/hhexp.yaml`

| Parameter | Default | Description |
|---|---|---|
| `min_item_price` | 0 | Minimum meaningful price in local currency. Any non-zero item below this value is flagged as implausibly small. Set to the price of a basic local purchase (e.g. bread, bus token). Leave at 0 to disable. |
| `max_single_item_food_7d` | 1,000,000 | Flag food items above this value |
| `max_single_item_nonfood_1m` | 1,000,000 | Flag short-term non-food items above this value |
| `max_single_item_nonfood_6m` | 5,000,000 | Flag long-term non-food items above this value |
| `flag_zero_total_food` | true | Flag households where all food expenditure is zero |

### `config/configurable/demo.yaml`

| Parameter | Default | Description |
|---|---|---|
| `high_hhsize_threshold` | 30 | Flag households larger than this size |

---

## Troubleshooting

| Problem | Likely cause | Solution |
|---|---|---|
| `python3: command not found` | Python is not installed | Follow Step 1 for your operating system |
| `pip: command not found` | pip not on PATH | Use `python3 -m pip install -r requirements.txt` instead |
| `ModuleNotFoundError: No module named 'streamlit'` | Virtual environment not active | Run the activate command before launching |
| No flags generated after upload | Column names do not match convention | Check names against the column reference tables above — matching is case-sensitive |
| Timing module produces no output | Timestamps not timezone-aware | Ensure `start` and `end` are exported in ODK/SurveyCTO default ISO 8601 format |
| Browser does not open automatically | Streamlit cannot detect browser | Navigate manually to `http://localhost:8501` |
| Port 8501 already in use | Another Streamlit instance is running | Stop it with `Ctrl + C`, or use `streamlit run app.py --server.port 8502` |
| Windows: `activate` gives execution policy error | PowerShell security setting | Follow the PowerShell note in Windows Step 3 |
| macOS: `Run HFC Checks.command` blocked | Gatekeeper security setting | Right-click → Open → Open |
| Stata file fails to load | Duplicate value labels | The tool will retry automatically with numeric codes and show an info message |

---

## Frequently Asked Questions

**Is my data safe?**
Yes. The application runs entirely on your local machine. No survey data, results, or any other information is transmitted to any external server.

**Can I run this without an internet connection?**
Yes, once dependencies are installed the app runs fully offline. An internet connection is only needed the first time (to install packages and load the Open Sans font in the browser).

**Can I use data that does not follow the VAM column naming?**
The indicator modules require exact column name matches. You can rename columns in your data export, or adjust the column lists in `config/standard/<indicator>.yaml` to match your own naming convention.

**How do I add a new country or context?**
Adjust the thresholds in `config/configurable/` for the specific context (currency scale, working hours, household size norms). No code changes are needed.

**How do I update the app when a new version is available?**
Replace the project files with the new version. Re-run `pip install -r requirements.txt` with the virtual environment active to update any changed dependencies.

**Where are the downloaded reports saved?**
Reports are saved to your browser's default download folder.

---

*Survey HFC · Aligned with iehfc (World Bank DIME) and SurveyCTO high-frequency check frameworks*
