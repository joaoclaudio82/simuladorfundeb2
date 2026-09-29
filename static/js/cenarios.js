/* Interface de cenários: o resultado exportado sempre usa seu próprio ID. */
(() => {
  'use strict';
  const s = { base: null, entes: [], matriculas: new Map(), ajustes: [], resultado: null, revision: 0, pagina: 0, load: 0 };
  const $c = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const n = value => value == null ? 'N/A' : Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const dinheiro = value => value == null ? 'N/A' : Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 });
  const cor = value => value > 0.005 ? 'c-pos' : value < -0.005 ? 'c-neg' : '';
  const parametros = { complementacao_vaaf:'Complementação VAAF (R$)', complementacao_vaat:'Complementação VAAT (R$)', complementacao_vaar:'Complementação VAAR (R$)', min_nse:'NSE mínimo', max_nse:'NSE máximo', min_nf:'Fator fiscal mínimo', max_nf:'Fator fiscal máximo' };
  const rotulos = {'B-A':'Efeito das matrículas', 'C-A':'Efeito da receita', 'D-A':'Efeito combinado', 'D-C':'Matrículas com receita ampliada'};

  async function api(url, body) {
    const response = await fetch(url, body === undefined ? {} : { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!response.ok) {
      let detail;
      try { detail = (await response.json()).detail; } catch (_) { detail = `Falha de comunicação (${response.status}).`; }
      throw new Error(Array.isArray(detail) ? detail.map(x => `${x.loc?.slice(1).join('.')}: ${x.msg}`).join('; ') : String(detail));
    }
    return response.json();
  }
  function erro(e) { $c('c-error').textContent = e.message; $c('c-error').hidden = false; }
  function limparErro() { $c('c-error').hidden = true; $c('c-error').textContent = ''; }
  function dirty() { s.revision++; if (s.resultado) $c('c-stale').hidden = false; }
  function options(select, rows) { select.innerHTML = rows.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join(''); }
  function valor(id) { const input = $c(id); if (input.value.trim() === '') throw new Error('Preencha os campos numéricos.'); const x = Number(input.value); if (!Number.isFinite(x)) throw new Error('Há um valor numérico inválido.'); return x; }
  function ufsFiltro() { return [...$c('c-filter').selectedOptions].map(x => x.value); }

  async function carregarBase() {
    const token = ++s.load, id = $c('c-base').value;
    s.base = null;
    $c('c-run').disabled = true; $c('c-add').disabled = true;
    try {
      const [base, entes] = await Promise.all([api(`/api/bases/${encodeURIComponent(id)}`), api(`/api/entes?base_id=${encodeURIComponent(id)}`)]);
      if (token !== s.load) return;
      s.base = base; s.entes = entes; s.ajustes = []; s.matriculas.clear();
      $c('c-base-badge').textContent = base.status === 'homologada' ? 'Base homologada' : 'Base sem homologação oficial';
      $c('c-base-info').textContent = `${base.redes.toLocaleString('pt-BR')} redes · ${base.categorias} categorias · Exercício: ${base.ano_exercicio ?? 'não identificado'} · Censo: ${base.ano_censo ?? 'não identificado'}`;
      $c('c-pendencias').innerHTML = (base.pendencias || []).map(x => `<li>${esc(x)}</li>`).join('');
      $c('c-fontes').textContent = `Fontes: ${JSON.stringify(base.fontes)}. Receitas: ${base.periodo_receita ?? 'período não identificado'}.`;
      $c('c-audit-result').textContent = '';
      options($c('c-uf'), base.ufs.map(x => [x,x]));
      if (base.ufs.includes('CE')) $c('c-uf').value = 'CE';
      options($c('c-filter'), base.ufs.map(x => [x,x]));
      for (const id of ['c-stage', 'c-destination', 'c-ept-origin']) options($c(id), base.etapas.map(x => [x.etapa,x.nome]));
      options($c('c-ept-stage'), base.etapas.filter(x => (base.etapas_ept || []).includes(x.etapa)).map(x => [x.etapa,x.nome]));
      if (base.etapas_ept?.length) $c('c-stage').value = base.etapas_ept[0];
      $c('c-propag-option').disabled = base.propag?.status !== 'validado';
      $c('c-propag-option').textContent = base.propag?.status === 'validado' ? 'Grupo Propag' : 'Grupo Propag — composição pendente';
      if ($c('c-propag-option').disabled && $c('c-scope').value === 'propag') $c('c-scope').value = 'estaduais';
      $c('c-amazon').disabled = base.amazonico?.status !== 'validado'; $c('c-amazon').checked = false;
      $c('c-amazon-status').textContent = base.amazonico?.status === 'validado' ? `Regra cadastrada: ${base.amazonico.norma}` : 'Fator amazônico pendente de norma, vigência e incidência confirmadas.';
      $c('c-vaat-rubric-label').textContent = base.modo_vaat === 'componentes' ? 'Outras receitas VAAT (fora do VAAF)' : 'Receita VAAT do snapshot';
      $c('c-parameters').innerHTML = Object.entries(parametros).map(([key,label]) => `<label>${esc(label)}<input id="c-p-${key}" type="number" min="${key.startsWith('complementacao')?0:0.01}" step="any" value="${base.parametros[key]}"></label>`).join('');
      $c('c-weights').querySelector('tbody').innerHTML = base.etapas.map((x,i) => `<tr><td>${esc(x.nome)}</td><td><input aria-label="Peso VAAF: ${esc(x.nome)}" id="c-w-vaaf-${i}" type="number" min="0.01" max="10" step="0.01" value="${x.peso_vaaf}"></td><td><input aria-label="Peso VAAT: ${esc(x.nome)}" id="c-w-vaat-${i}" type="number" min="0.01" max="10" step="0.01" value="${x.peso_vaat}"></td></tr>`).join('');
      if (base.ano_exercicio) $c('c-start-year').value = base.ano_exercicio;
      renderAjustes(); await carregarEntes();
    } catch (e) { erro(e); }
    finally { if (token === s.load) $c('c-run').disabled = !s.base; }
  }
  async function carregarEntes() {
    const tipo = $c('c-type').value, uf = $c('c-uf').value;
    const lista = s.entes.filter(e => e.uf === uf && (tipo === 'estaduais' ? ['estadual','distrital'].includes(e.tipo) : e.tipo === tipo));
    options($c('c-ente'), lista.map(e => [e.ibge, `${e.nome} (${e.tipo})`]));
    await carregarMatriculas();
  }
  async function carregarMatriculas() {
    const id = $c('c-ente').value, base = s.base?.id;
    $c('c-add').disabled = true;
    if (!id) { $c('c-original').textContent = 'Nenhuma rede nesse filtro.'; return; }
    try {
      const key = `${base}:${id}`;
      if (!s.matriculas.has(key)) s.matriculas.set(key, await api(`/api/entes/${id}/matriculas?base_id=${encodeURIComponent(base)}`));
      if ($c('c-ente').value === id && s.base?.id === base) { renderOriginal(); $c('c-add').disabled = false; }
    } catch (e) { erro(e); }
  }
  function matAtual() { return s.matriculas.get(`${s.base?.id}:${$c('c-ente').value}`); }
  function renderOriginal() {
    const mat = matAtual();
    $c('c-original').textContent = mat ? `Valor na base: ${n(mat.matriculas[$c('c-stage').value])} matrículas.` : '';
  }
  function renderOperacao() {
    const op = $c('c-op').value;
    $c('c-destination-label').hidden = op !== 'converter';
    $c('c-value-label').textContent = op === 'percentual' ? 'Aumento relativo (%)' : op === 'definir' ? 'Quantidade final' : op === 'converter' ? 'Quantidade a converter' : 'Novas matrículas';
    $c('c-value').step = op === 'percentual' ? '0.01' : '1';
  }
  function adicionar() {
    limparErro();
    try {
      const mat = matAtual(), etapa = $c('c-stage').value, operacao = $c('c-op').value, v = valor('c-value');
      if (!mat) throw new Error('Selecione uma rede válida.');
      if (v < 0 || (operacao !== 'percentual' && !Number.isInteger(v))) throw new Error('Informe uma quantidade inteira e não negativa.');
      const destino = operacao === 'converter' ? $c('c-destination').value : null;
      if (operacao === 'converter' && (!destino || destino === etapa || v > mat.matriculas[etapa])) throw new Error('Confira a categoria de destino e a quantidade disponível na origem.');
      const cells = [etapa, destino].filter(Boolean);
      if (s.ajustes.some(a => a.ibge === mat.ibge && [a.etapa,a.destino].some(c => cells.includes(c)))) throw new Error('Já existe ajuste nessa rede/categoria. Remova o ajuste anterior para substituí-lo.');
      const before = mat.matriculas[etapa];
      const after = operacao === 'definir' ? v : operacao === 'converter' ? before-v : before+(operacao === 'percentual' ? Math.round(before*v/100) : v);
      s.ajustes.push({ibge:mat.ibge, etapa, operacao, valor:v, destino, antes:before, depois:after, nome:mat.nome, uf:mat.uf});
      dirty(); renderAjustes();
    } catch (e) { erro(e); }
  }
  function renderAjustes() {
    const names = Object.fromEntries((s.base?.etapas || []).map(e => [e.etapa,e.nome]));
    $c('c-adjustments').querySelector('tbody').innerHTML = s.ajustes.map((a,i) => `<tr><td>${esc(a.uf)} · ${esc(a.nome)}</td><td>${esc(names[a.etapa])}<br><small>${esc(a.operacao)}${a.destino ? ' → '+esc(names[a.destino]) : ''} (${n(a.valor)}${a.operacao==='percentual'?'%':''})</small></td><td>${n(a.antes)}</td><td>${n(a.depois)}</td><td><button type="button" class="c-btn c-link" data-remove="${i}" aria-label="Remover ajuste de ${esc(a.nome)}">Remover</button></td></tr>`).join('');
    $c('c-adjustment-count').textContent = s.ajustes.length ? `${s.ajustes.length} alterações em ${new Set(s.ajustes.map(a=>a.ibge)).size} redes. Incremento líquido: ${n(s.ajustes.reduce((sum,a)=>sum+(a.operacao==='converter'?0:a.depois-a.antes),0))}.` : 'Nenhuma alteração. A referência pode ser calculada sem ajustes.';
  }
  function payload() {
    if (!s.base) throw new Error('Aguarde o carregamento da base.');
    const p = {}, metodo = $c('c-revenue-method').value;
    Object.keys(parametros).forEach(k => p[k] = valor(`c-p-${k}`));
    for (const m of ['vaaf','vaat']) p[`pesos_${m}`] = Object.fromEntries(s.base.etapas.map((e,i) => [e.etapa,valor(`c-w-${m}-${i}`)]));
    const rubricas = [];
    if ($c('c-grow-vaaf').checked) rubricas.push('recursos_vaaf');
    if ($c('c-grow-vaat').checked) rubricas.push(s.base.modo_vaat === 'componentes' ? 'outras_receitas_vaat' : 'recursos_vaat');
    if (!rubricas.length) throw new Error('Selecione ao menos uma rubrica de receita.');
    const receita = {metodo, taxa_percentual:metodo==='informada'?valor('c-rate'):0, rubricas, complementacoes:$c('c-union').value};
    if (metodo === 'pib_cagr') {
      receita.fonte = $c('c-pib-source').value.trim();
      receita.pib = $c('c-pib').value.trim().split(/\n/).filter(x=>x.trim()).map(line => {
        const parts = line.trim().split(/[;\t]/);
        if (parts.length !== 2 || parts.some(x=>!x.trim()) || !parts.every(x=>Number.isFinite(Number(x)))) throw new Error('Use ano;valor em cada linha do PIB, sem separador de milhar.');
        return {ano:Number(parts[0]),valor:Number(parts[1])};
      });
    }
    return {base_id:s.base.id, ano_exercicio:s.base.ano_exercicio, nome:$c('c-name').value.trim(),
      ajustes:s.ajustes.map(a=>({ibge:a.ibge,etapa:a.etapa,operacao:a.operacao,valor:a.valor,destino:a.destino})),
      parametros:p, receita, recorte:{tipo:$c('c-scope').value,ufs:ufsFiltro()}, fator_amazonico:$c('c-amazon').checked};
  }
  async function executar(event, trajetoria=false) {
    event?.preventDefault(); limparErro(); const revision = s.revision;
    $c('c-run').disabled = true; $c('c-run-trajectory').disabled = true;
    $c('c-status').textContent = trajetoria ? 'Calculando a trajetória nacional...' : 'Calculando as quatro combinações de matrículas e receita...';
    try {
      let body = payload(), url = '/api/cenarios';
      if (trajetoria) {
        if (s.ajustes.length) throw new Error('Limpe os ajustes avulsos antes de gerar a trajetória de EPT.');
        const ufs = ufsFiltro(); body.recorte = {tipo:'estaduais',ufs};
        body = {cenario:body,ano_inicial:valor('c-start-year'),ano_final:valor('c-end-year'),aumento_total_percentual:valor('c-ept-growth'),
          etapa:$c('c-ept-stage').value,operacao:$c('c-ept-op').value,origem:$c('c-ept-op').value==='converter'?$c('c-ept-origin').value:null,
          hipotese:$c('c-ept-hypothesis').value.trim(),entes:s.entes.filter(e=>['estadual','distrital'].includes(e.tipo)&&(!ufs.length||ufs.includes(e.uf))).map(e=>e.ibge)};
        url = '/api/trajetorias';
      }
      s.resultado = await api(url,body); s.pagina=0;
      renderResultado(); $c('c-stale').hidden = s.revision === revision;
      $c('c-status').textContent = 'Cálculo concluído. O resultado está disponível para exportação.';
      $c('c-results').scrollIntoView({behavior:'smooth',block:'start'});
    } catch(e) { erro(e); $c('c-status').textContent = ''; }
    finally { $c('c-run').disabled=false; $c('c-run-trajectory').disabled=false; }
  }
  function comps() {
    const r=s.resultado;
    return r.tipo==='cenario'?r.comparativos:r.series.find(x=>String(x.ano)===$c('c-year').value).comparativos;
  }
  function renderResultado() {
    const r=s.resultado; $c('c-results').hidden=false;
    $c('c-result-info').textContent = `${r.nome} · ${r.base.nome} · ${new Date(r.criado_em).toLocaleString('pt-BR')} · ${r.recorte.redes} redes no recorte`;
    $c('c-result-caveat').textContent = r.avisos.slice(0,1).join(' ')+' '+r.aviso;
    const metric=$c('c-metric').value;
    options($c('c-metric'),Object.entries(r.metricas)); if(metric in r.metricas) $c('c-metric').value=metric;
    $c('c-year-label').hidden = r.tipo!=='trajetoria';
    if(r.tipo==='trajetoria') { options($c('c-year'),r.series.map(x=>[x.ano,x.ano])); $c('c-year').value=r.series.at(-1).ano; }
    $c('c-result-meta').textContent=JSON.stringify({hipoteses:r.entrada,avisos:r.avisos,validacao:r.validacao,base:r.base.id,base_sha256:r.base.fingerprint,motor_sha256:r.motor_sha256,parametros:r.parametros_efetivos},null,2);
    $c('c-permalink').href=`/?tab=cenarios&cenario=${r.id}`;
    $c('c-denominator').textContent=`Participação calculada sobre: ${r.recorte.denominador}. ${r.nota_matriculas}`;
    renderTabela();
  }
  function renderTabela() {
    if(!s.resultado) return;
    const comparativos=comps(), c=comparativos[$c('c-comparison').value], metric=$c('c-metric').value;
    $c('c-cards').innerHTML=Object.entries(comparativos).map(([k,v])=>`<div class="c-card"><span>${esc(k)} · ${esc(rotulos[k])}</span><strong class="${cor(v.totais.recursos_fundeb.delta)}">${dinheiro(v.totais.recursos_fundeb.delta)}</strong><small>${n(v.totais.recursos_fundeb.percentual)}% nos recursos do recorte</small></div>`).join('');
    const pages=Math.ceil(c.linhas.length/50); s.pagina=Math.min(s.pagina,pages-1);
    $c('c-table-caption').textContent=s.resultado.metricas[metric];
    $c('c-comparison-table').querySelector('tbody').innerHTML=c.linhas.slice(s.pagina*50,(s.pagina+1)*50).map(row=>{
      const v=row.indicadores[metric],p=row.participacao;
      return `<tr><td>${esc(row.uf)}</td><td>${esc(row.nome)}<br><small>${esc(row.tipo)}</small></td><td>${n(v.base)}</td><td>${n(v.simulado)}</td><td class="${cor(v.delta)}">${n(v.delta)}</td><td class="${cor(v.percentual)}">${n(v.percentual)}</td><td>${n(p.base_pct)}</td><td>${n(p.simulado_pct)}</td><td class="${cor(p.delta_pp)}">${n(p.delta_pp)}</td></tr>`;
    }).join('');
    const t=c.totais[metric]; $c('c-comparison-table').querySelector('tfoot').innerHTML=`<tr><td colspan="2">Total do recorte</td><td>${n(t.base)}</td><td>${n(t.simulado)}</td><td>${n(t.delta)}</td><td>${n(t.percentual)}</td><td colspan="3"></td></tr>`;
    $c('c-pagination').innerHTML=`<span>${c.linhas.length} redes · Página ${s.pagina+1} de ${pages}</span><div><button type="button" class="c-btn c-secondary" id="c-prev" ${s.pagina===0?'disabled':''}>Anterior</button> <button type="button" class="c-btn c-secondary" id="c-next" ${s.pagina===pages-1?'disabled':''}>Próxima</button></div>`;
    $c('c-prev').onclick=()=>{s.pagina--;renderTabela();};$c('c-next').onclick=()=>{s.pagina++;renderTabela();};
    if(s.resultado.tipo==='trajetoria') {
      $c('c-trajectory-summary').innerHTML='<div class="c-table-wrap"><table class="c-table"><caption>Expansão e impacto anual no recorte</caption><thead><tr><th>Ano</th><th>Novas / convertidas EPT</th><th>Receita acumulada (%)</th><th>Efeito combinado (R$)</th></tr></thead><tbody>'+s.resultado.series.map(x=>`<tr><td>${x.ano}</td><td>${n(x.incremento_ept)}</td><td>${n(x.taxa_receita_acumulada)}</td><td>${dinheiro(x.comparativos['D-A'].totais.recursos_fundeb.delta)}</td></tr>`).join('')+'</tbody></table></div>';
    } else $c('c-trajectory-summary').textContent='';
  }
  async function baixar(button) {
    if(!s.resultado) return; limparErro(); button.disabled=true;
    try {
      const format=button.dataset.format, id=s.resultado.id, comparison=$c('c-comparison').value, metric=$c('c-metric').value;
      const response=await fetch(`/api/cenarios/${id}/exportar?formato=${format}&comparacao=${comparison}&indicador=${metric}`);
      if(!response.ok) { let data;try{data=await response.json();}catch(_){data={detail:'Falha ao exportar o resultado.'};}throw new Error(data.detail); }
      const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');
      link.href=url;link.download=`fundeb_${id}_${comparison}.${format}`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
    } catch(e){erro(e);}finally{button.disabled=false;}
  }
  document.addEventListener('DOMContentLoaded', async()=>{
    try{
      const response=await fetch('/static/cenarios.html'); if(!response.ok)throw new Error('Falha ao carregar a interface de cenários.');
      $c('tab-cenarios').innerHTML=await response.text();
      const bases=await api('/api/bases');options($c('c-base'),bases.map(b=>[b.id,b.nome]));
      $c('c-base').onchange=carregarBase;
      $c('c-uf').onchange=carregarEntes;$c('c-type').onchange=carregarEntes;$c('c-ente').onchange=carregarMatriculas;
      $c('c-stage').onchange=renderOriginal;$c('c-op').onchange=renderOperacao;$c('c-add').onclick=adicionar;
      $c('c-clear').onclick=()=>{s.ajustes=[];dirty();renderAjustes();};
      $c('c-adjustments').onclick=event=>{const b=event.target.closest('[data-remove]');if(b){s.ajustes.splice(Number(b.dataset.remove),1);dirty();renderAjustes();}};
      $c('c-form').onsubmit=executar;
      $c('c-form').addEventListener('input',dirty);$c('c-form').addEventListener('change',dirty);
      $c('c-trajectory').addEventListener('input',dirty);$c('c-trajectory').addEventListener('change',dirty);
      $c('c-revenue-method').onchange=()=>{$c('c-pib-fields').hidden=$c('c-revenue-method').value!=='pib_cagr';$c('c-rate-label').hidden=$c('c-revenue-method').value==='pib_cagr';};
      $c('c-ept-op').onchange=()=>{$c('c-ept-origin-label').hidden=$c('c-ept-op').value!=='converter';};
      for(const id of ['c-metric','c-comparison','c-year'])$c(id).onchange=()=>{s.pagina=0;renderTabela();};
      document.querySelectorAll('.c-export').forEach(b=>b.onclick=()=>baixar(b));
      $c('c-run-trajectory').onclick=e=>executar(e,true);
      $c('c-audit').onclick=async()=>{limparErro();$c('c-audit').disabled=true;try{const a=(await api(`/api/bases/${s.base.id}/auditoria`)).calibracao;$c('c-audit-result').innerHTML=`<p>${a.aprovada?'Dentro das tolerâncias definidas.':'Referência não reproduzida dentro das tolerâncias definidas.'} Referência oficial: ${a.referencia_oficial?'sim':'não confirmada'}. Redes em comum: ${a.redes_em_comum??0}.</p>`+(a.indicadores?'<table class="c-table"><thead><tr><th>Indicador</th><th>Redes fora da tolerância</th><th>Maior desvio absoluto</th></tr></thead><tbody>'+a.indicadores.map(x=>`<tr><td>${esc(x.indicador)}</td><td>${x.fora_tolerancia}</td><td>${n(x.maior_desvio_absoluto)}</td></tr>`).join('')+'</tbody></table>':'');}catch(e){erro(e);}finally{$c('c-audit').disabled=false;}};
      await carregarBase();
      const query=new URLSearchParams(location.search);
      if(query.get('tab')==='cenarios'||query.has('cenario')) document.querySelector('.sidebar-nav [data-tab="cenarios"]').click();
      if(query.has('cenario')) {s.resultado=await api('/api/cenarios/'+encodeURIComponent(query.get('cenario')));renderResultado();$c('c-stale').hidden=false;}
    }catch(e){if($c('c-error'))erro(e);else $c('tab-cenarios').textContent=e.message;}
  });
})();
