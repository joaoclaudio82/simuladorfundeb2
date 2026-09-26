# Simulador FUNDEB v2
![CI](https://github.com/joaoclaudio82/simuladorfundeb2/actions/workflows/ci.yml/badge.svg)
Simulador de Fatores de Ponderação do FUNDEB — Versão Python com frontend e backend separados.

- **Cenários nacionais**: alteração conjunta de várias redes, recortes por rede estadual/DF, municipal ou UF e comparação A–D de matrículas e receitas.
- **Exportações**: PDF, Excel e CSV associados ao resultado calculado, com dados, hipóteses e identificação da base.
- **Bases versionadas**: catálogo com hashes, auditoria de cobertura, importação de versões preliminares e conferência com referência.
- **Trajetória de EPT**: expansão linear e receita composta, com hipóteses explícitas.

Abra **Cenários nacionais** no menu ou acesse `/?tab=cenarios`. Consulte o [guia de uso, importação e API](docs/CENARIOS_NACIONAIS.md) e o [status de implementação e validação](docs/STATUS_IMPLEMENTACAO.md).

**Dados atuais:** a base legada contém 5.595 redes e não tem exercício identificado. Ela não é apresentada como base homologada de 2026. Receitas de agosto, divergências de PE, composição do grupo Propag e regra amazônica dependem de confirmação e fornecimento dos insumos correspondentes. Os resultados são cenários hipotéticos, não previsões.

- **Simulação VAAR**:  aba para simular a distribuição da complementação VAAR
- **Simulação por ente federado**: Permite ajustar matrículas de uma rede e ver o impacto em VAAF, VAAT e VAAR
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

## Estrutura

```
simulador-fundeb-v2/
├── main.py            # API FastAPI (backend)
├── simulador.py       # Motor de simulação (lógica de cálculo)
├── validacao.py       # Validação interna (RF-10) e comparação com dados oficiais (CA-05)
├── requirements.txt   # Dependências Python
├── data/              # Dados .rda (pesos, matrículas, cenário atual)
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

## Testes

```bash
python -m pytest tests/test_requisitos.py -v
```

Para a suíte completa e o fluxo da interface com API real:

```bash
python -m pytest tests/ -q
npm ci
npm run test:ui
```

O teste de interface usa DOM em memória; Node.js é necessário somente para os testes. A aplicação continua sendo servida pelo Python. Cenários persistem em `.runtime/cenarios.sqlite3`; use `FUNDEB_CENARIOS_DB` para apontar a um volume persistente na implantação.

Inclui testes para:
- **CA-02**: Participação 1000/10000 = 10% e 1100/10100 ≈ 10,89%
- **RN-03**: Alteração em um município redistribui todos os entes do estado
- **RF-10**: Validação interna (soma recursos, VAAF, participações)

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/estados` | Lista estados e regiões |
| GET | `/api/municipios?uf=XX` | Lista municípios de uma UF |
| GET | `/api/pesos` | Retorna fatores de ponderação |
| GET | `/api/etapas` | Retorna nomes das etapas |
| GET | `/api/municipio/{ibge}/matriculas` | Matrículas de um município |
| POST | `/api/simular` | Executa simulação principal |
| POST | `/api/simular/completo` | Simulação com todos os dados |
| POST | `/api/simular/municipio` | Simulação municipal com ajuste de matrículas |

## Créditos

Desenvolvido pelo IFCE, prof. João Cláudio Nunes Carvalho.
