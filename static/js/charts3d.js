/**
 * Graficos 3D — Simulador FUNDEB v2
 * Paleta vibrante: azul, ciano, verde, vermelho, roxo, amarelo
 */

/* Paleta vibrante para regioes */
var CORES_REGIOES = {
  'Norte':        '#00E5FF',   /* ciano brilhante */
  'Nordeste':     '#FF4081',   /* rosa/vermelho vibrante */
  'Sudeste':      '#536DFE',   /* azul indigo */
  'Sul':          '#00E676',   /* verde neon */
  'Centro-Oeste': '#FFD740'    /* amarelo ouro */
};

/* Cores para VAAF / VAAT / VAAR */
var COR_VAAF = '#2979FF';   /* azul vibrante */
var COR_VAAT = '#00E676';   /* verde vibrante */
var COR_VAAR = '#AA00FF';   /* roxo vibrante */
var COR_TOTAL = '#FF6D00';  /* laranja */
var COR_POSITIVO = '#00E676';
var COR_NEGATIVO = '#FF1744';
var COR_ORIGINAL = '#78909C'; /* cinza azulado */
var COR_AJUSTADO = '#00B0FF'; /* azul claro */
var COR_DIFERENCA = '#FFEA00'; /* amarelo */
var COR_DESTAQUE = '#FF4081'; /* rosa destaque */

var MAPA_REGIOES = {};
(function() {
  var r = {
    'Norte': ['AC','AM','AP','PA','RO','RR','TO'],
    'Nordeste': ['AL','BA','CE','MA','PB','PE','PI','RN','SE'],
    'Sudeste': ['ES','MG','RJ','SP'],
    'Sul': ['PR','RS','SC'],
    'Centro-Oeste': ['DF','GO','MS','MT']
  };
  for (var reg in r) { for (var i = 0; i < r[reg].length; i++) { MAPA_REGIOES[r[reg][i]] = reg; } }
})();

/* Altura padrao grande para os graficos 3D */
var CHART3D_HEIGHT = 720;

/* Layout base: fundo escuro para os cubos coloridos se destacarem */
var LAYOUT_3D_BASE = {
  paper_bgcolor: '#1a1a2e',
  plot_bgcolor: '#1a1a2e',
  font: { family: 'Inter, sans-serif', color: '#e0e0e0', size: 11 },
  margin: { l: 0, r: 0, t: 60, b: 0 },
  scene: {
    bgcolor: '#16213e',
    xaxis: { gridcolor: '#2a3a5c', showbackground: true, backgroundcolor: '#1a1a2e', color: '#90caf9', title: { font: { color: '#90caf9' } } },
    yaxis: { gridcolor: '#2a3a5c', showbackground: true, backgroundcolor: '#1a1a2e', color: '#a5d6a7', title: { font: { color: '#a5d6a7' } } },
    zaxis: { gridcolor: '#2a3a5c', showbackground: true, backgroundcolor: '#1a1a2e', color: '#ce93d8', title: { font: { color: '#ce93d8' } } },
    camera: { eye: { x: 1.6, y: 1.6, z: 1.0 } }
  }
};

function deepCopy(obj) { return JSON.parse(JSON.stringify(obj)); }

/* ---- Fullscreen toggle ---- */
function injectFullscreenButtons() {
  var charts = document.querySelectorAll('[id^="chart3d-"]');
  charts.forEach(function(el) {
    var wrapper = el.parentElement;
    if (!wrapper || wrapper.querySelector('.btn-fullscreen-3d')) return;
    var btn = document.createElement('button');
    btn.className = 'btn-fullscreen-3d';
    btn.title = 'Tela cheia';
    btn.innerHTML = '<i class="fas fa-expand"></i>';
    btn.addEventListener('click', function() { toggleFullscreen3D(el.id); });
    wrapper.style.position = 'relative';
    wrapper.appendChild(btn);
  });
}

