# Migração sem perda de histórico

A branch prepara o sistema, mas não acessa nem migra automaticamente o servidor em produção. Execute em homologação, confira os resultados e só depois troque a aplicação. **Não reinicie o servidor antigo antes de capturar os cenários vivos.**

## 1. Preservar a origem

Registre commit em execução, configuração (sem publicar segredos), `python --version` e `pip freeze`. Faça cópia verificável do diretório de dados e backup consistente do SQLite de usuários, incluindo transações em WAL. O comando `import-users` usa a API de backup do SQLite para obter uma fotografia consistente; durante o corte, suspenda alterações de usuários.

O código antigo guarda apenas os últimos 30 cenários na memória de **cada processo**. Um script iniciado em outro terminal não enxerga essa memória. Cenários já expulsos ou perdidos em reinícios anteriores não podem ser recuperados apenas pelo Git; será necessário procurar exportações e backups existentes.

Se houver acesso a um console Python **dentro do processo antigo**, carregue o script da nova branch por caminho absoluto, sem importar ou reiniciar o novo servidor:

```python
import importlib.util
from services.cenarios import repositorio  # instância já carregada no processo antigo
spec = importlib.util.spec_from_file_location(
    "captura_fundeb", "/caminho/nova-branch/scripts/capture_legacy_memory.py"
)
modulo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modulo)
modulo.capturar(repositorio, "/caminho/protegido/worker1.live-scenarios.zip")
```

Repita para cada worker. Suspenda novas simulações durante a captura final. A ferramenta bloqueia o repositório enquanto copia todos os objetos e preserva IDs, parâmetros e DataFrames. Ela exige PyArrow no ambiente antigo, dependência já listada no projeto original.

Se não existir esse acesso, **não trate a captura como concluída** e não reinicie o processo: identifique com o operador uma forma de exportação no processo vivo. Downloads pelas APIs antigas são úteis, mas não substituem a captura integral dos objetos. Arquivos CSV/XLSX/PDF já baixados pelos usuários também precisam ser preservados separadamente; não estão automaticamente no repositório.

## 2. Preparar um destino vazio

Localmente, use Python 3.12:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
export FUNDEB_DATABASE_URL='sqlite:///data/fundeb.db'
python -m app.cli migrate
python -m app.cli import-data --dry-run
python -m app.cli import-data
python -m app.cli import-users /caminho/protegido/usuarios.db --dry-run
python -m app.cli import-users /caminho/protegido/usuarios.db
python -m app.cli import-live /caminho/protegido/worker1.live-scenarios.zip --dry-run
python -m app.cli import-live /caminho/protegido/worker1.live-scenarios.zip
```

Para uma instalação sem usuários anteriores, `python -m app.cli create-admin` solicita CPF e senha no terminal; não passa a senha na linha de comando. Não execute isso antes de migrar os usuários existentes.

`import-data --dry-run` confere todos os arquivos e compara os caches com uma construção nova das bases, sem gravar dados. A importação efetiva é uma única transação: originais, versões, projeções e aliases. Repetir a mesma importação mantém as versões existentes. Conflitos de usuários/cenários interrompem a transação, sem sobrescrita nem rehash de senhas.

## 3. PostgreSQL com Compose

Copie `.env.example` para `.env` e configure senha do banco e segredo JWT. Para uma migração, mantenha inicialmente o segredo da instalação anterior, desde que atenda aos requisitos. Um segredo novo invalida sessões, mas não altera senhas nem cálculos. Sirva a aplicação por HTTPS para usar o cookie seguro de produção.

```bash
docker compose up -d db
docker compose build app
docker compose run --rm app python -m app.cli migrate
docker compose run --rm app python -m app.cli import-data --dry-run
docker compose run --rm app python -m app.cli import-data
```

Para migrar arquivos privados, monte o diretório como somente leitura:

```bash
docker compose run --rm -v /caminho/protegido:/migration:ro app \
  python -m app.cli import-users /migration/usuarios.db
docker compose run --rm -v /caminho/protegido:/migration:ro app \
  python -m app.cli import-live /migration/worker1.live-scenarios.zip
```

Confira usuários, quantidades, IDs, parâmetros, resultados e exportações antes de `docker compose up -d app`. Não use `docker compose down -v`: isso apagaria o volume do banco. Para implantação fora do Compose, exporte `FUNDEB_DATABASE_URL`, `FUNDEB_ENV=production`, `FUNDEB_DATA_SOURCE=database` e `FUNDEB_SECRET_KEY`; use um gerenciador de segredos do ambiente.

## 4. Validar antes da troca

```bash
pytest -q
# Banco PostgreSQL exclusivo de testes; o teste cria/remove schemas temporários.
FUNDEB_TEST_DATABASE_URL='postgresql+psycopg://usuario:senha@localhost/testes' \
  pytest tests/test_persistence.py -q
```

Confronte também os cenários reais capturados da produção. Garanta que cada worker foi capturado, que as senhas antigas continuam funcionando, que usuários inativos continuam inativos e que os IDs antigos podem ser consultados sem novo cálculo. A mudança de infraestrutura só deve ser liberada após esses critérios.

`/historico.html` reúne as simulações persistidas. O administrador vê todo o histórico; usuários veem os registros novos atribuídos a eles. Os registros importados, sem autoria antiga disponível, ficam listados para administradores.

## 5. Backup, ensaio de restauração e retorno

```bash
mkdir -p backups
python -m app.cli backup backups/pre-corte.fundeb-backup.zip
python -m app.cli verify-backup backups/pre-corte.fundeb-backup.zip
# Use OUTRO banco vazio para o ensaio. Nunca restaure sobre a produção atual.
FUNDEB_DATABASE_URL='sqlite:///backups/ensaio.db' python -m app.cli migrate
FUNDEB_DATABASE_URL='sqlite:///backups/ensaio.db' \
  python -m app.cli restore backups/pre-corte.fundeb-backup.zip
```

No Compose, use volume gravável restrito para backups e garanta permissão ao UID 10001. Guarde cópia fora do servidor, criptografada pela infraestrutura. Verifique periodicamente o restore em uma instância PostgreSQL separada.

No corte: suspenda escritas, capture o estado final, migre, compare, registre um backup e só então aponte o tráfego para a nova aplicação. Mantenha o servidor e arquivos antigos intactos durante a janela de validação. Se houver problema, interrompa novas escritas, preserve também os novos registros e restaure o backup em outro banco antes de decidir o retorno. Uma troca simples para o processo antigo não absorve os cenários criados no sistema novo.
