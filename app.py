"""
Pump Failure Prediction Dashboard - Streamlit app.

Run locally:   streamlit run app.py
Deploy:        Streamlit Community Cloud (main file = app.py, add KAGGLE_API_TOKEN to Secrets)

The ETL pipeline in src/ is used unchanged. The dataset is read from
data/raw/sensor.csv and downloaded from Kaggle on the first run if missing.
"""

import io
import json
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# must be the first Streamlit command
st.set_page_config(
    page_title="Pump Failure Prediction Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Kaggle credentials: .env (local)  or  st.secrets (Streamlit Cloud)
# ------------------------------------------------------------
load_dotenv()

for _key in ("KAGGLE_API_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY"):
    try:
        if not os.environ.get(_key) and _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
    except Exception:
        pass  # no secrets file -> fine, .env is used

from src import eda, theme  # noqa: E402
from src.config import (  # noqa: E402
    DEFAULT_PLOT_SENSORS,
    HORIZON_MIN,
    SENSOR_COLS,
    SENSOR_LABELS,
    STATUS_COL,
    TARGET,
    TIME_COL,
)
from src.extract import ensure_dataset  # noqa: E402
from src.model import predict_risk, train_risk_model  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402

TITLE = "Pump Failure Prediction Dashboard"
HORIZON_H = HORIZON_MIN // 60


def lab(c: str) -> str:
    return SENSOR_LABELS.get(c, c)


def chart(fig, name: str):
    """Show a matplotlib figure as an image + 'Download PNG' button (frees the figure)."""

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)

    png = buf.getvalue()

    st.image(png)
    st.download_button("Download PNG", png, f"{name}.png", "image/png", key=f"dl_{name}")


# ============================================================
# CACHED HEAVY WORK
# ============================================================

@st.cache_resource(show_spinner=False, max_entries=1)
def get_result(inject: bool, level: float):
    path = ensure_dataset()

    return run_pipeline(
        source=str(path),
        save=False,
        inject_noise=inject,
        noise_level=level,
        make_figs=False,
    )


@st.cache_resource(show_spinner=False, max_entries=1)
def get_bundle(inject: bool, level: float, _res):
    return train_risk_model(_res["final"], _res["scale_stats"])


# ============================================================
# THEME + SIDEBAR
# ============================================================

THEME = theme.resolve(st.session_state.get("theme_name", theme.DEFAULT_THEME))

eda.set_theme(THEME)
theme.inject(THEME)

# little confirmation when the theme is switched
if st.session_state.get("_theme_seen", THEME) != THEME:
    st.toast(f"Theme: {theme.LABELS[THEME]}", icon="🎨")

st.session_state["_theme_seen"] = THEME

if "params" not in st.session_state:
    st.session_state.params = {"inject": False, "level": 1.0}

