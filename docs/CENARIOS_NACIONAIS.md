# Cenários nacionais do Fundeb

## Executar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Abra `http://localhost:8000/?tab=cenarios` ou selecione **Cenários nacionais** no menu. As abas anteriores continuam disponíveis. As rotas antigas mantêm seus contratos e usam os arquivos legados; novas bases e cenários são selecionados na aba nacional.

1. Selecione a base e confira exercício, situação e pendências.
2. Escolha UF, tipo de rede, ente e categoria. Adicione cada ajuste ao conjunto. Trocar de UF não remove os ajustes adicionados.
3. Defina o recorte de apresentação. O motor continua calculando o universo nacional.
4. Informe a hipótese de receita, rubricas e tratamento das complementações; taxa zero mantém os valores.
5. Calcule A–D, selecione comparação e indicador e exporte.

Cada execução recebe um ID e guarda entradas, dados completos, hashes da base, versão do motor e validações. Modificar um controle marca o resultado como anterior; os downloads continuam usando o ID calculado. O link **Abrir este resultado** recupera o mesmo snapshot, inclusive após reiniciar o processo.

## O que cada cenário representa

| Cenário | Matrículas | Receita |
|---|---|---|
| A | Base | Base |
| B | Conjunto de ajustes | Base |
| C | Base | Hipótese de crescimento |
| D | Conjunto de ajustes | Hipótese de crescimento |

As comparações disponíveis são B−A, C−A, D−A e D−C. Não se pressupõe aditividade dos efeitos de receita e matrículas. Participações das redes estaduais usam como denominador o total nacional das redes estaduais e DF, mesmo quando a tabela mostra apenas UFs filtradas. Os recortes “todas” e “selecionadas” usam todas as redes do Brasil como denominador. A diferença de participação está em pontos percentuais.

VAAF e VAAT por aluno são calculados pela razão entre numeradores e denominadores compatíveis, inclusive nos totais. Complementações são valores financeiros distintos dos valores por aluno. Redes inabilitadas para VAAT continuam nos demais totais.

## Limitações da base disponibilizada

O catálogo inicial usa os arquivos existentes no repositório. São **5.595 redes: 5.568 municipais, 26 estaduais e a rede do DF**, com **41 categorias**. Não há metadados que confirmem o exercício, o ano do censo ou a atualização de agosto. Por isso, a base está identificada como `legado`, situação `pendente`, com exercício nulo. A API rejeita requisição que tente apresentá-la como exercício 2026.

Há **804 células fracionárias** em AEE e educação especial conveniada. Elas são preservadas e declaradas no manifesto; sua interpretação precisa ser confirmada na fonte. A soma das categorias não corresponde necessariamente ao número de alunos únicos, pois podem existir sobreposições.

A referência `cenario_atual.rda` não é presumida oficial. A auditoria compara IDs, cobertura e cinco indicadores, informa desvios por UF (incluindo PE) e não marca a base como homologada automaticamente. A igualdade A = B quando não há ajuste é verificada contra a mesma base recalculada; ela não significa igualdade com a referência externa.

No modelo legado, `recursos_vaat` é um snapshot independente da redistribuição VAAF. Essa limitação aparece na tela e nas exportações. O modo `componentes`, para futuras bases especificadas, exige a coluna explícita `outras_receitas_vaat` e calcula:

```text
recursos_vaat = recursos_vaaf_final + outras_receitas_vaat
```

O sistema não infere esse residual subtraindo valores de uma base cuja composição é desconhecida. A aplicação do modo por componentes depende da validação metodológica da equipe.

## Receita e PIB nominal

A taxa pode ser informada ou calculada pela taxa anual composta (CAGR) entre o primeiro e o último ano de uma série de PIB nominal fornecida pelo usuário. Informe valores na mesma unidade, em linhas `ano;valor`, sem separador de milhar e com ponto decimal; a fonte é obrigatória. O intervalo e os valores usados ficam registrados. Não há busca automática de PIB nem elasticidade de arrecadação presumida.

Somente as rubricas selecionadas são multiplicadas por `1 + taxa/100`. A complementação federal pode permanecer fixa ou receber a mesma taxa, conforme hipótese explícita. No modo por componentes, o crescimento aplica-se ao fundo VAAF e/ou às outras receitas VAAT, e não ao VAAT já recomposto. Valores nominais não devem ser interpretados como ganhos reais sem deflacionamento.

