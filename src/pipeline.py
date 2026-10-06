from src.config import (
    RAW_CSV,
    SENSOR_COLS,
    ENGINEERED_NUMERIC_COLS,
    TARGET,
)

from src.extract import ensure_dataset, extract_csv
from src.clean import clean_data
from src.schemas import validate_dataframe
from src.features import engineer_features
from src import eda
from src.load import load_to_db


def run_pipeline(
    source=RAW_CSV,
    save=True,
    inject_noise=False,
    noise_level=1.0,
    make_figs=True,
):
    """
    Full ETL + EDA pipeline on the backend pump dataset.

    Args:
        source:       path of sensor.csv (default: data/raw/sensor.csv)
        save:         write plots, processed CSV and SQLite DB to disk.
        inject_noise: DEMO ONLY - corrupt the raw data so cleaning has visible work to do.
        noise_level:  multiplier for the injected noise.
        make_figs:    build the matplotlib figures (the Streamlit app builds them
                      on demand instead, so it passes False).
    """

    # ========================================================
    # 1. EXTRACT
    # ========================================================

    if source == RAW_CSV:
        source = ensure_dataset(RAW_CSV)

    raw = extract_csv(source, inject_noise=inject_noise, noise_level=noise_level)

    # ========================================================
    # 2. EDA BEFORE CLEANING
    # ========================================================

    before_figs = {}

    if make_figs:
        before_figs = {
            "missing_before": eda.plot_missing(
                raw, "Missing Values — BEFORE Cleaning",
                "missing_before" if save else None),
            "dist_before": eda.plot_distributions(
                raw, "Distributions — BEFORE Cleaning",
                "dist_before" if save else None),
            "box_before": eda.plot_boxplots(
                raw, "Boxplots — BEFORE Cleaning",
                "box_before" if save else None),
        }

    # ========================================================
    # 3. CLEANING
    # ========================================================

    clean, report = clean_data(raw)

    # ========================================================
    # 4. PYDANTIC VALIDATION (bad rows are quarantined)
    # ========================================================

    valid, rejected = validate_dataframe(clean)

    report["pydantic_rejected_rows"] = rejected.attrs.get("total_rejected", len(rejected))

    # ========================================================
    # 5. FEATURE ENGINEERING
    # ========================================================

    final, scale_stats = engineer_features(valid)

    top_sensors = eda.top_correlated(final, 14)

    # ========================================================
    # 6. EDA AFTER CLEANING
    # ========================================================

    after_figs = {}

    if make_figs:
        correlation_columns = top_sensors + ["deviation_mean_abs", TARGET]

        after_figs = {
            "missing_after": eda.plot_missing(
                valid[SENSOR_COLS], "Missing Values — AFTER Cleaning",
                "missing_after" if save else None),
            "dist_after": eda.plot_distributions(
                valid, "Distributions — AFTER Cleaning",
                "dist_after" if save else None),
            "box_after": eda.plot_boxplots(
                valid, "Boxplots — AFTER Cleaning",
                "box_after" if save else None),
            "correlation": eda.plot_correlation(
                final, "Correlation Matrix", correlation_columns,
                "correlation_after" if save else None),
            "class_balance": eda.plot_class_balance(
                final, "class_balance" if save else None),
            "status_distribution": eda.plot_status_distribution(
                final, "status_distribution" if save else None),
        }

    # ========================================================
    # 7. LOAD
    # ========================================================

    if save:
        load_to_db(final)

    # ========================================================
    # 8. RETURN COMPLETE RESULT
    # ========================================================

    return {
        "raw": raw,
        "clean": valid,
        "final": final,
        "report": report,
        "rejected": rejected,
        "scale_stats": scale_stats,
        "top_sensors": top_sensors,
        "figs": {**before_figs, **after_figs},
    }


if __name__ == "__main__":
    import json
    import matplotlib.pyplot as plt

    result = run_pipeline(save=True, inject_noise=True)

    print(json.dumps(
        {k: v for k, v in result["report"].items() if not isinstance(v, (dict, list))},
        indent=2,
        default=str,
    ))
    print("Plots saved to outputs/plots, data saved to data/")

    plt.close("all")