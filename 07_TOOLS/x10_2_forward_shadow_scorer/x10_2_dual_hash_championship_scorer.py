#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, math, os, sys, traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

EXPECTED_PARENT_SHA256 = "F14D59DB4F401E7E7A275249D2F50BBB4231669D8D9FBE93DA085387C865D23B"
EXPECTED_DECISION_SHA256 = "3747EC5B12535E3F7EE0E24C57D8DCD07143F4EA17943840BF2E13F2393BC000"
EXPECTED_SYNC = "PAP-FWD-S2W1-S100-W80-P80-K80-R06"
ET = ZoneInfo("America/New_York")
CUTOFF = datetime.fromisoformat("2026-08-08T00:08:00-04:00")
ALPHAS = (0.00, 0.10, 0.25, 0.35, 0.50, 0.75)
CHALLENGERS = ("A_CURRENT", "B_CORE_TIER", "C_SIGNAL_SCALE")
QS = (1,2,3,4,5,6)
JUDGED_QS = (2,3,4,5,6)

MIN_TOTAL = 90
MIN_ROUTE = {"NY":30, "WEEKLY":8, "PREMIUM":8, "WEAK":8}
PRIMARY_ALPHA = 0.35
SECONDARY_ALPHA = 0.50

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def parse_dt(s: str) -> datetime:
    s=s.strip()
    if s.endswith("Z"): s=s[:-1]+"+00:00"
    dt=datetime.fromisoformat(s)
    if dt.tzinfo is None: dt=dt.replace(tzinfo=ET)
    return dt.astimezone(ET)

def route_from_signal(sig: str) -> str:
    u=sig.upper()
    if "WEEKLY" in u: return "WEEKLY"
    if "PREMIUM" in u: return "PREMIUM"
    if "WEAK" in u: return "WEAK"
    if " NY" in u or "NY|" in u: return "NY"
    return "OTHER"

def side_from_signal(sig: str):
    u=sig.upper()
    if "[CC] BUY " in u: return "BUY"
    if "[CC] SELL " in u: return "SELL"
    return None

def sync_from_signal(sig: str):
    return sig.split("|",1)[1].strip() if "|" in sig else None

@dataclass(frozen=True)
class Entry:
    trade_no:int
    ts:datetime
    route:str
    side:str
    sync:str
    qty:float
    pnl:float
    unit_pnl:float

@dataclass
class Candidate:
    path:Path
    side:str
    sync:str
    entries:list[Entry]
    mtime:float

REQUIRED={"Trade number","Type","Date and time","Signal","Size (qty)","Net PnL USD"}

