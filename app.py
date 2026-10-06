"""
Pump Failure Prediction Dashboard (Streamlit)

Run with:   streamlit run app.py

The dataset is read from the backend (data/raw/sensor.csv) - nothing to upload.
The full ETL pipeline runs automatically when the app starts.
"""

import io
import json
from contextlib import contextmanager

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src import eda
from src.config import (
    DEFAULT_PLOT_SENSORS,
    HORIZON_MIN,
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
from src.theme import get_css

st.set_page_config(page_title="Pump Failure Prediction", page_icon="🛡️", layout="wide")

TITLE = "Pump Failure Prediction Dashboard"


# ============================================================
# CACHED HEAVY WORK
# ============================================================

@st.cache_resource(show_spinner=False)
def get_results(path, stamp, inject_noise, noise_level):
    """Run the full ETL pipeline once per input combination (not on every click)."""

    return run_pipeline(
        source=path,
        save=False,
        inject_noise=inject_noise,
        noise_level=noise_level,
        make_figs=False,
    )


@st.cache_resource(show_spinner=False)
def get_model(_final, _stats, key):
    """Train the baseline risk model once per pipeline result."""

    return train_risk_model(_final, _stats)


# ============================================================
# SMALL UI HELPERS
# ============================================================

def kpi(col, label, value, sub=""):
    col.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub or "&nbsp;"}</div></div>',
        unsafe_allow_html=True,
    )


@contextmanager
def panel(key, title):
    with st.container(key=f"panel_{key}"):
        st.markdown(f'<div class="panel-title">{title}</div>', unsafe_allow_html=True)
        yield


def show_fig(fig, name, download=True):
    """Render a matplotlib figure (full width) with an optional PNG download button."""

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    data = buf.getvalue()

    try:
        st.image(data, width="stretch")
    except TypeError:  # older Streamlit versions
        st.image(data, use_container_width=True)

    if download:
        st.download_button("Download PNG", data, file_name=f"{name}.png",
                           mime="image/png", key=f"dl_{name}")


def sensor_label(c):
    return SENSOR_LABELS.get(c, c)


def pct(x):
    return f"{x:.2f}%"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(f"### {TITLE}")

    dark = st.toggle("Dark mode", value=False, key="dark_mode")
    mode = "dark" if dark else "light"

    st.divider()
    st.markdown("**Data source**")
    st.caption(f"Backend file: `data/raw/{RAW_CSV.name}` (pump sensor data, loaded automatically)")

    if TARGET_MODE == "early_warning":
        st.caption(f"Target: BROKEN within the next {HORIZON_MIN // 60} h")
    else:
        st.caption("Target: machine is BROKEN or RECOVERING")

    st.divider()
    st.markdown("**Cleaning demo**")

    inject = st.toggle(
        "Simulate dirty data",
        value=True,
        help="The real file already has gaps (e.g. sensor_50 is ~35% empty) but few glitches. "
             "This corrupts a COPY (dropouts, spikes, -999 sentinels, messy status text, duplicates) "
             "so the before/after graphs show more cleaning work. Turn it off to see the real data only.",
    )

    level = st.slider("Noise intensity", 0.5, 3.0, 1.0, 0.5, disabled=not inject)

    if st.button("Re-run pipeline", key="rerun"):
        st.cache_resource.clear()
        st.rerun()

eda.set_theme(mode)
st.markdown(get_css(mode), unsafe_allow_html=True)


# ============================================================
# LOAD BACKEND DATASET + RUN PIPELINE
# ============================================================

try:
    data_path = ensure_dataset()
except Exception as exc:
    st.markdown(f'<div class="sg-header">{TITLE}</div>', unsafe_allow_html=True)
    st.error(str(exc))
    st.stop()

try:
    with st.spinner("Running ETL pipeline (extract, clean, validate, engineer features)... "
                    "the first run takes about a minute."):
        result = get_results(str(data_path), data_path.stat().st_mtime, inject, float(level))
except Exception as exc:  # show a readable error instead of a stack trace
    st.markdown(f'<div class="sg-header">{TITLE}</div>', unsafe_allow_html=True)
    st.error(f"Pipeline failed: {exc}")
    st.stop()

