/**
 * Abas FUNDEB 2025 e 2026 — simulação multi-exercício
 */

const yearState = {
  2025: { pesos: null, estados: null, etapas: null, familias: null, meta: null, ultimaSimulacao: null },
  2026: { pesos: null, estados: null, etapas: null, familias: null, meta: null, ultimaSimulacao: null },
};

function qs(y, sel) {
  const tab = document.getElementById(`tab-simulacao-${y}`);
  if (!tab) return null;
  return tab.querySelector(sel);
}

function apiAno(ano, url, opts = {}) {
  const path = `/api/${ano}${url}`;
  if (typeof apiFetch === 'function') {
    return apiFetch(path, opts);
  }
  return fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  }).then(async (res) => {
    if (res.status === 401) {
      window.location.href = '/login.html';
      throw new Error('Não autenticado');
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `API ${res.status}`);
    }
    return res.json();
  });
}

function buildSimulacaoTab(ano, habilitado, banner) {
  const dis = habilitado ? '' : 'disabled';
  const bannerHtml = banner
    ? `<div class="alert alert-warning">${banner}</div>` : '';
  return `
  <div id="tab-simulacao-${ano}" class="tab-content">
    ${bannerHtml}
    <div class="row g-4">
      <div class="col-lg-4">
        <div class="card card-input">
          <div class="card-header"><i class="fas fa-cog"></i> Parâmetros — FUNDEB ${ano}</div>
          <div class="card-body">
            <h6 class="section-title">Complementação da União</h6>
            <div class="mb-3">
              <label class="form-label">Montante VAAF (R$)</label>
              <input type="number" class="form-control" id="inp-comp-vaaf-${ano}" step="1000000" ${dis}>
            </div>
            <div class="mb-3">
              <label class="form-label">Montante VAAT (R$)</label>
              <input type="number" class="form-control" id="inp-comp-vaat-${ano}" step="1000000" ${dis}>
            </div>
            <div class="mb-3">
              <label class="form-label">Montante VAAR (R$)</label>
              <input type="number" class="form-control" id="inp-comp-vaar-${ano}" value="0" step="1000000" ${dis}>
            </div>
            <h6 class="section-title mt-4">Ponderadores</h6>
            <div class="mb-3">
              <label class="form-label">NSE</label>
              <input type="text" class="form-control" value="Tabela oficial por ente (fixo)" disabled>
            </div>
            <div class="mb-3" id="wrap-nf-${ano}">
              <label class="form-label" id="lbl-pond-${ano}">DREC (oficial, fixo no VAAF)</label>
              <input type="text" class="form-control" value="Ponderador de Disponibilidade de Recursos" disabled>
            </div>
            <button id="btn-simular-${ano}" class="btn btn-primary btn-lg w-100 mt-3" ${dis}>
              <i class="fas fa-calculator"></i> Simular ${ano}
            </button>
          </div>
        </div>
      </div>
      <div class="col-lg-8">
        <div id="loading-simulacao-${ano}" class="text-center py-5 d-none">
          <div class="spinner-border"></div>
          <p class="mt-2">Executando simulação ${ano}...</p>
        </div>
        <div id="resultados-simulacao-${ano}"></div>
      </div>
    </div>
  </div>`;
}

function buildPesosTab(ano, habilitado, banner) {
  const bannerHtml = banner ? `<div class="alert alert-warning">${banner}</div>` : '';
  return `
  <div id="tab-pesos-${ano}" class="tab-content">
    ${bannerHtml}
    <p class="text-muted">Fatores por segmento (${ano}) — agrupados por família. Edite VAAF e VAAT de cada segmento; os valores são usados na simulação.</p>
    <div id="pesos-accordion-${ano}"></div>
  </div>`;
}

