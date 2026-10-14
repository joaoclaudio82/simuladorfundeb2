/**
 * Simulador FUNDEB v2 — Cenário nacional (FND-06, FND-07, FND-08, FND-11)
 * Cenários nacionais A, B, C e D com receita constante e ajustes independentes
 * de matrículas por cenário e rede.
 */

const CENARIOS_SIMULACAO_ORDEM = ['B', 'C', 'D'];

const NOMES_CENARIOS = {
  A: 'Cenário A — Referência',
  B: 'Cenário B — Simulação 1',
  C: 'Cenário C — Simulação 2',
  D: 'Cenário D — Simulação 3',
};

const EXPLICACOES_CENARIOS = {
  A: 'Matrículas originais da base selecionada.',
  B: 'Ajustes próprios de matrículas, mantendo a mesma receita da referência.',
  C: 'Ajustes próprios de matrículas, mantendo a mesma receita da referência.',
  D: 'Ajustes próprios de matrículas, mantendo a mesma receita da referência.',
};

const cen = {
  bases: [],
  base: null,           // detalhe da base ativa (GET /api/bases/{id})
  aviso: '',
  categorias: {},       // etapa -> nome
  cenariosAtivos: ['B', 'C', 'D'],
  ajustesPorCenario: {
    B: new Map(),
    C: new Map(),
    D: new Map(),
  },
  edicao: null,         // { cenario, ibge, rede, anoExercicio, baseId, rascunho: Map, sujo: boolean, excluidoDuranteEdicao: boolean }
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
function nomeCenario(id, metadados = null) {
  if (metadados && metadados.nomes_cenarios && metadados.nomes_cenarios[id]) {
    return metadados.nomes_cenarios[id];
  }
  return NOMES_CENARIOS[id] || `Cenário ${id}`;
}

function totalAjustesSalvos() {
  return cen.cenariosAtivos.reduce((acc, c) => acc + (cen.ajustesPorCenario[c]?.size || 0), 0);
}

function chaveDefinir(ibge, cat) { return `${ibge}|${cat}|definir`; }
function chaveConverter(ibge, origem, destino) { return `${ibge}|${origem}|converter|${destino}`; }

function clonarAjustesRede(cenarioId, ibge) {
  const origem = cen.ajustesPorCenario[cenarioId] || new Map();
  const copia = new Map();
  for (const [chave, item] of origem.entries()) {
    if (Number(item.ibge) === Number(ibge)) {
      copia.set(chave, { ...item });
    }
  }
  return copia;
}

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
      `<option value="${esc(b.base_id)}"${b.padrao ? ' selected' : ''}>${esc(b.ano_exercicio)} — ${esc(b.periodo_exibicao || b.situacao)}</option>`).join('');
    preencherUFs(estados.regioes);
    await trocarBase();
  } catch (e) {
    cen.iniciado = false;
    el('cen-base-info').innerHTML = `<div class="alert alert-danger">Falha ao carregar: ${esc(e.message)}</div>`;
    return;
  }

  el('cen-base').addEventListener('change', async () => {
    if ((totalAjustesSalvos() > 0 || (cen.edicao && cen.edicao.sujo)) &&
        !confirm('Trocar de exercício descarta as alterações pendentes. Continuar?')) {
      el('cen-base').value = cen.base.base_id;
      return;
    }
    await trocarBase();
  });

  el('cen-cenario-alvo').addEventListener('change', () => {
    // Se não há edição com rascunho pendente mas já existe uma rede carregada, podemos atualizar o cabeçalho se ainda não editou;
    // se já existe uma edição aberta, preservamos a identidade capturada da edição aberta até que o usuário clique em carregar/abrir outra edição.
    if (!cen.edicao) {
      atualizarCabecalhoEdicao();
    }
  });

  el('cen-uf').addEventListener('change', carregarRedesUF);
  el('cen-rede').addEventListener('change', () => {
    if (!cen.edicao || !cen.edicao.sujo) {
      carregarRedeNoCenarioSelecionado();
    }
  });
  el('cen-btn-abrir-edicao').addEventListener('click', carregarRedeNoCenarioSelecionado);
  el('cen-busca').addEventListener('input', renderFormRede);
  el('cen-todas').addEventListener('change', renderFormRede);
  el('cen-btn-converter').addEventListener('click', adicionarConversaoRascunho);
  el('cen-btn-salvar-edicao').addEventListener('click', salvarEdicaoAtiva);
  el('cen-btn-cancelar-edicao').addEventListener('click', cancelarEdicaoAtiva);
  el('cen-btn-limpar').addEventListener('click', limparTodosAjustes);
  el('cen-btn-calcular').addEventListener('click', calcularCenario);
  el('cen-recorte').addEventListener('change', trocarRecorte);

  document.querySelectorAll('#cen-parametros input, #cen-parametros select').forEach(x =>
    x.addEventListener('input', marcarDesatualizado));
  document.querySelectorAll('[data-cen-export]').forEach(btn =>
    btn.addEventListener('click', () => exportar(btn.dataset.cenExport)));
}

