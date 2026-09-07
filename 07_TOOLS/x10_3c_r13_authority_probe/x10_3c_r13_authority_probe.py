#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, os, re, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HQ=Path(os.environ.get("FF_HQ", r"C:\FLIP_FLOP_HQ"))
X3A=HQ/r"06_REPORTS\forensic\x10_3a_data_scout"
X3B=HQ/r"06_REPORTS\forensic\x10_3b_quant_core\runs"
BASE=HQ/r"06_REPORTS\forensic\x10_3c_target_ceiling\r13_authority_probe"
RUNS=BASE/"runs"
STATE=BASE/"state"

BLOCKS=[
    ("COVID_2020",pd.Timestamp("2020-03-16",tz="UTC"),pd.Timestamp("2020-03-19",tz="UTC")),
    ("AUG_2025",pd.Timestamp("2025-08-03",tz="UTC"),pd.Timestamp("2025-08-16",tz="UTC")),
    ("SEP_2025",pd.Timestamp("2025-09-14",tz="UTC"),pd.Timestamp("2025-09-21",tz="UTC")),
]

def latest_file(pattern,folder):
    xs=sorted(folder.glob(pattern),key=lambda p:p.stat().st_mtime,reverse=True)
    return xs[0] if xs else None

def date_tokens(s):
    out=[]
    for pat in [
        r"(20\d{2})[-_](\d{2})[-_](\d{2})",
        r"(20\d{2})(\d{2})(\d{2})",
        r"(20\d{2})[-_](\d{2})"
    ]:
        for m in re.finditer(pat,str(s)):
            out.append("-".join(m.groups()))
    return "|".join(dict.fromkeys(out))

def keyword_columns(cols):
    words=("time","ts_","date","bid","ask","price","size","qty","sequence","action","side","symbol","instrument")
    return "|".join([c for c in cols if any(w in c.lower() for w in words)])

def inspect_candidate(path,classification):
    out={
        "path":str(path),"exists":path.exists(),"classification":classification,
        "suffix":path.suffix.lower(),"size_bytes":path.stat().st_size if path.exists() else 0,
        "filename_date_tokens":date_tokens(path.name),
        "parser":"NONE","schema":"","columns":"","market_columns":"","rows":"",
        "candidate_start_utc":"","candidate_end_utc":"","decode_note":""
    }
    if not path.exists():
        out["decode_note"]="FILE_MISSING"
        return out
    try:
        low=path.name.lower()
        if path.suffix.lower()==".csv":
            df=pd.read_csv(path,nrows=5)
            out["parser"]="CSV_HEADER"
            out["columns"]="|".join(map(str,df.columns))
            out["market_columns"]=keyword_columns(list(map(str,df.columns)))
        elif path.suffix.lower() in (".parquet",".pq"):
            try:
                import pyarrow.parquet as pq
                pf=pq.ParquetFile(path)
                cols=pf.schema.names
                out["parser"]="PARQUET_META"
                out["schema"]="PARQUET"
                out["columns"]="|".join(cols)
                out["market_columns"]=keyword_columns(cols)
                out["rows"]=pf.metadata.num_rows
            except Exception as e:
                df=pd.read_parquet(path)
                out["parser"]="PARQUET_PANDAS"
                out["columns"]="|".join(map(str,df.columns))
                out["market_columns"]=keyword_columns(list(map(str,df.columns)))
                out["rows"]=len(df)
        elif path.suffix.lower()==".dbn" or ".dbn." in low or ("dbn" in low and low.endswith(".zst")):
            import databento as db
            store=db.DBNStore.from_file(path)
            meta=getattr(store,"metadata",None)
            out["parser"]="DATABENTO_DBN"
            out["schema"]=str(getattr(meta,"schema","")) if meta is not None else ""
            # Metadata timestamps are valuable diagnostics.
            for attr,key in [("start","candidate_start_utc"),("end","candidate_end_utc")]:
                v=getattr(meta,attr,None) if meta is not None else None
                if v is not None: out[key]=str(v)
            # Decode dataframe to reveal actual field names; owned set is small.
            df=store.to_df(price_type="float",pretty_ts=True)
            if isinstance(df.index,pd.DatetimeIndex):
                idxname=df.index.name or "index_ts"
                df=df.reset_index(names=idxname)
            else:
                df=df.reset_index(drop=False)
            cols=list(map(str,df.columns))
            out["columns"]="|".join(cols)
            out["market_columns"]=keyword_columns(cols)
            out["rows"]=len(df)
            # Get all plausible event clock ranges, then preserve the earliest/latest.
            ranges=[]
            for k in ("ts_event","ts_recv","index_ts","timestamp","datetime"):
                if k in df.columns:
                    ts=pd.to_datetime(df[k],utc=True,errors="coerce")
                    if ts.notna().any():
                        ranges.append((k,ts.min(),ts.max()))
            if ranges:
                # Prefer ts_event then index_ts then ts_recv.
                pref={"ts_event":0,"index_ts":1,"ts_recv":2,"timestamp":3,"datetime":4}
                ranges.sort(key=lambda z:pref.get(z[0],99))
                k,mn,mx=ranges[0]
                out["candidate_start_utc"]=mn.isoformat()
                out["candidate_end_utc"]=mx.isoformat()
                out["decode_note"]=f"clock={k}"
        else:
            out["decode_note"]="UNSUPPORTED_FOR_PROBE"
    except Exception as e:
        out["decode_note"]=f"{type(e).__name__}: {e}"[:400]
    return out

