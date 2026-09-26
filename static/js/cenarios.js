/**
 * Simulador FUNDEB v2 — Cenário nacional (FND-06, FND-07, FND-08, FND-11)
 * Edição conjunta de várias redes, execução única do motor nacional,
 * comparação por recorte e exportação do cenário calculado.
 */

const cen = {
  bases: [],
  base: null,           // detalhe da base ativa (GET /api/bases/{id})
  aviso: '',
  categorias: {},       // etapa -> nome
  ajustes: new Map(),   // chave -> ajuste pendente
  rede: null,           // rede em edição {ibge, uf, nome, tipo_rede, matriculas}
  cacheRedes: new Map(),
  ultimo: null,         // {id, assinatura, dados}
  iniciado: false,
};

function cenFetch(url, opts = {}) {
  return apiFetch(url, opts);  // auth.js: cookie de sessão e redirecionamento em 401
}

const cenFmt = {
  num: (v, c = 0) => v == null ? 'n/a' : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c }),
  moeda: (v) => v == null ? 'n/a' : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }),
  pct: (v, c = 2) => v == null ? 'n/a' : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: c }) + '%',
  pp: (v) => v == null ? 'n/a' : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 4 }) + ' p.p.',
  sinal: (v) => v == null ? '' : (v > 0 ? 'text-success' : v < 0 ? 'text-danger' : ''),
};

function esc(t) {
  const d = document.createElement('div');
  d.textContent = t == null ? '' : String(t);
  return d.innerHTML;
}

function el(id) { return document.getElementById(id); }
function nomeCategoria(etapa) { return cen.categorias[etapa] || etapa; }

// -------------------------------------------------------------------------
// Inicialização (sob demanda, ao abrir a aba)
// -------------------------------------------------------------------------
async function initCenario() {
  if (cen.iniciado || !el('tab-cenario')) return;
  cen.iniciado = true;
  try {
    if (typeof guardAuth === 'function') await guardAuth();
    const [bases, estados] = await Promise.all([cenFetch('/api/bases'), cenFetch('/api/estados')]);
    cen.bases = bases.bases;
    cen.aviso = bases.aviso;
    el('cen-aviso').textContent = cen.aviso;
    el('cen-base').innerHTML = cen.bases.map(b =>
      `<option value="${esc(b.base_id)}"${b.padrao ? ' selected' : ''}>${esc(b.ano_exercicio)} — ${esc(b.situacao)}</option>`).join('');
    preencherUFs(estados.regioes);
    await trocarBase();
  } catch (e) {
    cen.iniciado = false;
    el('cen-base-info').innerHTML = `<div class="alert alert-danger">Falha ao carregar: ${esc(e.message)}</div>`;
    return;
  }
  el('cen-base').addEventListener('change', async () => {
    if (cen.ajustes.size && !confirm('Trocar de exercício descarta as alterações pendentes. Continuar?')) {
      el('cen-base').value = cen.base.base_id;
      return;
    }
    await trocarBase();
  });
  el('cen-uf').addEventListener('change', carregarRedesUF);
  el('cen-rede').addEventListener('change', carregarRede);
  el('cen-busca').addEventListener('input', renderFormRede);
  el('cen-todas').addEventListener('change', renderFormRede);
  el('cen-btn-converter').addEventListener('click', adicionarConversao);
  el('cen-btn-limpar').addEventListener('click', () => { cen.ajustes.clear(); atualizarPendentes(); renderFormRede(); });
  el('cen-btn-calcular').addEventListener('click', calcularCenario);
  el('cen-recorte').addEventListener('change', trocarRecorte);
  el('cen-receita-tipo').addEventListener('change', () => {
    el('cen-receita-opcoes').style.display = el('cen-receita-tipo').value === 'crescimento' ? '' : 'none';
    marcarDesatualizado();
  });
  document.querySelectorAll('#cen-parametros input, #cen-parametros select').forEach(x =>
    x.addEventListener('input', marcarDesatualizado));
  document.querySelectorAll('[data-cen-export]').forEach(btn =>
    btn.addEventListener('click', () => exportar(btn.dataset.cenExport)));
}

