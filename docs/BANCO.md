# Banco de dados em uso

Retrato do PostgreSQL local que a aplicação consulta agora. Conferido em 29/09/2026. Não contém senhas, CPF nem segredo de sessão.

Este banco é a instalação local do volume `simuladorfundeb2_fundeb_postgres`. Não é o corte de um servidor antigo.

## Onde está

| Item | Valor |
|---|---|
| Container | `simuladorfundeb2-db-1` |
| Imagem | PostgreSQL 17.11 |
| Banco da aplicação | `fundeb` |
| Publicação no host | `127.0.0.1:5434` |
| Usuário do banco | `fundeb` |
| Revisão do esquema | Alembic `0001` |
| Aplicação | `http://127.0.0.1:8000`, com `FUNDEB_DATA_SOURCE=database` |

A senha fica só no `.env` local, fora do Git. A aplicação no Compose alcança o banco pelo hostname `db`, na porta interna `5432`.

Há dois outros bancos no mesmo servidor, separados do uso:

- `fundeb_test` — só para a suíte de testes, com schemas temporários.
- `fundeb_ensaio` — banco vazio usado para ensaiar a restauração do backup. Não recebe tráfego da aplicação.

## O que a aplicação lê

A execução consulta somente o PostgreSQL. Planilhas, RDA, PKL e Parquet continuam no Git como fonte de importação e auditoria. Depois da carga, simulações e histórico saem do banco.

A versão ativa de cada exercício é a linha de `base_aliases`. Um cenário já gravado guarda a versão que usou e não é recalculado quando a base ativa muda.

## Bases ativas

Origem dos arquivos: commit `b34590c50dbe68a07972f98c287f2d9f7936867c`. Importação em 29/09/2026, 02:01 UTC.

| Exercício | Base | Entes | Categorias | Matrículas | Registros financeiros |
|---|---|---:|---:|---:|---:|
| 2024 | `fundeb-2024` | 5.595 | 41 | 57.701 | 5.595 |
| 2025 | `fundeb-2025` | 5.595 | 319 | 88.762 | 5.595 |
| 2026 | `fundeb-2026` | 5.596 | 319 | 105.738 | 5.596 |

Identificadores ativos:

| Exercício | `version_id` | Snapshot |
|---|---|---|
| 2024 | `e6d4c9daba508abb8abd1d17333462cc52d1ad15c35be2b33fe909a3370d4bb9` | `13924d68412e…` |
| 2025 | `01b06a1275f47c07cee41523b3d1864f514d8ef4585b6d16eb4f5cb13359c1d9` | `63577ec153fa…` |
| 2026 | `3fb76f37418d916aef7eb9104835fe5fec6ab8a1c2df94b85fc82ad9de470010` | `de601d4cbffe…` |

As matrículas são a projeção esparsa: célula ausente vale zero. O snapshot da versão guarda a matriz completa, inclusive zeros, ordem e tipos.

## Versões inativas

Existem seis linhas em `base_versions`: as três ativas e uma cópia de cada exercício, gravada em 29/09/2026, 14:31 UTC. O snapshot de cada cópia é o mesmo da versão ativa. A segunda cópia surgiu porque a reimportação rodou com os arquivos Python em CRLF e o identificador da versão inclui o hash desses arquivos. Os aliases não foram trocados. A aplicação continua nas versões da tabela acima.

## Arquivos originais

`source_files` e `archives` têm 33 arquivos, 71.362.217 bytes. O SHA-256 de cada um confere com `data/manifesto_arquivos.json`. São 27 originais e 6 históricos, entre eles os Parquet de 2026.

## Operação gravada

Contagem no momento desta conferência:

| Tabela | Linhas | O que é |
|---|---:|---|
| `users` | 1 | Administrador local criado nesta instalação. Não veio de `usuarios.db`. O hash é bcrypt. |
| `scenarios` | 1 | Simulação de verificação `78e3a44b2bf243468755f786f8e17eb5`, base 2024, versão ativa de 2024, criada em 29/09/2026 14:37 UTC. |
| `scenario_results` | 11.190 | Projeção dessa simulação. |
| `exports` | 1 | CSV de 11.976 bytes dessa simulação, gerado em 29/09/2026 14:38 UTC. |
| `legacy_runs` | 3 | Duas chamadas a `/api/simular` e uma a `/api/2026/simular/municipio`, entre 14:53 e 14:54 UTC. |
| `audit_events` | 12 | 6 `base.import`, 1 `user.create`, 1 `scenario.save`, 1 `export.save`, 3 `legacy.save`. |

## O que não está neste banco

Não havia processo antigo em execução, então os cenários que o sistema anterior guardava só na memória de cada worker não foram capturados.

Não foram encontrados `usuarios.db`, `fundeb.db` nem arquivo `*.live-scenarios.zip` no repositório, na Área de Trabalho, em Documentos ou em Downloads. `import-users` e `import-live` não foram executados.

## Backup

O backup lógico conferido está em `backups/pos-verificacao.fundeb-backup.zip` (52.676.721 bytes). `verify-backup` validou as 16 tabelas. A restauração foi ensaiada em `fundeb_ensaio`, que ficou com as mesmas versões ativas e a mesma simulação de verificação. Esse zip é anterior às três simulações de rota antiga; elas existem só no banco `fundeb`.

Não apague o volume com `docker compose down -v`. Restaure sempre em um banco vazio.

Para repetir a conferência sem expor dados pessoais:

```bash
python -m app.cli verify-data
```
