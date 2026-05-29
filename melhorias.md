# Melhorias — Simulador FUNDEB v2

Registro das implementações e correções realizadas (FUNDEB 2024, 2025 e 2026).

---

## Infraestrutura e dados (backend)

### ETL e datasets multi-exercício (`dados/fundeb_dataset.py`)
- Carregamento de **2024** (legado `.rda` + PDF NSE), **2025** e **2026** (planilhas em `20252026/`).
- **2026:** matrículas detalhadas, NSE, DREC, receita total, memória VAAT; motor com ponderador **DREC** no VAAF.
- **2025:** consulta de matrículas habilitada; simulação bloqueada até receitas oficiais.
- Cache por exercício em `data/{ano}/dataset.pkl` (versão `DATASET_CACHE_VERSION = 2`).
- Montantes oficiais 2026 (Portaria MEC/MF nº 6/2026) em `COMPLEMENTACAO_2026`.
- **319 segmentos** únicos no motor 2026 (deduplicação de 6 linhas repetidas na aba FPs do Excel).
- Função `familia_segmento()` para agrupamento na UI.

### Motor (`simulador.py`)
- Modo `modo_ponderador`: `nf` (2024) vs `drec` (2025+).
- VAAF com NSE × DREC em 2026.
- `pondera_matriculas_etapa()` robusto: evita explosão de colunas duplicadas no `matmul`.

### API (`api_simulacao.py`, `main.py`)
- Rotas `/api/2025/*` e `/api/2026/*` (meta, pesos, etapas, estados, municípios, simular, simular/completo, simular/municipio).
- Simulação 2025 retorna **503** quando desabilitada.
- `/api/pesos` (2024) inclui campo `familia` para agrupamento.
- `reload` desligado por padrão no Uvicorn (`FUNDEB_RELOAD=1` para ativar).

### Testes
- `tests/test_dataset_2026.py`: alinhamento etapas/matriculas/pesos, RF-10, validação interna, fluxo API simular, 2025 bloqueado.

### Documentação
- `README.md` e `explicacao.md` atualizados para multi-ano e 2026.

---

## Frontend — navegação e estabilidade

### Menu lateral (`static/js/app.js`)
- `activateTab()` centralizado; delegação só em `li[data-tab]`.
- Rótulos `sidebar-section-label` com `pointer-events: none` (não interceptam cliques).
- Exposição de `window.activateFundebTab` para abas injetadas.
- Proteções em `initNavigation()` (toggle sidebar, resize).
- Tratamento de erro em `initData()`; listeners opcionais nos botões.

### Conflito JavaScript corrigido
- Removida redefinição de `$` em `app_multi_ano.js` que quebrava todo o `app.js`.

---

## FUNDEB 2026 — abas novas (`static/js/app_multi_ano.js`, `static/index.html`)

### Abas injetadas no menu
- Simulação 2026, Ponderações 2026, VAAR 2026, Município 2026.
- Consulta 2025 / Ponderações 2025 (somente leitura, banner de bloqueio).

### Simulação 2026
- Parâmetros VAAF, VAAT, VAAR com defaults de `/api/2026/meta`.
- Resultados: resumo, validação RF-10, gráficos VAAF/VAAT por UF.
- Envio de **pesos editados** da aba Ponderações.

### Ponderações 2026
- Accordion por **família de segmento** (como no plano FPs).
- **Campos editáveis** VAAF e VAAT por segmento (319 etapas no exercício).
- Pesos usados na simulação principal, VAAR e municipal.

### VAAR 2026
- UI completa espelhando 2024: parâmetros, info-boxes, gráficos por UF, tabela top 50, proporção VAAR, **3D**.
- `POST /api/2026/simular/completo` com dados e montantes **2026** (não 2024).
- Gráficos 3D com IDs por ano (`charts3d.js`).

### Município 2026
- UI completa: parâmetros VAAF/VAAT/VAAR na aba, loading, explicação, cenários original/ajustado, gráficos, tabela impacto no estado, **3D**.
- Matrículas por **segmento** (accordion por família), não mais soma errada no 1º segmento.
- Toggle **“Mostrar segmentos sem matrícula”** para ver/editar as 319 etapas (com destaque visual para zeradas).
- Contador: “X segmentos com matrícula neste município (de 319…)”.
- Seletor de **Estado por região** (`<optgroup>`: Norte, Nordeste, etc.), igual 2024.
- `renderExplicacao` / `renderResultadosMunicipio` generalizados para suportar ano 2026 (DREC na explicação).

