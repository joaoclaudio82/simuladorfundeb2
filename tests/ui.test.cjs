/* Testes de fluxo com DOM em memória e API real; não avaliam pixels/layout. */
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { spawn } = require('node:child_process');
const { JSDOM } = require('jsdom');

let server, dom, w, dir, base, logs = '', downloads = [], blobs = new Map();
const wait = async (predicate, label, timeout = 30000) => {
  const deadline = Date.now() + timeout;
  while (!predicate()) {
    if (Date.now() > deadline) throw new Error(`Tempo excedido: ${label}\n${logs}\n${w?.document.getElementById('c-error')?.textContent}`);
    await new Promise(resolve => setTimeout(resolve, 25));
  }
};
const el = id => w.document.getElementById(id);
const input = (id, value) => { el(id).value = String(value); el(id).dispatchEvent(new w.Event('input', {bubbles:true})); };
const select = (id, value) => { el(id).value = String(value); el(id).dispatchEvent(new w.Event('change', {bubbles:true})); };
const calcular = async () => {
  const anterior = el('c-permalink').getAttribute('href');
  el('c-form').dispatchEvent(new w.Event('submit', {cancelable:true,bubbles:true}));
  await wait(()=>el('c-permalink').getAttribute('href') !== anterior && !el('c-run').disabled, 'simulação nacional');
};

before(async () => {
  const listener=net.createServer(); await new Promise(resolve=>listener.listen(0,'127.0.0.1',resolve));
  const port=listener.address().port; await new Promise(resolve=>listener.close(resolve));
  base=`http://127.0.0.1:${port}`;dir=fs.mkdtempSync(path.join(os.tmpdir(),'fundeb-ui-'));
  const python=process.env.FUNDEB_TEST_PYTHON || 'python';
  server=spawn(python,['-m','uvicorn','main:app','--host','127.0.0.1','--port',String(port)],{
    env:{...process.env,FUNDEB_CENARIOS_DB:path.join(dir,'cenarios.sqlite3')},stdio:['ignore','pipe','pipe']});
  server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
  server.on('error',e=>logs+=e.message);
  let ready=false;
  for(let i=0;i<200;i++){
    try{ready=(await fetch(base+'/api/bases')).ok;}catch(_){}
    if(ready)break;await new Promise(resolve=>setTimeout(resolve,50));
  }
  assert.ok(ready,logs);
  dom=new JSDOM(fs.readFileSync('static/index.html','utf8'),{url:base+'/?tab=cenarios',runScripts:'outside-only'});w=dom.window;
  if(w.document.readyState==='loading')await new Promise(resolve=>w.document.addEventListener('DOMContentLoaded',resolve,{once:true}));
  w.fetch=(url,opts)=>fetch(new URL(url,base),opts);
  w.HTMLElement.prototype.scrollIntoView=function(){};
  w.URL.createObjectURL=blob=>{const id='blob:'+blobs.size;blobs.set(id,blob);return id;};
  w.URL.revokeObjectURL=()=>{};
  w.HTMLAnchorElement.prototype.click=function(){downloads.push({url:this.href,name:this.download});};
  w.eval(fs.readFileSync('static/js/app.js','utf8'));
  w.eval(fs.readFileSync('static/js/cenarios.js','utf8'));
  w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
  await wait(()=>el('c-add')&&!el('c-add').disabled&&el('c-base-info').textContent.includes('5.595'),'base carregada');
});

after(async()=>{
  if(dom)dom.window.close();
  if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>server.once('exit',resolve));}
  if(dir)fs.rmSync(dir,{recursive:true,force:true});
});

test('edição de duas UFs, cálculo nacional e exportação do snapshot após alterar controles',async()=>{
  assert.equal(el('c-amazon').disabled,true);
  assert.equal(el('c-propag-option').disabled,true);
  assert.equal(el('c-uf').value,'CE');
  input('c-value',500);el('c-add').click();
  select('c-uf','PI');await wait(()=>el('c-ente').selectedOptions[0]?.textContent.includes('Piauí')&&!el('c-add').disabled,'carregar PI');
  input('c-value',300);el('c-add').click();
  select('c-uf','CE');await wait(()=>!el('c-add').disabled,'retornar CE');
  assert.equal(el('c-adjustments').querySelectorAll('tbody tr').length,2);
  input('c-rate',5);await calcular();
  assert.equal(el('c-results').hidden,false);
  assert.equal(el('c-comparison-table').querySelectorAll('tbody tr').length,27);
  assert.equal(el('c-stale').hidden,true);
  const href=el('c-permalink').getAttribute('href');
  input('c-rate',7);assert.equal(el('c-stale').hidden,false);
  el('c-results').querySelector('[data-format="csv"]').click();
  await wait(()=>downloads.length===1,'download CSV');
  const csv=await blobs.get(downloads[0].url).text();
  assert.ok(csv.includes('""taxa_percentual"":5'));
  assert.ok(!csv.includes('""taxa_percentual"":7'));
  assert.equal(el('c-permalink').getAttribute('href'),href);
  assert.ok(downloads[0].name.endsWith('_B-A.csv'));
});

test('PIB informado e trajetória hipotética usam a API real',async()=>{
  el('c-clear').click();select('c-revenue-method','pib_cagr');
  input('c-pib','2020;100\n2022;121');input('c-pib-source','Série sintética usada apenas no teste');
  await calcular();
  const metadata=JSON.parse(el('c-result-meta').textContent);
  assert.ok(Math.abs(metadata.parametros.taxa_receita_percentual-10)<1e-10);
  select('c-revenue-method','informada');input('c-rate',0);
  select('c-filter','CE');input('c-start-year',2026);input('c-end-year',2027);
  input('c-ept-hypothesis','Hipótese sintética de expansão para teste');
  const anterior=el('c-permalink').href;el('c-run-trajectory').click();
  await wait(()=>el('c-permalink').href!==anterior&&!el('c-run-trajectory').disabled,'trajetória EPT');
  assert.equal(el('c-year-label').hidden,false);
  assert.equal(el('c-year').options.length,2);
  assert.equal(el('c-trajectory-summary').querySelectorAll('tbody tr').length,2);
  assert.equal(el('c-comparison-table').querySelectorAll('tbody tr').length,1);
});

test('quantidade inválida exibe mensagem e não entra no conjunto',()=>{
  input('c-value',-1);el('c-add').click();
  assert.equal(el('c-error').hidden,false);
  assert.match(el('c-error').textContent,/não negativa/);
  assert.equal(el('c-adjustments').querySelectorAll('tbody tr').length,0);
});
