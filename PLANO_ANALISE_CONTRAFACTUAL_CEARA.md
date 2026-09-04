# Plano de análise contrafactual do FUNDEB — municípios do Ceará

## Objetivo

Investigar, mantendo constante o número total de alunos de cada município, quais mudanças **educacionalmente válidas** na composição das matrículas entre etapas/modalidades alteram os recursos simulados do FUNDEB e quais configurações maximizam os repasses no modelo.

A análise deve separar claramente:

1. ótimo matemático;
2. ótimo educacionalmente factível;
3. políticas plausíveis, especialmente expansão real da educação em tempo integral.

> Os experimentos são contrafactuais. Os resultados não devem ser interpretados como recomendação para reclassificar artificialmente matrículas. Toda transformação factível deve corresponder a uma mudança real e válida da oferta educacional.

## Estrutura do simulador já identificada

O motor principal está em `simulador.py`, com fluxo aproximado:

`Matrículas → ponderação por etapa → NSE/fator socioeconômico → fator fiscal → fundos estaduais → equalização VAAF → redistribuição intraestadual → VAAT → VAAR → complementação da União → recursos FUNDEB`.

Funções relevantes já identificadas:

- `reescala_vetor`
- `pondera_matriculas_etapa`
- `pondera_matriculas_sociofiscal`
- `gera_fundo_estadual`
- `equaliza_fundo`
- `une_vaaf`
- `une_vaat`
- `simula_fundeb`

A lógica final contém aproximadamente:

```python
complemento_vaaf = recursos_vaaf_final - recursos_vaaf
complemento_vaat = recursos_vaat_final - recursos_vaat
complemento_uniao = complemento_vaar + complemento_vaat + complemento_vaaf
recursos_fundeb = recursos_vaaf + complemento_uniao
```

Consequência metodológica importante: **não estimar o impacto simplesmente multiplicando alunos pelos pesos**. Cada cenário deve executar novamente o motor completo, pois uma mudança em um município pode redistribuir recursos entre os demais entes.

## Dados disponíveis no repositório

O diretório `data/` contém:

- `cenario_atual.rda`
- `cenario_atual_agregada.rda`
- `cenario_ufs_atual.rda`
- `complementar.rda`
- `matriculas.rda`
- `pesos.rda`

Antes dos experimentos, inspecionar os objetos internos, dimensões, colunas, tipos, anos de referência, fontes e cobertura municipal.

**Não assumir o ano dos dados.** Os nomes dos arquivos não identificam explicitamente uma série temporal. Se existir apenas um snapshot, executar o estudo para esse snapshot e registrar a limitação.

## Pesos previamente recuperados

Foram recuperados do arquivo de pesos os seguintes valores relevantes, que devem ser novamente validados diretamente durante a execução:

| Modalidade | VAAF | VAAT |
|---|---:|---:|
| Creche pública integral | 1.50 | 1.80 |
| Creche pública parcial | 1.25 | 1.60 |
| Pré-escola pública integral | 1.40 | 1.75 |
| Pré-escola pública parcial | 1.15 | 1.50 |
| Fundamental tempo integral | 1.40 | 1.40 |
| Fundamental anos iniciais urbano | 1.00 | 1.00 |
| Fundamental anos finais urbano | 1.10 | 1.10 |
| Fundamental anos iniciais rural | 1.15 | 1.15 |
| Fundamental anos finais rural | 1.20 | 1.20 |

Hipóteses iniciais decorrentes apenas dos pesos:

- fundamental inicial urbano → integral: `1.00 → 1.40`, +40% de matrícula ponderada;
- fundamental final urbano → integral: `1.10 → 1.40`, aproximadamente +27,27%;
- creche parcial → integral: VAAF `1.25 → 1.50` (+20%) e VAAT `1.60 → 1.80` (+12,5%);
- pré-escola parcial → integral: VAAF `1.15 → 1.40` (+21,74%) e VAAT `1.50 → 1.75` (+16,67%).

Esses percentuais **não representam diretamente aumento de repasse**. O efeito financeiro final precisa ser obtido pelo simulador completo.

## Municípios selecionados

Analisar inicialmente dez municípios heterogêneos do Ceará:

1. Fortaleza
2. Caucaia
3. Maracanaú
4. Sobral
5. Juazeiro do Norte
6. Crato
7. Itapipoca
8. Maranguape
9. Quixadá
10. Iguatu

Os códigos IBGE devem ser identificados automaticamente nos dados, sem hardcode não verificado.

## Baseline

Executar o cenário `S0_BASELINE` sem alterações e armazenar, quando disponíveis/calculáveis:

- município e IBGE;
- total de matrículas;
- matrículas VAAF/VAAT ponderadas;
- recursos VAAF;
- complementos VAAF, VAAT e VAAR;
- complementação da União;
- recursos FUNDEB;
- VAAF e VAAT finais.

## Regra das simulações

Nas análises principais, manter o número total de alunos do município constante:

```python
matriculas[A] -= N
matriculas[B] += N
```

Garantir:

```python
assert total_antes == total_depois
assert todas_as_matriculas_sao_nao_negativas
```

## Transformações factíveis prioritárias

Testar separadamente:

- creche pública parcial → creche pública integral;
- pré-escola pública parcial → pré-escola pública integral;
- fundamental anos iniciais urbano → fundamental tempo integral;
- fundamental anos finais urbano → fundamental tempo integral.

A passagem para tempo integral deve ser interpretada como **expansão efetiva da oferta em tempo integral**, e não como simples alteração cadastral.

## Intensidade das transformações

Executar inicialmente 5%, 10%, 20%, 30% e 50% dos alunos elegíveis.

Depois realizar busca granular de `0%` a `100%`, em incrementos de 1 ponto percentual, para estudar:

- linearidade;
- retornos marginais;
- saturação;
- thresholds;
- pontos de inflexão decorrentes de VAAF/VAAT.

## Métricas

Para cada cenário e município calcular:

```text
R_base
R_cenario
delta_R = R_cenario - R_base
delta_R_percentual = 100 * delta_R / R_base
alunos_movidos
ganho_por_aluno = delta_R / alunos_movidos
```

Registrar também alterações em matrículas ponderadas VAAF/VAAT e nos componentes de complementação.

## Externalidades sobre os demais municípios

Toda alteração deve ser avaliada no sistema completo. Para cada cenário identificar:

- ganho do município-alvo;
- impacto nos demais municípios cearenses;
- cinco maiores beneficiados;
- cinco maiores prejudicados;
- soma dos recursos municipais do Ceará antes/depois.

Isso permitirá distinguir aumento de participação do município de mera redistribuição intrastadual.

## Otimização individual

Resolver, para cada município:

```text
maximize recursos_fundeb(municipio)
```

sujeito inicialmente a:

```text
total_matriculas_novo = total_matriculas_original
matricula_j >= 0
```

Produzir dois resultados distintos:

### ÓTIMO_MATEMÁTICO

Limite superior teórico, podendo explorar redistribuições amplas. Deve ser explicitamente marcado como potencialmente não factível do ponto de vista educacional.

### ÓTIMO_FACTÍVEL

Restrito a transformações educacionalmente plausíveis, especialmente parcial → integral dentro da etapa correspondente e transições para ensino fundamental integral quando compatíveis com os dados e regras aplicáveis.

Não permitir mudanças absurdas entre níveis apenas porque apresentam pesos maiores.

## Otimização conjunta dos dez municípios

Resolver também:

```text
maximize Σ recursos_fundeb(i), i ∈ municípios selecionados
```

com:

```text
G10 = Σ R_cenario_i - Σ R_base_i
```

Comparar ótimo individual e ótimo agregado para verificar se estratégias individualmente vantajosas apenas redistribuem recursos entre os dez ou aumentam sua participação conjunta relativamente ao restante do Ceará.

## Equidade / max-min

Investigar uma solução:

```text
maximize min(delta_R_percentual_i)
```

Comparar:

- ótimo individual;
- ótimo agregado;
- ótimo de equidade.

Se útil, construir uma fronteira de Pareto entre ganho agregado, distribuição dos ganhos e factibilidade.

## Sensibilidade marginal

Estimar numericamente:

```text
R(M + 1) - R(M)
```

para as principais transformações.

Investigar como o retorno marginal varia por município, tamanho da rede, modalidade e quantidade já convertida.

## Métrica econômica adicional

