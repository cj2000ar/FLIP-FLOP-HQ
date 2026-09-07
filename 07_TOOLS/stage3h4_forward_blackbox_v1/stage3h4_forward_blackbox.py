from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dateutil import tz

ROOT = Path(r"C:\FLIP_FLOP_HQ")
CONTROL_MANIFEST = ROOT / "00_CONTROL" / "V3_6_72_2020_BASELINE" / "control_manifest.json"

INSTALL_DIR = ROOT / "07_TOOLS" / "stage3h4_forward_blackbox_v1"
EXPERIMENT_DIR = ROOT / "05_EXPERIMENTS" / "forward_preentry_blackbox" / "stage3h4"
REPORT_DIR = ROOT / "06_REPORTS" / "forward_shadow" / "stage3h4"
LOG_DIR = ROOT / "08_LOGS" / "stage3h4"
INBOX = ROOT / "01_RAW" / "FORWARD_BLACKBOX_INBOX"

PROTOCOL_LOCK = EXPERIMENT_DIR / "FORWARD_BLACKBOX_PROTOCOL_LOCK.json"
SESSION_MANIFEST = EXPERIMENT_DIR / "FORWARD_SESSION_MANIFEST.csv"
EVENT_LEDGER = EXPERIMENT_DIR / "FORWARD_BLACKBOX_EVENT_LEDGER.jsonl"
LATEST_STATUS = EXPERIMENT_DIR / "FORWARD_BLACKBOX_LATEST_STATUS.csv"
CATALOG_CACHE = EXPERIMENT_DIR / "PARQUET_CATALOG_CACHE.csv"
HASH_CACHE = EXPERIMENT_DIR / "SOURCE_HASH_CACHE.csv"

PACKAGE_PROTOCOL_FROZEN_UTC = pd.Timestamp("2026-08-08T00:32:00Z")
PROTOCOL_ID = "FF-STAGE3H4-FROZEN-FORWARD-BLACKBOX-V1"
CONTROL_VERSION = "V3.6.72"

ET = tz.gettz("America/New_York")
if ET is None:
    raise RuntimeError("America/New_York timezone database unavailable")

FREEZE_MINUTES = 5
MICRO_FREEZE_SECONDS = 5
PREOPEN_MINUTES = 60

MICRO_HORIZONS = {
    "H300": 300,
    "H60": 60,
    "H15": 15,
}

# Forward capture is strict. These are frozen before any eligible forward session.
PREOPEN_MAX_START_LAG_SECONDS = 60.0
PREOPEN_MAX_END_LAG_SECONDS = 60.0
PREOPEN_MAX_GAP_SECONDS = 60.0

MICRO_MAX_START_LAG_SECONDS = {
    "H300": 5.0,
    "H60": 3.0,
    "H15": 1.5,
}
MICRO_MAX_END_LAG_SECONDS = 1.5
MICRO_MAX_GAP_SECONDS = {
    "H300": 10.0,
    "H60": 7.5,
    "H15": 3.0,
}

SCAN_ROOTS = [
    ROOT / "01_RAW",
    ROOT / "02_VALIDATED",
]

SCHEDULE_RULES = {
    "NY": "Monday-Friday 09:30 ET",
    "WEEKLY": "Sunday 18:00 ET",
    "WEEKDAY_REOPEN": "Monday-Thursday 18:00 ET",
    "WEEKDAY_1830": "DISABLED in frozen default (weekdayDelayedPool=OFF)",
}

ROUTE_STATIC_MAP = {
    "NY": "SELL",
    "WEEKLY": "BUY",
    "WEEKDAY_PREMIUM": "BUY",
    "WEEKDAY_WEAK": "SELL",
}

PROTOCOL_CORE = {
    "protocol_id": PROTOCOL_ID,
    "control_version": CONTROL_VERSION,
    "package_protocol_frozen_utc": PACKAGE_PROTOCOL_FROZEN_UTC.isoformat(),
    "schedule_rules": SCHEDULE_RULES,
    "preopen": {
        "start": "T-60m",
        "freeze": "T-5m",
        "decision": "FREEZE_GT_START_BUY__FREEZE_LT_START_SELL__EQUAL_SKIP",
        "max_start_lag_seconds": PREOPEN_MAX_START_LAG_SECONDS,
        "max_end_lag_seconds": PREOPEN_MAX_END_LAG_SECONDS,
        "max_internal_gap_seconds": PREOPEN_MAX_GAP_SECONDS,
    },
    "microstructure": {
        "freeze": "T-5s",
        "horizons_seconds": MICRO_HORIZONS,
        "max_start_lag_seconds": MICRO_MAX_START_LAG_SECONDS,
        "max_end_lag_seconds": MICRO_MAX_END_LAG_SECONDS,
        "max_internal_gap_seconds": MICRO_MAX_GAP_SECONDS,
        "decision_authority": "TELEMETRY_ONLY",
    },
    "path_authority": "ORDERED_TBBO_ONLY",
    "default_bars": "EXCLUDED",
    "pine_change": False,
    "stage4e_change": False,
    "quantity_change": False,
    "live_routing": False,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def json_safe(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): json_safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [json_safe(x) for x in v]
    if isinstance(v, tuple):
        return [json_safe(x) for x in v]
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if pd.isna(v):
        return None
    return v


def canonical_json(obj: Any) -> str:
    return json.dumps(json_safe(obj), sort_keys=True, separators=(",", ":"))


def protocol_hash() -> str:
    return sha256_text(canonical_json(PROTOCOL_CORE))


def now_utc() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc))


