from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd
from pydantic import Field, ValidationError, create_model

from src.config import SENSOR_COLS, TIME_COL, STATUS_COL, TARGET, VALID_STATUS


# One float field per sensor (finite numbers only) + timestamp, status, target.
_fields = {
    TIME_COL: (datetime, ...),
    STATUS_COL: (str, Field(pattern="^(" + "|".join(VALID_STATUS) + ")$")),
    TARGET: (int, Field(ge=0, le=1)),
}

for _col in SENSOR_COLS:
    _fields[_col] = (float, Field(allow_inf_nan=False))

MachineRecord = create_model("MachineRecord", **_fields)


def validate_dataframe(
    df: pd.DataFrame,
    max_reported: int = 1000,
    chunk_size: int = 20_000,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Validate every row of the cleaned dataframe against MachineRecord.

    Instead of crashing on the first bad row, bad rows are QUARANTINED.
    Rows are converted to dicts in chunks to keep memory low (220k rows x 54 cols).

    Returns:
        valid_df     - rows that passed (all original columns kept)
        rejected_df  - quarantined rows with the reason (capped at max_reported rows)
    """

    fields = [f for f in MachineRecord.model_fields if f in df.columns]

    ok = np.ones(len(df), dtype=bool)
    rejected = []

    for start in range(0, len(df), chunk_size):

        block = df.iloc[start:start + chunk_size]

        for offset, record in enumerate(block[fields].to_dict("records")):

            try:
                MachineRecord.model_validate(record)

            except ValidationError as exc:
                i = start + offset
                ok[i] = False

                if len(rejected) < max_reported:
                    reason = "; ".join(
                        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                        for err in exc.errors()
                    )
                    rejected.append({"row_index": int(df.index[i]), "reason": reason})

    valid_df = df.loc[ok].reset_index(drop=True)

    rejected_df = pd.DataFrame(rejected, columns=["row_index", "reason"])

    # keep the true total even if the detail list was capped
    rejected_df.attrs["total_rejected"] = int((~ok).sum())

    return valid_df, rejected_df