async function trocarBase() {
  const id = el('cen-base').value;
  el('cen-base-info').innerHTML = '<p class="small text-muted">Carregando a base…</p>';
  cen.base = await cenFetch(`/api/bases/${encodeURIComponent(id)}`);
  cen.cenariosAtivos = ['B', 'C', 'D'];
  cen.ajustesPorCenario = { B: new Map(), C: new Map(), D: new Map() };
  cen.edicao = null;
  cen.cacheRedes.clear();
  cen.categorias = {};
  renderBaseInfo();
  preencherParametros();
  el('cen-rede').innerHTML = '<option value="">Selecione a UF</option>';
  el('cen-uf').value = '';
  sincronizarSeletorCenarioAlvo();
  renderPainelCenarios();
  ocultarAlertaEdicao();
  atualizarCabecalhoEdicao();
  renderFormRede();
  atualizarPendentes();
}

function renderBaseInfo() {
  const b = cen.base;
  const badge = b.homologada
    ? '<span class="badge bg-success">homologada</span>'
    : b.periodo_exibicao
      ? `<span class="badge cen-badge-periodo">${esc(b.periodo_exibicao)}</span>`
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
// Gestão dos cenários B, C e D (com A fixo como referência)
// -------------------------------------------------------------------------
function sincronizarSeletorCenarioAlvo() {
  const sel = el('cen-cenario-alvo');
  if (!sel) return;
  const valorAnterior = sel.value;
  sel.innerHTML = cen.cenariosAtivos.map(id =>
    `<option value="${id}">${esc(NOMES_CENARIOS[id])}</option>`
  ).join('');
  if (cen.cenariosAtivos.includes(valorAnterior)) {
    sel.value = valorAnterior;
  } else if (cen.cenariosAtivos.length > 0) {
    sel.value = cen.cenariosAtivos[0];
  }
}

function renderPainelCenarios() {
  const container = el('cen-lista-cenarios');
  if (!container) return;
  let html = '';
  for (const id of CENARIOS_SIMULACAO_ORDEM) {
    const ativo = cen.cenariosAtivos.includes(id);
    if (ativo) {
      const mapa = cen.ajustesPorCenario[id] || new Map();
      const qtdAjustes = mapa.size;
      const qtdRedes = new Set([...mapa.values()].map(a => a.ibge)).size;
      const emEdicao = cen.edicao && cen.edicao.cenario === id && !cen.edicao.excluidoDuranteEdicao;
      html += `
        <div class="cen-cenario-item${emEdicao ? ' cen-cenario-em-edicao' : ''}" data-cen-card="${id}">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-1">
            <span class="cen-badge cen-badge-${id}">${esc(NOMES_CENARIOS[id])}</span>
            <div class="d-flex gap-1">
              <button type="button" class="btn btn-outline-primary btn-sm py-0 px-2" data-cen-selecionar="${id}" title="Selecionar ${esc(NOMES_CENARIOS[id])} para edição">
                Editar
              </button>
              <button type="button" class="btn btn-outline-danger btn-sm py-0 px-2" data-cen-excluir="${id}" title="Excluir ${esc(NOMES_CENARIOS[id])}">
                Excluir
              </button>
            </div>
          </div>
          <p class="small text-muted mb-1 mt-1">${esc(EXPLICACOES_CENARIOS[id])}</p>
          <div class="small">
            ${qtdAjustes > 0
              ? `<strong>${qtdAjustes}</strong> ajuste(s) salvo(s) em <strong>${qtdRedes}</strong> rede(s)`
              : '<span class="text-muted">Sem ajustes (matrículas originais da base)</span>'}
            ${emEdicao ? ' · <span class="text-primary fw-semibold">Em edição no formulário</span>' : ''}
          </div>
        </div>`;
    } else {
      html += `
        <div class="cen-cenario-item bg-light text-muted d-flex justify-content-between align-items-center" data-cen-card-inativo="${id}">
          <span class="small">${esc(NOMES_CENARIOS[id])} (excluído)</span>
          <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2" data-cen-restaurar="${id}">
            + Restaurar Cenário ${id}
          </button>
        </div>`;
    }
  }
  container.innerHTML = html;

  container.querySelectorAll('[data-cen-selecionar]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.cenSelecionar;
      el('cen-cenario-alvo').value = id;
      const ibge = parseInt(el('cen-rede').value) || cen.edicao?.ibge;
      if (ibge) {
        await abrirEdicaoCenarioRede(id, ibge);
      } else {
        atualizarCabecalhoEdicao();
      }
    });
  });

  container.querySelectorAll('[data-cen-excluir]').forEach(btn => {
    btn.addEventListener('click', () => excluirCenarioSimulacao(btn.dataset.cenExcluir));
  });

  container.querySelectorAll('[data-cen-restaurar]').forEach(btn => {
    btn.addEventListener('click', () => restaurarCenarioSimulacao(btn.dataset.cenRestaurar));
  });
}