with st.sidebar:
    theme.sidebar_brand(TITLE)

    st.markdown('<div class="pf-side-h">Appearance</div>', unsafe_allow_html=True)

    st.selectbox(
        "Theme",
        theme.THEME_ORDER,
        index=theme.THEME_ORDER.index(THEME),
        format_func=theme.LABELS.get,
        key="theme_name",
        label_visibility="collapsed",
    )

    theme.swatches(THEME)

    st.divider()

    st.markdown('<div class="pf-side-h">Data source</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pf-side-p">Backend file: <code>data/raw/sensor.csv</code><br>'
        "(pump sensor data, loaded automatically)<br><br>"
        f"Target: BROKEN within the next {HORIZON_H} h</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown('<div class="pf-side-h">Cleaning demo</div>', unsafe_allow_html=True)

    inject = st.toggle(
        "Simulate dirty data",
        value=st.session_state.params["inject"],
        help="DEMO ONLY: corrupts a copy of the raw data (dropouts, spikes, -999 sentinels, "
        "duplicates, messy status text) so the cleaning step has visible work to do.",
    )

    level = st.slider(
        "Noise intensity", 0.5, 3.0, float(st.session_state.params["level"]), 0.1, disabled=not inject
    )

    if st.button("Re-run pipeline"):
        st.session_state.params = {"inject": bool(inject), "level": float(level)}

params = st.session_state.params


# ============================================================
# RUN THE PIPELINE
# ============================================================

try:
    with st.spinner("Running ETL pipeline: extract → clean → validate → features (first run takes a minute)…"):
        res = get_result(params["inject"], params["level"])
except Exception as exc:
    st.error(f"Pipeline failed: {exc}")
    st.stop()

final, clean, raw, report = res["final"], res["clean"], res["raw"], res["report"]
events = list(final.loc[final[STATUS_COL] == "BROKEN", TIME_COL])


# ============================================================
# HEADER + NAVIGATION
# ============================================================

theme.banner(
    TITLE,
    f"{len(final):,} cleaned records",
    subtitle=f"Early-warning model: predicts a BROKEN pump up to {HORIZON_H} h ahead",
)

PAGES = ["Dashboard", "Before vs After", "Risk Inference", "Data & Report"]

page = st.radio("Page", PAGES, horizontal=True, label_visibility="collapsed", key="nav")

theme.flow_bar(PAGES.index(page), PAGES)


# ============================================================
# PAGES
# ============================================================

def page_dashboard():
    theme.kpi_row([
        ("Records Loaded", f"{len(final):,}", f"{len(raw):,} raw rows in"),
        ("Quarantined", f"{int(report['pydantic_rejected_rows']):,}", "failed schema validation"),
        ("Failure-Window Rate", f"{final[TARGET].mean() * 100:.2f}%", f"{int(final[TARGET].sum()):,} records flagged"),
        ("Breakdown Events", f"{len(events)}", "machine_status = BROKEN"),
        ("Active Sensors", f"{len(SENSOR_COLS)}", f"{', '.join(report['dead_sensors_dropped']) or 'no sensor'} dropped (empty)"),
    ])

    left, right = st.columns(2)

    # ---------------- telemetry ----------------
    with left:
        with st.container(key="panel_telemetry"):
            theme.title("Live Sensor Telemetry Trend")

            default = SENSOR_COLS.index("sensor_22") if "sensor_22" in SENSOR_COLS else 0

            sensor = st.selectbox("Sensor", SENSOR_COLS, index=default, format_func=lab, key="tel_sensor")

            view = st.radio("View", ["Latest samples", "Around a failure"], horizontal=True,
                            label_visibility="collapsed", key="tel_view")

            c1, c2 = st.columns(2)

            window = c1.slider("Rolling window (min)", 1, 240, 30, key="tel_window")

            if view == "Latest samples":
                n = c2.slider("Samples", 100, 50000, 3000, 100, key="tel_n")
                chart(eda.plot_telemetry(final, sensor, window=window, n=n), "telemetry")

            elif not events:
                st.info("No failure events in this run.")

            else:
                ev = c2.selectbox(
                    "Failure event",
                    range(len(events)),
                    format_func=lambda i: f"#{i + 1} - {events[i]:%Y-%m-%d %H:%M}",
                    key="tel_event",
                )
                hours = st.slider("± hours around the failure", 1, 336, 48, key="tel_hours")
                chart(eda.plot_telemetry(final, sensor, window=window, center=events[ev], hours=hours), "telemetry")

    # ---------------- breakdown ----------------
    with right:
        with st.container(key="panel_breakdown"):
            theme.title("Breakdown Analysis")

            by = st.selectbox("Group failure-window records by", [STATUS_COL, "month", "week", "weekday", "hour"], key="by")

            chart(eda.plot_failure_breakdown(final, by), "breakdown")

    left, right = st.columns(2)

    # ---------------- raw vs validated stream ----------------
    with left:
        with st.container(key="panel_signal"):
            theme.title("Signal Conditioning: Raw Outliers vs Validated Stream")
            st.caption("Uses the sensor chosen in the telemetry panel.")

            n = st.slider("Samples", 50, 5000, 1000, 50, key="sig_n")

            top = max(len(clean) - n, 1)

            start = st.slider("Window start (row)", 0, top, 0, max(1, top // 200), key="sig_start")

            chart(eda.plot_stream_before_after(raw, clean, sensor, start=start, n=n), "signal")

    # ---------------- correlation ----------------
    with right:
        with st.container(key="panel_corr"):
            theme.title("Correlation Matrix (Sensors Most Linked to Failure)")

            cols = res["top_sensors"] + ["deviation_mean_abs", TARGET]

            chart(eda.plot_correlation(final, "Correlation Matrix", cols), "correlation")


def page_ba():
    impossible = int(report["total_impossible_values"])
    outliers = int(report["total_outliers_replaced"])
    dups = int(report["duplicates_removed"] + report["duplicate_timestamps_removed"])

    theme.kpi_row([
        ("Rows In", f"{int(report['rows_in']):,}", "raw"),
        ("Rows Out", f"{int(report['rows_out']):,}", f"{int(report['rows_removed_total']):,} removed"),
        ("Duplicates", f"{dups:,}", "removed"),
        ("Invalid / Outliers", f"{impossible + outliers:,}", f"{impossible:,} sentinels + {outliers:,} spikes"),
        ("Missing Imputed", f"{int(report['missing_before_imputation']):,}", f"-> {int(report['missing_after_cleaning']):,} after cleaning"),
    ])

    tab = st.radio(
        "View",
        ["Missing values", "Distributions", "Boxplots", "Single feature", "Sensor stream", "Summary table"],
        horizontal=True, label_visibility="collapsed", key="ba_tab",
    )

    with st.container(key="panel_ba"):
        theme.title(f"Before vs After - {tab}")

        if tab == "Missing values":
            chart(eda.plot_missing_before_after(raw, clean), "ba_missing")

        elif tab == "Distributions":
            cols = st.multiselect("Sensors", SENSOR_COLS, default=DEFAULT_PLOT_SENSORS, format_func=lab, key="dist_cols")
            log = st.toggle("Log-scale counts (makes rare spikes visible)", value=True, key="dist_log")

            if cols:
                chart(eda.plot_distributions_before_after(raw, clean, cols, log=log), "ba_distributions")
            else:
                st.info("Pick at least one sensor.")

        elif tab == "Boxplots":
            cols = st.multiselect("Sensors", SENSOR_COLS, default=DEFAULT_PLOT_SENSORS, format_func=lab, key="box_cols")
            zoom = st.toggle("Zoom to valid range (hides -999 sentinels)", value=True, key="box_zoom")

            if cols:
                chart(eda.plot_boxplots_before_after(raw, clean, cols, zoom=zoom), "ba_boxplots")
            else:
                st.info("Pick at least one sensor.")

        elif tab == "Single feature":
            sensor = st.selectbox("Sensor", SENSOR_COLS, format_func=lab, key="single_sensor")
            chart(eda.plot_before_after(raw, clean, sensor), "ba_single")

        elif tab == "Sensor stream":
            sensor = st.selectbox("Sensor", SENSOR_COLS, format_func=lab, key="stream_sensor")

            n = st.slider("Samples", 50, 5000, 1000, 50, key="stream_n")

            top = max(len(clean) - n, 1)

            start = st.slider("Window start (row)", 0, top, min(top, 87500), max(1, top // 200), key="stream_start")

            chart(eda.plot_stream_before_after(raw, clean, sensor, start=start, n=n), "ba_stream")

        else:
            rows = []

            for c in SENSOR_COLS:
                b = pd.to_numeric(raw[c], errors="coerce")
                a = clean[c]

                rows.append({
                    "column": c,
                    "missing before": int(b.isna().sum()), "missing after": int(a.isna().sum()),
                    "min before": b.min(), "min after": a.min(),
                    "max before": b.max(), "max after": a.max(),
                    "mean before": b.mean(), "mean after": a.mean(),
                })

            st.dataframe(pd.DataFrame(rows).round(2), hide_index=True, height=420)


def page_risk():
    try:
        with st.spinner("Training the baseline model…"):
            bundle = get_bundle(params["inject"], params["level"], res)
    except Exception as exc:
        st.error(f"Model training failed: {exc}")
        return

    m = bundle["metrics"]

    with st.container(key="panel_risk"):
        theme.title("Real-Time Pump Failure Risk Inference (ML Engine)")

        preset = st.selectbox("Start from a historical reading", list(bundle["presets"]), key="preset")
        base = bundle["presets"][preset]

        st.caption(
            f"All {len(SENSOR_COLS)} sensors start from the chosen reading. Adjust the {len(bundle['top_sensors'])} "
            "sensors most linked to failure below; the remaining sensors keep their reading."
        )

        readings = dict(base)

        with st.container(key="inner_inputs"):
            cols = st.columns(3)

            for i, c in enumerate(bundle["top_sensors"]):
                lo, hi = bundle["ranges"][c]

                step = float((hi - lo) / 200) if hi > lo else 1.0

                readings[c] = cols[i % 3].number_input(
                    lab(c),
                    value=float(base[c]),
                    step=step,
                    format="%.3f",
                    help=f"Observed range: {lo:.2f} to {hi:.2f}",
                    key=f"num|{preset}|{c}",
                )

            run = st.button("Run Pump Risk Diagnosis")

        if run or "risk_out" not in st.session_state:
            st.session_state.risk_out = predict_risk(bundle, readings)

        out = st.session_state.risk_out

        p = out["probability"]
        pct = f"{p * 100:.0f}%" if p >= 0.01 else f"{p * 100:.1f}%"

        if p < 0.2:
            level_name, heading = "ok", f"PUMP NORMAL / HEALTHY ({pct} Failure Probability)"
        elif p < 0.5:
            level_name, heading = "warn", f"ELEVATED RISK ({pct} Failure Probability)"
        else:
            level_name, heading = "bad", f"HIGH FAILURE RISK ({pct} Failure Probability)"

        theme.result_box(
            level_name,
            heading,
            f"Deviation from healthy: {out['deviation_mean_abs']:.2f} σ (avg) | "
            f"Sensors beyond 3σ: {out['n_sensors_beyond_3sd']} | Sensors reading 0: {out['n_zero_sensors']}",
            probability=p,
        )

        st.caption(
            f"Probability that the pump is broken within the next {HORIZON_H} h. "
            f"Average failure-window rate in the held-out test period: {m['base_rate']:.1%}."
        )

    with st.expander("About this model", expanded=True):
        theme.md(
            f"HistGradientBoosting baseline. The pump has {m['failure_events']} failure events, so the split is "
            f"by event: trained on the first {m['train_rows']:,} records, tested on the last {m['test_rows']:,} "
            f"(from {m['test_start']}, {m['test_events']} failure events)."
        )

        theme.kpi_row([
            ("ROC-AUC", f"{m['roc_auc']:.2f}", "0.50 = coin flip"),
            ("PR-AUC", f"{m['pr_auc']:.2f}", f"baseline {m['base_rate']:.2f}"),
            ("Features", f"{len(bundle['features'])}", "sensors + deviation features"),
        ])

        theme.md(
            "This is a single-reading baseline - it does not see trends over time, and with only a few failure "
            "events the test score is a rough indication, not a guarantee. `machine_status` is excluded on purpose "
            "(it defines the target), and RECOVERING rows are left out of training. Rolling/lag features and "
            "cross-validation by event belong in Phase 2."
        )


def page_data():
    with st.container(key="panel_report"):
        theme.title("Cleaning Report")

        summary = pd.DataFrame(
            [{"metric": k, "value": str(v)} for k, v in report.items() if not isinstance(v, (dict, list))]
        )

        st.dataframe(summary, hide_index=True, height=360)

        with st.expander("Full report (JSON)"):
            st.json(json.loads(json.dumps(report, default=str)))

        st.download_button(
            "Download report (JSON)",
            json.dumps(report, indent=2, default=str),
            "cleaning_report.json",
            "application/json",
            key="dl_report",
        )

    with st.container(key="panel_data"):
        theme.title("Cleaned + Engineered Data")
        st.caption(f"{final.shape[0]:,} rows x {final.shape[1]} columns (first 500 shown)")

        head = final.head(500).copy()
        head[TIME_COL] = head[TIME_COL].astype(str)

        st.dataframe(head.round(4), hide_index=True, height=420)

        st.download_button(
            "Download sample (CSV)",
            final.head(1000).to_csv(index=False),
            "clean_features_sample.csv",
            "text/csv",
            key="dl_sample",
        )

    rejected = res["rejected"]
    total = int(rejected.attrs.get("total_rejected", len(rejected)))

    if total:
        with st.container(key="panel_rejected"):
            theme.title("Quarantined Rows")
            st.caption(f"{total:,} rows failed schema validation (first {len(rejected):,} shown).")
            st.dataframe(rejected, hide_index=True)


{
    "Dashboard": page_dashboard,
    "Before vs After": page_ba,
    "Risk Inference": page_risk,
    "Data & Report": page_data,
}[page]()