function buildVaarTab(ano, habilitado, banner) {
  const dis = habilitado ? '' : 'disabled';
  const bannerHtml = banner ? `<div class="alert alert-warning">${banner}</div>` : '';
  return `
  <div id="tab-vaar-${ano}" class="tab-content">
    ${bannerHtml}
    <div class="row g-4">
      <div class="col-lg-4">
        <div class="card card-input">
          <div class="card-header"><i class="fas fa-trophy"></i> Parâmetros VAAR — FUNDEB ${ano}</div>
          <div class="card-body">
            <p class="small text-muted">Complementação-VAAR (${ano}): indicadores de atendimento e aprendizagem. Dados e montantes oficiais do exercício ${ano}.</p>
            <div class="mb-3">
              <label class="form-label">Montante total VAAR (R$)</label>
              <input type="number" class="form-control" id="inp-vaar-montante-${ano}" step="1000000" ${dis}>
            </div>
            <div class="mb-3">
              <label class="form-label">Montante VAAF (R$)</label>
              <input type="number" class="form-control" id="inp-vaar-vaaf-${ano}" step="1000000" ${dis}>
            </div>
            <div class="mb-3">
              <label class="form-label">Montante VAAT (R$)</label>
              <input type="number" class="form-control" id="inp-vaar-vaat-${ano}" step="1000000" ${dis}>
            </div>
            <button id="btn-simular-vaar-${ano}" class="btn btn-primary btn-lg w-100 mt-3" ${dis}>
              <i class="fas fa-trophy"></i> Simular VAAR ${ano}
            </button>
          </div>
        </div>
      </div>
      <div class="col-lg-8">
        <div id="loading-vaar-${ano}" class="text-center py-5 d-none">
          <div class="spinner-border"></div>
          <p class="mt-2">Calculando VAAR ${ano}…</p>
        </div>
        <div id="resultados-vaar-${ano}">
          <div class="row g-3 mb-4">
            <div class="col-md-4">
              <div class="info-box info-box-orange">
                <div class="info-box-icon"><i class="fas fa-trophy"></i></div>
                <div class="info-box-content">
                  <span class="info-box-label">Total VAAR</span>
                  <span class="info-box-value" id="ib-vaar-total-${ano}">—</span>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="info-box info-box-blue">
                <div class="info-box-icon"><i class="fas fa-building"></i></div>
                <div class="info-box-content">
                  <span class="info-box-label">VAAR Municípios</span>
                  <span class="info-box-value" id="ib-vaar-mun-${ano}">—</span>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="info-box info-box-cyan">
                <div class="info-box-icon"><i class="fas fa-landmark"></i></div>
                <div class="info-box-content">
                  <span class="info-box-label">VAAR Estados</span>
                  <span class="info-box-value" id="ib-vaar-est-${ano}">—</span>
                </div>
              </div>
            </div>
          </div>
          <div class="card mb-4"><div class="card-body"><div id="chart-vaar-uf-${ano}"></div></div></div>
          <h4 class="mb-3"><i class="fas fa-cube"></i> Análises 3D — VAAR ${ano}</h4>
          <div class="card mb-4 chart3d-container"><div class="card-body"><div id="chart3d-vaar-dist-${ano}"></div></div></div>
          <div class="card mb-4 chart3d-container"><div class="card-body"><div id="chart3d-vaar-top-${ano}"></div></div></div>
          <div class="card mb-4">
            <div class="card-header"><i class="fas fa-trophy"></i> Distribuição VAAR por ente (top 50)</div>
            <div class="card-body table-responsive">
              <table id="tbl-vaar-${ano}" class="table table-sm table-striped"></table>
            </div>
          </div>
          <div class="card mb-4"><div class="card-body"><div id="chart-vaar-impacto-${ano}"></div></div></div>
        </div>
      </div>
    </div>
  </div>`;
}

