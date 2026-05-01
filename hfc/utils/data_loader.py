import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED = {".csv", ".xlsx", ".xls"}


class DataLoader:
    """Loads survey data from CSV or Excel into a pandas DataFrame."""

    def load(self, path: str, sheet: str | int = 0) -> pd.DataFrame:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        if p.suffix not in SUPPORTED:
            raise ValueError(f"Unsupported file type '{p.suffix}'. Supported: {SUPPORTED}")

        if p.suffix == ".csv":
            df = pd.read_csv(path, low_memory=False)
        else:
            df = pd.read_excel(path, sheet_name=sheet)

        logger.info(f"Loaded {len(df):,} rows × {len(df.columns)} columns from '{p.name}'")
        return df