def et_to_utc(dt_et: datetime) -> pd.Timestamp:
    require(dt_et.tzinfo is not None, "ET datetime must be timezone-aware")
    return pd.Timestamp(dt_et.astimezone(timezone.utc))


def utc_to_et(ts: pd.Timestamp) -> datetime:
    x = pd.Timestamp(ts)
    if x.tzinfo is None:
        x = x.tz_localize("UTC")
    return x.to_pydatetime().astimezone(ET)


def verify_frozen_pine_schedule() -> dict[str, Any]:
    require(CONTROL_MANIFEST.exists(), f"Missing control manifest: {CONTROL_MANIFEST}")
    manifest = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))

    require(manifest.get("status") == "PASS", "Frozen control manifest is not PASS")
    require(manifest.get("immutable_control") is True, "Frozen control is not immutable")

    pine_records = []
    for rec in manifest.get("files", []):
        path = Path(rec["path"])
        require(path.exists(), f"Frozen control file missing: {path}")
        actual = sha256_file(path)
        require(actual == rec["sha256"], f"Frozen control hash mismatch: {path.name}")
        if path.suffix.lower() == ".pine":
            pine_records.append((path, actual))

    require(len(pine_records) >= 2, "Expected frozen BUY and SELL Pine files")

    checks = {}
    for path, digest in pine_records:
        txt = path.read_text(encoding="utf-8", errors="replace")
        required_tokens = [
            'input.session("0930-1600"',
            'weeklyTiming = "WEEKLY 18:00"',
            'useMondayClockReopen = input.bool(true',
            'useTuesdayClockReopen = input.bool(true',
            'useWednesdayClockReopen = input.bool(true',
            'useThursdayClockReopen = input.bool(true',
            'weekdayDelayedPool = "OFF"',
        ]
        missing = [token for token in required_tokens if token not in txt]
        require(not missing, f"Frozen Pine schedule fingerprint missing in {path.name}: {missing}")
        checks[path.name] = {
            "sha256": digest,
            "schedule_fingerprint": "PASS",
        }

    return checks


def first_eligible_cutoff(existing_lock: dict[str, Any] | None = None) -> pd.Timestamp:
    if existing_lock:
        return pd.Timestamp(existing_lock["eligible_after_utc"])

    install_time = now_utc()
    return max(PACKAGE_PROTOCOL_FROZEN_UTC, install_time)


