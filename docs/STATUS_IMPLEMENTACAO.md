# Status da implementação

Verificação local em 26/09/2026. O software foi implementado em branch própria; a homologação das fontes e das regras não é presumida.

| Item | Implementação | Dependência restante |
|---|---|---|
| FND-01 — inventário | Catálogo, hashes, cobertura, tipos, categorias e relatório por UF. | Confirmar exercício e fonte dos arquivos legados. |
| FND-02 — indicadores e cálculo | Unidades separadas, agregação por razão de somas, junção por ID e modelo VAAT explícito. | Validar composição VAAT com a equipe responsável pela metodologia. |
| FND-03 — versões | Carregamento e importação de versões imutáveis, com conferência de hashes. | Fornecer as versões oficiais de interesse. |
| FND-04 — agosto e calibração | Importador e comparação por indicador/UF, com tolerâncias e rejeição de homologação inconsistente. | Receber receitas de agosto, esclarecer período e conferir PE; a base 2026 ainda não foi carregada. |
| FND-05 — cenário conjunto | Ajustes por rede/categoria; aplicação única antes do cálculo nacional; snapshot persistente. | Homologação funcional da equipe. |
| FND-06 — interface conjunta | Edição por UF, conjunto persistente ao trocar seletores, conflitos e remoção individual. | Revisão visual por usuários em navegador real. |
| FND-07 — visão nacional | Redes estaduais/DF por padrão; outros recortes; participação relativa e impacto em todas as redes. | Confirmar a lista do grupo Propag para habilitar esse recorte. |
| FND-08 — exportações | PDF, CSV e Excel a partir do mesmo snapshot; dados completos no Excel e todos os entes do recorte. | Revisão editorial pela equipe, caso haja modelo institucional de apresentação. |
| FND-09 — nomenclatura | “Ente federado”, unidades e aviso metodológico na interface e nos arquivos. | Homologação dos rótulos e do fluxo pelos usuários. |
| FND-10 — receita | Taxa informada ou CAGR de série PIB fornecida, rubricas e complementações parametrizadas. | Selecionar fonte/período do PIB e hipótese de crescimento da arrecadação. |
| FND-11 — A–D | Quatro cenários e quatro comparações; participação em p.p.; exportação vinculada à execução. | Validação de casos reais com as bases confirmadas. |
| FND-12 — censo preliminar | Importação com relatório de redes/categorias novas/ausentes, sem preencher ausências com zero. | Receber base preliminar e dicionário. |
| FND-13 — EPT | Trajetória linear, adição/conversão, arredondamento e receita composta; hipóteses registradas. | Confirmar definição normativa da meta, população e categorias. |
| FND-14 — fator amazônico | Adaptador de fatores por ente, vigência/cobertura verificadas e ativação condicionada. | Obter norma e coeficientes; se a incidência efetiva for diferente, implementar a regra específica. |

## Evidências da auditoria

- 5.595 redes: 5.568 municipais, 26 estaduais e a rede do Distrito Federal.
- 41 categorias; 804 valores fracionários em AEE/educação especial conveniada, preservados e declarados no catálogo.
- As tabelas legadas de matrículas, receitas e cadastro cobrem os mesmos IDs, sem duplicatas.
- Comparando o cálculo com os parâmetros legados ao arquivo `cenario_atual.rda`, 4.733 redes ficaram fora das tolerâncias de R$ 1 + 0,01% para recursos totais do Fundeb; maior desvio absoluto de aproximadamente R$ 4.806.976,71. O arquivo de referência não foi confirmado como oficial. Os demais indicadores e o detalhamento por UF estão no comando de auditoria.
- A comparação de cenários utiliza a mesma base recalculada para A–D, sem utilizar o snapshot divergente como se fosse a referência homologada de 2026.

## Validação executada

**45 testes Python passaram**, incluindo os sete testes preexistentes. Eles cobrem requisitos financeiros, recortes, entradas inválidas, hashes, importação, fatores condicionados, conservação e exportações. **Três testes de fluxo DOM com API real passaram**, verificando duas UFs no mesmo conjunto, persistência ao trocar seletores, taxa PIB, trajetória EPT e exportação do resultado anterior após editar controles. A verificação Ruff dos erros críticos também passou.

Foi executada uma simulação exploratória na base completa com acréscimos de 500 matrículas de ensino médio integrado no CE e 300 no PI, e hipótese nominal de receita de 5%. Os quatro cenários cobriram as 5.595 redes. Foram gerados PDF, CSV e Excel; o PDF foi renderizado para inspeção de paginação e o Excel aberto para conferência de abas. Esses números são entradas de verificação funcional, não resultados homologados de política pública.

O navegador disponibilizado no ambiente bloqueou o acesso ao servidor local. Portanto, não se declara verificação visual da interface em navegador real. A inspeção visual de PDF e os testes DOM/API foram realizados; a revisão visual da interface permanece explícita.

## Persistência e entrega

Os resultados ficam em SQLite local e não entram no Git. Bases novas têm ID próprio, e importações não substituem versões já registradas. Os arquivos legados originais não foram alterados. A implantação precisa preservar o banco entre reinicializações conforme o guia técnico.