function excluirCenarioSimulacao(cenarioId) {
  if (!CENARIOS_SIMULACAO_ORDEM.includes(cenarioId)) return;
  if (!cen.cenariosAtivos.includes(cenarioId)) return;
  if (cen.cenariosAtivos.length <= 1) {
    exibirAlertaEdicao('Mantenha pelo menos uma simulação ativa além da referência (Cenário A).');
    return;
  }
  // Remove apenas os ajustes deste cenário; nunca transfere ajustes para outro cenário.
  cen.ajustesPorCenario[cenarioId] = new Map();
  cen.cenariosAtivos = cen.cenariosAtivos.filter(c => c !== cenarioId);
  sincronizarSeletorCenarioAlvo();

  if (cen.edicao && cen.edicao.cenario === cenarioId) {
    cen.edicao.excluidoDuranteEdicao = true;
    exibirAlertaEdicao(
      `O ${NOMES_CENARIOS[cenarioId]} foi excluído durante a edição. O salvamento neste cenário foi bloqueado.`
    );
    atualizarCabecalhoEdicao();
  }
  renderPainelCenarios();
  atualizarPendentes();
}

function restaurarCenarioSimulacao(cenarioId) {
  if (!CENARIOS_SIMULACAO_ORDEM.includes(cenarioId)) return;
  if (!cen.cenariosAtivos.includes(cenarioId)) {
    cen.cenariosAtivos = CENARIOS_SIMULACAO_ORDEM.filter(
      c => c === cenarioId || cen.cenariosAtivos.includes(c)
    );
    cen.ajustesPorCenario[cenarioId] = new Map();
  }
  sincronizarSeletorCenarioAlvo();
  renderPainelCenarios();
  marcarDesatualizado();
}

// -------------------------------------------------------------------------
// Seleção e edição de redes (formulário lateral com identidade capturada)
// -------------------------------------------------------------------------
function exibirAlertaEdicao(msg) {
  const box = el('cen-edicao-alerta');
  if (!box) return;
  box.textContent = msg;
  box.classList.remove('d-none');
}

function ocultarAlertaEdicao() {
  const box = el('cen-edicao-alerta');
  if (!box) return;
  box.textContent = '';
  box.classList.add('d-none');
}

function atualizarCabecalhoEdicao() {
  const titulo = el('cen-form-titulo');
  const contexto = el('cen-edicao-contexto');
  const btnSalvar = el('cen-btn-salvar-edicao');
  const txtSalvar = el('cen-btn-salvar-texto');
  const btnCancelar = el('cen-btn-cancelar-edicao');

  const cenarioExibido = cen.edicao ? cen.edicao.cenario : (el('cen-cenario-alvo')?.value || 'B');
  if (titulo) {
    titulo.textContent = `Editar matrículas — Cenário ${cenarioExibido}`;
  }
  if (txtSalvar) {
    txtSalvar.textContent = `Salvar no cenário ${cenarioExibido}`;
  }

  if (cen.edicao && cen.edicao.rede) {
    const r = cen.edicao.rede;
    const bloqueado = Boolean(cen.edicao.excluidoDuranteEdicao || !cen.cenariosAtivos.includes(cen.edicao.cenario));
    if (contexto) {
      contexto.classList.remove('d-none');
      contexto.innerHTML = `
        <div><strong>${esc(NOMES_CENARIOS[cen.edicao.cenario])}</strong>${bloqueado ? ' <span class="badge bg-danger">Cenário excluído</span>' : ''}</div>
        <div>Rede em edição: <strong>${esc(r.nome)} (${esc(r.uf)})</strong> · ${esc(r.tipo_rede)}</div>
        <div>Exercício em edição: <strong>${esc(cen.edicao.anoExercicio)}</strong> (${esc(cen.edicao.baseId)})</div>`;
    }
    if (btnSalvar) btnSalvar.disabled = bloqueado;
    if (btnCancelar) btnCancelar.disabled = false;
  } else {
    if (contexto) {
      contexto.classList.add('d-none');
      contexto.innerHTML = '';
    }
    if (btnSalvar) btnSalvar.disabled = true;
    if (btnCancelar) btnCancelar.disabled = true;
  }
}

