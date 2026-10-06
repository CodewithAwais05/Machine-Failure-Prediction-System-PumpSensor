import math

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import (
    DEFAULT_PLOT_SENSORS,
    SENSOR_COLS,
    SENSOR_LABELS,
    STATUS_COL,
    TARGET,
    TIME_COL,
    PLOTS_DIR,
)


# ============================================================
# THEME  (maroon brand palette, light + dark)
# ============================================================

THEMES = {
    "light": {
        "bg": "#FFFFFF",
        "fg": "#1B1B22",
        "muted": "#5E6370",
        "grid": "#E6E8EC",
        "spine": "#C9CDD4",
        "before": "#A02C4D",     # raw / before
        "after": "#2D3142",      # cleaned / after
        "series": ["#C05A7C", "#6B1E33", "#2D3142", "#7F8489", "#D393B4"],
        "warn": "#F3B74F",
        "recover": "#9AA0A6",
        "cmap": "coolwarm",
    },
    "dark": {
        "bg": "#1F1B25",
        "fg": "#ECE8F0",
        "muted": "#A39DAE",
        "grid": "#342E3C",
        "spine": "#4A4354",
        "before": "#E58BAA",
        "after": "#8FA3D6",
        "series": ["#E58BAA", "#B0476A", "#8FA3D6", "#9AA0A6", "#F0B6CC"],
        "warn": "#C9962E",
        "recover": "#6E7480",
        "cmap": "coolwarm",
    },
}

_state = {"mode": "light"}


def set_theme(mode="light"):
    """Switch every following plot to the light or dark palette."""

    mode = "dark" if str(mode).lower() == "dark" else "light"
    _state["mode"] = mode
    t = THEMES[mode]

    plt.rcParams.update({
        "figure.facecolor": t["bg"],
        "savefig.facecolor": t["bg"],
        "axes.facecolor": t["bg"],
        "axes.edgecolor": t["spine"],
        "axes.labelcolor": t["fg"],
        "axes.titlecolor": t["fg"],
        "text.color": t["fg"],
        "xtick.color": t["muted"],
        "ytick.color": t["muted"],
        "grid.color": t["grid"],
        "axes.grid": True,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.facecolor": t["bg"],
        "legend.edgecolor": t["spine"],
        "font.size": 9,
    })

    return t


def pal():
    return THEMES[_state["mode"]]


set_theme("light")


# ============================================================
# HELPERS
# ============================================================

def _save(fig, name):

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    fig.savefig(PLOTS_DIR / f"{name}.png", dpi=120, bbox_inches="tight")


def _finish(fig, name):

    fig.tight_layout()

    if name:
        _save(fig, name)

    return fig


def _num(df, col):
    """Numeric values of a column; anything unreadable becomes NaN and is dropped."""

    return pd.to_numeric(df[col], errors="coerce").dropna()


def _missing_pct(df):
    """% missing per column; blank strings count as missing too."""

    out = {}

    for col in df.columns:
        s = df[col]
        miss = s.isna()

        if not pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_datetime64_any_dtype(s):
            miss = miss | s.astype("string").str.strip().eq("").fillna(False)

        out[col] = float(miss.mean() * 100)

    return pd.Series(out)


def _grid(n, ncols, cell=(4.6, 3.4)):

    nrows = max(1, math.ceil(n / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(cell[0] * ncols, cell[1] * nrows))

    axes = np.atleast_1d(axes).flatten()

    for ax in axes[n:]:
        ax.axis("off")

    return fig, axes


def _label(col):
    return SENSOR_LABELS.get(col, col)


def _pick_cols(df, cols):
    return [c for c in (cols or DEFAULT_PLOT_SENSORS) if c in df.columns]


def _runs(mask, times):
    """Contiguous True stretches of a boolean array -> [(start_time, end_time), ...]"""

    m = np.asarray(mask, dtype=bool)

    if not m.any():
        return []

    d = np.diff(np.concatenate(([0], m.astype(int), [0])))

    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1) - 1

    t = np.asarray(times)

    return [(pd.Timestamp(t[s]), pd.Timestamp(t[e])) for s, e in zip(starts, ends)]