function buildMunicipioTab(ano, habilitado, banner) {
  const dis = habilitado ? '' : 'disabled';
  const bannerHtml = banner ? `<div class="alert alert-warning">${banner}</div>` : '';
  return `
  <div id="tab-municipio-${ano}" class="tab-content">
    ${bannerHtml}
    <div class="row g-4">
      <div class="col-lg-4">
        <div class="card card-input">
          <div class="card-header"><i class="fas fa-map-marker-alt"></i> Seleção do Município — FUNDEB ${ano}</div>
          <div class="card-body">
            <div class="mb-3"><label class="form-label">Estado</label>
              <select class="form-select" id="sel-uf-mun-${ano}" ${dis}><option value="">Selecione...</option></select>
            </div>
            <div class="mb-3"><label class="form-label">Município</label>
              <select class="form-select" id="sel-mun-${ano}" ${dis}><option value="">Selecione...</option></select>
            </div>
            <hr style="border-color:var(--warm-sand)">
            <h6 class="section-title"><i class="fas fa-plus-circle"></i> Parâmetros gerais</h6>
            <div class="mb-2"><label class="form-label small">Complementação VAAF (R$)</label>
              <input type="number" class="form-control form-control-sm" id="inp-mun-vaaf-${ano}" step="1000000" ${dis}></div>
            <div class="mb-2"><label class="form-label small">Complementação VAAT (R$)</label>
              <input type="number" class="form-control form-control-sm" id="inp-mun-vaat-${ano}" step="1000000" ${dis}></div>
            <div class="mb-2"><label class="form-label small">Complementação VAAR (R$)</label>
              <input type="number" class="form-control form-control-sm" id="inp-mun-vaar-${ano}" step="1000000" ${dis}></div>
            <button id="btn-simular-mun-${ano}" class="btn btn-primary btn-lg w-100 mt-3" disabled ${dis}>
              <i class="fas fa-calculator"></i> Simular
            </button>
          </div>
        </div>
        <div class="card card-input mt-3">
          <div class="card-header"><i class="fas fa-edit"></i> Ajustar matrículas por segmento</div>
          <div class="card-body matriculas-mun-scroll" id="matriculas-mun-${ano}">
            <p class="text-muted small">Selecione um município para editar cada um dos segmentos (${ano}).</p>
          </div>
        </div>
      </div>
      <div class="col-lg-8">
        <div id="loading-municipio-${ano}" class="text-center py-5 d-none">
          <div class="spinner-border"></div>
          <p class="mt-2">Simulando impacto municipal (${ano})…</p>
        </div>
        <div id="resultados-municipio-${ano}">
          <div class="alert alert-info"><i class="fas fa-info-circle"></i> Selecione estado e município, ajuste matrículas por segmento se desejar e clique em <strong>Simular</strong>.</div>
          <div class="card mb-4" id="mun-explicacao-card-${ano}" style="display:none">
            <div class="card-header bg-dark text-white"><i class="fas fa-lightbulb"></i> Análise e Explicação dos Resultados</div>
            <div class="card-body" id="mun-explicacao-${ano}"></div>
          </div>
          <div class="row g-3 mb-4" id="mun-comparacao-${ano}" style="display:none">
            <div class="col-md-6"><div class="card"><div class="card-header bg-secondary text-white"><i class="fas fa-database"></i> Cenário original</div><div class="card-body" id="mun-original-${ano}"></div></div></div>
            <div class="col-md-6"><div class="card"><div class="card-header bg-primary text-white"><i class="fas fa-edit"></i> Cenário ajustado</div><div class="card-body" id="mun-ajustado-${ano}"></div></div></div>
          </div>
          <div class="card mb-4" id="mun-chart-card-${ano}" style="display:none"><div class="card-body"><div id="chart-mun-comparacao-${ano}"></div></div></div>
          <div id="mun-3d-section-${ano}" style="display:none">
            <h4 class="mb-3"><i class="fas fa-cube"></i> Análises 3D — Municipal ${ano}</h4>
            <div class="card mb-4 chart3d-container"><div class="card-body"><div id="chart3d-mun-comparacao-${ano}"></div></div></div>
            <div class="card mb-4 chart3d-container"><div class="card-body"><div id="chart3d-mun-estado-${ano}"></div></div></div>
          </div>
          <div class="card mb-4" id="mun-impacto-card-${ano}" style="display:none">
            <div class="card-header"><i class="fas fa-users"></i> Impacto nos entes do estado</div>
            <div class="card-body table-responsive"><table id="tbl-mun-impacto-${ano}" class="table table-sm table-striped"></table></div>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

let navMultiAnoInjected = false;

function injectNavAndTabs() {
  if (navMultiAnoInjected) return;
  const nav = document.querySelector('.sidebar-nav');
  const main = document.getElementById('main-content');
  if (!nav || !main) return;
  navMultiAnoInjected = true;

  const items = [
    { y: 2026, label: 'Simulação 2026', tab: 'simulacao-2026', icon: 'fa-calculator', ok: true },
    { y: 2026, label: 'Ponderações 2026', tab: 'pesos-2026', icon: 'fa-balance-scale', ok: true },
    { y: 2026, label: 'VAAR 2026', tab: 'vaar-2026', icon: 'fa-trophy', ok: true },
    { y: 2026, label: 'Município 2026', tab: 'municipio-2026', icon: 'fa-map-marker-alt', ok: true },
    { y: 2025, label: 'Consulta 2025', tab: 'simulacao-2025', icon: 'fa-calendar', ok: false },
    { y: 2025, label: 'Ponderações 2025', tab: 'pesos-2025', icon: 'fa-balance-scale', ok: false },
  ];

  const anchor =
    nav.querySelector('li[data-tab="documentacao"]') ||
    nav.querySelector('#nav-admin-usuarios');

  const frag = document.createDocumentFragment();

  const addSection = (text) => {
    const li = document.createElement('li');
    li.className = 'sidebar-section-label';
    li.innerHTML = `<span>${text}</span>`;
    frag.appendChild(li);
  };

  addSection('FUNDEB 2026');
  items.filter((it) => it.y === 2026).forEach((it) => {
    const li = document.createElement('li');
    li.dataset.tab = it.tab;
    li.innerHTML = `<i class="fas ${it.icon}"></i> <span>${it.label}</span>`;
    frag.appendChild(li);
  });

  addSection('FUNDEB 2025');
  items.filter((it) => it.y === 2025).forEach((it) => {
    const li = document.createElement('li');
    li.dataset.tab = it.tab;
    li.innerHTML = `<i class="fas ${it.icon}"></i> <span>${it.label}</span>`;
    frag.appendChild(li);
  });

  if (anchor) nav.insertBefore(frag, anchor);
  else nav.appendChild(frag);

  const banner2025 = 'Receitas e ponderadores oficiais de 2025 ainda não disponíveis. Matrículas carregadas apenas para consulta.';
  main.insertAdjacentHTML('beforeend', buildSimulacaoTab(2026, true, ''));
  main.insertAdjacentHTML('beforeend', buildPesosTab(2026, true, ''));
  main.insertAdjacentHTML('beforeend', buildVaarTab(2026, true, ''));
  main.insertAdjacentHTML('beforeend', buildMunicipioTab(2026, true, ''));
  main.insertAdjacentHTML('beforeend', buildSimulacaoTab(2025, false, banner2025));
  main.insertAdjacentHTML('beforeend', buildPesosTab(2025, false, banner2025));
}

async function initYear(ano) {
  const st = yearState[ano];
  const [meta, pesos, estados, etapas] = await Promise.all([
    apiAno(ano, '/meta'),
    apiAno(ano, '/pesos'),
    apiAno(ano, '/estados'),
    apiAno(ano, '/etapas'),
  ]);
  st.meta = meta;
  st.pesos = pesos;
  st.estados = estados.estados;
  st.regioes = estados.regioes;
  st.etapas = etapas.etapas || etapas;
  st.familias = etapas.familias || {};

  if (meta.defaults_complementacao) {
    const d = meta.defaults_complementacao;
    const setVal = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.value = v || 0;
    };
    setVal(`inp-comp-vaaf-${ano}`, d.vaaf);
    setVal(`inp-comp-vaat-${ano}`, d.vaat);
    setVal(`inp-comp-vaar-${ano}`, d.vaar);
    setVal(`inp-vaar-montante-${ano}`, d.vaar);
    setVal(`inp-vaar-vaaf-${ano}`, d.vaaf);
    setVal(`inp-vaar-vaat-${ano}`, d.vaat);
    setVal(`inp-mun-vaaf-${ano}`, d.vaaf);
    setVal(`inp-mun-vaat-${ano}`, d.vaat);
    setVal(`inp-mun-vaar-${ano}`, d.vaar);
  }

  renderPesosAccordion(ano);
  populateMunSelectors(ano);
}

function pesoInputId(ano, tipo, etapa) {
  return `peso-${tipo}-${ano}-${etapa}`;
}

function getPesosAno(ano) {
  const vaaf = [];
  const vaat = [];
  (yearState[ano].pesos || []).forEach((p) => {
    if (typeof canEditPesos === 'function' && !canEditPesos()) {
      vaaf.push(Number(p.peso_vaaf) || 0);
      vaat.push(Number(p.peso_vaat) || 0);
      return;
    }
    const elVaaf = document.getElementById(pesoInputId(ano, 'vaaf', p.etapa));
    const elVaat = document.getElementById(pesoInputId(ano, 'vaat', p.etapa));
    vaaf.push(parseFloat(elVaaf?.value ?? p.peso_vaaf) || 0);
    vaat.push(parseFloat(elVaat?.value ?? p.peso_vaat) || 0);
  });
  return { vaaf, vaat };
}

function renderPesosAccordion(ano) {
  const container = document.getElementById(`pesos-accordion-${ano}`);
  if (!container || !yearState[ano].pesos) return;
  const habilitado = yearState[ano].meta?.simulacao_habilitada !== false;
  const readOnly = !habilitado || (typeof canEditPesos === 'function' && !canEditPesos());
  const dis = readOnly ? 'disabled readonly' : '';
  let banner = '';
  if (habilitado && typeof canEditPesos === 'function' && !canEditPesos()) {
    banner = `<div class="alert alert-info py-2 mb-3">
      <i class="fas fa-lock"></i> Somente administradores podem alterar os fatores de ponderação.
    </div>`;
  }
  const famMap = {};
  yearState[ano].pesos.forEach((p) => {
    const fam = p.familia || p.nome;
    if (!famMap[fam]) famMap[fam] = [];
    famMap[fam].push(p);
  });
  let html = banner + '<div class="accordion" id="acc-pesos-' + ano + '">';
  let i = 0;
  for (const [fam, items] of Object.entries(famMap)) {
    const id = `acc-${ano}-${i++}`;
    html += `<div class="accordion-item">
      <h2 class="accordion-header">
        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#${id}">
          ${fam} <span class="badge bg-secondary ms-2">${items.length} segmentos</span>
        </button>
      </h2>
      <div id="${id}" class="accordion-collapse collapse" data-bs-parent="#acc-pesos-${ano}">
        <div class="accordion-body pesos-accordion-body">
          <div class="peso-segmento-header row g-2 d-none d-md-flex small text-muted fw-semibold mb-2">
            <div class="col-md-5">Segmento</div>
            <div class="col-md-3">Peso VAAF</div>
            <div class="col-md-3">Peso VAAT</div>
          </div>`;
    items.forEach((p) => {
      const vaaf = Number(p.peso_vaaf);
      const vaat = Number(p.peso_vaat);
      const idVaaf = pesoInputId(ano, 'vaaf', p.etapa);
      const idVaat = pesoInputId(ano, 'vaat', p.etapa);
      html += `<div class="peso-segmento-row row g-2 align-items-end mb-2 pb-2">
        <div class="col-12 col-md-5">
          <span class="peso-segmento-nome">${p.nome}</span>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label form-label-sm d-md-none" for="${idVaaf}">VAAF</label>
          <input type="number" class="form-control form-control-sm peso-input"
            id="${idVaaf}" data-ano="${ano}" data-etapa="${p.etapa}" data-tipo="vaaf"
            min="0" max="10" step="0.01" value="${vaaf}" ${dis}>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label form-label-sm d-md-none" for="${idVaat}">VAAT</label>
          <input type="number" class="form-control form-control-sm peso-input"
            id="${idVaat}" data-ano="${ano}" data-etapa="${p.etapa}" data-tipo="vaat"
            min="0" max="10" step="0.01" value="${vaat}" ${dis}>
        </div>
      </div>`;
    });
    html += `</div></div></div>`;
  }
  html += '</div>';
  container.innerHTML = html;
}

function populateMunSelectors(ano) {
  const selUf = document.getElementById(`sel-uf-mun-${ano}`);
  if (!selUf) return;
  selUf.innerHTML = '<option value="">Selecione...</option>';
  const regioes = yearState[ano].regioes || {};
  for (const [regiao, ufs] of Object.entries(regioes)) {
    const group = document.createElement('optgroup');
    group.label = regiao;
    ufs.forEach((uf) => {
      const opt = document.createElement('option');
      opt.value = uf;
      opt.textContent = uf;
      group.appendChild(opt);
    });
    selUf.appendChild(group);
  }
  selUf.onchange = async () => {
    const uf = selUf.value;
    const selMun = document.getElementById(`sel-mun-${ano}`);
    selMun.innerHTML = '<option value="">Selecione...</option>';
    const btn = document.getElementById(`btn-simular-mun-${ano}`);
    if (btn) btn.disabled = true;
    document.getElementById(`matriculas-mun-${ano}`).innerHTML =
      '<p class="text-muted small">Selecione um município.</p>';
    if (!uf) return;
    selMun.innerHTML = '<option value="">Carregando...</option>';
    const mun = await apiAno(ano, `/municipios?uf=${uf}`);
    selMun.innerHTML = '<option value="">Selecione...</option>';
    mun.filter((m) => m.ibge > 100).forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m.ibge;
      opt.textContent = `${m.nome} (${m.ibge})`;
      selMun.appendChild(opt);
    });
  };
  const selMun = document.getElementById(`sel-mun-${ano}`);
  if (selMun) selMun.onchange = () => loadMunMatriculas(ano);
}

function getMatriculasAjustadasAno(ano) {
  const result = {};
  document.querySelectorAll(`#matriculas-mun-acc-${ano} input[data-etapa]`).forEach((inp) => {
    result[inp.dataset.etapa] = parseFloat(inp.value) || 0;
  });
  return result;
}

