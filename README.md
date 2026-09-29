# Simulador FUNDEB

Aplicação FastAPI para simulações de 2024, 2025 e 2026, com PostgreSQL, bases versionadas, usuários e resultados persistidos. A refatoração conserva o motor de cálculo e os contratos da interface existente.

## Começar em desenvolvimento

Python 3.12:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.cli migrate
python -m app.cli import-data --dry-run
python -m app.cli import-data
python -m app.cli create-admin
FUNDEB_DATA_SOURCE=database uvicorn app.main:app --reload
```

Abra `http://localhost:8000`. O banco local padrão é `data/fundeb.db` (ignorado pelo Git). `uvicorn main:app` continua funcionando. Não existe usuário/senha padrão.

**Instalação existente:** antes de reiniciar ou substituir o servidor, siga [MIGRACAO.md](docs/MIGRACAO.md). Os cenários antigos podem existir apenas na memória do processo; o código novo, sozinho, não os recupera. Migre o SQLite real de usuários antes de criar um administrador.

## Organização

- [Arquitetura e modelo de dados](docs/ARQUITETURA.md)
- [Inventário, diferenças existentes e equivalência](docs/DADOS_E_COMPATIBILIDADE.md)
- [Migração, captura, backup e retorno](docs/MIGRACAO.md)
- [Documentação anterior preservada](docs/README_ANTERIOR.md) — referência histórica; execução atual segue este README.

Os dados originais permanecem nos caminhos existentes e também são importados integralmente. `data/manifesto_arquivos.json` confere todos os arquivos. Novas versões não substituem bases antigas. Cenários, solicitações, resultados e exportações ficam no banco e podem ser consultados em **Histórico de simulações**.

## Produção

Há `Dockerfile`, `compose.yaml` e `.env.example`. Produção exige PostgreSQL, dados carregados do banco e segredo de autenticação configurado. O roteiro completo está em [MIGRACAO.md](docs/MIGRACAO.md). Criar a branch não implanta nem altera o servidor existente.

## Verificação

```bash
pytest -q
ruff check app tests/test_persistence.py tests/test_regression_baseline.py tests/test_persistence_api.py
```

A integração contínua executa testes com SQLite e PostgreSQL, importa todas as bases e confronta resultados com o commit original `b34590c`. Testes verificam o código idêntico do motor, todas as células das bases, cenários A/B/C/D, precisão, usuários/hashes, retenção após reinício, exportações e backup/restauração.

Os dados continuam com suas pendências metodológicas de origem. A reorganização não muda fórmulas, padrões de complementação nem resultados para tentar corrigir essas pendências.