def top_correlated(df, k=14):
    """Sensors whose readings are most correlated (absolute) with the failure flag."""

    cols = [c for c in SENSOR_COLS if c in df.columns]

    corr = df[cols].corrwith(df[TARGET]).abs().fillna(0)

    return list(corr.sort_values(ascending=False).head(k).index)


# ============================================================
# SINGLE-DATASET PLOTS
# ============================================================

def plot_missing(df, title, name=None):

    t = pal()

    counts = df.isna().sum()

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.bar(counts.index, counts.values, color=t["series"][0])

    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("Missing values")

    plt.setp(ax.get_xticklabels(), rotation=70, ha="right", fontsize=7)

    return _finish(fig, name)


def plot_distributions(df, title, name=None, cols=None):

    t = pal()

    cols = _pick_cols(df, cols)

    if not cols:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No numerical columns available", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, axes = _grid(len(cols), 3, (4.7, 3.4))

    for ax, col in zip(axes, cols):
        ax.hist(_num(df, col), bins=30, color=t["series"][0], edgecolor=t["bg"])
        ax.set_title(_label(col), fontsize=10)
        ax.set_ylabel("Frequency")

    fig.suptitle(title, fontsize=14, fontweight="bold")

    fig.tight_layout()

    if name:
        _save(fig, name)

    return fig


def plot_boxplots(df, title, name=None, cols=None):

    t = pal()

    cols = _pick_cols(df, cols)

    fig, axes = _grid(len(cols), 4, (3.6, 3.6))

    for ax, col in zip(axes, cols):
        ax.boxplot(
            _num(df, col),
            patch_artist=True,
            boxprops=dict(facecolor=t["series"][0], color=t["fg"]),
            medianprops=dict(color=t["fg"]),
            whiskerprops=dict(color=t["muted"]),
            capprops=dict(color=t["muted"]),
            flierprops=dict(marker=".", markersize=2, markeredgecolor=t["muted"]),
        )
        ax.set_title(_label(col), fontsize=9)
        ax.set_xticks([])

    fig.suptitle(title, fontsize=14, fontweight="bold")

    fig.tight_layout()

    if name:
        _save(fig, name)

    return fig


def plot_correlation(df, title, cols, name=None):

    t = pal()

    available = [c for c in cols if c in df.columns]

    if not available:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No numerical columns available", ha="center", va="center")
        ax.axis("off")
        return fig

    corr = df[available].apply(pd.to_numeric, errors="coerce").corr()

    n = len(available)

    side = min(max(6, 0.55 * n + 3), 12)

    fig, ax = plt.subplots(figsize=(side, side * 0.85))

    image = ax.imshow(corr, vmin=-1, vmax=1, cmap=t["cmap"])

    ax.grid(False)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(available, rotation=60, ha="right", fontsize=8)
    ax.set_yticklabels(available, fontsize=8)

    if n <= 18:
        for i in range(n):
            for j in range(n):
                value = corr.iloc[i, j]
                if np.isnan(value):
                    continue
                ax.text(j, i, f"{value:.2f}", ha="center", va="center",
                        fontsize=7 if n > 10 else 8, color="#111111")

    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(colors=t["muted"])

    ax.set_title(title, fontweight="bold")

    for spine in ax.spines.values():
        spine.set_visible(False)

    return _finish(fig, name)


def plot_class_balance(df, name=None):

    t = pal()

    counts = df[TARGET].value_counts().reindex([0, 1], fill_value=0)

    total = max(int(counts.sum()), 1)

    fig, ax = plt.subplots(figsize=(5, 4))

    ax.bar(["No failure", "Failure window"], counts.values, color=[t["after"], t["series"][1]])

    for i, value in enumerate(counts.values):
        ax.text(i, value, f"{value:,}\n({value / total:.1%})", ha="center", va="bottom", fontsize=9)

    ax.set_ylim(0, max(counts.max(), 1) * 1.18)
    ax.set_ylabel("Number of records")
    ax.set_title("Class Balance", fontweight="bold")

    return _finish(fig, name)


