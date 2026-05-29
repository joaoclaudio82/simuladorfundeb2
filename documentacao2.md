# Documentação completa do Simulador FUNDEB v2

**Versão didática e detalhada** — explica o que o aplicativo faz, como cada tela funciona, de onde vêm os dados e como os cálculos são realizados, passo a passo.

> **Público:** gestores, analistas, professores e desenvolvedores que precisam entender o simulador sem ler o código-fonte.  
> **Complementa:** `documentacao.md` (referência técnica resumida) e `explicacao.md` (roteiro para apresentações).

---

## Índice

1. [O que é este aplicativo](#1-o-que-é-este-aplicativo)
2. [O FUNDEB em linguagem simples](#2-o-fundeb-em-linguagem-simples)
3. [Como entrar e quem pode fazer o quê](#3-como-entrar-e-quem-pode-fazer-o-quê)
4. [Visão da interface: menu lateral](#4-visão-da-interface-menu-lateral)
5. [Telas do FUNDEB 2024](#5-telas-do-fundeb-2024)
6. [Telas do FUNDEB 2026 e consulta 2025](#6-telas-do-fundeb-2026-e-consulta-2025)
7. [Administração de usuários](#7-administração-de-usuários)
8. [Arquitetura do sistema](#8-arquitetura-do-sistema)
9. [De onde vêm os dados](#9-de-onde-vêm-os-dados)
10. [Como a simulação calcula tudo (passo a passo)](#10-como-a-simulação-calcula-tudo-passo-a-passo)
11. [O algoritmo de equalização explicado](#11-o-algoritmo-de-equalização-explicado)
12. [Simulação municipal: o que muda quando você altera matrículas](#12-simulação-municipal-o-que-muda-quando-você-altera-matrículas)
13. [Gráficos, tabelas e validação automática](#13-gráficos-tabelas-e-validação-automática)
14. [API REST e integração](#14-api-rest-e-integração)
15. [Como executar e configurar](#15-como-executar-e-configurar)
16. [Glossário](#16-glossário)
17. [Referências legais e de dados](#17-referências-legais-e-de-dados)

---

## 1. O que é este aplicativo

O **Simulador de Fatores de Ponderação do FUNDEB v2** é uma aplicação web que reproduz, em computador, a lógica de distribuição dos recursos do **Fundo de Manutenção e Desenvolvimento da Educação Básica (FUNDEB)**.

### O que você consegue fazer na prática

| Ação | Para que serve |
|------|----------------|
| Alterar **montantes** de complementação federal (VAAF, VAAT, VAAR) | Ver quanto cada estado/município receberia se a União destinasse outros valores |
| Ajustar **pesos de ponderação** por etapa/modalidade | Testar políticas que valorizam mais creche, ensino integral, educação do campo etc. |
| Simular com **NSE** (nível socioeconômico) e **NF/DREC** oficiais | Refletir a capacidade fiscal e o contexto social de cada ente |
| Mudar **matrículas** de um município | Entender o efeito em cascata: um município que “ganha” matrículas altera o fundo estadual inteiro |
| Comparar com o **cenário atual** (dados oficiais de referência) | Medir ganhos e perdas em relação ao que já foi publicado |
| Ver **validação automática** dos resultados | Conferir se a matemática interna está coerente |

### Tecnologias (visão geral)

- **Backend:** Python + FastAPI (`main.py`, `api_simulacao.py`, `simulador.py`)
- **Dados:** planilhas Excel, arquivos R legados (`.rda`), PDF do NSE, SQLite de usuários
- **Frontend:** HTML estático + JavaScript (`app.js`, `app_multi_ano.js`, `auth.js`)
- **Gráficos:** Plotly.js (2D e 3D)
- **Interface:** Bootstrap 5, tema visual “Mocha Mousse”, menu lateral fixo

O motor de cálculo é uma reimplementação em Python do pacote R [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2), mantendo a mesma sequência lógica de equalização.

---

## 2. O FUNDEB em linguagem simples

### 2.1 O que é o fundo

O FUNDEB é o principal mecanismo de **financiamento da educação básica pública** no Brasil, criado pela **Lei nº 14.113/2020**. Cada estado (e o Distrito Federal) tem um **fundo estadual**; municípios e o próprio estado recebem recursos conforme suas matrículas e regras de ponderação.

### 2.2 De onde vem o dinheiro

1. **Contribuição dos entes** (~20% de impostos estaduais e municipais: ICMS, IPVA, FPM, FPE etc.)
2. **Complementação da União** — hoje até **23%** do total do fundo, distribuída em três “fatias”:
   - **VAAF** — Valor Aluno Ano do Fundeb (equalização entre **fundos estaduais**)
   - **VAAT** — Valor Aluno Ano Total (equalização entre **todos os entes**, incluindo municípios)
   - **VAAR** — Valor Aluno Ano Resultado (mérito: indicadores de aprendizagem e redução de desigualdades)

A implementação progressiva da complementação evoluiu de 2021 até atingir 23% a partir de 2026 (tabela na **Página Principal** do app).

### 2.3 Por que “fatores de ponderação”

Nem toda matrícula “pesa” igual. Uma vaga em **creche integral** ou em **educação do campo** pode contar mais no cálculo do que uma vaga em ensino regular parcial. Os **pesos VAAF e VAAT** (por etapa/segmento) transformam matrículas brutas em **matrículas ponderadas**, que entram nas fórmulas de rateio.

Além disso, cada ente tem:

- **NSE** (Ponderador de Nível Socioeconômico) — reflete vulnerabilidade social; multiplica matrículas VAAF e VAAT.
- **NF** (2024) ou **DREC** (2025+) — Disponibilidade de Recursos; no VAAF, penaliza ou beneficia entes com mais receita própria vinculada à educação.

### 2.4 As três modalidades em uma frase

| Modalidade | Escala | Ideia central |
|------------|--------|----------------|
| **VAAF** | Fundo estadual (27 UFs) | Igualar o “valor aluno” **dentro do estado** após a União complementar os fundos mais pobres **entre estados** |
| **VAAT** | Nacional (municípios + estados) | Igualar o “valor aluno total” (FUNDEB + outras receitas vinculadas) **em todo o país** |
| **VAAR** | Entes elegíveis | Distribuir bônus por **resultado educacional**, conforme peso VAAR de cada ente |

---

## 3. Como entrar e quem pode fazer o quê

### 3.1 Login

1. Acesse `http://localhost:8000` (ou o endereço do servidor).
2. Se não estiver autenticado, será redirecionado para **`/login.html`**.
3. Informe **CPF** (11 dígitos, com ou sem máscara) e **senha**.
4. O servidor valida as credenciais, grava um **cookie httpOnly** (`fundeb_token`, JWT) e libera o simulador.

**Primeiro acesso (banco vazio):** o sistema cria um administrador inicial usando variáveis de ambiente (padrão de desenvolvimento: CPF `529.982.247-25`, senha `admin123`). **Altere a senha** após o primeiro login.

### 3.2 Perfis

| Recurso | Administrador | Usuário comum |
|---------|:-------------:|:-------------:|
| Ver simulador e todas as abas de consulta | Sim | Sim |
| Editar ponderações (pesos VAAF/VAAT) | Sim | Não (somente leitura) |
| Enviar pesos customizados na simulação | Sim (API aplica) | Não (API usa pesos oficiais) |
| Simular VAAF/VAAT/VAAR/Municipal/Regional | Sim | Sim |
| Cadastrar, editar e excluir usuários | Sim | Não |

**Defesa em profundidade:** mesmo que alguém altere o HTML no navegador, o backend ignora `pesos_vaaf` e `pesos_vaat` customizados quando o perfil não é `admin` (`preparar_pesos` em `api_simulacao.py`).

### 3.3 Sair e gerenciar usuários

- **Sair:** link “Sair” no rodapé da barra lateral → encerra a sessão.
- **Usuários:** menu visível só para admin → página `/admin.html` (cadastro, edição, ativar/desativar, reset de senha).

---

## 4. Visão da interface: menu lateral

A barra lateral esquerda (**sidebar**) concentra toda a navegação. No topo aparecem o título **FUNDEB** e o nome/perfil do usuário logado.

### Estrutura do menu (de cima para baixo)

```
┌─────────────────────────────────────┐
│  FUNDEB — Simulador v2              │
├─────────────────────────────────────┤
│  🏠 Página Principal                │
├─ FUNDEB 2024 ───────────────────────┤
│  🧮 Simulação Principal             │
│  ⚖️  Ponderações                    │
│  🏆 Simulação VAAR                  │
│  📍 Simulação Municipal             │
│  🗺️  Análise Regional              │
├─ FUNDEB 2026 ───────────────────────┤  ← injetado por app_multi_ano.js
│  🧮 Simulação 2026                  │
│  ⚖️  Ponderações 2026               │
│  🏆 VAAR 2026                       │
│  📍 Município 2026                  │
├─ FUNDEB 2025 ───────────────────────┤
│  📅 Consulta 2025                   │
│  ⚖️  Ponderações 2025               │
├─────────────────────────────────────┤
│  📖 Documentação                    │
│  👥 Usuários (só admin)             │
├─────────────────────────────────────┤
│  🚪 Sair                            │
│  Créditos / Lei 14.113/2020         │
└─────────────────────────────────────┘
```

**Comportamento:** clicar em um item troca o painel central (`tab-content`). Em celular, o menu abre/fecha com o botão ☰ na barra superior; um fundo escuro fecha o menu ao tocar fora.

**Rótulos cinza** (`FUNDEB 2024`, `FUNDEB 2026` etc.) são apenas títulos — não são clicáveis.

---

## 5. Telas do FUNDEB 2024

O exercício **2024** é o núcleo histórico do simulador: **41 etapas** de matrícula, ponderador **NF** no VAAF, montantes padrão da complementação de 2024.

### 5.1 Página Principal (`#tab-inicio`)

**Função:** material introdutório — não executa cálculos.

**Conteúdo didático:**

- Definição do FUNDEB e objetivos (financiamento, equidade, qualidade)
- Composição do fundo (impostos dos entes + complementação federal)
- Explicação das modalidades VAAF, VAAT e VAAR
- Tabela da **implementação progressiva** da complementação (2021–2026+)
- Metodologia de contagem de matrículas (Censo, filtros, ponderações)

**Atalho:** botões “Ir para Simulação” usam `data-tab="simulacao"` para abrir a simulação principal sem passar pelo menu.

---

### 5.2 Simulação Principal (`#tab-simulacao`)

**Função:** simular **todo o país** com os parâmetros que você definir.

#### Painel esquerdo — Parâmetros

| Campo | Significado | Efeito no cálculo |
|-------|-------------|-------------------|
| **Montante VAAF (R$)** | Quanto a União destina à equalização entre **fundos estaduais** | Entra em `equaliza_fundo` no nível UF |
| **Montante VAAT (R$)** | Quanto a União destina à equalização **nacional** por ente | Equalização por `ibge` (município/estado) |
| **Montante VAAR (R$)** | Total da complementação por resultado | `complemento_vaar = peso_vaar × montante` |
| **NF máximo / mínimo** | Intervalo do reescalonamento do NF | Só 2024: NF é esticado linearmente entre min e max antes de multiplicar o VAAF |

Os valores padrão de VAAF e VAAT vêm dos dados oficiais carregados no startup (~R$ 24 bi e ~R$ 18 bi em 2024).

#### Painel direito — Resultados (após clicar “Simular”)

1. **Caixas resumo (infoboxes)**  
   - Menor VAAT e menor VAAF do país (simulado)  
   - Comparação com o cenário atual (referência oficial)  
   - Diferenças percentuais  
   - Quanto foi para municípios vs estados  
   - Percentual de entes que receberam complementação  

2. **Validação interna (RF-10)**  
   - Status **OK** ou **Falhou**  
   - Lista de erros, avisos e checagens realizadas (ver [seção 13](#13-gráficos-tabelas-e-validação-automática))  

3. **Gráficos 2D (Plotly)**  
   - VAAF e VAAT médio por UF  
   - Diferença de complementação por UF  
   - Complementação por modalidade e por tipo de ente (estado/município)  

4. **Tabelas**  
   - Maiores ganhadores e perdedores (VAAF e VAAT)  
   - Medidas resumo agregadas  

5. **Gráficos 3D** (`charts3d.js`)  
   - Cubo VAAF × VAAT × Complementação  
   - Barras de complementação  
   - Mapa de ganhos/perdas  

**Fluxo técnico:** o botão chama `POST /api/simular` com JSON dos parâmetros e, se admin, dos vetores `pesos_vaaf` e `pesos_vaat` lidos da aba Ponderações.

---

### 5.3 Ponderações (`#tab-pesos`)

**Função:** visualizar e (se admin) editar os **fatores de ponderação** das **41 etapas** de 2024.

**Layout:** acordeão Bootstrap agrupado por **família de segmento** (ex.: “Creche”, “Ensino Fundamental Anos Iniciais”) — vários segmentos por família (Urbano, Rural, Campo, Indígena…).

Cada segmento tem dois campos numéricos:

- **Peso VAAF** — usado na coluna `matriculas_vaaf`
- **Peso VAAT** — usado na coluna `matriculas_vaat`

**Usuário comum:** campos desabilitados + banner azul: *“Somente administradores podem alterar os fatores de ponderação.”* O `getPesos()` ignora o DOM e envia sempre os valores oficiais carregados do servidor.

**Administrador:** alterações aqui são enviadas nas próximas simulações (principal, VAAR, municipal, regional).

---

### 5.4 Simulação VAAR (`#tab-vaar`)

**Função:** focar na distribuição da **complementação VAAR** (mérito).

**Parâmetros:** montantes VAAR, VAAF e VAAT (para contexto; a VAAR em si usa o campo VAAR dedicado).

**Resultados típicos:**

- Distribuição da VAAR por UF  
- Participação da VAAR no total da complementação  
- Tabelas (ex.: top 50 entes) e gráficos 2D/3D  

**API:** `POST /api/simular/completo` — retorna uma linha por ente com todas as colunas do motor (útil para exportação mental ou tabelas grandes).

---

### 5.5 Simulação Municipal (`#tab-municipio`)

**Função:** responder à pergunta: *“Se eu mudar as matrículas deste município, o que acontece com ele e com os outros entes do estado?”*

#### Passo a passo na tela

1. Escolher **UF** (lista agrupada por região: Norte, Nordeste…)  
2. Escolher **município** (carrega `GET /api/municipio/{ibge}/matriculas`)  
3. Ver matrículas por **segmento** no acordeão (editáveis)  
4. Ajustar parâmetros VAAF/VAAT/VAAR se desejar  
5. Clicar **Simular**

#### O que o sistema compara

| Cenário | Descrição |
|---------|-----------|
| **Original** | Matrículas oficiais do município |
| **Ajustado** | Matrículas que você digitou |

Para **cada cenário**, o motor roda a simulação **inteira do país** (não só o município), porque a equalização VAAF redistribui o fundo estadual completo.

#### Painéis de saída

- Cards com VAAF, VAAT, complementos e recursos finais (antes/depois)  
- Texto explicativo passo a passo (`explicacao.js`) — mostra matrículas ponderadas, coeficiente no estado, VAAF-MIN etc.  
- Gráficos comparativos e tabela de **impacto nos outros entes da UF**  
- Visualização 3D opcional  

**API:** `POST /api/simular/municipio` com `ibge` e `matriculas_ajustadas` (dicionário etapa → valor).

---

### 5.6 Análise Regional (`#tab-regional`)

**Função:** visão **por estado (UF)** dos resultados da última simulação principal.

1. Ao abrir o app, uma simulação com **parâmetros padrão** é pré-carregada em segundo plano (`garantirDadosRegional`).  
2. Selecione a UF no dropdown.  
3. Veja resumo de recursos, complementação e comparação com cenário atual para aquela UF.

**Importante:** usa os dados da simulação **2024 principal** guardada em memória (`state.ultimaSimulacao`). Se você simular de novo na aba principal, a análise regional é atualizada automaticamente.

*(Análise regional para 2026 ainda não foi implementada — apenas 2024.)*

---

### 5.7 Documentação (`#tab-documentacao`)

**Função:** texto de apoio dentro do próprio app (links para portarias, FNDE, créditos). Não substitui este arquivo `documentacao2.md`.

---

## 6. Telas do FUNDEB 2026 e consulta 2025

As abas 2025/2026 são **injetadas dinamicamente** por `app_multi_ano.js` ao carregar a página (menu + painéis HTML). Usam rotas `/api/2026/...` e `/api/2025/...`.

### 6.1 Diferenças em relação a 2024

| Aspecto | 2024 | 2026 | 2025 |
|---------|------|------|------|
| Etapas/segmentos | 41 | **319** únicos no motor | 319 (consulta) |
| Ponderador fiscal VAAF | **NF** (reescalonável) | **DREC** (oficial, fixo) | DREC (dados carregados) |
| Simulação | Ativa | Ativa | **Bloqueada** (503) |
| Montantes padrão | Legado 2024 | Portaria MEC/MF nº 6/2026 | — |
| NSE | PDF 2024 | Planilha `ponderador-de-nivel-socioeconomico.xlsx` | Idem |

**Fórmulas 2026 (VAAF):**  
`matriculas_vaaf = (matrículas × pesos_vaaf) × NSE × DREC`  
**VAAT:**  
`matriculas_vaat = (matrículas × pesos_vaat) × NSE`

### 6.2 Simulação 2026 (`#tab-simulacao-2026`)

Equivalente à simulação principal de 2024, com:

- Defaults de complementação vindos de `GET /api/2026/meta`  
- Campo DREC exibido como fixo (não há slider de NF)  
- Validação RF-10 e gráficos por UF  
- Pesos editáveis na aba **Ponderações 2026** (admin)

### 6.3 Ponderações 2026 (`#tab-pesos-2026`)

- **319 segmentos** em acordeão por família  
- Mesma regra de permissão (admin edita / usuário só lê)  
- Fonte: aba **FPs** da planilha `Matrículas Fundeb 2025 e 2026.xlsx` (6 duplicatas removidas no ETL → 319 slugs únicos)

### 6.4 VAAR 2026 (`#tab-vaar-2026`)

Interface espelhada da VAAR 2024, mas dados e montantes de **2026**. Usa `POST /api/2026/simular/completo`.

### 6.5 Município 2026 (`#tab-municipio-2026`)

Paridade com municipal 2024, com extras:

- Parâmetros VAAF/VAAT/VAAR na própria aba  
- Edição por **segmento** (não por família agregada)  
- Toggle **“Mostrar segmentos sem matrícula”** — exibe todas as 319 etapas; as zeradas aparecem destacadas  
- Contador: quantos segmentos têm matrícula naquele município  
- Explicação textual menciona **DREC** em vez de NF  

### 6.6 Consulta 2025 (`#tab-simulacao-2025`, `#tab-pesos-2025`)

**Somente leitura.** Banner amarelo explica que receitas e ponderadores oficiais de 2025 ainda não estão disponíveis; matrículas podem ser consultadas. Botão **Simular** desabilitado; `POST /api/2025/simular` retorna HTTP **503**.

---

## 7. Administração de usuários

**URL:** `/admin.html` (somente administradores).

### 7.1 Cadastro (coluna esquerda)

| Campo | Regra |
|-------|-------|
| CPF | 11 dígitos, válido (dígitos verificadores) |
| Nome | Opcional |
| Senha | Mínimo 6 caracteres |
| Perfil | `usuario` (padrão) ou `admin` |

### 7.2 Lista (coluna direita)

Tabela com todos os usuários e ações:

| Botão | Ação |
|-------|------|
| ✏️ Editar | Abre modal: nome, perfil, ativo, senha opcional |
| 🔑 | Reset rápido de senha (prompt) |
| 🚫 / ✓ | Desativar ou reativar |
| 🗑️ | Excluir (bloqueado para si mesmo e para o último admin) |

**Regras de segurança no servidor:**

- Não desativar/excluir a si mesmo  
- Não remover o **último** administrador ativo  
- Usuário inativo não faz login (HTTP 403)

---

## 8. Arquitetura do sistema

```
┌──────────────┐     cookie JWT      ┌─────────────────────────────────┐
│   Browser    │ ◄──────────────────►│  FastAPI (main.py)              │
│  index.html  │   /api/* JSON       │  ├── auth/routes.py             │
│  app.js      │                     │  ├── api_simulacao.py (2025/26) │
│  auth.js     │                     │  └── rotas 2024 em main.py      │
└──────────────┘                     └──────────────┬──────────────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────┐
                    ▼                               ▼                       ▼
            ┌───────────────┐              ┌──────────────┐        ┌─────────────┐
            │ simulador.py  │              │ fundeb_      │        │ usuarios.db │
            │ (motor)       │◄─────────────│ dataset.py   │        │ (SQLite)    │
            └───────────────┘              │ (ETL/cache)  │        └─────────────┘
                    ▲                      └──────────────┘
                    │
            ┌───────────────┐
            │ validacao.py  │
            └───────────────┘
```

### Arquivos principais

| Arquivo | Papel |
|---------|-------|
| `main.py` | App FastAPI, rotas 2024, montagem de estáticos, startup do banco de usuários |
| `api_simulacao.py` | Rotas por ano, `executar_simulacao`, `preparar_pesos`, resposta agregada da simulação |
| `simulador.py` | Motor matemático (`simula_fundeb` e funções auxiliares) |
| `dados/fundeb_dataset.py` | Carrega Excel/RDA/PDF, monta `FundebDataset`, cache `dataset.pkl` |
| `validacao.py` | Checagens RF-10 após cada simulação |
| `auth/*` | Login, JWT, CRUD usuários |
| `static/js/app.js` | Lógica UI 2024 |
| `static/js/app_multi_ano.js` | UI 2025/2026 |
| `static/js/auth.js` | Sessão, `apiFetch`, guards |
| `static/js/explicacao.js` | Narrativa da simulação municipal |
| `static/js/charts3d.js` | Gráficos 3D Plotly |

---

## 9. De onde vêm os dados

### 9.1 Exercício 2024 (pasta `data/`)

| Fonte | Conteúdo |
|-------|----------|
| `dados_unificados.xlsx` | Matrículas, receitas, chave IBGE |
| `pesos.rda` | Pesos VAAF/VAAT por etapa |
| `complementar.rda` | NF, inabilitados VAAT, peso VAAR |
| `matriculas.rda` | Fallback de etapas |
| `cenario_atual*.rda` | Referência oficial para comparação |
| `PonderadorNSE 2024.pdf` | NSE por IBGE |

### 9.2 Exercícios 2025 e 2026 (pasta `20252026/`)

| Arquivo | Uso |
|---------|-----|
| `Matrículas Fundeb 2025 e 2026.xlsx` | Matrículas + aba FPs (pesos) |
| `ponderador-de-nivel-socioeconomico.xlsx` | NSE |
| `ponderador-de-disponibilidade-de-recursos.xlsx` | DREC |
| `1-receita-total-do-fundeb-por-ente-federado.xlsx` | Receitas |
| `MemriadeClculoVAAT2026 (2).xlsx` | Memória VAAT / cenário atual |

Após o primeiro carregamento, o ETL grava cache em `data/2026/dataset.pkl` (e `data/2025/`) para acelerar reinícios.

### 9.3 Usuários

- SQLite: `data/usuarios.db`  
- Tabela `users`: cpf, password_hash (bcrypt), role, nome, ativo, created_at  

---

## 10. Como a simulação calcula tudo (passo a passo)

Tudo converge na função **`simula_fundeb`** (`simulador.py`). Abaixo, a sequência **na ordem em que o computador executa**.

### Etapa 1 — Matrículas ponderadas por segmento

Para cada ente (município ou estado), há um vetor com o número de matrículas em cada etapa (ex.: `creche_integral`, `fundamental_anos_iniciais_urbano`…).

Multiplica-se pela matriz de pesos:

```
matriculas_vaaf = Σ (matrícula_etapa × peso_vaaf_etapa)
matriculas_vaat = Σ (matrícula_etapa × peso_vaat_etapa)
```

**Implementação:** produto matricial `matriz @ vetor_pesos` em `pondera_matriculas_etapa`.

**Intuição:** soma “pesos” de todas as modalidades em dois índices diferentes (VAAF e VAAT podem dar pesos distintos à mesma etapa).

---

### Etapa 2 — Ponderadores sociofiscais (NSE e NF ou DREC)

Cada ente traz, na tabela complementar:

- `nse` — Ponderador de Nível Socioeconômico (≥ 1 para entes mais vulneráveis)  
- `nf` (2024) ou `drec` (2026) — disponibilidade de recursos  

**2024 — com reescalonamento do NF:**

O NF original é comprimido/esticado linearmente para o intervalo `[min_nf, max_nf]` (parâmetros da tela, padrão 0,95–1,05):

```
NF_reescalado = min + (max - min) × (NF - NF_mínimo) / (NF_máximo - NF_mínimo)
```

Depois:

```
matriculas_vaaf ← matriculas_vaaf × NSE × NF_reescalado
matriculas_vaat ← matriculas_vaat × NSE
```

**2026 — DREC fixo:**

```
matriculas_vaaf ← matriculas_vaaf × NSE × DREC
matriculas_vaat ← matriculas_vaat × NSE
```

**Intuição:** entes mais pobres (NSE alto) “contam mais” matrículas; entes ricos (DREC/NF baixo no VAAF) “contam menos” na parcela VAAF.

---

### Etapa 3 — Fundo estadual (agregação por UF)

Para cada estado:

```
matriculas_estado_vaaf = soma(matriculas_vaaf dos entes da UF)
recursos_estado_vaaf   = soma(recursos_vaaf iniciais dos entes da UF)
vaaf_estado_inicial    = recursos_estado_vaaf / matriculas_estado_vaaf
```

**Intuição:** calcula o “valor aluno” médio do fundo estadual **antes** da complementação federal VAAF.

---

### Etapa 4 — Equalização VAAF (entre estados)

Entrada: tabela com 27 UFs ordenadas pelo `vaaf_estado_inicial` (menor = mais necessitado).

A União dispõe de um **montante fixo** (`complementacao_vaaf`). O algoritmo (`equaliza_fundo`) pergunta, de forma acumulada:

> “Se eu subisse todos os fundos até o patamar do próximo estado, quanto precisaria?”

Enquanto a necessidade acumulada for **menor** que o montante, esses estados são **complementados** e passam a dividir os recursos de forma que fiquem com o **mesmo valor aluno** entre si (após complementação).

Estados que “sobram” fora do bolsa mantêm o recurso original.

**Saída:** `recursos_pos` por UF — total de recursos VAAF do fundo após a complementação da União.

---

### Etapa 5 — Redistribuição intraestadual do VAAF

Cada município/estado recebe uma fatia do `recursos_pos` da sua UF proporcional às suas `matriculas_vaaf`:

```
recursos_vaaf_final = matriculas_vaaf × (recursos_pos_UF / matriculas_estado_vaaf)
vaaf_final          = recursos_vaaf_final / matriculas_vaaf
```

**Intuição:** primeiro equaliza **entre estados**; depois reparte **dentro** do estado conforme matrículas ponderadas.

---

### Etapa 6 — VAAT pré-complementação

```
vaat_pre = recursos_vaat / matriculas_vaat
```

Usa receitas vinculadas à educação já existentes no ente (não só FUNDEB).

---

### Etapa 7 — Equalização VAAT (entre todos os entes)

Mesmo algoritmo da etapa 4, mas:

- Ordenação por `vaat_pre`  
- Montante = `complementacao_vaat`  
- Identificador = `ibge` (cada município/estado)  
- **Excluídos:** entes com `inabilitados_vaat = true` (não recebem complementação VAAT)

Resultado: `recursos_vaat_final` e `vaat_final`.

---

### Etapa 8 — Complementação VAAR

Cada ente tem um `peso_vaar` (quanto do total da VAAR ele pode receber, conforme indicadores):

```
complemento_vaar = peso_vaar × complementacao_vaar
```

Se o montante VAAR for **zero**, toda essa parcela zera.

---

### Etapa 9 — Totais finais

```
complemento_vaaf   = recursos_vaaf_final - recursos_vaaf
complemento_vaat   = recursos_vaat_final - recursos_vaat
complemento_uniao  = complemento_vaaf + complemento_vaat + complemento_vaar
recursos_fundeb    = recursos_vaaf + complemento_uniao
```

Essas colunas alimentam tabelas, gráficos e a validação.

---

## 11. O algoritmo de equalização explicado

Imagine **4 estados** simplificados, com valor aluno inicial (VAAF) e matrículas:

| Ordem | UF | VAAF inicial | Matrículas (mi) |
|-------|-----|--------------|-----------------|
| 1 | A | R$ 3.000 | 1,0 |
| 2 | B | R$ 3.500 | 2,0 |
| 3 | C | R$ 4.000 | 1,5 |
| 4 | D | R$ 5.000 | 0,5 |

A União tem **R$ 1 bi** para VAAF.

1. **Subir A e B até o nível de B (R$ 3.500):** necessidade calculada com matrículas acumuladas.  
2. Se couber no bolsa, **todos até B** são complementados; o valor aluno deles iguala.  
3. O que sobrar tenta puxar o próximo grupo em direção a C, e assim por diante.  
4. Estados que não entraram no grupo complementado **ficam como estavam**.

No código, isso aparece como:

- `complementacao_necessaria` acumulada  
- máscara `complementados` quando necessidade < montante  
- `recursos_pos` proporcional às matrículas dos complementados  

A VAAT repete a lógica no nível **município**, com milhares de entes.

---

## 12. Simulação municipal: o que muda quando você altera matrículas

### Por que recalcula o país inteiro

O VAAF depende do **total de matrículas ponderadas do estado**. Se Jordão (AC) ganha matrículas:

1. A participação de Jordão no fundo do AC muda.  
2. A soma estadual de matrículas muda → pode mudar o `vaaf_estado_inicial`.  
3. A equalização VAAF entre UFs **não** muda só por isso, mas a **divisão intra-AC** de `recursos_pos` sim.  
4. Em cascata, **todos os municípios do AC** podem ganhar ou perder complementação.

Por isso o backend executa `simula_fundeb` duas vezes (original e ajustada) e compara.

### Coeficiente de participação (conceito)

```
participação do município no estado ≈ matriculas_vaaf_mun / matriculas_vaaf_total_UF
```

**Teste CA-02** (automático): se o município tem 1.000 de 10.000 matrículas, participação = 10%; se passa a 1.100 de 10.100, ≈ 10,89%.

### Texto explicativo (`explicacao.js`)

Monta um relatório legível com:

- Matrículas brutas e ponderadas (VAAF/VAAT)  
- Recursos do fundo estadual  
- VAAF-MIN / VAAT-MIN nacionais  
- Valores antes e depois da complementação  
- DREC (2026) ou NF (2024)  

---

## 13. Gráficos, tabelas e validação automática

### 13.1 Gráficos 2D

Gerados no frontend com **Plotly** a partir do JSON de `/api/simular`:

- Barras por UF (VAAF, VAAT, diferenças)  
- Pizza ou barras empilhadas de complementação por destino  

### 13.2 Gráficos 3D

`charts3d.js` cria cenas com eixos VAAF, VAAT e complementação — útil para ver **clusters** de entes (ricos/pobres/complementados).

IDs dos containers incluem o ano (`…-2026`) para não colidir entre abas.

### 13.3 Validação RF-10 (`validacao.py`)

Após cada simulação, o backend executa:

| # | Checagem | O que detecta |
|---|----------|----------------|
| 1 | Soma `recursos_vaaf` por UF = total estadual na base | Erro de merge ou agregação |
| 2 | `vaaf_final ≈ recursos_vaaf_final / matriculas_vaaf` | Inconsistência de fórmula |
| 3 | Participações VAAF no estado somam 100% | Erro de rateio intra-UF |
| 4 | `recursos_fundeb = recursos_vaaf + complemento_uniao` | Erro nas colunas finais |

**Resposta na API:**

```json
"validacao": {
  "valido": true,
  "erros": [],
  "avisos": [],
  "checagens": ["UF SP: soma recursos = total estadual OK", "..."]
}
```

Se `valido` for `false`, os resultados ainda são exibidos, mas com alerta — útil para diagnóstico.

---

## 14. API REST e integração

Todas as rotas abaixo (exceto login) exigem cookie `fundeb_token`.

### Autenticação

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/login` | Body: `{cpf, senha}` → cookie |
| POST | `/api/auth/logout` | Remove cookie |
| GET | `/api/auth/me` | `{cpf, role, nome}` |

### Administração

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/admin/usuarios` | Lista usuários |
| POST | `/api/admin/usuarios` | Cria usuário |
| PATCH | `/api/admin/usuarios/{cpf}` | Atualiza nome, role, ativo, senha |
| DELETE | `/api/admin/usuarios/{cpf}` | Remove usuário |

### FUNDEB 2024 (`/api/...`)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/estados` | UFs e regiões |
| GET | `/api/municipios?uf=XX` | Municípios |
| GET | `/api/pesos` | Pesos por etapa (+ família) |
| GET | `/api/etapas` | Nomes amigáveis |
| GET | `/api/municipio/{ibge}/matriculas` | Matrículas do município |
| GET | `/api/cenario-atual/resumo` | Referência oficial |
| POST | `/api/simular` | Simulação agregada (resumo + gráficos) |
| POST | `/api/simular/completo` | Uma linha por ente |
| POST | `/api/simular/municipio` | Comparativo original/ajustado |

### Por exercício (`/api/2026/...`, `/api/2025/...`)

Mesma estrutura: `meta`, `estados`, `municipios`, `pesos`, `etapas`, `simular`, `simular/completo`, `simular/municipio`.

**Corpo típico de simulação:**

```json
{
  "complementacao_vaaf": 60249853912.98,
  "complementacao_vaat": 63262346608.62,
  "complementacao_vaar": 0,
  "max_nf": 1.0,
  "min_nf": 1.0,
  "pesos_vaaf": [1.0, 1.2, ...],
  "pesos_vaat": [1.0, 1.1, ...]
}
```

`pesos_vaaf` / `pesos_vaat` só têm efeito para **admin**.

---

## 15. Como executar e configurar

### Instalação

```powershell
cd simulador-fundeb-v2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Acesse: **http://localhost:8000**

### Variáveis de ambiente

| Variável | Função |
|----------|--------|
| `FUNDEB_SECRET_KEY` | Assinatura JWT (obrigatório em produção) |
| `FUNDEB_ADMIN_CPF` | CPF do primeiro admin (banco vazio) |
| `FUNDEB_ADMIN_SENHA` | Senha do primeiro admin |
| `FUNDEB_USERS_DB` | Caminho do SQLite (padrão: `data/usuarios.db`) |
| `FUNDEB_TOKEN_HOURS` | Validade do cookie em horas (padrão: 12) |
| `FUNDEB_RELOAD=1` | Ativa reload do Uvicorn (dev) |

### Testes automatizados

```powershell
python -m pytest tests/ -v
```

- `test_requisitos.py` — regras de negócio CA/RN/RF  
- `test_dataset_2026.py` — ETL e API 2026  
- `test_auth.py` — login, perfis, pesos customizados  

### Primeira carga 2026

Pode levar **30–60 segundos** enquanto o ETL lê as planilhas e grava `data/2026/dataset.pkl`. As próximas execuções são bem mais rápidas.

---

## 16. Glossário

| Termo | Significado |
|-------|-------------|
| **Ente** | Município ou estado (inclui UF como ente no fundo) |
| **IBGE** | Código do ente (ex.: 1200054 = Assis Brasil/AC) |
| **VAAF** | Valor Aluno Ano do Fundeb — foco na parcela FUNDEB |
| **VAAT** | Valor Aluno Ano Total — inclui outras receitas vinculadas |
| **VAAR** | Valor Aluno Ano Resultado — complementação por mérito |
| **NSE** | Ponderador de Nível Socioeconômico |
| **NF** | Ponderador ligado à disponibilidade de recursos (modelo 2024) |
| **DREC** | Disponibilidade de Recursos (substitui NF no VAAF em 2026) |
| **Matrícula ponderada** | Matrícula × pesos × (NSE, NF/DREC conforme modalidade) |
| **Equalização** | Algoritmo que distribui complementação do menor para o maior valor aluno |
| **Cenário atual** | Dados oficiais de referência para comparação |
| **Segmento / etapa** | Categoria de matrícula (ex.: creche integral urbana) |
| **Família** | Agrupamento visual de segmentos (remove sufixos Urbano/Rural/Campo…) |
| **RF-10** | Requisito de validação interna automática |
| **Inabilitados VAAT** | Entes que não recebem complementação VAAT |

---

## 17. Referências legais e de dados

- **Lei nº 14.113/2020** — Marco do FUNDEB  
- **Portaria MEC/MF nº 6/2026** — Montantes de complementação 2026  
- **Resolução MEC nº 04/2023** — Pesos por etapa (referência histórica)  
- [Portal FNDE — FUNDEB](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb)  
- [Matrículas da educação básica](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/matriculas-da-educacao-basica)  

---

## Créditos

Desenvolvido pelo **IFCE** — prof. João Cláudio Nunes Carvalho.  
Motor baseado no pacote R **simulador.fundeb**.

---

*Documento gerado para o Simulador FUNDEB v2 — descreve o estado atual do sistema (2024, 2025 consulta, 2026, autenticação e administração de usuários).*
