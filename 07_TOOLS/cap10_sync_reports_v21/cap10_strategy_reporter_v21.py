from __future__ import annotations
from pathlib import Path
from datetime import datetime
import csv, html, math, os, re, sys

ROOT = Path(r"C:\FLIP_FLOP_HQ")
DOWNLOADS = Path.home() / "Downloads"
OUT = ROOT / "06_REPORTS" / "cap10"
OUT.mkdir(parents=True, exist_ok=True)

REQ = ["Trade number","Type","Date and time","Signal","Size (qty)","Net PnL USD","Adverse excursion USD"]

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def classify_worker(rows):
    sig=" ".join((r.get("Signal") or "") for r in rows[:400]).upper()
    buy=sig.count("BUY")
    sell=sig.count("SELL")
    if buy > sell and buy > 0: return "BUY"
    if sell > buy and sell > 0: return "SELL"
    return None

def valid(rows):
    if not rows: return False
    return all(c in rows[0] for c in REQ)

def newest_workers():
    found={"BUY":[], "SELL":[]}
    for p in DOWNLOADS.rglob("*.csv"):
        try:
            rows=read_csv(p)
        except Exception:
            continue
        if not valid(rows):
            continue
        w=classify_worker(rows)
        if w:
            found[w].append((p.stat().st_mtime,p,rows))
    out={}
    for w,items in found.items():
        if items:
            items.sort(reverse=True,key=lambda x:x[0])
            out[w]=items[0]
    return out

def trades(rows):
    by={}
    for r in rows:
        try:
            n=int(float(r["Trade number"]))
        except Exception:
            continue
        d=by.setdefault(n,{})
        typ=(r.get("Type") or "").lower()
        if typ.startswith("entry"): d["entry"]=r
        if typ.startswith("exit"): d["exit"]=r
    out=[]
    for n in sorted(by):
        d=by[n]
        if "entry" not in d or "exit" not in d: continue
        e,x=d["entry"],d["exit"]
        qty=abs(float(e["Size (qty)"]))
        if qty <= 0: continue
        pnl=float(x["Net PnL USD"])
        sig=e["Signal"]
        sync=sig.split("|",1)[1] if "|" in sig else ""
        weak=("WEAK" in sig.upper()) or ("18:30" in sig.upper())
        out.append({
            "n":n,"time":e["Date and time"],"entry_signal":sig,"exit_signal":x["Signal"],
            "qty":qty,"pnl":pnl,"unit":pnl/qty,"adv_unit":float(x["Adverse excursion USD"])/qty,"weak":weak,"sync":sync
        })
    return out

def perf(values, adverse_values=None):
    gp=sum(x for x in values if x>0)
    gl=sum(x for x in values if x<0)
    eq=peak=mdd=0.0
    if adverse_values is None:
        adverse_values=[min(0.0,x) for x in values]
    for x,a in zip(values,adverse_values):
        mdd=min(mdd,eq+a-peak)
        eq+=x
        mdd=min(mdd,eq-peak)
        peak=max(peak,eq)
    return {
        "trades":len(values),"net":sum(values),"gp":gp,"gl":gl,
        "pf":gp/abs(gl) if gl<0 else math.inf,
        "wins":sum(1 for x in values if x>0),
        "losses":sum(1 for x in values if x<0),
        "max_dd":mdd,"worst":min(values) if values else 0.0,
        "best":max(values) if values else 0.0,
    }

def scenario(ts,q,kind):
    if kind=="UNIFORM_QQ":
        mult=[q for _ in ts]
    else:
        mult=[1 if t["weak"] else q for t in ts]
    vals=[t["unit"]*m for t,m in zip(ts,mult)]
    adverse=[t["adv_unit"]*m for t,m in zip(ts,mult)]
    return vals, perf(vals,adverse)

def audited_parity(ts):
    vals=[t["unit"]*(1 if t["weak"] else 2) for t in ts]
    return abs(sum(vals)-sum(t["pnl"] for t in ts)) < 0.01

def write_csv(path, rows):
    if not rows: return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

