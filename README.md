# Simulador FUNDEB v2

Simulador de Fatores de Ponderação do FUNDEB — Versão Python com frontend e backend separados.

## Novidades em relação à versão original (R/Shiny)

- **Simulação VAAR**: Nova aba para simular a distribuição da complementação VAAR
- **Simulação Municipal**: Permite ajustar matrículas de um município e ver o impacto em VAAF, VAAT e VAAR
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
Motor de simulação baseado no pacote R [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2).