function toggleFullscreen3D(chartId) {
  var el = document.getElementById(chartId);
  if (!el) return;
  var card = el.closest('.card');
  if (!card) card = el.parentElement;

  if (card.classList.contains('chart3d-fullscreen')) {
    /* Sair do fullscreen */
    card.classList.remove('chart3d-fullscreen');
    document.body.style.overflow = '';
    var btn = card.querySelector('.btn-fullscreen-3d');
    if (btn) btn.innerHTML = '<i class="fas fa-expand"></i>';
    Plotly.relayout(chartId, { height: CHART3D_HEIGHT });
  } else {
    /* Entrar no fullscreen */
    card.classList.add('chart3d-fullscreen');
    document.body.style.overflow = 'hidden';
    var btn = card.querySelector('.btn-fullscreen-3d');
    if (btn) btn.innerHTML = '<i class="fas fa-compress"></i>';
    Plotly.relayout(chartId, { height: window.innerHeight - 20 });
  }
}

/* ESC para sair do fullscreen */
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var fs = document.querySelector('.chart3d-fullscreen');
    if (fs) {
      var chartEl = fs.querySelector('[id^="chart3d-"]');
      if (chartEl) toggleFullscreen3D(chartEl.id);
    }
  }
});

// =========================================================================
// SIMULACAO PRINCIPAL — 3D
// =========================================================================

function render3D_CuboUFs(data) {
  var porUf = data.por_uf;
  if (!porUf || porUf.length === 0) return;

  var ufs = porUf.map(function(d) { return d.uf; });
  var vaaf = porUf.map(function(d) { return d.vaaf_medio || 0; });
  var vaat = porUf.map(function(d) { return d.vaat_medio || 0; });
  var compl = porUf.map(function(d) { return (d.complemento_uniao || 0) / 1e6; });
  var regioes = ufs.map(function(uf) { return MAPA_REGIOES[uf] || 'Outro'; });
  var cores = regioes.map(function(r) { return CORES_REGIOES[r] || '#FFD740'; });

  var maxCompl = Math.max.apply(null, compl);
  var tamanhos = compl.map(function(c) { return Math.max(10, (c / (maxCompl || 1)) * 40); });

  var trace = {
    type: 'scatter3d',
    mode: 'markers+text',
    x: vaaf, y: vaat, z: compl,
    text: ufs,
    textposition: 'top center',
    textfont: { size: 10, color: '#ffffff', family: 'Inter' },
    marker: {
      size: tamanhos,
      color: cores,
      opacity: 0.92,
      symbol: 'square',
      line: { width: 1.5, color: 'rgba(255,255,255,0.4)' }
    },
    hovertemplate: '<b>%{text}</b><br>VAAF: R$ %{x:,.0f}<br>VAAT: R$ %{y:,.0f}<br>Compl.: R$ %{z:,.0f}M<extra></extra>'
  };

  var layout = deepCopy(LAYOUT_3D_BASE);
  layout.title = { text: '<b>Cubo 3D — VAAF x VAAT x Complementação por UF</b>', font: { size: 15, color: '#e0e0e0' } };
  layout.scene.xaxis.title = { text: 'VAAF médio (R$/aluno)', font: { color: '#90caf9' } };
  layout.scene.yaxis.title = { text: 'VAAT médio (R$/aluno)', font: { color: '#a5d6a7' } };
  layout.scene.zaxis.title = { text: 'Complementação (M R$)', font: { color: '#ce93d8' } };
  layout.height = CHART3D_HEIGHT;

  Plotly.newPlot('chart3d-cubo-ufs', [trace], layout, { responsive: true });
  setTimeout(injectFullscreenButtons, 100);
}

