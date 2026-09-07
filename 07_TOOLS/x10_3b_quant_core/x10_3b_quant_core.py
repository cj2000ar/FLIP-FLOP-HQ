#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, os, sys, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HQ=Path(os.environ.get("FF_HQ", r"C:\FLIP_FLOP_HQ"))
X3A=HQ/r"06_REPORTS\forensic\x10_3a_data_scout"
INV=X3A/"X10_3A_DATA_INVENTORY.csv"
BASE=HQ/r"06_REPORTS\forensic\x10_3b_quant_core"
RUNS=BASE/"runs"
STATE=BASE/"state"
TOOLS=HQ/r"07_TOOLS\x10_3b_quant_core"
NQ_TICK=0.25
QGRID=list(range(1,11))
MAX_SAMPLE_PER_FILE=15000

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest().upper()

def qtile(a,q):
    a=np.asarray(a,dtype=float)
    a=a[np.isfinite(a)]
    return float(np.quantile(a,q)) if len(a) else None

def fnum(x,d=3):
    if x is None or (isinstance(x,float) and not math.isfinite(x)): return "N/A"
    return f"{x:,.{d}f}"

def ts_series(s):
    if s is None: return None
    try:
        if pd.api.types.is_datetime64_any_dtype(s):
            return pd.to_datetime(s,utc=True,errors="coerce")
        if pd.api.types.is_numeric_dtype(s):
            vals=pd.to_numeric(s,errors="coerce")
            med=vals.dropna().abs().median()
            if pd.isna(med): return pd.to_datetime(s,utc=True,errors="coerce")
            unit="ns" if med>1e17 else ("us" if med>1e14 else ("ms" if med>1e11 else "s"))
            return pd.to_datetime(vals,unit=unit,utc=True,errors="coerce")
        return pd.to_datetime(s,utc=True,errors="coerce")
    except Exception:
        return pd.to_datetime(s,utc=True,errors="coerce")

def px_series(s):
    x=pd.to_numeric(s,errors="coerce").astype(float)
    med=x.dropna().abs().median()
    if pd.notna(med) and med>1e7:
        x=x/1e9
    return x

def sample_even(a,n=MAX_SAMPLE_PER_FILE):
    a=np.asarray(a)
    if len(a)<=n:return a
    idx=np.linspace(0,len(a)-1,n,dtype=int)
    return a[idx]

def schema_authority(schema,cols):
    s=(schema or "").lower()
    c={str(x).lower() for x in cols}
    # Deep-book evidence
    deeper=any(x.startswith("bid_px_01") or x.startswith("ask_px_01") for x in c)
    if "mbo" in s:
        return ("MBO","FULL_BOOK_RECONSTRUCTION_CANDIDATE",4)
    if "mbp-10" in s or "mbp10" in s or deeper:
        return ("MBP10","MULTI_LEVEL_BOOK_CANDIDATE",4)
    if "mbp-1" in s or "mbp1" in s:
        return ("MBP1","L1_BOOK_UPDATE_AUTHORITY",3)
    if "tbbo" in s:
        return ("TBBO","L1_TRADE_SPACE_AUTHORITY",2)
    if "bbo" in s:
        return ("BBO","L1_INTERVAL_AUTHORITY",1)
    # infer from columns
    if {"bid_px_00","ask_px_00","bid_sz_00","ask_sz_00"}.issubset(c):
        if "action" in c and "sequence" in c:
            return ("L1_UNKNOWN","L1_EVENT_AUTHORITY",2)
        return ("BBO_LIKE","L1_SNAPSHOT_AUTHORITY",1)
    return ("OTHER","NO_BOOK_AUTHORITY",0)

def load_csv(path):
    return pd.read_csv(path,low_memory=False), "CSV"

def load_parquet(path):
    return pd.read_parquet(path), "PARQUET"

def load_dbn(path):
    import databento as db
    store=db.DBNStore.from_file(path)
    meta=getattr(store,"metadata",None)
    schema=str(getattr(meta,"schema","")) if meta is not None else ""
    df=store.to_df(price_type="float",pretty_ts=True)
    if isinstance(df.index,pd.DatetimeIndex):
        idxname=df.index.name or "index_ts"
        if idxname in df.columns: idxname="index_ts"
        df=df.reset_index(names=idxname)
    else:
        df=df.reset_index(drop=False)
    return df, schema

