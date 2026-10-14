"""A página inicial montada permanece igual à referência e o menu tem um só exercício."""

from pathlib import Path

from app.ui.index_page import render_index_bytes


def test_index_html_preserva_a_referencia():
    golden = Path(__file__).parent / "golden" / "index.html"
    assert render_index_bytes() == golden.read_bytes()


def test_menu_tem_um_seletor_de_exercicio():
    texto = render_index_bytes().decode("utf-8")
    assert 'id="exercicio-ativo"' in texto
    barra = texto.split('id="sidebar"', 1)[1].split("</nav>", 1)[0]
    for rotulo in ("FUNDEB 2024", "FUNDEB 2025", "FUNDEB 2026"):
        assert rotulo not in barra
    assert "FUNDEB 2025" not in texto
    assert "FUNDEB 2026" not in texto


def test_tab_cenario_exibe_cenarios_independentes_e_receita_constante():
    texto = render_index_bytes().decode("utf-8")
    assert "Cenário A — Referência" in texto
    assert "Cenário B — Simulação 1" in texto
    assert "Cenário C — Simulação 2" in texto
    assert "Cenário D — Simulação 3" in texto
    assert "Matrículas originais da base selecionada." in texto
    assert "Ajustes próprios de matrículas, mantendo a mesma receita da referência." in texto
    assert (
        "Receita constante em todos os cenários. Configure diferentes ajustes de matrículas "
        "e compare os resultados entre redes e cenários."
    ) in texto
    assert "Editar matrículas — Cenário B" in texto
    assert "Salvar no cenário B" in texto
    assert "<th>Cenário</th>" in texto
    assert 'id="cen-receita-tipo"' not in texto