function render3D_BarrasComplementacao(data) {
  if (!data.complementacao_por_uf) return;
  var compl = data.complementacao_por_uf.slice();
  compl.sort(function(a, b) { return (b.complemento_vaaf + b.complemento_vaat) - (a.complemento_vaaf + a.complemento_vaat); });

  var ufs = compl.map(function(d) { return d.uf; });
  var traces = [];

  /* VAAF - azul */
  traces.push({
    type: 'scatter3d', mode: 'markers', name: 'VAAF',
    x: ufs.map(function(_, i) { return i; }),
    y: ufs.map(function() { return 0; }),
    z: compl.map(function(d) { return (d.complemento_vaaf || 0) / 1e6; }),
    marker: { size: 14, color: COR_VAAF, symbol: 'square', opacity: 0.92, line: { width: 1, color: 'rgba(255,255,255,0.3)' } },
    text: ufs.map(function(uf, i) { return uf + ' VAAF: R$ ' + ((compl[i].complemento_vaaf || 0) / 1e6).toFixed(0) + 'M'; }),
    hoverinfo: 'text'
  });

  /* VAAT - verde */
  traces.push({
    type: 'scatter3d', mode: 'markers', name: 'VAAT',
    x: ufs.map(function(_, i) { return i; }),
    y: ufs.map(function() { return 1; }),
    z: compl.map(function(d) { return (d.complemento_vaat || 0) / 1e6; }),
    marker: { size: 14, color: COR_VAAT, symbol: 'square', opacity: 0.92, line: { width: 1, color: 'rgba(255,255,255,0.3)' } },
    text: ufs.map(function(uf, i) { return uf + ' VAAT: R$ ' + ((compl[i].complemento_vaat || 0) / 1e6).toFixed(0) + 'M'; }),
    hoverinfo: 'text'
  });

  /* VAAR - roxo */
  traces.push({
    type: 'scatter3d', mode: 'markers', name: 'VAAR',
    x: ufs.map(function(_, i) { return i; }),
    y: ufs.map(function() { return 2; }),
    z: compl.map(function(d) { return (d.complemento_vaar || 0) / 1e6; }),
    marker: { size: 14, color: COR_VAAR, symbol: 'square', opacity: 0.92, line: { width: 1, color: 'rgba(255,255,255,0.3)' } },
    text: ufs.map(function(uf, i) { return uf + ' VAAR: R$ ' + ((compl[i].complemento_vaar || 0) / 1e6).toFixed(0) + 'M'; }),
    hoverinfo: 'text'
  });

  /* Linhas verticais - ciano translucido */
  for (var i = 0; i < ufs.length; i++) {
    traces.push({
      type: 'scatter3d', mode: 'lines', showlegend: false,
      x: [i, i, i], y: [0, 1, 2],
      z: [(compl[i].complemento_vaaf || 0) / 1e6, (compl[i].complemento_vaat || 0) / 1e6, (compl[i].complemento_vaar || 0) / 1e6],
      line: { color: 'rgba(0,229,255,0.2)', width: 2 },
      hoverinfo: 'skip'
    });
  }

  var layout = deepCopy(LAYOUT_3D_BASE);
  layout.title = { text: '<b>Cubo 3D — VAAF / VAAT / VAAR por UF</b>', font: { size: 15, color: '#e0e0e0' } };
  layout.scene.xaxis.title = { text: 'UF', font: { color: '#90caf9' } };
  layout.scene.xaxis.tickvals = ufs.map(function(_, i) { return i; });
  layout.scene.xaxis.ticktext = ufs;
  layout.scene.yaxis.title = { text: 'Modalidade', font: { color: '#a5d6a7' } };
  layout.scene.yaxis.tickvals = [0, 1, 2];
  layout.scene.yaxis.ticktext = ['VAAF', 'VAAT', 'VAAR'];
  layout.scene.zaxis.title = { text: 'Milhões (R$)', font: { color: '#ce93d8' } };
  layout.scene.camera = { eye: { x: 2.0, y: 1.2, z: 0.8 } };
  layout.height = CHART3D_HEIGHT;
  layout.showlegend = true;
  layout.legend = { x: 0.82, y: 0.95, bgcolor: 'rgba(26,26,46,0.85)', bordercolor: '#2a3a5c', borderwidth: 1, font: { size: 12, color: '#e0e0e0' } };

  Plotly.newPlot('chart3d-barras-compl', traces, layout, { responsive: true });
  setTimeout(injectFullscreenButtons, 100);
}

