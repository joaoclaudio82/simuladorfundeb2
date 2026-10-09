# Metodologia

## Objeto

Estudo contrafactual da composição das matrículas municipais e dos recursos do FUNDEB simulados para dez municípios do Ceará. A unidade de intervenção é um vetor de matrículas por etapa; a unidade de resultado é `recursos_fundeb` devolvido por `simula_fundeb` em `simulador.py`.

## Dados

Três snapshots independentes:

- **2024:** objetos R em `data/` (`pesos`, `matriculas`, `complementar`, `cenario_atual*`). O ano não está no nome do arquivo; a identificação usa o carregador `carregar_dataset_2024()`, o PDF `PonderadorNSE 2024.pdf` e a documentação do sistema.
- **2025 e 2026:** planilhas oficiais em `20252026/`, montadas por `dados/fundeb_dataset.py`. Em 2025 a simulação está habilitada quando receita, NSE, DREC e VAAT estão presentes.

Não se interpola série temporal entre os snapshots.

## Municípios

Fortaleza, Caucaia, Maracanaú, Sobral, Juazeiro do Norte, Crato, Itapipoca, Maranguape, Quixadá e Iguatu. Os códigos IBGE são resolvidos por nome normalizado na UF CE; não são gravados a priori no código de simulação.

## Transições factíveis

Detectadas no dataset de cada ano (aliases 2024 ≠ 2025/2026):

| Código | Origem conceitual | Destino conceitual |
| --- | --- | --- |
| A | Creche parcial pública | Creche integral pública |
| B | Pré-escola parcial pública | Pré-escola integral pública |
| C | Fundamental anos iniciais urbano | Fundamental integral |
| D | Fundamental anos finais urbano | Fundamental integral |

Não se admite, no conjunto factível, movimentos entre etapas etárias distintas (por exemplo creche → ensino médio).

## Conservação

Se `N` alunos saem de A e entram em B:

- `matriculas[A] -= N` e `matriculas[B] += N`
- total de alunos do município constante
- nenhuma matrícula negativa

Asserts no código e testes em `tests/test_fundeb_ceara.py`.

## Motor

Cada cenário chama `simula_fundeb` sobre **todos** os entes, com os montantes oficiais de complementação do exercício e `modo_ponderador` do dataset (`nf` em 2024, `drec` em 2025+). Parâmetros de reescalonamento: `max_nse = min_nse = max_nf = min_nf = 1.0`.

Após cada simulação, `validar_interno` (RF-10) verifica soma de recursos estaduais, identidade do VAAF, participações e `recursos_fundeb = recursos_vaaf + complemento_uniao`. Simulação inválida interrompe o estudo.

## Famílias de cenários

1. `S0_BASELINE` — matrículas observadas.
2. Transições individuais A–D em 1%, 2%, …, 100% (e os pontos 5/10/20/30/50).
3. `OTIMO_FACTIVEL` — A–D simultâneas a 25/50/75/100%.
4. `OTIMO_MATEMATICO` — concentração teórica em cada uma das cinco etapas de maior peso (VAAF+VAAT). Marcado como não factível.
5. Sensibilidade — um aluno adicional na origem da transição, no baseline e após 50% convertido.
6. `G10` — as mesmas políticas aplicadas aos dez municípios de uma vez.
7. Maximin (equidade) — no grid G10 factível, escolhe-se o percentual que maximiza o menor Δ% entre os dez.

## Métricas

- `delta_R = R_cenario - R_base`
- `delta_R_percentual = 100 * delta_R / R_base`
- `ganho_por_aluno = delta_R / alunos_movidos` (indefinido se ninguém se move)
- Spillover: Δ dos demais 183 municípios cearenses, cinco maiores ganhos e perdas, soma municipal do Ceará

## Linearidade

Para cada município e transição, ajusta-se `delta_R` a uma reta no percentual convertido. R² ≥ 0,995 é o critério operacional de quase-linearidade. Segunda diferença e resíduos grandes sinalizam mudança de regime da equalização.

## Hipóteses

1. A expansão contrafactual do tempo integral altera a participação relativa do município nos recursos simulados; a magnitude depende da estrutura de matrículas e da redistribuição entre entes.
2. O ganho percentual associado à mesma alteração relativa pode diferir entre redes grandes e pequenas.

## O que o estudo não faz

Não recomenda transferir ou reclassificar alunos. Não estima custo da vaga integral nem efeito pedagógico. Não trata o ótimo matemático como política.