def parse_candidate(path: Path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader=csv.DictReader(f)
            if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
                return None
            entries=[]; sides=set(); syncs=set()
            for row in reader:
                if not str(row.get("Type","")).startswith("Entry"):
                    continue
                sig=str(row.get("Signal",""))
                side=side_from_signal(sig); sync=sync_from_signal(sig)
                if not side or not sync: continue
                qty=abs(float(row["Size (qty)"]))
                if qty<=0: raise ValueError("Non-positive qty")
                pnl=float(row["Net PnL USD"])
                ts=parse_dt(row["Date and time"])
                route=route_from_signal(sig)
                entries.append(Entry(int(float(row["Trade number"])),ts,route,side,sync,qty,pnl,pnl/qty))
                sides.add(side); syncs.add(sync)
        if not entries or len(sides)!=1 or len(syncs)!=1: return None
        entries.sort(key=lambda e:(e.ts,e.trade_no))
        return Candidate(path,next(iter(sides)),next(iter(syncs)),entries,path.stat().st_mtime)
    except Exception:
        return None

def choose_pair(downloads: Path):
    cands=[c for p in downloads.glob("*.csv") if (c:=parse_candidate(p)) is not None]
    buys=[c for c in cands if c.side=="BUY" and c.sync==EXPECTED_SYNC]
    sells=[c for c in cands if c.side=="SELL" and c.sync==EXPECTED_SYNC]
    pairs=[]
    for b in buys:
        bk=[(e.ts,e.route) for e in b.entries]
        for s in sells:
            if len(b.entries)!=len(s.entries): continue
            if bk != [(e.ts,e.route) for e in s.entries]: continue
            pairs.append(((b.entries[-1].ts,len(b.entries),min(b.mtime,s.mtime)),b,s))
    if not pairs:
        raise RuntimeError("No exact synchronized BUY/SELL export pair found in Downloads.")
    pairs.sort(key=lambda x:x[0], reverse=True)
    return pairs[0][1],pairs[0][2]

LEDGER_FIELDS=["entry_time_et","route","sync","buy_unit_pnl","sell_unit_pnl",
               "buy_native_qty","sell_native_qty","buy_trade_no","sell_trade_no"]

def pair_rows(b:Candidate,s:Candidate):
    rows=[]
    for be,se in zip(b.entries,s.entries):
        if be.ts!=se.ts or be.route!=se.route: raise RuntimeError("BUY/SELL alignment failure")
        if be.sync!=se.sync or be.sync!=EXPECTED_SYNC: raise RuntimeError("SYNC failure")
        rows.append({
            "entry_time_et":be.ts.isoformat(),"route":be.route,"sync":be.sync,
            "buy_unit_pnl":be.unit_pnl,"sell_unit_pnl":se.unit_pnl,
            "buy_native_qty":be.qty,"sell_native_qty":se.qty,
            "buy_trade_no":be.trade_no,"sell_trade_no":se.trade_no
        })
    return rows

def key_of(r): return (r["entry_time_et"],r["route"])

def load_ledger(path:Path):
    if not path.exists(): return []
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    for r in rows:
        for k in ("buy_unit_pnl","sell_unit_pnl","buy_native_qty","sell_native_qty"): r[k]=float(r[k])
        for k in ("buy_trade_no","sell_trade_no"): r[k]=int(float(r[k]))
    return rows

def write_ledger(path:Path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=LEDGER_FIELDS); w.writeheader()
        for r in rows: w.writerow({k:r[k] for k in LEDGER_FIELDS})
    tmp.replace(path)

def reconcile(existing,incoming):
    old={key_of(r):r for r in existing}
    new={key_of(r):r for r in incoming}
    if len(new)!=len(incoming): raise RuntimeError("Duplicate incoming forward key")
    for k,r in old.items():
        if k not in new: raise RuntimeError(f"FORWARD LEDGER GAP: prior session missing: {k}")
        nr=new[k]
        if nr["sync"]!=r["sync"]: raise RuntimeError(f"FORWARD MUTATION sync: {k}")
        if abs(float(nr["buy_unit_pnl"])-float(r["buy_unit_pnl"]))>0.005: raise RuntimeError(f"FORWARD MUTATION BUY PnL: {k}")
        if abs(float(nr["sell_unit_pnl"])-float(r["sell_unit_pnl"]))>0.005: raise RuntimeError(f"FORWARD MUTATION SELL PnL: {k}")
    merged=sorted(incoming,key=lambda r:r["entry_time_et"])
    return merged,len(set(new)-set(old))

def quantities(ch,route,q):
    if ch=="A_CURRENT":
        if route in ("NY","WEEKLY","PREMIUM"): return q,q
        if route=="WEAK": return 1,1
        return 0,0
    if ch=="B_CORE_TIER":
        if route in ("NY","WEEKLY"): return q,q
        if route=="PREMIUM": return 1,1
        return 0,0
    if ch=="C_SIGNAL_SCALE":
        if route=="NY": return 1,q
        if route=="WEEKLY": return q,1
        if route=="PREMIUM": return q,1
        if route=="WEAK": return 1,1
        return 0,0
    raise ValueError(ch)

def scenario(rows,ch,q,alpha):
    vals=[]
    for r in rows:
        bq,sq=quantities(ch,r["route"],q)
        base=float(r["buy_unit_pnl"])*bq+float(r["sell_unit_pnl"])*sq
        bt=alpha*max(bq-1,0); st=alpha*max(sq-1,0)
        drag=10.0*(bq*bt+sq*st) # entry+exit, $5/tick
        vals.append(base-drag)
    return vals

def metrics(vals):
    vals=list(map(float,vals)); n=len(vals)
    if not n: return {"n":0,"net":0.0,"pf":None,"dd":0.0,"worst":None,"best":None,"r25":None,"r50":None,"r100":None}
    gp=sum(v for v in vals if v>0); gl=sum(v for v in vals if v<0)
    pf=gp/abs(gl) if gl<0 else math.inf
    eq=peak=0.0; mdd=0.0
    for v in vals:
        eq+=v; peak=max(peak,eq); mdd=min(mdd,eq-peak)
    def wr(k):
        if n<k:return None
        cur=sum(vals[:k]); worst=cur
        for i in range(k,n):
            cur+=vals[i]-vals[i-k]; worst=min(worst,cur)
        return worst
    return {"n":n,"net":sum(vals),"pf":pf,"dd":-mdd,"worst":min(vals),"best":max(vals),
            "r25":wr(25),"r50":wr(50),"r100":wr(100)}

def eff(m):
    if m["dd"]>0: return m["net"]/m["dd"]
    if m["net"]>0: return math.inf
    if m["net"]<0: return -math.inf
    return 0.0

def pf_num(x):
    if x is None:return float("nan")
    return x

def route_counts(rows):
    d={"NY":0,"WEEKLY":0,"PREMIUM":0,"WEAK":0,"OTHER":0}
    for r in rows:d[r["route"]]=d.get(r["route"],0)+1
    return d

def sample_ready(rows):
    rc=route_counts(rows)
    return len(rows)>=MIN_TOTAL and all(rc.get(k,0)>=v for k,v in MIN_ROUTE.items())

def championship(rows):
    rc=route_counts(rows)
    ready=sample_ready(rows)
    gates={
        "sample_total":len(rows)>=MIN_TOTAL,
        "sample_NY":rc.get("NY",0)>=MIN_ROUTE["NY"],
        "sample_WEEKLY":rc.get("WEEKLY",0)>=MIN_ROUTE["WEEKLY"],
        "sample_PREMIUM":rc.get("PREMIUM",0)>=MIN_ROUTE["PREMIUM"],
        "sample_WEAK":rc.get("WEAK",0)>=MIN_ROUTE["WEAK"],
    }
    details=[]
    if not ready:
        return "ACCUMULATING",gates,details

    c_m={}
    a_m={}
    b_m={}
    for q in JUDGED_QS:
        a=metrics(scenario(rows,"A_CURRENT",q,PRIMARY_ALPHA))
        b=metrics(scenario(rows,"B_CORE_TIER",q,PRIMARY_ALPHA))
        c=metrics(scenario(rows,"C_SIGNAL_SCALE",q,PRIMARY_ALPHA))
        a_m[q]=a; b_m[q]=b; c_m[q]=c

    # Frozen catastrophic rejection rule. Applied at ANY judged Q2-Q6.
    reject_any=any(c_m[q]["net"]<0 or (c_m[q]["pf"] is not None and c_m[q]["pf"]<1.00) for q in JUDGED_QS)

    all_net_pos=all(c_m[q]["net"]>0 for q in JUDGED_QS)
    all_pf_130=all(c_m[q]["pf"] is not None and c_m[q]["pf"]>=1.30 for q in JUDGED_QS)
    pf_beats=sum(c_m[q]["pf"]>a_m[q]["pf"] and c_m[q]["pf"]>b_m[q]["pf"] for q in JUDGED_QS)
    dd_beats=sum(c_m[q]["dd"]<a_m[q]["dd"] and c_m[q]["dd"]<b_m[q]["dd"] for q in JUDGED_QS)
    eff_beats=sum(eff(c_m[q])>eff(a_m[q]) and eff(c_m[q])>eff(b_m[q]) for q in JUDGED_QS)
    retain=sum(c_m[q]["net"]>=0.70*max(a_m[q]["net"],b_m[q]["net"]) for q in JUDGED_QS)

    c50=metrics(scenario(rows,"C_SIGNAL_SCALE",6,SECONDARY_ALPHA))
    secondary=(c50["net"]>0 and c50["pf"] is not None and c50["pf"]>=1.20)

    gates.update({
        "C_net_positive_every_Q2_Q6":all_net_pos,
        "C_PF_ge_1_30_every_Q2_Q6":all_pf_130,
        "C_PF_beats_both_ge_4_of_5":pf_beats>=4,
        "C_DD_beats_both_ge_4_of_5":dd_beats>=4,
        "C_eff_beats_both_ge_4_of_5":eff_beats>=4,
        "C_retains_70pct_best_control_ge_4_of_5":retain>=4,
        "C_Q6_alpha50_net_positive":c50["net"]>0,
        "C_Q6_alpha50_PF_ge_1_20":c50["pf"] is not None and c50["pf"]>=1.20,
    })
    details=[
        ("PF_BEATS_COUNT",pf_beats),("DD_BEATS_COUNT",dd_beats),
        ("EFF_BEATS_COUNT",eff_beats),("RETENTION_COUNT",retain),
        ("C_Q6_ALPHA50_NET",c50["net"]),("C_Q6_ALPHA50_PF",c50["pf"])
    ]

    if reject_any:
        return "REJECT_SIGNAL_SCALE",gates,details
    earned=all([
        all_net_pos,all_pf_130,pf_beats>=4,dd_beats>=4,eff_beats>=4,retain>=4,secondary
    ])
    if earned:return "SIGNAL_SCALE_EARNED_CANDIDATE",gates,details
    return "INCONCLUSIVE",gates,details

def fm(x):
    return "N/A" if x is None else f"${x:,.2f}"
def fp(x):
    if x is None:return "N/A"
    if math.isinf(x):return "INF"
    return f"{x:.3f}"

def write_scenarios(path,rows):
    fields=["challenger","Q","alpha","sessions","net","PF","closed_DD","worst","roll25","roll50","roll100","net_DD_efficiency"]
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for ch in CHALLENGERS:
            for q in QS:
                for a in ALPHAS:
                    m=metrics(scenario(rows,ch,q,a))
                    w.writerow({
                        "challenger":ch,"Q":q,"alpha":f"{a:.2f}","sessions":m["n"],
                        "net":f"{m['net']:.2f}",
                        "PF":"" if m["pf"] is None else ("INF" if math.isinf(m["pf"]) else f"{m['pf']:.6f}"),
                        "closed_DD":f"{m['dd']:.2f}",
                        "worst":"" if m["worst"] is None else f"{m['worst']:.2f}",
                        "roll25":"" if m["r25"] is None else f"{m['r25']:.2f}",
                        "roll50":"" if m["r50"] is None else f"{m['r50']:.2f}",
                        "roll100":"" if m["r100"] is None else f"{m['r100']:.2f}",
                        "net_DD_efficiency":f"{eff(m):.6f}" if math.isfinite(eff(m)) else str(eff(m))
                    })

def write_gate_csv(path,state,gates,details):
    rows=[("DECISION_STATE",state)]
    rows += [(k,"PASS" if v else "FAIL") for k,v in gates.items()]
    rows += [(k,v) for k,v in details]
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["item","value"]);w.writerows(rows)