raw = result["raw"]
clean = result["clean"]
final = result["final"]
report = result["report"]
rejected = result["rejected"]
scale_stats = result["scale_stats"]
top_sensors = result["top_sensors"]

# ============================================================
# HEADER + NAVIGATION
# ============================================================

chip = '<span class="sg-chip">noise demo ON</span>' if inject else ""

st.markdown(
    f'<div class="sg-header"><div>{TITLE}{chip}</div>'
    f'<span class="sg-sub">{len(final):,} cleaned records</span></div>',
    unsafe_allow_html=True,
)

page = st.radio(
    "Page",
    ["Dashboard", "Before vs After", "Risk Inference", "Data & Report"],
    horizontal=True,
    label_visibility="collapsed",
    key="page",
)

# ============================================================
# PAGE 1 - DASHBOARD
# ============================================================

if page == "Dashboard":

    events = list(final.loc[final[STATUS_COL] == "BROKEN", TIME_COL])

    c = st.columns(5)
    kpi(c[0], "Records Loaded", f"{len(final):,}", f"{len(raw):,} raw rows in")
    kpi(c[1], "Quarantined", f"{report['pydantic_rejected_rows']:,}", "failed schema validation")
    kpi(c[2], "Failure-Window Rate", pct(final[TARGET].mean() * 100), f"{int(final[TARGET].sum()):,} records flagged")
    kpi(c[3], "Breakdown Events", f"{len(events)}", "machine_status = BROKEN")
    kpi(c[4], "Active Sensors", f"{len(SENSOR_COLS)}", ", ".join(report["dead_sensors_dropped"]) + " dropped (empty)")

    st.write("")

    left, right = st.columns(2)

    with left:
        with panel("telemetry", "Live Sensor Telemetry Trend"):
            sensor = st.selectbox("Sensor", SENSOR_COLS, index=SENSOR_COLS.index(top_sensors[0]),
                                  key="tele_sensor", format_func=sensor_label)

            view = st.radio("View", ["Latest samples", "Around a failure"], horizontal=True,
                            key="tele_view", label_visibility="collapsed")

            c1, c2 = st.columns(2)
            window = c1.slider("Rolling window (min)", 1, 240, 30, key="tele_window")

            center, hours, n = None, 48, 3000

            if view == "Latest samples":
                n = c2.slider("Samples", 500, 20000, 3000, 500, key="tele_n")
            elif events:
                hours = c2.slider("Hours around failure", 6, 168, 48, 6, key="tele_hours")
                idx = st.selectbox("Failure event", list(range(len(events))), key="tele_event",
                                   format_func=lambda i: f"#{i + 1} - {events[i]:%Y-%m-%d %H:%M}")
                center = events[idx]
            else:
                st.info("No BROKEN events in the data.")

            show_fig(eda.plot_telemetry(final, sensor, window, n, center, hours), "telemetry")

    with right:
        with panel("breakdown", "Breakdown Analysis"):
            by = st.selectbox(
                "Group failure-window records by",
                [STATUS_COL, "month", "week", "weekday", "hour"],
                key="bd_by",
            )
            show_fig(eda.plot_failure_breakdown(final, by), "breakdowns")

    left, right = st.columns(2)

    with left:
        with panel("signal", "Signal Conditioning: Raw Outliers vs Validated Stream"):
            st.caption("Uses the sensor chosen in the telemetry panel.")

            max_start = max(len(clean) - 1000, 0)

            start = st.slider("Window start (row)", 0, max_start, 0, 1000, key="sig_start") if max_start else 0
            n_sig = st.slider("Samples", 200, 3000, 1000, 100, key="sig_n")

            show_fig(eda.plot_stream_before_after(raw, clean, sensor, start, n_sig), "signal_conditioning")

    with right:
        with panel("corr", "Correlation Matrix (Sensors Most Linked to Failure)"):
            cols = top_sensors + ["deviation_mean_abs", TARGET]
            show_fig(eda.plot_correlation(final, "Correlation Matrix", cols), "correlation")

# ============================================================
# PAGE 2 - BEFORE vs AFTER
# ============================================================