async function trocarBase() {
  const id = el('cen-base').value;
  el('cen-base-info').innerHTML = '<p class="small text-muted">Carregando a base…</p>';
  cen.base = await cenFetch(`/api/bases/${encodeURIComponent(id)}`);
  cen.ajustes.clear();
  cen.cacheRedes.clear();
  cen.rede = null;
  cen.categorias = {};
  renderBaseInfo();
  preencherParametros();
  el('cen-rede').innerHTML = '<option value="">Selecione a UF</option>';
  el('cen-uf').value = '';
  renderFormRede();
  atualizarPendentes();
}

function renderBaseInfo() {
  const b = cen.base;
  const badge = b.homologada
    ? '<span class="badge bg-success">homologada</span>'
    : '<span class="badge bg-warning text-dark">não homologada</span>';
  const pend = (b.pendencias || []).map(p => `<li>${esc(p)}</li>`).join('');
  el('cen-base-info').innerHTML = `
    <p class="mb-1"><strong>${esc(b.base_id)}</strong> ${badge}</p>
    <p class="mb-1 small">Exercício <strong>${esc(b.ano_exercicio)}</strong> · ${esc(b.periodo_receita || 'período de receita não informado')}
      · situação: ${esc(b.situacao)} · ponderador: ${esc(b.modo_ponderador === 'drec' ? 'NSE e DREC oficiais' : 'NSE e NF')}</p>
    <p class="mb-1 small">${cenFmt.num(b.quantidade_entes)} entes · ${cenFmt.num(b.quantidade_categorias)} categorias de matrícula</p>
    ${pend ? `<ul class="small mb-0">${pend}</ul>` : ''}`;
}

function preencherParametros() {
  const p = cen.base.parametros_referencia || {};
  el('cen-vaaf').value = p.complementacao_vaaf ?? '';
  el('cen-vaat').value = p.complementacao_vaat ?? '';
  el('cen-vaar').value = p.complementacao_vaar ?? '';
}

function preencherUFs(regioes) {
  const sel = el('cen-uf');
  sel.innerHTML = '<option value="">Selecione...</option>';
  for (const [regiao, ufs] of Object.entries(regioes)) {
    const g = document.createElement('optgroup');
    g.label = regiao;
    ufs.forEach(uf => { const o = document.createElement('option'); o.value = uf; o.textContent = uf; g.appendChild(o); });
    sel.appendChild(g);
  }
}

function preencherCategoriasConversao() {
  const opts = Object.entries(cen.categorias)
    .sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'))
    .map(([e, n]) => `<option value="${esc(e)}">${esc(n)}</option>`).join('');
  el('cen-conv-origem').innerHTML = opts;
  el('cen-conv-destino').innerHTML = opts;
}

// -------------------------------------------------------------------------
// Seleção e edição de redes
// -------------------------------------------------------------------------
async function carregarRedesUF() {
  const uf = el('cen-uf').value;
  const sel = el('cen-rede');
  sel.innerHTML = '<option value="">Carregando...</option>';
  if (!uf) { sel.innerHTML = '<option value="">Selecione a UF</option>'; return; }
  const dados = await cenFetch(`/api/entes?uf=${encodeURIComponent(uf)}&base_id=${encodeURIComponent(cen.base.base_id)}`);
  const estaduais = dados.entes.filter(e => e.tipo_rede !== 'rede municipal');
  const municipais = dados.entes.filter(e => e.tipo_rede === 'rede municipal');
  let html = '<option value="">Selecione...</option>';
  html += estaduais.map(e => `<option value="${e.ibge}">${esc(e.nome)} — ${esc(e.tipo_rede)}</option>`).join('');
  if (municipais.length) {
    html += '<optgroup label="Redes municipais">' +
      municipais.map(e => `<option value="${e.ibge}">${esc(e.nome)} (${e.ibge})</option>`).join('') + '</optgroup>';
  }
  sel.innerHTML = html;
  if (estaduais.length) { sel.value = estaduais[0].ibge; await carregarRede(); }
}