def main():
    workers=newest_workers()
    if "BUY" not in workers or "SELL" not in workers:
        print("CAP10 REPORTER: fresh BUY + SELL TradingView CSV exports are required.")
        print("Detected:", ", ".join(workers) if workers else "none")
        print("Export each worker's Strategy Tester -> List of Trades CSV into Downloads, then rerun.")
        sys.exit(2)

    bmtime,bpath,brows=workers["BUY"]
    smtime,spath,srows=workers["SELL"]
    bt=trades(brows); st=trades(srows)
    if not bt or not st:
        raise RuntimeError("Could not build complete entry/exit trades from one of the files.")

    buy_times={t["time"] for t in bt}
    sell_times={t["time"] for t in st}
    shared=sorted(buy_times & sell_times)
    bmap={t["time"]:t for t in bt}
    smap={t["time"]:t for t in st}
    full_pair = buy_times == sell_times
    shared_buy=[bmap[t] for t in shared]
    shared_sell=[smap[t] for t in shared]

    buy_sync={t["sync"] for t in bt if t["sync"]}
    sell_sync={t["sync"] for t in st if t["sync"]}
    sync_status="LEGACY_NO_SYNC_TAG"
    if buy_sync or sell_sync:
        sync_status="PASS" if len(buy_sync)==1 and buy_sync==sell_sync else "FAIL"

    rows=[]
    for kind in ["UNIFORM_QQ","STRONG_Q_WEAK1"]:
        for q in range(1,11):
            bv,bp=scenario(bt,q,kind)
            sv,sp=scenario(st,q,kind)
            pairvals=[]
            pairadv=[]
            for t in shared:
                bm=(q if kind=="UNIFORM_QQ" or not bmap[t]["weak"] else 1)
                sm=(q if kind=="UNIFORM_QQ" or not smap[t]["weak"] else 1)
                b=bmap[t]["unit"]*bm
                s=smap[t]["unit"]*sm
                pairvals.append(b+s)
                pairadv.append(bmap[t]["adv_unit"]*bm + smap[t]["adv_unit"]*sm)
            pp=perf(pairvals,pairadv)
            rows.append({
                "Sizing":kind,"Q":q,
                "BUY Net":round(bp["net"],2),"BUY PF":round(bp["pf"],6),"BUY Max DD":round(bp["max_dd"],2),
                "SELL Net":round(sp["net"],2),"SELL PF":round(sp["pf"],6),"SELL Max DD":round(sp["max_dd"],2),
                "PAIR Net (shared)":round(pp["net"],2),"PAIR PF (shared)":round(pp["pf"],6),
                "PAIR Max DD (shared)":round(pp["max_dd"],2),"Shared sessions":len(shared),
                "Pair full coverage":full_pair,
            })

    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_out=OUT/f"CAP10_Q1_Q10_TVDD_STRATEGY_REPORT_{stamp}.csv"
    write_csv(csv_out,rows)

    def money(x): return f"${x:,.2f}"
    trs=[]
    for r in rows:
        trs.append("<tr>" + "".join([
            f"<td>{html.escape(str(r['Sizing']))}</td>",
            f"<td>Q{r['Q']}</td>",
            f"<td>{money(r['BUY Net'])}</td><td>{r['BUY PF']:.3f}</td><td>{money(r['BUY Max DD'])}</td>",
            f"<td>{money(r['SELL Net'])}</td><td>{r['SELL PF']:.3f}</td><td>{money(r['SELL Max DD'])}</td>",
            f"<td>{money(r['PAIR Net (shared)'])}</td><td>{r['PAIR PF (shared)']:.3f}</td><td>{money(r['PAIR Max DD (shared)'])}</td>",
        ]) + "</tr>")

    html_out=OUT/f"CAP10_Q1_Q10_TVDD_STRATEGY_REPORT_{stamp}.html"
    html_out.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<title>FLIP FLOP CAP10 Strategy Report</title>
