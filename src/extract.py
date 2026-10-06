import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    RAW_CSV,
    KAGGLE_DATASET,
    REQUIRED_COLS,
    SENSOR_COLS,
    STATUS_COL,
    RANDOM_STATE,
    IQR_MULTIPLIER,
)


def ensure_dataset(path=RAW_CSV) -> Path:
    """
    Make sure the pump dataset exists in the backend (data/raw/sensor.csv).

    1. If the file is already there -> use it.
    2. Otherwise try `kagglehub` (pip install kagglehub) to download it once.
    3. Otherwise raise a clear error telling you where to put the file.
    """

    path = Path(path)

    if path.exists():
        return path

    try:
        import kagglehub

        folder = Path(kagglehub.dataset_download(KAGGLE_DATASET))

        found = next(folder.rglob("sensor.csv"), None) or next(folder.rglob("*.csv"), None)

        if found is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(found, path)
            return path

    except Exception:
        pass

    raise FileNotFoundError(
        f"Dataset not found at {path}. Download 'sensor.csv' from "
        f"https://www.kaggle.com/datasets/{KAGGLE_DATASET} and put it in that folder."
    )


def extract_csv(source=RAW_CSV, inject_noise: bool = False, noise_level: float = 1.0) -> pd.DataFrame:
    """
    Read the pump sensor CSV from the backend.

    Args:
        source: path to sensor.csv (or a file-like object)
        inject_noise: if True, corrupt a copy of the data on purpose (DEMO ONLY)
                      so the before/after cleaning plots have something to show.
        noise_level: multiplier for the amount of injected noise.

    Returns:
        pd.DataFrame: raw dataframe (index column removed, names stripped).
    """

    if isinstance(source, (str, Path)):
        source = Path(source)

        if not source.exists():
            raise FileNotFoundError(f"CSV file not found: {source}")

    try:
        df = pd.read_csv(source)
    except Exception as exc:
        raise ValueError(f"Unable to read CSV file: {exc}") from exc

    if df.empty:
        raise ValueError("The CSV file is empty.")

    df.columns = df.columns.astype(str).str.strip()

    # the Kaggle file starts with an unnamed running index column
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])

    missing = [c for c in REQUIRED_COLS if c not in df.columns]

    if missing:
        raise ValueError(f"CSV is missing expected columns: {missing}")

    if inject_noise:
        df = inject_demo_noise(df, level=noise_level)

    return df


def inject_demo_noise(df: pd.DataFrame, level: float = 1.0, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """
    DEMO ONLY - corrupt a copy of the data the way real sensors fail:

    * random dropouts (NaN)
    * extreme spikes (caught by the IQR fence)
    * sentinel value -999 (caught by the sentinel check)
    * messy machine_status text (case / spaces)
    * duplicated rows

    Only NORMAL rows are corrupted, so the 7 BROKEN rows and the recovery
    phase stay untouched.
    """

    rng = np.random.default_rng(seed)
    out = df.copy()

    normal_idx = np.flatnonzero(
        out[STATUS_COL].astype("string").str.strip().str.upper().eq("NORMAL").fillna(False).to_numpy()
    )

    def pick(fraction: float) -> np.ndarray:
        size = min(max(1, int(len(normal_idx) * fraction * level)), len(normal_idx))
        return rng.choice(normal_idx, size=size, replace=False)

    for col in SENSOR_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)

        if out[col].notna().sum() == 0:
            continue

        j = out.columns.get_loc(col)

        std = out[col].std()
        top = out[col].max()
        q1, q3 = out[col].quantile([0.25, 0.75])
        fence = q3 + (IQR_MULTIPLIER + 0.5) * (q3 - q1)

        out.iloc[pick(0.008), j] = np.nan

        idx = pick(0.004)
        out.iloc[idx, j] = np.maximum(top + rng.uniform(10, 20, len(idx)) * std, fence)

        out.iloc[pick(0.0008), j] = -999.0

    j = out.columns.get_loc(STATUS_COL)
    out[STATUS_COL] = out[STATUS_COL].astype(object)
    out.iloc[pick(0.002), j] = " normal "

    duplicates = out.sample(frac=min(0.003 * level, 0.5), random_state=seed)

    out = (
        pd.concat([out, duplicates])
        .sort_index(kind="stable")
        .reset_index(drop=True)
    )

    return out