import numpy as np
import pandas as pd

from src.config import (
    TIME_COL,
    STATUS_COL,
    SENSOR_COLS,
    DEAD_SENSORS,
    VALID_STATUS,
    VALID_RANGES,
    SENTINEL_VALUES,
    REQUIRED_COLS,
    TARGET,
    TARGET_MODE,
    HORIZON_MIN,
    IQR_MULTIPLIER,
    INTERP_LIMIT_MIN,
)


def build_target(df: pd.DataFrame) -> pd.Series:
    """
    Create breakdown_flag (0/1) from machine_status + timestamp.

    early_warning  : 1 if a BROKEN row occurs within the next HORIZON_MIN minutes
                     (the BROKEN row itself included)
    abnormal_state : 1 if status is BROKEN or RECOVERING
    """

    status = df[STATUS_COL]

    if TARGET_MODE == "abnormal_state":
        return status.isin(["BROKEN", "RECOVERING"]).astype(int)

    ts = df[TIME_COL].to_numpy(dtype="datetime64[ns]")

    broken = np.sort(ts[(status == "BROKEN").to_numpy()])

    if len(broken) == 0:
        return pd.Series(0, index=df.index)

    pos = np.searchsorted(broken, ts, side="left")

    nxt = broken[np.minimum(pos, len(broken) - 1)]

    ahead = nxt - ts

    flag = (pos < len(broken)) & (ahead <= np.timedelta64(HORIZON_MIN, "m"))

    return pd.Series(flag.astype(int), index=df.index)


