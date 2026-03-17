# Documentação Completa — Simulador de Fatores de Ponderação do FUNDEB v2

Simulador para análise e projeção da distribuição dos recursos do FUNDEB (Fundo de Manutenção e Desenvolvimento da Educação Básica), regulamentado pela Lei n. 14.113/2020.

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [Estrutura do projeto](#2-estrutura-do-projeto)
3. [Telas e funcionalidades](#3-telas-e-funcionalidades)
4. [Simulações disponíveis](#4-simulações-disponíveis)
5. [Metodologia de cálculo](#5-metodologia-de-cálculo)
6. [API REST](#6-api-rest)
7. [Validação e testes](#7-validação-e-testes)
8. [Fontes de dados](#8-fontes-de-dados)

---

## 1. Visão geral

O simulador permite:

- Alterar **montantes** de complementação VAAF, VAAT e VAAR
- Ajustar **fatores de ponderação** (pesos por etapa/modalidade)
- Aplicar **NSE oficial por ente** (tabela anual) e simular **NF** (recursos vinculados)
- Alterar **matrículas** de um município e ver o impacto em todo o estado
- Comparar cenários com o **cenário atual** (dados oficiais de referência)
- Validar internamente a consistência dos resultados

**Tecnologias:** Backend FastAPI (Python), frontend HTML/CSS/JavaScript, Plotly.js para gráficos 2D e 3D, Bootstrap 5.

---

## 2. Estrutura do projeto

```
simulador-fundeb-v2/
├── main.py              # API FastAPI, rotas e lógica de negócio
├── simulador.py         # Motor de simulação (cálculos FUNDEB)
├── validacao.py         # Validação interna e comparação com dados oficiais
├── test_app.py          # Teste de integração da API
├── requirements.txt     # Dependências Python
├── data/                # Dados híbridos (xlsx + rda)
│   ├── dados_unificados.xlsx    # Base principal de matrículas/receitas
│   ├── pesos.rda                # Fatores de ponderação por etapa
│   ├── complementar.rda         # NF, inabilitados VAAT, peso VAAR (fallback)
│   ├── matriculas.rda           # Fallback para etapas ausentes no xlsx
│   ├── cenario_atual.rda        # Cenário de referência (oficial)
│   ├── cenario_atual_agregada.rda
│   └── cenario_ufs_atual.rda
├── PonderadorNSE 2024.pdf # NSE oficial por ente (IBGE)
├── tests/
│   └── test_requisitos.py   # Testes unitários (RF, RN, CA)
├── static/
│   ├── index.html       # Interface única (SPA)
│   ├── css/styles.css   # Estilos (tema Mocha Mousse)
│   └── js/
│       ├── app.js       # Lógica principal do frontend
│       ├── charts3d.js  # Gráficos 3D Plotly
│       └── explicacao.js # Texto explicativo da simulação municipal
└── documentacao.md      # Este arquivo
```

---

## 3. Telas e funcionalidades

### 3.1 Página principal (Início)

**Objetivo:** Apresentar o FUNDEB e o simulador.

**Conteúdo:**

- **O que é o FUNDEB:** Definição e Lei n. 14.113/2020
- **Objetivos:** Financiamento adequado, redução de desigualdades, equidade, qualidade
- **Características:** 27 fundos, distribuição por matrículas, 23% complementação federal, ponderações
- **Composição do FUNDEB:**
  - contribuição dos estados/municípios (FPM, FPE, ITR, IPI-exp, ITCMD, IPVA, ICMS)
  - complementação da União (VAAF 10%, VAAT 10,5%, VAAR 2,5%)
- **Modalidades VAAF, VAAT, VAAR:** Objetivo, funcionamento e distribuição
- **Implementação progressiva (2021–2026):** Tabela com evolução anual
- **Metodologia de cálculo das matrículas:** Censo, filtragem, ponderação, socioeconômico
- **Fatores de ponderação:** Etapas, modalidades, jornada, estabelecimento (urbano/rural)

**Ação:** Botão *"Ir para Simulação Principal"* leva à tela de simulação.

---

### 3.2 Simulação principal

**Objetivo:** Simular a distribuição do FUNDEB com parâmetros configuráveis.

**Painel esquerdo — Parâmetros:**

| Parâmetro | Descrição | Valor padrão |
|-----------|-----------|--------------|
| Montante VAAF (R$) | Complementação federal para VAAF | 24.153.287.047 |
| Montante VAAT (R$) | Complementação federal para VAAT | 18.114.965.285 |
| Montante VAAR (R$) | Complementação federal para VAAR | 0 |
| Fator Recursos Vinculados máximo | Limite superior do reescalonamento NF | 1,00 |

**Resultados exibidos:**

- **Infoboxes:** VAAT mínimo (simulado e atual), VAAF mínimo (simulado e atual), diferenças em %, complementação a municípios/estados, % de entes complementados
- **Validação interna (RF-10):** Status (OK/Falhou), erros, avisos e checagens
- **Gráficos 2D:** VAAF e VAAT médio por UF, diferença de complementação por UF, complementação por modalidade e destino
- **Tabelas:** Entes com resultado positivo/negativo (VAAF e VAAT), medidas resumo
- **Gráficos 3D:** Cubo VAAF×VAAT×Complementação, barras de complementação, mapa de ganhos/perdas

---

### 3.3 Ponderações (Pesos)

**Objetivo:** Ajustar os fatores de ponderação por etapa/modalidade.

**Conteúdo:**

- Sliders para **peso VAAF** e **peso VAAT** de cada etapa (ex.: Creche Integral, Creche Parcial, Pré-escola, Ensino Fundamental etc.)
- Faixa típica: 0,8 a 3,5 por etapa
- Os pesos definidos aqui são usados em todas as simulações (principal, VAAR, municipal) até que a aba *Pesos* seja alterada

**Impacto:** Altera as matrículas ponderadas, o rateio estadual, o VAAF, o VAAT e, indiretamente, a complementação da União.

---

### 3.4 Simulação VAAR

**Objetivo:** Simular cenários com montante de VAAR maior que zero.

**Parâmetros:**

| Parâmetro | Descrição |
|-----------|-----------|
| Montante total VAAR (R$) | Valor total a distribuir via VAAR |
| Montante VAAF (R$) | Usado na equalização VAAF |
| Montante VAAT (R$) | Usado na equalização VAAT |

**Resultados:**

- Total VAAR distribuído, VAAR para municípios e estados
- Gráfico de complementação por UF (VAAF + VAAT + VAAR empilhados)
- Proporção da VAAR no total da complementação por UF
- Gráficos 3D: distribuição VAAR por UF, top 120 entes por complementação
- Tabela: distribuição VAAR por ente (top 50)

**Distribuição VAAR:** Cada ente recebe `peso_vaar × complementacao_vaar`, em que `peso_vaar` vem dos dados (indicadores educacionais/SAEB). O somatório dos `peso_vaar` é 1.

---

### 3.5 Simulação municipal

**Objetivo:** Ver o impacto de alterar matrículas de um município em todo o estado.

**Fluxo:**

1. Selecionar **Estado** e **Município**
2. (Opcional) Ajustar montantes de complementação VAAF, VAAT e VAAR
3. (Opcional) Alterar **matrículas por etapa** do município
4. Clicar em **Simular**

**Resultados:**

- **Análise e explicação dos resultados:** Alterações nas matrículas, impacto em VAAF/VAAT/VAAR, mecanismos (VAAF estadual, VAAT nacional)
- **Comparação:** Cenário original vs ajustado (tabelas e gráficos)
- **Impacto no estado:** Tabela com todos os entes do estado e variação de recursos
- **Gráficos 3D:** Comparação original vs ajustado, impacto no estado

**Comportamento:** Qualquer alteração em matrículas ou pesos dispara recálculo completo do estado (total de matrículas, participações e distribuição).

---

### 3.6 Análise regional

**Objetivo:** Focar a análise em uma UF específica.

**Uso:** Executar primeiro uma simulação principal e, em seguida, escolher a UF no filtro. São exibidos infoboxes e gráficos apenas para a UF selecionada.

---

### 3.7 Documentação (na interface)

**Conteúdo:** Resumo do FUNDEB, VAAF, VAAT, VAAR, simulação municipal e links para fontes oficiais (FNDE, MEC).

---

## 4. Simulações disponíveis

| Simulação | Endpoint API | Parâmetros principais |
|-----------|--------------|------------------------|
| **Principal** | `POST /api/simular` | complementacao_vaaf, complementacao_vaat, complementacao_vaar, max_nf, min_nf, pesos_vaaf, pesos_vaat |
| **Completa** | `POST /api/simular/completo` | Idem; retorna todos os entes |
| **Municipal** | `POST /api/simular/municipio` | ibge, matriculas_ajustadas, demais parâmetros |

---

## 5. Metodologia de cálculo

### 5.1 Visão geral do fluxo

```
Matrículas brutas → Ponderação por etapa → Ponderação NSE/NF
    → Rateio estadual (recursos fixos) → Equalização VAAF
    → Equalização VAAT → Distribuição VAAR → Resultados finais
```

### 5.2 Matrículas ponderadas

**Por etapa (VAAF e VAAT):**

\[
\text{matrículas\_vaaf} = \sum_{\text{etapas}} \text{matrícula}_e \times \text{peso\_vaaf}_e
\]

\[
\text{matrículas\_vaat} = \sum_{\text{etapas}} \text{matrícula}_e \times \text{peso\_vaat}_e
\]

**Ponderação sociofiscal:**

- VAAF: `matrículas_vaaf × NSE × NF`
- VAAT: `matrículas_vaat × NSE`

NSE é aplicado por ente com valor oficial anual (sem edição/reescala).  
NF é reescalonado no intervalo `[min_nf, max_nf]` (min-max).

### 5.3 Rateio municipal da receita estadual

A receita estadual do fundo é fixa. A participação de cada município é:

\[
\text{participação} = \frac{\text{matrículas\_ponderadas\_município}}{\text{matrículas\_ponderadas\_estado}}
\]

\[
\text{recursos\_vaaf\_mun} = \text{participação} \times \text{recursos\_estado\_vaaf}
\]

### 5.4 Equalização VAAF

1. Ordenar os **27 fundos estaduais** pelo VAAF inicial (recursos/matrículas).
2. De baixo para cima, complementar até igualar ao próximo fundo ou esgotar o montante da União.
3. Redistribuir o recurso equalizado **dentro de cada estado** aos municípios, mantendo o rateio por matrículas ponderadas.

**VAAF municipal final:**

\[
\text{vaaf\_final} = \frac{\text{recursos\_vaaf\_final}}{\text{matrículas\_vaaf}}
\]

### 5.5 Equalização VAAT

1. Calcular o VAAT pré-complementação: `recursos_vaat / matrículas_vaat` por ente.
2. Ordenar os **~5.570 entes** por esse VAAT.
3. Complementar de baixo para cima até igualar ou esgotar o montante.
4. Entes com `inabilitados_vaat = true` não recebem complementação VAAT.

**VAAT final:**

\[
\text{vaat\_final} = \frac{\text{recursos\_vaat\_final}}{\text{matrículas\_vaat}}
\]

### 5.6 Distribuição VAAR

\[
\text{complemento\_vaar}_i = \text{peso\_vaar}_i \times \text{complementação\_vaar\_total}
\]

Em que `peso_vaar` é o coeficiente do ente (soma = 1).

### 5.7 Recursos finais

\[
\text{complemento\_uniao} = \text{complemento\_vaaf} + \text{complemento\_vaat} + \text{complemento\_vaar}
\]

\[
\text{recursos\_fundeb} = \text{recursos\_vaaf} + \text{complemento\_uniao}
\]

---

## 6. API REST

### 6.1 Dados

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/estados` | Lista UFs e regiões |
| GET | `/api/municipios?uf=XX` | Lista municípios da UF |
| GET | `/api/pesos` | Fatores de ponderação |
| GET | `/api/etapas` | Nomes das etapas |
| GET | `/api/municipio/{ibge}/matriculas` | Matrículas e dados complementares do município |
| GET | `/api/cenario-atual/resumo` | Resumo do cenário atual |

### 6.2 Simulação

| Método | Rota | Corpo (JSON) |
|--------|------|--------------|
| POST | `/api/simular` | `complementacao_vaaf`, `complementacao_vaat`, `complementacao_vaar`, `max_nf`, `min_nf`, `pesos_vaaf?`, `pesos_vaat?` |
| POST | `/api/simular/completo` | Idem; retorna todos os entes |
| POST | `/api/simular/municipio` | `ibge`, `matriculas_ajustadas?`, demais parâmetros |

### 6.3 Resposta de `POST /api/simular`

- `resumo`: métricas agregadas (VAAF/VAAT mínimos, complementações, etc.)
- `por_uf`: dados agregados por UF
- `vencedores_perdedores`: entes com ganho/perda em VAAF e VAAT
- `complementacao_por_uf`: complementação por UF
- `complementacao_destino`: complementação para municípios vs estados
- `diferenca_uf`: diferença em relação ao cenário atual
- `dados_tabela`: amostra dos dados (até 200 entes)
- `validacao`: resultado da validação interna (valido, erros, avisos, checagens)

---

## 7. Validação e testes

### 7.1 Validação interna (RF-10)

O módulo `validacao.py` verifica:

1. **Soma de recursos por UF:** soma de `recursos_vaaf` dos municípios = total estadual
2. **VAAF:** `vaaf_final = recursos_vaaf_final / matriculas_vaaf`
3. **Participações:** soma das participações por UF = 100%
4. **Recursos FUNDEB:** `recursos_fundeb = recursos_vaaf + complemento_uniao`

O resultado é retornado em `validacao` na resposta da API e exibido no card de validação na interface.

### 7.2 Comparação com dados oficiais (CA-05)

A função `comparar_com_oficial()` em `validacao.py` permite comparar a simulação com um DataFrame de dados oficiais (por `ibge`). A estrutura está pronta para uso quando houver dados publicados.

### 7.3 Testes unitários

Executar:

```bash
python -m pytest tests/test_requisitos.py -v
```

**Testes incluídos:**

- CA-02: Participação 1000/10000 = 10%, 1100/10100 ≈ 10,89%
- Soma de recursos = total estadual
- VAAF = recursos/matrículas
- RN-03: alteração em um município redistribui todos
- Validação interna retorna resultado coerente

---

## 8. Fontes de dados

- **Matrículas:** Portaria interministerial n. 1/2024 — [FNDE](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/matriculas-da-educacao-basica)
- **Receitas:** Portal FNDE — [FUNDEB 2024](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2024-1)
- **Pesos:** Resolução MEC n. 04/2023 — [CIFUNDEB](https://www.gov.br/mec/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-intergovernamental-fundeb/Resoluo4_30102023.pdf)
- **NSE:** `PonderadorNSE 2024.pdf` (por ente, chave IBGE)

---

## Créditos

Desenvolvido pelo IFCE, prof. João Cláudio Nunes Carvalho.  
Motor de simulação baseado no pacote R [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2).
