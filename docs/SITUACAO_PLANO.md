# Situação do plano de implementação (v1.0, 26/09/2026)

Comparação entre o plano e o código da branch `maio2026` (commit `c0e65b7`), seguida do que esta branch acrescenta.

Legenda: **feito** (implementado e testado) · **parcial** (estrutura pronta, falta insumo ou decisão) · **pendente** (depende de terceiros ou de especificação).

## O que a `maio2026` já tinha

| Item do plano | Situação em `c0e65b7` |
|---|---|
| Dados de 2026 | **Existiam.** Matrículas FNDE (319 categorias), receita prevista da Portaria MEC/MF nº 6, de 29/04/2026, NSE e DREC oficiais, memória VAAT e lista de inabilitados com ajuste judicial (`dados/fundeb_dataset.py`). |
| Dados de 2025 | **Existiam.** Receita da Portaria nº 5/2026 (ajuste anual), NSE e DREC extraídos de PDF. Não há lista oficial de inabilitados ao VAAT. |
| Separação por exercício | **Parcial.** Rotas `/api/2025/...` e `/api/2026/...` e cache `data/{ano}/dataset.pkl` com versão do ETL. Não havia catálogo com fontes, hashes e situação da base. |
| Autenticação e perfis | **Existia.** Login por CPF; somente administradores simulam com pesos alterados. |
| Ajuste de matrículas de um ente | **Existia**, um ente por vez, por exercício. |
| Validação interna | **Existia.** O motor passou a recalcular o valor por aluno após o arredondamento, e o falso erro de VAAF não ocorre mais. |
| Comparação com valores oficiais | **Não existia.** O `cenario_atual` de 2025/2026 é gerado pelo próprio motor, então reproduzi-lo não mede a calibração. Os valores oficiais por ente estavam na planilha de receita, mas não eram usados. |
| Várias redes numa execução, comparativo nacional, exportações, cenários A–D, aviso metodológico | **Não existiam.** |
| Totais por UF (`gerar_dados_por_uf`) | Retiravam as redes inabilitadas ao VAAT dos totais financeiros. **Corrigido.** |

## Achados da auditoria (FND-01, FND-02, FND-04)

Detalhes e números em `docs/INVENTARIO_BASE.md`, gerado por `scripts/inventario_base.py`.

1. **2026: os totais nacionais batem com a receita oficial, mas não por ente.** Há diferenças de até R$ 52,8 milhões por ente, e 2.654 entes ficam acima de R$ 1.000.
   - **Pernambuco** tem a maior divergência: a complementação VAAF do fundo fica 2,94% abaixo da oficial, e a rede estadual fica R$ 52,8 milhões (−1,08%) abaixo. Isso confirma a divergência que a reunião atribuiu à conferência de Guido.
   - **Canavieiras (BA)** está inabilitada na lista de 2026, mas recebe R$ 18,0 milhões de VAAT na receita oficial (−29% no total do ente).
2. **2025: não há lista de inabilitados ao VAAT.** O critério de reserva não marca nenhuma rede, e 11 redes recebem VAAT só na simulação, entre elas Cubatão (SP), Pinhão (PR) e Oiapoque (AP). A complementação VAAF e a contribuição batem com o oficial.
3. **Montantes de 2026.** A constante `COMPLEMENTACAO_2026` (VAAF R$ 60,2 bi, VAAT R$ 63,3 bi, VAAR R$ 15,1 bi) diverge da soma da planilha de receita (R$ 30,1 bi, R$ 31,6 bi e R$ 7,5 bi). O sistema usa a soma da planilha, e a constante é só um valor de reserva. **É preciso confirmar qual montante corresponde ao exercício.**
4. **Parâmetros padrão da API antiga.** `SimulacaoRequest` usa os montantes de 2024 como padrão, inclusive nas rotas de 2025 e 2026. A interface envia os valores do exercício, mas uma chamada direta à API sem esses campos simula 2026 com os montantes de 2024. Nas rotas novas, os campos omitidos usam os valores do exercício. As rotas antigas não foram alteradas.
5. **Cadastro.** As redes estaduais foram identificadas pelo código IBGE da UF e verificadas nos três exercícios: 26 redes estaduais e a rede do DF. Não há identificadores duplicados. Em 2026 há 5.596 entes (um município a mais que em 2025).

## Situação por item do backlog

