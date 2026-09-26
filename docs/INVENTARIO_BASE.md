# Inventário das bases

Gerado por `scripts/inventario_base.py`. Não editar à mão.

A reprodução do cenário de referência e a validação interna não substituem a comparação com os valores oficiais. Tolerâncias usadas são provisórias (FND-02).

## `fundeb-2026` — exercício 2026

- Situação: preliminar · homologada: não
- Receita: Receita total prevista do Fundeb 2026 (publicação 2026-04-29)
- Ponderador: NSE e DREC oficiais

| Papel | Arquivo de origem | SHA-256 |
|---|---|---|
| matriculas | `20252026/Matrículas Fundeb 2026.xlsx` | `91279d7dbd2b87b5…` |
| receita | `20252026/1-receita-total-do-fundeb-por-ente-federado.xlsx` | `d4679c9c3004383f…` |
| nse | `20252026/ponderador-de-nivel-socioeconomico.xlsx` | `8e95aa2b9eb285d4…` |
| drec | `20252026/ponderador-de-disponibilidade-de-recursos.xlsx` | `1d5d34a2926f59fb…` |
| vaat | `20252026/MemriadeClculoVAAT2026 (2).xlsx` | `910fad0c111c81cc…` |
| inabilitados_vaat | `20252026/ListadosenteshabilitadoseinabilitadosaoVAAT2026Posicaofinalcomajustededecisaojudicial.xlsm` | `b61af6bc759c9548…` |

**Cobertura e cadastro**

- Entes: 5596 (rede municipal: 5569, rede estadual: 26, rede do Distrito Federal: 1)
- Identificadores duplicados: nenhum; matrículas e receitas cobrem o mesmo conjunto de entes
- Categorias de matrícula: 319; contagens não inteiras: não
- Redes inabilitadas para VAAT: 25 (estaduais/DF: MG)
- Redes com `recursos_vaat` igual a zero: 24
- Complementações de referência: VAAF R$ 30,125 bi, VAAT R$ 31,631 bi, VAAR R$ 7,531 bi

**Reprodução do cenário de referência** (`cenario_atual`): maior diferença por ente em recursos do Fundeb = R$ 0,00; validação interna: ok.
Nos exercícios 2025 e 2026 o `cenario_atual` é produzido pelo próprio motor com os dados oficiais; por isso a comparação com os valores oficiais abaixo é a que importa.

**Comparação com os valores oficiais por ente** (planilha de receita do exercício)

| Indicador | Total simulado (R$ bi) | Total oficial (R$ bi) | Maior diferença por ente (R$) | Entes acima de R$ 1.000 | Recebem só na simulação | Recebem só no oficial |
|---|---|---|---|---|---|---|
| Contribuição de estados e municípios | 301,249 | 301,249 | 31.924.280,71 | 1061 | 0 | 0 |
| Complementação VAAF | 30,125 | 30,125 | 20.877.822,02 | 1765 | 0 | 0 |
| Complementação VAAT | 31,631 | 31,631 | 18.020.774,90 | 2549 | 3 | 1 |
| Complementação VAAR | 7,531 | 7,531 | 0,00 | 0 | 0 | 0 |
| Recursos totais do Fundeb | 370,537 | 370,537 | 52.802.102,73 | 2654 | 0 | 0 |

UFs acima da tolerância provisória (0.5%): PE, PB

| UF | Desvio absoluto nos recursos do Fundeb (% do oficial) | Complementação VAAF: simulado − oficial (%) |
|---|---|---|
| PE | 0,389 | -2,942 |
| BA | 0,222 | 0,069 |
| PB | 0,109 | 0,623 |
| AM | 0,109 | 0,233 |
| PA | 0,086 | 0,171 |
| MA | 0,075 | 0,152 |
| CE | 0,074 | 0,179 |
| PI | 0,073 | 0,229 |

Maiores diferenças por ente (recursos do Fundeb):

