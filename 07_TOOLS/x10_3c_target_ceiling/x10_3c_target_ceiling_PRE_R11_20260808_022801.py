#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, os, re, sys, traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HQ=Path(os.environ.get("FF_HQ", r"C:\FLIP_FLOP_HQ"))
BASE=HQ/r"06_REPORTS\forensic\x10_3c_target_ceiling"
RUNS=BASE/"runs"
STATE=BASE/"state"
X3B=HQ/r"06_REPORTS\forensic\x10_3b_quant_core\runs"
DL=Path.home()/"Downloads"

REQ={"Trade number","Type","Date and time","Signal","Price USD","Size (qty)",
     "Net PnL USD","Commission USD","Favorable excursion USD"}

ROUTE_CAP_POINTS={"NY":16.0,"WEEKLY":10.0,"PREMIUM":10.0,"WEAK":10.0}
NQ_DOLLARS_PER_POINT=20.0
NY_TZ=ZoneInfo("America/New_York")

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest().upper()

def pct(a,b):
    return 100.0*a/b if b else None

def f(x,d=2):
    if x is None or (isinstance(x,float) and not math.isfinite(x)): return "N/A"
    return f"{x:,.{d}f}"

def classify_side(df):
    sig=" ".join(df["Signal"].astype(str).head(100).tolist()).upper()
    if "BUY" in sig and "SELL" not in sig: return "BUY"
    if "SELL" in sig and "BUY" not in sig: return "SELL"
    # broader vote
    s=df["Signal"].astype(str).str.upper()
    buy=int(s.str.contains("BUY").sum()); sell=int(s.str.contains("SELL").sum())
    return "BUY" if buy>sell else ("SELL" if sell>buy else "")

def candidate_reports():
    found=[]
    for p in DL.rglob("*.csv"):
        try:
            head=pd.read_csv(p,nrows=12)
            if not REQ.issubset(set(head.columns)): continue
            side=classify_side(head)
            if not side: continue
            # count exits cheaply using only Type
            typ=pd.read_csv(p,usecols=["Type"])
            n=int(typ["Type"].astype(str).str.startswith("Exit").sum())
            if n<100: continue
            found.append((p,side,n,p.stat().st_mtime))
        except Exception:
            pass
    chosen={}
    for side in ("BUY","SELL"):
        c=[x for x in found if x[1]==side]
        if not c: raise RuntimeError(f"No full TradingView {side} trade-list CSV found in Downloads.")
        c.sort(key=lambda x:(x[2],x[3]),reverse=True)
        chosen[side]=c[0][0]
    return chosen

def route_of(signal,qty):
    s=str(signal).upper()
    if "WEEKLY" in s: return "WEEKLY"
    if "WEEKDAY" in s:
        return "PREMIUM" if int(qty)>=2 else "WEAK"
    if "NY" in s: return "NY"
    return "OTHER"

def load_trades(path,side):
    df=pd.read_csv(path)
    e=df[df["Type"].astype(str).str.startswith("Entry")].copy()
    x=df[df["Type"].astype(str).str.startswith("Exit")].copy()
    m=e.merge(x,on="Trade number",suffixes=("_entry","_exit"),validate="one_to_one")
    m["side"]=side
    m["entry_dt"]=pd.to_datetime(m["Date and time_entry"],errors="coerce")
    m["exit_dt"]=pd.to_datetime(m["Date and time_exit"],errors="coerce")
    m["year"]=m["entry_dt"].dt.year
    m["entry_price"]=pd.to_numeric(m["Price USD_entry"],errors="coerce")
    m["exit_price"]=pd.to_numeric(m["Price USD_exit"],errors="coerce")
    m["qty"]=pd.to_numeric(m["Size (qty)_entry"],errors="coerce").astype("Int64")
    m["net"]=pd.to_numeric(m["Net PnL USD_exit"],errors="coerce")
    m["commission"]=pd.to_numeric(m["Commission USD_exit"],errors="coerce")
    m["fav_excursion"]=pd.to_numeric(m["Favorable excursion USD_exit"],errors="coerce")
    m["signal_exit"]=m["Signal_exit"].astype(str)
    m["route"]=[route_of(s,q) for s,q in zip(m["signal_exit"],m["qty"])]
    # Current frozen target labels. Session-flat and stop rows are excluded.
    sig=m["signal_exit"].str.upper()
    m["is_target"]=m["net"].gt(0) & ~sig.str.contains("STOP|SESSION END|SESSION_FLAT|FLATTEN",regex=True)
    direction=1.0 if side=="BUY" else -1.0
    m["points"]=(m["exit_price"]-m["entry_price"])*direction
    m["gross_realized"]=m["points"]*NQ_DOLLARS_PER_POINT*m["qty"].astype(float)
    m["target_bps"]=m["points"]/m["entry_price"]*10000.0
    # TradingView excursion includes entry-side commission but not closing commission.
    m["fav_gross_proxy"]=m["fav_excursion"]+m["commission"]/2.0
    m["pre_exit_extra_fav_gross_proxy"]=m["fav_gross_proxy"]-m["gross_realized"]
    m["route_cap_points"]=m["route"].map(ROUTE_CAP_POINTS)
    m["at_route_cap"]=np.isclose(m["points"],m["route_cap_points"],atol=1e-9)
    return m