def plot_status_distribution(df, name=None):
    """Rows per machine_status (log scale: BROKEN is only a handful of rows)."""

    t = pal()

    counts = df[STATUS_COL].value_counts()

    fig, ax = plt.subplots(figsize=(7, 4))

    colors = [t["series"][i % len(t["series"])] for i in range(len(counts))]

    ax.bar(counts.index.astype(str), counts.values, color=colors)

    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=9)

    ax.set_yscale("log")
    ax.set_ylabel("Records (log scale)")
    ax.set_title("Machine Status Distribution", fontweight="bold")

    return _finish(fig, name)


def _group_key(df, by):

    ts = pd.to_datetime(df[TIME_COL])

    if by == "month":
        return ts.dt.to_period("M").astype(str)

    if by == "week":
        return ts.dt.to_period("W").dt.start_time.dt.strftime("%m-%d")

    if by == "weekday":
        return ts.dt.day_name()

    if by == "hour":
        return ts.dt.hour

    return df[by]


def plot_failure_breakdown(df, by="machine_status", name=None):
    """Records inside the failure window (breakdown_flag = 1), grouped by a category or time unit."""

    t = pal()

    key = _group_key(df, by)

    counts = df.loc[df[TARGET] == 1].groupby(key[df[TARGET] == 1]).size()

    if by in ("month", "week", "hour"):
        counts = counts.sort_index()
    else:
        counts = counts.sort_values(ascending=False).head(12)

    fig, ax = plt.subplots(figsize=(7, 4.2))

    if counts.empty:
        ax.text(0.5, 0.5, "No failure records", ha="center", va="center")
        ax.axis("off")
        return fig

    colors = [t["series"][i % len(t["series"])] for i in range(len(counts))]

    ax.bar(counts.index.astype(str), counts.values, color=colors)

    if len(counts) <= 16:
        for i, v in enumerate(counts.values):
            ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=8)

    ax.set_ylim(0, max(counts.max() * 1.15, 1))
    ax.set_ylabel("Records in failure window")
    ax.set_xlabel(by)
    ax.set_title(f"Failure-window records by {by}", fontweight="bold")

    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")

    return _finish(fig, name)


def plot_feature_vs_failure(df, col, name=None):

    t = pal()

    if col not in df.columns:
        raise ValueError(f"Feature '{col}' does not exist.")

    fig, ax = plt.subplots(figsize=(7, 4))

    for label, text, color in [(0, "No failure", t["after"]), (1, "Failure window", t["series"][1])]:
        values = _num(df.loc[df[TARGET] == label], col)
        ax.hist(values, bins=30, alpha=0.6, label=text, density=True, color=color)

    ax.set_title(f"{_label(col)} by Failure Status", fontweight="bold")
    ax.set_xlabel(col)
    ax.set_ylabel("Density")
    ax.legend()

    return _finish(fig, name)


