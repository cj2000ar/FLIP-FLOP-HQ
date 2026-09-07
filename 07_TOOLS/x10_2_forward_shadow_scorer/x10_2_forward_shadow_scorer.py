#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, math, os, sys, traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

EXPECTED_PROTOCOL_SHA256 = "F14D59DB4F401E7E7A275249D2F50BBB4231669D8D9FBE93DA085387C865D23B"
EXPECTED_SYNC = "PAP-FWD-S2W1-S100-W80-P80-K80-R06"
CUTOFF = datetime.fromisoformat("2026-08-08T00:08:00-04:00")
ET = ZoneInfo("America/New_York")
ALPHAS = (0.00, 0.10, 0.25, 0.35, 0.50, 0.75)
CHALLENGERS = ("A_CURRENT", "B_CORE_TIER", "C_SIGNAL_SCALE")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def parse_dt(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ET)
    return dt.astimezone(ET)

def route_from_signal(sig: str) -> str:
    u = sig.upper()
    if "WEEKLY" in u:
        return "WEEKLY"
    if "PREMIUM" in u:
        return "PREMIUM"
    if "WEAK" in u:
        return "WEAK"
    if " NY" in u or "NY|" in u:
        return "NY"
    return "OTHER"

def side_from_signal(sig: str) -> str | None:
    u = sig.upper()
    if "[CC] BUY " in u:
        return "BUY"
    if "[CC] SELL " in u:
        return "SELL"
    return None

def sync_from_signal(sig: str) -> str | None:
    if "|" not in sig:
        return None
    return sig.split("|", 1)[1].strip()

@dataclass(frozen=True)
class Entry:
    trade_no: int
    ts: datetime
    route: str
    side: str
    sync: str
    qty: float
    pnl: float
    unit_pnl: float

@dataclass
class Candidate:
    path: Path
    side: str
    sync: str
    entries: list[Entry]
    mtime: float

REQUIRED = {"Trade number","Type","Date and time","Signal","Size (qty)","Net PnL USD"}

def parse_candidate(path: Path) -> Candidate | None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
                return None
            entries = []
            sides = set()
            syncs = set()
            for row in reader:
                if not str(row.get("Type","")).startswith("Entry"):
                    continue
                sig = str(row.get("Signal",""))
                side = side_from_signal(sig)
                sync = sync_from_signal(sig)
                if not side or not sync:
                    continue
                qty = abs(float(row["Size (qty)"]))
                if qty <= 0:
                    raise ValueError(f"Non-positive entry qty in {path.name}")
                pnl = float(row["Net PnL USD"])
                ts = parse_dt(row["Date and time"])
                route = route_from_signal(sig)
                entries.append(Entry(
                    trade_no=int(float(row["Trade number"])),
                    ts=ts, route=route, side=side, sync=sync,
                    qty=qty, pnl=pnl, unit_pnl=pnl/qty
                ))
                sides.add(side); syncs.add(sync)
        if not entries or len(sides) != 1 or len(syncs) != 1:
            return None
        entries.sort(key=lambda e: (e.ts, e.trade_no))
        return Candidate(path, next(iter(sides)), next(iter(syncs)), entries, path.stat().st_mtime)
    except Exception:
        return None