def latest_x3b_audit():
    files=sorted(X3B.glob("X10_3B_FILE_SCHEMA_AUDIT_*.csv"),key=lambda p:p.stat().st_mtime,reverse=True)
    return files[0] if files else None

def parse_utc(x):
    try:
        return pd.to_datetime(x,utc=True,errors="coerce")
    except Exception:
        return pd.NaT

def overlap_map(targets,audit_path):
    cols=["side","Trade number","route","entry_dt","exit_dt","net","points","at_route_cap",
          "exit_bar_utc","authority_files_overlapping_exit_bar","full_5m_covered",
          "full_30m_covered","best_authority_rank"]
    if audit_path is None or not audit_path.exists():
        return pd.DataFrame(columns=cols)
    a=pd.read_csv(audit_path)
    if "authority_rank" not in a.columns: return pd.DataFrame(columns=cols)
    a["authority_rank"]=pd.to_numeric(a["authority_rank"],errors="coerce").fillna(0).astype(int)
    a=a[(a["decode_status"].astype(str)=="PASS") & (a["authority_rank"]>=2)].copy()
    a["start"]=pd.to_datetime(a["start_utc"],utc=True,errors="coerce")
    a["end"]=pd.to_datetime(a["end_utc"],utc=True,errors="coerce")
    a=a[a["start"].notna() & a["end"].notna()].copy()

    out=[]
    for _,r in targets.iterrows():
        ex=r["exit_dt"]
        if pd.isna(ex): continue
        local=ex.to_pydatetime().replace(tzinfo=NY_TZ)
        bar=pd.Timestamp(local.astimezone(timezone.utc))
        e5=bar+pd.Timedelta(minutes=5)
        e30=bar+pd.Timedelta(minutes=30)
        ov=a[(a["start"]<e30)&(a["end"]>bar)]
        full5=a[(a["start"]<=bar)&(a["end"]>=e5)]
        full30=a[(a["start"]<=bar)&(a["end"]>=e30)]
        out.append({
            "side":r["side"],"Trade number":r["Trade number"],"route":r["route"],
            "entry_dt":r["entry_dt"],"exit_dt":r["exit_dt"],"net":r["net"],
            "points":r["points"],"at_route_cap":bool(r["at_route_cap"]),
            "exit_bar_utc":bar.isoformat(),
            "authority_files_overlapping_exit_bar":len(ov),
            "full_5m_covered":bool(len(full5)),
            "full_30m_covered":bool(len(full30)),
            "best_authority_rank":int(ov["authority_rank"].max()) if len(ov) else 0,
        })
    return pd.DataFrame(out)

