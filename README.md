# Simulador FUNDEB v2

Simulador de Fatores de Ponderação do FUNDEB — Versão Python com frontend e backend separados.

## Novidades em relação à versão original (R/Shiny)

- **Simulação VAAR**: Nova aba para simular a distribuição da complementação VAAR
- **Simulação Municipal**: Permite ajustar matrículas de um município e ver o impacto em VAAF, VAAT e VAAR
- **Exercícios 2025 e 2026**: Abas dedicadas com dados da pasta `20252026/` (2026 operacional; 2025 consulta de matrículas até receitas oficiais)
- **DREC (2025+)**: Ponderador de Disponibilidade de Recursos aplicado no VAAF (substitui NF reescalado)
- **325 segmentos de matrícula**: Detalhamento urbano/campo/indígena/quilombola/especial/bilíngue
- **Interface moderna**: Dashboard com sidebar, Bootstrap 5 e Plotly.js
- **API REST**: Backend FastAPI com endpoints para integração

## Requisitos

- Python 3.10+
- Pacotes listados em `requirements.txt`

## Instalação

```bash
cd simulador-fundeb-v2
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

O aplicativo estará disponível em: **http://localhost:8000**

Na primeira execução, se não houver usuários no banco, é criado um administrador inicial (veja [Autenticação](#autenticação)).

## Autenticação

Login por **CPF** e **senha**. Usuários são cadastrados somente por administradores (`/admin.html`).

### Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `FUNDEB_SECRET_KEY` | Segredo para JWT (obrigatório em produção) |
| `FUNDEB_ADMIN_CPF` | CPF do admin inicial (somente se o banco estiver vazio) |
| `FUNDEB_ADMIN_SENHA` | Senha do admin inicial (padrão dev: `admin123`) |
| `FUNDEB_USERS_DB` | Caminho do SQLite (padrão: `data/usuarios.db`) |
| `FUNDEB_TOKEN_HOURS` | Expiração do cookie em horas (padrão: 12) |

### Permissões

| Recurso | Admin | Usuário |
|---------|-------|---------|
| Simulador e consultas | Sim | Sim |
| Ponderações — visualizar | Sim | Sim (somente leitura) |
| Ponderações — editar | Sim | Não |
| Simular com pesos customizados | Sim | Não (API usa pesos oficiais) |
| Cadastro de usuários | Sim | Não |

### Primeiro acesso (desenvolvimento)

1. Suba o servidor: `python main.py`
2. Acesse `http://localhost:8000/login.html`
3. CPF padrão: `529.982.247-25` / senha: `admin123` (se o banco foi criado vazio)
4. Altere a senha em **Usuários** após o primeiro login

## Estrutura

```
simulador-fundeb-v2/
├── main.py            # API FastAPI (backend)
├── auth/              # Autenticação (SQLite, JWT, perfis admin/usuario)
├── simulador.py       # Motor de simulação (lógica de cálculo)
├── validacao.py       # Validação interna (RF-10) e comparação com dados oficiais (CA-05)
├── requirements.txt   # Dependências Python
├── data/              # Dados híbridos (xlsx + rda)
│   ├── dados_unificados.xlsx   # Base principal de matrículas/receitas
│   ├── pesos.rda               # Pesos por etapa (VAAF/VAAT)
│   ├── complementar.rda        # NF, inabilitados VAAT, peso VAAR (fallback técnico)
│   ├── matriculas.rda          # Fallback para etapas ausentes no xlsx
│   ├── cenario_atual*.rda      # Cenários de comparação
│   └── PonderadorNSE 2024.pdf  # NSE oficial por ente (extraído por IBGE)
├── tests/
│   └── test_requisitos.py  # Testes unitários RF, RN e CA
├── static/
│   ├── index.html     # Frontend HTML
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js     # Lógica do frontend
└── README.md
```

## Validação (RF-10, CA-05)

Cada simulação retorna um objeto `validacao` com:

- **valido**: `true` se todas as checagens passaram
- **erros**: inconsistências que indicam falha
- **avisos**: alertas não críticos
- **checagens**: lista das verificações realizadas (soma recursos = total estadual, VAAF = recursos/matrículas, participações = 100%, etc.)

Para comparar com dados oficiais do FUNDEB (CA-05), use a função `comparar_com_oficial()` em `validacao.py` passando um DataFrame com os dados publicados.

## Política de fontes de dados

- **Base principal**: `data/dados_unificados.xlsx`.
- **NSE oficial**: `PonderadorNSE 2024.pdf` (carregado por IBGE).
- **Complementos técnicos**: `complementar.rda` para `nf`, `inabilitados_vaat` e `peso_vaar`.
- **Pesos por etapa**: `pesos.rda`.
- **Fallback de etapas não presentes no xlsx**: `matriculas.rda`.

## Testes

```bash
python -m pytest tests/ -v
```

Inclui testes para:
- **CA-02**: Participação 1000/10000 = 10% e 1100/10100 ≈ 10,89%
- **RN-03**: Alteração em um município redistribui todos os entes do estado
- **RF-10**: Validação interna (soma recursos, VAAF, participações)
- **Auth**: login, perfis, restrição de pesos customizados para usuário comum

## API Endpoints

Rotas `/api/*` (exceto login) exigem cookie de sessão (`fundeb_token`).

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/login` | Login (público) |
| POST | `/api/auth/logout` | Encerra sessão |
| GET | `/api/auth/me` | Usuário autenticado |
| GET/POST/PATCH/DELETE | `/api/admin/usuarios` | CRUD de usuários (admin) |
| GET | `/api/estados` | Lista estados e regiões (2024) |
| GET | `/api/municipios?uf=XX` | Lista municípios de uma UF |
| GET | `/api/pesos` | Retorna fatores de ponderação |
| GET | `/api/etapas` | Retorna nomes das etapas |
| GET | `/api/municipio/{ibge}/matriculas` | Matrículas de um município |
| POST | `/api/simular` | Executa simulação principal |
| POST | `/api/simular/completo` | Simulação com todos os dados |
| POST | `/api/simular/municipio` | Simulação municipal com ajuste de matrículas |

Rotas equivalentes por exercício: `/api/2026/...` e `/api/2025/...` (2025: leitura; POST simular retorna 503).

## Créditos

Desenvolvido pelo IFCE, prof. João Cláudio Nunes Carvalho.
Motor de simulação baseado no pacote R [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2).
