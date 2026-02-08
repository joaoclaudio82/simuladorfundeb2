/**
 * Modulo de explicacao dos resultados municipais
 */
function renderExplicacao(orig, ajust) {
  var container = document.querySelector('#mun-explicacao');
  var munData = state.municipioMatriculas;
  if (!munData) return;
  var html = '';
  var alteracoes = [];
  var ajustados = getMatriculasAjustadas();
  for (var etapa in ajustados) {
    var novoValor = ajustados[etapa];
    var originalValor = (munData.matriculas && munData.matriculas[etapa]) ? munData.matriculas[etapa] : 0;
    var diffA = novoValor - originalValor;
    if (Math.abs(diffA) > 0.5) {
      var nomeEtapa = (state.etapas && state.etapas[etapa]) ? state.etapas[etapa] : etapa.replace(/_/g, ' ');
      var pctAlt = originalValor > 0 ? (diffA / originalValor * 100) : (novoValor > 0 ? 100 : 0);
      alteracoes.push({ etapa: etapa, nome: nomeEtapa, original: originalValor, novo: novoValor, diff: diffA, pct: pctAlt });
    }
  }
  html += '<div class="explicacao-section"><h6><i class="fas fa-pencil-alt"></i> Alterações Realizadas</h6>';
  if (alteracoes.length === 0) {
    html += '<p class="text-muted">Nenhuma alteração nas matrículas foi realizada. Os resultados refletem os parâmetros atuais.</p>';
  } else {
    html += '<div class="explicacao-alteracoes">';
    for (var i = 0; i < alteracoes.length; i++) {
      var a = alteracoes[i]; var tipo = a.diff > 0 ? 'aumento' : 'reducao'; var sinal = a.diff > 0 ? '+' : '';
      html += '<div class="alteracao-item ' + tipo + '"><span class="alteracao-nome">' + a.nome + '</span><span class="alteracao-de">' + Math.round(a.original) + '</span><span class="alteracao-seta"><i class="fas fa-arrow-right"></i></span><span class="alteracao-para ' + tipo + '">' + Math.round(a.novo) + '</span><span class="alteracao-pct ' + tipo + '">' + sinal + a.pct.toFixed(1) + '%</span></div>';
    }
    html += '</div>';
  }
  html += '</div>';

  var difMatVaaf = ajust.matriculas_vaaf - orig.matriculas_vaaf;
  var difMatVaat = ajust.matriculas_vaat - orig.matriculas_vaat;
  var pctMatVaaf = orig.matriculas_vaaf ? (difMatVaaf / orig.matriculas_vaaf * 100) : 0;
  var pctMatVaat = orig.matriculas_vaat ? (difMatVaat / orig.matriculas_vaat * 100) : 0;
  html += '<div class="explicacao-section"><h6><i class="fas fa-weight-hanging"></i> Impacto nas Matrículas Ponderadas</h6>';
  html += _resultRow('Matrículas VAAF (ponderadas)', orig.matriculas_vaaf, ajust.matriculas_vaaf, difMatVaaf, pctMatVaaf, false);
  html += _resultRow('Matrículas VAAT (ponderadas)', orig.matriculas_vaat, ajust.matriculas_vaat, difMatVaat, pctMatVaat, false);
  if (alteracoes.length > 0) {
    var temAum = alteracoes.some(function(x) { return x.diff > 0; });
    var temRed = alteracoes.some(function(x) { return x.diff < 0; });
    html += '<div class="explicacao-mecanismo"><strong>Como funciona:</strong> As matrículas brutas de cada modalidade são multiplicadas pelos <strong>pesos VAAF e VAAT</strong>. ';
    if (temAum && !temRed) html += 'O <strong>aumento</strong> resultou em mais alunos ponderados, aumentando a participação do município na distribuição de recursos.';
    else if (!temAum && temRed) html += 'A <strong>redução</strong> resultou em menos alunos ponderados, diminuindo a participação do município.';
    else html += 'As alterações combinadas modificaram o total de alunos ponderados do município.';
    html += ' O fator socioeconômico (NSE) e o fator de recursos vinculados (NF) também são aplicados.</div>';
  }
  html += '</div>';

  var difVaafFin = ajust.vaaf_final - orig.vaaf_final;
  var pctVaafFin = orig.vaaf_final ? (difVaafFin / orig.vaaf_final * 100) : 0;
  var oRVF = orig.recursos_vaaf_final || 0, aRVF = ajust.recursos_vaaf_final || 0;
  var difRVF = aRVF - oRVF, pctRVF = oRVF ? (difRVF / oRVF * 100) : 0;
  var difCVaaf = ajust.complemento_vaaf - orig.complemento_vaaf;
  var pctCVaaf = orig.complemento_vaaf ? (difCVaaf / orig.complemento_vaaf * 100) : 0;
  html += '<div class="explicacao-section"><h6><i class="fas fa-chart-bar"></i> Impacto no VAAF (Valor Aluno Ano Fundeb)</h6>';
  html += _resultRow('VAAF por aluno', orig.vaaf_final, ajust.vaaf_final, difVaafFin, pctVaafFin, false);
  html += _resultRow('Recursos VAAF totais', oRVF, aRVF, difRVF, pctRVF, true);
  html += _resultRow('Complementação VAAF', orig.complemento_vaaf, ajust.complemento_vaaf, difCVaaf, pctCVaaf, true);
html += '<div class="explicacao-mecanismo"><strong>Mecanismo VAAF:</strong> A complementação VAAF equaliza os <strong>fundos estaduais</strong> (27 fundos, um por UF). ';
    if (Math.abs(pctMatVaaf) > 0.01) {
    if (difMatVaaf > 0) html += 'Com o aumento de matrículas, o município representa uma <strong>fatia maior</strong> do fundo estadual de ' + orig.uf + '. Mais recursos VAAF, embora o valor por aluno possa ' + (difVaafFin >= 0 ? 'manter-se estável.' : 'cair levemente.');
    else html += 'Com a redução, o município representa uma <strong>fatia menor</strong> do fundo estadual de ' + orig.uf + '. Menos recursos VAAF totais, embora o valor por aluno possa aumentar.';
  } else html += 'Sem alteração significativa nas matrículas, o VAAF permanece praticamente inalterado.';
  html += ' Os demais municípios do estado são afetados inversamente.</div></div>';

  var difVaatFin = ajust.vaat_final - orig.vaat_final;
  var pctVaatFin = orig.vaat_final ? (difVaatFin / orig.vaat_final * 100) : 0;
  var oRVT = orig.recursos_vaat_final || 0, aRVT = ajust.recursos_vaat_final || 0;
  var difRVT = aRVT - oRVT, pctRVT = oRVT ? (difRVT / oRVT * 100) : 0;
  var difCVaat = ajust.complemento_vaat - orig.complemento_vaat;
  var pctCVaat = orig.complemento_vaat ? (difCVaat / orig.complemento_vaat * 100) : 0;
  html += '<div class="explicacao-section"><h6><i class="fas fa-chart-line"></i> Impacto no VAAT (Valor Aluno Ano Total)</h6>';
  html += _resultRow('VAAT por aluno', orig.vaat_final, ajust.vaat_final, difVaatFin, pctVaatFin, false);
  html += _resultRow('Recursos VAAT totais', oRVT, aRVT, difRVT, pctRVT, true);
  html += _resultRow('Complementação VAAT', orig.complemento_vaat, ajust.complemento_vaat, difCVaat, pctCVaat, true);
html += '<div class="explicacao-mecanismo"><strong>Mecanismo VAAT:</strong> A complementação VAAT equaliza os <strong>entes individuais</strong> (~5.570) em âmbito nacional. ';
    if (Math.abs(pctMatVaat) > 0.01) {
    if (difMatVaat > 0) {
      html += 'Com mais matrículas, o VAAT pré-complementação ';
      html += (ajust.vaat_pre || 0) < (orig.vaat_pre || 0) ? '<strong>diminui</strong> (mais alunos dividindo mesmos recursos). ' : 'permanece estável. ';
      html += 'O aumento pode resultar em <strong>mais recursos da União</strong>.';
    } else html += 'Com menos matrículas, o VAAT pré-complementação tende a <strong>aumentar</strong>, mas o município pode receber <strong>menos recursos totais</strong>.';
  } else html += 'Sem alteração significativa, o VAAT permanece praticamente inalterado.';
  html += '</div></div>';

  var difCVaar = ajust.complemento_vaar - orig.complemento_vaar;
  var pctCVaar = orig.complemento_vaar ? (difCVaar / orig.complemento_vaar * 100) : 0;
  html += '<div class="explicacao-section"><h6><i class="fas fa-award"></i> Impacto no VAAR (Valor Aluno Ano Resultado)</h6>';
  html += _resultRow('Complementação VAAR', orig.complemento_vaar, ajust.complemento_vaar, difCVaar, pctCVaar, true);
html += '<div class="explicacao-mecanismo"><strong>Mecanismo VAAR:</strong> Distribuída pelo <strong>peso VAAR</strong> de cada ente (indicadores educacionais). ';
    if (Math.abs(difCVaar) < 1) html += 'Como o peso VAAR não muda com matrículas, a complementação VAAR <strong>permanece inalterada</strong>. Só muda com o montante total.';
    else html += 'A variação reflete a mudança no montante total da VAAR.';
  html += '</div></div>';

  var difFundeb = ajust.recursos_fundeb - orig.recursos_fundeb;
  var pctFundeb = orig.recursos_fundeb ? (difFundeb / orig.recursos_fundeb * 100) : 0;
  var difCT = ajust.complemento_uniao - orig.complemento_uniao;
  var pctCT = orig.complemento_uniao ? (difCT / orig.complemento_uniao * 100) : 0;
  html += '<div class="explicacao-section"><h6><i class="fas fa-calculator"></i> Resultado Final</h6>';
  html += _resultRow('Total Complementação da União', orig.complemento_uniao, ajust.complemento_uniao, difCT, pctCT, true);
  html += _resultRow('Recursos FUNDEB Totais', orig.recursos_fundeb, ajust.recursos_fundeb, difFundeb, pctFundeb, true);
  html += '</div>';
  html += '<div class="explicacao-resumo">' + _resumoNarrativo(orig, ajust, alteracoes) + '</div>';
  container.innerHTML = html;
}