async function carregarRede() {
  const ibge = parseInt(el('cen-rede').value);
  if (!ibge) { cen.rede = null; renderFormRede(); return; }
  if (!cen.cacheRedes.has(ibge)) {
    const r = await cenFetch(`/api/entes/${ibge}/matriculas?base_id=${encodeURIComponent(cen.base.base_id)}`);
    cen.cacheRedes.set(ibge, r);
    if (!Object.keys(cen.categorias).length) {
      cen.categorias = r.nomes_categorias;
      preencherCategoriasConversao();
    }
  }
  cen.rede = cen.cacheRedes.get(ibge);
  renderFormRede();
}

function chaveDefinir(ibge, cat) { return `${ibge}|${cat}|definir`; }

function renderFormRede() {
  const box = el('cen-form');
  const r = cen.rede;
  if (!r) { box.innerHTML = '<p class="small text-muted">Selecione uma UF e um ente federado.</p>'; return; }
  const busca = el('cen-busca').value.trim().toLowerCase();
  const todas = el('cen-todas').checked;
  const itens = Object.entries(r.matriculas).filter(([etapa, original]) => {
    const editado = cen.ajustes.has(chaveDefinir(r.ibge, etapa));
    if (busca && !nomeCategoria(etapa).toLowerCase().includes(busca)) return false;
    return todas || busca || original > 0 || editado;
  });
  let html = `<p class="mb-1"><strong>${esc(r.nome)}</strong> — ${esc(r.uf)} · ${esc(r.tipo_rede)}</p>
    <p class="small text-muted mb-2">Mostrando ${itens.length} de ${Object.keys(r.matriculas).length} categorias.
    Informe o novo número de matrículas; as edições ficam guardadas ao trocar de rede.</p>
    <div class="cen-categorias">`;
  for (const [etapa, original] of itens) {
    const pend = cen.ajustes.get(chaveDefinir(r.ibge, etapa));
    const valor = pend ? pend.valor : original;
    html += `<div class="matricula-item${pend ? ' cen-editado' : ''}">
      <label title="${esc(etapa)}">${esc(nomeCategoria(etapa))}<br><small class="text-muted">original: ${cenFmt.num(original, 2)}</small></label>
      <input type="number" class="form-control form-control-sm" min="0" step="any"
             data-cen-etapa="${esc(etapa)}" value="${valor}">
    </div>`;
  }
  box.innerHTML = html + '</div>';
  box.querySelectorAll('input[data-cen-etapa]').forEach(inp => inp.addEventListener('change', () => {
    registrarDefinicao(r, inp.dataset.cenEtapa, inp.value);
    inp.closest('.matricula-item').classList.toggle('cen-editado', cen.ajustes.has(chaveDefinir(r.ibge, inp.dataset.cenEtapa)));
  }));
}

function registrarDefinicao(rede, etapa, texto) {
  const chave = chaveDefinir(rede.ibge, etapa);
  const original = rede.matriculas[etapa];
  const valor = parseFloat(texto);
  if (texto === '' || !Number.isFinite(valor) || valor < 0) {
    alert('Informe um número de matrículas maior ou igual a zero.');
    return;
  }
  if (Math.abs(valor - original) < 1e-9) cen.ajustes.delete(chave);
  else cen.ajustes.set(chave, {
    ibge: rede.ibge, uf: rede.uf, nome: rede.nome, operacao: 'definir',
    categoria: etapa, valor, original,
  });
  atualizarPendentes();
}

function adicionarConversao() {
  const r = cen.rede;
  if (!r) { alert('Selecione um ente federado.'); return; }
  const origem = el('cen-conv-origem').value;
  const destino = el('cen-conv-destino').value;
  const valor = parseFloat(el('cen-conv-valor').value);
  if (origem === destino) { alert('Origem e destino devem ser diferentes.'); return; }
  if (!Number.isFinite(valor) || valor <= 0) { alert('Informe uma quantidade positiva.'); return; }
  const chave = `${r.ibge}|${origem}|converter|${destino}`;
  const atual = cen.ajustes.get(chave);
  cen.ajustes.set(chave, {
    ibge: r.ibge, uf: r.uf, nome: r.nome, operacao: 'converter', categoria: origem,
    categoria_destino: destino, valor: (atual ? atual.valor : 0) + valor, original: r.matriculas[origem],
  });
  el('cen-conv-valor').value = '';
  atualizarPendentes();
}