def choose_pair(downloads: Path) -> tuple[Candidate, Candidate]:
    files = sorted(downloads.glob("*.csv"))
    cands = [c for p in files if (c := parse_candidate(p)) is not None]
    buys = [c for c in cands if c.side == "BUY" and c.sync == EXPECTED_SYNC]
    sells = [c for c in cands if c.side == "SELL" and c.sync == EXPECTED_SYNC]
    pairs = []
    for b in buys:
        bkeys = [(e.ts, e.route) for e in b.entries]
        for s in sells:
            if len(b.entries) != len(s.entries):
                continue
            skeys = [(e.ts, e.route) for e in s.entries]
            if bkeys != skeys:
                continue
            score = (b.entries[-1].ts, len(b.entries), min(b.mtime, s.mtime))
            pairs.append((score, b, s))
    if not pairs:
        detail = []
        for c in sorted(cands, key=lambda x: x.mtime, reverse=True)[:12]:
            detail.append(f"{c.side} {c.path.name} sync={c.sync} n={len(c.entries)} last={c.entries[-1].ts.isoformat()}")
        raise RuntimeError(
            "No exact synchronized BUY/SELL export pair found in Downloads.\n" +
            ("\n".join(detail) if detail else "No recognizable FLIP FLOP CSV exports found.")
        )
    pairs.sort(key=lambda x: x[0], reverse=True)
    _, b, s = pairs[0]
    return b, s

def pair_rows(b: Candidate, s: Candidate) -> list[dict]:
    out = []
    for be, se in zip(b.entries, s.entries):
        if be.ts != se.ts or be.route != se.route:
            raise RuntimeError("BUY/SELL timestamp or route mismatch.")
        if be.sync != se.sync or be.sync != EXPECTED_SYNC:
            raise RuntimeError("Sync mismatch.")
        out.append({
            "entry_time_et": be.ts.isoformat(),
            "route": be.route,
            "sync": be.sync,
            "buy_unit_pnl": be.unit_pnl,
            "sell_unit_pnl": se.unit_pnl,
            "buy_native_qty": be.qty,
            "sell_native_qty": se.qty,
            "buy_trade_no": be.trade_no,
            "sell_trade_no": se.trade_no,
        })
    return out

LEDGER_FIELDS = [
    "entry_time_et","route","sync","buy_unit_pnl","sell_unit_pnl",
    "buy_native_qty","sell_native_qty","buy_trade_no","sell_trade_no"
]

def key_of(r: dict) -> tuple[str,str]:
    return (r["entry_time_et"], r["route"])

def load_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("buy_unit_pnl","sell_unit_pnl","buy_native_qty","sell_native_qty"):
            r[k] = float(r[k])
        for k in ("buy_trade_no","sell_trade_no"):
            r[k] = int(float(r[k]))
    return rows

def write_ledger(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k:r[k] for k in LEDGER_FIELDS})
    tmp.replace(path)

def reconcile_ledger(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], int]:
    old = {key_of(r): r for r in existing}
    new = {key_of(r): r for r in incoming}
    if len(new) != len(incoming):
        raise RuntimeError("Duplicate forward session key detected in incoming exports.")
    for k, r in old.items():
        if k not in new:
            raise RuntimeError(f"FORWARD LEDGER GAP: previously recorded session missing from newest full export: {k}")
        nr = new[k]
        if nr["sync"] != r["sync"]:
            raise RuntimeError(f"FORWARD MUTATION: sync changed for {k}")
        if abs(float(nr["buy_unit_pnl"]) - float(r["buy_unit_pnl"])) > 0.005:
            raise RuntimeError(f"FORWARD MUTATION: BUY unit PnL changed for {k}")
        if abs(float(nr["sell_unit_pnl"]) - float(r["sell_unit_pnl"])) > 0.005:
            raise RuntimeError(f"FORWARD MUTATION: SELL unit PnL changed for {k}")
    added = len(set(new) - set(old))
    merged = sorted(incoming, key=lambda r: r["entry_time_et"])
    return merged, added

def quantities(ch: str, route: str, q: int) -> tuple[int,int]:
    if ch == "A_CURRENT":
        if route in ("NY","WEEKLY","PREMIUM"):
            return q,q
        if route == "WEAK":
            return 1,1
        return 0,0
    if ch == "B_CORE_TIER":
        if route in ("NY","WEEKLY"):
            return q,q
        if route == "PREMIUM":
            return 1,1
        return 0,0
    if ch == "C_SIGNAL_SCALE":
        if route == "NY":
            return 1,q
        if route == "WEEKLY":
            return q,1
        if route == "PREMIUM":
            return q,1
        if route == "WEAK":
            return 1,1
        return 0,0
    raise ValueError(ch)