def test_fluxo_js_edicao_cenarios_independentes_isolamento_e_exclusao():
    import subprocess

    script = r"""
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const elements = {};
function makeEl(id, tag='div') {
  const el = {
    id, tagName: tag.toUpperCase(), value: '', textContent: '', _innerHTML: '',
    disabled: false, checked: false, dataset: {},
    style: { display: '' },
    classList: {
      _set: new Set(),
      add(c) { this._set.add(c); },
      remove(c) { this._set.delete(c); },
      toggle(c, f) { if (f === undefined) { if (this._set.has(c)) this._set.delete(c); else this._set.add(c); } else if (f) this._set.add(c); else this._set.delete(c); },
      contains(c) { return this._set.has(c); }
    },
    listeners: {},
    addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); },
    dispatchEvent(ev) { (this.listeners[ev.type] || []).forEach(fn => fn(ev)); },
    appendChild() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return makeEl('closest'); }
  };
  Object.defineProperty(el, 'innerHTML', {
    get() { return this._innerHTML; },
    set(v) { this._innerHTML = String(v); }
  });
  elements[id] = el;
  return el;
}

[
  'tab-cenario','cen-aviso','cen-base','cen-base-info','cen-uf','cen-rede','cen-busca','cen-todas',
  'cen-form','cen-rascunho-conversoes','cen-conv-origem','cen-conv-destino','cen-conv-valor','cen-btn-conv',
  'cen-ajustes','cen-ajustes-count','cen-btn-limpar','cen-btn-executar','cen-btn-salvar-edicao',
  'cen-btn-salvar-texto','cen-btn-cancelar-edicao','cen-btn-abrir-edicao','cen-cenario-alvo',
  'cen-form-titulo','cen-edicao-contexto','cen-edicao-alerta','cen-cenarios-lista',
  'cen-pesos-modo','cen-pesos-box','cen-pesos','cen-btn-pesos-padrao','cen-recorte',
  'cen-efeito-ativo','cen-filtro-rede','cen-resultado','cen-tabela-comparativa','cen-cards',
  'cen-metadados','cen-fora-recorte','cen-status'
].forEach(id => makeEl(id));

elements['cen-base'].value = 'fundeb-2024';
elements['cen-cenario-alvo'].value = 'B';
elements['cen-recorte'].value = 'selecionadas';
elements['cen-efeito-ativo'].value = 'B_A';
elements['cen-pesos-modo'].value = 'padrao';

const redesMock = {
  2304400: {
    ibge: 2304400, uf: 'CE', nome: 'FORTALEZA', tipo_rede: 'rede municipal',
    nomes_categorias: { creche_parcial: 'Creche Parcial', fundamental: 'Fundamental' },
    matriculas: { creche_parcial: 1000, fundamental: 5000 }
  },
  2312908: {
    ibge: 2312908, uf: 'CE', nome: 'SOBRAL', tipo_rede: 'rede municipal',
    nomes_categorias: { creche_parcial: 'Creche Parcial', fundamental: 'Fundamental' },
    matriculas: { creche_parcial: 500, fundamental: 3000 }
  }
};

const alertas = [];
const sandbox = {
  console, Math, Date, Promise, Map, Set, Number, String, Boolean, Array, Object, RegExp, JSON,
  parseInt, parseFloat, isNaN, isFinite, setTimeout, clearTimeout,
  encodeURIComponent,
  alert(msg) { alertas.push(msg); },
  confirm() { return true; },
  Chart: function() { return { destroy() {} }; },
  window: {},
  document: {
    getElementById(id) { return elements[id] || makeEl(id); },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    addEventListener() {},
    createElement(tag) { return makeEl('tmp_' + Math.random(), tag); }
  },
  apiFetch: async (url) => {
    if (url === '/api/bases') {
      return { aviso: '', bases: [{ base_id: 'fundeb-2024', ano_exercicio: 2024, situacao: 'Oficial', padrao: true }] };
    }
    if (url === '/api/estados') {
      return { regioes: { Nordeste: [{ uf: 'CE', nome: 'Ceará' }] } };
    }
    if (url.startsWith('/api/bases/')) {
      return {
        base_id: 'fundeb-2024', ano_exercicio: 2024, descricao: 'Base 2024', situacao: 'Oficial',
        total_redes: 2, total_matriculas: 9500, grupos_disponiveis: [], avisos: [],
        parametros_referencia: { complementacao_vaaf: 1000, complementacao_vaat: 500, complementacao_vaar: 100 },
        pesos: [
          { etapa: 'creche_parcial', nome: 'Creche Parcial', peso_vaaf: 1.3, peso_vaat: 1.3 },
          { etapa: 'fundamental', nome: 'Fundamental', peso_vaaf: 1.0, peso_vaat: 1.0 }
        ]
      };
    }
    if (url.startsWith('/api/entes?')) {
      return { entes: Object.values(redesMock) };
    }
    const m = url.match(/\/api\/entes\/(\d+)\/matriculas/);
    if (m) {
      return JSON.parse(JSON.stringify(redesMock[Number(m[1])]));
    }
    return {};
  }
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('static/js/cenarios.js', 'utf8') + '\nwindow.__cen = cen;', sandbox);

(async () => {
  await sandbox.initCenario();
  const cen = sandbox.__cen;

  // Caso 1: Fortaleza em B (+100 -> 1100) e em C (+200 -> 1200)
  await sandbox.abrirEdicaoCenarioRede('B', 2304400);
  assert.strictEqual(elements['cen-form-titulo'].textContent, 'Editar matrículas — Cenário B');
  assert.strictEqual(elements['cen-btn-salvar-texto'].textContent, 'Salvar no cenário B');
  sandbox.registrarDefinicaoRascunho('creche_parcial', '1100');
  // Troca o seletor da UI para C enquanto B está aberto: salvar deve atualizar B (identidade capturada)
  elements['cen-cenario-alvo'].value = 'C';
  sandbox.salvarEdicaoAtiva();
  assert.strictEqual(cen.ajustesPorCenario.B.get('2304400|creche_parcial|definir').valor, 1100);
  assert.strictEqual(cen.ajustesPorCenario.C.size, 0);
  assert.strictEqual(JSON.stringify(sandbox.montarRequisicao().cenarios_ativos), '["B"]');

  // Edita Fortaleza em C (+200 -> 1200)
  await sandbox.abrirEdicaoCenarioRede('C', 2304400);
  assert.strictEqual(elements['cen-form-titulo'].textContent, 'Editar matrículas — Cenário C');
  assert.strictEqual(elements['cen-btn-salvar-texto'].textContent, 'Salvar no cenário C');
  sandbox.registrarDefinicaoRascunho('creche_parcial', '1200');
  sandbox.salvarEdicaoAtiva();
  assert.strictEqual(cen.ajustesPorCenario.B.get('2304400|creche_parcial|definir').valor, 1100);
  assert.strictEqual(cen.ajustesPorCenario.C.get('2304400|creche_parcial|definir').valor, 1200);
  assert.strictEqual(JSON.stringify(sandbox.montarRequisicao().cenarios_ativos), '["B","C"]');

  // Reabrir B recupera 1100 (+100) e Cancelar descarta alterações não salvas
  await sandbox.abrirEdicaoCenarioRede('B', 2304400);
  assert.strictEqual(cen.edicao.rascunho.get('2304400|creche_parcial|definir').valor, 1100);
  sandbox.registrarDefinicaoRascunho('creche_parcial', '1999');
  sandbox.cancelarEdicaoAtiva();
  assert.strictEqual(cen.ajustesPorCenario.B.get('2304400|creche_parcial|definir').valor, 1100);
  assert.strictEqual(cen.edicao.rascunho.get('2304400|creche_parcial|definir').valor, 1100);

  // Excluir cenário C durante edição impede salvamento e não transfere ajustes para B ou D
  await sandbox.abrirEdicaoCenarioRede('C', 2304400);
  sandbox.registrarDefinicaoRascunho('creche_parcial', '1500');
  sandbox.excluirCenarioSimulacao('C');
  assert.strictEqual(cen.edicao.excluidoDuranteEdicao, true);
  assert.strictEqual(elements['cen-btn-salvar-edicao'].disabled, true);
  sandbox.salvarEdicaoAtiva();
  assert.strictEqual(cen.ajustesPorCenario.C.size, 0);
  assert.strictEqual(cen.ajustesPorCenario.B.get('2304400|creche_parcial|definir').valor, 1100);
  assert.strictEqual(cen.ajustesPorCenario.D.size, 0);
  assert.ok(alertas.some(m => m.includes('excluído durante a edição')));
})();
"""
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
