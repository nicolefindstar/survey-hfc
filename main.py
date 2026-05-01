#!/usr/bin/env python3
"""
Survey High-Frequency Data Quality Checks
==========================================

Usage:
  python main.py --input data.csv
  python main.py --input data.xlsx --output my_report.xlsx --config ./config
  python main.py --input data.csv --skip FCS,rCSI

The tool reads a CSV or Excel survey file, runs all enabled data-quality
checks, and writes a colour-coded Excel workbook with:
  • Summary      — flag rates and check breakdown per indicator
  • MasterSheet  — all flagged households consolidated
  • <Indicator>  — one sheet per indicator showing flagged records

Column names must follow VAM naming conventions (see config/standard/).
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from hfc.utils.config_handler import ConfigHandler
from hfc.utils.data_loader import DataLoader
from hfc.reports.excel_reporter import ExcelReporter
from hfc.indicators import get_indicator_class


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("hfc_run.log", mode="w", encoding="utf-8"),
        ],
    )


def run(args):
    logger = logging.getLogger("hfc.main")

    # ── Load data ──────────────────────────────────────────────────────────────
    loader = DataLoader()
    df = loader.load(args.input, sheet=args.sheet)

    # ── Load config ────────────────────────────────────────────────────────────
    cfg_handler = ConfigHandler(args.config)
    main_cfg    = cfg_handler.load_main_config()
    base_cfg    = cfg_handler.load_configurable_config("base")

    skip = {s.strip() for s in args.skip.split(",")} if args.skip else set()
    only = {s.strip() for s in args.only.split(",")} if args.only else set()

    indicators_cfg = main_cfg.get("indicators", {})

    # ── Run indicators in order ────────────────────────────────────────────────
    # Demo runs first so Sum_Children / Sum_Adults are available for rCSI/LCS.
    # FCS runs before rCSI so FCG is available.
    priority = ["Demo", "FCS", "HDDS", "rCSI", "Housing", "LCS",
                "HHExpF", "HHExpNF1M", "HHExpNF6M", "Timing"]
    ordered = priority + [k for k in indicators_cfg if k not in priority]

    results: dict[str, pd.DataFrame] = {}
    working_df = df.copy()   # shared df so derived columns propagate across indicators

    for name in ordered:
        ind_cfg = indicators_cfg.get(name, {})
        if not ind_cfg.get("enabled", True):
            logger.info(f"  [SKIP] {name} — disabled in config")
            continue
        if name in skip:
            logger.info(f"  [SKIP] {name} — excluded via --skip flag")
            continue
        if only and name not in only:
            continue

        try:
            logger.info(f"  [RUN ] {name}")
            cls      = get_indicator_class(name)
            std_cfg  = cfg_handler.load_standard_config(name)
            c_cfg    = cfg_handler.load_configurable_config(name)

            # For expenditure modules share the hhexp.yaml standard config
            if name in ("HHExpF", "HHExpNF1M", "HHExpNF6M"):
                std_cfg = cfg_handler.load_standard_config("hhexp")
                c_cfg   = cfg_handler.load_configurable_config("hhexp")

            indicator = cls(df=working_df, std_config=std_cfg, cfg_config=c_cfg, base_config=base_cfg)
            result_df = indicator.run()
            results[name] = result_df

            # Propagate derived columns (FCG, Sum_Children etc.) back to working_df
            for col in indicator.df.columns:
                if col not in working_df.columns:
                    working_df[col] = indicator.df[col]

            overall = f"Flag_{name}_Overall"
            n_flagged = int((result_df[overall] == 1).sum()) if overall in result_df.columns else "?"
            logger.info(f"         → {n_flagged}/{len(df)} records flagged")

        except KeyError as exc:
            logger.warning(f"  [SKIP] {name} — {exc}")
        except Exception as exc:
            logger.error(f"  [FAIL] {name} — {exc}", exc_info=True)

    if not results:
        logger.error("No indicators produced output. Check column names match config/standard/*.yaml")
        sys.exit(1)

    # ── Generate report ────────────────────────────────────────────────────────
    reporter = ExcelReporter(output_path=args.output)
    reporter.generate(results, df)

    # ── Console summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print(f"  HFC Report: {args.output}")
    print("=" * 62)
    print(f"  {'Indicator':<18} {'Total':>7} {'Flagged':>9} {'Rate':>8}")
    print("  " + "-" * 46)
    for name, res_df in results.items():
        overall = f"Flag_{name}_Overall"
        total   = len(res_df)
        flagged = int((res_df[overall] == 1).sum()) if overall in res_df.columns else 0
        rate    = f"{flagged/total*100:.1f}%" if total else "N/A"
        print(f"  {name:<18} {total:>7,} {flagged:>9,} {rate:>8}")
    print("=" * 62 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Survey High-Frequency Data Quality Checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input",  "-i", required=True,
                        help="Path to survey data file (CSV or Excel)")
    parser.add_argument("--output", "-o", default="hfc_report.xlsx",
                        help="Output Excel report path (default: hfc_report.xlsx)")
    parser.add_argument("--config", "-c", default="./config",
                        help="Config directory (default: ./config)")
    parser.add_argument("--sheet",  "-s", default=0,
                        help="Excel sheet name or index to read (default: first sheet)")
    parser.add_argument("--skip",   default="",
                        help="Comma-separated list of indicators to skip, e.g. 'LCS,Timing'")
    parser.add_argument("--only",   default="",
                        help="Run only these indicators, e.g. 'FCS,rCSI'")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable DEBUG logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not Path(args.input).exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()
