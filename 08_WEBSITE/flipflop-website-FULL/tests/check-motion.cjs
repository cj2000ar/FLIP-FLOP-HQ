const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const project = path.resolve(__dirname, '..');
const ts = require(path.join(project, 'node_modules/typescript'));
const frames = new Map();
const observers = [];
const listeners = new Map();
const refs = [];
const effects = [];
let writes = 0, frameId = 0, clock = 0, visible = true;
const media = { matches: false, addEventListener: (_, fn) => listeners.set('motion', fn), removeEventListener() {} };
const node = { setAttribute() { writes++; } };
const svg = { querySelector: () => node, querySelectorAll: () => Array.from({length:45},()=>node) };
const sandbox = {
  console, performance: { now: () => clock },
  document: { hidden: false, addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener() {} },
  matchMedia: () => media,
  requestAnimationFrame: fn => { frames.set(++frameId, fn); return frameId; },
  cancelAnimationFrame: id => frames.delete(id),
  IntersectionObserver: class { constructor(fn) { this.fn=fn; observers.push(this); } observe() { this.fn([{isIntersecting:visible}]); } disconnect() {} },
};
vm.createContext(sandbox);
const react = { useRef: value => { const ref={current:refs.length===0?svg:value}; refs.push(ref); return ref; }, useEffect: fn => effects.push(fn) };
const cache = new Map();
function load(filename, source = fs.readFileSync(filename,'utf8')) {
  if(cache.has(filename)) return cache.get(filename);
  const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
  const exports={}; cache.set(filename,exports);
  const requireLocal = id => id==='react'?react:id==='react/jsx-runtime'?{jsx:()=>null,jsxs:()=>null}:load(path.resolve(path.dirname(filename),id+'.ts'));
  vm.runInContext('(function(require,exports){'+code+'\n})',sandbox)(requireLocal,exports);
  return exports;
}
const page=fs.readFileSync(path.join(project,'src/app/page.tsx'),'utf8');
const pageAst=ts.createSourceFile('page.tsx',page,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const component=pageAst.statements.find(n=>ts.isFunctionDeclaration(n)&&n.name?.text==='MarketMotion').getText(pageAst);
const motionImport="import { createMotionLoop } from './motion-loop';";
const {MarketMotion}=load(path.join(project,'src/app/chart-check.ts'),"import {useRef,useEffect} from 'react';\nconst useLanguage = () => ({ t: (s: string) => s });\n"+motionImport+'\n'+component+'\nexport {MarketMotion};');
MarketMotion({paused:false});
const cleanups=effects.map(fn=>fn()).filter(Boolean);
function tick(count=12){for(let i=0;i<count;i++){clock+=1000/60;const callbacks=[...frames.values()];frames.clear();callbacks.forEach(fn=>fn(clock));}}
tick();const onscreen=writes;
visible=false;observers.forEach(o=>o.fn([{isIntersecting:false}]));writes=0;tick();
const offscreen=writes;
visible=true;observers.forEach(o=>o.fn([{isIntersecting:true}]));writes=0;tick();const resumed=writes;
media.matches=true;listeners.get('motion')?.();tick(1);writes=0;tick();const reducedMotion=writes;const idleFrames=frames.size;
cleanups.forEach(fn=>fn());
console.log(JSON.stringify({onscreenWrites:onscreen,offscreenWrites:offscreen,resumedWrites:resumed,reducedMotionWrites:reducedMotion,idleFrames,pendingAfterCleanup:frames.size}));
if(!onscreen||offscreen||!resumed||reducedMotion||idleFrames||frames.size) process.exitCode=1;
