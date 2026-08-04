/**
 * Simulador FUNDEB v2 — Frontend Logic
 */

// =========================================================================
// Estado global
// =========================================================================
const state = {
  pesos: null,
  estados: null,
  regioes: null,
  etapas: null,
  ultimaSimulacao: null,
  municipioMatriculas: null,
  user: null,
};

const API = '';  // base URL (mesmo servidor)

// =========================================================================
// Utilidades
// =========================================================================
const fmt = {
  moeda: (v) => v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }),
  numero: (v) => v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 2 }),
  pct: (v) => v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + '%',
};

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

// apiFetch definido em auth.js (credentials + redirect 401)

function buildTable(headers, rows) {
  let html = '<thead><tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr></thead><tbody>';
  for (const row of rows) {
    html += '<tr>' + row.map(c => `<td>${c}</td>`).join('') + '</tr>';
  }
  html += '</tbody>';
  return html;
}

// =========================================================================
// Navegação sidebar
// =========================================================================
function isMobile() { return window.innerWidth <= 768; }

function closeSidebarMobile() {
  const sidebar = $('#sidebar');
  const backdrop = $('#sidebar-backdrop');
  if (sidebar) sidebar.classList.remove('open');
  if (backdrop) backdrop.classList.remove('visible');
  document.body.style.overflow = '';
}

function openSidebarMobile() {
  const sidebar = $('#sidebar');
  const backdrop = $('#sidebar-backdrop');
  if (sidebar) sidebar.classList.add('open');
  if (backdrop) backdrop.classList.add('visible');
  document.body.style.overflow = 'hidden';
}

function activateTab(tabId) {
  if (!tabId) return false;
  const panel = document.getElementById(`tab-${tabId}`);
  if (!panel) return false;
  $$('.sidebar-nav li[data-tab]').forEach((l) => {
    l.classList.toggle('active', l.dataset.tab === tabId);
  });
  $$('.tab-content').forEach((t) => t.classList.remove('active'));
  panel.classList.add('active');
  window.scrollTo(0, 0);
  return true;
}

function initNavigation() {
  const sidebar = $('#sidebar');
  const toggleBtn = $('#sidebar-toggle');
  const backdrop = $('#sidebar-backdrop');
  const sidebarNav = document.querySelector('.sidebar-nav');

  if (sidebarNav) {
    sidebarNav.addEventListener('click', (e) => {
      const li = e.target.closest('li[data-tab]');
      if (!li) return;
      activateTab(li.dataset.tab);
      if (isMobile()) closeSidebarMobile();
    });
  }

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      if (isMobile()) {
        const isOpen = sidebar.classList.contains('open');
        if (isOpen) closeSidebarMobile();
        else openSidebarMobile();
      } else {
        sidebar.classList.toggle('collapsed');
        const main = $('#main-content');
        if (main) main.classList.toggle('expanded');
      }
    });
  }

  if (backdrop) {
    backdrop.addEventListener('click', () => {
      if (isMobile()) closeSidebarMobile();
    });
  }

  window.addEventListener('resize', () => {
    if (!isMobile()) {
      closeSidebarMobile();
      if (sidebar) sidebar.classList.remove('collapsed');
      const main = $('#main-content');
      if (main) main.classList.remove('expanded');
    }
  });

  // Links/botoes com data-tab (ex: "Ir para Simulacao" na pagina principal)
  document.addEventListener('click', (e) => {
    const target = e.target.closest('[data-tab]');
    if (target && !target.closest('.sidebar-nav')) {
      e.preventDefault();
      activateTab(target.dataset.tab);
      if (isMobile()) closeSidebarMobile();
    }
  });
}

// exposto para app_multi_ano.js (abas injetadas apos o load)
window.activateFundebTab = activateTab;

// =========================================================================
// Carregar dados iniciais
// =========================================================================
async function initData() {
  const [pesosRes, estadosRes, etapasRes] = await Promise.all([
    apiFetch('/api/pesos'),
    apiFetch('/api/estados'),
    apiFetch('/api/etapas'),
  ]);
  state.pesos = pesosRes.map((p) => ({
    ...p,
    familia: p.familia || familiaSegmento(p.nome),
  }));
  state.estados = estadosRes.estados;
  state.regioes = estadosRes.regioes;
  state.etapas = etapasRes;

  renderPesos();
  populateEstadoSelectors();
}

// =========================================================================
// Pesos — accordion por família (igual FUNDEB 2026)
// =========================================================================
const ANO_PESOS_2024 = 2024;

function familiaSegmento(nome) {
  let n = String(nome);
  const sufixos = [
    ' Campo', ' Indígena', ' Indigena', ' Quilombola',
    ' Especial', ' Bilíngue De Surdos', ' Bilingue De Surdos',
    ' Urbano', ' Rural',
  ];
  for (const suf of sufixos) {
    if (n.includes(suf)) n = n.split(suf)[0];
  }
  return n.trim();
}

function pesoInputId2024(tipo, etapa) {
  return `peso-${tipo}-${ANO_PESOS_2024}-${etapa}`;
}

