"""
Quick baseline risk model for the dashboard's "Risk Inference" page.

This is NOT the Phase-2 scikit-learn pipeline - it is a fast
HistGradientBoosting baseline so the GUI has a live ML engine.

Leakage guard: machine_status (it defines the target) is never a model input.
In early-warning mode the RECOVERING rows (days after a failure) are excluded.

Split: the pump has only 7 failures, so a plain "last 20 % of the timeline"
could contain no failure at all. The split is therefore EVENT based: the last
~30 % of failure events (and everything after the start of their warning
window) form the test set; earlier data is the training set. No shuffling.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.config import (
    MODEL_EXCLUDE_STATUS,
    POINT_ENGINEERED_COLS,
    RANDOM_STATE,
    SENSOR_COLS,
    STATUS_COL,
    TARGET,
    TARGET_MODE,
    TEST_EVENT_FRACTION,
    TIME_COL,
)
from src.features import deviation_features


def _split_point(df: pd.DataFrame):
    """Row position where the test set starts + (total events, test events)."""

    y = df[TARGET].to_numpy()

    prev = np.concatenate(([0], y[:-1]))

    starts = np.flatnonzero((y == 1) & (prev != 1))

    n_events = len(starts)

    if n_events >= 3:
        n_test = max(1, int(round(n_events * TEST_EVENT_FRACTION)))
        cut = int(starts[n_events - n_test])
    else:
        cut = int(len(df) * 0.8)
        n_test = int((starts >= cut).sum())

    return cut, n_events, n_test


def train_risk_model(final: pd.DataFrame, stats: dict) -> dict:

    features = SENSOR_COLS + POINT_ENGINEERED_COLS

    df = final.sort_values(TIME_COL).reset_index(drop=True)

    if TARGET_MODE == "early_warning":
        df = df[~df[STATUS_COL].isin(MODEL_EXCLUDE_STATUS)].reset_index(drop=True)

    cut, n_events, n_test = _split_point(df)

    train, test = df.iloc[:cut], df.iloc[cut:]

    if train[TARGET].nunique() < 2 or test[TARGET].nunique() < 2:
        raise ValueError(
            "Train or test split contains only one class - not enough failure events to train a model."
        )

    model = HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.08,
        max_depth=6,
        random_state=RANDOM_STATE,
    )

    model.fit(train[features], train[TARGET])

    proba = model.predict_proba(test[features])[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {
        "roc_auc": float(roc_auc_score(test[TARGET], proba)),
        "pr_auc": float(average_precision_score(test[TARGET], proba)),
        "precision": float(precision_score(test[TARGET], pred, zero_division=0)),
        "recall": float(recall_score(test[TARGET], pred, zero_division=0)),
        "base_rate": float(test[TARGET].mean()),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "failure_events": int(n_events),
        "test_events": int(n_test),
        "test_start": str(test[TIME_COL].iloc[0]),
    }

    # sensors most correlated with the target on TRAIN data -> editable in the form
    corr = train[SENSOR_COLS].corrwith(train[TARGET]).abs().fillna(0)
    top_sensors = list(corr.sort_values(ascending=False).head(12).index)

    # ready-made readings the user can start from
    healthy = final[(final[STATUS_COL] == "NORMAL") & (final[TARGET] == 0)]

    if healthy.empty:
        healthy = final

    presets = {"Healthy baseline (median of normal operation)": healthy[SENSOR_COLS].median().to_dict()}

    ts = final[TIME_COL].to_numpy(dtype="datetime64[ns]")

    for k, b in enumerate(final.loc[final[STATUS_COL] == "BROKEN", TIME_COL], 1):
        i = np.searchsorted(ts, (b - pd.Timedelta(hours=2)).to_datetime64(), side="right") - 1

        if i >= 0:
            row = final.iloc[i][SENSOR_COLS].astype(float).to_dict()
            presets[f"2 h before failure #{k} ({b:%Y-%m-%d %H:%M})"] = row

    return {
        "model": model,
        "features": features,
        "stats": stats,
        "top_sensors": top_sensors,
        "presets": presets,
        "ranges": {c: (float(final[c].min()), float(final[c].max())) for c in SENSOR_COLS},
        "metrics": metrics,
    }


def predict_risk(bundle: dict, readings: dict) -> dict:
    """Failure probability for one full set of sensor readings."""

    row = pd.DataFrame([{c: float(readings[c]) for c in SENSOR_COLS}])

    dev = deviation_features(row, bundle["stats"])

    X = pd.concat([row, dev], axis=1)[bundle["features"]]

    probability = float(bundle["model"].predict_proba(X)[0, 1])

    return {
        "probability": probability,
        "deviation_mean_abs": float(dev["deviation_mean_abs"].iloc[0]),
        "n_sensors_beyond_3sd": int(dev["n_sensors_beyond_3sd"].iloc[0]),
        "n_zero_sensors": int(dev["n_zero_sensors"].iloc[0]),
    }