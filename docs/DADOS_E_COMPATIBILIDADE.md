# Dados encontrados e comportamento preservado

O inventário `data/manifesto_arquivos.json` identifica os **33 arquivos** de dados e referências existentes no commit de origem: 71.362.217 bytes. A importação guarda seus bytes, além das tabelas estruturadas. Fontes incluem RDA, planilhas XLSX/XLSM, PDFs, caches PKL e Parquet. Os arquivos continuam no Git. PDFs e planilhas históricos não são promovidos automaticamente a base ativa.

| Exercício | Entes | Categorias ativas | Origem da base utilizada |
|---|---:|---:|---|
| 2024 | 5.595 | 41 | RDA + ponderador NSE em PDF |
| 2025 | 5.595 | 319 | Planilha de matrículas, receita, NSE/DREC e receita STN VAAT |
| 2026 | 5.596 | 319 | Matrículas, receita prevista, NSE/DREC, memória VAAT e inabilitados |

Os dados educacionais são agregados por rede, não cadastros de alunos. Os dados pessoais de autenticação são separados nas tabelas de usuários e autoria.

## Diferenças preexistentes que não foram corrigidas nesta refatoração

- Os Parquet de 2026 diferem da base carregada pelo sistema. Foram arquivados como históricos; os valores ativos continuam vindo do dataset usado em `maio2026`.
- Existem matrículas fracionárias em 2024 e 2025. Não foram arredondadas nem convertidas para inteiros.
- O catálogo identifica pendências de homologação, inclusive Pernambuco e Canavieiras em 2026. Continuam visíveis; a migração não equivale a homologação legal ou metodológica.
- A base de 2025 não tem a lista oficial de inabilitados VAAT. O comportamento existente é conservado.
- As rotas antigas usam valores padrão de complementação de 2024 quando o cliente omite parâmetros, inclusive em outros exercícios. Isso difere dos padrões dos cenários nacionais. Os testes conservam ambos os contratos.
- O motor atual não reescala NSE pelos parâmetros mínimo/máximo. O cálculo do NF depende do modo do exercício. Não houve mudança dessa regra.
- A agregação de VAAF/VAAT nas rotas antigas e nos comparativos nacionais não é idêntica. Cada uma foi preservada.
- Ajustes fracionários em colunas originalmente inteiras podem ser recusados pelo pandas da versão testada. A refatoração não muda esse comportamento nem os tipos das bases para contorná-lo.

Qualquer correção metodológica posterior deve criar outra versão do motor/base, com testes próprios. Resultados históricos não devem ser atualizados retroativamente.

## Evidência de equivalência

`tests/golden/legacy_b34590c.json` foi capturado no checkout original **antes** de mover os módulos. Contém identificação do commit, hash do motor, versões numéricas, hashes de todas as células/tipos/ordens das seis tabelas de cada exercício, três perfis de cenários por exercício e respostas das rotas antigas.

Os perfis cobrem A/B, A/B/C/D com receita ampliada, ajustes de matrícula, pesos customizados e parâmetros fiscais. A regressão compara todas as linhas nacionais, não apenas totais ou amostras. O arquivo `app/domain/calculo/motor.py` mantém exatamente os bytes do motor original, verificados em teste.

A referência usa Python 3.12, pandas 3.0.6, NumPy 2.5.3 e PyArrow 25.0.1; as dependências são fixadas em `requirements.txt`. O ambiente efetivo do servidor antigo deve ser registrado antes da troca. Não se presume que suas versões sejam estas. Se a produção tiver outras versões, capture resultados representativos nesse ambiente e confronte antes da liberação.

## Destino operacional

Todos os três exercícios são lidos exclusivamente do PostgreSQL. Os caminhos acima identificam as fontes históricas preservadas no Git; não são o armazenamento ativo da aplicação. A carga inclui seus bytes integrais em `source_files`, as versões completas em `base_versions` e as projeções por ente/categoria. `python -m app.cli verify-data` permite conferir o banco de destino.