function renderPesos() {
  const container = document.getElementById('pesos-accordion-2024');
  if (!container || !state.pesos) return;

  const readOnly = typeof canEditPesos === 'function' && !canEditPesos();
  const roAttr = readOnly ? 'readonly disabled' : '';
  let banner = '';
  if (readOnly) {
    banner = `<div class="alert alert-info py-2 mb-3">
      <i class="fas fa-lock"></i> Somente administradores podem alterar os fatores de ponderação.
    </div>`;
  }

  const famMap = {};
  state.pesos.forEach((p) => {
    const fam = p.familia || p.nome;
    if (!famMap[fam]) famMap[fam] = [];
    famMap[fam].push(p);
  });

  let html = banner + `<div class="accordion" id="acc-pesos-${ANO_PESOS_2024}">`;
  let i = 0;
  for (const [fam, items] of Object.entries(famMap)) {
    const id = `acc-${ANO_PESOS_2024}-${i++}`;
    html += `<div class="accordion-item">
      <h2 class="accordion-header">
        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#${id}">
          ${fam} <span class="badge bg-secondary ms-2">${items.length} segmento${items.length > 1 ? 's' : ''}</span>
        </button>
      </h2>
      <div id="${id}" class="accordion-collapse collapse" data-bs-parent="#acc-pesos-${ANO_PESOS_2024}">
        <div class="accordion-body pesos-accordion-body">
          <div class="peso-segmento-header row g-2 d-none d-md-flex small text-muted fw-semibold mb-2">
            <div class="col-md-5">Segmento</div>
            <div class="col-md-3">Peso VAAF</div>
            <div class="col-md-3">Peso VAAT</div>
          </div>`;
    items.forEach((p) => {
      const vaaf = Number(p.peso_vaaf);
      const vaat = Number(p.peso_vaat);
      const idVaaf = pesoInputId2024('vaaf', p.etapa);
      const idVaat = pesoInputId2024('vaat', p.etapa);
      html += `<div class="peso-segmento-row row g-2 align-items-end mb-2 pb-2">
        <div class="col-12 col-md-5">
          <span class="peso-segmento-nome">${p.nome}</span>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label form-label-sm d-md-none" for="${idVaaf}">VAAF</label>
          <input type="number" class="form-control form-control-sm peso-input"
            id="${idVaaf}" data-etapa="${p.etapa}" data-tipo="vaaf"
            min="0" max="10" step="0.01" value="${vaaf}" ${roAttr}>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label form-label-sm d-md-none" for="${idVaat}">VAAT</label>
          <input type="number" class="form-control form-control-sm peso-input"
            id="${idVaat}" data-etapa="${p.etapa}" data-tipo="vaat"
            min="0" max="10" step="0.01" value="${vaat}" ${roAttr}>
        </div>
      </div>`;
    });
    html += `</div></div></div>`;
  }
  html += '</div>';
  container.innerHTML = html;
}

function getPesos() {
  const vaaf = [];
  const vaat = [];
  state.pesos.forEach((p) => {
    if (typeof canEditPesos === 'function' && !canEditPesos()) {
      vaaf.push(Number(p.peso_vaaf) || 0);
      vaat.push(Number(p.peso_vaat) || 0);
      return;
    }
    const elVaaf = document.getElementById(pesoInputId2024('vaaf', p.etapa));
    const elVaat = document.getElementById(pesoInputId2024('vaat', p.etapa));
    vaaf.push(parseFloat(elVaaf?.value ?? p.peso_vaaf) || 0);
    vaat.push(parseFloat(elVaat?.value ?? p.peso_vaat) || 0);
  });
  return { vaaf, vaat };
}

// =========================================================================
// Selectors de estados
// =========================================================================
function populateEstadoSelectors() {
  const selectors = ['#sel-mun-uf', '#sel-regional-uf'];
  selectors.forEach(sel => {
    const el = $(sel);
    if (!el) return;
    el.innerHTML = '<option value="">Selecione...</option>';
    for (const [regiao, ufs] of Object.entries(state.regioes)) {
      const group = document.createElement('optgroup');
      group.label = regiao;
      ufs.forEach(uf => {
        const opt = document.createElement('option');
        opt.value = uf;
        opt.textContent = uf;
        group.appendChild(opt);
      });
      el.appendChild(group);
    }
  });

  // Eventos
  $('#sel-mun-uf').addEventListener('change', loadMunicipios);
}

async function loadMunicipios() {
  const uf = $('#sel-mun-uf').value;
  const sel = $('#sel-mun-cidade');
  sel.innerHTML = '<option value="">Carregando...</option>';
  if (!uf) { sel.innerHTML = '<option value="">Selecione o estado primeiro</option>'; return; }

  const muns = await apiFetch(`/api/municipios?uf=${uf}`);
  sel.innerHTML = '<option value="">Selecione...</option>';
  muns.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.ibge;
    opt.textContent = `${m.nome} (${m.ibge})`;
    sel.appendChild(opt);
  });

  sel.addEventListener('change', onMunicipioSelecionado);
}

async function onMunicipioSelecionado() {
  const ibge = parseInt($('#sel-mun-cidade').value);
  if (!ibge) return;

  const data = await apiFetch(`/api/municipio/${ibge}/matriculas`);
  state.municipioMatriculas = data;
  renderMatriculasForm(data);
  $('#btn-simular-mun').disabled = false;
}

