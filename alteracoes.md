# Resumo de Alteracoes - simulador-fundeb-v2

## O que foi diagnosticado

- O projeto estava originalmente carregando dados principais via `.rda`.
- Foi solicitada migracao para usar `dados_unificados.xlsx` e NSE do PDF.
- Ao migrar matriculas para a planilha, os valores de varios campos (ex.: Jordao/AC) mudaram por diferenca de agregacao.
- Havia inconsistencias de execucao no ambiente (`pypdf` e `openpyxl` faltando no `.venv`).
- A simulacao municipal mostrou `VAAR=0` para entes com VAAR na planilha porque `peso_vaar` vinha do `complementar.rda` (e no Jordao era 0).

## Alteracoes realizadas

### 1) Pipeline hibrido de dados no backend
Arquivo: `simulador-fundeb-v2/main.py`

- Adicionado carregamento e normalizacao de fontes:
  - `dados_unificados.xlsx`
  - `pesos.rda`
  - `complementar.rda`
  - `cenario_atual*.rda`
  - `PonderadorNSE 2024.pdf`
- Adicionadas funcoes utilitarias para:
  - normalizacao de texto/colunas,
  - leitura e parsing do NSE no PDF,
  - validacoes de chave IBGE e cobertura de dados.

### 2) Regra de chave IBGE

- Foi definida regra canonica usando `Codigo IBGE_x` para merges da planilha.
- Sistema detecta divergencia `IBGE_x` vs `IBGE_y` e emite aviso.

### 3) NSE oficial por ente

- O `nse` passou a ser extraido do `PonderadorNSE 2024.pdf` por `ibge`.
- Em caso de ausencia no PDF, mantem fallback do `complementar.rda` (com aviso).

### 4) Correcao do VAAR municipal

- `peso_vaar` passou a ser derivado da coluna `Complementacao VAAR` da planilha (`dados_unificados.xlsx`) quando disponivel.
- Isso corrigiu o caso de municipios que apareciam com `VAAR=0` por causa do peso no `.rda`.

### 5) Decisao final sobre matriculas

- Apos detectar divergencia nos numeros com a planilha, foi ajustado para:
  - usar `matriculas.rda` como fonte de verdade das 41 etapas do motor,
  - usar `dados_unificados.xlsx` apenas para receitas/campos extras/checagens.
- Isso restaurou os valores de Jordao/AC para o padrao anterior nas matriculas e no VAAT.

## Ajustes de dependencias e execucao

Arquivo: `simulador-fundeb-v2/requirements.txt`

- adicionados:
  - `pypdf`
  - `openpyxl`

No ambiente:
- instalados `pypdf` e `openpyxl` no `.venv` para evitar falha ao ler PDF/XLSX.
- servidor FastAPI operacional em `http://localhost:8000`.

## Ajustes de documentacao

Arquivos:
- `simulador-fundeb-v2/README.md`
- `simulador-fundeb-v2/documentacao.md`

Atualizados para refletir:
- politica de fontes hibridas,
- NSE oficial via PDF,
- papel do `.rda` como fallback tecnico/consistencia.

## Validacoes executadas

- Testes automatizados: `python -m pytest tests/test_requisitos.py -q` -> `7 passed`.
- Cobertura de campos criticos validada (sem faltas em `nse`, `nf`, `inabilitados_vaat`, `peso_vaar`).
- Teste especifico Jordao/AC:
  - matriculas voltaram ao padrao anterior (`matriculas.rda`);
  - `complemento_vaat` voltou para `7.758.076` no cenario original;
  - `complemento_vaar` passou a refletir peso da planilha (quando montante VAAR > 0).
