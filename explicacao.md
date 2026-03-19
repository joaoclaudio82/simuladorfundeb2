# Simulador FUNDEB v2 - Explicacao Completa

Este documento resume tudo que o sistema faz, como os calculos sao realizados e como os dados entram no processo. O objetivo e servir como base para apresentacao (PPT), reunindo a visao funcional e tecnica em linguagem clara.

## 1) O que e o sistema

O `simulador-fundeb-v2` e uma aplicacao web para simular distribuicao de recursos do FUNDEB em diferentes cenarios.  
Ele possui:

- **Backend** em Python com FastAPI (`main.py`).
- **Motor de calculo** dedicado (`simulador.py`).
- **Frontend** em HTML/CSS/JavaScript (`static/index.html` e `static/js/app.js`).
- **Validacao interna** das simulacoes (`validacao.py`).

O sistema permite simular cenarios para todo o pais e tambem simular alteracoes de matriculas em um municipio especifico para observar o impacto.

## 2) Principais capacidades (o que o sistema e capaz de fazer)

### 2.1 Simulacao principal (nacional)

Permite ajustar:

- Montante de complementacao **VAAF**
- Montante de complementacao **VAAT**
- Montante de complementacao **VAAR**
- Fator maximo de **NF** (disponibilidade de recursos vinculados)
- Pesos VAAF/VAAT por etapa (aba de ponderacoes)

E retorna:

- VAAT minimo simulado e comparacao com referencia
- VAAF minimo simulado e comparacao com referencia
- Complementacao para municipios e estados
- Percentual de entes que receberam complementacao
- Tabelas de ganhadores/perdedores
- Graficos por UF (VAAF, VAAT, diferencas, complementacao por tipo e destino)

### 2.2 Simulacao VAAR

Executa cenario com montante VAAR > 0 e mostra:

- Distribuicao VAAR por ente e por UF
- Participacao da VAAR no total da complementacao
- Tabelas e graficos 2D/3D para leitura analitica

### 2.3 Simulacao municipal

Permite selecionar UF e municipio, alterar matriculas por etapa e comparar:

- **Cenario original** x **cenario ajustado**
- VAAF, VAAT, complementos e recursos finais
- Impacto sobre outros entes do mesmo estado

Tambem mostra indicadores discriminados para validacao tecnica:

- Matriculas ponderadas VAAF/VAAT do ente
- Matriculas ponderadas do fundo estadual
- Receitas VAAF/VAAT do fundo
- VAAF-MIN e VAAT-MIN
- VAAF e VAAT antes da complementacao
- Coeficiente do ente no fundo estadual

### 2.4 API REST para integracao

Endpoints principais:

- `GET /api/estados`
- `GET /api/municipios?uf=XX`
- `GET /api/pesos`
- `GET /api/etapas`
- `GET /api/municipio/{ibge}/matriculas`
- `POST /api/simular`
- `POST /api/simular/completo`
- `POST /api/simular/municipio`

## 3) Fontes de dados e politica atual de uso

O sistema opera com uma politica hibrida para manter consistencia dos resultados e comparabilidade historica:

- **Fonte de verdade das 41 etapas de matriculas do motor:** `data/matriculas.rda`
- **Pesos VAAF/VAAT por etapa:** `data/pesos.rda`
- **Campos tecnicos por ente:** `data/complementar.rda`  
  (NF, inabilitados VAAT, fallback de peso VAAR)
- **Cenarios de referencia/comparacao:** `data/cenario_atual.rda`, `data/cenario_atual_agregada.rda`, `data/cenario_ufs_atual.rda`
- **Planilha unificada para checagens e campos extras:** `data/dados_unificados.xlsx`
- **NSE oficial por ente (IBGE):** `PonderadorNSE 2024.pdf`

### Regras importantes de dados

- Chave canonica de merge em planilha: `Codigo IBGE_x`.
- Divergencias entre `Codigo IBGE_x` e `Codigo IBGE_y` sao detectadas e sinalizadas.
- O `nse` e carregado do PDF oficial por IBGE.
- O `peso_vaar` e atualizado com base na coluna de Complementacao VAAR da planilha quando disponivel.

## 4) Como os calculos sao feitos (passo a passo)

O motor segue uma sequencia clara:

### Etapa 1 - Ponderacao de matriculas por etapa/modalidade

Para cada ente:

- `matriculas_vaaf = matriz_matriculas x vetor_peso_vaaf`
- `matriculas_vaat = matriz_matriculas x vetor_peso_vaat`