// =========================================================================
// Formulário de matrículas por município
// =========================================================================
function renderMatriculasForm(data) {
  const container = $('#matriculas-container');
  const groups = {
    'Educação Infantil': [],
    'Ensino Fundamental': [],
    'Ensino Médio': [],
    'Educação Profissional': [],
    'Educação Especial e EJA': [],
    'Educação Indígena/Quilombola': [],
    'Rede Conveniada': [],
  };

  for (const [etapa, valor] of Object.entries(data.matriculas)) {
    const nome = state.etapas[etapa] || etapa.replace(/_/g, ' ');
    const item = { etapa, nome, valor };

    if (etapa.includes('creche') || etapa.includes('pre_escola')) {
      if (etapa.includes('conveniada')) groups['Rede Conveniada'].push(item);
      else if (etapa.includes('ind_quil') || etapa.includes('esp_')) groups['Educação Indígena/Quilombola'].push(item);
      else groups['Educação Infantil'].push(item);
    } else if (etapa.includes('fundamental')) {
      if (etapa.includes('conveniada')) groups['Rede Conveniada'].push(item);
      else groups['Ensino Fundamental'].push(item);
    } else if (etapa.includes('medio') || etapa.includes('ensino_medio')) {
      if (etapa.includes('conveniada')) groups['Rede Conveniada'].push(item);
      else groups['Ensino Médio'].push(item);
    } else if (etapa.includes('profissional') || etapa.includes('itinerario')) {
      if (etapa.includes('conveniada')) groups['Rede Conveniada'].push(item);
      else groups['Educação Profissional'].push(item);
    } else if (etapa.includes('especial') || etapa.includes('aee') || etapa.includes('jovens')) {
      if (etapa.includes('conveniada')) groups['Rede Conveniada'].push(item);
      else groups['Educação Especial e EJA'].push(item);
    } else if (etapa.includes('indigena') || etapa.includes('quilombola') || etapa.includes('ind_quil')) {
      groups['Educação Indígena/Quilombola'].push(item);
    } else {
      if (etapa.includes('conveniada')) groups['Rede Conveniada'].push(item);
      else groups['Educação Profissional'].push(item);
    }
  }

  let html = `<p class="mb-2"><strong>${data.nome}</strong> — ${data.uf}</p>`;
  for (const [grupo, items] of Object.entries(groups)) {
    if (items.length === 0) continue;
    html += `<div class="matricula-group"><h6>${grupo}</h6>`;
    items.forEach(item => {
      html += `
        <div class="matricula-item">
          <label>${item.nome}</label>
          <input type="number" class="form-control form-control-sm" 
                 data-etapa="${item.etapa}" value="${Math.round(item.valor)}" min="0" step="1">
        </div>`;
    });
    html += '</div>';
  }
  container.innerHTML = html;
}

function getMatriculasAjustadas() {
  const result = {};
  $$('#matriculas-container input[data-etapa]').forEach(inp => {
    result[inp.dataset.etapa] = parseFloat(inp.value) || 0;
  });
  return result;
}

// =========================================================================
// Slider de NF — atualização de label
// =========================================================================
function initSliders() {
  const inpNf = $('#inp-nf');
  if (!inpNf) return;
  inpNf.addEventListener('input', () => {
    $('#lbl-nf').textContent = parseFloat(inpNf.value).toFixed(2);
  });
}