function collectMunInputValues(ano) {
  const v = {};
  document.querySelectorAll(`#matriculas-mun-acc-${ano} input[data-etapa]`).forEach((inp) => {
    v[inp.dataset.etapa] = parseFloat(inp.value) || 0;
  });
  return v;
}

function countMunSegmentosComMatricula(ano, data) {
  return (yearState[ano].pesos || []).filter(
    (p) => (data.matriculas[p.etapa] || 0) > 0,
  ).length;
}

function renderMunMatriculasForm(ano, data, overrides = {}) {
  const box = document.getElementById(`matriculas-mun-${ano}`);
  if (!box || !yearState[ano].pesos) return;

  const showEmpty = yearState[ano].munShowEmpty === true;
  const totalEtapas = yearState[ano].pesos.length;
  const comMatricula = countMunSegmentosComMatricula(ano, data);

  const famMap = {};
  yearState[ano].pesos.forEach((p) => {
    const fam = p.familia || p.nome;
    if (!famMap[fam]) famMap[fam] = [];
    famMap[fam].push(p);
  });

  let accHtml = `<div class="accordion" id="acc-mun-${ano}">`;
  let i = 0;
  let exibidos = 0;
  for (const [fam, items] of Object.entries(famMap)) {
    const comMat = items.filter((p) => (data.matriculas[p.etapa] || 0) > 0);
    const lista = showEmpty ? items : comMat;
    if (lista.length === 0) continue;
    exibidos += lista.length;
    const id = `acc-mun-${ano}-${i++}`;
    const badge = showEmpty
      ? `${lista.length} <span class="text-muted fw-normal">(${comMat.length} c/ matr.)</span>`
      : String(lista.length);
    accHtml += `<div class="accordion-item">
      <h2 class="accordion-header">
        <button class="accordion-button collapsed py-2" type="button" data-bs-toggle="collapse" data-bs-target="#${id}">
          ${fam} <span class="badge bg-secondary ms-2">${badge}</span>
        </button>
      </h2>
      <div id="${id}" class="accordion-collapse collapse" data-bs-parent="#acc-mun-${ano}">
        <div class="accordion-body p-2">`;
    lista.forEach((p) => {
      const original = data.matriculas[p.etapa] || 0;
      const val = Math.round(overrides[p.etapa] ?? original);
      const semMat = original <= 0;
      const cls = semMat ? ' matricula-item-zero' : '';
      accHtml += `<div class="matricula-item mb-1${cls}">
        <label class="small">${p.nome}${semMat ? ' <span class="text-muted">(sem matrícula)</span>' : ''}</label>
        <input type="number" class="form-control form-control-sm"
          data-etapa="${p.etapa}" value="${val}" min="0" step="1">
      </div>`;
    });
    accHtml += `</div></div></div>`;
  }
  accHtml += '</div>';

  box.innerHTML = `
    <p class="mb-2"><strong>${data.nome}</strong> — ${data.uf}</p>
    <p class="text-muted small mb-2">
      ${comMatricula} segmento(s) com matrícula neste município (de ${totalEtapas} no exercício ${ano}).
      ${showEmpty ? `Exibindo <strong>${exibidos}</strong> segmentos.` : 'Expanda as famílias para editar.'}
    </p>
    <div class="form-check form-switch mb-2">
      <input class="form-check-input" type="checkbox" id="chk-mun-show-empty-${ano}"
        ${showEmpty ? 'checked' : ''}>
      <label class="form-check-label small" for="chk-mun-show-empty-${ano}">
        Mostrar segmentos sem matrícula
      </label>
    </div>
    <div id="matriculas-mun-acc-${ano}">${accHtml}</div>`;

  const chk = document.getElementById(`chk-mun-show-empty-${ano}`);
  if (chk) {
    chk.onchange = () => {
      yearState[ano].munShowEmpty = chk.checked;
      const vals = collectMunInputValues(ano);
      renderMunMatriculasForm(ano, data, vals);
    };
  }
}

