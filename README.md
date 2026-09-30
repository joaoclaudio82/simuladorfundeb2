# Simulador FUNDEB

Aplicação FastAPI para simulações de 2024, 2025 e 2026, com PostgreSQL, bases versionadas, usuários e resultados persistidos. A refatoração conserva o motor de cálculo e os contratos da interface existente.

## Banco único: PostgreSQL

Dados de 2024/2025/2026, arquivos originais, matrículas, pesos, receitas, usuários, cenários, resultados e exportações ficam no **mesmo PostgreSQL**. A aplicação e os testes exigem PostgreSQL. Não há banco SQLite local nem consulta automática a planilhas, RDA, PKL ou Parquet durante a execução.

Os arquivos continuam no Git como fontes preservadas para importação e auditoria. O comando `import-data` grava também seus bytes integrais no PostgreSQL. Após a importação, as simulações consultam o banco.

## Executar

Configure `.env` a partir de `.env.example`, com senha do PostgreSQL e segredo JWT. Depois:

```bash
docker compose up -d db
docker compose build app
docker compose run --rm app python -m app.cli migrate
docker compose run --rm app python -m app.cli import-data --dry-run
docker compose run --rm app python -m app.cli import-data
docker compose run --rm app python -m app.cli verify-data
# Apenas em instalação nova, sem usuários anteriores:
docker compose run --rm app python -m app.cli create-admin
docker compose up -d app
```

A aplicação escuta em `127.0.0.1:8000`; configure o proxy HTTPS para o cookie seguro de produção. Em desenvolvimento HTTP local, use `FUNDEB_ENV=development` e `FUNDEB_COOKIE_SECURE=false`, mantendo PostgreSQL. Para execução Python direta, configure `FUNDEB_DATABASE_URL` com `postgresql+psycopg://…` ou as variáveis `FUNDEB_DB_HOST`, `FUNDEB_DB_NAME`, `FUNDEB_DB_USER` e `FUNDEB_DB_PASSWORD`. Não coloque senhas no Git.

**Instalação existente:** siga [MIGRACAO.md](docs/MIGRACAO.md) antes de reiniciar o servidor. `import-users` lê o SQLite antigo de autenticação; `import-sqlite` transfere integralmente um eventual `fundeb.db` unificado para PostgreSQL vazio, incluindo os cálculos já salvos. SQLite é aceito somente como arquivo de origem da migração.

## Organização

- [Arquitetura e modelo de dados](docs/ARQUITETURA.md)
- [Estado do PostgreSQL local](docs/BANCO.md)
- [Inventário, diferenças existentes e equivalência](docs/DADOS_E_COMPATIBILIDADE.md)
- [Migração, captura, backup e retorno](docs/MIGRACAO.md)
- [Documentação anterior preservada](docs/README_ANTERIOR.md) — referência histórica; execução atual segue este README.

Os dados originais permanecem nos caminhos existentes e também são importados integralmente. `data/manifesto_arquivos.json` confere todos os arquivos. Novas versões não substituem bases antigas. Cenários, solicitações, resultados e exportações ficam no banco e podem ser consultados em **Histórico de simulações**.

## Produção

Há `Dockerfile`, `compose.yaml` e `.env.example`. Produção exige PostgreSQL, dados carregados do banco e segredo de autenticação configurado. O roteiro completo está em [MIGRACAO.md](docs/MIGRACAO.md). Criar a branch não implanta nem altera o servidor existente.

## Verificação

```bash
FUNDEB_TEST_DATABASE_URL='postgresql+psycopg://usuario:senha@localhost/fundeb_test' pytest -q
ruff check app tests
```

Toda a integração contínua executa em PostgreSQL, importa as três bases e confronta resultados com o commit original `b34590c`. Os testes usam schemas próprios em banco de testes explicitamente configurado; verificam também a execução com a leitura dos arquivos originais bloqueada. Testes verificam o código idêntico do motor, todas as células das bases, cenários A/B/C/D, precisão, usuários/hashes, retenção após reinício, exportações e backup/restauração.

Os dados continuam com suas pendências metodológicas de origem. A reorganização não muda fórmulas, padrões de complementação nem resultados para tentar corrigir essas pendências.