| UF | Ente | IBGE | Simulado (R$) | Oficial (R$) | Diferença (%) |
|---|---|---|---|---|---|
| PE | Pernambuco | 26 | 4.835.354.594 | 4.888.156.697 | -1,08 |
| BA | CANAVIEIRAS | 2906303 | 43.401.303 | 61.394.393 | -29,31 |
| BA | TANHACU | 2931004 | 74.682.826 | 86.446.944 | -13,61 |
| BA | MANOEL VITORINO | 2920403 | 43.370.046 | 48.749.856 | -11,04 |
| AM | BENJAMIN CONSTANT | 1300607 | 192.574.327 | 196.890.397 | -2,19 |
| BA | Bahia | 29 | 6.228.642.551 | 6.224.669.487 | 0,06 |
| BA | PARIPIRANGA | 2923803 | 53.702.781 | 57.675.480 | -6,89 |
| MA | Maranhão | 21 | 4.030.734.070 | 4.027.141.425 | 0,09 |

Entes com elegibilidade VAAT divergente (recebem em um lado e não no outro):

- TO ITAGUATINS (1710706): inabilitado na base = False; simulado R$ 1.916,96; oficial R$ 0,00
- BA CANAVIEIRAS (2906303): inabilitado na base = True; simulado R$ 0,00; oficial R$ 18.020.774,90
- PR NOVA LONDRINA (4117107): inabilitado na base = False; simulado R$ 4.905,52; oficial R$ 0,00
- MT SAO JOSE DOS QUATRO MARCOS (5107107): inabilitado na base = False; simulado R$ 5.290,24; oficial R$ 0,00

## `fundeb-2025` — exercício 2025

- Situação: definitiva · homologada: não
- Receita: Ajuste anual das receitas efetivas de 2025 (publicação 2026-04-29)
- Ponderador: NSE e DREC oficiais

| Papel | Arquivo de origem | SHA-256 |
|---|---|---|
| matriculas | `20252026/Matrículas Fundeb 2025 e 2026.xlsx` | `c15893c9d7dbc328…` |
| receita | `20252026/1-receita-total-do-fundeb-por-ente-federado-2025.xlsx` | `919d1d4ce58d5953…` |
| nse | `20252026/PonderadorNSEFundeb2025.pdf` | `305867d1b3b3550d…` |
| drec | `20252026/PonderadorDRecFundeb2025.pdf` | `699b5d73bbd2b457…` |
| vaat | `20252026/Receita STN 2023 VAAT 2025 para publicação.xlsx` | `e9ae32f9d07afad3…` |

**Cobertura e cadastro**

- Entes: 5595 (rede municipal: 5568, rede estadual: 26, rede do Distrito Federal: 1)
- Identificadores duplicados: nenhum; matrículas e receitas cobrem o mesmo conjunto de entes
- Categorias de matrícula: 319; contagens não inteiras: sim
- Redes inabilitadas para VAAT: 0 (estaduais/DF: nenhuma)
- Redes com `recursos_vaat` igual a zero: 0
- Complementações de referência: VAAF R$ 26,675 bi, VAAT R$ 24,509 bi, VAAR R$ 5,092 bi

**Reprodução do cenário de referência** (`cenario_atual`): maior diferença por ente em recursos do Fundeb = R$ 0,00; validação interna: ok.
Nos exercícios 2025 e 2026 o `cenario_atual` é produzido pelo próprio motor com os dados oficiais; por isso a comparação com os valores oficiais abaixo é a que importa.

**Comparação com os valores oficiais por ente** (planilha de receita do exercício)

| Indicador | Total simulado (R$ bi) | Total oficial (R$ bi) | Maior diferença por ente (R$) | Entes acima de R$ 1.000 | Recebem só na simulação | Recebem só no oficial |
|---|---|---|---|---|---|---|
| Contribuição de estados e municípios | 282,525 | 282,525 | 0,31 | 0 | 0 | 0 |
| Complementação VAAF | 26,675 | 26,675 | 0,05 | 0 | 0 | 0 |
| Complementação VAAT | 24,509 | 24,509 | 19.026.993,57 | 2383 | 9 | 2 |
| Complementação VAAR | 5,092 | 5,092 | 0,00 | 0 | 0 | 0 |
| Recursos totais do Fundeb | 338,802 | 338,802 | 19.026.993,56 | 2383 | 0 | 0 |

UFs acima da tolerância provisória (0.5%): AP

| UF | Desvio absoluto nos recursos do Fundeb (% do oficial) | Complementação VAAF: simulado − oficial (%) |
|---|---|---|
| AP | 0,502 | n/a |
| PR | 0,065 | n/a |
| MA | 0,034 | 0,000 |
| SP | 0,031 | n/a |
| CE | 0,029 | -0,000 |
| PA | 0,025 | -0,000 |
| BA | 0,025 | 0,000 |
| AL | 0,025 | -0,000 |