def make_capture_id(entry_utc: pd.Timestamp, passport: str) -> str:
    raw = f"{PROTOCOL_ID}|{entry_utc.isoformat()}|{passport}|{CONTROL_VERSION}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def generate_sessions(eligible_after_utc: pd.Timestamp, days: int = 180) -> pd.DataFrame:
    start_et = utc_to_et(eligible_after_utc).date()
    end_date = start_et + timedelta(days=days)

    rows = []
    d = start_et
    while d <= end_date:
        weekday = d.weekday()  # Mon=0 ... Sun=6

        candidates = []

        if weekday <= 4:
            candidates.append(("NY", time(9, 30)))

        if weekday == 6:
            candidates.append(("WEEKLY", time(18, 0)))

        if 0 <= weekday <= 3:
            candidates.append(("WEEKDAY_REOPEN", time(18, 0)))

        for passport, clock in candidates:
            local_dt = datetime.combine(d, clock).replace(tzinfo=ET)
            entry_utc = et_to_utc(local_dt)

            if entry_utc <= eligible_after_utc:
                continue

            rows.append({
                "capture_id": make_capture_id(entry_utc, passport),
                "protocol_id": PROTOCOL_ID,
                "protocol_hash": protocol_hash(),
                "control_version": CONTROL_VERSION,
                "scheduled_entry_et": local_dt.isoformat(),
                "scheduled_entry_utc": entry_utc.isoformat(),
                "passport": passport,
                "route_class": (
                    passport
                    if passport in {"NY", "WEEKLY"}
                    else "PENDING_PREMIUM_OR_WEAK"
                ),
                "route_static_action": (
                    ROUTE_STATIC_MAP.get(passport, "PENDING_ROUTE")
                ),
                "preopen_start_utc": (entry_utc - pd.Timedelta(minutes=PREOPEN_MINUTES)).isoformat(),
                "preopen_freeze_utc": (entry_utc - pd.Timedelta(minutes=FREEZE_MINUTES)).isoformat(),
                "micro_h300_start_utc": (entry_utc - pd.Timedelta(seconds=300)).isoformat(),
                "micro_h60_start_utc": (entry_utc - pd.Timedelta(seconds=60)).isoformat(),
                "micro_h15_start_utc": (entry_utc - pd.Timedelta(seconds=15)).isoformat(),
                "micro_freeze_utc": (entry_utc - pd.Timedelta(seconds=MICRO_FREEZE_SECONDS)).isoformat(),
                "forward_eligible": True,
            })

        d += timedelta(days=1)

    out = pd.DataFrame(rows)
    require(not out.empty, "No future sessions generated")
    return out.sort_values("scheduled_entry_utc").reset_index(drop=True)


def install_protocol(package_root: Path) -> dict[str, Any]:
    for p in [INSTALL_DIR, EXPERIMENT_DIR, REPORT_DIR, LOG_DIR, INBOX]:
        p.mkdir(parents=True, exist_ok=True)

    pine_checks = verify_frozen_pine_schedule()

    existing_lock = None
    if PROTOCOL_LOCK.exists():
        existing_lock = json.loads(PROTOCOL_LOCK.read_text(encoding="utf-8"))
        require(existing_lock["protocol_hash"] == protocol_hash(), "Existing Stage 3H.4 protocol hash differs")
        eligible_after = pd.Timestamp(existing_lock["eligible_after_utc"])
        install_status = "ALREADY_FROZEN_IDEMPOTENT"
    else:
        eligible_after = first_eligible_cutoff()
        lock = {
            "status": "FROZEN",
            "protocol_id": PROTOCOL_ID,
            "protocol_hash": protocol_hash(),
            "package_protocol_frozen_utc": PACKAGE_PROTOCOL_FROZEN_UTC.isoformat(),
            "installed_utc": now_utc().isoformat(),
            "eligible_after_utc": eligible_after.isoformat(),
            "pine_schedule_checks": pine_checks,
            "protocol": PROTOCOL_CORE,
        }
        PROTOCOL_LOCK.write_text(json.dumps(json_safe(lock), indent=2), encoding="utf-8")
        install_status = "NEW_PROTOCOL_FROZEN"

    sessions = generate_sessions(eligible_after, days=180)

    if SESSION_MANIFEST.exists():
        old = pd.read_csv(SESSION_MANIFEST)
        if len(old):
            old_ids = set(old["capture_id"].astype(str))
            new_only = sessions[~sessions["capture_id"].astype(str).isin(old_ids)].copy()
            merged = pd.concat([old, new_only], ignore_index=True)
            merged = merged.drop_duplicates("capture_id", keep="first")
            merged = merged.sort_values("scheduled_entry_utc")
            merged.to_csv(SESSION_MANIFEST, index=False)
        else:
            sessions.to_csv(SESSION_MANIFEST, index=False)
    else:
        sessions.to_csv(SESSION_MANIFEST, index=False)

    # Install scorer files inside the Quant Lab so the scheduled task is not tied to Downloads.
    source_tool = package_root / "TOOLS" / "stage3h4_forward_blackbox.py"
    source_runner = package_root / "TOOLS" / "RUN_LOCAL_FORWARD_SCORER.ps1"
    require(source_tool.exists(), f"Package tool missing: {source_tool}")
    require(source_runner.exists(), f"Package local runner missing: {source_runner}")

    shutil.copy2(source_tool, INSTALL_DIR / source_tool.name)
    shutil.copy2(source_runner, INSTALL_DIR / source_runner.name)

    all_sessions = pd.read_csv(SESSION_MANIFEST)
    all_sessions["scheduled_entry_utc"] = pd.to_datetime(all_sessions["scheduled_entry_utc"], utc=True)
    future = all_sessions[all_sessions["scheduled_entry_utc"] > now_utc()].sort_values("scheduled_entry_utc")
    next_row = future.iloc[0] if len(future) else None

    report = {
        "status": "PASS",
        "install_status": install_status,
        "protocol_hash": protocol_hash(),
        "eligible_after_utc": eligible_after.isoformat(),
        "next_session": None if next_row is None else {
            "capture_id": next_row["capture_id"],
            "passport": next_row["passport"],
            "scheduled_entry_et": next_row["scheduled_entry_et"],
            "scheduled_entry_utc": next_row["scheduled_entry_utc"].isoformat(),
            "preopen_start_utc": next_row["preopen_start_utc"],
            "preopen_freeze_utc": next_row["preopen_freeze_utc"],
        },
        "manifest_rows": int(len(all_sessions)),
        "inbox": str(INBOX),
        "install_dir": str(INSTALL_DIR),
        "live_routing": "LOCKED",
        "pine_change": "BLOCKED",
        "stage4e_change": "BLOCKED",
        "quantity_change": "BLOCKED",
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "FLIP_FLOP_STAGE3H4_INSTALL_REPORT.json"
    report_path.write_text(json.dumps(json_safe(report), indent=2), encoding="utf-8")

    return report


def parquet_candidates() -> list[Path]:
    paths = []
    for base in SCAN_ROOTS:
        if base.exists():
            paths.extend(base.rglob("*.parquet"))
    return sorted(set(p.resolve() for p in paths if p.exists()))


def load_catalog_cache() -> pd.DataFrame:
    if CATALOG_CACHE.exists():
        try:
            return pd.read_csv(CATALOG_CACHE)
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "path", "size_bytes", "mtime_ns", "min_utc", "max_utc", "rows", "read_ok"
    ])


