#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, re, sys, traceback
from datetime import datetime
from pathlib import Path

HQ = Path(os.environ.get("FF_HQ", r"C:\FLIP_FLOP_HQ"))
REPORT_DIR = HQ / r"06_REPORTS\forensic\x10_3a_data_scout"
STATE_DIR = REPORT_DIR / "state"

TARGET_ROOTS = [
    HQ / r"01_INBOX\market_data\raw",
    HQ / r"02_VALIDATED\market_data\GIVEBACK_BLOCKS_2025",
    HQ / r"02_VALIDATED\market_data\COVID_2020_03_16\surgical",
]
EXTS = {
    ".csv",".parquet",".pq",".feather",".arrow",".dbn",".zst",
    ".gz",".json",".jsonl"
}
TBBO_HINTS = {
    "ts_event","ts_recv","sequence","bid_px_00","ask_px_00",
    "bid_sz_00","ask_sz_00","price","size","action","side"
}

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def human_bytes(n: int) -> str:
    units=["B","KB","MB","GB","TB"]
    x=float(n)
    for u in units:
        if x<1024 or u=="TB": return f"{x:,.2f} {u}"
        x/=1024

def count_lines_fast(path: Path) -> int:
    n=0
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            n += block.count(b"\n")
    return n

def read_header(path: Path):
    try:
        with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
            r=csv.reader(f)
            return next(r,[])
    except Exception:
        return []

def first_last_csv_rows(path: Path, header):
    first=None; last=None
    try:
        with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
            dr=csv.DictReader(f)
            for i,row in enumerate(dr):
                if i==0: first=row
                last=row
        return first,last
    except Exception:
        return None,None

def parse_time(x):
    if x is None: return None
    s=str(x).strip()
    if not s: return None
    # Databento and ISO-ish formats
    try:
        if s.endswith("Z"): s=s[:-1]+"+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        pass
    # numeric ns/us/ms/s epochs
    try:
        v=float(s)
        av=abs(v)
        if av>1e17: v/=1e9
        elif av>1e14: v/=1e6
        elif av>1e11: v/=1e3
        return datetime.fromtimestamp(v)
    except Exception:
        return None

def extract_time(row):
    if not row: return None
    for k in ("ts_event","ts_recv","timestamp","datetime","Date and time","time"):
        if k in row and row[k]:
            t=parse_time(row[k])
            if t: return t
    return None

def detect_date_tokens(name: str):
    pats=[
        r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})",
        r"(20\d{2})[-_](\d{2})",
    ]
    out=[]
    for p in pats:
        for m in re.finditer(p,name):
            out.append("-".join(m.groups()))
    return out[:4]

def classify(path: Path, header):
    low=path.name.lower()
    joined=" ".join(x.lower() for x in header)
    if path.suffix.lower()==".dbn" or ".dbn." in low or ("dbn" in low and low.endswith(".zst")):
        return "DBN_HIGH_DETAIL"
    if "tbbo" in low:
        return "TBBO_HIGH_DETAIL"
    hits=sum(1 for h in TBBO_HINTS if h.lower() in joined)
    if path.suffix.lower()==".csv" and hits>=6:
        return "TBBO_LIKE_CSV"
    if path.suffix.lower() in (".parquet",".pq",".feather",".arrow"):
        return "COLUMNAR_MARKET_DATA"
    if "market" in str(path).lower():
        return "MARKET_DATA_OTHER"
    return "OTHER"

def inspect_parquet(path: Path):
    info={"rows":"","columns":"","schema_error":""}
    try:
        import pyarrow.parquet as pq
        pf=pq.ParquetFile(path)
        info["rows"]=pf.metadata.num_rows
        info["columns"]="|".join(pf.schema.names)
    except Exception as e:
        info["schema_error"]=str(e)[:180]
    return info