function render3D_SuperficieDiferenca(data) {
  if (!data.diferenca_uf || !data.por_uf) return;

  var porUf = data.por_uf.slice().sort(function(a, b) { return (a.vaaf_medio || 0) - (b.vaaf_medio || 0); });
  var diffMap = {};
  data.diferenca_uf.forEach(function(d) { diffMap[d.uf] = d.diferenca || 0; });

  var ufs = porUf.map(function(d) { return d.uf; });
  var vaafVals = porUf.map(function(d) { return d.vaaf_medio || 0; });
  var vaatVals = porUf.map(function(d) { return d.vaat_medio || 0; });
  var diffVals = ufs.map(function(uf) { return (diffMap[uf] || 0) / 1e6; });
  var regioes = ufs.map(function(uf) { return MAPA_REGIOES[uf] || ''; });

  var trace = {
    type: 'scatter3d',
    mode: 'markers+text',
    x: vaafVals, y: vaatVals, z: diffVals,
    text: ufs,
    textposition: 'top center',
    textfont: { size: 9, color: '#ffffff' },
    marker: {
      size: diffVals.map(function(d) { return Math.max(8, Math.min(35, Math.abs(d) * 0.9)); }),
      color: diffVals,
      colorscale: [[0, '#FF1744'], [0.5, '#424242'], [1, '#00E676']],
      cmid: 0,
      colorbar: { title: { text: 'Dif (M R$)', font: { color: '#e0e0e0' } }, thickness: 16, len: 0.6, tickfont: { size: 10, color: '#bbb' }, bgcolor: 'rgba(26,26,46,0.8)', bordercolor: '#2a3a5c' },
      symbol: 'square',
      opacity: 0.92,
      line: { width: 1, color: 'rgba(255,255,255,0.3)' }
    },
    customdata: regioes,
    hovertemplate: '<b>%{text}</b> (%{customdata})<br>VAAF: R$ %{x:,.0f}<br>VAAT: R$ %{y:,.0f}<br>Diferença: R$ %{z:,.0f}M<extra></extra>'
  };

  /* Plano zero - azul translucido */
  var xR = [Math.min.apply(null, vaafVals) * 0.95, Math.max.apply(null, vaafVals) * 1.05];
  var yR = [Math.min.apply(null, vaatVals) * 0.95, Math.max.apply(null, vaatVals) * 1.05];
  var planoZero = {
    type: 'mesh3d',
    x: [xR[0], xR[1], xR[1], xR[0]], y: [yR[0], yR[0], yR[1], yR[1]], z: [0,0,0,0],
    i: [0,0], j: [1,2], k: [2,3],
    color: 'rgba(41,121,255,0.08)',
    flatshading: true, showlegend: false, hoverinfo: 'skip'
  };

  var layout = deepCopy(LAYOUT_3D_BASE);
  layout.title = { text: '<b>Cubo 3D — Mapa de Impacto: Ganhos vs Perdas</b>', font: { size: 15, color: '#e0e0e0' } };
  layout.scene.xaxis.title = { text: 'VAAF médio (R$/aluno)', font: { color: '#90caf9' } };
  layout.scene.yaxis.title = { text: 'VAAT médio (R$/aluno)', font: { color: '#a5d6a7' } };
  layout.scene.zaxis.title = { text: 'Diferença (M R$)', font: { color: '#ce93d8' } };
  layout.scene.camera = { eye: { x: 1.8, y: 1.4, z: 1.2 } };
  layout.height = CHART3D_HEIGHT;

  Plotly.newPlot('chart3d-superficie-diff', [planoZero, trace], layout, { responsive: true });
  setTimeout(injectFullscreenButtons, 100);
}

// =========================================================================
// SIMULACAO VAAR — 3D
// =========================================================================