async function carregarRedesUF() {
  const uf = el('cen-uf').value;
  const sel = el('cen-rede');
  sel.innerHTML = '<option value="">Carregando...</option>';
  if (!uf) {
    sel.innerHTML = '<option value="">Selecione a UF</option>';
    return;
  }
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
  if (estaduais.length && (!cen.edicao || !cen.edicao.sujo)) {
    sel.value = estaduais[0].ibge;
    await carregarRedeNoCenarioSelecionado();
  }
}

async function obterDadosRede(ibge) {
  const id = Number(ibge);
  if (!cen.cacheRedes.has(id)) {
    const r = await cenFetch(`/api/entes/${id}/matriculas?base_id=${encodeURIComponent(cen.base.base_id)}`);
    cen.cacheRedes.set(id, r);
    if (!Object.keys(cen.categorias).length) {
      cen.categorias = r.nomes_categorias;
      preencherCategoriasConversao();
    }
  }
  return cen.cacheRedes.get(id);
}

async function carregarRedeNoCenarioSelecionado() {
  const ibge = parseInt(el('cen-rede').value);
  const cenarioId = el('cen-cenario-alvo').value || cen.cenariosAtivos[0] || 'B';
  if (!ibge) {
    if (!cen.edicao) {
      renderFormRede();
    }
    return;
  }
  await abrirEdicaoCenarioRede(cenarioId, ibge);
}

async function abrirEdicaoCenarioRede(cenarioId, ibge) {
  if (!CENARIOS_SIMULACAO_ORDEM.includes(cenarioId) || !cen.cenariosAtivos.includes(cenarioId)) {
    exibirAlertaEdicao(`O cenário ${cenarioId} não está ativo para edição.`);
    return;
  }
  ocultarAlertaEdicao();
  const rede = await obterDadosRede(ibge);

  // Sincroniza os seletores visuais de UF / Ente / Cenário ao abrir a edição
  if (el('cen-cenario-alvo')) el('cen-cenario-alvo').value = cenarioId;
  if (el('cen-uf') && el('cen-uf').value !== rede.uf) {
    el('cen-uf').value = rede.uf;
    const dados = await cenFetch(`/api/entes?uf=${encodeURIComponent(rede.uf)}&base_id=${encodeURIComponent(cen.base.base_id)}`);
    const estaduais = dados.entes.filter(e => e.tipo_rede !== 'rede municipal');
    const municipais = dados.entes.filter(e => e.tipo_rede === 'rede municipal');
    let html = '<option value="">Selecione...</option>';
    html += estaduais.map(e => `<option value="${e.ibge}">${esc(e.nome)} — ${esc(e.tipo_rede)}</option>`).join('');
    if (municipais.length) {
      html += '<optgroup label="Redes municipais">' +
        municipais.map(e => `<option value="${e.ibge}">${esc(e.nome)} (${e.ibge})</option>`).join('') + '</optgroup>';
    }
    el('cen-rede').innerHTML = html;
  }
  if (el('cen-rede')) el('cen-rede').value = String(rede.ibge);

  // Captura a identidade do cenário, da rede e do exercício no momento da abertura
  cen.edicao = {
    cenario: cenarioId,
    ibge: Number(rede.ibge),
    rede,
    anoExercicio: cen.base?.ano_exercicio ?? '',
    baseId: cen.base?.base_id ?? '',
    rascunho: clonarAjustesRede(cenarioId, rede.ibge),
    sujo: false,
    excluidoDuranteEdicao: false,
  };

  atualizarCabecalhoEdicao();
  renderPainelCenarios();
  renderFormRede();
}