async function loadMunMatriculas(ano) {
  const ibge = parseInt(document.getElementById(`sel-mun-${ano}`).value, 10);
  const btn = document.getElementById(`btn-simular-mun-${ano}`);
  if (!ibge) return;
  const data = await apiAno(ano, `/municipio/${ibge}/matriculas`);
  yearState[ano].munMat = data;
  yearState[ano].munShowEmpty = false;
  renderMunMatriculasForm(ano, data);
  if (btn && yearState[ano].meta?.simulacao_habilitada) btn.disabled = false;
}

async function executarSimulacaoAno(ano) {
  if (!yearState[ano].meta?.simulacao_habilitada) {
    alert(yearState[ano].meta?.mensagem_bloqueio || 'Simulação indisponível.');
    return;
  }
  const loading = document.getElementById(`loading-simulacao-${ano}`);
  loading?.classList.remove('d-none');
  const pesos = getPesosAno(ano);
  const body = {
    complementacao_vaaf: parseFloat(document.getElementById(`inp-comp-vaaf-${ano}`).value) || 0,
    complementacao_vaat: parseFloat(document.getElementById(`inp-comp-vaat-${ano}`).value) || 0,
    complementacao_vaar: parseFloat(document.getElementById(`inp-comp-vaar-${ano}`).value) || 0,
    max_nse: 1.1,
    min_nse: 1.0,
    max_nf: 1.0,
    min_nf: 1.0,
    pesos_vaaf: pesos.vaaf,
    pesos_vaat: pesos.vaat,
  };
  try {
    const data = await apiAno(ano, '/simular', { method: 'POST', body: JSON.stringify(body) });
    yearState[ano].ultimaSimulacao = data;
    renderResultadosAno(ano, data);
  } catch (e) {
    alert('Erro: ' + e.message);
  } finally {
    loading?.classList.add('d-none');
  }
}