## Trajetória de EPT

A interface oferece trajetória linear entre dois anos, com horizonte de até 15 anos. O aumento total é relativo às matrículas EPT da base, e cada incremento anual é arredondado à unidade (metade para cima). A receita cresce de forma composta. Uma rede com zero matrícula EPT não ganha vagas por crescimento percentual; nesse caso, use um cenário de acréscimo absoluto.

O usuário define novas matrículas ou conversão de uma categoria de origem. A conversão preserva o total e não pode exceder a origem. As regras, pesos e habilitações permanecem constantes. O ano inicial é uma hipótese temporal quando a base não tem exercício identificado. O valor inicial de 50% no formulário não atesta a definição normativa da meta citada na reunião.

## Exportações

- **PDF:** indicador e comparação selecionados, todas as redes do recorte, unidades, hipótese de receita, identificação do cenário e pendências. Nas trajetórias, inclui todos os anos.
- **CSV:** UTF-8 com BOM, separador `;`, ponto decimal, todas as redes da comparação selecionada, todos os indicadores, percentuais e metadados. Ajustes completos não são repetidos por linha; há quantidade/hash dos ajustes e vínculo ao snapshot.
- **Excel:** Resumo, Comparativo selecionado, outras três comparações, Dados A/B/C/D, Ajustes e Metadados. Trajetórias têm abas por comparação e resumo temporal; o resultado completo de cada ano pode ser reproduzido a partir das hipóteses registradas.

As exportações não usam os limites de prévia da interface. Campos de texto que possam ser interpretados como fórmula são gravados como texto. Valores com denominador zero aparecem como N/A no PDF e como ausência em dados tabulares, sem substituir a ausência por zero.

## Catálogo e importação de novas bases

O catálogo padrão é `data/catalogo.json`. Cada versão tem ID único, arquivos, hashes, fonte, situação, exercício, período da receita, categorias EPT e parâmetros. As tabelas podem ser `.rda` com um único objeto ou CSV UTF-8 separado por vírgulas. O cadastro `entes` deve identificar explicitamente `estadual`, `municipal` ou `distrital`; não se classificam novas redes por um limiar arbitrário no código IBGE.

Colunas requeridas:

| Tabela | Colunas |
|---|---|
| `entes` | `ibge`, `uf`, `nome`, `tipo` |
| `matriculas` | `ibge` e uma coluna para cada categoria do arquivo de pesos |
| `pesos` | `etapa`, `nome`, `peso_vaaf`, `peso_vaat` |
| `complementar` | `ibge`, `recursos_vaaf`, `recursos_vaat`, `nse`, `nf`, `peso_vaar`, `inabilitados_vaat`; `outras_receitas_vaat` no modo por componentes |
| `referencia` (opcional) | `ibge` e indicadores financeiros/por aluno para calibração |

Use como modelo a entrada do catálogo, mude o ID e a identificação, informe caminhos relativos ao manifesto e forneça todas as tabelas coerentes. Os hashes são calculados na importação. Declare categorias fracionárias apenas quando justificadas na fonte. O processo não preenche redes ausentes com zero nem transforma ausência em valor observado.

```bash
# Apenas conferir: não altera catálogo nem dados
python -m scripts.importar_base /caminho/da/nova_base/manifesto.json

# Registrar versão nova, sem sobrescrever versões anteriores
python -m scripts.importar_base /caminho/da/nova_base/manifesto.json --registrar

# Auditoria por ID, incluindo desvios por UF
python -m scripts.auditar_base legado
```

O relatório de importação informa redes/categorias novas e ausentes, além da calibração. O registro usa cópia validada, lock de importação e troca atômica do catálogo. Um ID existente nunca é sobrescrito. Bases preliminares devem usar `status: "preliminar"`; a versão definitiva recebe outro ID.

Para `status: "homologada"`, são necessários exercício, fontes, registro `homologacao` com responsável, referência tabular declarada oficial (`referencia_oficial: true`) e comparação aprovada nas tolerâncias do manifesto. A marcação é uma decisão do operador responsável pelas fontes; não é certificação do FNDE.

### Grupo Propag

O catálogo inicial não inventa a lista dos 22 estados. Quando a equipe a confirmar, uma nova versão deve registrar `propag.status: "validado"`, `propag.ufs` e `propag.fonte`. A seleção fica disponível após esse registro.