function renderFormRede() {
  const box = el('cen-form');
  const boxConv = el('cen-rascunho-conversoes');
  if (boxConv) boxConv.innerHTML = '';

  if (!cen.edicao || !cen.edicao.rede) {
    box.innerHTML = '<p class="small text-muted">Selecione um cenário (B, C ou D), uma UF e um ente federado.</p>';
    atualizarCabecalhoEdicao();
    return;
  }

  const ed = cen.edicao;
  const r = ed.rede;
  const busca = el('cen-busca').value.trim().toLowerCase();
  const todas = el('cen-todas').checked;
  const itens = Object.entries(r.matriculas).filter(([etapa, original]) => {
    const editado = ed.rascunho.has(chaveDefinir(r.ibge, etapa));
    if (busca && !nomeCategoria(etapa).toLowerCase().includes(busca)) return false;
    return todas || busca || original > 0 || editado;
  });

  let html = `<p class="mb-1"><strong>${esc(r.nome)}</strong> — ${esc(r.uf)} · ${esc(r.tipo_rede)}
    · <span class="cen-badge cen-badge-${ed.cenario}">${esc(NOMES_CENARIOS[ed.cenario])}</span></p>
    <p class="small text-muted mb-2">Mostrando ${itens.length} de ${Object.keys(r.matriculas).length} categorias (base original de ${esc(ed.anoExercicio)}).
    Altere os valores abaixo e clique em <strong>Salvar no cenário ${esc(ed.cenario)}</strong> para confirmar.</p>
    <div class="cen-categorias">`;

  for (const [etapa, original] of itens) {
    const pend = ed.rascunho.get(chaveDefinir(r.ibge, etapa));
    const valor = pend ? pend.valor : original;
    html += `<div class="matricula-item${pend ? ' cen-editado' : ''}">
      <label title="${esc(etapa)}">${esc(nomeCategoria(etapa))}<br><small class="text-muted">original (A): ${cenFmt.num(original, 2)}</small></label>
      <input type="number" class="form-control form-control-sm" min="0" step="any"
             data-cen-etapa="${esc(etapa)}" value="${valor}">
    </div>`;
  }
  box.innerHTML = html + '</div>';

  box.querySelectorAll('input[data-cen-etapa]').forEach(inp => inp.addEventListener('change', () => {
    registrarDefinicaoRascunho(inp.dataset.cenEtapa, inp.value);
    inp.closest('.matricula-item').classList.toggle(
      'cen-editado',
      ed.rascunho.has(chaveDefinir(r.ibge, inp.dataset.cenEtapa))
    );
  }));

  renderConversoesRascunho();
  atualizarCabecalhoEdicao();
}

function renderConversoesRascunho() {
  const boxConv = el('cen-rascunho-conversoes');
  if (!boxConv || !cen.edicao) return;
  const conversoes = [...cen.edicao.rascunho.entries()].filter(([, a]) => a.operacao === 'converter');
  if (!conversoes.length) {
    boxConv.innerHTML = '';
    return;
  }
  boxConv.innerHTML = `<div class="fw-semibold mb-1">Conversões nesta edição (${esc(NOMES_CENARIOS[cen.edicao.cenario])}):</div>` +
    conversoes.map(([chave, a]) => `
      <div class="d-flex justify-content-between align-items-center border rounded px-2 py-1 mb-1 bg-light">
        <span>${esc(nomeCategoria(a.categoria))} → ${esc(nomeCategoria(a.categoria_destino))}: <strong>${cenFmt.num(a.valor, 2)}</strong></span>
        <button type="button" class="btn btn-sm btn-link text-danger p-0" data-cen-rem-conv="${esc(chave)}">remover</button>
      </div>
    `).join('');
  boxConv.querySelectorAll('[data-cen-rem-conv]').forEach(btn => {
    btn.addEventListener('click', () => {
      cen.edicao.rascunho.delete(btn.dataset.cenRemConv);
      cen.edicao.sujo = true;
      renderConversoesRascunho();
    });
  });
}

function registrarDefinicaoRascunho(etapa, texto) {
  if (!cen.edicao || !cen.edicao.rede) return;
  const rede = cen.edicao.rede;
  const chave = chaveDefinir(rede.ibge, etapa);
  const original = rede.matriculas[etapa];
  const valor = parseFloat(texto);
  if (texto === '' || !Number.isFinite(valor) || valor < 0) {
    alert('Informe um número de matrículas maior ou igual a zero.');
    return;
  }
  if (Math.abs(valor - original) < 1e-9) {
    cen.edicao.rascunho.delete(chave);
  } else {
    cen.edicao.rascunho.set(chave, {
      cenario: cen.edicao.cenario,
      ibge: rede.ibge,
      uf: rede.uf,
      nome: rede.nome,
      operacao: 'definir',
      categoria: etapa,
      valor,
      original,
    });
  }
  cen.edicao.sujo = true;
}