def report(parent,decision,b,s,rows,added,state,gates,details):
    rc=route_counts(rows)
    lines=[
        "="*124,
        "FLIP FLOP X10.2 DUAL-HASH FORWARD CHAMPIONSHIP SCORE",
        "="*124,
        "ENGINE STATUS: PASS",
        f"DECISION STATE: {state}",
        "",
        f"Parent protocol SHA256:   {sha256_file(parent)}",
        f"Decision protocol SHA256: {sha256_file(decision)}",
        f"Freeze cutoff: {CUTOFF.isoformat()}",
        "",
        f"BUY source:  {b.path}",
        f"SELL source: {s.path}",
        f"SYNC: {EXPECTED_SYNC}",
        f"Full aligned export sessions: {len(b.entries)}",
        f"Cumulative forward sessions: {len(rows)}",
        f"New sessions this run: {added}",
        f"Coverage: NY={rc.get('NY',0)} | WEEKLY={rc.get('WEEKLY',0)} | PREMIUM={rc.get('PREMIUM',0)} | WEAK={rc.get('WEAK',0)}",
        "",
        "MINIMUM SAMPLE",
        f"TOTAL >=90: {'PASS' if len(rows)>=90 else 'WAIT'}",
        f"NY >=30: {'PASS' if rc.get('NY',0)>=30 else 'WAIT'}",
        f"WEEKLY >=8: {'PASS' if rc.get('WEEKLY',0)>=8 else 'WAIT'}",
        f"PREMIUM >=8: {'PASS' if rc.get('PREMIUM',0)>=8 else 'WAIT'}",
        f"WEAK >=8: {'PASS' if rc.get('WEAK',0)>=8 else 'WAIT'}",
        "",
        "PRIMARY ALPHA 0.35 — Q2-Q6",
    ]
    for q in JUDGED_QS:
        lines.append(f"Q{q}")
        for ch in CHALLENGERS:
            m=metrics(scenario(rows,ch,q,PRIMARY_ALPHA))
            lines.append(f"  {ch:<15} Net {fm(m['net']):>14} | PF {fp(m['pf']):>7} | DD {fm(m['dd']):>12} | Net/DD {eff(m):.3f}")
    lines += ["","SECONDARY ALPHA 0.50 — Q6"]
    for ch in CHALLENGERS:
        m=metrics(scenario(rows,ch,6,SECONDARY_ALPHA))
        lines.append(f"  {ch:<15} Net {fm(m['net']):>14} | PF {fp(m['pf']):>7} | DD {fm(m['dd']):>12}")
    lines += ["","FROZEN GATE SCORECARD"]
    for k,v in gates.items():
        lines.append(f"{k:<48} {'PASS' if v else 'FAIL'}")
    if details:
        lines += ["","DETAIL COUNTS"]
        for k,v in details:
            if isinstance(v,float):
                lines.append(f"{k:<48} {v:.6f}" if math.isfinite(v) else f"{k:<48} {v}")
            else: lines.append(f"{k:<48} {v}")
    lines += [
        "",
        "AUTHORITY",
        "ACCUMULATING = minimum sample incomplete.",
        "SIGNAL_SCALE_EARNED_CANDIDATE = permission to BUILD a side-by-side Pine research candidate only.",
        "INCONCLUSIVE = continue forward evidence with frozen rules.",
        "REJECT_SIGNAL_SCALE = frozen catastrophic rejection rule triggered after minimum sample.",
        "",
        "Frozen V3.6.72 modified: NO",
        "Pine promotion before gate: BLOCKED",
        "Capacity live routing: LOCKED",
        "Forward ledger: APPEND-ONLY",
        "Historical retuning: PROHIBITED",
        "="*124
    ]
    return "\n".join(lines)