### Etapa 2 - Aplicacao dos ponderadores sociofiscais

- O **NSE** (oficial por ente) e aplicado em VAAF e VAAT.
- O **NF** e reescalonado por min-max no intervalo de simulacao e aplicado no VAAF.

Formulas:

- `matriculas_vaaf = matriculas_vaaf * nse * nf`
- `matriculas_vaat = matriculas_vaat * nse`

### Etapa 3 - Formacao dos fundos estaduais (VAAF)

Agrupa por UF:

- soma das matriculas ponderadas do estado
- soma dos recursos VAAF do estado
- calcula `vaaf_estado_inicial = recursos_estado_vaaf / matriculas_estado_vaaf`

### Etapa 4 - Equalizacao VAAF (entre UFs)

Algoritmo:

1. Ordena fundos pelo menor valor aluno (VAAF inicial).
2. Calcula necessidade acumulada de complementacao.
3. Define quais fundos recebem complementacao com base no montante disponivel.
4. Redistribui recursos proporcionalmente as matriculas dos complementados.
5. Fundos nao complementados mantem recursos originais.

### Etapa 5 - Redistribuicao intraestadual do VAAF

Com o total estadual pos-equalizacao definido, redistribui para os entes da UF proporcionalmente as matriculas ponderadas.

### Etapa 6 - Calculo do VAAT pre-complementacao

- `vaat_pre = recursos_vaat / matriculas_vaat`

### Etapa 7 - Equalizacao VAAT (entre entes)

Mesmo principio da equalizacao VAAF, agora em nivel de ente:

- ordena por `vaat_pre`
- aplica montante VAAT disponivel
- exclui entes inabilitados (`inabilitados_vaat = true`) do recebimento VAAT

### Etapa 8 - Complementacao VAAR

- `complemento_vaar = peso_vaar * montante_vaar`

### Etapa 9 - Colunas finais

- `complemento_vaaf = recursos_vaaf_final - recursos_vaaf`
- `complemento_vaat = recursos_vaat_final - recursos_vaat`
- `complemento_uniao = complemento_vaaf + complemento_vaat + complemento_vaar`
- `recursos_fundeb = recursos_vaaf + complemento_uniao`

## 5) O que significa cada indicador-chave

- **VAAF final**: valor aluno/ano FUNDEB apos equalizacao VAAF.
- **VAAT final**: valor aluno/ano total apos equalizacao VAAT.
- **VAAF-MIN / VAAT-MIN**: piso nacional observado no cenario simulado.
- **Complemento VAAF/VAAT/VAAR**: parcela de cada modalidade recebida pelo ente.
- **Coeficiente do ente no fundo**: participacao do ente nas matriculas ponderadas do estado.

## 6) Validacao interna da simulacao (qualidade dos resultados)

O modulo `validacao.py` executa checagens automaticas:

1. Soma dos recursos VAAF dos entes por UF bate com total estadual.
2. Consistencia de formula: `vaaf_final = recursos_vaaf_final / matriculas_vaaf`.
3. Participacoes no estado somam 100%.
4. `recursos_fundeb = recursos_vaaf + complemento_uniao`.

Saida da validacao:

- `valido` (true/false)
- `erros`
- `avisos`
- `checagens`

## 7) O que mudou recentemente (resumo para apresentacao)

- Integracao de **NSE oficial** por IBGE a partir do PDF.
- Manutencao de comparabilidade historica ao usar `matriculas.rda` como fonte das 41 etapas.
- Atualizacao do `peso_vaar` com base em dados oficiais da planilha quando disponivel.
- Enriquecimento da simulacao municipal com campos discriminados para auditoria tecnica.
- Documentacao atualizada e testes automatizados passando.

## 8) Sugestao de roteiro de PPT (estrutura pronta)

1. **Contexto e objetivo**
2. **Arquitetura do sistema (backend, motor, frontend, API)**
3. **Fontes de dados e governanca**
4. **Fluxo de calculo (VAAF, VAAT, VAAR)**
5. **Simulacao municipal e impacto federativo**
6. **Validacao interna e confiabilidade**
7. **Caso pratico (ex.: Jordao/AC)**
8. **Conclusoes e proximos passos**

## 9) Mensagem-chave para audiencia nao tecnica

O sistema permite testar cenarios de financiamento educacional com transparencia matematica, rastreabilidade de dados oficiais e validacao automatica, apoiando decisoes tecnicas e de politica publica com maior seguranca.