function render3D_VAAR_Distribuicao(dados, plotId) {
  plotId = plotId || 'chart3d-vaar-dist';
  if (!dados || dados.length === 0) return;

  var porUf = {};
  dados.forEach(function(d) {
    if (!porUf[d.uf]) porUf[d.uf] = { vaaf: 0, vaat: 0, vaar: 0, n: 0 };
    porUf[d.uf].vaaf += (d.complemento_vaaf || 0);
    porUf[d.uf].vaat += (d.complemento_vaat || 0);
    porUf[d.uf].vaar += (d.complemento_vaar || 0);
    porUf[d.uf].n++;
  });

  var ufs = Object.keys(porUf).sort(function(a, b) { return porUf[b].vaar - porUf[a].vaar; });

  var trace = {
    type: 'scatter3d',
    mode: 'markers+text',
    x: ufs.map(function(uf) { return porUf[uf].vaaf / 1e6; }),
    y: ufs.map(function(uf) { return porUf[uf].vaat / 1e6; }),
    z: ufs.map(function(uf) { return porUf[uf].vaar / 1e6; }),
    text: ufs,
    textposition: 'top center',
    textfont: { size: 10, color: '#ffffff' },
    marker: {
      size: ufs.map(function(uf) { return Math.max(10, Math.min(35, porUf[uf].n / 4)); }),
      color: ufs.map(function(uf) { return porUf[uf].vaar / 1e6; }),
      colorscale: [[0, '#1a237e'], [0.25, '#00B0FF'], [0.5, '#00E676'], [0.75, '#FFEA00'], [1, '#FF1744']],
      colorbar: { title: { text: 'VAAR (M)', font: { color: '#e0e0e0' } }, thickness: 16, len: 0.6, tickfont: { size: 10, color: '#bbb' }, bgcolor: 'rgba(26,26,46,0.8)', bordercolor: '#2a3a5c' },
      symbol: 'square',
      opacity: 0.92,
      line: { width: 1, color: 'rgba(255,255,255,0.3)' }
    },
    hovertemplate: '<b>%{text}</b><br>VAAF: R$ %{x:,.0f}M<br>VAAT: R$ %{y:,.0f}M<br>VAAR: R$ %{z:,.0f}M<extra></extra>'
  };

  var layout = deepCopy(LAYOUT_3D_BASE);
  layout.title = { text: '<b>Cubo 3D — Complementação VAAF x VAAT x VAAR por UF</b>', font: { size: 15, color: '#e0e0e0' } };
  layout.scene.xaxis.title = { text: 'VAAF (M R$)', font: { color: '#90caf9' } };
  layout.scene.yaxis.title = { text: 'VAAT (M R$)', font: { color: '#a5d6a7' } };
  layout.scene.zaxis.title = { text: 'VAAR (M R$)', font: { color: '#ce93d8' } };
  layout.scene.camera = { eye: { x: 1.5, y: 1.8, z: 1.0 } };
  layout.height = CHART3D_HEIGHT;

  Plotly.newPlot(plotId, [trace], layout, { responsive: true });
  setTimeout(injectFullscreenButtons, 100);
}

function render3D_VAAR_TopEntes(dados, plotId) {
  plotId = plotId || 'chart3d-vaar-top';
  if (!dados || dados.length === 0) return;

  var sorted = dados.slice().sort(function(a, b) { return (b.complemento_uniao || 0) - (a.complemento_uniao || 0); });
  var top = sorted.slice(0, 120);

  var regioes = top.map(function(d) { return MAPA_REGIOES[d.uf] || 'Outro'; });
  var cores = regioes.map(function(r) { return CORES_REGIOES[r] || '#FFD740'; });

  var trace = {
    type: 'scatter3d',
    mode: 'markers',
    x: top.map(function(d) { return d.complemento_vaaf || 0; }),
    y: top.map(function(d) { return d.complemento_vaat || 0; }),
    z: top.map(function(d) { return d.complemento_vaar || 0; }),
    marker: {
      size: top.map(function(d) { return Math.max(5, Math.min(20, (d.recursos_fundeb || 0) / 1e8)); }),
      color: cores,
      symbol: 'square',
      opacity: 0.85,
      line: { width: 0.8, color: 'rgba(255,255,255,0.25)' }
    },
    text: top.map(function(d) { return d.nome + ' (' + d.uf + ')'; }),
    hovertemplate: '<b>%{text}</b><br>VAAF: R$ %{x:,.0f}<br>VAAT: R$ %{y:,.0f}<br>VAAR: R$ %{z:,.0f}<extra></extra>'
  };

  var layout = deepCopy(LAYOUT_3D_BASE);
  layout.title = { text: '<b>Cubo 3D — Top 120 Entes por Complementação</b>', font: { size: 15, color: '#e0e0e0' } };
  layout.scene.xaxis.title = { text: 'Comp. VAAF (R$)', font: { color: '#90caf9' } };
  layout.scene.yaxis.title = { text: 'Comp. VAAT (R$)', font: { color: '#a5d6a7' } };
  layout.scene.zaxis.title = { text: 'Comp. VAAR (R$)', font: { color: '#ce93d8' } };
  layout.scene.camera = { eye: { x: 1.4, y: 1.6, z: 1.2 } };
  layout.height = CHART3D_HEIGHT;

  Plotly.newPlot(plotId, [trace], layout, { responsive: true });
  setTimeout(injectFullscreenButtons, 100);
}

// =========================================================================
// SIMULACAO MUNICIPAL — 3D
// =========================================================================

