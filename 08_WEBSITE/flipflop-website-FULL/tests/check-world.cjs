const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname, '..'),ts=require(path.join(root,'node_modules/typescript'));
function load(file){const src=fs.readFileSync(path.join(root,'src/app',file),'utf8');const code=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;const context={exports:{}};vm.createContext(context);vm.runInContext(code,context);return context.exports;}
const {sampleWorldJourney}=load('world-journey.ts'),{drawWorldAtmosphere}=load('world-atmosphere.ts');
const anchors=[0,850,1900,3000,5200,6100,7450];
const frames=anchors.map(scroll=>sampleWorldJourney(scroll,anchors));
assert.equal(frames[0].earth,1);assert.equal(frames[6].earth,1);assert(frames[0].tunnel>0);assert.equal(frames[1].tunnel,0); for(const scroll of [850,1200,1699]){const hold=sampleWorldJourney(scroll,anchors,1700);assert.equal(hold.earth,1);assert.equal(hold.tunnel,0);assert.equal(hold.orbit,0);}assert.equal(frames[3].flow,1);assert.equal(frames[5].flow,1);
for(let i=1;i<anchors.length;i++){const before=sampleWorldJourney(anchors[i]-.001,anchors),after=sampleWorldJourney(anchors[i]+.001,anchors);for(const key of Object.keys(before))assert(Math.abs(before[key]-after[key])<.0001,'Discontinuous '+key);}
for(const scroll of [0,200,1500,2900,6200,8300,-100]){const a=sampleWorldJourney(scroll,anchors);for(const key of ['earth','tunnel','orbit','flow','digits'])assert(a[key]>=0&&a[key]<=1);assert.deepEqual(a,sampleWorldJourney(scroll,anchors));}
let strokes=0,points=0;
const finite=(...args)=>{assert(args.every(Number.isFinite),'Non-finite canvas geometry');};
const ctx={clearRect:finite,beginPath(){},closePath(){},moveTo:finite,lineTo:finite,stroke(){strokes++;},fillRect(...args){finite(...args);points++;},fillText(text,...args){assert(text.length>0);finite(...args);},set globalAlpha(value){assert(Number.isFinite(value)&&value>=0&&value<=1,'Invalid opacity '+value);},set lineWidth(value){assert(Number.isFinite(value)&&value>0);}};
for(const [width,height] of [[320,700],[768,1024],[1440,900],[2560,1440]])for(const frame of frames)for(const time of [0,15,180])drawWorldAtmosphere(ctx,width,height,time,frame,['#b8bdc6','#599a67','#e14237']);
console.log('PASS: seven chapters, continuous reversible path, visible opening tunnel, pure-black palette, finite geometry at four viewport sizes. '+strokes+' strokes / '+points+' particle draws.');
