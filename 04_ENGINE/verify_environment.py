from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import duckdb
import numpy
import pandas
import plotly
import polars
import pyarrow
import pydantic
import streamlit

ROOT = Path(r"C:\FLIP_FLOP_HQ")
REPORT = ROOT / "08_LOGS" / "PYTHON_ENVIRONMENT.json"

details = {
    "status": "PASS",
    "python": sys.version,
    "python_64_bit": platform.architecture()[0],
    "platform": platform.platform(),
    "packages": {
        "polars": polars.__version__,
        "duckdb": duckdb.__version__,
        "pyarrow": pyarrow.__version__,
        "pandas": pandas.__version__,
        "numpy": numpy.__version__,
        "plotly": plotly.__version__,
        "streamlit": streamlit.__version__,
        "pydantic": pydantic.__version__,
    },
}

# Basic DuckDB execution proof.
result = duckdb.sql("SELECT 2583 + 2583 AS matched_worker_trades").fetchone()[0]
details["duckdb_test"] = result

# Basic Polars execution proof.
frame = polars.DataFrame(
    {
        "worker": ["BUY", "SELL"],
        "trades": [2583, 2583],
        "net_profit": [148888.0, 145388.0],
    }
)

details["polars_test"] = {
    "rows": frame.height,
    "combined_trades": int(frame["trades"].sum()),
    "combined_profit": float(frame["net_profit"].sum()),
}

REPORT.write_text(json.dumps(details, indent=2), encoding="utf-8")

print("=" * 60)
print("FLIP FLOP QUANT LAB PYTHON CHECK")
print("=" * 60)
print(json.dumps(details, indent=2))
print("=" * 60)
print(f"REPORT SAVED: {REPORT}")
print("=" * 60)
