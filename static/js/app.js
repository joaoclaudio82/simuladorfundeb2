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

async function apiFetch(url, opts = {}) {
  const res = await fetch(API + url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

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

function initNavigation() {
  const sidebar = $('#sidebar');
  const toggleBtn = $('#sidebar-toggle');
  const backdrop = $('#sidebar-backdrop');

  $$('.sidebar-nav li').forEach(li => {
    li.addEventListener('click', () => {
      $$('.sidebar-nav li').forEach(l => l.classList.remove('active'));
      li.classList.add('active');
      $$('.tab-content').forEach(t => t.classList.remove('active'));
      $(`#tab-${li.dataset.tab}`).classList.add('active');
      if (isMobile()) closeSidebarMobile();
    });
  });

  toggleBtn.addEventListener('click', () => {
    if (isMobile()) {
      const isOpen = sidebar.classList.contains('open');
      if (isOpen) closeSidebarMobile();
      else openSidebarMobile();
    } else {
      sidebar.classList.toggle('collapsed');
      $('#main-content').classList.toggle('expanded');
    }
  });

  if (backdrop) {
    backdrop.addEventListener('click', () => {
      if (isMobile()) closeSidebarMobile();
    });
  }

  window.addEventListener('resize', () => {
    if (!isMobile()) {
      closeSidebarMobile();
      sidebar.classList.remove('collapsed');
      $('#main-content').classList.remove('expanded');
    }
  });

  // Links/botoes com data-tab (ex: "Ir para Simulacao" na pagina principal)
  document.addEventListener('click', (e) => {
    const target = e.target.closest('[data-tab]');
    if (target && !target.closest('.sidebar-nav')) {
      e.preventDefault();
      const tab = target.dataset.tab;
      $$('.sidebar-nav li').forEach(l => {
        l.classList.toggle('active', l.dataset.tab === tab);
      });
      $$('.tab-content').forEach(t => t.classList.remove('active'));
      const el = $(`#tab-${tab}`);
      if (el) el.classList.add('active');
      if (isMobile()) closeSidebarMobile();
    }
  });
}

// =========================================================================
// Carregar dados iniciais
// =========================================================================
async function initData() {
  const [pesosRes, estadosRes, etapasRes] = await Promise.all([
    apiFetch('/api/pesos'),
    apiFetch('/api/estados'),
    apiFetch('/api/etapas'),
  ]);
  state.pesos = pesosRes;
  state.estados = estadosRes.estados;
  state.regioes = estadosRes.regioes;
  state.etapas = etapasRes;

  renderPesos();
  populateEstadoSelectors();
}

// =========================================================================
// Pesos — renderizar sliders
// =========================================================================
function renderPesos() {
  const vaafContainer = $('#pesos-vaaf-container');
  const vaatContainer = $('#pesos-vaat-container');
  vaafContainer.innerHTML = '';
  vaatContainer.innerHTML = '';

  state.pesos.forEach((p, i) => {
    const makeSlider = (tipo, valor) => {
      const id = `peso-${tipo}-${i}`;
      return `
        <div class="mb-2">
          <label class="form-label small">${i + 1}. ${p.nome}:
            <strong id="lbl-${id}">${Number(valor).toFixed(2)}</strong>
          </label>
          <input type="range" class="form-range" id="${id}" min="0.8" max="3.5" step="0.05" value="${valor}">
        </div>`;
    };
    vaafContainer.innerHTML += makeSlider('vaaf', p.peso_vaaf);
    vaatContainer.innerHTML += makeSlider('vaat', p.peso_vaat);
  });

  // Atualizar labels
  $$('[id^="peso-"]').forEach(inp => {
    if (inp.tagName === 'INPUT') {
      inp.addEventListener('input', () => {
        $(`#lbl-${inp.id}`).textContent = Number(inp.value).toFixed(2);
      });
    }
  });
}

function getPesos() {
  const vaaf = [], vaat = [];
  state.pesos.forEach((_, i) => {
    vaaf.push(parseFloat($(`#peso-vaaf-${i}`)?.value ?? state.pesos[i].peso_vaaf));
    vaat.push(parseFloat($(`#peso-vaat-${i}`)?.value ?? state.pesos[i].peso_vaat));
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
// Sliders de NSE/NF — atualização de labels
// =========================================================================
function initSliders() {
  $('#inp-nse').addEventListener('input', () => {
    $('#lbl-nse').textContent = parseFloat($('#inp-nse').value).toFixed(2);
  });
  $('#inp-nf').addEventListener('input', () => {
    $('#lbl-nf').textContent = parseFloat($('#inp-nf').value).toFixed(2);
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
    max_nse: parseFloat($('#inp-nse').value) || 1,
    min_nse: 1,
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
    max_nse: parseFloat($('#inp-nse').value) || 1.1,
    min_nse: 1,
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
    max_nse: parseFloat($('#inp-nse').value) || 1.1,
    min_nse: 1,
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
    renderResultadosMunicipio(data);
  } catch (e) {
    alert('Erro na simulação municipal: ' + e.message);
  } finally {
    loading.classList.add('d-none');
  }
}

function renderResultadosMunicipio(data) {
  const orig = data.municipio_original;
  const ajust = data.municipio_ajustado;

  // Mostrar cards
  $('#mun-comparacao').style.display = '';
  $('#mun-chart-card').style.display = '';
  $('#mun-impacto-card').style.display = '';
  $('#mun-explicacao-card').style.display = '';
  $('#mun-3d-section').style.display = '';

  // Gerar explicação
  renderExplicacao(orig, ajust);

  // Card original
  const renderCard = (container, d) => {
    const items = [
      ['Matrículas VAAF', fmt.numero(d.matriculas_vaaf)],
      ['Matrículas VAAT', fmt.numero(d.matriculas_vaat)],
      ['Recursos VAAF', fmt.moeda(d.recursos_vaaf)],
      ['Recursos VAAT', fmt.moeda(d.recursos_vaat)],
      ['VAAF Final', fmt.numero(d.vaaf_final)],
      ['VAAT Final', fmt.numero(d.vaat_final)],
      ['Complemento VAAF', fmt.moeda(d.complemento_vaaf)],
      ['Complemento VAAT', fmt.moeda(d.complemento_vaat)],
      ['Complemento VAAR', fmt.moeda(d.complemento_vaar)],
      ['Total Complementação', fmt.moeda(d.complemento_uniao)],
      ['Recursos FUNDEB', fmt.moeda(d.recursos_fundeb)],
    ];
    $(container).innerHTML = items.map(([label, value]) =>
      `<div class="comparison-row"><span class="comparison-label">${label}</span><span class="comparison-value">${value}</span></div>`
    ).join('');
  };

  renderCard('#mun-original', orig);
  renderCard('#mun-ajustado', ajust);

  // Gráfico de comparação
  const labels = ['VAAF Final', 'VAAT Final', 'Comp. VAAF', 'Comp. VAAT', 'Comp. VAAR', 'Recursos FUNDEB'];
  const origVals = [orig.vaaf_final, orig.vaat_final, orig.complemento_vaaf, orig.complemento_vaat, orig.complemento_vaar, orig.recursos_fundeb];
  const ajustVals = [ajust.vaaf_final, ajust.vaat_final, ajust.complemento_vaaf, ajust.complemento_vaat, ajust.complemento_vaar, ajust.recursos_fundeb];

  Plotly.newPlot('chart-mun-comparacao', [
    { x: labels, y: origVals, type: 'bar', name: 'Original', marker: { color: '#94a3b8' } },
    { x: labels, y: ajustVals, type: 'bar', name: 'Ajustado', marker: { color: '#3b82f6' } },
  ], {
    barmode: 'group',
    title: `<b>Comparação — ${orig.nome} (${orig.uf})</b>`,
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
    $('#tbl-mun-impacto').innerHTML = buildTable(headers, rows.slice(0, 50));
  }

  // Graficos 3D Municipal
  render3D_Municipal(orig, ajust);
  if (data.estado_original && data.estado_ajustado) {
    render3D_MunicipalEstado(data.estado_original, data.estado_ajustado, orig.ibge);
  }
}

// =========================================================================
// ANÁLISE REGIONAL
// =========================================================================
function initRegional() {
  $('#sel-regional-uf').addEventListener('change', renderRegional);
}

function renderRegional() {
  const uf = $('#sel-regional-uf').value;
  const container = $('#resultados-regional');
  if (!uf || !state.ultimaSimulacao) {
    container.innerHTML = '<p class="text-muted">Execute uma simulação na aba principal e selecione uma UF.</p>';
    return;
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

  await initData();

  // Eventos
  $('#btn-simular').addEventListener('click', executarSimulacao);
  $('#btn-simular-vaar').addEventListener('click', executarSimulacaoVAAR);
  $('#btn-simular-mun').addEventListener('click', executarSimulacaoMunicipal);
  initRegional();
});