function atualizarPendentes() {
  const tbody = el('cen-pendentes-corpo');
  const lista = [...cen.ajustes.entries()].sort((a, b) =>
    (a[1].uf + a[1].nome + a[1].categoria).localeCompare(b[1].uf + b[1].nome + b[1].categoria));
  let acrescidas = 0, reduzidas = 0, convertidas = 0;
  tbody.innerHTML = lista.length ? lista.map(([chave, a]) => {
    let novo;
    if (a.operacao === 'converter') {
      convertidas += a.valor;
      novo = `${cenFmt.num(a.valor, 2)} → ${esc(nomeCategoria(a.categoria_destino))}`;
    } else {
      const d = a.valor - a.original;
      if (d > 0) acrescidas += d; else reduzidas -= d;
      novo = cenFmt.num(a.valor, 2);
    }
    return `<tr><td>${esc(a.uf)}</td><td>${esc(a.nome)}</td><td>${a.operacao === 'converter' ? 'conversão' : 'novo valor'}</td>
      <td>${esc(nomeCategoria(a.categoria))}</td><td class="text-end">${cenFmt.num(a.original, 2)}</td>
      <td class="text-end">${novo}</td>
      <td><button class="btn btn-sm btn-outline-danger" data-cen-remover="${esc(chave)}" title="Remover"><i class="fas fa-times"></i></button></td></tr>`;
  }).join('') : '<tr><td colspan="7" class="text-muted small">Nenhuma alteração pendente.</td></tr>';
  tbody.querySelectorAll('[data-cen-remover]').forEach(btn => btn.addEventListener('click', () => {
    cen.ajustes.delete(btn.dataset.cenRemover);
    atualizarPendentes();
    renderFormRede();
  }));
  const redes = new Set(lista.map(([, a]) => a.ibge)).size;
  el('cen-pendentes-resumo').innerHTML =
    `${lista.length} alteração(ões) em ${redes} rede(s) · novas matrículas: <strong>${cenFmt.num(acrescidas, 2)}</strong>
     · matrículas retiradas: <strong>${cenFmt.num(reduzidas, 2)}</strong>
     · convertidas entre categorias: <strong>${cenFmt.num(convertidas, 2)}</strong>`;
  marcarDesatualizado();
}

// -------------------------------------------------------------------------
// Requisição e execução
// -------------------------------------------------------------------------
function numeroOuNulo(id) {
  const v = el(id).value;
  return v === '' ? null : parseFloat(v);
}

function montarRequisicao() {
  const tipo = el('cen-receita-tipo').value;
  const rubricas = [...document.querySelectorAll('[data-cen-rubrica]:checked')].map(c => c.dataset.cenRubrica);
  const receita = tipo === 'crescimento' ? {
    tipo, taxa: (numeroOuNulo('cen-taxa') || 0) / 100, rubricas,
    complementacoes: el('cen-complementacoes').value,
    fonte_taxa: el('cen-fonte-taxa').value || null,
  } : { tipo: 'constante', taxa: 0 };
  return {
    base_id: cen.base.base_id,
    ajustes: [...cen.ajustes.values()].map(a => {
      const x = { ibge: a.ibge, categoria: a.categoria, operacao: a.operacao, valor: a.valor };
      if (a.categoria_destino) x.categoria_destino = a.categoria_destino;
      return x;
    }),
    parametros: {
      complementacao_vaaf: numeroOuNulo('cen-vaaf'),
      complementacao_vaat: numeroOuNulo('cen-vaat'),
      complementacao_vaar: numeroOuNulo('cen-vaar'),
    },
    receita,
    recorte: el('cen-recorte').value,
  };
}

function assinatura(req) {
  const { recorte, ...resto } = req;
  resto.ajustes = [...resto.ajustes].sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  return JSON.stringify(resto);
}