def self_test():
    fake=[]
    routes=["NY"]*30+["WEEKLY"]*8+["PREMIUM"]*8+["WEAK"]*8+["NY"]*36
    for i,r in enumerate(routes):
        fake.append({"entry_time_et":f"2026-08-09T00:{i%60:02d}:00-04:00","route":r,"sync":EXPECTED_SYNC,
                     "buy_unit_pnl":10.0,"sell_unit_pnl":10.0,"buy_native_qty":2.0,"sell_native_qty":2.0,
                     "buy_trade_no":i+1,"sell_trade_no":i+1})
    state,g,d=championship(fake)
    assert state in ("SIGNAL_SCALE_EARNED_CANDIDATE","INCONCLUSIVE","REJECT_SIGNAL_SCALE")
    assert quantities("C_SIGNAL_SCALE","NY",6)==(1,6)
    assert quantities("C_SIGNAL_SCALE","WEEKLY",6)==(6,1)
    assert quantities("C_SIGNAL_SCALE","WEAK",6)==(1,1)
    print("DUAL-HASH CHAMPIONSHIP SELF-TEST: PASS")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--self-test",action="store_true");args=ap.parse_args()
    if args.self_test:self_test();return 0

    hq=Path(os.environ.get("FF_HQ",r"C:\FLIP_FLOP_HQ"))
    downloads=Path(os.environ.get("FF_DOWNLOADS",str(Path.home()/"Downloads")))
    base=hq/r"06_REPORTS\forensic\x10_2_forward_shadow"
    parent=base/"X10_2_FROZEN_FORWARD_PROTOCOL.txt"
    decision=base/"X10_2_FROZEN_DECISION_PROTOCOL.txt"
    if not parent.exists():raise RuntimeError(f"Parent protocol missing: {parent}")
    if not decision.exists():raise RuntimeError(f"Decision protocol missing: {decision}")
    ph=sha256_file(parent);dh=sha256_file(decision)
    if ph!=EXPECTED_PARENT_SHA256:raise RuntimeError(f"PARENT HASH FAIL expected {EXPECTED_PARENT_SHA256} actual {ph}")
    if dh!=EXPECTED_DECISION_SHA256:raise RuntimeError(f"DECISION HASH FAIL expected {EXPECTED_DECISION_SHA256} actual {dh}")

    runs=base/"runs";state_dir=base/"state";runs.mkdir(parents=True,exist_ok=True);state_dir.mkdir(parents=True,exist_ok=True)
    b,s=choose_pair(downloads)
    allrows=pair_rows(b,s)
    eligible=[r for r in allrows if parse_dt(r["entry_time_et"])>CUTOFF]

    ledger_path=state_dir/"X10_2_APPEND_ONLY_FORWARD_LEDGER.csv"
    old=load_ledger(ledger_path)
    ledger,added=reconcile(old,eligible)
    write_ledger(ledger_path,ledger)

    decision_state,gates,details=championship(ledger)
    stamp=datetime.now(ET).strftime("%Y%m%d_%H%M%S")
    scen=runs/f"X10_2_CHAMPIONSHIP_SCENARIOS_{stamp}.csv"
    gate=runs/f"X10_2_CHAMPIONSHIP_GATES_{stamp}.csv"
    txt=runs/f"X10_2_CHAMPIONSHIP_SCORE_{stamp}.txt"
    write_scenarios(scen,ledger);write_gate_csv(gate,decision_state,gates,details)
    txt.write_text(report(parent,decision,b,s,ledger,added,decision_state,gates,details),encoding="utf-8")
    (base/"LATEST_X10_2_CHAMPIONSHIP_SCORE.txt").write_text(txt.read_text(encoding="utf-8"),encoding="utf-8")

    print("="*88)
    print("FLIP FLOP X10.2 DUAL-HASH FORWARD CHAMPIONSHIP")
    print("ENGINE STATUS: PASS")
    print(f"DECISION STATE: {decision_state}")
    print(f"Parent SHA256: {ph}")
    print(f"Decision SHA256: {dh}")
    print(f"Eligible forward sessions: {len(ledger)}")
    print(f"New sessions this run: {added}")
    print(f"Report: {txt}")
    print("Frozen V3.6.72 modified: NO")
    print("Live routing: LOCKED")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except SystemExit: raise
    except Exception as e:
        print("ENGINE STATUS: FAIL",file=sys.stderr)
        print(str(e),file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