### Fator amazônico

Está disponível um adaptador para **fatores validados incidentes sobre matrículas ponderadas por ente**. Ele exige no manifesto `amazonico.status: "validado"`, `norma`, `responsavel_validacao`, `ano_inicio`, `ano_fim` e `incidencia: "matriculas_ponderadas_por_ente"`, além do arquivo `fatores_amazonicos` com `ibge`, `fator_vaaf`, `fator_vaat` para todas as redes; use fator 1 nas não abrangidas. Os coeficientes devem vir da especificação confirmada pela equipe, não de estimativa do aplicativo.

O catálogo legado não contém essa regra, e a ativação é rejeitada. Se a norma efetiva incidir por categoria ou por outro mecanismo, será necessário implementar essa incidência específica; o adaptador não é apresentado como implementação normativa universal. Vigência, incidência e cobertura são verificadas antes do cálculo.

## API

| Rota | Comportamento |
|---|---|
| `GET /api/bases` | Bases cadastradas e situação |
| `GET /api/bases/{id}` | Metadados, categorias e parâmetros |
| `GET /api/bases/{id}/auditoria` | Cobertura e calibração |
| `GET /api/entes?base_id=legado&tipo=estaduais&uf=CE` | Cadastro filtrado |
| `GET /api/entes/{ibge}/matriculas?base_id=legado` | Valores originais |
| `POST /api/cenarios` | Calcula e guarda A–D; devolve resumo e comparação |
| `GET /api/cenarios/{id}?completo=true` | Recupera snapshot, incluindo dados nacionais |
| `GET /api/cenarios/{id}/exportar?formato=xlsx&comparacao=B-A` | Exportação do resultado salvo |
| `POST /api/trajetorias` | Trajetória linear EPT e receita composta |

O OpenAPI em `/docs` descreve o contrato integral. Operações de matrícula: `definir`, `adicionar`, `percentual` (aumento relativo) e `converter` (exige `destino`). Cada célula rede/categoria pode participar de apenas um ajuste no conjunto, incluindo origem e destino. Conflitos são rejeitados, evitando dependência da ordem de aplicação.

Exemplo exploratório com a base legada, sem atribuir exercício:

```json
{
  "base_id": "legado",
  "nome": "Expansão conjunta CE e PI",
  "ajustes": [
    {"ibge": 23, "etapa": "ensino_medio_integrado_a_educacao_profissional_rede_publica", "operacao": "adicionar", "valor": 500},
    {"ibge": 22, "etapa": "ensino_medio_integrado_a_educacao_profissional_rede_publica", "operacao": "adicionar", "valor": 300}
  ],
  "receita": {"taxa_percentual": 5, "rubricas": ["recursos_vaaf", "recursos_vaat"], "complementacoes": "fixas"},
  "recorte": {"tipo": "estaduais", "ufs": []}
}
```

## Persistência e configuração

| Variável | Padrão | Uso |
|---|---|---|
| `FUNDEB_CATALOGO` | `data/catalogo.json` | Catálogo alternativo |
| `FUNDEB_CENARIOS_DB` | `.runtime/cenarios.sqlite3` | SQLite local com snapshots JSON comprimidos |
| `FUNDEB_MAX_CENARIOS` | `1000` | Limite de cenários; ao atingir, novas gravações são recusadas, sem apagar anteriores |

Em implantação, monte armazenamento persistente para o banco e para as bases. Instâncias devem acessar o mesmo armazenamento local compatível com SQLite, ou receber um adaptador de armazenamento compartilhado antes de operar em múltiplos servidores independentes. Para backup, use o mecanismo de backup do SQLite, considerando o modo WAL; não copie apenas o arquivo principal durante gravações.

## Verificação

```bash
python -m pytest tests/ -q
npm ci
# Se o Python não estiver no ambiente ativo, aponte para ele:
FUNDEB_TEST_PYTHON=.venv/bin/python npm run test:ui
```

Os testes de interface usam DOM em memória e API real; não verificam pixels. Os testes financeiros cobrem execução nacional conjunta, independência da ordem, conservação, limites de entrada, modelos de receita, snapshot, importação, vigência e exportações. A verificação com navegador real e a homologação por Marcele/Joyce permanecem necessárias para a aprovação visual pelos usuários.
