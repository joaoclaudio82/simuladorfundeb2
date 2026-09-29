# Arquitetura e contratos de preservação

Esta refatoração parte de `maio2026`, commit `b34590c50dbe68a07972f98c287f2d9f7936867c`. A branch `main` tem outro histórico. As demais branches permanecem no Git e não são incorporadas silenciosamente como bases ativas.

## Estrutura

| Diretório | Responsabilidade |
|---|---|
| `app/main.py` | Composição da aplicação e rotas compatíveis |
| `app/api/` | Rotas por exercício e captura das simulações antigas |
| `app/domain/calculo/` | Motor matemático e validação interna |
| `app/services/` | Cenários, comparação, calibração e exportação |
| `app/repositories/` | Persistência de bases, cenários e cálculos antigos |
| `app/db/` | Esquema, conexões, serialização, backup e restauração |
| `app/ingestion/` | Leitura das fontes e migrações verificadas |
| `app/auth/` | Usuários, autenticação, perfis e cookies |
| `app/schemas/` | Contratos de entrada |
| `app/core/` | Configuração e validação do ambiente |
| `static/` | Interface existente e histórico de simulações |
| `migrations/` | Revisões Alembic, com DDL inicial congelado |
| `tests/golden/` | Referências capturadas antes da mudança |
| `scripts/` | Ferramenta para captura no processo antigo |

Os módulos antigos na raiz e em `auth/`, `dados/`, `services/` e `schemas/` são adaptadores de importação. Não contêm uma segunda implementação. Preservam `uvicorn main:app`, scripts e testes existentes. O carregador histórico de planilha, antes misturado ao bootstrap, permanece em `app/ingestion/legacy_2024.py`.

## O que existe no banco

| Tabela | Conteúdo / garantia |
|---|---|
| `users` | CPF, hash bcrypt, nome, perfil, situação e data; nunca senha aberta |
| `source_files` | Bytes integrais dos arquivos originais, tamanho e SHA-256 |
| `archives` | Caminho, origem e classificação de cada arquivo; inclui derivados históricos |
| `base_versions` | Versão imutável de todas as tabelas, manifesto, ETL e origem |
| `base_aliases` | Versão explicitamente ativa para cada identificador de base |
| `base_sources` | Fontes exatas de cada versão |
| `entities` | Entes, UF, rede e ordem original |
| `categories` | Categorias, pesos VAAF/VAAT e ordem original |
| `enrollments` | Matrículas por versão, ente e categoria; projeção esparsa |
| `financial_inputs` | Valores sociofiscais e financeiros por ente |
| `scenarios` | Requisição, parâmetros, resultados completos, validações, motor, proprietário e resposta original |
| `scenario_results` | Resultados por cenário A/B/C/D e ente, consultáveis por SQL |
| `exports` | Bytes dos CSV/XLSX/PDF efetivamente gerados e seus hashes |
| `legacy_runs` | Requisição e resposta exata das rotas antigas; todas as entradas e linhas de cálculo |
| `audit_events` | Importações, ativações, gravações, exportações e mudanças de usuários; sem senhas |

As matrículas usam `DOUBLE PRECISION` no PostgreSQL para preservar o tipo numérico do motor. A projeção esparsa omite **apenas zeros**: para uma combinação válida de versão/ente/categoria, ausência significa zero. Matrículas fracionárias são conservadas. O snapshot mantém também zeros explícitos, índices, tipos e ordem originais. Não se reconstrói a entrada do motor por somas SQL.

Os snapshots usam ZIP com JSON tipado e Arrow IPC, com SHA-256. Preservam tipos pandas, ordem, categorias, valores nulos, infinitos, frações e precisão binária. A aplicação não desserializa pickle recebido de usuário nem lê pickle do banco. Os pickles legados são lidos somente na importação das fontes locais verificadas pelo inventário; a importação compara seu conteúdo com uma construção nova do ETL sem sobrescrever os arquivos.

Valores não finitos viram `null` nas projeções JSON consultáveis, como já acontece nas respostas da API. O valor original continua no snapshot. A interface e o motor recebem o snapshot exato, não essa projeção.

## Versões e imutabilidade

A identidade de uma base inclui hash do snapshot, hashes das fontes e hash do processamento. Um arquivo novo não substitui uma versão antiga. Uma nova versão só passa a ser ativa com `import-data --activate`; a ativação é auditada. Faça isso em manutenção e reinicie todos os workers juntos: o endpoint legado 2024 conserva seu dataset inicial durante a vida do processo.

Cenários novos mantêm a versão da base utilizada. Uma tentativa de substituir o resultado de um ID existente por outro conteúdo falha. Consultas não executam novamente o motor. A resposta original de criação é devolvida quando o cenário é consultado sem alterar o recorte. Um novo recorte reorganiza os resultados armazenados; não recalcula o Fundeb. A primeira exportação de cada combinação de formato/recorte/seleção é gravada; downloads seguintes devolvem os mesmos bytes, inclusive XLSX/PDF.

As rotas antigas agora capturam também o resultado nacional inteiro, mesmo quando a resposta mostra apenas as primeiras 200 linhas. O middleware só entrega sucesso depois da gravação, com `X-Simulation-ID`. O histórico permite recuperar essa resposta e baixar o snapshot completo.

Cenários trazidos do processo antigo mantêm seu ID, data e versão de motor. O sistema anterior não registrava proprietário nem versão do ETL da base: esses campos permanecem desconhecidos, sem atribuição inventada. Administradores os veem no histórico. O acesso por ID de cenário conserva o contrato autenticado já existente; o histórico pessoal de cenários novos filtra o proprietário. As simulações das rotas antigas têm consulta por proprietário ou administrador.

## Operação

PostgreSQL é o banco exigido em produção. SQLite serve ao desenvolvimento e aos testes locais. `FUNDEB_DATABASE_URL` seleciona o destino; usuários, fontes e simulações usam o mesmo banco. Em produção, o processo exige esquema migrado, fonte `database`, segredo forte e cookies seguros. Não há administrador com senha padrão. Cookies de sessões antigas podem continuar válidos se o mesmo segredo for mantido na migração; perfil e situação continuam consultados no banco.

Backups lógicos são consistentes, incluem todas as tabelas, usam checksums e são gravados com permissão local `0600`. A restauração exige um banco vazio e ocorre em transação. O arquivo contém CPFs e hashes: armazenamento e transporte precisam ser restritos, com criptografia provida pela infraestrutura. Mantenha também o backup nativo/PITR do PostgreSQL conforme a política do ambiente.

Novas migrações recebem novas revisões Alembic. A revisão inicial não deve ser editada depois de implantada. Downgrade destrutivo é recusado; a recuperação usa backup em outro banco e troca controlada de conexão.