function adicionarConversaoRascunho() {
  if (!cen.edicao || !cen.edicao.rede) {
    alert('Selecione um ente federado.');
    return;
  }
  const r = cen.edicao.rede;
  const origem = el('cen-conv-origem').value;
  const destino = el('cen-conv-destino').value;
  const valor = parseFloat(el('cen-conv-valor').value);
  if (origem === destino) { alert('Origem e destino devem ser diferentes.'); return; }
  if (!Number.isFinite(valor) || valor <= 0) { alert('Informe uma quantidade positiva.'); return; }
  const chave = chaveConverter(r.ibge, origem, destino);
  const atual = cen.edicao.rascunho.get(chave);
  const definida = cen.edicao.rascunho.get(chaveDefinir(r.ibge, origem));
  const disponivel = definida ? definida.valor : (r.matriculas[origem] || 0);
  const jaConvertido = [...cen.edicao.rascunho.values()]
    .filter(a => a.operacao === 'converter' && a.categoria === origem)
    .reduce((s, a) => s + a.valor, 0);
  if (jaConvertido + valor > disponivel + 1e-9) {
    alert(`${nomeCategoria(origem)} tem ${cenFmt.num(disponivel, 2)} matrícula(s) nesta rede` +
      (jaConvertido > 0 ? ` e ${cenFmt.num(jaConvertido, 2)} já estão em conversão` : '') +
      '. Informe uma quantidade menor.');
    return;
  }
  cen.edicao.rascunho.set(chave, {
    cenario: cen.edicao.cenario,
    ibge: r.ibge,
    uf: r.uf,
    nome: r.nome,
    operacao: 'converter',
    categoria: origem,
    categoria_destino: destino,
    valor: (atual ? atual.valor : 0) + valor,
    original: r.matriculas[origem],
  });
  cen.edicao.sujo = true;
  el('cen-conv-valor').value = '';
  renderConversoesRascunho();
}

function salvarEdicaoAtiva() {
  if (!cen.edicao || !cen.edicao.rede) return;
  const { cenario, ibge } = cen.edicao;

  // Se o cenário foi excluído enquanto o formulário estava aberto, impede o salvamento e informa o usuário.
  if (cen.edicao.excluidoDuranteEdicao || !cen.cenariosAtivos.includes(cenario)) {
    const msg = `Não é possível salvar: o ${NOMES_CENARIOS[cenario] || `Cenário ${cenario}`} foi excluído durante a edição.`;
    exibirAlertaEdicao(msg);
    alert(msg);
    return;
  }

  ocultarAlertaEdicao();
  const mapaCenario = cen.ajustesPorCenario[cenario] || new Map();
  // Remove entradas anteriores apenas desta rede neste cenário capturado
  for (const [chave, item] of [...mapaCenario.entries()]) {
    if (Number(item.ibge) === Number(ibge)) {
      mapaCenario.delete(chave);
    }
  }
  // Grava os novos ajustes da rede no cenário capturado ao abrir o formulário
  for (const [chave, item] of cen.edicao.rascunho.entries()) {
    mapaCenario.set(chave, { ...item, cenario });
  }
  cen.ajustesPorCenario[cenario] = mapaCenario;
  cen.edicao.sujo = false;

  renderPainelCenarios();
  atualizarPendentes();
  renderFormRede();
}

function cancelarEdicaoAtiva() {
  if (!cen.edicao || !cen.edicao.rede) return;
  ocultarAlertaEdicao();
  // Descarta somente as alterações ainda não salvas no rascunho, restaurando o estado salvo deste cenário e rede
  if (cen.cenariosAtivos.includes(cen.edicao.cenario) && !cen.edicao.excluidoDuranteEdicao) {
    cen.edicao.rascunho = clonarAjustesRede(cen.edicao.cenario, cen.edicao.ibge);
    cen.edicao.sujo = false;
    renderFormRede();
  } else {
    cen.edicao = null;
    renderPainelCenarios();
    renderFormRede();
  }
}

function limparTodosAjustes() {
  for (const id of CENARIOS_SIMULACAO_ORDEM) {
    cen.ajustesPorCenario[id] = new Map();
  }
  if (cen.edicao && cen.edicao.rede) {
    cen.edicao.rascunho = new Map();
    cen.edicao.sujo = false;
  }
  ocultarAlertaEdicao();
  renderPainelCenarios();
  atualizarPendentes();
  renderFormRede();
}

