const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname, '..'),ts=require(path.join(root,'node_modules/typescript'));
const file=path.join(root,'src/app/site-language.tsx');
const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
async function test(saved,blocked=false){
  const values=new Map([['hq-website-language',saved]]);let subscribe,getSnapshot,serverSnapshot,failLanguage='';
  const mock={createContext:()=>({Provider:'provider'}),useEffect:()=>{},useMemo:fn=>fn(),useSyncExternalStore:(sub,get,server)=>{subscribe=sub;getSnapshot=get;serverSnapshot=server;return get();}};
  const ctx={exports:{},queueMicrotask,localStorage:{getItem:key=>values.get(key),setItem:(key,value)=>{if(blocked)throw Error('blocked storage');values.set(key,value);}}};
  ctx.require=id=>id==='react'?mock:id==='react/jsx-runtime'?{jsx:(type,props)=>({type,props})}:id==='lucide-react'?{}:id===`./locales/${failLanguage}.json`?(()=>{throw Error('offline');})():require(path.resolve(path.dirname(file),id));
  vm.createContext(ctx);vm.runInContext(code,ctx,{filename:file});
  const render=()=>ctx.exports.LanguageProvider({children:null}).props.value;
  assert.equal(render().locale,'es');assert.equal(serverSnapshot().locale,'es');
  const dispose=subscribe(()=>{});await new Promise(setImmediate);
  assert.equal(getSnapshot().locale,saved==='en'?'en':'es');
  for(const locale of ['fr','de','pt','it','en','es']){render().setLocale(locale);await new Promise(setImmediate);assert.equal(getSnapshot().locale,locale);assert.equal(render().busy,false);if(!blocked)assert.equal(values.get('hq-website-language'),locale);}
  render().setLocale('fr');render().setLocale('de');await new Promise(setImmediate);assert.equal(getSnapshot().locale,'de','Last selection wins');
  failLanguage='it';render().setLocale('it');await new Promise(setImmediate);assert.equal(getSnapshot().locale,'de');assert.equal(render().error,true);assert.equal(render().busy,false);
  dispose();console.log(`PASS locale store: saved=${saved}, storageBlocked=${blocked}, persistence, race handling and failed-load recovery`);
}
test('en').then(()=>test('invalid',true)).catch(error=>{console.error(error);process.exitCode=1;});