def plot_telemetry(df, col, window=30, n=3000, center=None, hours=48, name=None):
    """
    Sensor trend with rolling mean.
    * center=None  -> the latest n samples
    * center=<ts>  -> +/- `hours` around a timestamp (e.g. a failure)
    Shading: amber = failure window (warning), grey = RECOVERING, x = BROKEN.
    """

    t = pal()

    if center is not None:
        c = pd.Timestamp(center)
        half = pd.Timedelta(hours=hours)
        sel = df[(df[TIME_COL] >= c - half) & (df[TIME_COL] <= c + half)]
    else:
        sel = df.tail(n)

    fig, ax = plt.subplots(figsize=(7.5, 4))

    if sel.empty:
        ax.text(0.5, 0.5, "No data for this selection", ha="center", va="center")
        ax.axis("off")
        return fig

    x = sel[TIME_COL]
    y = pd.to_numeric(sel[col], errors="coerce")

    times = x.to_numpy()
    status = sel[STATUS_COL].to_numpy()

    warn = (sel[TARGET].to_numpy() == 1) & (status == "NORMAL")

    for i, (s, e) in enumerate(_runs(warn, times)):
        ax.axvspan(s, e, color=t["warn"], alpha=0.25, lw=0, label="Failure window" if i == 0 else None)

    for i, (s, e) in enumerate(_runs(status == "RECOVERING", times)):
        ax.axvspan(s, e, color=t["recover"], alpha=0.25, lw=0, label="Recovering" if i == 0 else None)

    ax.plot(x, y, color=t["series"][0], alpha=0.55, linewidth=1, label=_label(col))

    if window > 1:
        ax.plot(x, y.rolling(window, min_periods=1).mean(),
                color=t["after"], linewidth=1.8, label=f"{window}-sample mean")

    bd = sel[sel[STATUS_COL] == "BROKEN"]

    if len(bd):
        ax.scatter(bd[TIME_COL], pd.to_numeric(bd[col], errors="coerce"),
                   marker="x", color=t["series"][1], s=60, zorder=3, label="Breakdown")

    ax.set_ylabel(_label(col))
    ax.set_title(f"{_label(col)} · {x.min():%Y-%m-%d %H:%M} to {x.max():%Y-%m-%d %H:%M}", fontsize=10)
    ax.legend(loc="upper left", ncols=3, fontsize=7)

    fig.autofmt_xdate()

    return _finish(fig, name)


# ============================================================
# BEFORE vs AFTER PLOTS
# ============================================================

def plot_before_after(before, after, col):
    """Histogram of ONE column: raw vs cleaned, same x-axis."""

    t = pal()

    if col not in before.columns:
        raise ValueError(f"'{col}' does not exist in raw data.")

    if col not in after.columns:
        raise ValueError(f"'{col}' does not exist in cleaned data.")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharex=True)

    axes[0].hist(_num(before, col), bins=40, color=t["before"], edgecolor=t["bg"])
    axes[0].set_title(f"{col}: BEFORE CLEANING", fontweight="bold")

    axes[1].hist(_num(after, col), bins=40, color=t["after"], edgecolor=t["bg"])
    axes[1].set_title(f"{col}: AFTER CLEANING", fontweight="bold")

    axes[0].set_ylabel("Frequency")

    return _finish(fig, None)


def plot_missing_before_after(before, after, title="Missing Values: Before vs After"):

    t = pal()

    common = list(before.columns)

    b = _missing_pct(before[common])

    in_after = [c for c in common if c in after.columns]

    # sensors removed during cleaning (e.g. the empty sensor_15) count as 0 % after
    a = _missing_pct(after[in_after]).reindex(common).fillna(0.0)

    keep = [c for c in common if b[c] > 0 or a[c] > 0]

    if not keep:
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.text(0.5, 0.5, "No missing or blank values before or after cleaning",
                ha="center", va="center")
        ax.axis("off")
        return fig

    b, a = b[keep], a[keep]

    names = [c if c in after.columns else f"{c} (dropped)" for c in keep]

    y = np.arange(len(keep))

    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.45 * len(keep) + 1.5)))

    ax.barh(y - 0.2, b.values, height=0.38, color=t["before"], label="Before")
    ax.barh(y + 0.2, a.values, height=0.38, color=t["after"], label="After")

    for i, (vb, va) in enumerate(zip(b.values, a.values)):
        ax.text(vb, i - 0.2, f" {vb:.2f}%", va="center", fontsize=7)
        ax.text(va, i + 0.2, f" {va:.2f}%", va="center", fontsize=7)

    ax.set_xscale("symlog", linthresh=0.1)
    ax.set_xlim(left=0)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Missing / blank (% of rows, symlog scale)")
    ax.set_title(title, fontweight="bold")
    ax.legend(loc="lower right")

    return _finish(fig, None)


