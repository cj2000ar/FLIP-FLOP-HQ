from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import polars as pl

ROOT = Path(r"C:\FLIP_FLOP_HQ")
RAW_DIR = ROOT / "01_INBOX" / "market_data" / "raw"
NORMALIZED_DIR = ROOT / "01_INBOX" / "market_data" / "normalized"
DATABASE = ROOT / "03_DATABASE" / "flip_flop.duckdb"
REPORT_DIR = ROOT / "06_REPORTS" / "forensic" / "stage2"

CANONICAL = ["timestamp_utc", "contract", "price", "bid", "ask", "size"]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize validated NQ tick/second data into the FLIP FLOP replay database."
    )
    parser.add_argument("csv", type=Path, help="Raw provider CSV path")
    parser.add_argument("--timestamp", required=True, help="Provider timestamp column")
    parser.add_argument("--contract", required=True, help="Provider contract-symbol column")
    parser.add_argument("--price", required=True, help="Provider trade/close price column")
    parser.add_argument("--bid", default=None, help="Provider bid column, optional")
    parser.add_argument("--ask", default=None, help="Provider ask column, optional")
    parser.add_argument("--size", default=None, help="Provider trade-size column, optional")
    parser.add_argument("--timezone", default="UTC",
                        help="Timezone of provider timestamps. UTC strongly preferred.")
    parser.add_argument("--quality", choices=["A", "B", "C"], required=True)
    args = parser.parse_args()

    source = args.csv.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    raw_hash = sha256(source)
    preserved = RAW_DIR / f"{raw_hash[:12]}_{source.name}"
    if not preserved.exists():
        shutil.copy2(source, preserved)

    frame = pl.read_csv(source, try_parse_dates=False)
    required_provider = [args.timestamp, args.contract, args.price]
    missing = [c for c in required_provider if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing required provider columns: {missing}")

    expressions = [
        pl.col(args.timestamp).alias("timestamp_source"),
        pl.col(args.contract).cast(pl.Utf8).alias("contract"),
        pl.col(args.price).cast(pl.Float64).alias("price"),
        (pl.col(args.bid).cast(pl.Float64) if args.bid else pl.lit(None, dtype=pl.Float64)).alias("bid"),
        (pl.col(args.ask).cast(pl.Float64) if args.ask else pl.lit(None, dtype=pl.Float64)).alias("ask"),
        (pl.col(args.size).cast(pl.Float64) if args.size else pl.lit(None, dtype=pl.Float64)).alias("size"),
    ]
    normalized = frame.select(expressions)

    # Strict timestamp policy: the importer does not silently guess formats/timezones.
    try:
        normalized = normalized.with_columns(
            pl.col("timestamp_source")
              .str.to_datetime(strict=True, time_zone=args.timezone)
              .dt.convert_time_zone("UTC")
              .alias("timestamp_utc")
        )
    except Exception as exc:
        raise ValueError(
            "Timestamp parsing failed. Export ISO-8601 timestamps or provide a provider-specific "
            "adapter. No timestamps were guessed."
        ) from exc

    normalized = (
        normalized.select(CANONICAL)
        .drop_nulls(["timestamp_utc", "contract", "price"])
        .sort(["contract", "timestamp_utc"])
        .with_columns([
            pl.lit(str(preserved)).alias("source_file"),
            pl.lit(args.quality).alias("quality_tier"),
        ])
    )

    if normalized.height == 0:
        raise ValueError("No valid rows remained after normalization")

    if args.quality == "A":
        if normalized["bid"].null_count() > 0 or normalized["ask"].null_count() > 0:
            raise ValueError("Tier A requires bid and ask on every row")
    if args.quality in {"A", "B"} and normalized["size"].null_count() == normalized.height:
        raise ValueError("Tier A/B requires a trade-size column")

    output = NORMALIZED_DIR / f"{raw_hash[:12]}_{source.stem}.parquet"
    normalized.write_parquet(output)

    con = duckdb.connect(str(DATABASE))
    try:
        con.execute("DELETE FROM market_ticks WHERE source_file = ?", [str(preserved)])
        con.execute(
            "INSERT INTO market_ticks SELECT * FROM read_parquet(?)",
            [str(output)],
        )
        con.commit()
    finally:
        con.close()

    report = {
        "status": "PASS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "preserved_raw": str(preserved),
        "source_sha256": raw_hash,
        "normalized_parquet": str(output),
        "quality_tier": args.quality,
        "rows": normalized.height,
        "contracts": normalized["contract"].n_unique(),
        "first_timestamp_utc": str(normalized["timestamp_utc"].min()),
        "last_timestamp_utc": str(normalized["timestamp_utc"].max()),
        "bid_nulls": normalized["bid"].null_count(),
        "ask_nulls": normalized["ask"].null_count(),
        "size_nulls": normalized["size"].null_count(),
    }
    report_path = REPORT_DIR / f"MARKET_DATA_IMPORT_{raw_hash[:12]}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print("")
    print("MARKET DATA IMPORT - PASS")
    print("Pull testing remains blocked until contract coverage and roll mapping pass.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print("MARKET DATA IMPORT FAILED")
        print(str(exc))
        sys.exit(1)