def clean_data(df: pd.DataFrame):
    """
    Clean and validate the pump sensor time series.

    Returns:
        cleaned_df  (sorted by time, no missing values, with breakdown_flag)
        cleaning_report
    """

    df = df.copy()

    report = {
        "rows_in": len(df),
        "columns_in": len(df.columns),
        "target_mode": TARGET_MODE,
        "horizon_min": HORIZON_MIN,
    }

    # ========================================================
    # 1. STANDARDIZE COLUMN NAMES
    # ========================================================

    df.columns = df.columns.astype(str).str.strip()

    # ========================================================
    # 2. REQUIRED COLUMN CHECK
    # ========================================================

    missing_required = [c for c in REQUIRED_COLS if c not in df.columns]

    if missing_required:
        raise ValueError("Missing required columns: " + ", ".join(missing_required))

    # ========================================================
    # 3. DEAD SENSORS (100 % empty in the source file)
    # ========================================================

    dead = [c for c in DEAD_SENSORS if c in df.columns]

    report["dead_sensors_dropped"] = dead

    df = df.drop(columns=dead)

    # ========================================================
    # 4. DUPLICATE ROWS
    # ========================================================

    before = len(df)

    df = df.drop_duplicates(keep="first").reset_index(drop=True)

    report["duplicates_removed"] = before - len(df)

    # ========================================================
    # 5. TIMESTAMP CLEANING (parse, sort, unique, gaps)
    # ========================================================

    before_missing = int(df[TIME_COL].isna().sum())

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")

    after_missing = int(df[TIME_COL].isna().sum())

    report["invalid_dates"] = max(0, after_missing - before_missing)
    report["rows_removed_missing_date"] = after_missing

    df = df.dropna(subset=[TIME_COL])

    df = df.sort_values(TIME_COL, kind="stable").reset_index(drop=True)

    before = len(df)

    df = df.drop_duplicates(subset=[TIME_COL], keep="first").reset_index(drop=True)

    report["duplicate_timestamps_removed"] = before - len(df)

    step_min = df[TIME_COL].diff().dt.total_seconds() / 60

    report["median_step_min"] = float(step_min.median()) if len(df) > 1 else 0.0
    report["time_gaps_over_1min"] = int((step_min > 1.5).sum())

    # ========================================================
    # 6. MACHINE STATUS CLEANING
    # ========================================================

    s = df[STATUS_COL].astype("string").str.strip().str.upper()

    s = s.mask(s.eq("").fillna(False))

    df[STATUS_COL] = s

    invalid_status = s.isna() | ~s.isin(VALID_STATUS)

    report["invalid_status_rows_removed"] = int(invalid_status.sum())

    df = df.loc[~invalid_status].reset_index(drop=True)

    df[STATUS_COL] = df[STATUS_COL].astype(str)

    report["status_counts"] = {k: int(v) for k, v in df[STATUS_COL].value_counts().items()}

    # ========================================================
    # 7. NUMERIC CONVERSION
    # ========================================================

    conversion_report = {}

    for col in SENSOR_COLS:

        before_missing = int(df[col].isna().sum())

        df[col] = pd.to_numeric(df[col], errors="coerce")

        after_missing = int(df[col].isna().sum())

        conversion_report[col] = max(0, after_missing - before_missing)

    report["invalid_numeric_values"] = conversion_report

    empty = [c for c in SENSOR_COLS if df[c].isna().all()]

    if empty:
        raise ValueError(
            f"Sensors {empty} contain no valid values. Add them to DEAD_SENSORS in src/config.py."
        )

    # ========================================================
    # 8. SENTINELS / PHYSICALLY IMPOSSIBLE VALUES -> NaN
    # ========================================================

    impossible_report = {}

    for col in SENSOR_COLS:

        mask = df[col].isin(SENTINEL_VALUES) | np.isinf(df[col])

        if col in VALID_RANGES:
            lower, upper = VALID_RANGES[col]

            if lower is not None:
                mask |= df[col] < lower

            if upper is not None:
                mask |= df[col] > upper

        impossible_report[col] = int(mask.sum())

        df.loc[mask, col] = np.nan

    report["impossible_values_nulled"] = impossible_report
    report["total_impossible_values"] = sum(impossible_report.values())

    # ========================================================
    # 9. TARGET
    # ========================================================

    df[TARGET] = build_target(df)

    report["broken_events"] = int((df[STATUS_COL] == "BROKEN").sum())

    # ========================================================
    # 10. OUTLIERS (glitches inside NORMAL operation only)
    #     Fence is computed on NORMAL rows and applied to NORMAL rows only,
    #     so the extreme readings of BROKEN / RECOVERING rows are kept.
    # ========================================================

    normal = df[STATUS_COL].eq("NORMAL")

    outlier_report = {}

    for col in SENSOR_COLS:

        ref = df.loc[normal, col]

        q1 = ref.quantile(0.25)
        q3 = ref.quantile(0.75)

        iqr = q3 - q1

        if not np.isfinite(iqr) or iqr <= 0:
            outlier_report[col] = {"count": 0, "lower_bound": None, "upper_bound": None}
            continue

        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr

        mask = normal & ((df[col] < lower) | (df[col] > upper))

        outlier_report[col] = {
            "count": int(mask.sum()),
            "lower_bound": float(lower),
            "upper_bound": float(upper),
        }

        df.loc[mask, col] = np.nan

    report["outliers_replaced"] = outlier_report
    report["total_outliers_replaced"] = sum(v["count"] for v in outlier_report.values())

    # ========================================================
    # 11. MISSING VALUES BEFORE IMPUTATION
    # ========================================================

    report["missing_before_imputation"] = int(df[SENSOR_COLS].isna().sum().sum())

    # ========================================================
    # 12. IMPUTATION (time series aware)
    #     a) short gaps  -> linear interpolation in time
    #     b) long gaps   -> median of the same machine_status
    #     c) fallback    -> global median
    # ========================================================

    n0 = int(df[SENSOR_COLS].isna().sum().sum())

    df[SENSOR_COLS] = df[SENSOR_COLS].interpolate(
        method="linear", limit=INTERP_LIMIT_MIN, limit_area="inside"
    )

    n1 = int(df[SENSOR_COLS].isna().sum().sum())

    status_median = df.groupby(STATUS_COL)[SENSOR_COLS].transform("median")

    df[SENSOR_COLS] = df[SENSOR_COLS].fillna(status_median)

    n2 = int(df[SENSOR_COLS].isna().sum().sum())

    global_median = df[SENSOR_COLS].median()

    df[SENSOR_COLS] = df[SENSOR_COLS].fillna(global_median)

    report["filled_by_interpolation"] = n0 - n1
    report["filled_by_status_median"] = n1 - n2
    report["filled_by_global_median"] = n2

    report["numeric_imputation_values"] = {c: float(v) for c, v in global_median.items()}

    # ========================================================
    # 13. FINAL DATA TYPES
    # ========================================================

    df[TARGET] = df[TARGET].astype(int)

    # ========================================================
    # 14. FINAL CHECK + REPORT
    # ========================================================

    df = df.reset_index(drop=True)

    report["missing_after_cleaning"] = int(df.isna().sum().sum())

    report["rows_out"] = len(df)
    report["columns_out"] = len(df.columns)
    report["rows_removed_total"] = report["rows_in"] - report["rows_out"]
    report["target_distribution"] = {
        int(k): int(v) for k, v in df[TARGET].value_counts().items()
    }

    return df, report