def inspect_dbn(path: Path):
    # Metadata-only best effort. No huge conversion.
    info={"dbn_schema":"","dbn_start":"","dbn_end":"","dbn_error":""}
    try:
        import databento as db
        store=db.DBNStore.from_file(path)
        meta=getattr(store,"metadata",None)
        if meta is not None:
            for attr,key in [("schema","dbn_schema"),("start","dbn_start"),("end","dbn_end")]:
                v=getattr(meta,attr,None)
                if v is not None: info[key]=str(v)
    except Exception as e:
        info["dbn_error"]=str(e)[:180]
    return info

def discover_roots():
    roots=[]
    for r in TARGET_ROOTS:
        if r.exists():
            roots.append(r)
    # Add any other market_data directories without scanning report/tool trees.
    for base in [HQ/"01_INBOX",HQ/"02_VALIDATED",HQ/"03_RESEARCH",HQ/"04_STAGE",HQ/"05_DATA"]:
        if not base.exists(): continue
        try:
            for p in base.rglob("*"):
                if p.is_dir() and p.name.lower()=="market_data" and p not in roots:
                    roots.append(p)
        except Exception:
            pass
    # dedupe nested exact paths
    seen=set(); clean=[]
    for r in roots:
        s=str(r.resolve()).lower()
        if s not in seen:
            seen.add(s); clean.append(r)
    return clean

def inventory():
    roots=discover_roots()
    files=[]
    for r in roots:
        try:
            for p in r.rglob("*"):
                if not p.is_file(): continue
                low=p.name.lower()
                if p.suffix.lower() in EXTS or ".dbn." in low:
                    files.append(p)
        except Exception:
            continue
    # exact dedupe by path
    uniq=[]; seen=set()
    for p in files:
        s=str(p.resolve()).lower()
        if s not in seen:
            seen.add(s); uniq.append(p)
    files=sorted(uniq,key=lambda p:str(p).lower())

    records=[]
    hash_groups={}
    for idx,p in enumerate(files,1):
        rec={
            "path":str(p),"name":p.name,"size_bytes":p.stat().st_size,
            "size_human":human_bytes(p.stat().st_size),
            "mtime":datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            "sha256":"","classification":"","csv_rows":"","columns":"",
            "first_time":"","last_time":"","date_tokens":"|".join(detect_date_tokens(p.name)),
            "integrity_status":"PASS","notes":""
        }
        try:
            rec["sha256"]=sha256_file(p)
            hash_groups.setdefault(rec["sha256"],[]).append(str(p))
        except Exception as e:
            rec["integrity_status"]="FAIL"
            rec["notes"] += f"HASH_ERROR:{e};"

        header=[]
        if p.suffix.lower()==".csv":
            header=read_header(p)
            rec["columns"]="|".join(header)
        rec["classification"]=classify(p,header)

        try:
            if p.stat().st_size==0:
                rec["integrity_status"]="FAIL"
                rec["notes"]+="ZERO_BYTE;"
            elif p.suffix.lower()==".csv":
                lines=count_lines_fast(p)
                rec["csv_rows"]=max(0,lines-1)
                first,last=first_last_csv_rows(p,header)
                ft=extract_time(first); lt=extract_time(last)
                rec["first_time"]=ft.isoformat() if ft else ""
                rec["last_time"]=lt.isoformat() if lt else ""
                if ft and lt and lt<ft:
                    rec["integrity_status"]="FAIL"
                    rec["notes"]+="END_BEFORE_START;"
            elif p.suffix.lower() in (".parquet",".pq"):
                q=inspect_parquet(p)
                if q["rows"]!="": rec["csv_rows"]=q["rows"]
                if q["columns"]: rec["columns"]=q["columns"]
                if q["schema_error"]: rec["notes"]+="PARQUET_META:"+q["schema_error"]+";"
            elif rec["classification"]=="DBN_HIGH_DETAIL":
                q=inspect_dbn(p)
                if q["dbn_schema"]: rec["notes"]+=f"DBN_SCHEMA:{q['dbn_schema']};"
                if q["dbn_start"]: rec["first_time"]=q["dbn_start"]
                if q["dbn_end"]: rec["last_time"]=q["dbn_end"]
                if q["dbn_error"]: rec["notes"]+="DBN_META:"+q["dbn_error"]+";"
        except Exception as e:
            rec["notes"]+=f"INSPECT_ERROR:{e};"

        records.append(rec)

    dup_hashes={h:ps for h,ps in hash_groups.items() if h and len(ps)>1}
    for rec in records:
        if rec["sha256"] in dup_hashes:
            rec["notes"]+="DUPLICATE_CONTENT;"
    return roots,records,dup_hashes