Além do ganho bruto do FUNDEB, uma extensão importante é comparar o incremento de recursos com o custo efetivo da expansão da oferta integral:

```text
ganho_liquido = FUNDEB_adicional - custo_incremental_da_politica
```

Essa análise é necessária antes de interpretar maior repasse como vantagem fiscal líquida.

## Estrutura proposta para os artefatos

```text
analises/fundeb_ceara/
├── README.md
├── metodologia.md
├── RESULTADOS.md
├── scripts/
│   ├── 01_inspecao_dados.py
│   ├── 02_baseline.py
│   ├── 03_cenarios_individuais.py
│   ├── 04_busca_percentual.py
│   ├── 05_otimizacao.py
│   └── 06_gerar_resultados.py
├── resultados/
│   ├── baseline.csv
│   ├── pesos.csv
│   ├── simulacoes.csv
│   ├── melhores_cenarios.csv
│   ├── impactos_outros_municipios.csv
│   └── otimizacao.csv
└── figuras/
```

## Gráficos mínimos

1. percentual convertido × variação de recursos FUNDEB;
2. município × ganho máximo percentual;
3. município × ganho por aluno convertido;
4. heatmap município × transformação usando `delta_R_percentual`;
5. externalidades da alteração de um município sobre os demais do Ceará;
6. recursos baseline × recursos no cenário ótimo.

## Tabela principal

| Município | Melhor transformação | % convertido | Alunos | Base R$ | Novo R$ | Δ R$ | Δ % | R$/aluno |
|---|---|---:|---:|---:|---:|---:|---:|---:|

Gerar rankings por:

- maior ganho absoluto;
- maior ganho percentual;
- maior ganho por aluno alterado;
- transformação mais eficiente.

## Validação e testes

Utilizar `validacao.py` quando aplicável e verificar:

- conservação das matrículas brutas nos cenários de redistribuição;
- ausência de matrículas negativas;
- consistência dos recursos FUNDEB;
- VAAF e VAAT;
- conservação/redistribuição dos fundos conforme as regras implementadas.

Executar a suíte existente com `pytest` e adicionar testes para as novas rotinas.

## Reprodutibilidade

Registrar:

- versão Python;
- dependências;
- commit analisado;
- dataset;
- ano de referência quando identificado;
- parâmetros;
- seed, se houver procedimento estocástico;
- número de cenários;
- tempo total e médio de execução.

Idealmente todo o estudo deve ser reproduzível com um único comando.

## Hipóteses científicas

Hipótese principal:

> A expansão efetiva da educação em tempo integral aumenta a participação relativa de determinados municípios nos recursos distribuídos pelo FUNDEB, mas a magnitude do efeito depende da estrutura municipal de matrículas e dos mecanismos redistributivos VAAF/VAAT.

Hipóteses adicionais:

- municípios de diferentes portes apresentam respostas percentuais diferentes à mesma alteração relativa;
- o ganho pode não ser linear devido aos mecanismos de equalização;
- podem existir thresholds e pontos de inflexão;
- a estratégia que maximiza um município pode não maximizar conjuntamente um grupo de municípios.

## Análise temporal

Se os arquivos contiverem vários anos, repetir o protocolo por ano e avaliar estabilidade das estratégias.

Se houver somente um snapshot, não construir artificialmente uma série temporal. Registrar a limitação e indicar os dados adicionais necessários.

## Potencial artigo

Título provisório:

**Impacto da composição das matrículas escolares sobre as transferências do FUNDEB: uma análise contrafactual de municípios cearenses**

Possível contribuição:

> Desenvolver uma abordagem computacional para quantificar efeitos redistributivos decorrentes de alterações contrafactuais na composição das matrículas municipais, considerando conjuntamente fatores de ponderação e os mecanismos VAAF, VAAT e VAAR do FUNDEB.

## Critério de conclusão

A análise não termina com a criação dos scripts. É necessário:

1. executar efetivamente as simulações;
2. gerar CSVs e gráficos;
3. validar os resultados;
4. gerar `RESULTADOS.md` com números provenientes diretamente dos experimentos;
5. identificar ótimo matemático e ótimo factível;
6. medir externalidades sobre os demais municípios;
7. documentar limitações e eventuais problemas encontrados no simulador.
