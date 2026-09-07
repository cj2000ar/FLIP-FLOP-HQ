
from pathlib import Path
import csv, html, math, os, sys
from datetime import datetime

ROOT=Path(r"C:\FLIP_FLOP_HQ")
DOWNLOADS=Path.home()/"Downloads"
OUT=ROOT/"06_REPORTS"/"cap10"/"final"
OUT.mkdir(parents=True,exist_ok=True)
REQ=["Trade number","Type","Date and time","Signal","Size (qty)","Net PnL USD","Adverse excursion USD"]

def read(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

def worker(rows):
    s=" ".join((r.get("Signal") or "") for r in rows[:500]).upper()
    b=s.count("BUY"); x=s.count("SELL")
    return "BUY" if b>x else "SELL" if x>b else None

def newest():
    found={"BUY":[],"SELL":[]}
    for p in DOWNLOADS.rglob("*.csv"):
        try: rows=read(p)
        except: continue
        if not rows or not all(k in rows[0] for k in REQ): continue
        w=worker(rows)
        if w: found[w].append((p.stat().st_mtime,p,rows))
    out={}
    for w,v in found.items():
        if v: out[w]=sorted(v,reverse=True,key=lambda z:z[0])[0]
    return out

def trades(rows):
    d={}
    for r in rows:
        try:n=int(float(r["Trade number"]))
        except:continue
        q=d.setdefault(n,{})
        t=(r.get("Type") or "").lower()
        if t.startswith("entry"):q["e"]=r
        elif t.startswith("exit"):q["x"]=r
    out=[]
    for n in sorted(d):
        if "e" not in d[n] or "x" not in d[n]:continue
        e,x=d[n]["e"],d[n]["x"]; qty=abs(float(e["Size (qty)"]))
        sig=e["Signal"]; sync=sig.split("|",1)[1] if "|" in sig else ""
        out.append({"time":e["Date and time"],"unit":float(x["Net PnL USD"])/qty,
                    "adv":float(x["Adverse excursion USD"])/qty,
                    "weak":("WEAK" in sig.upper() or "18:30" in sig.upper()),
                    "sync":sync,"native":float(x["Net PnL USD"])})
    return out

def side(ts,q,kind):
    vals=[]; advs=[]
    for t in ts:
        m=1 if kind=="STRONG_Q_WEAK1" and t["weak"] else q
        vals.append(t["unit"]*m); advs.append(t["adv"]*m)
    gp=sum(v for v in vals if v>0); gl=sum(v for v in vals if v<0)
    eq=peak=0.0;mdd=0.0
    for v,a in zip(vals,advs):
        mdd=min(mdd,eq+a-peak);eq+=v;mdd=min(mdd,eq-peak);peak=max(peak,eq)
    return vals,{"net":sum(vals),"pf":gp/abs(gl) if gl<0 else math.inf,"dd":-mdd}

def pair(b,s,q,kind):
    vals=[]
    for x,y in zip(b,s):
        bm=1 if kind=="STRONG_Q_WEAK1" and x["weak"] else q
        sm=1 if kind=="STRONG_Q_WEAK1" and y["weak"] else q
        vals.append(x["unit"]*bm+y["unit"]*sm)
    gp=sum(v for v in vals if v>0);gl=sum(v for v in vals if v<0)
    eq=peak=0.0;mdd=0.0
    for v in vals:
        eq+=v;peak=max(peak,eq);mdd=min(mdd,eq-peak)
    return {"net":sum(vals),"pf":gp/abs(gl) if gl<0 else math.inf,"closed_dd":-mdd}

def main():
    f=newest()
    if "BUY" not in f or "SELL" not in f:
        raise RuntimeError("Fresh BUY + SELL TradingView List-of-Trades CSVs are required in Downloads.")
    _,bp,br=f["BUY"];_,sp,sr=f["SELL"]
    b=trades(br);s=trades(sr)
    if [x["time"] for x in b] != [x["time"] for x in s]:
        raise RuntimeError("BUY/SELL coverage or timestamps do not match. Full pair report blocked.")
    bs={x["sync"] for x in b if x["sync"]};ss={x["sync"] for x in s if x["sync"]}
    if len(bs)!=1 or bs!=ss:
        raise RuntimeError(f"Sync profile mismatch. BUY={bs} SELL={ss}")
    rows=[]
    for kind in ["STRONG_Q_WEAK1","UNIFORM_QQ"]:
        for q in range(1,11):
            _,B=side(b,q,kind);_,S=side(s,q,kind);P=pair(b,s,q,kind)
            rows.append({"Sizing":kind,"Q":q,"BUY Net":B["net"],"BUY PF":B["pf"],"BUY TV DD":B["dd"],
                         "SELL Net":S["net"],"SELL PF":S["pf"],"SELL TV DD":S["dd"],
                         "PAIR Net":P["net"],"PAIR PF":P["pf"],"PAIR Closed-Equity DD":P["closed_dd"]})
    q2=[r for r in rows if r["Sizing"]=="STRONG_Q_WEAK1" and r["Q"]==2][0]
    if abs(q2["BUY Net"]-sum(x["native"] for x in b))>.01 or abs(q2["SELL Net"]-sum(x["native"] for x in s))>.01:
        raise RuntimeError("Audited 2/1 native reconstruction parity FAILED.")
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    co=OUT/f"FLIP_FLOP_CAP10_FINAL_Q1_Q10_{stamp}.csv"
    with co.open("w",encoding="utf-8-sig",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    to=OUT/f"FLIP_FLOP_CAP10_FINAL_Q1_Q10_{stamp}.txt"
    lines=["="*112,"FLIP FLOP CAP10 FINAL Q1-Q10 REPORT","="*112,"STATUS: PASS",
           f"BUY: {bp}",f"SELL: {sp}",f"SYNC: {next(iter(bs))}",
           f"Sessions: {len(b)}","BUY/SELL timestamps: MATCH","Audited 2/1 parity: PASS","",
           "PAIR DD = CLOSED-EQUITY DD. Exact combined intratrade DD is not claimed.",""]
    for r in rows:
        lines.append(f"{r['Sizing']:<18} Q{r['Q']:<2} | BUY {r['BUY Net']:>11,.2f} PF {r['BUY PF']:.3f} DD {r['BUY TV DD']:>9,.2f} | "
                     f"SELL {r['SELL Net']:>11,.2f} PF {r['SELL PF']:.3f} DD {r['SELL TV DD']:>9,.2f} | "
                     f"PAIR {r['PAIR Net']:>12,.2f} PF {r['PAIR PF']:.3f} CLOSED-DD {r['PAIR Closed-Equity DD']:>9,.2f}")
    to.write_text("\n".join(lines),encoding="utf-8")
    print("\n".join(lines[:12]));print("CSV:",co);print("TXT:",to)
    os.system(f'notepad.exe "{to}"')

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("CAP10 FINAL REPORTER FAILED");print(type(e).__name__+": "+str(e));sys.exit(1)