def inspect_one(row):
    path=Path(row["path"])
    out={
        "path":str(path),"name":path.name,"x3a_classification":row.get("classification",""),
        "sha256":row.get("sha256",""),"decode_status":"PASS","decode_error":"",
        "actual_schema":"","authority_type":"","authority_label":"","authority_rank":0,
        "rows":0,"start_utc":"","end_utc":"","duration_s":None,"timestamp_violations":0,
        "valid_bbo_rows":0,"valid_bbo_pct":None,
        "spread_median_ticks":None,"spread_p90_ticks":None,"spread_p99_ticks":None,"spread_max_ticks":None,
        "top_depth_median":None,"top_depth_p10":None,"top_depth_p90":None,
        "bid_size_median":None,"ask_size_median":None,"imbalance_abs_median":None,
        "event_gap_median_ms":None,"event_gap_p95_ms":None,"event_gap_max_ms":None,
        "event_rate_per_s":None,"quote_change_rate":None,
        "recv_minus_event_median_us":None,"recv_minus_event_p95_us":None,
        "instrument_count":None,"symbol_count":None,
    }
    samples={"spread":[],"depth":[],"gap_ms":[],"lat_us":[],"bid_sz":[],"ask_sz":[]}
    qcov={q:{"buy":0,"sell":0,"both":0,"den":0,"buy_short":0.0,"sell_short":0.0} for q in QGRID}
    try:
        if not path.exists(): raise FileNotFoundError(path)
        low=path.name.lower()
        suf=path.suffix.lower()
        if suf==".csv":
            df,schema=load_csv(path)
        elif suf in (".parquet",".pq"):
            df,schema=load_parquet(path)
        elif suf==".dbn" or ".dbn." in low or ("dbn" in low and low.endswith(".zst")):
            df,schema=load_dbn(path)
        else:
            out["decode_status"]="SKIP"
            out["decode_error"]="Format not decoded by X10.3B quantitative core"
            return out,samples,qcov
        out["actual_schema"]=schema
        out["rows"]=len(df)
        cols=list(df.columns)
        atype,alabel,rank=schema_authority(schema,cols)
        out["authority_type"]=atype;out["authority_label"]=alabel;out["authority_rank"]=rank

        # time authority preference ts_event, then index ts, then ts_recv
        t=None
        for k in ("ts_event","index_ts","ts_recv","timestamp","datetime","Date and time"):
            if k in df.columns:
                tt=ts_series(df[k])
                if tt is not None and tt.notna().any():
                    t=tt;break
        if t is not None:
            tv=t.dropna()
            if len(tv):
                out["start_utc"]=tv.min().isoformat()
                out["end_utc"]=tv.max().isoformat()
                out["duration_s"]=max(0.0,(tv.max()-tv.min()).total_seconds())
                ns=tv.astype("int64").to_numpy()
                dif=np.diff(ns)/1e6
                out["timestamp_violations"]=int((dif<0).sum())
                good=dif[dif>=0]
                if len(good):
                    out["event_gap_median_ms"]=qtile(good,.5)
                    out["event_gap_p95_ms"]=qtile(good,.95)
                    out["event_gap_max_ms"]=float(np.max(good))
                    samples["gap_ms"]=sample_even(good)
                if out["duration_s"] and out["duration_s"]>0:
                    out["event_rate_per_s"]=len(tv)/out["duration_s"]

        # feed receive latency proxy
        if "ts_recv" in df.columns and "ts_event" in df.columns:
            tr=ts_series(df["ts_recv"]);te=ts_series(df["ts_event"])
            lat=(tr.astype("int64")-te.astype("int64"))/1000.0
            lat=np.asarray(lat,dtype=float)
            lat=lat[np.isfinite(lat) & (lat>=0)]
            if len(lat):
                out["recv_minus_event_median_us"]=qtile(lat,.5)
                out["recv_minus_event_p95_us"]=qtile(lat,.95)
                samples["lat_us"]=sample_even(lat)

        if "instrument_id" in df.columns:
            out["instrument_count"]=int(pd.Series(df["instrument_id"]).nunique(dropna=True))
        if "symbol" in df.columns:
            out["symbol_count"]=int(pd.Series(df["symbol"]).nunique(dropna=True))

        needed={"bid_px_00","ask_px_00","bid_sz_00","ask_sz_00"}
        if needed.issubset(set(cols)):
            bid=px_series(df["bid_px_00"]).to_numpy()
            ask=px_series(df["ask_px_00"]).to_numpy()
            bsz=pd.to_numeric(df["bid_sz_00"],errors="coerce").to_numpy(dtype=float)
            asz=pd.to_numeric(df["ask_sz_00"],errors="coerce").to_numpy(dtype=float)
            valid=np.isfinite(bid)&np.isfinite(ask)&np.isfinite(bsz)&np.isfinite(asz)&(ask>=bid)&(bid>0)&(ask>0)&(bsz>=0)&(asz>=0)
            n=int(valid.sum())
            out["valid_bbo_rows"]=n
            out["valid_bbo_pct"]=100*n/len(df) if len(df) else None
            if n:
                bid=bid[valid];ask=ask[valid];bsz=bsz[valid];asz=asz[valid]
                spread=(ask-bid)/NQ_TICK
                depth=bsz+asz
                imb=np.abs((bsz-asz)/np.where(depth>0,depth,np.nan))
                out["spread_median_ticks"]=qtile(spread,.5)
                out["spread_p90_ticks"]=qtile(spread,.9)
                out["spread_p99_ticks"]=qtile(spread,.99)
                out["spread_max_ticks"]=float(np.nanmax(spread))
                out["top_depth_median"]=qtile(depth,.5)
                out["top_depth_p10"]=qtile(depth,.1)
                out["top_depth_p90"]=qtile(depth,.9)
                out["bid_size_median"]=qtile(bsz,.5)
                out["ask_size_median"]=qtile(asz,.5)
                out["imbalance_abs_median"]=qtile(imb,.5)
                samples["spread"]=sample_even(spread)
                samples["depth"]=sample_even(depth)
                samples["bid_sz"]=sample_even(bsz)
                samples["ask_sz"]=sample_even(asz)
                if n>1:
                    qchg=(np.diff(bid)!=0)|(np.diff(ask)!=0)
                    out["quote_change_rate"]=float(qchg.mean())
                for q in QGRID:
                    qcov[q]["den"]=n
                    qcov[q]["buy"]=int((asz>=q).sum())
                    qcov[q]["sell"]=int((bsz>=q).sum())
                    qcov[q]["both"]=int(((asz>=q)&(bsz>=q)).sum())
                    qcov[q]["buy_short"]=float(np.maximum(q-asz,0).sum())
                    qcov[q]["sell_short"]=float(np.maximum(q-bsz,0).sum())
        return out,samples,qcov
    except Exception as e:
        out["decode_status"]="FAIL"
        out["decode_error"]=f"{type(e).__name__}: {e}"[:500]
        return out,samples,qcov

