/* Histórico usa resultados armazenados; abrir/baixar nunca envia uma nova simulação. */
'use strict';
const historyPage = { offset: 0, limit: 25 };
const historyEl = id => document.getElementById(id);
const historyMoney = n => n == null ? '—' : Number(n).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
function historyCell(row, text) {
  const cell = document.createElement('td');
  cell.textContent = text == null ? '—' : String(text);
  row.append(cell);
  return cell;
}
function historyLink(parent, text, href) {
  const a = document.createElement('a'); a.textContent = text; a.href = href;
  a.className = 'me-3'; parent.append(a); return a;
}
async function showSavedScenario(id) {
  try {
    const data = await apiFetch(`/api/cenarios/${encodeURIComponent(id)}`);
    historyEl('history-result').hidden = false;
    historyEl('result-info').textContent = `${data.metadados.base.base_id} · ${new Date(data.metadados.criado_em).toLocaleString('pt-BR')} · ${data.comparacao.recorte.descricao}`;
    historyEl('result-warning').textContent = data.metadados.aviso;
    const exports = historyEl('result-exports'); exports.replaceChildren();
    for (const format of ['csv', 'xlsx', 'pdf']) {
      historyLink(exports, `Baixar ${format.toUpperCase()}`, `/api/cenarios/${encodeURIComponent(id)}/exportar?formato=${format}`);
    }
    const rows = historyEl('result-rows'); rows.replaceChildren();
    for (const line of data.comparacao.linhas) {
      const row = document.createElement('tr');
      [line.uf, line.nome, historyMoney(line.recursos_fundeb_A), historyMoney(line.recursos_fundeb_B),
        historyMoney(line.recursos_fundeb_dif_B_A), line.recursos_fundeb_pct_B_A == null ? '—' : `${line.recursos_fundeb_pct_B_A.toLocaleString('pt-BR')}%`]
        .forEach(value => historyCell(row, value));
      rows.append(row);
    }
    historyEl('history-result').scrollIntoView({ behavior: 'smooth' });
  } catch (error) { historyEl('history-status').textContent = error.message; }
}
async function loadHistory() {
  historyEl('history-status').textContent = 'Carregando…';
  try {
    const data = await apiFetch(`/api/historico?limit=${historyPage.limit}&offset=${historyPage.offset}`);
    const entries = [
      ...data.cenarios.map(item => ({ ...item, kind: 'scenario' })),
      ...data.simulacoes_legadas.map(item => ({ ...item, kind: 'legacy' }))
    ].sort((a, b) => b.created_at.localeCompare(a.created_at));
    const rows = historyEl('history-rows'); rows.replaceChildren();
    for (const item of entries) {
      const row = document.createElement('tr');
      historyCell(row, new Date(item.created_at).toLocaleString('pt-BR'));
      historyCell(row, item.kind === 'scenario' ? (item.request_json.descricao || `Cenário ${item.id.slice(0, 8)}`) : `Simulação ${item.id.slice(0, 8)}`);
      historyCell(row, item.base_id || item.path);
      const actions = historyCell(row, '');
      if (item.kind === 'scenario') {
        const button = document.createElement('button'); button.className = 'btn btn-sm btn-outline-primary';
        button.textContent = 'Abrir resultado'; button.addEventListener('click', () => showSavedScenario(item.id));
        actions.append(button);
      } else {
        historyLink(actions, 'Resultado JSON', `/api/historico/legado/${encodeURIComponent(item.id)}`);
        historyLink(actions, 'Baixar dados completos', `/api/historico/legado/${encodeURIComponent(item.id)}/snapshot`);
      }
      rows.append(row);
    }
    historyEl('history-status').textContent = entries.length ? `Página ${1 + historyPage.offset / historyPage.limit}` : 'Nenhuma simulação nesta página.';
    historyEl('history-prev').disabled = historyPage.offset === 0;
    historyEl('history-next').disabled = data.cenarios.length < historyPage.limit && data.simulacoes_legadas.length < historyPage.limit;
  } catch (error) { historyEl('history-status').textContent = error.message; }
}
historyEl('history-prev').addEventListener('click', () => { historyPage.offset = Math.max(0, historyPage.offset - historyPage.limit); loadHistory(); });
historyEl('history-next').addEventListener('click', () => { historyPage.offset += historyPage.limit; loadHistory(); });
guardAuth().then(loadHistory).catch(error => { historyEl('history-status').textContent = error.message; });
