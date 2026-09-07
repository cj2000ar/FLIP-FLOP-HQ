const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm'), assert=require('node:assert/strict');
const root=path.resolve(__dirname, '..'), ts=require(path.join(root,'node_modules/typescript'));
const React=require(path.join(root,'node_modules/react'));
const {renderToStaticMarkup}=require(path.join(root,'node_modules/react-dom/server'));
const sourceFiles=['page.tsx','access-details.tsx','access-request.tsx','product-showcase.tsx','product-chart.tsx','experience-demo.tsx','trade-simulator.tsx','demo/page.tsx'];
const es=require(path.join(root,'src/app/locales/es.json'));
let active='es', dictionary=es, called=new Set(), cache=new Map(), view='overview', automationIndex=0;
let experienceView='chart', experiencePlan=50, experiencePC='windows';
function translate(source){called.add(source);assert(Object.hasOwn(dictionary,source),`Missing ${active}: ${source}`);return dictionary[source];}
function load(filename){
  if(cache.has(filename))return cache.get(filename);
  const code=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
  const module={exports:{}};cache.set(filename,module.exports);
  function local(id){
    if(id==='react')return {...React,useState:initial=>React.useState(filename.endsWith('automation-story.tsx')?automationIndex:filename.endsWith('experience-demo.tsx')?(initial==='chart'?experienceView:initial===50?experiencePlan:initial==='windows'?experiencePC:initial):initial==='overview'?view:initial)};
    if(id.endsWith('/site-language'))return {useLanguage:()=>({locale:active,t:translate}),LanguageProvider:({children})=>children,LanguageSelector:()=>React.createElement('span',null,active)};
    if(id==='next/link')return ({children,...props})=>React.createElement('a',props,children);
    if(id==='next/image')return ({unoptimized,fill,priority,...props})=>React.createElement('img',props);
    if(id.startsWith('.')){let p=path.resolve(path.dirname(filename),id);p+=fs.existsSync(p+'.tsx')?'.tsx':'.ts';return load(p);}
    return require(path.join(root,'node_modules',id));
  }
  vm.runInThisContext('(function(require,module,exports){'+code+'\n})',{filename})(local,module,module.exports);
  return module.exports;
}
for(const locale of ['es','en','pt','fr','it','de']){
  active=locale;dictionary=require(path.join(root,'src/app/locales',locale+'.json'));called=new Set();cache=new Map();
  assert.deepEqual(Object.keys(dictionary).sort(),Object.keys(es).sort(),'Dictionary coverage '+locale);
  const {default:Page}=load(path.join(root,'src/app/page.tsx'));
  const markup=renderToStaticMarkup(React.createElement(Page));
  assert(markup.includes('cjar292@gmail.com'));
  for(const id of ['producto','como-funciona','requisitos','reparto','condiciones','acceso'])assert(markup.includes(`id="${id}"`));
  assert(!/undefined|NaN/.test(markup));
  assert(!markup.includes('saturn-trading.png'));
  assert(markup.includes('earth-intro-mark'));
  const {default:Experience}=load(path.join(root,'src/app/experience-demo.tsx'));
  for(experienceView of ['chart','setup','agreement'])for(experiencePlan of [50,70])for(experiencePC of ['windows','mac']){
    const html=renderToStaticMarkup(React.createElement(Experience,{paused:false,onRequest:()=>{}}));
    assert(!/undefined|NaN/.test(html));
    assert(!html.includes('experience-tabs'));assert(!html.includes('experience-agreement'));
  }
  experienceView='chart';experiencePlan=50;experiencePC='windows';
  const Demo=load(path.join(root,'src/app/demo/page.tsx')).default;
  assert(renderToStaticMarkup(React.createElement(Demo)).includes('trade-simulator'));
  const {default:Showcase}=load(path.join(root,'src/app/product-showcase.tsx'));
  for(view of ['overview','trades','performance','calendar','agents','settings']) renderToStaticMarkup(React.createElement(Showcase,null,React.createElement('span',null,'Chart')));
  view='overview';
  const {default:Automation}=load(path.join(root,'src/app/automation-story.tsx'));
  for(automationIndex of [0,1,2]) {
    const html=renderToStaticMarkup(React.createElement(Automation,{paused:false}));
    assert.equal((html.match(/aria-pressed="true"/g)||[]).length,1);
    assert(html.includes('aria-live="polite"'));
    assert(!/undefined|NaN/.test(html));
  }
  automationIndex=0;
  // Check all literal calls, including views not selected during the initial render.
  for(const file of sourceFiles){
    const sf=ts.createSourceFile(file,fs.readFileSync(path.join(root,'src/app',file),'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
    const walk=n=>{if(ts.isCallExpression(n)&&n.expression.getText(sf)==='t'&&ts.isStringLiteral(n.arguments[0]))translate(n.arguments[0].text);ts.forEachChild(n,walk);};walk(sf);
  }
  // Exercise the real email composer for both commercial modes.
  const source=fs.readFileSync(path.join(root,'src/app/access-request.tsx'),'utf8');
  const ast=ts.createSourceFile('access-request.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  let body='';const find=n=>{if(ts.isFunctionDeclaration(n)&&n.name?.text==='submit')body=n.getText(ast);ts.forEachChild(n,find);};find(ast);assert(body);
  const compiled=ts.transpileModule(body,{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText;
  for(const split of [50,70]){
    const subject=translate('Solicitud de acceso · Flip Flop HQ');
    let draft='';const scope={t:translate,split,FormData:class{constructor(form){this.form=form;}get(k){return this.form[k]??null;}},setDraft:x=>draft=x,setPrepared:()=>{},setCopyState:()=>{},window:{location:{href:''}}};
    vm.createContext(scope);vm.runInContext(compiled+'\nsubmit({name:"  Test & Person  ",email:"test@example.com",experience:"Basics",pc:"Yes",reason:"I want to understand the system & its access terms."});',scope);
    const uri=new URL(scope.window.location.href);assert.equal(uri.protocol,'mailto:');assert.equal(uri.pathname,'cjar292@gmail.com');assert.equal(uri.searchParams.get('subject'),subject);assert.equal(uri.searchParams.get('body'),draft);assert(draft.includes('Test & Person'));assert(draft.includes(split===70?'70%':'50%')||draft.includes(split===70?'70 %':'50 %'));
  }
  console.log(`PASS ${locale}: ${Object.keys(dictionary).length} messages, ${called.size} UI/composer keys exercised, both plans encoded correctly`);
}
console.log('PASS: multilingual server rendering and email preparation. No email was sent.');