def update_catalog() -> pd.DataFrame:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    old = load_catalog_cache()
    old_idx = {}
    for _, r in old.iterrows():
        old_idx[str(r["path"])] = r.to_dict()

    rows = []
    for p in parquet_candidates():
        stat = p.stat()
        key = str(p)
        previous = old_idx.get(key)

        if (
            previous
            and int(previous.get("size_bytes", -1)) == int(stat.st_size)
            and int(previous.get("mtime_ns", -1)) == int(stat.st_mtime_ns)
            and str(previous.get("read_ok", "")).lower() in {"true", "1"}
        ):
            rows.append(previous)
            continue

        rec = {
            "path": key,
            "size_bytes": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
            "min_utc": None,
            "max_utc": None,
            "rows": 0,
            "read_ok": False,
        }
        try:
            f = pd.read_parquet(p, columns=["ts_event_utc"])
            ts = pd.to_datetime(f["ts_event_utc"], utc=True, errors="coerce").dropna()
            if len(ts):
                rec.update({
                    "min_utc": ts.min().isoformat(),
                    "max_utc": ts.max().isoformat(),
                    "rows": int(len(ts)),
                    "read_ok": True,
                })
        except Exception:
            pass
        rows.append(rec)

    out = pd.DataFrame(rows)
    out.to_csv(CATALOG_CACHE, index=False)
    if len(out):
        out["min_utc"] = pd.to_datetime(out["min_utc"], utc=True, errors="coerce")
        out["max_utc"] = pd.to_datetime(out["max_utc"], utc=True, errors="coerce")
    return out