function render3D_Municipal(orig, ajust, plotId) {
  plotId = plotId || 'chart3d-mun-comparacao';
  if (!orig || !ajust) return;

  var metricas = ['VAAF Final', 'VAAT Final', 'Comp VAAF', 'Comp VAAT', 'Comp VAAR', 'FUNDEB'];
  var coresMetr = [COR_VAAF, COR_VAAT, COR_VAAF, COR_VAAT, COR_VAAR, COR_TOTAL];
  var origVals = [orig.vaaf_final, orig.vaat_final, orig.complemento_vaaf, orig.complemento_vaat, orig.complemento_vaar, orig.recursos_fundeb];
  var ajustVals = [ajust.vaaf_final, ajust.vaat_final, ajust.complemento_vaaf, ajust.complemento_vaat, ajust.complemento_vaar, ajust.recursos_fundeb];
  var diffs = origVals.map(function(v, i) { return ajustVals[i] - v; });
  var maxVal = Math.max.apply(null, origVals.concat(ajustVals).map(Math.abs));
  if (maxVal === 0) maxVal = 1;

  var traceOrig = {
    type: 'scatter3d', mode: 'markers+text', name: 'Original',
    x: metricas.map(function(_, i) { return i; }),
    y: metricas.map(function() { return 0; }),
    z: origVals.map(function(v) { return v / maxVal * 100; }),
    text: metricas,
    textposition: 'top center',
    textfont: { size: 9, color: '#aaa' },
    marker: { size: 14, color: COR_ORIGINAL, symbol: 'square', opacity: 0.7, line: { width: 1.5, color: 'rgba(255,255,255,0.3)' } },
    hovertemplate: '<b>%{text}</b> (Original)<extra></extra>'
  };

  var traceAjust = {
    type: 'scatter3d', mode: 'markers+text', name: 'Ajustado',
    x: metricas.map(function(_, i) { return i; }),
    y: metricas.map(function() { return 1; }),
    z: ajustVals.map(function(v) { return v / maxVal * 100; }),
    text: metricas,
    textposition: 'top center',
    textfont: { size: 9, color: '#ffffff' },
    marker: { size: 16, color: coresMetr, symbol: 'square', opacity: 0.95, line: { width: 1.5, color: 'rgba(255,255,255,0.4)' } },
    hovertemplate: '<b>%{text}</b> (Ajustado)<extra></extra>'
  };

  var linhas = [];
  for (var i = 0; i < metricas.length; i++) {
    linhas.push({
      type: 'scatter3d', mode: 'lines', showlegend: false,
      x: [i, i], y: [0, 1],
      z: [origVals[i] / maxVal * 100, ajustVals[i] / maxVal * 100],
      line: { color: diffs[i] >= 0 ? COR_POSITIVO : COR_NEGATIVO, width: 5 },
      hoverinfo: 'skip'
    });
  }

  var traceDiff = {
    type: 'scatter3d', mode: 'markers', name: 'Diferença',
    x: metricas.map(function(_, i) { return i; }),
    y: metricas.map(function() { return 2; }),
    z: diffs.map(function(d) { return d / maxVal * 100; }),
    marker: {
      size: diffs.map(function(d) { return Math.max(10, Math.min(22, Math.abs(d / maxVal * 100) * 2.5)); }),
      color: diffs.map(function(d) { return d >= 0 ? COR_POSITIVO : COR_NEGATIVO; }),
      symbol: 'diamond',
      opacity: 0.95,
      line: { width: 1.5, color: 'rgba(255,255,255,0.4)' }
    },
    hovertemplate: '<b>Diferenca</b><extra></extra>'
  };

  var allTraces = [traceOrig, traceAjust, traceDiff].concat(linhas);

  var layout = deepCopy(LAYOUT_3D_BASE);
  layout.title = { text: '<b>' + orig.nome + ' (' + orig.uf + ') — Original vs Ajustado</b>', font: { size: 14, color: '#e0e0e0' } };
  layout.scene.xaxis.title = { text: 'Métrica', font: { color: '#90caf9' } };
  layout.scene.xaxis.tickvals = metricas.map(function(_, i) { return i; });
  layout.scene.xaxis.ticktext = metricas;
  layout.scene.xaxis.tickfont = { size: 9, color: '#bbb' };
  layout.scene.yaxis.title = { text: 'Cenário', font: { color: '#a5d6a7' } };
  layout.scene.yaxis.tickvals = [0, 1, 2];
  layout.scene.yaxis.ticktext = ['Original', 'Ajustado', 'Dif'];
  layout.scene.zaxis.title = { text: 'Valor (norm.)', font: { color: '#ce93d8' } };
  layout.scene.camera = { eye: { x: 1.8, y: 1.5, z: 1.0 } };
  layout.height = CHART3D_HEIGHT;
  layout.showlegend = true;
  layout.legend = { x: 0.78, y: 0.95, bgcolor: 'rgba(26,26,46,0.9)', bordercolor: '#2a3a5c', borderwidth: 1, font: { size: 12, color: '#e0e0e0' } };

  Plotly.newPlot(plotId, allTraces, layout, { responsive: true });
  setTimeout(injectFullscreenButtons, 100);
}