function renderResultadosAno(ano, data) {
  const el = document.getElementById(`resultados-simulacao-${ano}`);
  if (!el) return;
  const r = data.resumo;
  const val = data.validacao || {};
  el.innerHTML = `
    <div class="row g-3 mb-3">
      <div class="col-md-4"><div class="info-box info-box-green"><div class="info-box-content">
        <span class="info-box-label">VAAF mín. simulado</span><span class="info-box-value">${fmt.numero(r.vaaf_minimo_simulado)}</span>
      </div></div></div>
      <div class="col-md-4"><div class="info-box info-box-purple"><div class="info-box-content">
        <span class="info-box-label">VAAT mín. simulado</span><span class="info-box-value">${fmt.numero(r.vaat_minimo_simulado)}</span>
      </div></div></div>
      <div class="col-md-4"><div class="info-box info-box-cyan"><div class="info-box-content">
        <span class="info-box-label">% complementados</span><span class="info-box-value">${fmt.pct(r.percentual_complementados)}</span>
      </div></div></div>
    </div>
    <div class="card mb-3"><div class="card-header">Validação RF-10: ${val.valido ? 'OK' : 'Falhou'}</div>
      <div class="card-body small">${(val.erros || []).map((e) => `<div class="text-danger">${e}</div>`).join('')}
      ${(val.checagens || []).slice(0, 5).map((c) => `<div class="text-success">${c}</div>`).join('')}</div></div>
    <div id="chart-vaaf-uf-${ano}"></div>
    <div id="chart-vaat-uf-${ano}" class="mt-3"></div>`;

  const ufs = data.por_uf.map((d) => d.uf).sort();
  Plotly.newPlot(`chart-vaaf-uf-${ano}`, [{
    x: ufs, y: ufs.map((uf) => data.por_uf.find((d) => d.uf === uf)?.vaaf_medio || 0),
    type: 'bar', marker: { color: '#3b82f6' },
  }], { title: `VAAF médio por UF — ${ano}`, margin: { t: 40 } }, { responsive: true });

  Plotly.newPlot(`chart-vaat-uf-${ano}`, [{
    x: ufs, y: ufs.map((uf) => data.por_uf.find((d) => d.uf === uf)?.vaat_medio || 0),
    type: 'bar', marker: { color: '#8b5cf6' },
  }], { title: `VAAT médio por UF — ${ano}`, margin: { t: 40 } }, { responsive: true });
}

