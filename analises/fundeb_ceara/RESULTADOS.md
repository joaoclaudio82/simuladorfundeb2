# Resultados: composição das matrículas e transferências do FUNDEB no Ceará

Estudo contrafactual. Os números abaixo foram lidos diretamente dos CSVs em `resultados/`.
Não se trata de recomendação para reclassificar alunos.

## 1. Dados utilizados

| Ano | Entes | Etapas | Municípios CE | Ponderador | VAAF União | VAAT União | VAAR União | Fonte |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 2024 | 5595 | 41 | 184 | nf | R$ 24.153.287.047,00 | R$ 18.114.965.285,00 | R$ 0,00 | data/*.rda + PonderadorNSE 2024.pdf |
| 2025 | 5595 | 319 | 184 | drec | R$ 26.675.375.783,98 | R$ 24.509.321.488,13 | R$ 5.092.263.767,54 | 20252026/ planilhas oficiais + cache data/{ano}/ |
| 2026 | 5596 | 319 | 184 | drec | R$ 30.124.926.956,49 | R$ 31.631.173.304,31 | R$ 7.531.231.739,12 | 20252026/ planilhas oficiais + cache data/{ano}/ |

## 2. Ano identificado

Os arquivos `data/*.rda` **não trazem o ano no nome**. A identificação de **2024** baseia-se em: (i) `carregar_dataset_2024()` em `dados/fundeb_dataset.py`; (ii) `PonderadorNSE 2024.pdf`; (iii) montantes-padrão de complementação da União usados no dataset legado; (iv) documentação do próprio repositório (`manual-do-sistema.md`, `README.md`). Os exercícios **2025** e **2026** vêm das planilhas em `20252026/`, filtradas pela coluna de ano quando ela existe.

Há três snapshots, não uma série construída artificialmente. Cada exercício foi simulado por completo com o motor `simula_fundeb`.

## 3. Metodologia

Para cada cenário, as matrículas de um (ou dez) município(s) são alteradas conservando o total de alunos e a não-negatividade. O motor completo do FUNDEB é reexecutado sobre todos os entes. O baseline `S0_BASELINE` usa pesos, NSE/DREC e montantes oficiais, com `max_nse=min_nse=max_nf=min_nf=1.0` — o mesmo critério do cenário de referência dos exercícios 2025/2026. Em 2024 isso achata o NF para 1 após o reescalonamento interno do motor; o NSE oficial permanece. A validação interna (`validar_interno`, RF-10) roda após cada simulação.

Transições factíveis detectadas:

| ano | codigo | origem | destino | peso_vaaf_origem | peso_vaaf_destino | peso_vaat_origem | peso_vaat_destino |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | A | creche_parcial_rede_publica | creche_integral_rede_publica | 1.2500 | 1.5000 | 1.6000 | 1.8000 |
| 2024 | B | pre_escola_parcial_rede_publica | pre_escola_integral_rede_publica | 1.1500 | 1.4000 | 1.5000 | 1.7500 |
| 2024 | C | ens_fundamental_series_iniciais_urbano_rede_publica | ens_fundamental_integral_rede_publica | 1.0000 | 1.4000 | 1.0000 | 1.4000 |
| 2024 | D | ens_fundamental_series_finais_urbano_rede_publica | ens_fundamental_integral_rede_publica | 1.1000 | 1.4000 | 1.1000 | 1.4000 |
| 2025 | A | creche_parcial_publica | creche_integral_publica | 1.2500 | 1.5500 | 1.6000 | 1.9000 |
| 2025 | B | pre_escola_parcial_publica | pre_escola_integral_publica | 1.1500 | 1.5000 | 1.5000 | 1.8800 |
| 2025 | C | anos_iniciais_fundamental | ensino_fundamental_integral | 1.0000 | 1.5000 | 1.0000 | 1.5000 |
| 2025 | D | anos_finais_fundamental | ensino_fundamental_integral | 1.1000 | 1.5000 | 1.1000 | 1.5000 |
| 2026 | A | creche_parcial_publica | creche_integral_publica | 1.2500 | 1.5500 | 1.6000 | 1.9000 |
| 2026 | B | pre_escola_parcial_publica | pre_escola_integral_publica | 1.1500 | 1.5000 | 1.5000 | 1.8800 |
| 2026 | C | anos_iniciais_fundamental | ensino_fundamental_integral | 1.0000 | 1.5000 | 1.0000 | 1.5000 |
| 2026 | D | anos_finais_fundamental | ensino_fundamental_integral | 1.1000 | 1.5000 | 1.1000 | 1.5000 |

## 4. Municípios

| ano | municipio | ibge | total_matriculas |
| --- | --- | --- | --- |
| 2024 | Caucaia | 2303709 | 56.712 |
| 2024 | Crato | 2304202 | 18.222 |
| 2024 | Fortaleza | 2304400 | 249.678 |
| 2024 | Iguatu | 2305506 | 11.871 |
| 2024 | Itapipoca | 2306405 | 26.134 |
| 2024 | Juazeiro do Norte | 2307304 | 34.679 |
| 2024 | Maracanaú | 2307650 | 41.002 |
| 2024 | Maranguape | 2307700 | 15.366 |
| 2024 | Quixadá | 2311306 | 12.476 |
| 2024 | Sobral | 2312908 | 34.308 |
| 2025 | Caucaia | 2303709 | 56.422 |
| 2025 | Crato | 2304202 | 18.235 |
| 2025 | Fortaleza | 2304400 | 253.754 |
| 2025 | Iguatu | 2305506 | 12.194 |
| 2025 | Itapipoca | 2306405 | 28.081 |
| 2025 | Juazeiro do Norte | 2307304 | 35.025 |
| 2025 | Maracanaú | 2307650 | 42.921 |
| 2025 | Maranguape | 2307700 | 15.572 |
| 2025 | Quixadá | 2311306 | 12.487 |
| 2025 | Sobral | 2312908 | 34.458 |
| 2026 | Caucaia | 2303709 | 54.599 |
| 2026 | Crato | 2304202 | 17.955 |
| 2026 | Fortaleza | 2304400 | 257.695 |
| 2026 | Iguatu | 2305506 | 12.639 |
| 2026 | Itapipoca | 2306405 | 29.787 |
| 2026 | Juazeiro do Norte | 2307304 | 35.049 |
| 2026 | Maracanaú | 2307650 | 43.591 |
| 2026 | Maranguape | 2307700 | 16.036 |
| 2026 | Quixadá | 2311306 | 12.974 |
| 2026 | Sobral | 2312908 | 33.912 |

Códigos IBGE obtidos por correspondência de nome normalizado na UF CE, sem hardcode prévio.

## 5. Baseline

| ano | municipio | ibge | total_matriculas | matriculas_vaaf | matriculas_vaat | recursos_vaaf | complemento_vaaf | complemento_vaat | complemento_vaar | complemento_uniao | recursos_fundeb | vaaf_final | vaat_final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | Caucaia | 2303709 | 56.712 | 68.537,1 | 73.623,8 | R$ 256.160.723,16 | R$ 111.296.268,52 | R$ 97.181.421,41 | R$ 0,00 | R$ 208.477.689,93 | R$ 464.638.413,10 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Crato | 2304202 | 18.222 | 21.899,3 | 23.521,9 | R$ 81.849.627,94 | R$ 35.561.884,96 | R$ 25.672.991,11 | R$ 0,00 | R$ 61.234.876,08 | R$ 143.084.504,01 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Fortaleza | 2304400 | 249.678 | 328.392,2 | 346.913,5 | R$ 1.227.381.197,93 | R$ 533.270.462,78 | R$ 0,00 | R$ 0,00 | R$ 533.270.462,78 | R$ 1.760.651.660,71 | R$ 5.361,43 | R$ 8.974,00 |
| 2024 | Iguatu | 2305506 | 11.871 | 15.963,6 | 17.011,7 | R$ 59.664.889,03 | R$ 25.923.097,93 | R$ 20.800.039,47 | R$ 0,00 | R$ 46.723.137,40 | R$ 106.388.026,43 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Itapipoca | 2306405 | 26.134 | 35.613,7 | 37.914,3 | R$ 133.107.672,40 | R$ 57.832.391,58 | R$ 99.806.390,03 | R$ 0,00 | R$ 157.638.781,61 | R$ 290.746.454,02 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Juazeiro do Norte | 2307304 | 34.679 | 40.297,3 | 42.935,0 | R$ 150.612.916,20 | R$ 65.438.039,67 | R$ 33.849.907,08 | R$ 0,00 | R$ 99.287.946,75 | R$ 249.900.862,95 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Maracanaú | 2307650 | 41.002 | 49.534,9 | 52.712,6 | R$ 185.139.044,79 | R$ 80.438.892,38 | R$ 58.948.326,50 | R$ 0,00 | R$ 139.387.218,89 | R$ 324.526.263,68 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Maranguape | 2307700 | 15.366 | 19.095,7 | 20.320,7 | R$ 71.370.927,07 | R$ 31.009.117,11 | R$ 35.002.343,94 | R$ 0,00 | R$ 66.011.461,05 | R$ 137.382.388,12 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Quixadá | 2311306 | 12.476 | 15.408,3 | 16.445,8 | R$ 57.589.284,19 | R$ 25.021.292,72 | R$ 27.534.341,07 | R$ 0,00 | R$ 52.555.633,79 | R$ 110.144.917,99 | R$ 5.361,43 | R$ 8.420,96 |
| 2024 | Sobral | 2312908 | 34.308 | 42.575,1 | 46.164,1 | R$ 159.126.536,39 | R$ 69.137.022,67 | R$ 70.581.836,88 | R$ 0,00 | R$ 139.718.859,54 | R$ 298.845.395,93 | R$ 5.361,43 | R$ 8.420,96 |
| 2025 | Caucaia | 2303709 | 56.422 | 75.732,5 | 78.813,2 | R$ 286.740.173,64 | R$ 142.673.911,85 | R$ 146.521.753,85 | R$ 25.317.561,01 | R$ 314.513.226,70 | R$ 601.253.400,34 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Crato | 2304202 | 18.235 | 23.723,0 | 24.694,4 | R$ 89.820.751,55 | R$ 44.692.300,44 | R$ 40.374.178,52 | R$ 0,00 | R$ 85.066.478,96 | R$ 174.887.230,52 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Fortaleza | 2304400 | 253.754 | 363.693,5 | 372.737,3 | R$ 1.377.024.908,51 | R$ 685.169.182,65 | R$ 20.256.245,28 | R$ 0,00 | R$ 705.425.427,93 | R$ 2.082.450.336,43 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Iguatu | 2305506 | 12.194 | 18.029,6 | 18.665,8 | R$ 68.264.088,38 | R$ 33.966.306,16 | R$ 33.541.649,88 | R$ 0,00 | R$ 67.507.956,05 | R$ 135.772.044,42 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Itapipoca | 2306405 | 28.081 | 43.622,3 | 44.899,6 | R$ 165.163.657,91 | R$ 82.180.828,97 | R$ 138.270.336,61 | R$ 14.230.611,83 | R$ 234.681.777,41 | R$ 399.845.435,31 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Juazeiro do Norte | 2307304 | 35.025 | 43.330,0 | 44.865,0 | R$ 164.056.950,79 | R$ 81.630.162,38 | R$ 56.841.934,86 | R$ 0,00 | R$ 138.472.097,24 | R$ 302.529.048,03 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Maracanaú | 2307650 | 42.921 | 56.242,9 | 58.106,2 | R$ 212.948.130,41 | R$ 105.957.049,55 | R$ 112.678.067,42 | R$ 10.869.721,37 | R$ 229.504.838,34 | R$ 442.452.968,76 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Maranguape | 2307700 | 15.572 | 21.089,4 | 21.700,2 | R$ 79.849.090,87 | R$ 39.730.680,24 | R$ 47.122.735,33 | R$ 0,00 | R$ 86.853.415,57 | R$ 166.702.506,44 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Quixadá | 2311306 | 12.487 | 17.085,5 | 17.607,7 | R$ 64.689.365,80 | R$ 32.187.623,93 | R$ 36.555.370,01 | R$ 3.418.702,10 | R$ 72.161.696,03 | R$ 136.851.061,83 | R$ 5.670,14 | R$ 8.021,60 |
| 2025 | Sobral | 2312908 | 34.458 | 47.142,1 | 49.140,5 | R$ 178.490.531,05 | R$ 88.811.909,30 | R$ 99.111.756,54 | R$ 20.046.301,91 | R$ 207.969.967,75 | R$ 386.460.498,80 | R$ 5.670,14 | R$ 8.021,60 |
| 2026 | Caucaia | 2303709 | 54.599 | 75.051,4 | 77.636,2 | R$ 287.385.077,44 | R$ 159.766.984,40 | R$ 155.706.291,95 | R$ 36.093.297,89 | R$ 351.566.574,24 | R$ 638.951.651,68 | R$ 5.957,94 | R$ 10.196,31 |
| 2026 | Crato | 2304202 | 17.955 | 23.629,2 | 24.502,8 | R$ 90.480.352,36 | R$ 50.301.056,59 | R$ 43.703.823,09 | R$ 12.711.722,24 | R$ 106.716.601,92 | R$ 197.196.954,28 | R$ 5.957,94 | R$ 10.196,31 |
| 2026 | Fortaleza | 2304400 | 257.695 | 373.332,0 | 381.244,9 | R$ 1.429.554.044,17 | R$ 794.736.945,67 | R$ 11.781.556,58 | R$ 0,00 | R$ 806.518.502,24 | R$ 2.236.072.546,41 | R$ 5.957,94 | R$ 10.196,31 |
| 2026 | Iguatu | 2305506 | 12.639 | 19.190,8 | 19.755,6 | R$ 73.485.145,62 | R$ 40.852.852,27 | R$ 49.815.648,60 | R$ 0,00 | R$ 90.668.500,87 | R$ 164.153.646,49 | R$ 5.957,94 | R$ 10.196,31 |
| 2026 | Itapipoca | 2306405 | 29.787 | 46.321,8 | 47.594,8 | R$ 177.374.257,56 | R$ 98.608.287,16 | R$ 178.997.032,45 | R$ 20.835.607,71 | R$ 298.440.927,32 | R$ 475.815.184,89 | R$ 5.957,94 | R$ 10.196,31 |
| 2026 | Juazeiro do Norte | 2307304 | 35.049 | 43.706,9 | 45.100,1 | R$ 167.361.542,50 | R$ 93.041.883,69 | R$ 67.672.059,44 | R$ 0,00 | R$ 160.713.943,13 | R$ 328.075.485,64 | R$ 5.957,95 | R$ 10.196,31 |
| 2026 | Maracanaú | 2307650 | 43.591 | 58.066,8 | 59.795,7 | R$ 222.348.095,19 | R$ 123.610.748,94 | R$ 134.214.020,32 | R$ 15.459.460,87 | R$ 273.284.230,13 | R$ 495.632.325,33 | R$ 5.957,94 | R$ 10.196,31 |
| 2026 | Maranguape | 2307700 | 16.036 | 22.432,2 | 22.935,5 | R$ 85.896.934,85 | R$ 47.752.981,37 | R$ 61.262.771,93 | R$ 0,00 | R$ 109.015.753,30 | R$ 194.912.688,15 | R$ 5.957,94 | R$ 10.196,31 |
| 2026 | Quixadá | 2311306 | 12.974 | 18.296,2 | 18.691,2 | R$ 70.059.507,76 | R$ 38.948.425,52 | R$ 49.387.975,87 | R$ 8.743.925,62 | R$ 97.080.327,01 | R$ 167.139.834,77 | R$ 5.957,95 | R$ 10.196,31 |
| 2026 | Sobral | 2312908 | 33.912 | 47.134,4 | 48.881,9 | R$ 180.486.145,20 | R$ 100.338.289,66 | R$ 96.511.904,88 | R$ 28.039.764,05 | R$ 224.889.958,59 | R$ 405.376.103,79 | R$ 5.957,94 | R$ 10.196,31 |

## 6. Cenários

Foram executados **12666** cenários, dos quais **12666** passaram na validação interna. Tempo total: **165.2 s**.

| Ano | Cenários | Válidos | Tempo (s) | Tempo médio (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 2024 | 4222 | 4222 | 47.1 | 11.15 |
| 2025 | 4222 | 4222 | 57.0 | 13.50 |
| 2026 | 4222 | 4222 | 61.1 | 14.47 |

Famílias: transições individuais A–D em 0–100%; ótimo factível (A–D simultâneas); ótimo matemático (concentração teórica); sensibilidade +1 aluno; G10 conjunto e maximin.

## 7. Resultados

Maior ΔR$ individual: **Fortaleza** (2026), Fundamental anos iniciais urbano → fundamental integral a 100% → R$ 233.908.847,17 (10,461%).

Maior Δ%: **Juazeiro do Norte** (2026), Fundamental anos iniciais urbano → fundamental integral a 100% → 20,896% (R$ 68.555.235,07).

## 8. Melhor transformação de cada município

| ano | municipio | transformacao | pct_convertido | alunos | base_r | novo_r | delta_r | delta_pct | r_por_aluno |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | 11.688,0 | R$ 464.638.413,10 | R$ 529.910.749,86 | R$ 65.272.336,76 | 14,048% | R$ 5.584,56 |
| 2024 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | 3.531,0 | R$ 143.084.504,01 | R$ 162.875.632,57 | R$ 19.791.128,56 | 13,832% | R$ 5.604,96 |
| 2024 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | 32.481,0 | R$ 1.760.651.660,71 | R$ 1.829.988.894,53 | R$ 69.337.233,82 | 3,938% | R$ 2.134,70 |
| 2024 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | 1.320,0 | R$ 106.388.026,43 | R$ 113.794.520,31 | R$ 7.406.493,88 | 6,962% | R$ 5.610,98 |
| 2024 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | 3.288,0 | R$ 290.746.454,02 | R$ 302.383.952,50 | R$ 11.637.498,48 | 4,003% | R$ 3.539,39 |
| 2024 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | 8.692,0 | R$ 249.900.862,95 | R$ 298.372.747,54 | R$ 48.471.884,59 | 19,396% | R$ 5.576,61 |
| 2024 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | 7.935,0 | R$ 324.526.263,68 | R$ 368.712.004,38 | R$ 44.185.740,70 | 13,615% | R$ 5.568,46 |
| 2024 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | 3.052,0 | R$ 137.382.388,12 | R$ 154.533.252,56 | R$ 17.150.864,44 | 12,484% | R$ 5.619,55 |
| 2024 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | 2.185,0 | R$ 110.144.917,99 | R$ 122.465.746,61 | R$ 12.320.828,62 | 11,186% | R$ 5.638,82 |
| 2024 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | 6.621,0 | R$ 298.845.395,93 | R$ 335.979.206,05 | R$ 37.133.810,12 | 12,426% | R$ 5.608,49 |
| 2025 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | 10.880,0 | R$ 601.253.400,34 | R$ 677.896.609,29 | R$ 76.643.208,95 | 12,747% | R$ 7.044,41 |
| 2025 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | 3.137,0 | R$ 174.887.230,52 | R$ 197.081.236,73 | R$ 22.194.006,21 | 12,690% | R$ 7.074,91 |
| 2025 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | 33.767,0 | R$ 2.082.450.336,43 | R$ 2.314.694.367,46 | R$ 232.244.031,03 | 11,152% | R$ 6.877,84 |
| 2025 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | 1.453,0 | R$ 135.772.044,42 | R$ 146.016.957,02 | R$ 10.244.912,60 | 7,546% | R$ 7.050,87 |
| 2025 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | 1.421,0 | R$ 399.845.435,31 | R$ 407.300.291,53 | R$ 7.454.856,22 | 1,864% | R$ 5.246,20 |
| 2025 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | 8.490,0 | R$ 302.529.048,03 | R$ 362.284.968,59 | R$ 59.755.920,56 | 19,752% | R$ 7.038,39 |
| 2025 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | 9.447,0 | R$ 442.452.968,76 | R$ 508.757.886,41 | R$ 66.304.917,65 | 14,986% | R$ 7.018,62 |
| 2025 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | 3.157,0 | R$ 166.702.506,44 | R$ 189.072.898,20 | R$ 22.370.391,76 | 13,419% | R$ 7.085,97 |
| 2025 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | 2.246,0 | R$ 136.851.061,83 | R$ 152.828.554,54 | R$ 15.977.492,71 | 11,675% | R$ 7.113,75 |
| 2025 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | 6.266,0 | R$ 386.460.498,80 | R$ 430.704.322,04 | R$ 44.243.823,24 | 11,448% | R$ 7.060,94 |
| 2026 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | 11.380,0 | R$ 638.951.651,68 | R$ 733.433.112,27 | R$ 94.481.460,59 | 14,787% | R$ 8.302,41 |
| 2026 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | 3.031,0 | R$ 197.196.954,28 | R$ 222.468.194,74 | R$ 25.271.240,46 | 12,815% | R$ 8.337,59 |
| 2026 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | 28.837,0 | R$ 2.236.072.546,41 | R$ 2.469.981.393,58 | R$ 233.908.847,17 | 10,461% | R$ 8.111,41 |
| 2026 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | 1.211,0 | R$ 164.153.646,49 | R$ 174.215.361,06 | R$ 10.061.714,57 | 6,129% | R$ 8.308,60 |
| 2026 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | 1.243,0 | R$ 475.815.184,89 | R$ 483.526.541,17 | R$ 7.711.356,28 | 1,621% | R$ 6.203,83 |
| 2026 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | 8.265,0 | R$ 328.075.485,64 | R$ 396.630.720,71 | R$ 68.555.235,07 | 20,896% | R$ 8.294,64 |
| 2026 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | 9.123,0 | R$ 495.632.325,33 | R$ 571.093.532,84 | R$ 75.461.207,51 | 15,225% | R$ 8.271,53 |
| 2026 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | 2.947,0 | R$ 194.912.688,15 | R$ 219.517.985,24 | R$ 24.605.297,09 | 12,624% | R$ 8.349,27 |
| 2026 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | 2.157,0 | R$ 167.139.834,77 | R$ 185.219.601,54 | R$ 18.079.766,77 | 10,817% | R$ 8.381,90 |
| 2026 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | 5.713,0 | R$ 405.376.103,79 | R$ 452.914.647,21 | R$ 47.538.543,42 | 11,727% | R$ 8.321,12 |

## 9. Ótimo matemático

Cenário **teórico**: todo o estoque de matrículas do município é concentrado na etapa de maior soma de pesos VAAF+VAAT entre as cinco mais altas. **Não é educacionalmente factível.**

| ano | municipio | transformacao | alunos_movidos | delta_r | delta_r_percentual |
| --- | --- | --- | --- | --- | --- |
| 2024 | Caucaia | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 56.712 | R$ 349.854.954,40 | 75,30% |
| 2024 | Crato | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 18.222 | R$ 114.757.047,67 | 80,20% |
| 2024 | Fortaleza | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 249.678 | R$ 965.189.351,88 | 54,82% |
| 2024 | Iguatu | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 11.871 | R$ 51.709.983,57 | 48,61% |
| 2024 | Itapipoca | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 26.134 | R$ 113.822.432,52 | 39,15% |
| 2024 | Juazeiro do Norte | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 34.679 | R$ 237.735.717,79 | 95,13% |
| 2024 | Maracanaú | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 41.002 | R$ 253.634.218,93 | 78,16% |
| 2024 | Maranguape | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 15.366 | R$ 90.218.877,89 | 65,67% |
| 2024 | Quixadá | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 12.476 | R$ 75.174.210,77 | 68,25% |
| 2024 | Sobral | Concentrar 100% em Creche em Tempo Integral na Rede Pública | 34.308 | R$ 194.533.272,70 | 65,09% |
| 2025 | Caucaia | Concentrar 100% em Creche Integral Pública Indígena | 56.422 | R$ 890.005.684,38 | 148,03% |
| 2025 | Crato | Concentrar 100% em Creche Integral Pública Quilombola Especial | 18.235 | R$ 300.514.598,99 | 171,83% |
| 2025 | Fortaleza | Concentrar 100% em Creche Integral Pública Indígena Bilíngue De Surdos | 253.754 | R$ 3.562.832.835,22 | 171,09% |
| 2025 | Iguatu | Concentrar 100% em Creche Integral Pública Indígena | 12.194 | R$ 170.060.434,72 | 125,25% |
| 2025 | Itapipoca | Concentrar 100% em Creche Integral Pública Quilombola | 28.081 | R$ 377.223.737,59 | 94,34% |
| 2025 | Juazeiro do Norte | Concentrar 100% em Creche Integral Pública Indígena Especial | 35.025 | R$ 604.109.463,83 | 199,69% |
| 2025 | Maracanaú | Concentrar 100% em Creche Integral Pública Indígena Bilíngue De Surdos | 42.921 | R$ 693.748.712,80 | 156,80% |
| 2025 | Maranguape | Concentrar 100% em Creche Integral Pública Quilombola | 15.572 | R$ 247.878.489,59 | 148,70% |
| 2025 | Quixadá | Concentrar 100% em Creche Integral Pública Quilombola Especial | 12.487 | R$ 197.817.203,38 | 144,55% |
| 2025 | Sobral | Concentrar 100% em Creche Integral Pública Indígena Bilíngue De Surdos | 34.458 | R$ 532.992.780,25 | 137,92% |
| 2026 | Caucaia | Concentrar 100% em Creche Integral Pública Indígena Bilíngue De Surdos | 54.599 | R$ 1.007.969.503,06 | 157,75% |
| 2026 | Crato | Concentrar 100% em Creche Integral Pública Indígena Especial | 17.955 | R$ 350.747.528,23 | 177,87% |
| 2026 | Fortaleza | Concentrar 100% em Creche Integral Pública Indígena Especial | 257.695 | R$ 4.304.234.663,18 | 192,49% |
| 2026 | Iguatu | Concentrar 100% em Creche Integral Pública Indígena Bilíngue De Surdos | 12.639 | R$ 204.387.792,40 | 124,51% |
| 2026 | Itapipoca | Concentrar 100% em Creche Integral Pública Indígena Especial | 29.787 | R$ 480.658.071,39 | 101,02% |
| 2026 | Juazeiro do Norte | Concentrar 100% em Creche Integral Pública Indígena Especial | 35.049 | R$ 719.455.315,32 | 219,30% |
| 2026 | Maracanaú | Concentrar 100% em Creche Integral Pública Quilombola | 43.591 | R$ 830.693.370,35 | 167,60% |
| 2026 | Maranguape | Concentrar 100% em Creche Integral Pública Indígena Bilíngue De Surdos | 16.036 | R$ 295.612.824,32 | 151,66% |
| 2026 | Quixadá | Concentrar 100% em Creche Integral Pública Indígena | 12.974 | R$ 238.979.765,36 | 142,98% |
| 2026 | Sobral | Concentrar 100% em Creche Integral Pública Indígena | 33.912 | R$ 618.873.860,59 | 152,67% |

## 10. Ótimo factível

Apenas as transições A–D (parcial→integral na educação infantil pública e fundamental urbano→integral). Conversão simultânea a 25%, 50%, 75% e 100%.

| ano | municipio | percentual | alunos_movidos | delta_r | delta_r_percentual | ganho_por_aluno |
| --- | --- | --- | --- | --- | --- | --- |
| 2024 | Caucaia | 100 | 34.822,0 | R$ 152.330.109,99 | 32,785% | R$ 4.374,54 |
| 2024 | Crato | 100 | 11.251,0 | R$ 48.874.440,14 | 34,158% | R$ 4.344,01 |
| 2024 | Fortaleza | 100 | 70.579,0 | R$ 123.191.202,97 | 6,997% | R$ 1.745,44 |
| 2024 | Iguatu | 100 | 2.792,0 | R$ 13.125.310,79 | 12,337% | R$ 4.701,04 |
| 2024 | Itapipoca | 100 | 5.795,0 | R$ 19.547.639,19 | 6,723% | R$ 3.373,19 |
| 2024 | Juazeiro do Norte | 100 | 24.707,0 | R$ 110.351.970,91 | 44,158% | R$ 4.466,43 |
| 2024 | Maracanaú | 100 | 21.512,0 | R$ 96.855.523,49 | 29,845% | R$ 4.502,40 |
| 2024 | Maranguape | 100 | 7.692,0 | R$ 34.575.921,48 | 25,168% | R$ 4.495,05 |
| 2024 | Quixadá | 100 | 6.390,0 | R$ 27.914.109,15 | 25,343% | R$ 4.368,41 |
| 2024 | Sobral | 100 | 19.926,0 | R$ 84.539.519,64 | 28,289% | R$ 4.242,67 |
| 2025 | Caucaia | 100 | 27.729,0 | R$ 164.292.167,98 | 27,325% | R$ 5.924,92 |
| 2025 | Crato | 100 | 9.115,0 | R$ 54.049.752,14 | 30,905% | R$ 5.929,76 |
| 2025 | Fortaleza | 100 | 65.802,0 | R$ 391.730.621,55 | 18,811% | R$ 5.953,17 |
| 2025 | Iguatu | 100 | 2.922,0 | R$ 18.002.475,72 | 13,259% | R$ 6.161,01 |
| 2025 | Itapipoca | 100 | 2.754,0 | R$ 14.689.619,55 | 3,674% | R$ 5.333,92 |
| 2025 | Juazeiro do Norte | 100 | 22.978,0 | R$ 137.219.008,02 | 45,357% | R$ 5.971,76 |
| 2025 | Maracanaú | 100 | 21.036,0 | R$ 128.669.569,99 | 29,081% | R$ 6.116,64 |
| 2025 | Maranguape | 100 | 6.354,0 | R$ 39.423.344,68 | 23,649% | R$ 6.204,49 |
| 2025 | Quixadá | 100 | 4.842,0 | R$ 29.666.846,34 | 21,678% | R$ 6.126,98 |
| 2025 | Sobral | 100 | 16.050,0 | R$ 92.075.294,65 | 23,825% | R$ 5.736,78 |
| 2026 | Caucaia | 100 | 23.395,0 | R$ 166.956.055,58 | 26,130% | R$ 7.136,40 |
| 2026 | Crato | 100 | 8.609,0 | R$ 60.371.263,96 | 30,615% | R$ 7.012,58 |
| 2026 | Fortaleza | 100 | 56.933,0 | R$ 399.764.384,11 | 17,878% | R$ 7.021,66 |
| 2026 | Iguatu | 100 | 2.051,0 | R$ 15.104.132,50 | 9,201% | R$ 7.364,28 |
| 2026 | Itapipoca | 100 | 2.136,0 | R$ 12.444.327,04 | 2,615% | R$ 5.826,00 |
| 2026 | Juazeiro do Norte | 100 | 22.220,0 | R$ 156.709.744,21 | 47,766% | R$ 7.052,64 |
| 2026 | Maracanaú | 100 | 19.375,0 | R$ 141.013.596,00 | 28,451% | R$ 7.278,12 |
| 2026 | Maranguape | 100 | 5.028,0 | R$ 37.206.442,64 | 19,089% | R$ 7.399,85 |
| 2026 | Quixadá | 100 | 3.937,0 | R$ 28.727.667,66 | 17,188% | R$ 7.296,84 |
| 2026 | Sobral | 100 | 13.967,0 | R$ 94.529.507,36 | 23,319% | R$ 6.768,06 |

## 11. Impacto sobre os demais municípios

A 50% da transição individual de maior ΔR$ de cada alvo:

| ano | municipio | delta_alvo | delta_demais | delta_ce_municipal | n_beneficiados | n_prejudicados |
| --- | --- | --- | --- | --- | --- | --- |
| 2024 | Caucaia | R$ 32.641.470,94 | R$ -3.325.899,08 | R$ 29.315.571,86 | 0 | 183 |
| 2024 | Crato | R$ 9.896.048,78 | R$ -1.038.034,98 | R$ 8.858.013,80 | 0 | 183 |
| 2024 | Fortaleza | R$ 34.680.417,51 | R$ -2.591.333,74 | R$ 32.089.083,77 | 0 | 183 |
| 2024 | Iguatu | R$ 3.703.314,76 | R$ -389.888,01 | R$ 3.313.426,75 | 0 | 183 |
| 2024 | Itapipoca | R$ 5.818.916,92 | R$ -605.323,27 | R$ 5.213.593,65 | 0 | 183 |
| 2024 | Juazeiro do Norte | R$ 24.238.859,24 | R$ -2.514.188,04 | R$ 21.724.671,20 | 0 | 183 |
| 2024 | Maracanaú | R$ 22.095.296,77 | R$ -2.278.831,99 | R$ 19.816.464,78 | 0 | 183 |
| 2024 | Maranguape | R$ 8.575.796,00 | R$ -901.162,58 | R$ 7.674.633,42 | 0 | 183 |
| 2024 | Quixadá | R$ 6.160.601,99 | R$ -648.804,51 | R$ 5.511.797,48 | 0 | 183 |
| 2024 | Sobral | R$ 18.568.616,92 | R$ -1.922.689,75 | R$ 16.645.927,17 | 0 | 183 |
| 2025 | Caucaia | R$ 38.327.929,99 | R$ -4.333.182,81 | R$ 33.994.747,18 | 0 | 183 |
| 2025 | Crato | R$ 11.097.531,46 | R$ -1.285.588,61 | R$ 9.811.942,85 | 0 | 183 |
| 2025 | Fortaleza | R$ 116.237.414,52 | R$ -11.335.788,67 | R$ 104.901.625,85 | 0 | 183 |
| 2025 | Iguatu | R$ 5.122.568,84 | R$ -594.992,58 | R$ 4.527.576,26 | 0 | 183 |
| 2025 | Itapipoca | R$ 3.727.488,58 | R$ -430.861,53 | R$ 3.296.627,05 | 0 | 183 |
| 2025 | Juazeiro do Norte | R$ 29.881.798,01 | R$ -3.430.615,47 | R$ 26.451.182,54 | 0 | 183 |
| 2025 | Maracanaú | R$ 33.157.187,43 | R$ -3.783.839,69 | R$ 29.373.347,74 | 0 | 183 |
| 2025 | Maranguape | R$ 11.185.732,53 | R$ -1.297.412,57 | R$ 9.888.319,96 | 0 | 183 |
| 2025 | Quixadá | R$ 7.989.020,04 | R$ -928.324,09 | R$ 7.060.695,95 | 0 | 183 |
| 2025 | Sobral | R$ 22.124.015,80 | R$ -2.535.063,96 | R$ 19.588.951,84 | 0 | 183 |
| 2026 | Caucaia | R$ 47.248.736,27 | R$ -5.349.636,98 | R$ 41.899.099,29 | 0 | 183 |
| 2026 | Crato | R$ 12.636.187,99 | R$ -1.464.526,37 | R$ 11.171.661,62 | 0 | 183 |
| 2026 | Fortaleza | R$ 117.004.839,32 | R$ -11.414.709,04 | R$ 105.590.130,28 | 0 | 183 |
| 2026 | Iguatu | R$ 5.030.947,26 | R$ -584.267,12 | R$ 4.446.680,14 | 0 | 183 |
| 2026 | Itapipoca | R$ 3.855.731,31 | R$ -443.379,38 | R$ 3.412.351,93 | 0 | 183 |
| 2026 | Juazeiro do Norte | R$ 34.281.806,85 | R$ -3.937.667,83 | R$ 30.344.139,02 | 0 | 183 |
| 2026 | Maracanaú | R$ 37.735.689,40 | R$ -4.306.294,12 | R$ 33.429.395,28 | 0 | 183 |
| 2026 | Maranguape | R$ 12.303.186,72 | R$ -1.426.812,26 | R$ 10.876.374,46 | 0 | 183 |
| 2026 | Quixadá | R$ 9.040.173,88 | R$ -1.050.331,56 | R$ 7.989.842,32 | 0 | 183 |
| 2026 | Sobral | R$ 23.771.284,75 | R$ -2.725.932,68 | R$ 21.045.352,07 | 0 | 183 |

Se `delta_ce_municipal` é pequeno frente a `delta_alvo` e `delta_demais` tem sinal oposto, o mecanismo está sobretudo **redistribuindo** o fundo estadual/a equalização, não criando recursos novos na mesma magnitude do ganho do alvo.

## 12. Otimização conjunta

| ano | cenario_id | percentual | g10 | g10_percentual | min_delta_pct | max_delta_pct | alunos_movidos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | G10_FACTIVEL_010 | 10 | R$ 69.291.024,31 | 1,783% | 0,615% | 4,351% | 20.547 |
| 2024 | G10_FACTIVEL_020 | 20 | R$ 138.534.935,82 | 3,565% | 1,229% | 8,700% | 41.093 |
| 2024 | G10_FACTIVEL_030 | 30 | R$ 207.731.748,14 | 5,345% | 1,843% | 13,046% | 61.640 |
| 2024 | G10_FACTIVEL_040 | 40 | R$ 276.881.116,35 | 7,125% | 2,456% | 17,388% | 82.186 |
| 2024 | G10_FACTIVEL_050 | 50 | R$ 345.983.537,81 | 8,903% | 3,069% | 21,728% | 102.733 |
| 2024 | G10_FACTIVEL_060 | 60 | R$ 415.037.281,22 | 10,679% | 3,682% | 26,065% | 123.280 |
| 2024 | G10_FACTIVEL_070 | 70 | R$ 484.042.970,46 | 12,455% | 4,294% | 30,398% | 143.826 |
| 2024 | G10_FACTIVEL_080 | 80 | R$ 553.001.567,44 | 14,229% | 4,905% | 34,729% | 164.373 |
| 2024 | G10_FACTIVEL_090 | 90 | R$ 621.913.293,79 | 16,003% | 5,516% | 39,057% | 184.919 |
| 2024 | G10_FACTIVEL_100 | 100 | R$ 690.777.777,87 | 17,775% | 6,127% | 43,382% | 205.466 |
| 2024 | G10_MELHOR_INDIVIDUAL | — | R$ 324.420.542,49 | 8,348% | 3,732% | 19,064% | 80.793 |
| 2025 | G10_FACTIVEL_010 | 10 | R$ 103.531.344,45 | 2,144% | 0,297% | 4,455% | 17.958 |
| 2025 | G10_FACTIVEL_020 | 20 | R$ 206.807.492,38 | 4,282% | 0,592% | 8,902% | 35.916 |
| 2025 | G10_FACTIVEL_030 | 30 | R$ 309.892.976,19 | 6,417% | 0,885% | 13,343% | 53.875 |
| 2025 | G10_FACTIVEL_040 | 40 | R$ 412.876.001,29 | 8,550% | 1,178% | 17,780% | 71.833 |
| 2025 | G10_FACTIVEL_050 | 50 | R$ 515.756.184,64 | 10,680% | 1,470% | 22,213% | 89.791 |
| 2025 | G10_FACTIVEL_060 | 60 | R$ 618.532.770,01 | 12,808% | 1,762% | 26,641% | 107.749 |
| 2025 | G10_FACTIVEL_070 | 70 | R$ 721.205.255,97 | 14,934% | 2,054% | 31,064% | 125.707 |
| 2025 | G10_FACTIVEL_080 | 80 | R$ 823.769.674,85 | 17,058% | 2,345% | 35,483% | 143.666 |
| 2025 | G10_FACTIVEL_090 | 90 | R$ 926.228.595,93 | 19,180% | 2,636% | 39,898% | 161.624 |
| 2025 | G10_FACTIVEL_100 | 100 | R$ 1.028.583.939,91 | 21,299% | 2,927% | 44,308% | 179.582 |
| 2025 | G10_MELHOR_INDIVIDUAL | — | R$ 537.667.913,06 | 11,134% | 1,482% | 19,255% | 80.264 |
| 2026 | G10_FACTIVEL_010 | 10 | R$ 107.651.583,60 | 2,030% | 0,198% | 4,702% | 15.765 |
| 2026 | G10_FACTIVEL_020 | 20 | R$ 215.214.496,38 | 4,058% | 0,396% | 9,400% | 31.530 |
| 2026 | G10_FACTIVEL_030 | 30 | R$ 322.688.805,56 | 6,085% | 0,594% | 14,094% | 47.295 |
| 2026 | G10_FACTIVEL_040 | 40 | R$ 430.075.949,36 | 8,110% | 0,791% | 18,785% | 63.060 |
| 2026 | G10_FACTIVEL_050 | 50 | R$ 537.374.876,21 | 10,133% | 0,989% | 23,471% | 78.826 |
| 2026 | G10_FACTIVEL_060 | 60 | R$ 644.585.785,73 | 12,154% | 1,186% | 28,154% | 94.591 |
| 2026 | G10_FACTIVEL_070 | 70 | R$ 751.708.867,89 | 14,174% | 1,383% | 32,833% | 110.356 |
| 2026 | G10_FACTIVEL_080 | 80 | R$ 858.740.825,86 | 16,192% | 1,580% | 37,508% | 126.121 |
| 2026 | G10_FACTIVEL_090 | 90 | R$ 965.679.164,73 | 18,209% | 1,776% | 42,180% | 141.886 |
| 2026 | G10_FACTIVEL_100 | 100 | R$ 1.072.516.103,54 | 20,223% | 1,973% | 46,847% | 157.651 |
| 2026 | G10_MELHOR_INDIVIDUAL | — | R$ 584.964.302,02 | 11,030% | 1,274% | 20,432% | 73.907 |

O cenário marcado como `pareto_equidade` maximiza o menor ganho percentual entre os dez (maximin) no grid de conversão factível conjunta.

## 13. Análise de sensibilidade

Efeito de converter **mais um aluno** (mediana entre os 10 municípios):

| ano | codigo_transicao | transformacao | mediana_dR | media_dR |
| --- | --- | --- | --- | --- |
| 2024 | A | Creche parcial → creche integral (rede pública) | R$ 3.076,51 | R$ 2.903,25 |
| 2024 | B | Pré-escola parcial → pré-escola integral (rede pública) | R$ 3.504,56 | R$ 3.288,57 |
| 2024 | C | Fundamental anos iniciais urbano → fundamental integral | R$ 5.607,00 | R$ 5.261,47 |
| 2024 | D | Fundamental anos finais urbano → fundamental integral | R$ 4.205,47 | R$ 3.946,22 |
| 2025 | A | Creche parcial → creche integral (rede pública) | R$ 4.233,89 | R$ 4.231,56 |
| 2025 | B | Pré-escola parcial → pré-escola integral (rede pública) | R$ 5.184,24 | R$ 5.181,13 |
| 2025 | C | Fundamental anos iniciais urbano → fundamental integral | R$ 7.056,05 | R$ 7.051,85 |
| 2025 | D | Fundamental anos finais urbano → fundamental integral | R$ 5.645,26 | R$ 5.641,92 |
| 2026 | A | Creche parcial → creche integral (rede pública) | R$ 4.989,27 | R$ 4.986,51 |
| 2026 | B | Pré-escola parcial → pré-escola integral (rede pública) | R$ 6.131,94 | R$ 6.128,34 |
| 2026 | C | Fundamental anos iniciais urbano → fundamental integral | R$ 8.315,01 | R$ 8.310,06 |
| 2026 | D | Fundamental anos finais urbano → fundamental integral | R$ 6.652,48 | R$ 6.648,56 |

## 14. Linearidade e tamanho da rede

Fração de curvas município×transição com R² linear ≥ 0,995: **100,0%**. Valores abaixo disso indicam não-linearidade associada à equalização VAAF/VAAT (mudança de quem é complementado).


Correlação de Pearson entre tamanho da rede e ganho % máximo: **-0.142**. A hipótese de que municípios menores têm ganho percentual diferente dos maiores é avaliada por esse coeficiente (não por causalidade).

## 15. Limitações

- Três snapshots (2024, 2025, 2026), não um painel de matrículas idêntico ao longo do tempo.
- Em 2025/2026 as transições usam o segmento urbano/padrão, não todos os sufixos campo/indígena/quilombola.
- O ótimo matemático ignora restrições pedagógicas, de infraestrutura e de etapa etária.
- VAAR entra com o peso observado; não modelamos mudança de condicionalidades VAAR.
- NF de 2024 é reescalonado para 1 pelo motor quando max=min=1; DREC de 2025+ permanece oficial.
- Custos da jornada integral e efeitos de aprendizagem estão fora do modelo.

## 16. Implicações para políticas públicas

O experimento contrafactual indica que a composição das matrículas altera os recursos simulados devido aos fatores de ponderação do FUNDEB e aos mecanismos de equalização VAAF, VAAT e VAAR. A expansão efetiva da oferta em tempo integral apresenta simultaneamente implicações educacionais e fiscais, cuja magnitude pode ser estimada pelo modelo. Isso descreve **incentivos financeiros implícitos**, não uma prescrição para transferir alunos entre etapas.

## 17. Possíveis extensões

- Incluir sufixos campo/indígena/quilombola e rede conveniada como transições factíveis adicionais.
- Custo-efetividade: ΔFUNDEB versus custo da vaga em tempo integral.
- Otimização com restrições de capacidade (teto de vagas integrais).
- Repetir o desenho para outras UFs.
- Painel verdadeiro se o INEP/FNDE publicar matrículas comparáveis por mais anos.

## Reprodutibilidade

- Python: `3.12.13 (main, Mar  3 2026, 12:39:30) [Clang 21.0.0 (clang-2100.0.123.102)]`
- Plataforma: `macOS-26.5-arm64-arm-64bit`
- Data: 2026-09-02 17:45 UTC
- Commit: `c0e65b7`
- Comando: `python -m analises.fundeb_ceara.run`

## Rankings (melhor transição individual por município)

### Exercício 2024
**A_ganho_absoluto**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 69.337.233,82 |
| 2 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 65.272.336,76 |
| 3 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 48.471.884,59 |
| 4 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 44.185.740,70 |
| 5 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 37.133.810,12 |
| 6 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 19.791.128,56 |
| 7 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 17.150.864,44 |
| 8 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 12.320.828,62 |
| 9 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | R$ 11.637.498,48 |
| 10 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.406.493,88 |

**B_ganho_percentual**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | 19,396% |
| 2 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | 14,048% |
| 3 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | 13,832% |
| 4 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | 13,615% |
| 5 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | 12,484% |
| 6 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | 12,426% |
| 7 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | 11,186% |
| 8 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | 6,962% |
| 9 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | 4,003% |
| 10 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | 3,938% |

**C_ganho_por_aluno**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.638,82 |
| 2 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.619,55 |
| 3 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.610,98 |
| 4 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.608,49 |
| 5 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.604,96 |
| 6 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.584,56 |
| 7 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.576,61 |
| 8 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 5.568,46 |
| 9 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | R$ 3.539,39 |
| 10 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 2.134,70 |

**D_transicao_eficiente**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | nan | Fundamental anos iniciais urbano → fundamental integral | — | R$ 5.604,96 |
| 2 | nan | Pré-escola parcial → pré-escola integral (rede pública) | — | R$ 3.539,39 |

### Exercício 2025
**A_ganho_absoluto**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 232.244.031,03 |
| 2 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 76.643.208,95 |
| 3 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 66.304.917,65 |
| 4 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 59.755.920,56 |
| 5 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 44.243.823,24 |
| 6 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 22.370.391,76 |
| 7 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 22.194.006,21 |
| 8 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 15.977.492,71 |
| 9 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 10.244.912,60 |
| 10 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | R$ 7.454.856,22 |

**B_ganho_percentual**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | 19,752% |
| 2 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | 14,986% |
| 3 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | 13,419% |
| 4 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | 12,747% |
| 5 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | 12,690% |
| 6 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | 11,675% |
| 7 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | 11,448% |
| 8 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | 11,152% |
| 9 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | 7,546% |
| 10 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | 1,864% |

**C_ganho_por_aluno**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.113,75 |
| 2 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.085,97 |
| 3 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.074,91 |
| 4 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.060,94 |
| 5 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.050,87 |
| 6 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.044,41 |
| 7 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.038,39 |
| 8 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 7.018,62 |
| 9 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 6.877,84 |
| 10 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | R$ 5.246,20 |

**D_transicao_eficiente**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | nan | Fundamental anos iniciais urbano → fundamental integral | — | R$ 7.050,87 |
| 2 | nan | Pré-escola parcial → pré-escola integral (rede pública) | — | R$ 5.246,20 |

### Exercício 2026
**A_ganho_absoluto**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 233.908.847,17 |
| 2 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 94.481.460,59 |
| 3 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 75.461.207,51 |
| 4 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 68.555.235,07 |
| 5 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 47.538.543,42 |
| 6 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 25.271.240,46 |
| 7 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 24.605.297,09 |
| 8 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 18.079.766,77 |
| 9 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 10.061.714,57 |
| 10 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | R$ 7.711.356,28 |

**B_ganho_percentual**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | 20,896% |
| 2 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | 15,225% |
| 3 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | 14,787% |
| 4 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | 12,815% |
| 5 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | 12,624% |
| 6 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | 11,727% |
| 7 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | 10,817% |
| 8 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | 10,461% |
| 9 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | 6,129% |
| 10 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | 1,621% |

**C_ganho_por_aluno**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | Quixadá | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.381,90 |
| 2 | Maranguape | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.349,27 |
| 3 | Crato | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.337,59 |
| 4 | Sobral | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.321,12 |
| 5 | Iguatu | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.308,60 |
| 6 | Caucaia | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.302,41 |
| 7 | Juazeiro do Norte | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.294,64 |
| 8 | Maracanaú | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.271,53 |
| 9 | Fortaleza | Fundamental anos iniciais urbano → fundamental integral | 100 | R$ 8.111,41 |
| 10 | Itapipoca | Pré-escola parcial → pré-escola integral (rede pública) | 100 | R$ 6.203,83 |

**D_transicao_eficiente**

| posicao | municipio | transformacao | percentual | valor |
| --- | --- | --- | --- | --- |
| 1 | nan | Fundamental anos iniciais urbano → fundamental integral | — | R$ 8.308,60 |
| 2 | nan | Pré-escola parcial → pré-escola integral (rede pública) | — | R$ 6.203,83 |