function render3D_MunicipalEstado(estadoOrig, estadoAjust, ibgeMunicipio, plotId) {
  plotId = plotId || 'chart3d-mun-estado';
  if (!estadoOrig || !estadoAjust || estadoOrig.length === 0) return;

  var origMap = {};
  estadoOrig.forEach(function(d) { origMap[d.ibge] = d; });

  var pontos = [];
  estadoAjust.forEach(function(d) {
    var o = origMap[d.ibge];
    if (!o) return;
    pontos.push({
      nome: d.nome, ibge: d.ibge,
      difVaaf: d.vaaf_final - o.vaaf_final,
      difVaat: d.vaat_final - o.vaat_final,
      vaafAjust: d.vaaf_final,
      eMunicipio: d.ibge === ibgeMunicipio,
      regiao: MAPA_REGIOES[d.uf] || 'Outro'
    });
  });

  var traceOutros = {
    type: 'scatter3d', mode: 'markers', name: 'Demais entes',
    x: [], y: [], z: [], text: [],
    marker: { size: [], color: [], symbol: 'circle', opacity: 0.6, line: { width: 0.5, color: 'rgba(255,255,255,0.15)' } },
    hovertemplate: '<b>%{text}</b><br>Dif VAAF: R$ %{x:,.2f}<br>Dif VAAT: R$ %{y:,.2f}<br>VAAF: R$ %{z:,.0f}<extra></extra>'
  };

  var traceMun = {
    type: 'scatter3d', mode: 'markers+text', name: 'Município selecionado',
    x: [], y: [], z: [], text: [],
    textposition: 'top center',
    textfont: { size: 12, color: '#ffffff', family: 'Inter' },
    marker: { size: 24, color: COR_DESTAQUE, symbol: 'square', opacity: 1, line: { width: 2.5, color: '#ffffff' } },
    hovertemplate: '<b>%{text}</b><br>Dif VAAF: R$ %{x:,.2f}<br>Dif VAAT: R$ %{y:,.2f}<br>VAAF: R$ %{z:,.0f}<extra></extra>'
  };

  pontos.forEach(function(p) {
    if (p.eMunicipio) {
      traceMun.x.push(p.difVaaf); traceMun.y.push(p.difVaat); traceMun.z.push(p.vaafAjust); traceMun.text.push(p.nome);
    } else {
      traceOutros.x.push(p.difVaaf); traceOutros.y.push(p.difVaat); traceOutros.z.push(p.vaafAjust); traceOutros.text.push(p.nome);
      traceOutros.marker.size.push(7);
      traceOutros.marker.color.push(CORES_REGIOES[p.regiao] || '#78909C');
    }
  });

  var layout = deepCopy(LAYOUT_3D_BASE);
  layout.title = { text: '<b>Impacto no Estado: Dif VAAF x Dif VAAT x VAAF Final</b>', font: { size: 14, color: '#e0e0e0' } };
  layout.scene.xaxis.title = { text: 'Dif VAAF (R$/aluno)', font: { color: '#90caf9' } };
  layout.scene.yaxis.title = { text: 'Dif VAAT (R$/aluno)', font: { color: '#a5d6a7' } };
  layout.scene.zaxis.title = { text: 'VAAF Final (R$/aluno)', font: { color: '#ce93d8' } };
  layout.scene.camera = { eye: { x: 1.6, y: 1.6, z: 1.2 } };
  layout.height = CHART3D_HEIGHT;

  Plotly.newPlot(plotId, [traceOutros, traceMun], layout, { responsive: true });
  setTimeout(injectFullscreenButtons, 100);
}
