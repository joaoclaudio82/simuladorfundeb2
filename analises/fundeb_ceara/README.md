# Estudo contrafactual FUNDEB — municípios do Ceará

Análise computacional sobre **incentivos financeiros implícitos** nos fatores de ponderação do FUNDEB. Não é recomendação para reclassificar alunos.

## Pergunta

Mantendo constante o número total de alunos de um município, quais mudanças factíveis na composição das matrículas entre etapas/modalidades produzem o maior aumento nos recursos do FUNDEB simulados para esse município?

## Como reproduzir

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m analises.fundeb_ceara.run
```

Grade reduzida (5/10/20/30/50/100%):

```bash
python -m analises.fundeb_ceara.run --rapido
```

Um exercício apenas:

```bash
python -m analises.fundeb_ceara.run --anos 2024
```

Testes do estudo:

```bash
python -m pytest tests/test_fundeb_ceara.py -v
```

## Estrutura

```
analises/fundeb_ceara/
├── README.md
├── metodologia.md
├── RESULTADOS.md          # gerado após a execução
├── run.py
├── scripts/
├── resultados/            # CSVs
└── figuras/
```

## Anos

| Snapshot | Fonte | Etapas | Ponderador |
| ---: | --- | ---: | --- |
| 2024 | `data/*.rda` + NSE 2024 | 41 | NF (reescalonado para 1 no motor com max=min=1) |
| 2025 | `20252026/` | ~319 | DREC |
| 2026 | `20252026/` | ~319 | DREC |

O ano dos `.rda` **não está no nome do arquivo**. A atribuição a 2024 vem do carregador, do PDF de NSE e da documentação do repositório.

## Interpretação

Três camadas, sem misturá-las:

1. **Ótimo matemático** — limite teórico (concentrar matrículas na etapa de maior peso).
2. **Ótimo educacionalmente factível** — só parcial→integral na educação infantil pública e fundamental urbano→integral.
3. **Política plausível de expansão** — a mesma família de transições, lida como expansão de jornada, não como reclassificação.

O motor completo (`simula_fundeb`) é reexecutado em cada cenário. Não se estima impacto multiplicando alunos pelo peso.