def relevant_paths(catalog: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    if catalog.empty:
        return []
    x = catalog[
        (catalog["read_ok"].astype(str).str.lower().isin(["true", "1"]))
        & catalog["min_utc"].notna()
        & catalog["max_utc"].notna()
        & (catalog["max_utc"] >= start)
        & (catalog["min_utc"] <= end)
    ]
    return x["path"].astype(str).tolist()


def load_union(paths: list[str], start: pd.Timestamp, end: pd.Timestamp):
    frames = []
    failures = []

    for raw in paths:
        p = Path(raw)
        try:
            try:
                f = pd.read_parquet(
                    p,
                    columns=["ts_event_utc", "price", "bid", "ask", "quote_state", "sequence"],
                )
            except Exception:
                f = pd.read_parquet(p)

            needed = {"ts_event_utc", "price", "bid", "ask", "quote_state"}
            if not needed.issubset(f.columns):
                failures.append({"path": str(p), "error": "missing TBBO columns"})
                continue

            f["ts_event_utc"] = pd.to_datetime(f["ts_event_utc"], utc=True, errors="coerce")
            f = f[
                (f["ts_event_utc"] >= start)
                & (f["ts_event_utc"] <= end)
                & f["quote_state"].isin(["VALID", "LOCKED"])
                & f["price"].notna()
                & f["bid"].notna()
                & f["ask"].notna()
            ].copy()

            if f.empty:
                continue

            if "sequence" not in f.columns:
                f["sequence"] = np.nan
            f["_source_file"] = str(p)
            frames.append(f)

        except Exception as exc:
            failures.append({"path": str(p), "error": f"{type(exc).__name__}: {exc}"})

    if not frames:
        return pd.DataFrame(), {
            "read_failures": failures,
            "duplicates_removed": 0,
            "timestamp_regressions": 0,
            "sequence_regressions": 0,
            "source_files": [],
        }

    f = pd.concat(frames, ignore_index=True, sort=False)
    before = len(f)
    f["_seq_sort"] = pd.to_numeric(f["sequence"], errors="coerce").fillna(np.inf)
    f = f.sort_values(["ts_event_utc", "_seq_sort", "_source_file"]).reset_index(drop=True)

    dedup = ["ts_event_utc", "price", "bid", "ask"]
    if f["sequence"].notna().any():
        dedup.insert(1, "sequence")

    f = f.drop_duplicates(subset=dedup, keep="first").reset_index(drop=True)
    f["gap_sec"] = f["ts_event_utc"].diff().dt.total_seconds()

    seq = pd.to_numeric(f["sequence"], errors="coerce")
    same_ts = f["ts_event_utc"].eq(f["ts_event_utc"].shift(1))
    seq_reg = int(
        (
            same_ts
            & seq.notna()
            & seq.shift(1).notna()
            & (seq < seq.shift(1))
        ).sum()
    )
    time_reg = int((f["ts_event_utc"].diff().dt.total_seconds() < 0).sum())

    return f, {
        "read_failures": failures,
        "duplicates_removed": int(before - len(f)),
        "timestamp_regressions": time_reg,
        "sequence_regressions": seq_reg,
        "source_files": sorted(f["_source_file"].unique().tolist()),
    }


def continuity(
    events: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    max_start: float,
    max_end: float,
    max_gap: float,
    diag: dict[str, Any],
) -> dict[str, Any]:
    if events.empty:
        return {
            "coverage_pass": False,
            "coverage_status": "NO_VALID_TBBO_ROWS",
        }

    first_lag = float((events["ts_event_utc"].min() - start).total_seconds())
    last_lag = float((end - events["ts_event_utc"].max()).total_seconds())
    internal_gap = float(events["gap_sec"].max(skipna=True)) if len(events) > 1 else math.inf

    passed = (
        first_lag <= max_start
        and last_lag <= max_end
        and internal_gap <= max_gap
        and int(diag["timestamp_regressions"]) == 0
        and int(diag["sequence_regressions"]) == 0
        and len(diag["read_failures"]) == 0
    )

    return {
        "coverage_pass": bool(passed),
        "coverage_status": "VALIDATED_ORDERED_TBBO" if passed else "CONTINUITY_FAIL",
        "first_event_lag_sec": first_lag,
        "last_event_lag_sec": last_lag,
        "max_internal_gap_sec": internal_gap,
        "timestamp_regressions": int(diag["timestamp_regressions"]),
        "sequence_regressions": int(diag["sequence_regressions"]),
        "read_failure_count": int(len(diag["read_failures"])),
        "source_files": diag["source_files"],
    }


def price_features(events: pd.DataFrame) -> dict[str, Any]:
    price = events["price"].astype(float)
    bid = events["bid"].astype(float)
    ask = events["ask"].astype(float)
    spread = ask - bid

    start = float(price.iloc[0])
    end = float(price.iloc[-1])
    high = float(price.max())
    low = float(price.min())
    rng = high - low
    disp = end - start
    path = float(price.diff().abs().sum())
    eff = abs(disp) / path if path > 0 else 0.0

    duration = max(
        1e-9,
        (events["ts_event_utc"].max() - events["ts_event_utc"].min()).total_seconds(),
    )

    return {
        "start_price": start,
        "freeze_price": end,
        "displacement_points": disp,
        "high": high,
        "low": low,
        "range_points": rng,
        "finish_location_0_1": ((end - low) / rng if rng > 0 else 0.5),
        "event_path_points": path,
        "event_efficiency": eff,
        "event_rate_per_sec": float(len(events) / duration),
        "spread_median_points": float(spread.median()),
        "spread_p95_points": float(spread.quantile(0.95)),
        "spread_max_points": float(spread.max()),
        "spread_last_points": float(spread.iloc[-1]),
        "locked_quote_share": float((events["quote_state"] == "LOCKED").mean()),
    }


def score_window(
    catalog: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    max_start: float,
    max_end: float,
    max_gap: float,
) -> dict[str, Any]:
    paths = relevant_paths(catalog, start, end)
    if not paths:
        return {
            "coverage_pass": False,
            "coverage_status": "NO_OVERLAPPING_FILES",
            "source_files": [],
        }

    events, diag = load_union(paths, start, end)
    cov = continuity(events, start, end, max_start, max_end, max_gap, diag)
    out = dict(cov)

    if cov["coverage_pass"]:
        out.update(price_features(events))

    return out


def flatten(prefix: str, data: dict[str, Any], dest: dict[str, Any]) -> None:
    for k, v in data.items():
        if isinstance(v, (dict, list)):
            dest[f"{prefix}__{k}"] = json.dumps(json_safe(v), sort_keys=True)
        else:
            dest[f"{prefix}__{k}"] = v


def score_session(row: pd.Series, catalog: pd.DataFrame) -> dict[str, Any]:
    entry = pd.Timestamp(row["scheduled_entry_utc"])
    if entry.tzinfo is None:
        entry = entry.tz_localize("UTC")

    pre_start = entry - pd.Timedelta(minutes=PREOPEN_MINUTES)
    pre_freeze = entry - pd.Timedelta(minutes=FREEZE_MINUTES)

    result = {
        "capture_id": row["capture_id"],
        "protocol_id": PROTOCOL_ID,
        "protocol_hash": protocol_hash(),
        "control_version": CONTROL_VERSION,
        "scheduled_entry_et": row["scheduled_entry_et"],
        "scheduled_entry_utc": entry.isoformat(),
        "passport": row["passport"],
        "route_class": row["route_class"],
        "route_static_action": row["route_static_action"],
        "scored_utc": now_utc().isoformat(),
    }

    pre = score_window(
        catalog,
        pre_start,
        pre_freeze,
        PREOPEN_MAX_START_LAG_SECONDS,
        PREOPEN_MAX_END_LAG_SECONDS,
        PREOPEN_MAX_GAP_SECONDS,
    )
    flatten("PREOPEN60", pre, result)

    if pre.get("coverage_pass"):
        disp = float(pre["displacement_points"])
        result["PREOPEN60__action"] = "BUY" if disp > 0 else "SELL" if disp < 0 else "SKIP"
    else:
        result["PREOPEN60__action"] = "UNAVAILABLE"

    micro_freeze = entry - pd.Timedelta(seconds=MICRO_FREEZE_SECONDS)
    for h, seconds in MICRO_HORIZONS.items():
        start = entry - pd.Timedelta(seconds=seconds)
        micro = score_window(
            catalog,
            start,
            micro_freeze,
            MICRO_MAX_START_LAG_SECONDS[h],
            MICRO_MAX_END_LAG_SECONDS,
            MICRO_MAX_GAP_SECONDS[h],
        )
        flatten(h, micro, result)

    result["microstructure_decision_authority"] = "TELEMETRY_ONLY"
    result["live_order_authority"] = "NONE"

    return result


def load_last_ledger_by_capture() -> dict[str, dict[str, Any]]:
    out = {}
    if not EVENT_LEDGER.exists():
        return out

    with EVENT_LEDGER.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out[rec["capture_id"]] = rec
    return out


def append_changed_records(records: list[dict[str, Any]]) -> int:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    previous_by_id = load_last_ledger_by_capture()

    # Find the chain head.
    previous_chain = None
    if EVENT_LEDGER.exists():
        with EVENT_LEDGER.open("rb") as f:
            for line in f:
                if line.strip():
                    try:
                        previous_chain = json.loads(line)["record_hash"]
                    except Exception:
                        pass

    appended = 0
    with EVENT_LEDGER.open("a", encoding="utf-8") as f:
        for rec in records:
            payload = dict(rec)
            payload.pop("scored_utc", None)

            state_hash = sha256_text(canonical_json(payload))
            previous = previous_by_id.get(rec["capture_id"])
            if previous and previous.get("state_hash") == state_hash:
                continue

            envelope = dict(rec)
            envelope["state_hash"] = state_hash
            envelope["previous_record_hash"] = previous_chain
            envelope["record_hash"] = sha256_text(
                canonical_json({
                    "previous_record_hash": previous_chain,
                    "state_hash": state_hash,
                    "capture_id": rec["capture_id"],
                    "scored_utc": rec["scored_utc"],
                })
            )

            f.write(json.dumps(json_safe(envelope), sort_keys=True) + "\n")
            previous_chain = envelope["record_hash"]
            previous_by_id[rec["capture_id"]] = envelope
            appended += 1

    return appended


def rebuild_latest_status() -> pd.DataFrame:
    latest = load_last_ledger_by_capture()
    if not latest:
        out = pd.DataFrame()
        out.to_csv(LATEST_STATUS, index=False)
        return out

    out = pd.DataFrame(list(latest.values()))
    out["scheduled_entry_utc"] = pd.to_datetime(out["scheduled_entry_utc"], utc=True)
    out = out.sort_values("scheduled_entry_utc")
    out.to_csv(LATEST_STATUS, index=False)
    return out


def run_scorer() -> dict[str, Any]:
    require(PROTOCOL_LOCK.exists(), "Stage 3H.4 protocol is not installed/frozen")
    lock = json.loads(PROTOCOL_LOCK.read_text(encoding="utf-8"))
    require(lock["protocol_hash"] == protocol_hash(), "Protocol hash mismatch")
    require(SESSION_MANIFEST.exists(), "Forward session manifest missing")

    catalog = update_catalog()
    manifest = pd.read_csv(SESSION_MANIFEST)
    manifest["scheduled_entry_utc"] = pd.to_datetime(manifest["scheduled_entry_utc"], utc=True)

    # Score sessions whose pre-entry windows are fully in the past.
    cutoff = now_utc()
    eligible = manifest[
        (manifest["forward_eligible"].astype(str).str.lower().isin(["true", "1"]))
        & (manifest["scheduled_entry_utc"] - pd.Timedelta(seconds=MICRO_FREEZE_SECONDS) <= cutoff)
    ].copy()

    # Bound routine work to the last 120 days while keeping the immutable manifest.
    lower = cutoff - pd.Timedelta(days=120)
    eligible = eligible[eligible["scheduled_entry_utc"] >= lower].sort_values("scheduled_entry_utc")

    records = [score_session(r, catalog) for _, r in eligible.iterrows()]
    appended = append_changed_records(records)
    latest = rebuild_latest_status()

    report = {
        "status": "PASS",
        "protocol_hash": protocol_hash(),
        "run_utc": cutoff.isoformat(),
        "catalog_files": int(len(catalog)),
        "eligible_sessions_examined": int(len(eligible)),
        "ledger_records_appended": int(appended),
        "latest_sessions": int(len(latest)),
        "preopen_pass": (
            int(latest["PREOPEN60__coverage_pass"].astype(str).str.lower().isin(["true", "1"]).sum())
            if len(latest) and "PREOPEN60__coverage_pass" in latest.columns else 0
        ),
        "h300_pass": (
            int(latest["H300__coverage_pass"].astype(str).str.lower().isin(["true", "1"]).sum())
            if len(latest) and "H300__coverage_pass" in latest.columns else 0
        ),
        "h60_pass": (
            int(latest["H60__coverage_pass"].astype(str).str.lower().isin(["true", "1"]).sum())
            if len(latest) and "H60__coverage_pass" in latest.columns else 0
        ),
        "h15_pass": (
            int(latest["H15__coverage_pass"].astype(str).str.lower().isin(["true", "1"]).sum())
            if len(latest) and "H15__coverage_pass" in latest.columns else 0
        ),
        "live_routing": "LOCKED",
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "FLIP_FLOP_STAGE3H4_LATEST_SCORER_REPORT.json").write_text(
        json.dumps(json_safe(report), indent=2), encoding="utf-8"
    )

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "scorer_runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(json_safe(report), sort_keys=True) + "\n")

    return report


def status_report() -> str:
    require(PROTOCOL_LOCK.exists(), "Stage 3H.4 not installed")
    lock = json.loads(PROTOCOL_LOCK.read_text(encoding="utf-8"))
    manifest = pd.read_csv(SESSION_MANIFEST)
    manifest["scheduled_entry_utc"] = pd.to_datetime(manifest["scheduled_entry_utc"], utc=True)

    current = now_utc()
    future = manifest[manifest["scheduled_entry_utc"] > current].sort_values("scheduled_entry_utc")
    next_row = future.iloc[0] if len(future) else None

    latest = pd.DataFrame()
    if LATEST_STATUS.exists():
        try:
            latest = pd.read_csv(LATEST_STATUS)
        except Exception:
            pass

    lines = [
        "=" * 104,
        "FLIP FLOP STAGE 3H.4 - FROZEN FORWARD BLACK BOX V1",
        "=" * 104,
        f"Protocol: {PROTOCOL_ID}",
        f"Protocol hash: {lock['protocol_hash']}",
        f"Eligible after UTC: {lock['eligible_after_utc']}",
        "Path authority: ORDERED TBBO ONLY",
        "PREOPEN60: directional shadow only",
        "Microstructure: toxicity telemetry only",
        "Live routing: LOCKED",
        "",
    ]

    if next_row is not None:
        next_et = next_row["scheduled_entry_et"]
        lines += [
            "NEXT FROZEN SESSION",
            f"Passport: {next_row['passport']}",
            f"Entry ET: {next_et}",
            f"PREOPEN60 starts UTC: {next_row['preopen_start_utc']}",
            f"PREOPEN60 freezes UTC: {next_row['preopen_freeze_utc']}",
            f"Capture ID: {next_row['capture_id']}",
            "",
        ]

    lines += [
        "LOCAL DATA INBOX",
        str(INBOX),
        "",
        "LATEST CAPTURE COUNTS",
        f"Sessions with status rows: {len(latest)}",
    ]

    if len(latest):
        def count_pass(col: str) -> int:
            if col not in latest.columns:
                return 0
            return int(latest[col].astype(str).str.lower().isin(["true", "1"]).sum())

        lines += [
            f"PREOPEN60 validated: {count_pass('PREOPEN60__coverage_pass')}",
            f"H300 validated: {count_pass('H300__coverage_pass')}",
            f"H60 validated: {count_pass('H60__coverage_pass')}",
            f"H15 validated: {count_pass('H15__coverage_pass')}",
        ]

    lines += [
        "",
        "IMPORTANT",
        "This machine does not download market data, place orders, change Pine, change Stage 4E, or change size.",
        "It automatically scores authoritative TBBO files that appear in the Quant Lab raw/validated folders.",
        "=" * 104,
    ]

    return "\n".join(lines)


def register_task() -> dict[str, Any]:
    runner = INSTALL_DIR / "RUN_LOCAL_FORWARD_SCORER.ps1"
    require(runner.exists(), f"Installed local runner missing: {runner}")

    task_name = "FLIP_FLOP_STAGE3H4_FORWARD_BLACKBOX"
    command = (
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass '
        f'-File "{runner}"'
    )

    # Hourly is deliberate: no need for tighter polling because the scorer only processes files
    # that already exist locally and does not drive orders.
    args = [
        "schtasks", "/Create", "/F",
        "/SC", "HOURLY", "/MO", "1",
        "/TN", task_name,
        "/TR", command,
    ]
    proc = subprocess.run(args, capture_output=True, text=True, shell=False)

    return {
        "status": "PASS" if proc.returncode == 0 else "FAILED",
        "task_name": task_name,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def remove_task() -> dict[str, Any]:
    task_name = "FLIP_FLOP_STAGE3H4_FORWARD_BLACKBOX"
    proc = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", task_name],
        capture_output=True, text=True, shell=False,
    )
    return {
        "status": "PASS" if proc.returncode == 0 else "FAILED",
        "task_name": task_name,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["install", "score", "status", "register-task", "remove-task"])
    parser.add_argument("--package-root", default=None)
    args = parser.parse_args()

    if args.mode == "install":
        require(args.package_root, "--package-root is required for install")
        report = install_protocol(Path(args.package_root))
        print("=" * 104)
        print("FLIP FLOP STAGE 3H.4 - FORWARD BLACK BOX INSTALL")
        print("=" * 104)
        print("STATUS: PASS")
        print(f"Install status: {report['install_status']}")
        print(f"Protocol hash: {report['protocol_hash']}")
        print(f"Eligible after UTC: {report['eligible_after_utc']}")
        if report["next_session"]:
            n = report["next_session"]
            print("")
            print("NEXT ELIGIBLE SESSION")
            print(f"Passport: {n['passport']}")
            print(f"Entry ET: {n['scheduled_entry_et']}")
            print(f"Capture ID: {n['capture_id']}")
        print("")
        print(f"Forward raw inbox: {report['inbox']}")
        print("NO DATA DOWNLOAD")
        print("NO ORDERS")
        print("NO PINE CHANGE")
        print("NO STAGE 4E CHANGE")
        print("NO QUANTITY CHANGE")
        print("LIVE ROUTING LOCKED")
        print("=" * 104)
        return

    if args.mode == "score":
        report = run_scorer()
        print("=" * 104)
        print("FLIP FLOP STAGE 3H.4 - LOCAL FORWARD SCORER")
        print("=" * 104)
        print("STATUS: PASS")
        for k, v in report.items():
            print(f"{k}: {v}")
        print("=" * 104)
        return

    if args.mode == "status":
        print(status_report())
        return

    if args.mode == "register-task":
        report = register_task()
        print(json.dumps(report, indent=2))
        if report["status"] != "PASS":
            sys.exit(1)
        return

    if args.mode == "remove-task":
        report = remove_task()
        print(json.dumps(report, indent=2))
        if report["status"] != "PASS":
            sys.exit(1)
        return


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print("STAGE 3H.4 FORWARD BLACK BOX - FAILED")
        print(type(exc).__name__ + ": " + str(exc))
        sys.exit(1)