<style>
body{{font-family:Arial;background:#111;color:#eee;padding:24px}}
.ok{{color:#55e87a}} .bad{{color:#ff5d5d}} .warn{{color:#ffb84d}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #444;padding:7px;text-align:right}}
th{{background:#222;position:sticky;top:0}}td:first-child,th:first-child{{text-align:left}}
.note{{line-height:1.5;color:#ccc}}
</style></head><body>
<h1>FLIP FLOP CAP10 Q1-Q10 Strategy Report</h1>
<p>BUY: {html.escape(str(bpath))}<br>SELL: {html.escape(str(spath))}</p>
<p class="{'ok' if sync_status=='PASS' else 'warn' if sync_status=='LEGACY_NO_SYNC_TAG' else 'bad'}">
Sync profile: {sync_status}</p>
<p>BUY audited 2/1 reconstruction: {'PASS' if audited_parity(bt) else 'FAIL'}<br>
SELL audited 2/1 reconstruction: {'PASS' if audited_parity(st) else 'FAIL'}<br>
Pair coverage: {'FULL' if full_pair else 'OVERLAP ONLY'} ({len(shared)} shared sessions)</p>
<table><thead><tr>
<th>Sizing</th><th>Q</th><th>BUY Net</th><th>BUY PF</th><th>BUY DD</th>
<th>SELL Net</th><th>SELL PF</th><th>SELL DD</th>
<th>PAIR Net</th><th>PAIR PF</th><th>PAIR DD</th>
</tr></thead><tbody>{''.join(trs)}</tbody></table>
<p class="note"><strong>Authority:</strong> This reconstructs Q1-Q10 using each native trade's
per-contract TradingView P/L. It is exact same-fill arithmetic under the exported fills and linear
commission/slippage assumptions. It is not proof that real larger NQ orders would receive identical fills.
If BUY/SELL date coverage differs, pair statistics are overlap-only and are labeled that way.</p>
</body></html>""",encoding="utf-8")

    print("="*106)
    print("FLIP FLOP CAP10 Q1-Q10 REPORTER")
    print("="*106)
    print("STATUS: PASS")
    print("BUY:",bpath)
    print("SELL:",spath)
    print("BUY audited 2/1 reconstruction:", "PASS" if audited_parity(bt) else "FAIL")
    print("SELL audited 2/1 reconstruction:", "PASS" if audited_parity(st) else "FAIL")
    print("SYNC PROFILE:",sync_status)
    print("PAIR COVERAGE:", "FULL" if full_pair else f"OVERLAP ONLY ({len(shared)} shared)")
    print("CSV:",csv_out)
    print("HTML:",html_out)
    print("="*106)

    txt_out=OUT/f"CAP10_Q1_Q10_TVDD_STRATEGY_REPORT_{stamp}.txt"
    txt_lines=[
        "="*106,
        "FLIP FLOP CAP10 Q1-Q10 TV-DD STRATEGY REPORT",
        "="*106,
        f"BUY: {bpath}",
        f"SELL: {spath}",
        f"BUY audited 2/1 reconstruction: {'PASS' if audited_parity(bt) else 'FAIL'}",
        f"SELL audited 2/1 reconstruction: {'PASS' if audited_parity(st) else 'FAIL'}",
        f"SYNC PROFILE: {sync_status}",
        f"PAIR COVERAGE: {'FULL' if full_pair else f'OVERLAP ONLY ({len(shared)} shared)'}",
        "",
        "Q1-Q10 RESULTS",
    ]
    for r in rows:
        txt_lines.append(
            f"{r['Sizing']:<18} | Q{r['Q']:<2} | "
            f"BUY {r['BUY Net']:>11,.2f} PF {r['BUY PF']:.3f} DD {r['BUY Max DD']:>10,.2f} | "
            f"SELL {r['SELL Net']:>11,.2f} PF {r['SELL PF']:.3f} DD {r['SELL Max DD']:>10,.2f} | "
            f"PAIR {r['PAIR Net (shared)']:>11,.2f} PF {r['PAIR PF (shared)']:.3f} DD {r['PAIR Max DD (shared)']:>10,.2f}"
        )
    txt_lines += [
        "",
        "AUTHORITY",
        "Same-fill TradingView arithmetic from native Deep Backtesting exports.",
        "Not proof of identical live fills, slippage, margin, or market impact at larger NQ size.",
        "="*106,
    ]
    txt_out.write_text("\n".join(txt_lines),encoding="utf-8")
    print("TXT:",txt_out)
    os.startfile(html_out)
    os.system(f'notepad.exe "{txt_out}"')


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print("CAP10 REPORTER FAILED")
        print(type(exc).__name__ + ": " + str(exc))
        sys.exit(1)