def agent_manifest():
    return [
        ("DATA_SCOUT","ACTIVE","filesystem/schema/date/hash inventory"),
        ("INTEGRITY_SCANNER","ACTIVE","zero-byte/hash/duplicate/basic time sanity"),
        ("CLOCK_AUDITOR","ARMED_NEXT","ordered timestamp/session-anchor validation"),
        ("BOOK_RECONSTRUCTOR","ARMED_NEXT","ordered bid/ask/depth state"),
        ("FILL_ENGINE","ARMED_NEXT","Q1-Q10 VWAP/partial-fill simulation"),
        ("LATENCY_SCANNER","ARMED_NEXT","+25/+50/+100/+250/+500ms replay"),
        ("CAPACITY_BEND","ARMED_NEXT","nonlinear Q deterioration detector"),
        ("SIGNAL_SCALE_AGENT","ARMED_NEXT","Current/Core-Tier/Signal-Scale footprint compare"),
        ("TOXICITY_AGENT","ARMED_NEXT","spread/depth/velocity/structure quality score"),
        ("ANOMALY_HUNTER","ARMED_NEXT","worst depth/spread/gap/fill divergence"),
        ("RED_TEAM","ARMED_NEXT","depth haircuts/latency/spread shock"),
        ("GOVERNOR","ACTIVE","no Pine changes/no live authority"),
    ]

