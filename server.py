"""
Pump Failure Prediction - FastAPI backend (replaces the Streamlit app.py).

Run locally:   uvicorn server:app --reload --port 8000
API docs:      http://localhost:8000/docs

The ETL pipeline in src/ is reused unchanged. Instead of matplotlib images,
every chart endpoint returns plain JSON which the React frontend draws.
"""

import json
import os
import threading
import time
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from src import eda
from src.config import (
    DEFAULT_PLOT_SENSORS,
    HORIZON_MIN,
    INTERP_LIMIT_MIN,
    RAW_CSV,
    SENSOR_COLS,
    SENSOR_LABELS,
    STATUS_COL,
    TARGET,
    TARGET_MODE,
    TIME_COL,
)
from src.extract import ensure_dataset
from src.load import load_to_db
from src.model import predict_risk, train_risk_model
from src.pipeline import run_pipeline

TITLE = "Pump Failure Prediction Dashboard"
MAX_POINTS = 1500
EPOCH = pd.Timestamp("1970-01-01")


# ============================================================
# SMALL HELPERS
# ============================================================

def ms(series) -> list:
    """Datetimes -> epoch milliseconds (unit-agnostic, works on every pandas version)."""
    idx = pd.DatetimeIndex(pd.to_datetime(series))
    return [int(v) for v in ((idx - EPOCH) // pd.Timedelta(milliseconds=1))]


def nums(values) -> list:
    """Numbers -> JSON-safe list (NaN / inf become null)."""
    arr = np.asarray(values, dtype="float64")
    return [float(v) if np.isfinite(v) else None for v in arr]


def stride(n: int, cap: int = MAX_POINTS) -> np.ndarray:
    return np.arange(0, n, max(1, int(np.ceil(n / cap))))


def check_sensor(name: str) -> str:
    if name not in SENSOR_COLS:
        raise HTTPException(400, f"Unknown sensor '{name}'")
    return name


def check_cols(cols: str | None) -> list:
    wanted = cols.split(",") if cols else DEFAULT_PLOT_SENSORS
    return [c for c in wanted if c in SENSOR_COLS]


def label(c: str) -> str:
    return SENSOR_LABELS.get(c, c)


# ============================================================
# SHARED STATE  (pipeline result lives in memory, like st.cache_resource)
# ============================================================

class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = False
        self.state = "idle"          # idle | running | ready | error
        self.error = ""
        self.params = {"inject": True, "level": 1.0}
        self.pending = None
        self.run_id = 0
        self.t0 = None
        self.result = None
        self.raw_t = None
        self.events = []
        self.bundle = None
        self.bundle_state = "idle"   # idle | training | ready | error
        self.bundle_error = ""


store = Store()


def _worker():
    while True:
        with store.lock:
            params = dict(store.params)
            store.state, store.error, store.t0 = "running", "", time.time()
            store.result = store.raw_t = store.bundle = None
            store.bundle_state, store.bundle_error = "idle", ""

        try:
            path = ensure_dataset()

            res = run_pipeline(
                source=str(path),
                save=False,
                inject_noise=params["inject"],
                noise_level=params["level"],
                make_figs=False,
            )

            final = res["final"]

            with store.lock:
                store.result = res
                store.raw_t = pd.to_datetime(res["raw"][TIME_COL], errors="coerce")
                store.events = list(final.loc[final[STATUS_COL] == "BROKEN", TIME_COL])
                store.run_id += 1
                store.state = "ready"

        except Exception as exc:  # shown in the UI instead of a stack trace
            with store.lock:
                store.state, store.error = "error", str(exc)

        with store.lock:
            if store.pending is None:
                store.running = False
                return
            store.params, store.pending = store.pending, None


def start_run(params: dict):
    with store.lock:
        if store.running:
            store.pending = params          # picked up when the current run ends
            return
        store.running = True
        store.params = params
        store.state = "running"

    threading.Thread(target=_worker, daemon=True).start()


def need() -> dict:
    res = store.result

    if res is None or store.state != "ready":
        raise HTTPException(503, "Pipeline is not ready yet")

    return res


# ============================================================
# APP
# ============================================================

@asynccontextmanager
async def lifespan(_app):
    start_run(dict(store.params))   # like Streamlit: the pipeline starts with the app
    yield


app = FastAPI(title="Pump Failure Prediction API", lifespan=lifespan)

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "pump-failure-prediction-api", "docs": "/docs", "state": store.state}


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------- status / control ----------------

class RunBody(BaseModel):
    inject: bool = True
    level: float = 1.0


@app.get("/api/status")
def status():
    return {
        "state": store.state,
        "error": store.error,
        "params": store.params,
        "pending": store.pending is not None,
        "run_id": store.run_id,
        "elapsed": round(time.time() - store.t0, 1) if store.t0 and store.state == "running" else 0,
    }


@app.post("/api/pipeline/run")
def run(body: RunBody):
    start_run({"inject": body.inject, "level": float(min(max(body.level, 0.5), 3.0))})
    return status()


@app.get("/api/meta")
def meta():
    return {
        "title": TITLE,
        "sensors": [{"value": c, "label": label(c)} for c in SENSOR_COLS],
        "default_plot_sensors": DEFAULT_PLOT_SENSORS,
        "target_mode": TARGET_MODE,
        "horizon_hours": HORIZON_MIN // 60,
        "raw_file": f"data/raw/{RAW_CSV.name}",
        "interp_limit_min": INTERP_LIMIT_MIN,
    }


@app.get("/api/overview")
def overview():
    r = need()
    final, report, raw = r["final"], r["report"], r["raw"]

    return {
        "records": len(final),
        "raw_rows": len(raw),
        "clean_rows": len(r["clean"]),
        "quarantined": int(report["pydantic_rejected_rows"]),
        "failure_rate": float(final[TARGET].mean() * 100),
        "flagged": int(final[TARGET].sum()),
        "events": [{"index": i, "label": f"#{i + 1} - {t:%Y-%m-%d %H:%M}"} for i, t in enumerate(store.events)],
        "active_sensors": len(SENSOR_COLS),
        "dead_sensors": report["dead_sensors_dropped"],
        "top_sensors": r["top_sensors"],
        "ba": {
            "rows_in": int(report["rows_in"]),
            "rows_out": int(report["rows_out"]),
            "removed": int(report["rows_removed_total"]),
            "duplicates": int(report["duplicates_removed"] + report["duplicate_timestamps_removed"]),
            "impossible": int(report["total_impossible_values"]),
            "outliers": int(report["total_outliers_replaced"]),
            "missing_before": int(report["missing_before_imputation"]),
        },
    }


# ============================================================
# DASHBOARD CHARTS
# ============================================================

@app.get("/api/telemetry")
def telemetry(
    sensor: str,
    view: str = "latest",
    window: int = Query(30, ge=1, le=240),
    n: int = Query(3000, ge=100, le=50000),
    event: int = 0,
    hours: int = Query(48, ge=1, le=336),
):
    final = need()["final"]
    col = check_sensor(sensor)

    if view == "failure" and store.events:
        center = store.events[min(max(event, 0), len(store.events) - 1)]
        half = pd.Timedelta(hours=hours)
        sel = final[(final[TIME_COL] >= center - half) & (final[TIME_COL] <= center + half)]
    else:
        sel = final.tail(n)

    if sel.empty:
        return {"x": [], "y": [], "mean": [], "warn": [], "recover": [], "broken": []}

    y = pd.to_numeric(sel[col], errors="coerce")
    mean = y.rolling(window, min_periods=1).mean() if window > 1 else None
    status_arr = sel[STATUS_COL].to_numpy()
    times = sel[TIME_COL].to_numpy()

    warn = (sel[TARGET].to_numpy() == 1) & (status_arr == "NORMAL")

    def runs(mask):
        return [[ms([s])[0], ms([e])[0]] for s, e in eda._runs(mask, times)]

    idx = stride(len(sel))
    x_all = sel[TIME_COL].iloc[idx]

    broken = sel[sel[STATUS_COL] == "BROKEN"]

    return {
        "x": ms(x_all),
        "y": nums(y.to_numpy()[idx]),
        "mean": nums(mean.to_numpy()[idx]) if mean is not None else None,
        "warn": runs(warn),
        "recover": runs(status_arr == "RECOVERING"),
        "broken": [{"x": x, "y": v} for x, v in zip(ms(broken[TIME_COL]), nums(pd.to_numeric(broken[col], errors="coerce")))],
        "title": f"{label(col)}  |  {sel[TIME_COL].min():%Y-%m-%d %H:%M} to {sel[TIME_COL].max():%Y-%m-%d %H:%M}",
    }


@app.get("/api/breakdown")
def breakdown(by: str = STATUS_COL):
    if by not in (STATUS_COL, "month", "week", "weekday", "hour"):
        raise HTTPException(400, "Unknown grouping")

    final = need()["final"]
    key = eda._group_key(final, by)
    mask = final[TARGET] == 1
    counts = final.loc[mask].groupby(key[mask]).size()

    if by in ("month", "week", "hour"):
        counts = counts.sort_index()
    else:
        counts = counts.sort_values(ascending=False).head(12)

    return {"by": by, "items": [{"label": str(k), "value": int(v)} for k, v in counts.items()]}


@app.get("/api/stream")
def stream(sensor: str, start: int = Query(0, ge=0), n: int = Query(1000, ge=50, le=5000)):
    """Raw stream vs validated stream for the same time window."""

    r = need()
    clean, raw = r["clean"], r["raw"]
    col = check_sensor(sensor)

    a_win = clean.iloc[start:start + n]

    if a_win.empty:
        return {"empty": True}

    t0, t1 = a_win[TIME_COL].min(), a_win[TIME_COL].max()
    mask = ((store.raw_t >= t0) & (store.raw_t <= t1)).to_numpy()

    bx = store.raw_t[mask]
    by = pd.to_numeric(raw.loc[mask, col], errors="coerce")
    ay = pd.to_numeric(a_win[col], errors="coerce")

    ref = ay.dropna()
    ylim = None

    if len(ref):
        span = max(ref.max() - ref.min(), 1e-6)
        lo = ref.min() - 0.5 * span
        visible = by[by >= lo]
        hi = max(visible.max() if len(visible) else ref.max(), ref.max()) + 0.1 * span
        ylim = [float(lo), float(hi)]

    bi, ai = stride(len(bx), 3200), stride(len(a_win), 3200)

    return {
        "empty": False,
        "ylim": ylim,
        "before": {"x": ms(bx.iloc[bi]), "y": nums(by.to_numpy()[bi])},
        "after": {"x": ms(a_win[TIME_COL].iloc[ai]), "y": nums(ay.to_numpy()[ai])},
    }


@app.get("/api/correlation")
def correlation():
    r = need()
    final = r["final"]
    cols = [c for c in r["top_sensors"] + ["deviation_mean_abs", TARGET] if c in final.columns]
    corr = final[cols].apply(pd.to_numeric, errors="coerce").corr()

    return {"cols": cols, "matrix": [nums(row) for row in corr.to_numpy()]}


# ============================================================
# BEFORE vs AFTER
# ============================================================

@app.get("/api/ba/missing")
def ba_missing():
    r = need()
    raw, clean = r["raw"], r["clean"]

    common = list(raw.columns)
    b = eda._missing_pct(raw[common])
    in_after = [c for c in common if c in clean.columns]
    a = eda._missing_pct(clean[in_after]).reindex(common).fillna(0.0)

    items = [
        {"name": c if c in clean.columns else f"{c} (dropped)", "before": float(b[c]), "after": float(a[c])}
        for c in common
        if b[c] > 0 or a[c] > 0
    ]

    return {"items": items, "note": f"Gaps up to {INTERP_LIMIT_MIN} min are interpolated; longer gaps use the median of the same machine_status."}


def _hist(b, a, n_bins):
    lo, hi = float(min(b.min(), a.min())), float(max(b.max(), a.max()))

    if not hi > lo:
        hi = lo + 1.0

    edges = np.linspace(lo, hi, n_bins + 1)
    mid = (edges[:-1] + edges[1:]) / 2

    return {
        "mid": nums(mid),
        "before": [int(v) for v in np.histogram(b, bins=edges)[0]],
        "after": [int(v) for v in np.histogram(a, bins=edges)[0]],
    }


@app.get("/api/ba/distributions")
def ba_distributions(cols: str | None = None):
    r = need()
    out = []

    for c in check_cols(cols):
        b, a = eda._num(r["raw"], c), eda._num(r["clean"], c)

        if len(b) and len(a):
            out.append({"col": c, "label": label(c), **_hist(b, a, 50)})

    return {"items": out}


@app.get("/api/ba/single")
def ba_single(col: str):
    r = need()
    c = check_sensor(col)

    return {"col": c, "label": label(c), **_hist(eda._num(r["raw"], c), eda._num(r["clean"], c), 40)}


def _box(values: pd.Series):
    v = values.to_numpy(dtype="float64")

    if len(v) == 0:
        return None

    q1, med, q3 = np.percentile(v, [25, 50, 75])
    iqr = q3 - q1
    f_lo, f_hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr

    inside = v[(v >= f_lo) & (v <= f_hi)]
    out = np.sort(v[(v < f_lo) | (v > f_hi)])

    if len(out) > 60:
        out = out[np.linspace(0, len(out) - 1, 60).astype(int)]

    return {
        "q1": float(q1), "med": float(med), "q3": float(q3),
        "wl": float(inside.min()) if len(inside) else float(q1),
        "wh": float(inside.max()) if len(inside) else float(q3),
        "fliers": [float(x) for x in out],
        "min": float(v.min()), "max": float(v.max()),
    }


@app.get("/api/ba/boxplots")
def ba_boxplots(cols: str | None = None):
    r = need()
    out = []

    for c in check_cols(cols):
        b, a = eda._num(r["raw"], c), eda._num(r["clean"], c)

        if not len(b) or not len(a):
            continue

        span = max(float(a.max() - a.min()), 1e-6)

        out.append({
            "col": c, "label": label(c),
            "before": _box(b), "after": _box(a),
            "ylim": [float(a.min() - 0.4 * span), float(a.max() + 2.0 * span)],
        })

    return {"items": out}


@app.get("/api/ba/table")
def ba_table():
    r = need()
    rows = []

    for c in SENSOR_COLS:
        b = pd.to_numeric(r["raw"][c], errors="coerce")
        a = r["clean"][c]

        rows.append({
            "column": c,
            "missing before": int(b.isna().sum()), "missing after": int(a.isna().sum()),
            "min before": b.min(), "min after": a.min(),
            "max before": b.max(), "max after": a.max(),
            "mean before": b.mean(), "mean after": a.mean(),
        })

    df = pd.DataFrame(rows).round(2)

    return {"columns": list(df.columns), "rows": json.loads(df.to_json(orient="values"))}


# ============================================================
# RISK INFERENCE
# ============================================================

def _train(run_id: int):
    try:
        r = store.result
        bundle = train_risk_model(r["final"], r["scale_stats"])

        with store.lock:
            if store.run_id == run_id:
                store.bundle, store.bundle_state = bundle, "ready"

    except Exception as exc:
        with store.lock:
            store.bundle_state, store.bundle_error = "error", str(exc)


@app.get("/api/risk/bundle")
def risk_bundle():
    need()

    with store.lock:
        if store.bundle_state == "idle":
            store.bundle_state = "training"
            threading.Thread(target=_train, args=(store.run_id,), daemon=True).start()

        st = store.bundle_state

    if st == "training":
        return {"ready": False}

    if st == "error":
        raise HTTPException(500, f"Model training failed: {store.bundle_error}")

    b = store.bundle

    return {
        "ready": True,
        "presets": {k: {c: float(v[c]) for c in SENSOR_COLS} for k, v in b["presets"].items()},
        "top_sensors": b["top_sensors"],
        "ranges": {c: list(v) for c, v in b["ranges"].items()},
        "metrics": b["metrics"],
        "n_features": len(b["features"]),
        "horizon_hours": HORIZON_MIN // 60,
        "target_mode": TARGET_MODE,
    }


class PredictBody(BaseModel):
    readings: dict[str, float]


@app.post("/api/risk/predict")
def risk_predict(body: PredictBody):
    need()
    b = store.bundle

    if b is None:
        raise HTTPException(409, "Model is not ready yet")

    base = next(iter(b["presets"].values()))     # healthy baseline fills any missing sensor
    readings = {c: body.readings.get(c, base[c]) for c in SENSOR_COLS}

    out = predict_risk(b, readings)
    out["base_rate"] = b["metrics"]["base_rate"]

    return out


# ============================================================
# DATA & REPORT
# ============================================================

@app.get("/api/report")
def report():
    rep = need()["report"]

    return {
        "summary": [{"metric": k, "value": str(v)} for k, v in rep.items() if not isinstance(v, (dict, list))],
        "full": json.loads(json.dumps(rep, default=str)),
    }


@app.get("/api/report/download")
def report_download():
    rep = need()["report"]

    return Response(
        json.dumps(rep, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="cleaning_report.json"'},
    )


@app.get("/api/data/preview")
def data_preview(rows: int = Query(500, ge=1, le=1000)):
    final = need()["final"]

    head = final.head(rows).copy()
    head[TIME_COL] = head[TIME_COL].astype(str)
    head = head.round(4)

    return {
        "shape": list(final.shape),
        "columns": list(head.columns),
        "rows": json.loads(head.to_json(orient="values")),
    }


@app.get("/api/data/sample.csv")
def data_sample():
    final = need()["final"]

    return Response(
        final.head(1000).to_csv(index=False),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clean_features_sample.csv"'},
    )


@app.post("/api/data/save")
def data_save():
    load_to_db(need()["final"])

    return {"ok": True, "message": "Saved to data/processed/clean_features.csv and data/maintenance.db"}


@app.get("/api/rejected")
def rejected():
    rej = need()["rejected"]

    return {
        "total": int(rej.attrs.get("total_rejected", len(rej))),
        "rows": rej.to_dict("records"),
    }