def main():
    BASE.mkdir(parents=True,exist_ok=True);RUNS.mkdir(parents=True,exist_ok=True);STATE.mkdir(parents=True,exist_ok=True)
    reports=candidate_reports()
    buy=load_trades(reports["BUY"],"BUY")
    sell=load_trades(reports["SELL"],"SELL")
    alltr=pd.concat([buy,sell],ignore_index=True)
    targets=alltr[alltr["is_target"]].copy()
    ny=targets[targets["route"]=="NY"].copy()

    if len(buy)!=len(sell):
        raise RuntimeError(f"BUY/SELL trade count mismatch: {len(buy)} vs {len(sell)}")

    run=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    buy_sha=sha256(reports["BUY"]); sell_sha=sha256(reports["SELL"])
    sync=hashlib.sha256((buy_sha+"|"+sell_sha).encode()).hexdigest().upper()

    # Highest recurring target PnL is a robust normal ceiling detector.
    vc=targets["net"].value_counts()
    recurring=vc[vc>=2]
    normal_max=float(recurring.index.max()) if len(recurring) else float(targets["net"].max())
    abs_max=float(targets["net"].max())
    absmax_row=targets.loc[targets["net"].idxmax()]
    normal_count=int(np.isclose(targets["net"],normal_max).sum())
    ny_normal_count=int(np.isclose(ny["net"],normal_max).sum())

    # TV target winners expose no post-exit path if excursion stops at realized target.
    extra=targets["pre_exit_extra_fav_gross_proxy"].fillna(0).to_numpy(float)
    extra_nonzero=int((np.abs(extra)>1e-8).sum())
    post_target_authority="NONE_FROM_TV_TRADE_LIST" if extra_nonzero==0 else "LIMITED_PRE_EXIT_ONLY"

    # Year x route table
    rows=[]
    for (year,route),g in targets.groupby(["year","route"]):
        cap=ROUTE_CAP_POINTS.get(route,np.nan)
        rows.append({
            "year":int(year),"route":route,"target_wins":len(g),
            "median_target_points":float(g["points"].median()),
            "mean_target_points":float(g["points"].mean()),
            "max_target_points":float(g["points"].max()),
            "median_target_bps":float(g["target_bps"].median()),
            "median_entry_price":float(g["entry_price"].median()),
            "route_cap_points":cap,
            "cap_wins":int(g["at_route_cap"].sum()),
            "cap_wins_pct":pct(int(g["at_route_cap"].sum()),len(g))
        })
    yearroute=pd.DataFrame(rows).sort_values(["year","route"])

    # Specific 2025/2026 cap saturation
    y25=targets[targets["year"]==2025]
    y26=targets[targets["year"]==2026]
    ny25=ny[ny["year"]==2025]; ny26=ny[ny["year"]==2026]
    first_cap=targets[targets["at_route_cap"]].sort_values("entry_dt").head(1)

    # Compression, regular NY target winners only, excluding any target >20 pts (COVID dislocation).
    nyreg=ny[ny["points"]<=20].copy()
    nyyear=nyreg.groupby("year").agg(
        target_wins=("points","size"),
        median_target_points=("points","median"),
        median_target_bps=("target_bps","median"),
        median_entry_price=("entry_price","median"),
        cap_wins=("at_route_cap","sum")
    ).reset_index()
    nyyear["cap_wins_pct"]=100*nyyear["cap_wins"]/nyyear["target_wins"]

    overlap=overlap_map(targets,latest_x3b_audit())
    overlap5=int(overlap["full_5m_covered"].sum()) if len(overlap) else 0
    overlap30=int(overlap["full_30m_covered"].sum()) if len(overlap) else 0
    overlap_any=int((overlap["authority_files_overlapping_exit_bar"]>0).sum()) if len(overlap) else 0

    # Write outputs
    targets_csv=RUNS/f"X10_3C_TARGET_WINNERS_{run}.csv"
    keep=["side","Trade number","entry_dt","exit_dt","route","qty","entry_price","exit_price","net",
          "commission","points","target_bps","route_cap_points","at_route_cap",
          "pre_exit_extra_fav_gross_proxy","signal_exit"]
    targets[keep].to_csv(targets_csv,index=False)

    yr_csv=RUNS/f"X10_3C_YEAR_ROUTE_CEILING_{run}.csv"
    yearroute.to_csv(yr_csv,index=False)

    ny_csv=RUNS/f"X10_3C_NY_COMPRESSION_{run}.csv"
    nyyear.to_csv(ny_csv,index=False)

    ov_csv=RUNS/f"X10_3C_HIGH_DETAIL_TARGET_OVERLAP_{run}.csv"
    overlap.to_csv(ov_csv,index=False)

    # Agent board
    agents=[
        ("QUANT_MATH_AGENT","ACTIVE","ceiling frequency, bps compression, route/year math"),
        ("RESULTS_ORGANIZER","ACTIVE","append-only run ledger + immutable CSV outputs"),
        ("TARGET_CEILING_AGENT","ACTIVE","hard-cap saturation and recurring max-win audit"),
        ("TV_PATH_AUTHORITY_AGENT","ACTIVE","blocks false post-target claims from closed Trade List"),
        ("HIGH_DETAIL_OVERLAP_AGENT","ACTIVE","maps target exits to owned L1 authority windows"),
        ("POST_TARGET_REPLAY_AGENT","ARMED_NEXT","ordered TBBO replay only on covered target winners"),
        ("SIGNAL_SCALE_AGENT","UNCHANGED","capacity research remains separate"),
        ("GOVERNOR","ACTIVE","no Pine/X10.2/live modifications"),
    ]
    agent_csv=RUNS/f"X10_3C_AGENT_BOARD_{run}.csv"
    pd.DataFrame(agents,columns=["agent","state","job"]).to_csv(agent_csv,index=False)

    # ledger
    ledger=STATE/"X10_3C_RESULTS_LEDGER.csv"
    led={
        "run_utc":datetime.now(timezone.utc).isoformat(),"sync_sha256":sync,
        "pair_sessions":len(buy),"worker_trades":len(alltr),"target_wins":len(targets),
        "ny_target_wins":len(ny),"normal_max_recurring_win":normal_max,
        "normal_max_count":normal_count,"absolute_max_win":abs_max,
        "absolute_max_date":str(absmax_row["entry_dt"]),"absolute_max_side":absmax_row["side"],
        "ny_2025_cap_wins":int(ny25["at_route_cap"].sum()),"ny_2025_target_wins":len(ny25),
        "ny_2026_cap_wins":int(ny26["at_route_cap"].sum()),"ny_2026_target_wins":len(ny26),
        "all_2026_cap_wins":int(y26["at_route_cap"].sum()),"all_2026_target_wins":len(y26),
        "tv_post_target_authority":post_target_authority,
        "high_detail_exitbar_overlap":overlap_any,"high_detail_full5m":overlap5,"high_detail_full30m":overlap30
    }
    exists=ledger.exists()
    with ledger.open("a",encoding="utf-8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(led.keys()))
        if not exists:w.writeheader()
        w.writerow(led)

    # report
    first_cap_txt="N/A"
    if len(first_cap):
        rr=first_cap.iloc[0]
        first_cap_txt=f"{rr['entry_dt']} | {rr['side']} | {rr['route']} | {rr['points']:.2f} pts | ${rr['net']:.2f}"

    # NY median bps endpoints
    bps2020=None;bps2024=None;bps2026=None
    for yr,var in [(2020,"bps2020"),(2024,"bps2024"),(2026,"bps2026")]:
        z=nyyear[nyyear["year"]==yr]
        if len(z):
            val=float(z.iloc[0]["median_target_bps"])
            if yr==2020:bps2020=val
            elif yr==2024:bps2024=val
            else:bps2026=val
    comp20_26=pct((bps2020-bps2026),bps2020) if bps2020 and bps2026 else None
    comp24_26=pct((bps2024-bps2026),bps2024) if bps2024 and bps2026 else None

    txt=RUNS/f"X10_3C_TARGET_CEILING_SUMMARY_{run}.txt"
    lines=[
        "="*128,
        "FLIP FLOP X10.3C TARGET CEILING AUTOPSY",
        "="*128,
        "STATUS: PASS",
        "",
        "SOURCE AUTHORITY",
        f"BUY:  {reports['BUY']}",
        f"SELL: {reports['SELL']}",
        f"BUY SHA256:  {buy_sha}",
        f"SELL SHA256: {sell_sha}",
        f"PAIR SYNC SHA256: {sync}",
        "",
        "CORE COUNTS",
        f"Synchronized pair sessions:             {len(buy):,}",
        f"Worker trades analyzed:                 {len(alltr):,}",
        f"Target winners analyzed:                {len(targets):,}",
        f"NY target winners:                      {len(ny):,}",
        "",
        "MAX-WIN AUTOPSY",
        f"Highest recurring normal target win:    ${normal_max:,.2f}",
        f"Occurrences of that recurring max:      {normal_count:,}",
        f"As % of all target wins:                {pct(normal_count,len(targets)):.2f}%",
        f"As % of NY target wins:                 {pct(ny_normal_count,len(ny)):.2f}%",
        f"Absolute historical max target win:     ${abs_max:,.2f}",
        f"Absolute max event:                     {absmax_row['entry_dt']} | {absmax_row['side']} | {absmax_row['route']} | {absmax_row['points']:.2f} pts",
        "",
        "CEILING SATURATION",
        f"NY 2025 cap wins / target wins:         {int(ny25['at_route_cap'].sum())} / {len(ny25)} = {pct(int(ny25['at_route_cap'].sum()),len(ny25)):.2f}%",
        f"NY 2026 cap wins / target wins:         {int(ny26['at_route_cap'].sum())} / {len(ny26)} = {pct(int(ny26['at_route_cap'].sum()),len(ny26)):.2f}%",
        f"ALL routes 2025 cap wins/target wins:   {int(y25['at_route_cap'].sum())} / {len(y25)} = {pct(int(y25['at_route_cap'].sum()),len(y25)):.2f}%",
        f"ALL routes 2026 cap wins/target wins:   {int(y26['at_route_cap'].sum())} / {len(y26)} = {pct(int(y26['at_route_cap'].sum()),len(y26)):.2f}%",
        f"First observed route-cap target winner: {first_cap_txt}",
        "",
        "NY TARGET SCALE COMPRESSION",
        f"Median target bps 2020:                 {f(bps2020,3)}",
        f"Median target bps 2024:                 {f(bps2024,3)}",
        f"Median target bps 2026:                 {f(bps2026,3)}",
        f"Compression 2020 -> 2026:               {f(comp20_26,2)}%",
        f"Compression 2024 -> 2026:               {f(comp24_26,2)}%",
        "",
        "TRADINGVIEW POST-TARGET AUTHORITY CHECK",
        f"Target winners with nonzero extra favorable excursion beyond realized target: {extra_nonzero} / {len(targets)}",
        f"POST-TARGET CONTINUATION AUTHORITY:     {post_target_authority}",
        "Interpretation: the closed Trade List does not tell us what price did AFTER the target exit.",
        "Any claim about profits left after target therefore requires ordered market-data replay.",
        "",
        "OWNED HIGH-DETAIL REPLAY READINESS",
        f"Target exits with any L1 authority overlap in exit bar: {overlap_any}",
        f"Target exits with one-file full +5m coverage:           {overlap5}",
        f"Target exits with one-file full +30m coverage:          {overlap30}",
        "",
        "NEXT PREDECLARED REPLAY METRICS",
        "For every covered target winner, ordered TBBO trade-space replay will measure:",
        "  +1s / +5s / +30s / +1m / +5m / +15m / +30m continuation",
        "  extra favorable points beyond original target",
        "  retracement after target",
        "  time-to-extra +1 / +2 / +4 / +8 points",
        "  route/year/side distributions",
        "  no multi-level fill claims (authority remains L1 trade-space only)",
        "",
        "AGENTS",
    ]
    for a,s,j in agents: lines.append(f"{a:<28} {s:<14} {j}")
    lines += [
        "",
        "GOVERNANCE",
        "Frozen V3.6.72 modified: NO",
        "X10.2 forward championship modified: NO",
        "Entry/exit logic modified: NO",
        "Target geometry modified: NO",
        "Live routing: LOCKED",
        "X10.3C authority: FORENSIC RESEARCH ONLY",
        "="*128
    ]
    txt.write_text("\n".join(lines),encoding="utf-8")
    latest=BASE/"LATEST_X10_3C_TARGET_CEILING_SUMMARY.txt"
    latest.write_text(txt.read_text(encoding="utf-8"),encoding="utf-8")

    manifest={
        "run":run,"pair_sync_sha256":sync,"summary":str(txt),
        "targets":str(targets_csv),"year_route":str(yr_csv),"ny_compression":str(ny_csv),
        "overlap":str(ov_csv),"agent_board":str(agent_csv),"ledger":str(ledger)
    }
    (RUNS/f"X10_3C_RUN_MANIFEST_{run}.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")

    print("="*92)
    print("FLIP FLOP X10.3C TARGET CEILING AUTOPSY")
    print("STATUS: PASS")
    print(f"Pair sessions: {len(buy):,}")
    print(f"Target winners: {len(targets):,}")
    print(f"Recurring normal max win: ${normal_max:,.2f} ({normal_count} occurrences)")
    print(f"Absolute max: ${abs_max:,.2f}")
    print(f"NY 2025 cap saturation: {pct(int(ny25['at_route_cap'].sum()),len(ny25)):.2f}%")
    print(f"NY 2026 cap saturation: {pct(int(ny26['at_route_cap'].sum()),len(ny26)):.2f}%")
    print(f"All-route 2026 cap saturation: {pct(int(y26['at_route_cap'].sum()),len(y26)):.2f}%")
    print(f"TV post-target authority: {post_target_authority}")
    print(f"High-detail target exit-bar overlap: {overlap_any}")
    print("Frozen V3.6.72 modified: NO")
    print("X10.2 modified: NO")
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
