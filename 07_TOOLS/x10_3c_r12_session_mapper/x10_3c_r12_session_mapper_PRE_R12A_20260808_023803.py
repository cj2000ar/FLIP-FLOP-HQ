#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, os, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HQ=Path(os.environ.get("FF_HQ", r"C:\FLIP_FLOP_HQ"))
X3C=HQ/r"06_REPORTS\forensic\x10_3c_target_ceiling"
X3B=HQ/r"06_REPORTS\forensic\x10_3b_quant_core\runs"
BASE=X3C/r"r12_session_mapper"
RUNS=BASE/"runs"
STATE=BASE/"state"
NY=ZoneInfo("America/New_York")

def latest(pattern,folder):
    xs=sorted(folder.glob(pattern),key=lambda p:p.stat().st_mtime,reverse=True)
    return xs[0] if xs else None

def pct(a,b): return 100*a/b if b else None
def fmt(x,d=2):
    if x is None or (isinstance(x,float) and not math.isfinite(x)): return "N/A"
    return f"{x:,.{d}f}"

def main():
    BASE.mkdir(parents=True,exist_ok=True);RUNS.mkdir(parents=True,exist_ok=True);STATE.mkdir(parents=True,exist_ok=True)
    target_file=latest("X10_3C_TARGET_WINNERS_*.csv",X3C/"runs")
    audit_file=latest("X10_3B_FILE_SCHEMA_AUDIT_*.csv",X3B)
    if not target_file: raise RuntimeError("No X10.3C target-winner CSV found. Run X10.3C-R1.1 first.")
    if not audit_file: raise RuntimeError("No X10.3B file-schema audit found. Run X10.3B first.")

    t=pd.read_csv(target_file)
    a=pd.read_csv(audit_file)

    # Authority rows with real event windows.
    a["authority_rank"]=pd.to_numeric(a["authority_rank"],errors="coerce").fillna(0).astype(int)
    a["start_utc"]=pd.to_datetime(a["start_utc"],utc=True,errors="coerce")
    a["end_utc"]=pd.to_datetime(a["end_utc"],utc=True,errors="coerce")
    a=a[(a["decode_status"].astype(str)=="PASS")&(a["authority_rank"]>=2)&a["start_utc"].notna()&a["end_utc"].notna()].copy()
    if not len(a): raise RuntimeError("No rank>=2 high-detail event windows with valid timestamps in X10.3B audit.")

    a["start_et"]=a["start_utc"].dt.tz_convert("America/New_York")
    a["end_et"]=a["end_utc"].dt.tz_convert("America/New_York")
    a["local_date_start"]=a["start_et"].dt.date.astype(str)
    a["local_date_end"]=a["end_et"].dt.date.astype(str)

    # TradingView exports use bar labels. Treat them as ET session anchors, not exact target-hit timestamps.
    t["entry_dt"]=pd.to_datetime(t["entry_dt"],errors="coerce")
    t["exit_dt"]=pd.to_datetime(t["exit_dt"],errors="coerce")
    rows=[]
    for _,r in t.iterrows():
        if pd.isna(r["entry_dt"]): continue
        entry_naive=r["entry_dt"].to_pydatetime()
        anchor_et=pd.Timestamp(entry_naive.replace(tzinfo=NY))
        anchor_utc=anchor_et.tz_convert("UTC")
        bar_end=anchor_utc+pd.Timedelta(minutes=30)
        plus5=bar_end+pd.Timedelta(minutes=5)
        plus30=bar_end+pd.Timedelta(minutes=30)

        # exact bar overlap
        ov=a[(a["start_utc"]<bar_end)&(a["end_utc"]>anchor_utc)]
        fullbar=a[(a["start_utc"]<=anchor_utc)&(a["end_utc"]>=bar_end)]
        full5=a[(a["start_utc"]<=anchor_utc)&(a["end_utc"]>=plus5)]
        full30=a[(a["start_utc"]<=anchor_utc)&(a["end_utc"]>=plus30)]

        # session-date candidates: file overlaps same ET calendar date around the route anchor.
        day0=anchor_et.normalize()
        day1=day0+pd.Timedelta(days=1)
        datecand=a[(a["start_et"]<day1)&(a["end_et"]>day0)]

        # nearest event-window boundary to anchor, diagnostic only
        nearest=None; nearest_path=""; nearest_start=""; nearest_end=""
        if len(a):
            ds=(a["start_utc"]-anchor_utc).abs()/pd.Timedelta(minutes=1)
            de=(a["end_utc"]-anchor_utc).abs()/pd.Timedelta(minutes=1)
            d=np.minimum(ds.to_numpy(float),de.to_numpy(float))
            j=int(np.argmin(d))
            nearest=float(d[j])
            rr=a.iloc[j]
            nearest_path=str(rr["path"]); nearest_start=str(rr["start_utc"]); nearest_end=str(rr["end_utc"])

        rows.append({
            "side":r.get("side",""),"Trade number":r.get("Trade number",""),
            "route":r.get("route",""),"entry_dt_tv":str(r["entry_dt"]),
            "net":r.get("net",""),"points":r.get("points",""),"at_route_cap":r.get("at_route_cap",""),
            "anchor_et":anchor_et.isoformat(),"anchor_utc":anchor_utc.isoformat(),
            "exact_30m_bar_overlap_files":len(ov),
            "full_30m_bar_files":len(fullbar),
            "full_bar_plus5m_files":len(full5),
            "full_bar_plus30m_files":len(full30),
            "same_et_date_candidate_files":len(datecand),
            "nearest_window_boundary_minutes":nearest,
            "nearest_file":nearest_path,
            "nearest_file_start_utc":nearest_start,
            "nearest_file_end_utc":nearest_end,
        })
    m=pd.DataFrame(rows)

    # Known owned high-detail date blocks, already validated in prior research.
    blocks=[
        ("COVID_2020","2020-03-16","2020-03-19"),
        ("AUG_2025","2025-08-03","2025-08-16"),
        ("SEP_2025","2025-09-14","2025-09-20"),
    ]
    t["entry_ts"]=pd.to_datetime(t["entry_dt"],errors="coerce")
    block_rows=[]
    for name,start,end in blocks:
        g=t[(t["entry_ts"]>=pd.Timestamp(start))&(t["entry_ts"]<pd.Timestamp(end))]
        mg=m[(pd.to_datetime(m["entry_dt_tv"])>=pd.Timestamp(start))&(pd.to_datetime(m["entry_dt_tv"])<pd.Timestamp(end))]
        block_rows.append({
            "block":name,"target_winners":len(g),
            "cap_target_winners":int(pd.Series(g["at_route_cap"]).astype(str).str.lower().eq("true").sum()),
            "with_exact_30m_overlap":int((mg["exact_30m_bar_overlap_files"]>0).sum()) if len(mg) else 0,
            "with_full_30m_bar":int((mg["full_30m_bar_files"]>0).sum()) if len(mg) else 0,
            "with_same_et_date_candidate":int((mg["same_et_date_candidate_files"]>0).sum()) if len(mg) else 0,
        })
    blocks_df=pd.DataFrame(block_rows)

    exact=int((m["exact_30m_bar_overlap_files"]>0).sum())
    full=int((m["full_30m_bar_files"]>0).sum())
    datec=int((m["same_et_date_candidate_files"]>0).sum())

    # Selected 2025 target winner counts
    b25=blocks_df[blocks_df["block"].isin(["AUG_2025","SEP_2025"])]
    owned25_targets=int(b25["target_winners"].sum())
    owned25_caps=int(b25["cap_target_winners"].sum())
    owned25_exact=int(b25["with_exact_30m_overlap"].sum())
    owned25_date=int(b25["with_same_et_date_candidate"].sum())

    # Diagnose mapper outcome.
    if owned25_targets>0 and owned25_exact==0 and owned25_date>0:
        diagnosis="BAR_TIME_JOIN_MISMATCH_LIKELY"
    elif owned25_targets>0 and owned25_exact==0 and owned25_date==0:
        diagnosis="AUDIT_WINDOW_OR_TIMEZONE_MISMATCH_REQUIRES_FILE_LEVEL_REVIEW"
    elif owned25_exact>0:
        diagnosis="OVERLAP_RECOVERED"
    else:
        diagnosis="NO_OWNED_TARGET_WINNERS"

    run=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    map_csv=RUNS/f"X10_3C_R12_TARGET_SESSION_MAP_{run}.csv"
    block_csv=RUNS/f"X10_3C_R12_BLOCK_SUMMARY_{run}.csv"
    auth_csv=RUNS/f"X10_3C_R12_AUTHORITY_WINDOWS_{run}.csv"
    m.to_csv(map_csv,index=False)
    blocks_df.to_csv(block_csv,index=False)
    a[["path","authority_type","authority_label","authority_rank","start_utc","end_utc","start_et","end_et"]].to_csv(auth_csv,index=False)

    txt=RUNS/f"X10_3C_R12_SESSION_MAPPER_SUMMARY_{run}.txt"
    lines=[
        "="*128,
        "FLIP FLOP X10.3C-R1.2 SESSION / HIGH-DETAIL OVERLAP AUDIT",
        "="*128,
        "STATUS: PASS",
        "",
        "WHY R1.2 EXISTS",
        "TradingView Trade List exit times are 30-minute bar labels, not proven exact target-hit event timestamps.",
        "R1.2 maps the ET session anchor to ordered high-detail file windows before any post-target replay is attempted.",
        "",
        "INPUTS",
        f"Target file: {target_file}",
        f"X10.3B audit: {audit_file}",
        f"Rank>=2 authority files/windows: {len(a)}",
        "",
        "OWNED BLOCK TARGET COUNTS",
    ]
    for _,r in blocks_df.iterrows():
        lines.append(
            f"{r['block']:<12} target winners {int(r['target_winners']):>3} | "
            f"cap winners {int(r['cap_target_winners']):>3} | "
            f"exact 30m overlap {int(r['with_exact_30m_overlap']):>3} | "
            f"full 30m {int(r['with_full_30m_bar']):>3} | "
            f"same-ET-date candidates {int(r['with_same_et_date_candidate']):>3}"
        )
    lines += [
        "",
        "2025 HIGH-DETAIL BLOCK",
        f"Target winners in Aug/Sep 2025 windows:     {owned25_targets}",
        f"Route-cap target winners in those windows: {owned25_caps}",
        f"Recovered exact 30m overlaps:              {owned25_exact}",
        f"Same-ET-date candidate matches:            {owned25_date}",
        "",
        "ALL TARGET WINNERS",
        f"Exact 30m bar overlaps:                    {exact} / {len(m)}",
        f"Full 30m bar coverage:                     {full} / {len(m)}",
        f"Same-ET-date candidate matches:            {datec} / {len(m)}",
        "",
        f"DIAGNOSIS: {diagnosis}",
        "",
        "AUTHORITY RULE",
        "R1.2 does NOT claim an exact target-hit timestamp from TradingView.",
        "The next replay must detect the first ordered TBBO event that reaches/crosses the frozen target price inside the bar.",
        "Only after that detected event may post-target +1s/+5s/+30s/+1m/+5m continuation be measured.",
        "",
        "GOVERNANCE",
        "Frozen V3.6.72 modified: NO",
        "X10.2 modified: NO",
        "Target geometry modified: NO",
        "Live routing: LOCKED",
        "="*128,
    ]
    txt.write_text("\n".join(lines),encoding="utf-8")
    latest=BASE/"LATEST_X10_3C_R12_SESSION_MAPPER_SUMMARY.txt"
    latest.write_text(txt.read_text(encoding="utf-8"),encoding="utf-8")

    ledger=STATE/"X10_3C_R12_LEDGER.csv"
    row={
        "run_utc":datetime.now(timezone.utc).isoformat(),
        "authority_windows":len(a),"target_winners":len(m),
        "owned_2025_target_winners":owned25_targets,"owned_2025_cap_winners":owned25_caps,
        "owned_2025_exact_overlap":owned25_exact,"owned_2025_same_date":owned25_date,
        "all_exact_overlap":exact,"all_full30m":full,"all_same_date":datec,
        "diagnosis":diagnosis
    }
    exists=ledger.exists()
    with ledger.open("a",encoding="utf-8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(row.keys()))
        if not exists:w.writeheader()
        w.writerow(row)

    print("="*92)
    print("FLIP FLOP X10.3C-R1.2 SESSION MAPPER")
    print("STATUS: PASS")
    print(f"2025 owned-window target winners: {owned25_targets}")
    print(f"2025 owned-window cap winners: {owned25_caps}")
    print(f"Recovered exact overlaps: {owned25_exact}")
    print(f"Same-ET-date candidates: {owned25_date}")
    print(f"Diagnosis: {diagnosis}")
    print("Frozen V3.6.72 modified: NO")
    print("X10.2 modified: NO")
    print("Target geometry modified: NO")
    print("Live routing: LOCKED")
    print(f"Report: {txt}")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except SystemExit: raise
    except Exception as e:
        print("STATUS: FAIL",file=sys.stderr)
        print(str(e),file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