def scenario_values(rows: list[dict], ch: str, q: int, alpha: float) -> list[float]:
    vals = []
    for r in rows:
        bq, sq = quantities(ch, r["route"], q)
        base = float(r["buy_unit_pnl"])*bq + float(r["sell_unit_pnl"])*sq
        bticks = alpha * max(bq-1, 0)
        sticks = alpha * max(sq-1, 0)
        drag = 10.0 * (bq*bticks + sq*sticks)  # entry+exit, $5/tick/contract
        vals.append(base - drag)
    return vals

def metrics(vals: list[float]) -> dict:
    n = len(vals)
    if not n:
        return {"n":0,"net":0.0,"pf":None,"dd":0.0,"worst":None,"best":None,
                "roll25":None,"roll50":None,"roll100":None}
    gp = sum(v for v in vals if v > 0)
    gl = sum(v for v in vals if v < 0)
    pf = gp/abs(gl) if gl < 0 else math.inf
    eq = peak = 0.0
    dd = 0.0
    for v in vals:
        eq += v
        peak = max(peak, eq)
        dd = min(dd, eq-peak)
    def worst_roll(k):
        if n < k:
            return None
        cur = sum(vals[:k]); worst = cur
        for i in range(k, n):
            cur += vals[i] - vals[i-k]
            worst = min(worst, cur)
        return worst
    return {
        "n":n,"net":sum(vals),"pf":pf,"dd":-dd,
        "worst":min(vals),"best":max(vals),
        "roll25":worst_roll(25),"roll50":worst_roll(50),"roll100":worst_roll(100)
    }

def fmt_money(x):
    return "N/A" if x is None else f"${x:,.2f}"
def fmt_pf(x):
    if x is None: return "N/A"
    if math.isinf(x): return "INF"
    return f"{x:.3f}"
def fmt_num(x):
    return "N/A" if x is None else f"{x:,.2f}"

