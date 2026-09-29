# Checklist — habilitar simulação FUNDEB 2025

Guia para completar os dados de 2025 no simulador. Hoje o exercício 2025 está em **modo consulta** (matrículas e pesos); a simulação fica bloqueada até os arquivos abaixo estarem em `20252026/`.

**Portal oficial:** [FNDE — FUNDEB 2025](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2025)

---

## 1. Situação atual no repositório

| Dado | Status | Arquivo / origem |
|------|--------|------------------|
| Matrículas por ente (325 segmentos) | ✅ | `Matrículas Fundeb 2025 e 2026.xlsx` → aba `Detalhadas`, `ANO=2025` |
| Fatores de ponderação (FPs) | ✅ | Mesma planilha → aba `FPs` |
| Receita total por ente | ❌ | Só existe versão **2026** |
| NSE | ❌ | Só existe versão **2026** |
| DREC | ❌ | Só existe versão **2026** |
| Memória de cálculo VAAT | ❌ | Só `MemriadeClculoVAAT2026 (2).xlsx` |
| Montantes federais (VAAF/VAAT/VAAR) | ❌ | `COMPLEMENTACAO_2025` não definida no código |
| Inabilitados VAAT / pesos VAAR | ❌ | Placeholders zerados no dataset 2025 |

---

## 2. O que baixar no portal FNDE

Escolha **uma portaria de referência** (recomendado: **última publicação do exercício** — 5ª Portaria MEC/MF nº 13/2025 ou 6ª Portaria nº 5/2026 com ajuste anual de 2025). Use a mesma portaria para todos os anexos.

### 2.1 Obrigatórios para o motor de simulação

| # | Publicação FNDE | Salvar como (`20252026/`) | Uso no simulador |
|---|-----------------|---------------------------|------------------|
| 1 | **Receita total do Fundeb por ente federado** (XLSX) | `1-receita-total-do-fundeb-por-ente-federado-2025.xlsx` | `recursos_vaaf`, complementações oficiais, `peso_vaar` |
| 2 | **Ponderador de nível socioeconômico** (dados brutos) | `ponderador-de-nivel-socioeconomico-2025.xlsx` | Coluna `nse` no VAAF e VAAT |
| 3 | **Ponderador de disponibilidade de recursos** (dados brutos) | `ponderador-de-disponibilidade-de-recursos-2025.xlsx` | Coluna `drec` no VAAF |
| 4 | **Metodologia de correção monetária… VAAT** ou planilha equivalente | `MemoriaCalculoVAAT2025.xlsx` | `recursos_vaat`, `matriculas_vaat_ref`, `inabilitados_vaat` |

### 2.2 Complementares (validação e VAAR)

| # | Publicação FNDE | Uso |
|---|-----------------|-----|
| 5 | **Redes beneficiadas… complementação-VAAR prevista** | Conferir `peso_vaar` e beneficiários |
| 6 | **VAAT, VAAT-MIN e complementação-VAAT por ente** | Conferir cenário oficial pós-equalização |
| 7 | **Lista dos entes habilitados/inabilitados ao VAAT 2025 (posição final)** | Flag `inabilitados_vaat` |
| 8 | **Lista dos entes inabilitados à complementação VAAR 2025** | Auditoria VAAR |

### 2.3 Já no repositório (não baixar de novo)

- `Matrículas Fundeb 2025 e 2026.xlsx` — matrículas e FPs de 2025 e 2026.

---

## 3. Arquivos em `20252026/` (integrados no ETL)

```
20252026/
├── Matrículas Fundeb 2025 e 2026.xlsx
├── 1-receita-total-do-fundeb-por-ente-federado-2025.xlsx   # Portaria 5/2026 (ajuste 2025)
├── PonderadorNSEFundeb2025.pdf
├── PonderadorDRecFundeb2025.pdf
└── Receita STN 2023 VAAT 2025 para publicação.xlsx
```

NSE e DREC são lidos dos **PDFs** (o FNDE não publica XLSX para 2025). VAAT usa a planilha **STN** (aba `COM CORREÇÃO`).