def block_match_from_text(path):
    s=str(path).lower()
    hits=[]
    if "2020" in s and ("03_16" in s or "03-16" in s or "covid" in s or "20200316" in s):
        hits.append("COVID_2020")
    if "2025" in s and ("aug" in s or "08_" in s or "08-" in s or "202508" in s or "giveback" in s):
        hits.append("AUG_2025")
    if "2025" in s and ("sep" in s or "09_" in s or "09-" in s or "202509" in s):
        hits.append("SEP_2025")
    return "|".join(hits)

def main():
    BASE.mkdir(parents=True,exist_ok=True);RUNS.mkdir(parents=True,exist_ok=True);STATE.mkdir(parents=True,exist_ok=True)
    inv=X3A/"X10_3A_DATA_INVENTORY.csv"
    audit=latest_file("X10_3B_FILE_SCHEMA_AUDIT_*.csv",X3B)
    if not inv.exists(): raise RuntimeError("X10.3A inventory missing.")
    if not audit: raise RuntimeError("X10.3B file schema audit missing.")

    ia=pd.read_csv(inv,dtype=str).fillna("")
    ab=pd.read_csv(audit,dtype=str).fillna("")
    ab["authority_rank_num"]=pd.to_numeric(ab["authority_rank"],errors="coerce").fillna(0).astype(int)

    rank2=ab[ab["authority_rank_num"]>=2].copy()
    rank2["reported_start_utc"]=pd.to_datetime(rank2["start_utc"],utc=True,errors="coerce")
    rank2["reported_end_utc"]=pd.to_datetime(rank2["end_utc"],utc=True,errors="coerce")
    rank2["reported_start_et"]=rank2["reported_start_utc"].dt.tz_convert("America/New_York").astype(str)
    rank2["reported_end_et"]=rank2["reported_end_utc"].dt.tz_convert("America/New_York").astype(str)
    rank2["filename_date_tokens"]=rank2["path"].map(date_tokens)
    rank2["path_block_hint"]=rank2["path"].map(block_match_from_text)

    # Block overlap based on reported audit times.
    for name,start,end in BLOCKS:
        rank2[f"reported_overlap_{name}"]=(
            rank2["reported_start_utc"].notna() & rank2["reported_end_utc"].notna() &
            (rank2["reported_start_utc"]<end) & (rank2["reported_end_utc"]>start)
        )

    # Candidate files whose path strongly points to one of the known owned blocks.
    ia["block_hint"]=ia["path"].map(block_match_from_text)
    block_candidates=ia[ia["block_hint"]!=""].copy()
    # Join authority result to see whether known-block files were ranked 0/1/2.
    joincols=["path","actual_schema","authority_type","authority_label","authority_rank",
              "rows","start_utc","end_utc","decode_status","decode_error","columns"]
    avail=[c for c in joincols if c in ab.columns]
    merged=block_candidates.merge(ab[avail],on="path",how="left",suffixes=("_x3a","_x3b"))
    merged["authority_rank"]=pd.to_numeric(merged.get("authority_rank",""),errors="coerce").fillna(-1).astype(int)

    # Inspect every rank>=2 file plus every path-hinted block candidate, deduped.
    paths={}
    for _,r in rank2.iterrows():
        paths[str(r["path"])]=r.get("x3a_classification","")
    for _,r in block_candidates.iterrows():
        paths[str(r["path"])]=r.get("classification","")
    inspected=[]
    for p,cl in sorted(paths.items()):
        rec=inspect_candidate(Path(p),cl)
        rec["block_hint"]=block_match_from_text(p)
        # attach x3b authority
        z=ab[ab["path"]==p]
        if len(z):
            rr=z.iloc[0]
            rec["x3b_authority_rank"]=int(pd.to_numeric(rr["authority_rank"],errors="coerce") or 0)
            rec["x3b_authority_type"]=rr.get("authority_type","")
            rec["x3b_start_utc"]=rr.get("start_utc","")
            rec["x3b_end_utc"]=rr.get("end_utc","")
        else:
            rec["x3b_authority_rank"]=-1
            rec["x3b_authority_type"]="NOT_IN_X3B"
            rec["x3b_start_utc"]="";rec["x3b_end_utc"]=""
        inspected.append(rec)
    insp=pd.DataFrame(inspected)

    # Heuristic schema-alias detector on known block files.
    def alias_flag(row):
        cols=str(row.get("market_columns","")).lower()
        if not cols: return ""
        has_bid="bid" in cols
        has_ask="ask" in cols
        has_time=("ts_" in cols or "time" in cols or "date" in cols)
        has_px=("price" in cols or "_px" in cols or "bid" in cols or "ask" in cols)
        has_sz=("size" in cols or "qty" in cols or "_sz" in cols)
        if has_bid and has_ask and has_time and has_px and has_sz and int(row.get("x3b_authority_rank",-1))<2:
            return "POSSIBLE_SCHEMA_ALIAS_GAP"
        return ""
    if len(insp):
        insp["alias_flag"]=insp.apply(alias_flag,axis=1)
    else:
        insp["alias_flag"]=[]

    block_ins=insp[insp["block_hint"]!=""].copy()
    alias_count=int((block_ins["alias_flag"]=="POSSIBLE_SCHEMA_ALIAS_GAP").sum()) if len(block_ins) else 0
    rank2_block_hint=int((block_ins["x3b_authority_rank"]>=2).sum()) if len(block_ins) else 0

    # How many X10.3A known-block candidates, by classification and rank.
    summary=[]
    if len(merged):
        for (block,cl,rank),g in merged.groupby(["block_hint","classification","authority_rank"],dropna=False):
            summary.append({"block_hint":block,"classification":cl,"x3b_authority_rank":int(rank),"files":len(g)})
    summary_df=pd.DataFrame(summary)

    run=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rank_csv=RUNS/f"X10_3C_R13_RANK2_WINDOWS_{run}.csv"
    cand_csv=RUNS/f"X10_3C_R13_KNOWN_BLOCK_CANDIDATES_{run}.csv"
    insp_csv=RUNS/f"X10_3C_R13_FILE_LEVEL_INSPECTION_{run}.csv"
    sum_csv=RUNS/f"X10_3C_R13_BLOCK_AUTHORITY_COUNTS_{run}.csv"
    rank2.to_csv(rank_csv,index=False)
    merged.to_csv(cand_csv,index=False)
    insp.to_csv(insp_csv,index=False)
    summary_df.to_csv(sum_csv,index=False)

    # Diagnose.
    reported_block_overlaps=0
    for name,_,_ in BLOCKS:
        reported_block_overlaps += int(rank2[f"reported_overlap_{name}"].sum())
    if reported_block_overlaps==0 and len(block_candidates)>0 and rank2_block_hint==0:
        if alias_count>0:
            diagnosis="KNOWN_BLOCK_FILES_EXIST_BUT_AUTHORITY_RANKING_MISSED_SCHEMA_ALIASES"
        else:
            diagnosis="KNOWN_BLOCK_FILES_EXIST_BUT_RANK2_FILES_ARE_DIFFERENT_DATASET_OR_CLOCK_DECODE"
    elif reported_block_overlaps>0:
        diagnosis="RANK2_WINDOWS_DO_OVERLAP_KNOWN_BLOCKS_MAPPING_LAYER_NEEDS_RECHECK"
    else:
        diagnosis="FILE_LEVEL_REVIEW_REQUIRED"

    txt=RUNS/f"X10_3C_R13_AUTHORITY_PROBE_SUMMARY_{run}.txt"
    lines=[
        "="*132,
        "FLIP FLOP X10.3C-R1.3 FILE-LEVEL AUTHORITY PROBE",
        "="*132,
        "STATUS: PASS",
        "",
        "INPUTS",
        f"X10.3A inventory: {inv}",
        f"X10.3B audit:     {audit}",
        "",
        "COUNTS",
        f"X10.3B rank>=2 authority files:       {len(rank2)}",
        f"Known-block candidates from X10.3A:   {len(block_candidates)}",
        f"Known-block files with rank>=2:       {rank2_block_hint}",
        f"Possible schema-alias gaps:            {alias_count}",
        f"Reported rank2 overlaps with blocks:   {reported_block_overlaps}",
        "",
        "RANK>=2 AUTHORITY WINDOWS",
    ]
    for _,r in rank2.iterrows():
        lines += [
            f"FILE: {r['path']}",
            f"  schema/type/rank: {r.get('actual_schema','')} | {r.get('authority_type','')} | {r['authority_rank_num']}",
            f"  reported UTC:     {r.get('start_utc','')} -> {r.get('end_utc','')}",
            f"  reported ET:      {r.get('reported_start_et','')} -> {r.get('reported_end_et','')}",
            f"  filename dates:   {r.get('filename_date_tokens','')}",
            f"  path block hint:  {r.get('path_block_hint','')}",
        ]
    lines += ["","KNOWN-BLOCK FILES / AUTHORITY"]
    if len(block_ins):
        for _,r in block_ins.iterrows():
            lines += [
                f"FILE: {r['path']}",
                f"  block:            {r.get('block_hint','')}",
                f"  class/parser:     {r.get('classification','')} | {r.get('parser','')}",
                f"  X3B rank/type:    {r.get('x3b_authority_rank','')} | {r.get('x3b_authority_type','')}",
                f"  decoded schema:   {r.get('schema','')}",
                f"  decoded UTC:      {r.get('candidate_start_utc','')} -> {r.get('candidate_end_utc','')}",
                f"  market columns:   {r.get('market_columns','')[:500]}",
                f"  alias flag:       {r.get('alias_flag','')}",
                f"  note:             {r.get('decode_note','')}",
            ]
    else:
        lines.append("NONE FOUND BY PATH HINT")
    lines += [
        "",
        f"DIAGNOSIS: {diagnosis}",
        "",
        "INTERPRETATION",
        "If known-block files exist but rank>=2 files are different, X10.3B authority detection is selecting the wrong subset.",
        "If a known-block file exposes bid/ask/time/size columns but rank<2, the schema detector needs an alias-aware patch.",
        "If decoded event dates differ from filename/block dates, timestamp decoding must be corrected before replay.",
        "",
        "GOVERNANCE",
        "Frozen V3.6.72 modified: NO",
        "X10.2 modified: NO",
        "Target geometry modified: NO",
        "Replay performed: NO",
        "Live routing: LOCKED",
        "="*132,
    ]
    txt.write_text("\n".join(lines),encoding="utf-8")
    latest=BASE/"LATEST_X10_3C_R13_AUTHORITY_PROBE_SUMMARY.txt"
    latest.write_text(txt.read_text(encoding="utf-8"),encoding="utf-8")

    print("="*94)
    print("FLIP FLOP X10.3C-R1.3 FILE-LEVEL AUTHORITY PROBE")
    print("STATUS: PASS")
    print(f"Rank>=2 files: {len(rank2)}")
    print(f"Known-block candidates: {len(block_candidates)}")
    print(f"Known-block rank>=2: {rank2_block_hint}")
    print(f"Schema-alias gaps: {alias_count}")
    print(f"Diagnosis: {diagnosis}")
    print("Replay performed: NO")
    print("Frozen V3.6.72 modified: NO")
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
