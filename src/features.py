import numpy as np
import pandas as pd

from src.config import (
    SENSOR_COLS,
    TIME_COL,
    STATUS_COL,
    ROLL_WINDOW,
    POINT_ENGINEERED_COLS,
)


def reference_stats(df: pd.DataFrame) -> dict:
    """
    Mean / std of every sensor during NORMAL operation (healthy baseline).
    Every reading is later expressed as "how many sigmas away from healthy".
    """

    ref = df[df[STATUS_COL] == "NORMAL"] if STATUS_COL in df.columns else df

    if ref.empty:
        ref = df

    mean = ref[SENSOR_COLS].mean()
    std = ref[SENSOR_COLS].std(ddof=0)

    return {
        c: {"mean": float(mean[c]), "std": float(std[c])}
        for c in SENSOR_COLS
    }


def _zscores(X: np.ndarray, stats: dict) -> np.ndarray:

    mean = np.array([stats[c]["mean"] for c in SENSOR_COLS], dtype="float64")
    std = np.array([stats[c]["std"] for c in SENSOR_COLS], dtype="float64")

    std = np.where(std > 0, std, np.nan)

    Z = (X - mean) / std

    return np.nan_to_num(Z, nan=0.0, posinf=0.0, neginf=0.0)


def _point_features(X: np.ndarray, Z: np.ndarray, index) -> pd.DataFrame:

    absZ = np.abs(Z)

    return pd.DataFrame(
        {
            "deviation_mean_abs": absZ.mean(axis=1),
            "deviation_max_abs": absZ.max(axis=1),
            "n_sensors_beyond_3sd": (absZ > 3).sum(axis=1),
            "n_zero_sensors": (X == 0).sum(axis=1),
        },
        index=index,
    )[POINT_ENGINEERED_COLS]


def deviation_features(df: pd.DataFrame, stats: dict) -> pd.DataFrame:
    """Single-reading health features (used for training AND live inference)."""

    X = df[SENSOR_COLS].to_numpy(dtype="float64")

    return _point_features(X, _zscores(X, stats), df.index)


def engineer_features(df: pd.DataFrame):
    """
    Adds to the cleaned data:
      * <sensor>_z                 z-score vs. healthy (NORMAL) baseline
      * deviation_mean_abs         average |z| over all sensors
      * deviation_max_abs          largest |z| of any sensor
      * n_sensors_beyond_3sd       how many sensors are beyond 3 sigma
      * n_zero_sensors             how many sensors read exactly 0 (flat-line)
      * deviation_roll_mean/_std   trailing ROLL_WINDOW-minute mean / std of deviation_mean_abs
    """

    df = df.sort_values(TIME_COL, kind="stable").reset_index(drop=True)

    stats = reference_stats(df)

    X = df[SENSOR_COLS].to_numpy(dtype="float64")
    Z = _zscores(X, stats)

    z_df = pd.DataFrame(
        Z.astype("float32"),
        columns=[f"{c}_z" for c in SENSOR_COLS],
        index=df.index,
    )

    point = _point_features(X, Z, df.index)

    roll = point["deviation_mean_abs"].rolling(ROLL_WINDOW, min_periods=1)

    point["deviation_roll_mean"] = roll.mean()
    point["deviation_roll_std"] = roll.std().fillna(0.0)

    df = pd.concat([df, point, z_df], axis=1)

    return df, stats