---

## FUNDEB 2024 — melhorias de UI

### Ponderações
- Substituídos sliders em duas colunas por **accordion por família** com inputs numéricos VAAF/VAAT por etapa (41 etapas).
- Mesmo padrão visual das Ponderações 2026.

### Análise Regional
- **Pré-carga automática** da simulação com parâmetros padrão ao iniciar o app.
- Ao selecionar UF, carrega dados se necessário (sem exigir simular antes na aba principal).
- Atualização automática após simular na aba principal.
- Texto inicial ajustado.

---

## Correções de bugs

| Problema | Solução |
|----------|---------|
| Menu lateral não trocava abas | `activateTab()` + delegação correta; CSS `pointer-events` nos rótulos |
| `app.js` quebrava após load multi-ano | Remoção de `$` duplicado em `app_multi_ano.js` |
| Simulação 2026: erro matmul 325 vs 337 | `drop_duplicates` na aba FPs; etapas únicas na API; matriz coluna a coluna no motor |
| Município 2026: original ≠ ajustado sem editar | Edição por segmento real (não soma da família no 1º slug) |
| VAAR 2026 vazio | Implementação completa da aba + `/simular/completo` |
| Município 2026 sem explicação/gráficos | Paridade com `renderResultadosMunicipio` 2024 |
| Análise Regional 2024 sumia ao escolher UF | `garantirDadosRegional()` + pré-carga no startup |
| Loop reload Uvicorn no Windows | `reload=False` por padrão em `main.py` |
| Cache pickle sem pyarrow | Migração para `dataset.pkl` |

---

## CSS (`static/css/styles.css`)

- Estilos accordion ponderações multi-ano (`.pesos-accordion-body`, `.peso-segmento-row`, etc.).
- Área scroll matrículas municipal (`.matriculas-mun-scroll`).
- Destaque segmentos sem matrícula (`.matricula-item-zero`).

---

## Arquivos principais alterados

- `dados/fundeb_dataset.py`
- `simulador.py`
- `api_simulacao.py`
- `main.py`
- `static/js/app.js`
- `static/js/app_multi_ano.js`
- `static/js/explicacao.js`
- `static/js/charts3d.js`
- `static/index.html`
- `static/css/styles.css`
- `tests/test_dataset_2026.py`
- `README.md`, `explicacao.md`

---

## Pendências / não implementado (referência)

- Aba **Análise Regional 2026** (só 2024 hoje).
- Parser completo anexo VAAF `.ods` (receitas VAAF hoje via memória VAAT / receita total).
- Paridade total 2026 com todos os gráficos 3D da simulação principal 2024.
- Reaplicar correção RF-10 pós-arredondamento em 2024 (revertida a pedido anterior).
- Atualizar menções a **325** vs **319** segmentos em `README.md` / `explicacao.md` (fonte FPs tem 325 linhas; motor usa 319 únicos).

---

## Autenticação e perfis (`auth/`)

### Backend
- SQLite em `data/usuarios.db` com perfis **admin** e **usuario**.
- Login por CPF + senha; sessão em cookie httpOnly `fundeb_token` (JWT HS256).
- Bootstrap do primeiro admin via `FUNDEB_ADMIN_CPF` / `FUNDEB_ADMIN_SENHA` quando o banco está vazio.
- Rotas: `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`, CRUD `/api/admin/usuarios`.
- Todas as rotas `/api/*` de simulação e consulta exigem autenticação.
- Usuário comum: `preparar_pesos()` ignora `pesos_vaaf` / `pesos_vaat` customizados (pesos oficiais).

### Frontend
- `login.html` + `auth.js` (`guardAuth`, `apiFetch` com `credentials: 'include'`).
- Ponderações 2024/2026 somente leitura para perfil usuario (banner informativo).
- Menu **Usuários** e página `admin.html` (cadastro, ativar/desativar, reset senha) — só admin.
- Logout na sidebar.

### Testes
- `tests/test_auth.py`: login, CPF inválido, 403 admin, usuário inativo, pesos customizados por perfil.

---

## Como rodar

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

→ http://localhost:8000 — primeira carga 2026 pode levar ~30–60 s (gera `data/2026/dataset.pkl`).