// -------------------------------------------------------------------------
// Tabela de ajustes por cenário (B, C, D)
// -------------------------------------------------------------------------
function listarTodosAjustesSalvos() {
  const itens = [];
  for (const cenarioId of cen.cenariosAtivos) {
    const mapa = cen.ajustesPorCenario[cenarioId] || new Map();
    for (const [chave, a] of mapa.entries()) {
      itens.push({ cenario: cenarioId, chave, ajuste: { ...a, cenario: cenarioId } });
    }
  }
  return itens.sort((x, y) => {
    if (x.cenario !== y.cenario) return x.cenario.localeCompare(y.cenario);
    const kx = `${x.ajuste.uf}|${x.ajuste.nome}|${x.ajuste.categoria}`;
    const ky = `${y.ajuste.uf}|${y.ajuste.nome}|${y.ajuste.categoria}`;
    return kx.localeCompare(ky, 'pt-BR');
  });
}

function atualizarPendentes() {
  const tbody = el('cen-pendentes-corpo');
  const lista = listarTodosAjustesSalvos();
  let acrescidas = 0, reduzidas = 0, convertidas = 0;

  tbody.innerHTML = lista.length ? lista.map(({ cenario, chave, ajuste: a }) => {
    let novo;
    if (a.operacao === 'converter') {
      convertidas += a.valor;
      novo = `${cenFmt.num(a.valor, 2)} → ${esc(nomeCategoria(a.categoria_destino))}`;
    } else {
      const d = a.valor - a.original;
      if (d > 0) acrescidas += d; else reduzidas -= d;
      novo = cenFmt.num(a.valor, 2);
    }
    return `<tr data-cen-linha-cenario="${esc(cenario)}" data-cen-linha-ibge="${a.ibge}">
      <td><span class="cen-badge cen-badge-${esc(cenario)}">${esc(NOMES_CENARIOS[cenario])}</span></td>
      <td>${esc(a.uf)}</td>
      <td>${esc(a.nome)}</td>
      <td>${a.operacao === 'converter' ? 'conversão' : 'novo valor'}</td>
      <td>${esc(nomeCategoria(a.categoria))}</td>
      <td class="text-end">${cenFmt.num(a.original, 2)}</td>
      <td class="text-end">${novo}</td>
      <td class="text-end">
        <button type="button" class="btn btn-sm btn-outline-primary me-1" data-cen-editar-cenario="${esc(cenario)}" data-cen-editar-ibge="${a.ibge}" title="Editar matrículas desta rede no ${esc(NOMES_CENARIOS[cenario])}">
          Editar
        </button>
        <button type="button" class="btn btn-sm btn-outline-danger" data-cen-remover-cenario="${esc(cenario)}" data-cen-remover="${esc(chave)}" title="Remover ajuste do ${esc(NOMES_CENARIOS[cenario])}">
          <i class="fas fa-times"></i>
        </button>
      </td>
    </tr>`;
  }).join('') : '<tr><td colspan="8" class="text-muted small">Nenhum ajuste salvo nos cenários B, C ou D. O Cenário A — Referência mantém as matrículas originais da base.</td></tr>';

  tbody.querySelectorAll('[data-cen-editar-cenario]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const cenId = btn.dataset.cenEditarCenario;
      const ibge = parseInt(btn.dataset.cenEditarIbge);
      await abrirEdicaoCenarioRede(cenId, ibge);
    });
  });

  tbody.querySelectorAll('[data-cen-remover]').forEach(btn => {
    btn.addEventListener('click', () => {
      const cenId = btn.dataset.cenRemoverCenario;
      const chave = btn.dataset.cenRemover;
      cen.ajustesPorCenario[cenId]?.delete(chave);
      if (cen.edicao && cen.edicao.cenario === cenId && !cen.edicao.sujo) {
        cen.edicao.rascunho = clonarAjustesRede(cenId, cen.edicao.ibge);
        renderFormRede();
      }
      renderPainelCenarios();
      atualizarPendentes();
    });
  });

  const redes = new Set(lista.map(item => item.ajuste.ibge)).size;
  const porCenTexto = cen.cenariosAtivos.map(c => {
    const n = cen.ajustesPorCenario[c]?.size || 0;
    return `${NOMES_CENARIOS[c]}: <strong>${n}</strong>`;
  }).join(' · ');

  el('cen-pendentes-resumo').innerHTML =
    `${lista.length} ajuste(s) salvo(s) em ${redes} rede(s) (${porCenTexto}) · novas matrículas: <strong>${cenFmt.num(acrescidas, 2)}</strong>
     · matrículas retiradas: <strong>${cenFmt.num(reduzidas, 2)}</strong>
     · convertidas: <strong>${cenFmt.num(convertidas, 2)}</strong>`;
  marcarDesatualizado();
}

