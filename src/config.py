from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================
# The dataset lives in the backend:  <project>/data/raw/sensor.csv
# (Kaggle: nphantawee/pump-sensor-data). Nothing is uploaded in the app.

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_CSV = BASE_DIR / "data" / "raw" / "sensor.csv"

PROCESSED_CSV = BASE_DIR / "data" / "processed" / "clean_features.csv"

DB_PATH = BASE_DIR / "data" / "maintenance.db"

PLOTS_DIR = BASE_DIR / "outputs" / "plots"

TABLE_NAME = "pump_sensor_data"

KAGGLE_DATASET = "nphantawee/pump-sensor-data"


# ============================================================
# DATASET COLUMNS
# ============================================================
# sensor.csv = [unnamed index], timestamp, sensor_00 ... sensor_51, machine_status
# 220,320 rows, one reading per minute (Apr-Aug 2018), ONE pump.

TIME_COL = "timestamp"

STATUS_COL = "machine_status"

ALL_SENSOR_COLS = [f"sensor_{i:02d}" for i in range(52)]

# sensor_15 is 100 % empty in the source file -> dropped during cleaning
DEAD_SENSORS = ["sensor_15"]

SENSOR_COLS = [c for c in ALL_SENSOR_COLS if c not in DEAD_SENSORS]

# kept so older code that says NUMERIC_COLS still works
NUMERIC_COLS = SENSOR_COLS

SENSOR_LABELS = {c: c.replace("sensor_", "Sensor ") for c in ALL_SENSOR_COLS}

# 52 sensors are too many for one grid of plots -> default subset for grids
DEFAULT_PLOT_SENSORS = [
    "sensor_00", "sensor_01", "sensor_02", "sensor_04",
    "sensor_06", "sensor_07", "sensor_08", "sensor_09",
    "sensor_10", "sensor_11", "sensor_50", "sensor_51",
]

VALID_STATUS = ["NORMAL", "BROKEN", "RECOVERING"]

REQUIRED_COLS = [TIME_COL] + ALL_SENSOR_COLS + [STATUS_COL]


# ============================================================
# TARGET DEFINITION
# ============================================================
# The raw data has only 7 BROKEN rows (out of 220,320), so we cannot
# train on "status == BROKEN" directly. Two ways to build breakdown_flag:
#
#   "early_warning"  : 1 = a BROKEN event happens within the next
#                      HORIZON_MIN minutes  (real prediction task)  <- default
#   "abnormal_state" : 1 = status is BROKEN or RECOVERING
#                      (detects an abnormal state, much easier)

TARGET = "breakdown_flag"

TARGET_MODE = "early_warning"

HORIZON_MIN = 1440  # 24 hours

# Columns that must NOT be model inputs (they define / reveal the target)
LEAKY_COLS = [STATUS_COL, TARGET]

# In early-warning mode the RECOVERING rows (the days after a failure) are
# not "normal operation" and not a warning phase -> left out of the ML model.
MODEL_EXCLUDE_STATUS = ["RECOVERING"]

# share of failure EVENTS (not rows) held out for the time-based test split
TEST_EVENT_FRACTION = 0.3


# ============================================================
# DATA CLEANING SETTINGS
# ============================================================

# sensor "no data" codes that are never real readings
SENTINEL_VALUES = [-999.0]

# Optional per-sensor physical limits, e.g. {"sensor_04": (0, 2000)}.
# Units of this dataset are not published, so nothing is assumed by default.
VALID_RANGES = {}

# Outlier fence = Q3 + k * IQR, computed on NORMAL rows only and applied to
# NORMAL rows only. Rows in BROKEN / RECOVERING state are never touched:
# their extreme values ARE the failure signal.
IQR_MULTIPLIER = 8.0

# gaps up to this many minutes are linearly interpolated; longer gaps fall
# back to the median of the same machine_status
INTERP_LIMIT_MIN = 30


# ============================================================
# FEATURE ENGINEERING
# ============================================================

# rolling window (rows = minutes) for the trailing deviation statistics
ROLL_WINDOW = 60

# Aggregate "health" features built from the z-scores of all sensors.
# These need only ONE reading, so the Risk Inference page can compute them.
POINT_ENGINEERED_COLS = [
    "deviation_mean_abs",
    "deviation_max_abs",
    "n_sensors_beyond_3sd",
    "n_zero_sensors",
]

# These need history (trailing window) - used for EDA / Phase 2, not the baseline model.
ROLLING_ENGINEERED_COLS = [
    "deviation_roll_mean",
    "deviation_roll_std",
]

ENGINEERED_NUMERIC_COLS = POINT_ENGINEERED_COLS + ROLLING_ENGINEERED_COLS

SCALE_COLS = SENSOR_COLS

BINARY_COLS = [TARGET]


# ============================================================
# OUTPUT / VISUALIZATION SETTINGS
# ============================================================

PLOT_DPI = 150

PLOT_FORMAT = "png"

SAVE_PLOTS = True


# ============================================================
# RANDOM STATE
# ============================================================

RANDOM_STATE = 42