def plot_distributions_before_after(before, after, cols=None, log=True,
                                    title="Distributions: Before vs After"):

    t = pal()

    cols = [c for c in (cols or DEFAULT_PLOT_SENSORS) if c in before.columns and c in after.columns]

    fig, axes = _grid(len(cols), 3, (4.7, 3.4))

    for ax, col in zip(axes, cols):
        b = _num(before, col)
        a = _num(after, col)

        lo = min(b.min(), a.min())
        hi = max(b.max(), a.max())

        bins = np.linspace(lo, hi, 50) if hi > lo else 10

        ax.hist(b, bins=bins, histtype="step", linewidth=1.6, color=t["before"], label="Before")
        ax.hist(a, bins=bins, color=t["after"], alpha=0.55, label="After")

        if log:
            ax.set_yscale("log")

        ax.set_title(_label(col), fontsize=10)

    axes[0].legend(fontsize=8)

    fig.suptitle(title + (" (log counts)" if log else ""), fontsize=14, fontweight="bold")

    fig.tight_layout()

    return fig


def plot_boxplots_before_after(before, after, cols=None, zoom=True,
                               title="Boxplots: Before vs After"):

    t = pal()

    cols = [c for c in (cols or DEFAULT_PLOT_SENSORS) if c in before.columns and c in after.columns]

    fig, axes = _grid(len(cols), 4, (3.6, 3.6))

    for ax, col in zip(axes, cols):
        bp = ax.boxplot(
            [_num(before, col), _num(after, col)],
            patch_artist=True,
            widths=0.6,
            medianprops=dict(color=t["fg"]),
            whiskerprops=dict(color=t["muted"]),
            capprops=dict(color=t["muted"]),
            flierprops=dict(marker=".", markersize=2, markeredgecolor=t["muted"]),
        )

        for patch, color in zip(bp["boxes"], [t["before"], t["after"]]):
            patch.set_facecolor(color)
            patch.set_edgecolor(t["fg"])

        ax.set_xticks([1, 2])
        ax.set_xticklabels(["Before", "After"], fontsize=8)
        ax.set_title(_label(col), fontsize=9)

        if zoom:
            # sentinels such as -999 would flatten every box: show the valid range
            # plus generous headroom so positive spikes are still visible
            a = _num(after, col)
            span = max(a.max() - a.min(), 1e-6)
            ax.set_ylim(a.min() - 0.4 * span, a.max() + 2.0 * span)

    fig.suptitle(title, fontsize=14, fontweight="bold")

    fig.tight_layout()

    return fig


def plot_stream_before_after(before, after, col, start=0, n=1000):
    """
    Raw sensor stream vs the validated stream for the SAME time window.
    Gaps in the left panel are dropouts, spikes are outliers.
    """

    t = pal()

    a_win = after.iloc[start:start + n]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)

    if a_win.empty:
        axes[0].text(0.5, 0.5, "No data for this selection", ha="center", va="center")
        return fig

    t0, t1 = a_win[TIME_COL].min(), a_win[TIME_COL].max()

    raw_t = pd.to_datetime(before[TIME_COL], errors="coerce")

    mask = (raw_t >= t0) & (raw_t <= t1)

    bx = raw_t[mask]
    by = pd.to_numeric(before.loc[mask, col], errors="coerce")

    ay = pd.to_numeric(a_win[col], errors="coerce")

    axes[0].plot(bx, by, color=t["before"], linewidth=1.1)
    axes[0].set_title("Before: raw readings (outliers and gaps)", fontsize=10, color=t["before"], fontweight="bold")

    axes[1].plot(a_win[TIME_COL], ay, color=t["after"], linewidth=1.1)
    axes[1].set_title("After: validated and cleaned readings", fontsize=10, fontweight="bold")

    axes[0].set_ylabel(_label(col))

    # Sentinel values such as -999 would flatten the chart, so the view is
    # limited to just below the cleaned range; positive spikes stay visible.
    ref = ay.dropna()

    if len(ref):
        span = max(ref.max() - ref.min(), 1e-6)
        lo = ref.min() - 0.5 * span
        visible = by[by >= lo]
        hi = max(visible.max() if len(visible) else ref.max(), ref.max()) + 0.1 * span
        axes[0].set_ylim(lo, hi)

    fig.autofmt_xdate()

    return _finish(fig, None)