// -------------------------------------------------------------------------
// Requisição e execução
// -------------------------------------------------------------------------
function numeroOuNulo(id) {
  const elem = el(id);
  if (!elem) return null;
  const v = elem.value;
  return v === '' ? null : parseFloat(v);
}

function cenariosComAjustes() {
  return cen.cenariosAtivos.filter(c => (cen.ajustesPorCenario[c]?.size || 0) > 0);
}

function montarRequisicao() {
  const ajustes = [];
  const ajustesPorCenario = {};
  const executar = cenariosComAjustes();
  for (const cenarioId of executar) {
    const mapa = cen.ajustesPorCenario[cenarioId] || new Map();
    const listaCen = [...mapa.values()].map(a => {
      const x = {
        cenario: cenarioId,
        ibge: a.ibge,
        categoria: a.categoria,
        operacao: a.operacao,
        valor: a.valor,
      };
      if (a.categoria_destino) x.categoria_destino = a.categoria_destino;
      return x;
    });
    ajustesPorCenario[cenarioId] = listaCen;
    ajustes.push(...listaCen);
  }
  return {
    base_id: cen.base.base_id,
    modo_cenarios: 'matriculas_independentes',
    cenarios_ativos: executar,
    ajustes,
    ajustes_por_cenario: ajustesPorCenario,
    parametros: {
      complementacao_vaaf: numeroOuNulo('cen-vaaf'),
      complementacao_vaat: numeroOuNulo('cen-vaat'),
      complementacao_vaar: numeroOuNulo('cen-vaar'),
    },
    receita: { tipo: 'constante', taxa: 0 },
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
  if (!cenariosComAjustes().length) {
    alert('Salve ajustes de matrículas em pelo menos um cenário (B, C ou D) antes de calcular.');
    return;
  }
  if (cen.edicao && cen.edicao.sujo) {
    if (!confirm(`Existem alterações não salvas no formulário de ${NOMES_CENARIOS[cen.edicao.cenario]}. Deseja calcular usando apenas os ajustes já salvos?`)) {
      return;
    }
  }
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
// Resultados e comparação entre cenários (A, B, C, D)
// -------------------------------------------------------------------------
function renderResultado(dados) {
  const m = dados.metadados;
  const c = dados.comparacao;
  el('cen-resultados').classList.remove('d-none');
  el('cen-exportar').querySelectorAll('button').forEach(b => { b.disabled = false; });

  renderTotais(c, m);

  const u = c.universo;
  const porCenarioUniv = u.por_cenario
    ? Object.entries(u.por_cenario).map(([k, info]) =>
        `<strong>${esc(nomeCenario(k, m))} − A</strong>: ${cenFmt.num(info.redes_sem_ajuste_afetadas)} redes sem ajuste direto afetadas (fora do recorte: ${cenFmt.moeda(info.variacao_fora_do_recorte)})`
      ).join(' · ')
    : `Redes fora do recorte com variação de recursos: <strong>${cenFmt.num(u.redes_fora_do_recorte_afetadas)}</strong> (${cenFmt.moeda(u.variacao_fora_do_recorte)}) · redes sem ajuste direto afetadas: ${cenFmt.num(u.redes_sem_ajuste_afetadas)}`;

  el('cen-universo').innerHTML = `Impacto sistêmico nacional (redistribuição entre redes do mesmo fundo): ${porCenarioUniv}`;
}

function renderTotais(c, m) {
  const cenarios = Object.keys(c.totais.por_cenario);
  const efeitos = Object.keys(c.totais.efeitos);
  const rotuloEfeito = (e) => e.replace('_', ' − ');
  let html = '<thead><tr><th>Indicador</th><th>Unidade</th>' +
    cenarios.map(k => `<th class="text-end" title="${esc(m.cenarios[k] || '')}">${esc(nomeCenario(k, m))}</th>`).join('') +
    efeitos.map(e => `<th class="text-end" title="${esc(c.efeitos[e] || '')}">${rotuloEfeito(e)}</th>`).join('') + '</tr></thead><tbody>';
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

// A aba só carrega os dados quando é aberta pela primeira vez.
document.addEventListener('click', (e) => {
  if (e.target.closest('[data-tab="cenario"]')) initCenario();
});