function _resultRow(label, valorOrig, valorNovo, diff, pct, isMoeda) {
  var classe = Math.abs(diff) < 0.01 ? 'neutro' : (diff > 0 ? 'positivo' : 'negativo');
  var sn = diff > 0 ? '+' : '';
  var fn = isMoeda ? fmt.moeda : fmt.numero;
  return '<div class="explicacao-resultado ' + classe + '"><span class="resultado-label">' + label + '</span><span class="resultado-original">' + fn(valorOrig) + '</span><span class="resultado-seta"><i class="fas fa-arrow-right"></i></span><span class="resultado-novo">' + fn(valorNovo) + '</span><span class="resultado-dif">' + sn + pct.toFixed(2) + '%</span></div>';
}

function _resumoNarrativo(orig, ajust, alteracoes) {
  var difFundeb = ajust.recursos_fundeb - orig.recursos_fundeb;
  var pctFundeb = orig.recursos_fundeb ? (difFundeb / orig.recursos_fundeb * 100) : 0;
  var destaque = pctFundeb >= 0 ? 'destaque-positivo' : 'destaque-negativo';
  var texto = '<strong>Resumo para ' + orig.nome + ' (' + orig.uf + '):</strong> ';
  if (alteracoes.length === 0) return texto + 'Nenhuma alteracao de matriculas foi realizada. Os valores refletem os parametros atuais.';
  var numAum = alteracoes.filter(function(x) { return x.diff > 0; }).length;
  var numRed = alteracoes.filter(function(x) { return x.diff < 0; }).length;
  if (numAum > 0 && numRed === 0) texto += 'Foi realizado o <strong>aumento de matrículas</strong> em ' + numAum + ' modalidade(s). ';
  else if (numRed > 0 && numAum === 0) texto += 'Foi realizada a <strong>redução de matrículas</strong> em ' + numRed + ' modalidade(s). ';
  else texto += 'Foram realizadas alterações em ' + alteracoes.length + ' modalidade(s). ';
  texto += 'Como resultado, os recursos totais do FUNDEB passaram de ' + fmt.moeda(orig.recursos_fundeb) + ' para <span class="' + destaque + '">' + fmt.moeda(ajust.recursos_fundeb) + '</span> (<span class="' + destaque + '">' + (pctFundeb >= 0 ? '+' : '') + pctFundeb.toFixed(2) + '%</span>). ';
  var difMV = ajust.matriculas_vaaf - orig.matriculas_vaaf;
  if (Math.abs(difMV) > 0.5) {
    if (difMV > 0) texto += 'O aumento nas matrículas ponderadas fez o município ter <strong>participação maior</strong> no fundo estadual (VAAF) e na equalização nacional (VAAT). ';
    else texto += 'A redução nas matrículas diminuiu a <strong>participação do município</strong> no fundo estadual e equalização nacional. ';
  }
  var difVF = ajust.vaat_final - orig.vaat_final;
  if (Math.abs(difVF) > 0.5) {
    if (difVF < 0) texto += 'O <strong>valor por aluno (VAAT)</strong> diminuiu levemente - esperado com mais alunos compartilhando recursos. ';
    else texto += 'O <strong>valor por aluno (VAAT)</strong> aumentou, refletindo proporção mais favorável. ';
  }
  texto += 'Esta alteração também <strong>afeta os demais entes</strong> do estado, pois o fundo estadual VAAF é dividido proporcionalmente.';
  return texto;
}
