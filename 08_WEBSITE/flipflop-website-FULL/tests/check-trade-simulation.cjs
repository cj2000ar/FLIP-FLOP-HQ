const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname, '..'),ts=require(path.join(root,'node_modules/typescript'));
const code=ts.transpileModule(fs.readFileSync(path.join(root,'src/app/trade-simulation.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const scope={exports:{}};vm.runInNewContext(code,scope);const {demoMarkets,replayTrade,drawTradeChart}=scope.exports;
let count=0,draws=0;
const ctx=new Proxy({}, {get:(o,k)=>o[k]??((...args)=>{for(const n of args)if(typeof n==='number')assert(Number.isFinite(n),k+' coordinate');}),set:(o,k,v)=>{o[k]=v;return true;}});
for(const m of demoMarkets)for(const d of ['long','short'])for(const o of ['tp','sl']){
 const sign=d==='long'?1:-1;
 for(let i=0;i<=100;i++){
  const f=replayTrade(m,d,o,i/100);count++;
  assert.equal(f.closed,i===100);assert.equal(f.candles.length,i===100?60:31+Math.floor(i/100*30));
  for(const c of f.candles){assert(c.high>=Math.max(c.open,c.close));assert(c.low<=Math.min(c.open,c.close));assert(Object.values(c).every(Number.isFinite));}
  assert((f.target-f.entry)*sign>0);assert((f.stop-f.entry)*sign<0);
  if(i<100)for(const c of f.candles.slice(30)){assert(c.high<Math.max(f.stop,f.target));assert(c.low>Math.min(f.stop,f.target));}
  if(i===100){assert(Math.abs(f.riskUnits-(o==='tp'?2:-1))<1e-8);assert(Math.abs(f.current-(o==='tp'?f.target:f.stop))<1e-10);}
  if([0,25,50,100].includes(i))for(const [w,h] of [[250,300],[296,300],[768,350],[1200,410]]){drawTradeChart(ctx,w,h,f,m,{entry:'Entrada'});draws++;}
 }
 assert.equal(replayTrade(m,d,o,-1).progress,0);assert.equal(replayTrade(m,d,o,2).progress,1);assert.equal(replayTrade(m,d,o,NaN).progress,0);
 assert.deepEqual(replayTrade(m,d,o,.5),replayTrade(m,d,o,.5));
}
assert(demoMarkets.some(m=>m.symbol==='MNQ'));
console.log(`PASS ${count} synthetic frames, ${draws} canvas draws at four sizes: long/short, TP/SL, OHLC, barriers, final R, deterministic reset and invalid progress.`);