def write_scenario_csv(path: Path, rows: list[dict]) -> None:
    fields = ["challenger","Q","alpha","sessions","net","PF","closed_DD","worst_session","best_session",
              "worst_roll25","worst_roll50","worst_roll100"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for ch in CHALLENGERS:
            for q in range(1,7):
                for a in ALPHAS:
                    m = metrics(scenario_values(rows,ch,q,a))
                    w.writerow({
                        "challenger":ch,"Q":q,"alpha":f"{a:.2f}","sessions":m["n"],
                        "net":f"{m['net']:.2f}",
                        "PF":"" if m["pf"] is None else ("INF" if math.isinf(m["pf"]) else f"{m['pf']:.6f}"),
                        "closed_DD":f"{m['dd']:.2f}",
                        "worst_session":"" if m["worst"] is None else f"{m['worst']:.2f}",
                        "best_session":"" if m["best"] is None else f"{m['best']:.2f}",
                        "worst_roll25":"" if m["roll25"] is None else f"{m['roll25']:.2f}",
                        "worst_roll50":"" if m["roll50"] is None else f"{m['roll50']:.2f}",
                        "worst_roll100":"" if m["roll100"] is None else f"{m['roll100']:.2f}",
                    })

def write_snapshot(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS); w.writeheader()
        for r in rows:
            w.writerow({k:r[k] for k in LEDGER_FIELDS})

def report_text(protocol: Path, b: Candidate, s: Candidate, ledger: list[dict], added: int) -> str:
    counts = {r:0 for r in ("NY","WEEKLY","PREMIUM","WEAK","OTHER")}
    for x in ledger:
        counts[x["route"]] = counts.get(x["route"],0)+1
    lines = [
        "="*124,
        "FLIP FLOP X10.2 FROZEN FORWARD SHADOW SCORE",
        "="*124,
        "ENGINE STATUS: PASS",
        f"FORWARD STATUS: {'ACTIVE' if ledger else 'WAITING_FOR_FORWARD_SESSIONS'}",
        f"Protocol SHA256: {sha256_file(protocol)}",
        f"Freeze cutoff: {CUTOFF.isoformat()}",
        "Authority rule: entry timestamp must be STRICTLY AFTER cutoff.",
        "",
        f"BUY source:  {b.path}",
        f"BUY SHA256:  {sha256_file(b.path)}",
        f"SELL source: {s.path}",
        f"SELL SHA256: {sha256_file(s.path)}",
        f"SYNC: {EXPECTED_SYNC}",
        f"BUY/SELL full-export sessions aligned: {len(b.entries)}",
        f"Latest full-export session: {b.entries[-1].ts.isoformat()}",
        "",
        f"Cumulative eligible forward sessions: {len(ledger)}",
        f"New sessions added this run: {added}",
        f"Route coverage: NY={counts.get('NY',0)} | WEEKLY={counts.get('WEEKLY',0)} | PREMIUM={counts.get('PREMIUM',0)} | WEAK={counts.get('WEAK',0)}",
        "",
        "SIGNAL MAP — FROZEN",
        "NY=SELL | WEEKLY=BUY | PREMIUM=BUY | WEAK=NO DIRECTIONAL SCALING",
        "",
        "CHALLENGERS",
        "A_CURRENT:      NY/WEEKLY/PREMIUM both sides Q; WEAK 1/1",
        "B_CORE_TIER:    NY/WEEKLY both sides Q; PREMIUM 1/1; WEAK skipped",
        "C_SIGNAL_SCALE: NY 1/Q(SELL); WEEKLY Q(BUY)/1; PREMIUM Q(BUY)/1; WEAK 1/1",
        "",
        "BASELINE FORWARD SCORE — ALPHA 0.00",
    ]
    for ch in CHALLENGERS:
        lines.append(ch)
        for q in range(1,7):
            m = metrics(scenario_values(ledger,ch,q,0.0))
            lines.append(
                f"  Q{q} | Net {fmt_money(m['net']):>14} | PF {fmt_pf(m['pf']):>7} | "
                f"Closed-DD {fmt_money(m['dd']):>12} | Worst {fmt_money(m['worst']):>11} | "
                f"R25 {fmt_money(m['roll25']):>11} | R50 {fmt_money(m['roll50']):>11} | R100 {fmt_money(m['roll100']):>11}"
            )
    lines += ["", "Q6 HOSTILE COMPARISON — SIZE-DEPENDENT EXECUTION STRESS"]
    for a in ALPHAS:
        lines.append(f"alpha {a:.2f} tick/fill per added contract")
        for ch in CHALLENGERS:
            m = metrics(scenario_values(ledger,ch,6,a))
            lines.append(
                f"  {ch:<15} Net {fmt_money(m['net']):>14} | PF {fmt_pf(m['pf']):>7} | DD {fmt_money(m['dd']):>12}"
            )
    lines += [
        "",
        "GOVERNANCE",
        "Frozen V3.6.72 modified: NO",
        "Pine promotion: BLOCKED",
        "Capacity live routing: LOCKED",
        "Historical rows at/before cutoff: EXCLUDED",
        "Forward ledger: APPEND-ONLY; missing/mutated prior forward rows cause a hard failure.",
        "",
        "IMPORTANT",
        "This scorer has NO authority to declare a winner or authorize quantity.",
        "The frozen protocol did not define a minimum forward sample or promotion threshold.",
        "It records forward evidence only. Any promotion protocol must be frozen separately before it can judge these results.",
        "="*124
    ]
    return "\n".join(lines)

def self_test() -> None:
    fake = [
        {"route":"NY","buy_unit_pnl":10.0,"sell_unit_pnl":20.0},
        {"route":"WEEKLY","buy_unit_pnl":30.0,"sell_unit_pnl":-5.0},
        {"route":"PREMIUM","buy_unit_pnl":8.0,"sell_unit_pnl":2.0},
        {"route":"WEAK","buy_unit_pnl":1.0,"sell_unit_pnl":-1.0},
    ]
    assert quantities("C_SIGNAL_SCALE","NY",6) == (1,6)
    assert quantities("C_SIGNAL_SCALE","WEEKLY",6) == (6,1)
    assert quantities("C_SIGNAL_SCALE","PREMIUM",6) == (6,1)
    assert quantities("C_SIGNAL_SCALE","WEAK",6) == (1,1)
    v0 = scenario_values(fake,"C_SIGNAL_SCALE",6,0.0)
    v1 = scenario_values(fake,"C_SIGNAL_SCALE",6,0.35)
    assert len(v0)==4 and sum(v1) < sum(v0)
    m = metrics(v0)
    assert m["n"]==4 and m["net"] == sum(v0)
    print("SELF-TEST: PASS")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0

    hq = Path(os.environ.get("FF_HQ", r"C:\FLIP_FLOP_HQ"))
    downloads = Path(os.environ.get("FF_DOWNLOADS", str(Path.home()/"Downloads")))
    protocol = Path(os.environ.get(
        "FF_PROTOCOL",
        str(hq/r"06_REPORTS\forensic\x10_2_forward_shadow\X10_2_FROZEN_FORWARD_PROTOCOL.txt")
    ))
    base = hq/r"06_REPORTS\forensic\x10_2_forward_shadow"
    runs = base/"runs"
    state = base/"state"
    runs.mkdir(parents=True, exist_ok=True); state.mkdir(parents=True, exist_ok=True)

    if not protocol.exists():
        raise RuntimeError(f"Frozen protocol missing: {protocol}")
    got = sha256_file(protocol)
    if got != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(
            f"PROTOCOL HASH FAIL\nExpected: {EXPECTED_PROTOCOL_SHA256}\nActual:   {got}\n"
            "Scoring refused. Do not edit the frozen protocol."
        )

    b, s = choose_pair(downloads)
    rows = pair_rows(b,s)
    eligible = [r for r in rows if parse_dt(r["entry_time_et"]) > CUTOFF]

    ledger_path = state/"X10_2_APPEND_ONLY_FORWARD_LEDGER.csv"
    existing = load_ledger(ledger_path)
    ledger, added = reconcile_ledger(existing, eligible)
    write_ledger(ledger_path, ledger)

    stamp = datetime.now(ET).strftime("%Y%m%d_%H%M%S")
    scenario_path = runs/f"X10_2_FORWARD_SCENARIOS_{stamp}.csv"
    snapshot_path = runs/f"X10_2_FORWARD_LEDGER_SNAPSHOT_{stamp}.csv"
    report_path = runs/f"X10_2_FORWARD_SCORE_{stamp}.txt"
    write_scenario_csv(scenario_path, ledger)
    write_snapshot(snapshot_path, ledger)
    report_path.write_text(report_text(protocol,b,s,ledger,added), encoding="utf-8")

    latest = base/"LATEST_X10_2_FORWARD_SCORE.txt"
    latest.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print("="*88)
    print("FLIP FLOP X10.2 FORWARD SHADOW SCORER")
    print("ENGINE STATUS: PASS")
    print(f"FORWARD STATUS: {'ACTIVE' if ledger else 'WAITING_FOR_FORWARD_SESSIONS'}")
    print(f"Protocol SHA256: {got}")
    print(f"Eligible forward sessions: {len(ledger)}")
    print(f"New sessions this run: {added}")
    print(f"Report: {report_path}")
    print(f"Ledger: {ledger_path}")
    print("Frozen V3.6.72 modified: NO")
    print("Live routing: LOCKED")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("ENGINE STATUS: FAIL", file=sys.stderr)
        print(str(e), file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