elif page == "Before vs After":

    outliers = report["total_outliers_replaced"]

    c = st.columns(5)
    kpi(c[0], "Rows In", f"{report['rows_in']:,}", "raw")
    kpi(c[1], "Rows Out", f"{report['rows_out']:,}", f"{report['rows_removed_total']:,} removed")
    kpi(c[2], "Duplicates", f"{report['duplicates_removed'] + report['duplicate_timestamps_removed']:,}", "removed")
    kpi(c[3], "Invalid / Outliers", f"{report['total_impossible_values'] + outliers:,}",
        f"{report['total_impossible_values']:,} sentinels + {outliers:,} spikes")
    kpi(c[4], "Missing Imputed", f"{report['missing_before_imputation']:,}", "-> 0 after cleaning")

    st.write("")

    view = st.radio(
        "View",
        ["Missing values", "Distributions", "Boxplots", "Single feature", "Sensor stream", "Summary table"],
        horizontal=True,
        label_visibility="collapsed",
        key="ba_view",
    )

    with panel("ba", f"Before vs After - {view}"):

        if view == "Missing values":
            show_fig(eda.plot_missing_before_after(raw, clean), "ba_missing")
            st.caption(
                "sensor_15 is 100% empty in the source and is dropped. Gaps up to "
                f"{30} min are interpolated; longer gaps use the median of the same machine_status."
            )

        elif view in ("Distributions", "Boxplots"):
            cols = st.multiselect("Sensors", SENSOR_COLS, default=DEFAULT_PLOT_SENSORS, key="ba_cols",
                                  format_func=sensor_label)

            if not cols:
                st.info("Select at least one sensor.")
            elif view == "Distributions":
                log = st.toggle("Log-scale counts (makes rare spikes visible)", value=True, key="ba_log")
                show_fig(eda.plot_distributions_before_after(raw, clean, cols, log=log), "ba_distributions")
            else:
                zoom = st.toggle("Zoom to valid range (hides -999 sentinels)", value=True, key="ba_zoom")
                show_fig(eda.plot_boxplots_before_after(raw, clean, cols, zoom=zoom), "ba_boxplots")

        elif view == "Single feature":
            col = st.selectbox("Sensor", SENSOR_COLS, key="ba_single", format_func=sensor_label)
            show_fig(eda.plot_before_after(raw, clean, col), f"ba_{col}")

        elif view == "Sensor stream":
            sensor = st.selectbox("Sensor", SENSOR_COLS, key="ba_stream_sensor", format_func=sensor_label)
            max_start = max(len(clean) - 200, 0)
            start = st.slider("Window start (row)", 0, max_start, 0, 500, key="ba_stream_start") if max_start else 0
            n = st.slider("Samples", 200, 3000, 1000, 100, key="ba_stream_n")
            show_fig(eda.plot_stream_before_after(raw, clean, sensor, start, n), "ba_stream")

        else:
            rows = []

            for col in SENSOR_COLS:
                b = pd.to_numeric(raw[col], errors="coerce")
                a = clean[col]
                rows.append({
                    "column": col,
                    "missing before": int(b.isna().sum()),
                    "missing after": int(a.isna().sum()),
                    "min before": b.min(), "min after": a.min(),
                    "max before": b.max(), "max after": a.max(),
                    "mean before": b.mean(), "mean after": a.mean(),
                })

            st.dataframe(pd.DataFrame(rows).round(2), hide_index=True)

# ============================================================
# PAGE 3 - RISK INFERENCE
# ============================================================