function marcarDesatualizado() {
  const aviso = el('cen-desatualizado');
  if (!aviso || !cen.base) return;
  const alterado = cen.ultimo && assinatura(montarRequisicao()) !== cen.ultimo.assinatura;
  aviso.classList.toggle('d-none', !alterado);
}

async function calcularCenario() {
  const req = montarRequisicao();
  const loading = el('cen-loading');
  loading.classList.remove('d-none');
  try {
    const dados = await cenFetch('/api/cenarios', { method: 'POST', body: JSON.stringify(req) });
    cen.ultimo = { id: dados.metadados.cenario_id, assinatura: assinatura(req), dados };
    renderResultado(dados);
  } catch (e) {
    alert('Não foi possível calcular o cenário: ' + e.message);
  } finally {
    loading.classList.add('d-none');
    marcarDesatualizado();
  }
}

async function trocarRecorte() {
  if (!cen.ultimo) return;
  const recorte = el('cen-recorte').value;
  try {
    const dados = await cenFetch(`/api/cenarios/${cen.ultimo.id}?recorte=${recorte}`);
    cen.ultimo.dados = dados;
    renderResultado(dados);
  } catch (e) {
    alert(e.message);
    el('cen-recorte').value = cen.ultimo.dados.comparacao.recorte.id;
  }
}

function exportar(formato) {
  if (!cen.ultimo) { alert('Calcule um cenário antes de exportar.'); return; }
  const recorte = cen.ultimo.dados.comparacao.recorte.id;
  window.location.href = `/api/cenarios/${cen.ultimo.id}/exportar?formato=${formato}&recorte=${recorte}`;
}

// -------------------------------------------------------------------------
// Resultados
// -------------------------------------------------------------------------
function renderResultado(dados) {
  const m = dados.metadados;
  const c = dados.comparacao;
  el('cen-resultados').classList.remove('d-none');
  el('cen-exportar').querySelectorAll('button').forEach(b => { b.disabled = false; });

  const validacao = Object.entries(m.validacoes).map(([k, v]) =>
    `${k}: ${v.valido ? '<span class="text-success">ok</span>' : `<span class="text-danger" title="${esc(v.erros.join('; '))}">com erros</span>`}`).join(' · ');
  el('cen-ident').innerHTML = `
    Cenário <code>${esc(m.cenario_id.slice(0, 8))}</code> · base <strong>${esc(m.base.base_id)}</strong>
    (exercício ${esc(m.base.ano_exercicio)}, ${m.base.homologada ? 'homologada' : 'não homologada'}) · motor ${esc(m.versao_motor)}
    · calculado em ${esc(m.criado_em)}<br>
    Recorte: <strong>${esc(c.recorte.descricao)}</strong> — ${c.recorte.quantidade_redes} redes · validação interna: ${validacao}`;

  renderTotais(c, m);
  renderTabelaComparativa(c);
  const u = c.universo;
  el('cen-universo').innerHTML = `
    Redes fora do recorte com variação de recursos (B − A): <strong>${cenFmt.num(u.redes_fora_do_recorte_afetadas)}</strong>
    (soma ${cenFmt.moeda(u.variacao_fora_do_recorte)}) · redes municipais: ${cenFmt.moeda(u.variacao_redes_municipais)}
    · redes sem ajuste direto afetadas: ${cenFmt.num(u.redes_sem_ajuste_afetadas)}
    · variação nacional: ${cenFmt.moeda(u.variacao_total_nacional)}`;
}

