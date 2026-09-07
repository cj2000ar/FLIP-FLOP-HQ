const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname, '..'),ts=require(path.join(root,'node_modules/typescript'));
function harness(file){
 let index=0,clock=0,frameId=0,draws=0;const slots=[],pending=[],frames=new Map(),observers=[],listeners=new Map(),cache=new Map();
 function on(k,fn){if(!listeners.has(k))listeners.set(k,new Set());listeners.get(k).add(fn);}function off(k,fn){listeners.get(k)?.delete(fn);}
 const media={matches:false,addEventListener:(k,f)=>on('motion',f),removeEventListener:(k,f)=>off('motion',f)};
 const ctx=new Proxy({clearRect(){draws++;}}, {get:(o,k)=>o[k]??(()=>{}),set:(o,k,v)=>{o[k]=v;return true;}});
 const host={style:{},clientWidth:600,clientHeight:340,getContext:()=>ctx};
 const sandbox={document:{hidden:false,addEventListener:on,removeEventListener:off},matchMedia:()=>media,devicePixelRatio:2,ResizeObserver:class{constructor(fn){this.fn=fn;}observe(){this.fn();}disconnect(){}},IntersectionObserver:class{constructor(fn){this.fn=fn;observers.push(this);}observe(){this.fn([{isIntersecting:true}]);}disconnect(){}},requestAnimationFrame:fn=>{frames.set(++frameId,fn);return frameId;},cancelAnimationFrame:id=>frames.delete(id)};vm.createContext(sandbox);
 const react={useState:init=>{const i=index++;slots[i]??={value:typeof init==='function'?init():init};return[slots[i].value,v=>slots[i].value=typeof v==='function'?v(slots[i].value):v];},useRef:init=>{const i=index++;return(slots[i]??={current:init===null?host:init});},useId:()=>{index++;return'test-range';},useEffect:(fn,deps)=>{const i=index++,old=slots[i];if(!old||deps.some((v,j)=>v!==old.deps[j])){old?.cleanup?.();slots[i]={deps};pending.push(()=>slots[i].cleanup=fn());}}};
 const jsx=(type,props)=>({type,props});
 function load(name){if(cache.has(name))return cache.get(name);const exports={};cache.set(name,exports);const source=fs.readFileSync(path.join(root,'src/app',name),'utf8');const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
 const req=id=>id==='react'?react:id==='react/jsx-runtime'?{jsx,jsxs:jsx}:id==='./site-language'?{useLanguage:()=>({t:s=>s})}:id==='lucide-react'?new Proxy({},{get:()=> 'svg'}):load(id.slice(2)+(fs.existsSync(path.join(root,'src/app',id.slice(2)+'.tsx'))?'.tsx':'.ts'));
 vm.runInContext('(function(require,exports){'+code+'\n})',sandbox)(req,exports);return exports;}
 const Component=load(file).default;let props={},tree;
 const all=(type)=>{const out=[];function walk(n){if(!n||typeof n!=='object')return;if(n.type===type)out.push(n);for(const c of [n.props?.children].flat(Infinity))walk(c);}walk(tree);return out;};
 const text=n=>typeof n==='string'||typeof n==='number'?String(n):[n?.props?.children].flat(Infinity).map(c=>c===undefined?'':text(c)).join('');
 const api={render(p=props){props=p;index=0;tree=Component(props);pending.splice(0).forEach(fn=>fn());return api;},all,text,button(label){const n=all('button').find(n=>text(n)===label||n.props['aria-label']===label);assert(n,'button '+label);return n;},click(label){api.button(label).props.onClick();api.render();},tick(n=60){for(let i=0;i<n;i++){clock+=1000/60;const f=[...frames.values()];frames.clear();f.forEach(fn=>fn(clock));}api.render();},offscreen(v){observers.forEach(o=>o.fn([{isIntersecting:!v}]));},reduced(v){media.matches=v;listeners.get('motion')?.forEach(fn=>fn());api.render();},hide(v){sandbox.document.hidden=v;listeners.get('visibilitychange')?.forEach(fn=>fn());},get draws(){return draws;},get scheduled(){return frames.size;},dispose(){slots.forEach(s=>s?.cleanup?.());assert.equal(frames.size,0);for(const s of listeners.values())assert.equal(s.size,0);}};
 return api;
}

const h=harness('trade-simulator.tsx').render({paused:false});
assert.equal(h.all('button').length,1);assert.equal(h.all('select').length,0);assert.equal(h.all('input').length,0);
h.tick(1300);assert.equal(h.text(h.all('output')[0]),'Operación simulada abierta');h.tick(150);assert.equal(h.text(h.all('output')[0]),'TP alcanzado');
h.tick(200);assert.equal(h.text(h.all('output')[0]),'Operación simulada abierta');assert(h.all('span').some(n=>h.text(n)==='Short'));
h.click('Pausar reproducción');h.tick(2);let draws=h.draws;h.tick(60);assert.equal(h.draws,draws);h.click('Reanudar simulación');h.tick(10);assert(h.draws>draws);
h.offscreen(true);draws=h.draws;h.tick();assert.equal(h.draws,draws);h.offscreen(false);h.tick();assert(h.draws>draws);
h.hide(true);draws=h.draws;h.tick();assert.equal(h.draws,draws);h.hide(false);h.tick();
h.render({paused:true});h.tick(2);draws=h.draws;h.tick();assert.equal(h.draws,draws);assert.equal(h.button('Reanudar simulación').props.disabled,true);
h.render({paused:false});h.reduced(true);h.tick(2);draws=h.draws;h.tick();assert.equal(h.draws,draws);assert.equal(h.button('Reanudar simulación').props.disabled,true);h.reduced(false);
h.tick(1300);assert.equal(h.text(h.all('output')[0]),'SL alcanzado');h.tick(300);assert.equal(h.text(h.all('output')[0]),'Operación simulada abierta');h.dispose();
console.log('PASS automatic playback, repeated TP/SL cycles, one pause control, no manual setup, offscreen/hidden pauses, reduced motion and cleanup.');