def main():
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    roots,records,dups=inventory()

    inv=REPORT_DIR/"X10_3A_DATA_INVENTORY.csv"
    fields=list(records[0].keys()) if records else [
        "path","name","size_bytes","size_human","mtime","sha256","classification",
        "csv_rows","columns","first_time","last_time","date_tokens","integrity_status","notes"
    ]
    with inv.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in records:w.writerow(r)

    total_bytes=sum(r["size_bytes"] for r in records)
    high=[r for r in records if r["classification"] in ("DBN_HIGH_DETAIL","TBBO_HIGH_DETAIL","TBBO_LIKE_CSV","COLUMNAR_MARKET_DATA")]
    tbbo=[r for r in records if r["classification"] in ("DBN_HIGH_DETAIL","TBBO_HIGH_DETAIL","TBBO_LIKE_CSV")]
    csv_tbbo=[r for r in records if r["classification"]=="TBBO_LIKE_CSV"]
    known_rows=sum(int(r["csv_rows"]) for r in records if str(r["csv_rows"]).isdigit())
    fails=[r for r in records if r["integrity_status"]=="FAIL"]
    roots_found=len(roots)

    starts=[]; ends=[]
    for r in records:
        try:
            if r["first_time"]: starts.append(parse_time(r["first_time"]) if False else r["first_time"])
            if r["last_time"]: ends.append(r["last_time"])
        except Exception: pass
    first_known=min(starts) if starts else "UNKNOWN"
    last_known=max(ends) if ends else "UNKNOWN"

    # Agent manifest CSV
    agent_csv=REPORT_DIR/"X10_3A_ALGORITHM_AGENT_MANIFEST.csv"
    with agent_csv.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["agent","state","job"]);w.writerows(agent_manifest())

    txt=REPORT_DIR/"X10_3A_DATA_SCOUT_SUMMARY.txt"
    lines=[
        "="*120,
        "FLIP FLOP X10.3A DATA SCOUT + INTEGRITY SCANNER + ALGORITHM-AGENT SHELL",
        "="*120,
        "STATUS: PASS",
        "",
        "NUMERIC SUMMARY",
        f"Market-data roots found:          {roots_found}",
        f"Candidate files found:            {len(records)}",
        f"High-detail/columnar candidates:   {len(high)}",
        f"TBBO/DBN candidates:               {len(tbbo)}",
        f"TBBO-like CSV candidates:          {len(csv_tbbo)}",
        f"Known inspectable event/data rows: {known_rows:,}",
        f"Total candidate bytes:             {total_bytes:,} ({human_bytes(total_bytes)})",
        f"Duplicate-content hash groups:     {len(dups)}",
        f"Integrity hard failures:           {len(fails)}",
        f"First known timestamp:             {first_known}",
        f"Last known timestamp:              {last_known}",
        "",
        "ROOTS",
    ]
    for r in roots: lines.append(f"  {r}")
    if not roots: lines.append("  NONE FOUND")
    lines += ["","CLASSIFICATION COUNTS"]
    counts={}
    for r in records: counts[r["classification"]]=counts.get(r["classification"],0)+1
    for k in sorted(counts): lines.append(f"  {k:<28} {counts[k]}")
    lines += ["","ALGORITHM / SCANNER AGENTS"]
    for a,state,job in agent_manifest():
        lines.append(f"  {a:<22} {state:<11} {job}")
    lines += [
        "",
        "READINESS",
        f"DATA_DISCOVERY:                  {'PASS' if records else 'WAIT'}",
        f"HIGH_DETAIL_DISCOVERY:           {'PASS' if high else 'WAIT'}",
        f"TBBO_DISCOVERY:                  {'PASS' if tbbo else 'WAIT'}",
        f"INTEGRITY_NO_HARD_FAILURES:      {'PASS' if not fails else 'REVIEW'}",
        "",
        "GOVERNANCE",
        "Frozen V3.6.72 modified: NO",
        "X10.2 forward championship modified: NO",
        "Entry/exit logic modified: NO",
        "Live routing: LOCKED",
        "X10.3A authority: INVENTORY / FORENSIC RESEARCH ONLY",
        "",
        "NEXT NUMERIC OUTPUT AFTER THIS SCOUT",
        "X10.3B will only be built against files this scout proves exist.",
        "Targets: Q1-Q10 fill tax, edge retention, latency sensitivity, route capacity,",
        "Signal-Scale footprint advantage, capacity-bend quantity, and red-team survival.",
        "="*120
    ]
    txt.write_text("\n".join(lines),encoding="utf-8")

    # JSON machine state
    state={
        "status":"PASS","roots":[str(x) for x in roots],
        "candidate_files":len(records),"high_detail_candidates":len(high),
        "tbbo_candidates":len(tbbo),"known_rows":known_rows,
        "bytes":total_bytes,"duplicate_groups":len(dups),"hard_failures":len(fails),
        "frozen_v3672_modified":False,"x10_2_modified":False,"live_routing":"LOCKED"
    }
    (STATE_DIR/"X10_3A_STATE.json").write_text(json.dumps(state,indent=2),encoding="utf-8")

    print("="*88)
    print("FLIP FLOP X10.3A DATA SCOUT")
    print("STATUS: PASS")
    print(f"Market-data roots found: {roots_found}")
    print(f"Candidate files: {len(records)}")
    print(f"High-detail candidates: {len(high)}")
    print(f"TBBO/DBN candidates: {len(tbbo)}")
    print(f"Known rows: {known_rows:,}")
    print(f"Total data: {human_bytes(total_bytes)}")
    print(f"Duplicate hash groups: {len(dups)}")
    print(f"Integrity hard failures: {len(fails)}")
    print("Frozen V3.6.72 modified: NO")
    print("X10.2 modified: NO")
    print("Live routing: LOCKED")
    print(f"Report: {txt}")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("STATUS: FAIL",file=sys.stderr)
        print(str(e),file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