elif page == "Risk Inference":

    with st.spinner("Training baseline model (first visit only)..."):
        try:
            bundle = get_model(final, scale_stats, f"{len(final)}-{inject}-{level}")
        except Exception as exc:
            st.error(f"Model training failed: {exc}")
            st.stop()

    r = bundle["ranges"]
    names = list(bundle["presets"])

    with panel("risk", "Real-Time Pump Failure Risk Inference (ML Engine)"):

        preset = st.selectbox("Start from a historical reading", names, key="risk_preset")
        base = bundle["presets"][preset]
        p_idx = names.index(preset)

        st.caption(
            "All 51 sensors start from the chosen reading. Adjust the 12 sensors most linked "
            "to failure below; the remaining sensors keep their reading."
        )

        with st.form("risk_form"):
            cols = st.columns(3)
            vals = dict(base)

            for i, key in enumerate(bundle["top_sensors"]):
                lo, hi = r[key]
                vals[key] = cols[i % 3].number_input(
                    sensor_label(key),
                    value=float(round(base[key], 3)),
                    step=float((hi - lo) / 100 or 1.0),
                    format="%.3f",
                    help=f"Training range: {lo:.2f} to {hi:.2f}",
                    key=f"risk_{p_idx}_{key}",
                )

            submitted = st.form_submit_button("Run Pump Risk Diagnosis")

        if submitted:
            st.session_state["risk"] = predict_risk(bundle, vals)

        out = st.session_state.get("risk")

        if out:
            p = out["probability"]
            base_rate = bundle["metrics"]["base_rate"]

            if p < 0.15:
                css, title = "ok", "PUMP NORMAL / HEALTHY"
            elif p < 0.30:
                css, title = "warn", "ELEVATED RISK - SCHEDULE INSPECTION"
            else:
                css, title = "bad", "HIGH FAILURE RISK - ACT NOW"

            st.markdown(
                f'<div class="result {css}"><div class="result-title">{title} '
                f'({p * 100:.0f}% Failure Probability)</div>'
                f'<div class="result-sub">Deviation from healthy: {out["deviation_mean_abs"]:.2f} σ (avg) | '
                f'Sensors beyond 3σ: {out["n_sensors_beyond_3sd"]} | '
                f'Sensors reading 0: {out["n_zero_sensors"]}</div></div>',
                unsafe_allow_html=True,
            )

            horizon = f"within the next {HORIZON_MIN // 60} h" if TARGET_MODE == "early_warning" else "now"

            st.caption(
                f"Probability that the pump is broken {horizon}. "
                f"Average failure-window rate in the held-out test period: {base_rate * 100:.1f}%."
            )

    m = bundle["metrics"]

    with st.expander("About this model"):
        st.write(
            f"HistGradientBoosting baseline. The pump has {m['failure_events']} failure events, so the "
            f"split is by event: trained on the first {m['train_rows']:,} records, tested on the last "
            f"{m['test_rows']:,} (from {m['test_start']}, {m['test_events']} failure events)."
        )
        c = st.columns(3)
        kpi(c[0], "ROC-AUC", f"{m['roc_auc']:.2f}", "0.50 = coin flip")
        kpi(c[1], "PR-AUC", f"{m['pr_auc']:.2f}", f"baseline {m['base_rate']:.2f}")
        kpi(c[2], "Features", f"{len(bundle['features'])}", "sensors + deviation features")
        st.write(
            "This is a single-reading baseline - it does not see trends over time, and with only a few "
            "failure events the test score is a rough indication, not a guarantee. `machine_status` is "
            "excluded on purpose (it defines the target), and RECOVERING rows are left out of training. "
            "Rolling/lag features and cross-validation by event belong in Phase 2."
        )

# ============================================================
# PAGE 4 - DATA & REPORT
# ============================================================

else:

    with panel("report", "Cleaning Report"):
        summary = {k: v for k, v in report.items() if not isinstance(v, (dict, list))}
        st.dataframe(pd.DataFrame({"metric": summary.keys(), "value": [str(v) for v in summary.values()]}),
                     hide_index=True)

        with st.expander("Full report (JSON)"):
            st.json(json.loads(json.dumps(report, default=str)))

        st.download_button("Download report (JSON)", json.dumps(report, indent=2, default=str),
                           file_name="cleaning_report.json", mime="application/json", key="dl_report")

    with panel("preview", "Cleaned + Engineered Data"):
        st.caption(f"{final.shape[0]:,} rows x {final.shape[1]} columns (first 500 shown)")
        st.dataframe(final.head(500), hide_index=True)

        c1, c2 = st.columns(2)

        c1.download_button("Download 1,000-row sample (CSV)", final.head(1000).to_csv(index=False),
                           file_name="clean_features_sample.csv", mime="text/csv", key="dl_sample")

        if c2.button("Save full dataset to data/ (CSV + SQLite)", key="save_db"):
            with st.spinner("Writing data/processed/clean_features.csv and data/maintenance.db ..."):
                load_to_db(final)
            st.success("Saved to data/processed/clean_features.csv and data/maintenance.db")

    with panel("quarantine", "Quarantined Rows (failed Pydantic validation)"):
        if rejected.empty:
            st.success("No rows were quarantined - every cleaned row passed schema validation.")
        else:
            st.dataframe(rejected, hide_index=True)