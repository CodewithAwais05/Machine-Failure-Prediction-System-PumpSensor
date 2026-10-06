import sqlite3

import pandas as pd

from src.config import (
    DB_PATH,
    TABLE_NAME,
    PROCESSED_CSV,
)


def load_to_db(
    df: pd.DataFrame
):

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    PROCESSED_CSV.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # SAVE PROCESSED CSV
    # ========================================================

    df.to_csv(
        PROCESSED_CSV,
        index=False
    )

    # ========================================================
    # SAVE SQLITE DATABASE
    # ========================================================

    with sqlite3.connect(
        DB_PATH
    ) as conn:

        df.to_sql(
            TABLE_NAME,
            conn,
            if_exists="replace",
            index=False,
            chunksize=10_000
        )


def run_query(
    sql: str
):

    query = sql.strip()

    if not query.lower().startswith(
        "select"
    ):

        raise ValueError(
            "Only SELECT queries are allowed."
        )

    with sqlite3.connect(
        DB_PATH
    ) as conn:

        return pd.read_sql_query(
            query,
            conn
        )