def dataset_fingerprint(rows):
    hs=sorted(str(r.get("sha256","")) for r in rows if r.get("sha256"))
    return hashlib.sha256("|".join(hs).encode()).hexdigest().upper()

def main():
    if not INV.exists():
        raise RuntimeError(f"X10.3A inventory missing: {INV}. Run X10.3A first.")
    BASE.mkdir(parents=True,exist_ok=True);RUNS.mkdir(parents=True,exist_ok=True);STATE.mkdir(parents=True,exist_ok=True)
    inv=pd.read_csv(INV,dtype=str).fillna("")
    rows=inv.to_dict("records")
    work=[r for r in rows if r.get("classification","") in
          ("DBN_HIGH_DETAIL","TBBO_HIGH_DETAIL","TBBO_LIKE_CSV","COLUMNAR_MARKET_DATA")]
    dataset_sha=dataset_fingerprint(work)
    run=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    workers=max(1,min(4,(os.cpu_count() or 2)))
    results=[];sample_pool={"spread":[],"depth":[],"gap_ms":[],"lat_us":[],"bid_sz":[],"ask_sz":[]}
    qagg={q:{"buy":0,"sell":0,"both":0,"den":0,"buy_short":0.0,"sell_short":0.0} for q in QGRID}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs={ex.submit(inspect_one,r):r for r in work}
        for fut in as_completed(futs):
            rec,samp,qcov=fut.result()
            results.append(rec)
            for k,a in samp.items():
                if len(a): sample_pool[k].append(np.asarray(a))
            for q in QGRID:
                for k in qagg[q]: qagg[q][k]+=qcov[q][k]
    results.sort(key=lambda r:r["path"].lower())

    file_csv=RUNS/f"X10_3B_FILE_SCHEMA_AUDIT_{run}.csv"
    pd.DataFrame(results).to_csv(file_csv,index=False)

    # schema authority counts
    auth={}
    for r in results:
        key=(r["authority_type"],r["authority_label"],r["authority_rank"])
        z=auth.setdefault(key,{"files":0,"rows":0,"valid_bbo_rows":0})
        z["files"]+=1;z["rows"]+=int(r["rows"] or 0);z["valid_bbo_rows"]+=int(r["valid_bbo_rows"] or 0)
    auth_rows=[]
    for (t,l,rank),z in sorted(auth.items(),key=lambda kv:(-kv[0][2],kv[0][0])):
        auth_rows.append({"authority_type":t,"authority_label":l,"authority_rank":rank,**z})
    auth_csv=RUNS/f"X10_3B_SCHEMA_AUTHORITY_{run}.csv"
    pd.DataFrame(auth_rows).to_csv(auth_csv,index=False)

    # L1 Q1-Q10 capacity proxy
    cap=[]
    for q in QGRID:
        z=qagg[q];den=z["den"]
        cap.append({
            "Q":q,"valid_bbo_events":den,
            "buy_top_size_ge_Q_pct":100*z["buy"]/den if den else None,
            "sell_top_size_ge_Q_pct":100*z["sell"]/den if den else None,
            "both_sides_top_size_ge_Q_pct":100*z["both"]/den if den else None,
            "mean_buy_contract_shortfall_per_event":z["buy_short"]/den if den else None,
            "mean_sell_contract_shortfall_per_event":z["sell_short"]/den if den else None,
            "authority_note":"L1 top-of-book coverage proxy only; not a multi-level fill guarantee"
        })
    cap_csv=RUNS/f"X10_3B_L1_Q1_Q10_CAPACITY_PROXY_{run}.csv"
    pd.DataFrame(cap).to_csv(cap_csv,index=False)

    def pool(k):
        return np.concatenate(sample_pool[k]) if sample_pool[k] else np.array([],dtype=float)
    spreads=pool("spread");depth=pool("depth");gaps=pool("gap_ms");lats=pool("lat_us")
    total_rows=sum(int(r["rows"] or 0) for r in results)
    bbo_rows=sum(int(r["valid_bbo_rows"] or 0) for r in results)
    decode_pass=sum(r["decode_status"]=="PASS" for r in results)
    decode_fail=sum(r["decode_status"]=="FAIL" for r in results)
    decode_skip=sum(r["decode_status"]=="SKIP" for r in results)
    max_rank=max([int(r["authority_rank"]) for r in results],default=0)
    authority_best={4:"FULL/MULTI-LEVEL BOOK CANDIDATE",3:"L1 BOOK UPDATE AUTHORITY",2:"L1 TRADE-SPACE AUTHORITY",1:"L1 SNAPSHOT AUTHORITY",0:"NO BOOK AUTHORITY"}[max_rank]

    # If full multi-level not found, don't permit exact multi-level Q fill agent
    exact_depth_ready=max_rank>=4
    l1_update_ready=max_rank>=3
    trade_l1_ready=max_rank>=2

    # Quant-math calculation registry
    math_rows=[
        ("dataset_sha256",dataset_sha),
        ("files_attempted",len(work)),
        ("files_decode_pass",decode_pass),
        ("files_decode_fail",decode_fail),
        ("files_decode_skip",decode_skip),
        ("decoded_rows",total_rows),
        ("valid_bbo_rows",bbo_rows),
        ("best_authority_rank",max_rank),
        ("spread_median_ticks",qtile(spreads,.5)),
        ("spread_p90_ticks",qtile(spreads,.9)),
        ("spread_p99_ticks",qtile(spreads,.99)),
        ("top_depth_median",qtile(depth,.5)),
        ("top_depth_p10",qtile(depth,.1)),
        ("event_gap_median_ms",qtile(gaps,.5)),
        ("event_gap_p95_ms",qtile(gaps,.95)),
        ("recv_minus_event_median_us",qtile(lats,.5)),
        ("recv_minus_event_p95_us",qtile(lats,.95)),
    ]
    math_csv=RUNS/f"X10_3B_QUANT_MATH_REGISTRY_{run}.csv"
    pd.DataFrame(math_rows,columns=["metric","value"]).to_csv(math_csv,index=False)

    # Algorithm agent organizer
    agents=[
        ("QUANT_MATH_AGENT","ACTIVE","robust quantiles, Q1-Q10 L1 coverage, dataset fingerprint"),
        ("RESULTS_ORGANIZER","ACTIVE","append-only run ledger, LATEST reports, run manifests"),
        ("SCHEMA_AUTHORITY_AGENT","ACTIVE","TBBO vs MBP-1 vs MBP-10/MBO authority"),
        ("CLOCK_AUDITOR","ACTIVE","timestamps, gaps, monotonicity, feed receive/event latency"),
        ("BBO_RECONSTRUCTOR","ACTIVE" if trade_l1_ready else "WAIT","BBO state metrics within actual schema authority"),
        ("FULL_BOOK_RECONSTRUCTOR","READY" if exact_depth_ready else "BLOCKED","requires MBP-10/MBO/deeper levels"),
        ("FILL_ENGINE_L1_PROXY","READY" if trade_l1_ready else "BLOCKED","top-of-book Q1-Q10 coverage only"),
        ("FILL_ENGINE_MULTI_LEVEL","READY" if exact_depth_ready else "BLOCKED","multi-level VWAP fill walk"),
        ("LATENCY_AGENT","READY" if trade_l1_ready else "BLOCKED","ordered event repricing after session anchors are mapped"),
        ("CAPACITY_BEND_AGENT","READY" if trade_l1_ready else "BLOCKED","Q curve from valid fill/coverage metrics"),
        ("SIGNAL_SCALE_AGENT","WAIT_SESSION_MAP","needs FLIP FLOP entry anchors joined to market events"),
        ("TOXICITY_AGENT","READY_FEATURES","spread/depth/velocity/gap feature generation"),
        ("RED_TEAM","WAIT_FILL_MODEL","depth haircut/latency/spread shock after fill authority selected"),
        ("GOVERNOR","ACTIVE","no Pine/X10.2/live modifications")
    ]
    agent_csv=RUNS/f"X10_3B_AGENT_BOARD_{run}.csv"
    pd.DataFrame(agents,columns=["agent","state","job"]).to_csv(agent_csv,index=False)

    # append run ledger
    ledger=STATE/"X10_3B_RESULTS_LEDGER.csv"
    ledger_row={
        "run_utc":datetime.now(timezone.utc).isoformat(),"dataset_sha256":dataset_sha,
        "files":len(work),"decode_pass":decode_pass,"decode_fail":decode_fail,"decoded_rows":total_rows,
        "valid_bbo_rows":bbo_rows,"best_authority_rank":max_rank,"best_authority":authority_best,
        "spread_median_ticks":qtile(spreads,.5),"depth_median":qtile(depth,.5),
        "q6_buy_top_coverage_pct":cap[5]["buy_top_size_ge_Q_pct"],
        "q6_sell_top_coverage_pct":cap[5]["sell_top_size_ge_Q_pct"],
        "q6_both_top_coverage_pct":cap[5]["both_sides_top_size_ge_Q_pct"],
        "exact_depth_ready":exact_depth_ready,"l1_update_ready":l1_update_ready
    }
    exists=ledger.exists()
    with ledger.open("a",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(ledger_row.keys()))
        if not exists:w.writeheader()
        w.writerow(ledger_row)

    txt=RUNS/f"X10_3B_QUANT_CORE_SUMMARY_{run}.txt"
    lines=[
        "="*124,
        "FLIP FLOP X10.3B QUANT-MATH + SCHEMA-AUTHORITY CORE",
        "="*124,
        "STATUS: PASS",
        "",
        "DATASET",
        f"X10.3A high-detail candidates attempted: {len(work)}",
        f"Decode PASS / FAIL / SKIP:             {decode_pass} / {decode_fail} / {decode_skip}",
        f"Decoded rows:                          {total_rows:,}",
        f"Valid BBO rows:                        {bbo_rows:,}",
        f"Dataset SHA256:                        {dataset_sha}",
        "",
        "SCHEMA AUTHORITY",
        f"Best authority rank:                   {max_rank}/4",
        f"Best authority:                        {authority_best}",
        f"L1 trade-space/BBO metrics ready:      {'YES' if trade_l1_ready else 'NO'}",
        f"L1 book-update authority ready:        {'YES' if l1_update_ready else 'NO'}",
        f"Exact multi-level depth fill ready:    {'YES' if exact_depth_ready else 'NO'}",
        "",
        "GLOBAL QUANT-MATH (sampled robust aggregates)",
        f"Spread median / P90 / P99 ticks:       {fnum(qtile(spreads,.5))} / {fnum(qtile(spreads,.9))} / {fnum(qtile(spreads,.99))}",
        f"Top BBO depth median / P10:             {fnum(qtile(depth,.5),2)} / {fnum(qtile(depth,.1),2)} contracts",
        f"Event gap median / P95 ms:              {fnum(qtile(gaps,.5))} / {fnum(qtile(gaps,.95))}",
        f"Receive-event latency median/P95 us:    {fnum(qtile(lats,.5))} / {fnum(qtile(lats,.95))}",
        "",
        "Q1-Q10 TOP-OF-BOOK CAPACITY PROXY",
        "This is L1 size coverage only. It is NOT an exact multi-level fill claim.",
    ]
    for z in cap:
        lines.append(
            f"Q{z['Q']:<2} | BUY top-size coverage {fnum(z['buy_top_size_ge_Q_pct'],2):>8}% | "
            f"SELL {fnum(z['sell_top_size_ge_Q_pct'],2):>8}% | BOTH {fnum(z['both_sides_top_size_ge_Q_pct'],2):>8}% | "
            f"mean shortfall B/S {fnum(z['mean_buy_contract_shortfall_per_event'],3)}/{fnum(z['mean_sell_contract_shortfall_per_event'],3)}"
        )
    lines += ["","AGENT BOARD"]
    for a,state,job in agents:
        lines.append(f"{a:<26} {state:<16} {job}")
    lines += [
        "",
        "AUTHORITY RULE",
        "TBBO = top-of-book in trade space. It cannot prove hidden/multi-level Q1-Q10 fills.",
        "MBP-1 = top-level book-update authority, still L1 only.",
        "MBP-10/MBO/deeper levels = candidate authority for multi-level VWAP fill walking.",
        "",
        "NEXT",
        "If MBP-10/MBO exists: X10.3C may build a true multi-level fill walker.",
        "If only TBBO/MBP-1 exists: X10.3C will use honest L1 execution proxies + latency/toxicity analysis,",
        "and will not fabricate deeper-book liquidity.",
        "",
        "RESULT KEEPING",
        f"Append-only results ledger: {ledger}",
        "",
        "GOVERNANCE",
        "Frozen V3.6.72 modified: NO",
        "X10.2 championship modified: NO",
        "Entry/exit logic modified: NO",
        "Live routing: LOCKED",
        "="*124
    ]
    txt.write_text("\n".join(lines),encoding="utf-8")
    latest=BASE/"LATEST_X10_3B_QUANT_CORE_SUMMARY.txt"
    latest.write_text(txt.read_text(encoding="utf-8"),encoding="utf-8")
    manifest={
        "run":run,"dataset_sha256":dataset_sha,"summary":str(txt),
        "file_audit":str(file_csv),"schema_authority":str(auth_csv),"capacity_proxy":str(cap_csv),
        "math_registry":str(math_csv),"agent_board":str(agent_csv),"results_ledger":str(ledger)
    }
    (RUNS/f"X10_3B_RUN_MANIFEST_{run}.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")

    print("="*90)
    print("FLIP FLOP X10.3B QUANT-MATH CORE")
    print("STATUS: PASS")
    print(f"Files attempted: {len(work)}")
    print(f"Decode PASS/FAIL/SKIP: {decode_pass}/{decode_fail}/{decode_skip}")
    print(f"Decoded rows: {total_rows:,}")
    print(f"Valid BBO rows: {bbo_rows:,}")
    print(f"Best authority: {authority_best} ({max_rank}/4)")
    print(f"Exact multi-level fill ready: {'YES' if exact_depth_ready else 'NO'}")
    print(f"Q6 BUY/SELL/BOTH top-size coverage: {fnum(cap[5]['buy_top_size_ge_Q_pct'],2)}% / {fnum(cap[5]['sell_top_size_ge_Q_pct'],2)}% / {fnum(cap[5]['both_sides_top_size_ge_Q_pct'],2)}%")
    print(f"Dataset SHA256: {dataset_sha}")
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