// =========================================================================
// SIMULAÇÃO PRINCIPAL
// =========================================================================
async function executarSimulacao() {
  const loading = $('#loading-simulacao');
  loading.classList.remove('d-none');

  const pesos = getPesos();
  const body = {
    complementacao_vaaf: parseFloat($('#inp-comp-vaaf').value) || 0,
    complementacao_vaat: parseFloat($('#inp-comp-vaat').value) || 0,
    complementacao_vaar: parseFloat($('#inp-comp-vaar').value) || 0,
    max_nf: parseFloat($('#inp-nf').value) || 1,
    min_nf: 1,
    pesos_vaaf: pesos.vaaf,
    pesos_vaat: pesos.vaat,
  };

  try {
    const data = await apiFetch('/api/simular', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    state.ultimaSimulacao = data;
    renderResultados(data);
  } catch (e) {
    alert('Erro na simulação: ' + e.message);
  } finally {
    loading.classList.add('d-none');
  }
}

function renderResultados(data) {
  const r = data.resumo;

  // InfoBoxes
  $('#ib-vaat-sim').textContent = fmt.numero(r.vaat_minimo_simulado);
  $('#ib-vaat-atual').textContent = fmt.numero(r.vaat_minimo_atual);
  $('#ib-vaat-dif').textContent = fmt.pct(r.vaat_diferenca_pct);
  $('#ib-vaaf-sim').textContent = fmt.numero(r.vaaf_minimo_simulado);
  $('#ib-vaaf-atual').textContent = fmt.numero(r.vaaf_minimo_atual);
  $('#ib-vaaf-dif').textContent = fmt.pct(r.vaaf_diferenca_pct);
  $('#ib-compl-mun').textContent = fmt.moeda(r.complementacao_municipios);
  $('#ib-compl-est').textContent = fmt.moeda(r.complementacao_estados);
  $('#ib-perc-compl').textContent = fmt.pct(r.percentual_complementados);

  // Gráficos
  renderChartVAAFUF(data);
  renderChartVAATUF(data);
  renderChartDiffUF(data);
  renderChartComplModalidade(data);
  renderChartComplDestino(data);

  // Tabelas
  renderTabelaVP(data.vencedores_perdedores);
  renderTabelaResumo(data.resumo);

  // Validacao interna (RF-10)
  renderValidacao(data.validacao);

  // Graficos 3D
  render3D_CuboUFs(data);
  render3D_BarrasComplementacao(data);
  render3D_SuperficieDiferenca(data);

  renderRegional();
}

function renderValidacao(validacao) {
  const card = $('#validacao-card');
  if (!card) return;
  if (!validacao) {
    card.classList.add('d-none');
    return;
  }
  card.classList.remove('d-none');
  const status = $('#validacao-status');
  const errosEl = $('#validacao-erros');
  const avisosEl = $('#validacao-avisos');
  const checagensEl = $('#validacao-checagens');
  const header = card.querySelector('.validacao-header');
  const icon = card.querySelector('.validacao-icon');
  header.classList.remove('validacao-ok', 'validacao-falha');
  if (validacao.valido) {
    header.classList.add('validacao-ok');
    status.textContent = 'OK';
    status.title = 'Todas as checagens passaram.';
    if (icon) {
      icon.className = 'fas fa-check-circle validacao-icon';
    }
  } else {
    header.classList.add('validacao-falha');
    status.textContent = 'Falhou';
    status.title = 'Inconsistências encontradas';
    if (icon) {
      icon.className = 'fas fa-exclamation-circle validacao-icon';
    }
  }
  function listar(id, itens, icone, classe) {
    const el = $(id);
    if (!el) return;
    if (!itens || itens.length === 0) {
      el.innerHTML = '';
      el.classList.add('d-none');
      return;
    }
    el.classList.remove('d-none');
    el.innerHTML = itens.map(item => `<div class="validacao-item ${classe}"><i class="fas ${icone}"></i> ${escapeHtml(item)}</div>`).join('');
  }
  listar('#validacao-erros', validacao.erros || [], 'fa-times-circle', 'erro');
  listar('#validacao-avisos', validacao.avisos || [], 'fa-exclamation-triangle', 'aviso');
  listar('#validacao-checagens', validacao.checagens || [], 'fa-check', 'checagem');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ---- Gráficos ----
function renderChartVAAFUF(data) {
  const ufs = data.por_uf.map(d => d.uf).sort();
  const simData = ufs.map(uf => data.por_uf.find(d => d.uf === uf)?.vaaf_medio || 0);

  Plotly.newPlot('chart-vaaf-uf', [
    { x: ufs, y: simData, type: 'bar', name: 'Simulação', marker: { color: '#3b82f6' } },
  ], {
    title: '<b>VAAF Médio por UF — Simulação</b>',
    xaxis: { title: '' },
    yaxis: { title: 'Valor Aluno/Ano (R$)', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });
}

function renderChartVAATUF(data) {
  const ufs = data.por_uf.map(d => d.uf).sort();
  const simData = ufs.map(uf => data.por_uf.find(d => d.uf === uf)?.vaat_medio || 0);

  Plotly.newPlot('chart-vaat-uf', [
    { x: ufs, y: simData, type: 'bar', name: 'Simulação', marker: { color: '#8b5cf6' } },
  ], {
    title: '<b>VAAT Médio por UF — Simulação</b>',
    xaxis: { title: '' },
    yaxis: { title: 'Valor Aluno/Ano (R$)', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });
}

function renderChartDiffUF(data) {
  const sorted = [...data.diferenca_uf].sort((a, b) => b.diferenca - a.diferenca);
  Plotly.newPlot('chart-diff-uf', [{
    x: sorted.map(d => d.uf),
    y: sorted.map(d => (d.diferenca || 0) / 1e6),
    type: 'bar',
    marker: { color: sorted.map(d => d.diferenca >= 0 ? '#22c55e' : '#ef4444') },
    hovertemplate: 'UF: %{x}<br>Diferença: %{y:,.0f} milhões<extra></extra>',
  }], {
    title: '<b>Diferença da Complementação da União por UF</b> (Simulação vs. Cenário Atual)',
    yaxis: { title: 'Milhões (R$)', separatethousands: true },
    xaxis: { title: '' },
    margin: { t: 50, b: 40 },
  }, { responsive: true });
}

function renderChartComplModalidade(data) {
  const ufs = [...new Set(data.complementacao_por_uf.map(d => d.uf))];
  const sorted = ufs.sort((a, b) => {
    const sa = data.complementacao_por_uf.find(d => d.uf === a) || {};
    const sb = data.complementacao_por_uf.find(d => d.uf === b) || {};
    return ((sb.complemento_vaaf || 0) + (sb.complemento_vaat || 0)) - ((sa.complemento_vaaf || 0) + (sa.complemento_vaat || 0));
  });

  const vaafVals = sorted.map(uf => (data.complementacao_por_uf.find(d => d.uf === uf)?.complemento_vaaf || 0) / 1e6);
  const vaatVals = sorted.map(uf => (data.complementacao_por_uf.find(d => d.uf === uf)?.complemento_vaat || 0) / 1e6);

  Plotly.newPlot('chart-compl-modalidade', [
    { x: sorted, y: vaafVals, type: 'bar', name: 'VAAF', marker: { color: '#3b82f6' } },
    { x: sorted, y: vaatVals, type: 'bar', name: 'VAAT', marker: { color: '#8b5cf6' } },
  ], {
    barmode: 'stack',
    title: '<b>Complementação da União por UF e Modalidade</b>',
    yaxis: { title: 'Milhões (R$)', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });
}

function renderChartComplDestino(data) {
  const ufs = [...new Set(data.complementacao_destino.map(d => d.uf))];
  const sorted = ufs.sort((a, b) => {
    const sa = data.complementacao_destino.filter(d => d.uf === a).reduce((s, d) => s + (d.complemento || 0), 0);
    const sb = data.complementacao_destino.filter(d => d.uf === b).reduce((s, d) => s + (d.complemento || 0), 0);
    return sb - sa;
  });

  const munVals = sorted.map(uf => (data.complementacao_destino.find(d => d.uf === uf && d.tipo === 'Município')?.complemento || 0) / 1e6);
  const estVals = sorted.map(uf => (data.complementacao_destino.find(d => d.uf === uf && d.tipo === 'Estado')?.complemento || 0) / 1e6);

  Plotly.newPlot('chart-compl-destino', [
    { x: sorted, y: munVals, type: 'bar', name: 'Municípios', marker: { color: '#06b6d4' } },
    { x: sorted, y: estVals, type: 'bar', name: 'Estados', marker: { color: '#f59e0b' } },
  ], {
    barmode: 'stack',
    title: '<b>Complementação da União por UF e Categoria Administrativa</b>',
    yaxis: { title: 'Milhões (R$)', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });
}

// ---- Tabelas ----
function renderTabelaVP(vp) {
  const headers = ['Resultado', 'Região', 'Entes', 'Média (%)', 'Máximo (%)', 'Mínimo (%)'];

  const rowsVaaf = (vp.vaaf || []).map(r => [
    r.resultado_vaaf, r.regiao, r.entes, fmt.pct(r.media), fmt.pct(r.maximo), fmt.pct(r.minimo),
  ]);
  $('#tbl-vp-vaaf').innerHTML = buildTable(headers, rowsVaaf);

  const rowsVaat = (vp.vaat || []).map(r => [
    r.resultado_vaat, r.regiao, r.entes, fmt.pct(r.media), fmt.pct(r.maximo), fmt.pct(r.minimo),
  ]);
  $('#tbl-vp-vaat').innerHTML = buildTable(headers, rowsVaat);
}

function renderTabelaResumo(r) {
  const rows = [
    ['Maior aumento (percentual)', fmt.pct(r.maior_aumento_pct)],
    ['Maior redução (percentual)', fmt.pct(r.maior_reducao_pct)],
    ['Média de mudança (percentual)', fmt.pct(r.media_mudanca_pct)],
    ['Mediana de mudança (percentual)', fmt.pct(r.mediana_mudanca_pct)],
    ['Maior aumento (absoluto)', fmt.moeda(r.maior_aumento_abs)],
    ['Maior redução (absoluto)', fmt.moeda(r.maior_reducao_abs)],
    ['Mudança no VAAF mínimo', fmt.pct(r.vaaf_diferenca_pct)],
    ['Mudança no VAAT mínimo', fmt.pct(r.vaat_diferenca_pct)],
    ['Total complementação VAAF', fmt.moeda(r.total_complementacao_vaaf)],
    ['Total complementação VAAT', fmt.moeda(r.total_complementacao_vaat)],
    ['Total complementação VAAR', fmt.moeda(r.total_complementacao_vaar)],
  ];
  $('#tbl-resumo').innerHTML = buildTable(['Variável', 'Valor'], rows);
}

// =========================================================================
// SIMULAÇÃO VAAR
// =========================================================================
async function executarSimulacaoVAAR() {
  const loading = $('#loading-vaar');
  loading.classList.remove('d-none');

  const pesos = getPesos();
  const body = {
    complementacao_vaaf: parseFloat($('#inp-vaar-vaaf').value) || 0,
    complementacao_vaat: parseFloat($('#inp-vaar-vaat').value) || 0,
    complementacao_vaar: parseFloat($('#inp-vaar-montante').value) || 0,
    max_nf: parseFloat($('#inp-nf').value) || 1,
    min_nf: 1,
    pesos_vaaf: pesos.vaaf,
    pesos_vaat: pesos.vaat,
  };

  try {
    const data = await apiFetch('/api/simular/completo', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    renderResultadosVAAR(data, body.complementacao_vaar);
  } catch (e) {
    alert('Erro na simulação VAAR: ' + e.message);
  } finally {
    loading.classList.add('d-none');
  }
}

function renderResultadosVAAR(data, totalVaar) {
  // Info boxes
  const vaarMun = data.filter(d => d.ibge > 100).reduce((s, d) => s + (d.complemento_vaar || 0), 0);
  const vaarEst = data.filter(d => d.ibge < 100).reduce((s, d) => s + (d.complemento_vaar || 0), 0);

  $('#ib-vaar-total').textContent = fmt.moeda(totalVaar);
  $('#ib-vaar-mun').textContent = fmt.moeda(vaarMun);
  $('#ib-vaar-est').textContent = fmt.moeda(vaarEst);

  // Gráfico VAAR por UF
  const porUf = {};
  data.forEach(d => {
    if (!porUf[d.uf]) porUf[d.uf] = { vaar: 0, vaaf: 0, vaat: 0, total: 0 };
    porUf[d.uf].vaar += d.complemento_vaar || 0;
    porUf[d.uf].vaaf += d.complemento_vaaf || 0;
    porUf[d.uf].vaat += d.complemento_vaat || 0;
    porUf[d.uf].total += d.complemento_uniao || 0;
  });

  const ufs = Object.keys(porUf).sort((a, b) => porUf[b].vaar - porUf[a].vaar);

  Plotly.newPlot('chart-vaar-uf', [
    { x: ufs, y: ufs.map(uf => porUf[uf].vaar / 1e6), type: 'bar', name: 'VAAR', marker: { color: '#f59e0b' } },
    { x: ufs, y: ufs.map(uf => porUf[uf].vaaf / 1e6), type: 'bar', name: 'VAAF', marker: { color: '#3b82f6' } },
    { x: ufs, y: ufs.map(uf => porUf[uf].vaat / 1e6), type: 'bar', name: 'VAAT', marker: { color: '#8b5cf6' } },
  ], {
    barmode: 'stack',
    title: '<b>Complementação da União por UF — VAAF + VAAT + VAAR</b>',
    yaxis: { title: 'Milhões (R$)', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });

  // Gráfico de impacto VAAR — proporção do total
  const ufsImpacto = Object.keys(porUf).sort((a, b) => {
    const pctA = porUf[a].total > 0 ? porUf[a].vaar / porUf[a].total : 0;
    const pctB = porUf[b].total > 0 ? porUf[b].vaar / porUf[b].total : 0;
    return pctB - pctA;
  });

  Plotly.newPlot('chart-vaar-impacto', [{
    x: ufsImpacto,
    y: ufsImpacto.map(uf => porUf[uf].total > 0 ? (porUf[uf].vaar / porUf[uf].total * 100) : 0),
    type: 'bar',
    marker: { color: '#f59e0b' },
    hovertemplate: '%{x}: %{y:.1f}%<extra></extra>',
  }], {
    title: '<b>Proporção da VAAR no Total da Complementação por UF</b>',
    yaxis: { title: '%', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });

  // Tabela VAAR — top 50 entes
  const sorted = [...data].sort((a, b) => (b.complemento_vaar || 0) - (a.complemento_vaar || 0));
  const top = sorted.slice(0, 50);
  const headers = ['Posição', 'UF', 'Município', 'VAAR (R$)', 'VAAF (R$)', 'VAAT (R$)', 'Total Comp. (R$)', 'Recursos FUNDEB (R$)'];
  const rows = top.map((d, i) => [
    i + 1, d.uf, d.nome,
    fmt.moeda(d.complemento_vaar), fmt.moeda(d.complemento_vaaf),
    fmt.moeda(d.complemento_vaat), fmt.moeda(d.complemento_uniao),
    fmt.moeda(d.recursos_fundeb),
  ]);
  $('#tbl-vaar').innerHTML = buildTable(headers, rows);

  // Graficos 3D VAAR
  render3D_VAAR_Distribuicao(data);
  render3D_VAAR_TopEntes(data);
}

// =========================================================================
// SIMULAÇÃO MUNICIPAL
// =========================================================================
async function executarSimulacaoMunicipal() {
  const ibge = parseInt($('#sel-mun-cidade').value);
  if (!ibge) { alert('Selecione um município'); return; }

  const loading = $('#loading-municipio');
  loading.classList.remove('d-none');

  const pesos = getPesos();
  const body = {
    ibge,
    complementacao_vaaf: parseFloat($('#inp-mun-vaaf').value) || 0,
    complementacao_vaat: parseFloat($('#inp-mun-vaat').value) || 0,
    complementacao_vaar: parseFloat($('#inp-mun-vaar').value) || 0,
    max_nf: parseFloat($('#inp-nf').value) || 1,
    min_nf: 1,
    pesos_vaaf: pesos.vaaf,
    pesos_vaat: pesos.vaat,
    matriculas_ajustadas: getMatriculasAjustadas(),
  };

  try {
    const data = await apiFetch('/api/simular/municipio', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    renderResultadosMunicipio(data, {});
  } catch (e) {
    alert('Erro na simulação municipal: ' + e.message);
  } finally {
    loading.classList.add('d-none');
  }
}

function munId(base, ano) {
  return ano ? `${base}-${ano}` : base;
}

function renderResultadosMunicipio(data, opts) {
  opts = opts || {};
  const ano = opts.ano || null;
  const orig = data.municipio_original;
  const ajust = data.municipio_ajustado;

  const show = (id) => {
    const el = document.getElementById(munId(id, ano));
    if (el) el.style.display = '';
  };
  show('mun-comparacao');
  show('mun-chart-card');
  show('mun-impacto-card');
  show('mun-explicacao-card');
  show('mun-3d-section');

  renderExplicacao(orig, ajust, {
    containerId: munId('mun-explicacao', ano),
    explicacaoCardId: munId('mun-explicacao-card', ano),
    munData: opts.munData,
    etapasNomes: opts.etapasNomes,
    getAjustadas: opts.getAjustadas,
    ponderadorLabel: opts.ponderadorLabel || 'NF',
  });

  // Card original
  const fmtCoef = (v) => (v == null || isNaN(v)) ? '-' : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 8, maximumFractionDigits: 8 });
  const renderCard = (container, d) => {
    const ufFundo = d.fundo_estadual?.uf || d.uf;
    const items = [
      ['Matrículas VAAF', fmt.numero(d.matriculas_brutas)],
      ['Matrículas ponderadas VAAF', fmt.numero(d.matriculas_vaaf)],
      ['Matrículas ponderadas VAAT', fmt.numero(d.matriculas_vaat)],
      ['Matrículas ponderadas VAAF do Fundo', fmt.numero(d.fundo_estadual?.matriculas_pond_vaaf)],
      [`Receitas VAAF Fundo ${ufFundo}`, fmt.moeda(d.fundo_estadual?.receitas_vaaf)],
      [`Complemento VAAF Fundo ${ufFundo}`, fmt.moeda(d.fundo_estadual?.complemento_vaaf_fundo)],
      ['Receita da contribuição de estados e municípios ao Fundeb', fmt.moeda(d.recursos_vaaf)],
      ['Receitas VAAT', fmt.moeda(d.recursos_vaat)],
      ['VAAF-MIN', fmt.numero(d.vaaf_minimo)],
      ['VAAT-MIN', fmt.numero(d.vaat_minimo)],
      ['VAAF (antes da complementação)', fmt.numero(d.vaaf)],
      ['VAAT (antes da complementação)', fmt.numero(d.vaat)],
      ['Coeficiente (matrículas ente / fundo)', fmtCoef(d.coeficiente)],
      ['VAAF Final', fmt.numero(d.vaaf_final)],
      ['VAAT Final', fmt.numero(d.vaat_final)],
      ['Complemento VAAF', fmt.moeda(d.complemento_vaaf)],
      ['Complemento VAAT', fmt.moeda(d.complemento_vaat)],
      ['Complemento VAAR', fmt.moeda(d.complemento_vaar)],
      ['Total Complementação', fmt.moeda(d.complemento_uniao)],
      ['Receita Total do Fundeb', fmt.moeda(d.recursos_fundeb)],
    ];
    $(container).innerHTML = items.map(([label, value]) =>
      `<div class="comparison-row"><span class="comparison-label">${label}</span><span class="comparison-value">${value}</span></div>`
    ).join('');
  };

  renderCard(`#${munId('mun-original', ano)}`, orig);
  renderCard(`#${munId('mun-ajustado', ano)}`, ajust);

  const labels = ['VAAF Final', 'VAAT Final', 'Comp. VAAF', 'Comp. VAAT', 'Comp. VAAR', 'Recursos FUNDEB'];
  const origVals = [orig.vaaf_final, orig.vaat_final, orig.complemento_vaaf, orig.complemento_vaat, orig.complemento_vaar, orig.recursos_fundeb];
  const ajustVals = [ajust.vaaf_final, ajust.vaat_final, ajust.complemento_vaaf, ajust.complemento_vaat, ajust.complemento_vaar, ajust.recursos_fundeb];

  Plotly.newPlot(munId('chart-mun-comparacao', ano), [
    { x: labels, y: origVals, type: 'bar', name: 'Original', marker: { color: '#94a3b8' } },
    { x: labels, y: ajustVals, type: 'bar', name: 'Ajustado', marker: { color: '#3b82f6' } },
  ], {
    barmode: 'group',
    title: `<b>Comparação — ${orig.nome} (${orig.uf})${ano ? ' — FUNDEB ' + ano : ''}</b>`,
    yaxis: { title: 'R$', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });

  // Tabela impacto no estado
  if (data.estado_original && data.estado_ajustado) {
    const headers = ['Município', 'VAAF Original', 'VAAF Ajustado', 'Dif VAAF', 'VAAT Original', 'VAAT Ajustado', 'Dif VAAT'];
    const rows = [];
    const origMap = {};
    data.estado_original.forEach(d => origMap[d.ibge] = d);

    data.estado_ajustado.forEach(d => {
      const o = origMap[d.ibge];
      if (!o) return;
      const difVaaf = d.vaaf_final - o.vaaf_final;
      const difVaat = d.vaat_final - o.vaat_final;
      if (Math.abs(difVaaf) > 0.01 || Math.abs(difVaat) > 0.01 || d.ibge === orig.ibge) {
        rows.push([
          d.ibge === orig.ibge ? `<strong>${d.nome}</strong>` : d.nome,
          fmt.numero(o.vaaf_final), fmt.numero(d.vaaf_final),
          `<span class="${difVaaf >= 0 ? 'comparison-value positive' : 'comparison-value negative'}">${fmt.numero(difVaaf)}</span>`,
          fmt.numero(o.vaat_final), fmt.numero(d.vaat_final),
          `<span class="${difVaat >= 0 ? 'comparison-value positive' : 'comparison-value negative'}">${fmt.numero(difVaat)}</span>`,
        ]);
      }
    });
    rows.sort((a, b) => {
      if (a[0].includes('<strong>')) return -1;
      if (b[0].includes('<strong>')) return 1;
      return 0;
    });
    const tbl = document.getElementById(munId('tbl-mun-impacto', ano));
    if (tbl) tbl.innerHTML = buildTable(headers, rows.slice(0, 50));
  }

  render3D_Municipal(orig, ajust, munId('chart3d-mun-comparacao', ano));
  if (data.estado_original && data.estado_ajustado) {
    render3D_MunicipalEstado(
      data.estado_original, data.estado_ajustado, orig.ibge,
      munId('chart3d-mun-estado', ano),
    );
  }
}

window.renderResultadosMunicipio = renderResultadosMunicipio;

// =========================================================================
// ANÁLISE REGIONAL
// =========================================================================
async function garantirDadosRegional() {
  if (state.ultimaSimulacao) return state.ultimaSimulacao;
  const pesos = getPesos();
  const body = {
    complementacao_vaaf: parseFloat($('#inp-comp-vaaf')?.value) || 0,
    complementacao_vaat: parseFloat($('#inp-comp-vaat')?.value) || 0,
    complementacao_vaar: parseFloat($('#inp-comp-vaar')?.value) || 0,
    max_nf: parseFloat($('#inp-nf')?.value) || 1,
    min_nf: 1,
    pesos_vaaf: pesos.vaaf,
    pesos_vaat: pesos.vaat,
  };
  const data = await apiFetch('/api/simular', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  state.ultimaSimulacao = data;
  return data;
}

function initRegional() {
  const sel = $('#sel-regional-uf');
  if (sel) sel.addEventListener('change', () => renderRegional());
}

async function renderRegional() {
  const uf = $('#sel-regional-uf')?.value;
  const container = $('#resultados-regional');
  if (!container) return;

  if (!uf) {
    container.innerHTML = '<p class="text-muted">Selecione uma UF para visualizar a análise regional.</p>';
    return;
  }

  if (!state.ultimaSimulacao) {
    container.innerHTML = '<p class="text-muted"><span class="spinner-border spinner-border-sm me-2"></span>Carregando dados regionais...</p>';
    try {
      await garantirDadosRegional();
    } catch (e) {
      container.innerHTML = `<p class="text-danger">Erro ao carregar dados regionais: ${e.message}</p>`;
      return;
    }
  }

  const data = state.ultimaSimulacao;
  const ufData = data.por_uf.find(d => d.uf === uf);
  if (!ufData) {
    container.innerHTML = '<p class="text-muted">Dados não encontrados para esta UF.</p>';
    return;
  }

  container.innerHTML = `
    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="info-box info-box-green">
          <div class="info-box-icon"><i class="fas fa-chart-bar"></i></div>
          <div class="info-box-content">
            <span class="info-box-label">VAAF Médio — ${uf}</span>
            <span class="info-box-value">${fmt.numero(ufData.vaaf_medio)}</span>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="info-box info-box-purple">
          <div class="info-box-icon"><i class="fas fa-chart-line"></i></div>
          <div class="info-box-content">
            <span class="info-box-label">VAAT Médio — ${uf}</span>
            <span class="info-box-value">${fmt.numero(ufData.vaat_medio)}</span>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="info-box info-box-blue">
          <div class="info-box-icon"><i class="fas fa-hand-holding-usd"></i></div>
          <div class="info-box-content">
            <span class="info-box-label">Complementação Total — ${uf}</span>
            <span class="info-box-value">${fmt.moeda(ufData.complemento_uniao)}</span>
          </div>
        </div>
      </div>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="info-box info-box-orange">
          <div class="info-box-icon"><i class="fas fa-award"></i></div>
          <div class="info-box-content">
            <span class="info-box-label">Complementação VAAF — ${uf}</span>
            <span class="info-box-value">${fmt.moeda(ufData.complemento_vaaf)}</span>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="info-box info-box-cyan">
          <div class="info-box-icon"><i class="fas fa-award"></i></div>
          <div class="info-box-content">
            <span class="info-box-label">Complementação VAAT — ${uf}</span>
            <span class="info-box-value">${fmt.moeda(ufData.complemento_vaat)}</span>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="info-box info-box-orange">
          <div class="info-box-icon"><i class="fas fa-award"></i></div>
          <div class="info-box-content">
            <span class="info-box-label">Complementação VAAR — ${uf}</span>
            <span class="info-box-value">${fmt.moeda(ufData.complemento_vaar)}</span>
          </div>
        </div>
      </div>
    </div>
    <div class="card mb-4">
      <div class="card-header">Recursos FUNDEB na UF: ${uf}</div>
      <div class="card-body">
        <p>Total de recursos FUNDEB: <strong>${fmt.moeda(ufData.recursos_fundeb)}</strong></p>
      </div>
    </div>
  `;
}

// =========================================================================
// Inicialização
// =========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  initNavigation();
  initSliders();

  try {
    await guardAuth();
    await initData();
    // Pré-carrega simulação padrão para análise regional (cenário oficial / parâmetros iniciais)
    await garantirDadosRegional().catch((e) => {
      console.warn('Pré-carga regional:', e);
    });
  } catch (err) {
    console.error('Falha ao carregar dados iniciais (2024):', err);
  }

  $('#btn-simular')?.addEventListener('click', executarSimulacao);
  $('#btn-simular-vaar')?.addEventListener('click', executarSimulacaoVAAR);
  $('#btn-simular-mun')?.addEventListener('click', executarSimulacaoMunicipal);
  initRegional();
});