Maiores diferenças por ente (recursos do Fundeb):

| UF | Ente | IBGE | Simulado (R$) | Oficial (R$) | Diferença (%) |
|---|---|---|---|---|---|
| SP | CUBATAO | 3513504 | 128.892.191 | 109.865.197 | 17,32 |
| PR | PINHAO | 4119301 | 33.771.525 | 27.209.829 | 24,12 |
| AP | OIAPOQUE | 1600501 | 50.531.491 | 44.147.291 | 14,46 |
| PR | CIDADE GAUCHA | 4105607 | 15.624.776 | 12.104.941 | 29,08 |
| AP | CALCOENE | 1600204 | 19.538.091 | 17.049.236 | 14,60 |
| MA | Maranhão | 21 | 3.116.181.738 | 3.117.512.364 | -0,04 |
| CE | FORTALEZA | 2304400 | 2.082.450.336 | 2.083.460.339 | -0,05 |
| GO | CAMPO ALEGRE DE GOIAS | 5204805 | 7.854.211 | 7.005.226 | 12,12 |

Entes com elegibilidade VAAT divergente (recebem em um lado e não no outro):

- AP CALCOENE (1600204): inabilitado na base = False; simulado R$ 2.488.854,65; oficial R$ 0,00
- AP CUTIAS (1600212): inabilitado na base = False; simulado R$ 776.902,03; oficial R$ 0,00
- AP OIAPOQUE (1600501): inabilitado na base = False; simulado R$ 6.384.200,12; oficial R$ 0,00
- MG RUBIM (3156601): inabilitado na base = False; simulado R$ 0,00; oficial R$ 266,62
- SP CUBATAO (3513504): inabilitado na base = False; simulado R$ 19.026.993,57; oficial R$ 0,00
- SP TAGUAI (3553005): inabilitado na base = False; simulado R$ 0,00; oficial R$ 2.680,02
- PR CIDADE GAUCHA (4105607): inabilitado na base = False; simulado R$ 3.519.835,44; oficial R$ 0,00
- PR LUNARDELLI (4113759): inabilitado na base = False; simulado R$ 391.729,17; oficial R$ 0,00
- PR PINHAO (4119301): inabilitado na base = False; simulado R$ 6.561.695,52; oficial R$ 0,00
- PR ROSARIO DO IVAI (4122651): inabilitado na base = False; simulado R$ 349.387,22; oficial R$ 0,00
- GO CAMPO ALEGRE DE GOIAS (5204805): inabilitado na base = False; simulado R$ 848.985,22; oficial R$ 0,00

## `fundeb-2024` — exercício 2024

- Situação: legado · homologada: não
- Receita: não informado
- Ponderador: NSE e NF

| Papel | Arquivo de origem | SHA-256 |
|---|---|---|
| matriculas | `data/matriculas.rda` | `cc10ff4af4629524…` |
| complementar | `data/complementar.rda` | `d8e31655dc7d8eeb…` |
| pesos | `data/pesos.rda` | `3aff131e5e90c4a9…` |
| referencia | `data/cenario_atual.rda` | `d77dc7bd6725e39c…` |
| nse | `PonderadorNSE 2024.pdf` | `49aff1e4456faffb…` |

**Cobertura e cadastro**

- Entes: 5595 (rede municipal: 5568, rede estadual: 26, rede do Distrito Federal: 1)
- Identificadores duplicados: nenhum; matrículas e receitas cobrem o mesmo conjunto de entes
- Categorias de matrícula: 41; contagens não inteiras: sim
- Redes inabilitadas para VAAT: 94 (estaduais/DF: AL, DF, MG, RJ, RN, RR, RS)
- Redes com `recursos_vaat` igual a zero: 0
- Complementações de referência: VAAF R$ 24,153 bi, VAAT R$ 18,115 bi, VAAR R$ 0,000 bi

**Reprodução do cenário de referência** (`cenario_atual`): maior diferença por ente em recursos do Fundeb = R$ 0,02; validação interna: ok.

**Comparação com valores oficiais:** indisponível (base sem valores oficiais por ente).