function renderTotais(c, m) {
  const cenarios = Object.keys(c.totais.por_cenario);
  const efeitos = Object.keys(c.totais.efeitos);
  const rotuloEfeito = (e) => e.replace('_', ' − ');
  let html = '<thead><tr><th>Indicador</th><th>Unidade</th>' +
    cenarios.map(k => `<th class="text-end" title="${esc(m.cenarios[k])}">Cenário ${k}</th>`).join('') +
    efeitos.map(e => `<th class="text-end" title="${esc(c.efeitos[e])}">${rotuloEfeito(e)}</th>`).join('') + '</tr></thead><tbody>';
  for (const ind of c.indicadores) {
    const casas = ind.agregacao === 'razao' ? 2 : 0;
    html += `<tr><td>${esc(ind.rotulo)}${ind.agregacao === 'razao' ? ' <small class="text-muted">(razão de somas)</small>' : ''}</td><td class="small">${esc(ind.unidade)}</td>` +
      cenarios.map(k => `<td class="text-end">${cenFmt.num(c.totais.por_cenario[k][ind.coluna], casas)}</td>`).join('') +
      efeitos.map(e => {
        const x = c.totais.efeitos[e].indicadores[ind.coluna];
        return `<td class="text-end ${cenFmt.sinal(x.diferenca)}">${cenFmt.num(x.diferenca, casas)}<br><small>${cenFmt.pct(x.variacao_pct)}</small></td>`;
      }).join('') + '</tr>';
  }
  const p = c.participacao;
  html += `<tr><td>Participação nos recursos nacionais <small class="text-muted" title="${esc(p.denominador)}">(?)</small></td><td class="small">%</td>` +
    cenarios.map(k => `<td class="text-end">${cenFmt.pct(p.participacao_pct[k], 4)}</td>`).join('') +
    efeitos.map(e => `<td class="text-end ${cenFmt.sinal(p.variacao_pp[e])}">${cenFmt.pp(p.variacao_pp[e])}</td>`).join('') + '</tr></tbody>';
  el('cen-tabela-totais').innerHTML = html;
}

function renderTabelaComparativa(c) {
  const cab = ['UF', 'Rede', 'Matrículas A', 'Matrículas B', 'Recursos Fundeb A', 'Recursos Fundeb B',
    'Variação (R$)', 'Variação (%)', 'Compl. VAAF B−A', 'Compl. VAAT B−A', 'VAAF/aluno A → B', 'VAAT/aluno A → B', 'Particip. (p.p.)'];
  let html = '<thead><tr>' + cab.map(h => `<th>${h}</th>`).join('') + '</tr></thead><tbody>';
  for (const r of c.linhas) {
    html += `<tr>
      <td>${esc(r.uf)}</td>
      <td>${esc(r.nome)}${r.inabilitado_vaat ? ' <span class="badge bg-secondary" title="Inabilitada para a complementação VAAT">VAAT inab.</span>' : ''}</td>
      <td class="text-end">${cenFmt.num(r.matriculas_total_A)}</td>
      <td class="text-end">${cenFmt.num(r.matriculas_total_B)}</td>
      <td class="text-end">${cenFmt.moeda(r.recursos_fundeb_A)}</td>
      <td class="text-end">${cenFmt.moeda(r.recursos_fundeb_B)}</td>
      <td class="text-end ${cenFmt.sinal(r.recursos_fundeb_dif_B_A)}">${cenFmt.moeda(r.recursos_fundeb_dif_B_A)}</td>
      <td class="text-end ${cenFmt.sinal(r.recursos_fundeb_pct_B_A)}">${cenFmt.pct(r.recursos_fundeb_pct_B_A)}</td>
      <td class="text-end">${cenFmt.moeda(r.complemento_vaaf_dif_B_A)}</td>
      <td class="text-end">${cenFmt.moeda(r.complemento_vaat_dif_B_A)}</td>
      <td class="text-end">${cenFmt.num(r.vaaf_final_A, 2)} → ${cenFmt.num(r.vaaf_final_B, 2)}</td>
      <td class="text-end">${cenFmt.num(r.vaat_final_A, 2)} → ${cenFmt.num(r.vaat_final_B, 2)}</td>
      <td class="text-end ${cenFmt.sinal(r.participacao_nacional_pp_B_A)}">${cenFmt.pp(r.participacao_nacional_pp_B_A)}</td>
    </tr>`;
  }
  el('cen-tabela-comparativa').innerHTML = html + '</tbody>';
}

// A aba só carrega os dados quando é aberta pela primeira vez.
document.addEventListener('click', (e) => {
  if (e.target.closest('[data-tab="cenario"]')) initCenario();
});