Os arquivos **sem sufixo `-2025`** continuam sendo usados pelo exercício **2026**.

---

## 4. Montantes de complementação federal (Portaria)

Atualizar em `dados/fundeb_dataset.py` → `COMPLEMENTACAO_2025` com os totais da portaria escolhida (soma nacional VAAF, VAAT e VAAR).

**Referência inicial (Cartilha FUNDEB 2025, estimativa dez/2024):**

| Modalidade | Valor (R$) |
|------------|------------|
| VAAF | 26,9 bilhões |
| VAAT | 24,2 bilhões |
| VAAR | 5,4 bilhões |

**Importante:** esses valores foram revisados nas portarias quadrimestrais (abr/ago/nov/dez 2025). Para simulação fiel ao cenário oficial, use os totais da **mesma portaria** da planilha de receita (ex.: soma da coluna “Complementação VAAF” no XLSX).

---

## 5. Passos no código (após colocar os arquivos)

1. **Invalidar cache** — apagar `data/2025/dataset.pkl` e parquets em `data/2025/`.
2. **Subir o servidor** — `python main.py`; o ETL detecta arquivos `-2025` e habilita `simulacao_habilitada=True`.
3. **Conferir meta da API** — `GET /api/2025/meta` deve retornar `simulacao_habilitada: true`.
4. **Rodar testes** — `python -m pytest tests/test_dataset_2026.py tests/test_dataset_2025.py -v`.
5. **Atualizar UI** — remover banner de bloqueio em `static/js/app_multi_ano.js` se a meta indicar simulação habilitada (ou deixar o front ler `meta.simulacao_habilitada` dinamicamente).

### Funções ETL envolvidas (`dados/fundeb_dataset.py`)

| Função | Papel |
|--------|-------|
| `_arquivos_ano(ano)` | Mapeia paths por exercício |
| `_dados_2025_completos()` | Verifica se os 4 arquivos obrigatórios existem |
| `_montar_complementar(ano, mat, pesos)` | Monta `complementar` (NSE, DREC, receita, VAAT) |
| `construir_dataset_2025()` | Consulta ou simulação conforme disponibilidade |
| `_gerar_cenario_referencia(..., complementacao=...)` | Cenário oficial para comparação |

---

## 6. Validação pós-carga

- [ ] ~5.595 entes com matrículas 2025 (IBGE único)
- [ ] 319 etapas alinhadas entre `matriculas` e `pesos`
- [ ] `complementar.recursos_vaaf.sum()` > 0
- [ ] `complementar.nse` e `drec` com variação (não todos 1,0)
- [ ] `peso_vaar` positivo para redes beneficiadas
- [ ] `POST /api/2025/simular` retorna 200 (não 503)
- [ ] `validacao.valido == true` na resposta da simulação
- [ ] Comparar totais com planilha oficial (`comparar_com_oficial` em `validacao.py`)

---

## 7. Portarias publicadas em 2025 (referência)

| # | Portaria | Data | Observação |
|---|----------|------|------------|
| 1ª | MEC/MF nº 14/2024 | 27/12/2024 | Estimativa inicial exercício 2025 |
| 2ª | MEC/MF nº 4/2025 | 30/04/2025 | 1ª revisão quadrimestral |
| 3ª | MEC/MF nº 5/2025 | 28/08/2025 | 2ª revisão |
| 4ª | MEC/MF nº 11/2025 | 27/11/2025 | 3ª revisão |
| 5ª | MEC/MF nº 13/2025 | 29/12/2025 | 4ª revisão |
| 6ª | MEC/MF nº 5/2026 | 29/04/2026 | Ajuste anual das receitas efetivas de 2025 |

---

## 8. Links úteis

- [Portal FUNDEB 2025 (FNDE)](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2025)
- [Matrículas da educação básica](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/matriculas-da-educacao-basica)
- [Resolução CIFUNDEB — fatores de ponderação](https://www.gov.br/mec/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-intergovernamental-fundeb)
- [Cartilha FUNDEB 2025 (PDF)](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/manuais-a-cartilhas-1/Cartilha_v_final_01_08_2025.pdf)