| Item | Situação | O que foi criado | O que falta |
|---|---|---|---|
| FND-01 Inventário | **feito** | `scripts/inventario_base.py` → `docs/INVENTARIO_BASE.md` para 2024, 2025 e 2026; checagens de duplicidade, cobertura e ausência no carregamento; linha de base da suíte registrada (30 testes; passam depois de instalar `odfpy`) | — |
| FND-02 Indicadores | **parcial** | Dicionário de indicadores (`services/comparacao.py`); ausência → `null`/“n/a”; percentual com denominador zero → não aplicável; tolerâncias provisórias (R$ 1.000 por ente e 0,5% por UF) | Aprovação das tolerâncias e das regras de `recursos_vaat`, VAAR e complementações |
| FND-03 Catálogo | **feito** | `data/catalogo.json`: exercício, publicação, situação, fontes e hashes dos arquivos em `20252026/`; `services/bases.py` recusa arquivo alterado sem atualizar o catálogo; escolha da base por `base_id` ou `ano_exercicio`; base ativa exibida na tela | — |
| FND-04 Calibração | **parcial** | `services/calibracao.py` e `GET /api/bases/{id}/calibracao`: comparação por ente, por UF e de elegibilidade VAAT com a receita oficial | Receita de agosto/2026 (João), conferência de PE (Guido), decisão sobre Canavieiras e sobre a lista de inabilitados de 2025 |
| FND-05 Contrato e serviço | **feito** | `schemas/cenarios.py`, `services/cenarios.py`; `POST /api/cenarios`, `GET /api/cenarios/{id}`; operações definir, acrescentar e converter; validações; ordem canônica; cópias da base; modo DREC/NF conforme o exercício; autenticação e restrição de pesos a administradores | Persistência (hoje ficam em memória os últimos 30 cenários) |
| FND-06 Edição de várias redes | **feito** | Aba “Cenário Nacional”: seletor de exercício, filtro das 319 categorias, edições mantidas ao trocar de UF, lista de pendências, totais separados (novas, retiradas, convertidas), aviso de controles alterados | Seleção do grupo Propag |
| FND-07 Comparação e recortes | **feito** | Recortes estaduais e DF, selecionadas e universo; soma para valores financeiros e razão de somas para valores por aluno; participação em p.p.; inspeção do universo | Recorte Propag bloqueado até a lista ser versionada em `grupos.propag` |
| FND-08 Exportações | **feito** | CSV (UTF-8 com BOM, `;`, decimal `,`, metadados em linhas `#`), XLSX (5 abas) e PDF paginado, gerados do resultado guardado; proteção contra fórmulas | Inspeção visual pelos usuários |
| FND-09 Termos e homologação | **parcial** | Aviso metodológico na tela, no PDF e nos metadados; termos “ente federado” e “rede estadual/municipal/do Distrito Federal” | Revisão com Marcele e Joyce |
| FND-10 Receita | **parcial** | Receita constante ou crescimento informado; rubricas escolhidas; complementações fixas ou acompanhando a taxa; fonte registrada | Opção fundamentada em PIB; regra oficial das complementações |
| FND-11 Cenários A–D | **feito** | A, B, C e D; efeitos B−A, C−A, D−A e D−C sem supor aditividade; participação e variação em p.p.; os quatro cenários nas exportações | — |
| FND-12 Censo preliminar | **pendente** | O catálogo aceita novas bases com `situacao: preliminar` | Base, dicionário e versão (Fabio) |
| FND-13 Trajetória de EPT | **pendente** | — | Definição da meta |
| FND-14 Fator amazônico | **pendente** | — | Norma e fórmula |

## Verificação (seção 7 do plano)

| Caso | Teste |
|---|---|
| Nenhum ajuste reproduz a referência (2024, 2025, 2026) | `test_sem_ajustes_b_igual_a`, `test_base_real_reproduz_referencia` |
| Ajuste em uma rede compatível com a rota anterior | `test_cenario_ajuste_unico_compativel_com_rota_anterior` (contra `/api/2026/simular/municipio`) |
| Ajustes simultâneos = execução direta | `test_ajustes_simultaneos_igual_execucao_direta` |
| Ordem dos ajustes | `test_ordem_dos_ajustes_nao_altera_resultado` |
| Conversão preserva total, sem negativos | `test_conversao_preserva_total_e_rejeita_negativo` |
| Nova matrícula | `test_nova_matricula_incrementa_total_sem_duplicar_linhas` |
| Identificador ausente ou repetido | `test_ente_ou_categoria_inexistente`, `test_identificador_repetido_rejeitado` |
| Dois cenários sem contaminação | `test_cenarios_distintos_sem_contaminacao`, `test_base_original_nao_e_alterada` |
| Crescimento zero (C = A, D = B) | `test_crescimento_zero_reproduz_base` |
| Denominador zero | `test_denominador_zero_nao_gera_infinito` |
| Exportações | `tests/test_exportacao.py`, `test_obter_e_exportar_mesmo_cenario` |
| Calibração oficial | `tests/test_calibracao.py` (totais batem; divergências por ente e de PE ficam expostas) |
| Autenticação e perfis | `test_rotas_exigem_autenticacao`, `test_pesos_alterados_so_para_admin` |

Tempo medido neste ambiente para um cenário A–D completo de 2026 com comparação: cerca de 0,6 s.