function renderResultadosVAARAno(ano, data, totalVaar) {
  const vaarMun = data.filter((d) => d.ibge > 100).reduce((s, d) => s + (d.complemento_vaar || 0), 0);
  const vaarEst = data.filter((d) => d.ibge < 100).reduce((s, d) => s + (d.complemento_vaar || 0), 0);

  const elTotal = document.getElementById(`ib-vaar-total-${ano}`);
  const elMun = document.getElementById(`ib-vaar-mun-${ano}`);
  const elEst = document.getElementById(`ib-vaar-est-${ano}`);
  if (elTotal) elTotal.textContent = fmt.moeda(totalVaar);
  if (elMun) elMun.textContent = fmt.moeda(vaarMun);
  if (elEst) elEst.textContent = fmt.moeda(vaarEst);

  const porUf = {};
  data.forEach((d) => {
    if (!porUf[d.uf]) porUf[d.uf] = { vaar: 0, vaaf: 0, vaat: 0, total: 0 };
    porUf[d.uf].vaar += d.complemento_vaar || 0;
    porUf[d.uf].vaaf += d.complemento_vaaf || 0;
    porUf[d.uf].vaat += d.complemento_vaat || 0;
    porUf[d.uf].total += d.complemento_uniao || 0;
  });

  const ufs = Object.keys(porUf).sort((a, b) => porUf[b].vaar - porUf[a].vaar);

  Plotly.newPlot(`chart-vaar-uf-${ano}`, [
    { x: ufs, y: ufs.map((uf) => porUf[uf].vaar / 1e6), type: 'bar', name: 'VAAR', marker: { color: '#f59e0b' } },
    { x: ufs, y: ufs.map((uf) => porUf[uf].vaaf / 1e6), type: 'bar', name: 'VAAF', marker: { color: '#3b82f6' } },
    { x: ufs, y: ufs.map((uf) => porUf[uf].vaat / 1e6), type: 'bar', name: 'VAAT', marker: { color: '#8b5cf6' } },
  ], {
    barmode: 'stack',
    title: `<b>Complementação da União por UF — FUNDEB ${ano}</b>`,
    yaxis: { title: 'Milhões (R$)', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });

  const ufsImpacto = Object.keys(porUf).sort((a, b) => {
    const pctA = porUf[a].total > 0 ? porUf[a].vaar / porUf[a].total : 0;
    const pctB = porUf[b].total > 0 ? porUf[b].vaar / porUf[b].total : 0;
    return pctB - pctA;
  });

  Plotly.newPlot(`chart-vaar-impacto-${ano}`, [{
    x: ufsImpacto,
    y: ufsImpacto.map((uf) => (porUf[uf].total > 0 ? (porUf[uf].vaar / porUf[uf].total * 100) : 0)),
    type: 'bar',
    marker: { color: '#f59e0b' },
    hovertemplate: '%{x}: %{y:.1f}%<extra></extra>',
  }], {
    title: `<b>Proporção da VAAR no total da complementação por UF — ${ano}</b>`,
    yaxis: { title: '%', separatethousands: true },
    margin: { t: 50, b: 40 },
  }, { responsive: true });

  const sorted = [...data].sort((a, b) => (b.complemento_vaar || 0) - (a.complemento_vaar || 0));
  const top = sorted.slice(0, 50);
  const headers = ['Posição', 'UF', 'Ente', 'VAAR (R$)', 'VAAF (R$)', 'VAAT (R$)', 'Total comp. (R$)', 'Recursos FUNDEB (R$)'];
  const rows = top.map((d, i) => [
    i + 1, d.uf, d.nome,
    fmt.moeda(d.complemento_vaar), fmt.moeda(d.complemento_vaaf),
    fmt.moeda(d.complemento_vaat), fmt.moeda(d.complemento_uniao),
    fmt.moeda(d.recursos_fundeb),
  ]);
  const tbl = document.getElementById(`tbl-vaar-${ano}`);
  if (tbl) tbl.innerHTML = buildTable(headers, rows);

  if (typeof render3D_VAAR_Distribuicao === 'function') {
    render3D_VAAR_Distribuicao(data, `chart3d-vaar-dist-${ano}`);
  }
  if (typeof render3D_VAAR_TopEntes === 'function') {
    render3D_VAAR_TopEntes(data, `chart3d-vaar-top-${ano}`);
  }
}

async function executarVaarAno(ano) {
  if (!yearState[ano].meta?.simulacao_habilitada) {
    alert(yearState[ano].meta?.mensagem_bloqueio || 'Simulação indisponível.');
    return;
  }
  const loading = document.getElementById(`loading-vaar-${ano}`);
  loading?.classList.remove('d-none');
  const pesos = getPesosAno(ano);
  const body = {
    complementacao_vaaf: parseFloat(document.getElementById(`inp-vaar-vaaf-${ano}`).value) || 0,
    complementacao_vaat: parseFloat(document.getElementById(`inp-vaar-vaat-${ano}`).value) || 0,
    complementacao_vaar: parseFloat(document.getElementById(`inp-vaar-montante-${ano}`).value) || 0,
    max_nse: 1.1,
    min_nse: 1.0,
    max_nf: 1.0,
    min_nf: 1.0,
    pesos_vaaf: pesos.vaaf,
    pesos_vaat: pesos.vaat,
  };
  try {
    const data = await apiAno(ano, '/simular/completo', { method: 'POST', body: JSON.stringify(body) });
    renderResultadosVAARAno(ano, data, body.complementacao_vaar);
  } catch (e) {
    alert('Erro na simulação VAAR: ' + e.message);
  } finally {
    loading?.classList.add('d-none');
  }
}

async function executarMunAno(ano) {
  const ibge = parseInt(document.getElementById(`sel-mun-${ano}`).value, 10);
  if (!ibge) {
    alert('Selecione um município');
    return;
  }
  if (!yearState[ano].meta?.simulacao_habilitada) {
    alert(yearState[ano].meta?.mensagem_bloqueio || 'Simulação indisponível.');
    return;
  }

  const loading = document.getElementById(`loading-municipio-${ano}`);
  loading?.classList.remove('d-none');

  const pesos = getPesosAno(ano);
  const body = {
    ibge,
    matriculas_ajustadas: getMatriculasAjustadasAno(ano),
    complementacao_vaaf: parseFloat(document.getElementById(`inp-mun-vaaf-${ano}`).value) || 0,
    complementacao_vaat: parseFloat(document.getElementById(`inp-mun-vaat-${ano}`).value) || 0,
    complementacao_vaar: parseFloat(document.getElementById(`inp-mun-vaar-${ano}`).value) || 0,
    max_nse: 1.1,
    min_nse: 1.0,
    max_nf: 1.0,
    min_nf: 1.0,
    pesos_vaaf: pesos.vaaf,
    pesos_vaat: pesos.vaat,
  };

  try {
    const data = await apiAno(ano, '/simular/municipio', { method: 'POST', body: JSON.stringify(body) });
    if (typeof window.renderResultadosMunicipio === 'function') {
      window.renderResultadosMunicipio(data, {
        ano,
        munData: yearState[ano].munMat,
        etapasNomes: yearState[ano].etapas,
        getAjustadas: () => getMatriculasAjustadasAno(ano),
        ponderadorLabel: yearState[ano].meta?.modo_ponderador === 'drec' ? 'DREC' : 'NF',
      });
    }
  } catch (e) {
    alert('Erro na simulação municipal: ' + e.message);
  } finally {
    loading?.classList.add('d-none');
  }
}

function wireEvents() {
  document.getElementById('btn-simular-2026')?.addEventListener('click', () => executarSimulacaoAno(2026));
  document.getElementById('btn-simular-vaar-2026')?.addEventListener('click', () => executarVaarAno(2026));
  document.getElementById('btn-simular-mun-2026')?.addEventListener('click', () => executarMunAno(2026));
}

function initMultiAno() {
  injectNavAndTabs();
  wireEvents();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initMultiAno, { once: true });
} else {
  initMultiAno();
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    if (typeof guardAuth === 'function') await guardAuth();
    await initYear(2026);
    await initYear(2025);
  } catch (e) {
    console.error('Init multi-ano:', e);
  }
});
