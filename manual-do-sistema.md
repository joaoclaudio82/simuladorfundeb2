# Manual do Simulador FUNDEB v2

**Versão do documento:** agosto/2026 (branch `maio2026`)
**Público:** gestores educacionais, analistas, professores, técnicos e desenvolvedores — inclusive quem nunca ouviu falar em FUNDEB
**Autor:** IFCE — prof. João Cláudio Nunes Carvalho

---

## Como ler este manual

O manual está dividido em três partes. Você não precisa ler tudo:

| Parte | Seções | Para quem |
|-------|--------|-----------|
| **I — Entender** | 1 e 2 | Todo mundo. Explica o que é o sistema e o que é o FUNDEB, sem jargão. |
| **II — Usar** | 3 a 8 | Quem vai operar o simulador no dia a dia. |
| **III — Manter** | 9 a 18 | Quem mantém, integra, audita ou atualiza os dados do sistema. |

Se aparecer uma sigla desconhecida (VAAF, VAAT, NSE, DREC…), a **seção 2** explica cada uma em linguagem do dia a dia e o **glossário** da seção 17 serve para consulta rápida.

---

## Sumário

**Parte I — Entender**

1. [Visão geral do sistema](#1-visão-geral-do-sistema)
2. [O FUNDEB em linguagem simples](#2-o-fundeb-em-linguagem-simples)

**Parte II — Usar**

3. [Instalação e execução](#3-instalação-e-execução)
4. [Login e perfis de acesso](#4-login-e-perfis-de-acesso)
5. [As telas do sistema](#5-as-telas-do-sistema)
6. [Os exercícios 2024, 2025 e 2026](#6-os-exercícios-2024-2025-e-2026)
7. [Como ler os cards de cenário](#7-como-ler-os-cards-de-cenário)
8. [Administração de usuários](#8-administração-de-usuários)

**Parte III — Manter**

9. [Arquitetura técnica](#9-arquitetura-técnica)
10. [Fontes de dados e cache](#10-fontes-de-dados-e-cache)
11. [Motor de simulação, passo a passo](#11-motor-de-simulação-passo-a-passo)
12. [Validação automática (RF-10)](#12-validação-automática-rf-10)
13. [API REST](#13-api-rest)
14. [Testes automatizados](#14-testes-automatizados)
15. [Operação e manutenção](#15-operação-e-manutenção)
16. [Solução de problemas](#16-solução-de-problemas)
17. [Glossário](#17-glossário)
18. [Referências](#18-referências)

---

# Parte I — Entender

## 1. Visão geral do sistema

### 1.1 O que é, em uma frase

O **Simulador de Fatores de Ponderação do FUNDEB v2** é um programa que roda no navegador e **reproduz as contas oficiais de distribuição do dinheiro da educação básica** no Brasil. Ele permite fazer perguntas do tipo *"e se…?"* e ver a resposta em números, tabelas e gráficos.

> **Analogia:** pense num simulador de voo. O piloto treina decolagens e pousos sem colocar um avião de verdade no ar. Aqui é igual: o gestor altera montantes, pesos e matrículas e vê o resultado **sem mexer no dinheiro real**. É um laboratório seguro para testar ideias antes de defendê-las.

O motor reproduz a lógica da **Lei nº 14.113/2020** e do pacote de cálculo original escrito em R. A seção 2 explica o que é o FUNDEB; por ora, basta saber que é o fundo que financia as escolas públicas, da creche ao ensino médio.

### 1.2 O problema que ele resolve

A distribuição do FUNDEB envolve **5.596 entes federados, 27 fundos estaduais, centenas de tipos de matrícula e vários pesos diferentes**. Fazer essa conta numa planilha é lento e arriscado — e há um agravante: por causa da equalização, **mexer em um município altera o resultado de todos os outros do mesmo estado**, em cascata.

O simulador entrega:

- **Rapidez:** o que levaria horas numa planilha roda em segundos.
- **Segurança:** nenhum cálculo manual sobre dinheiro público real.
- **Transparência:** o sistema mostra o passo a passo e ainda **confere a própria matemática** (seção 12).
- **Experimentação:** dá para testar políticas antes de propô-las ("e se valorizássemos mais a creche integral?").
- **Comparabilidade:** os rótulos e as linhas dos resultados seguem a nomenclatura das publicações oficiais do FNDE (seção 7).

### 1.3 O que dá para fazer

| Funcionalidade | O que ela faz |
|----------------|---------------|
| **Simulação principal** | Recalcula o país inteiro com os montantes de complementação federal que você escolher (VAAF, VAAT e VAAR). |
| **Ponderações** | Mostra — e, para administradores, permite alterar — o peso de cada tipo de matrícula. |
| **Simulação VAAR** | Detalha a fatia que premia resultados educacionais. |
| **Simulação municipal / estadual** | Altera as matrículas de **um** ente e mostra o efeito nele e em todos os demais do mesmo estado. |
| **Análise regional** | Organiza os resultados por UF (disponível no exercício 2024). |
| **Exercícios 2024, 2025 e 2026** | Abas separadas, cada uma com os dados oficiais do respectivo ano. |
| **Validação automática** | Confere se as contas fecham (conjunto RF-10). |
| **Gestão de usuários** | Controla quem entra (login por CPF) e o que cada perfil pode fazer. |

### 1.4 Panorama dos dados carregados

Números efetivamente carregados pelo sistema na versão atual:

| Exercício | Entes federados | Tipos de matrícula | Ponderador fiscal | Simulação |
|-----------|-----------------|--------------------|-------------------|-----------|
| **2024** | 5.595 | 41 etapas | NF (ajustável) | Habilitada |
| **2025** | 5.595 | 319 segmentos | DREC (oficial) | Habilitada |
| **2026** | 5.596 | 319 segmentos | DREC (oficial) | Habilitada |

Montantes de complementação usados como valor inicial das telas (somas das colunas oficiais das planilhas de receita):

| Exercício | VAAF | VAAT | VAAR |
|-----------|------|------|------|
| **2025** | R$ 26,68 bi | R$ 24,51 bi | R$ 5,09 bi |
| **2026** | R$ 30,12 bi | R$ 31,63 bi | R$ 7,53 bi |

### 1.5 Tecnologias

Você não precisa desta tabela para usar o sistema. Em resumo: o "cérebro" que faz as contas é **Python**, os dados vêm de **planilhas oficiais** e a tela é uma **página web comum**.

| Camada | Tecnologia | Papel |
|--------|------------|-------|
| Backend | Python 3.10+, FastAPI, Uvicorn | Recebe os pedidos e coordena o cálculo |
| Motor de cálculo | `simulador.py` | Reproduz a fórmula do FUNDEB |
| Leitura de dados (ETL) | pandas, openpyxl, odfpy, pypdf, pyreadr | Lê XLSX, ODS, PDF e arquivos R (`.rda`) |
| Autenticação | SQLite, bcrypt, JWT | Usuários e sessões |
| Frontend | HTML, Bootstrap 5, JavaScript, Plotly.js | Telas, tabelas e gráficos 2D/3D |
| Testes | pytest | Verificam automaticamente se o sistema continua correto |

> O motor é uma **reescrita em Python** do pacote R [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2): a mesma lógica traduzida para outra linguagem, mantendo os resultados.

---

## 2. O FUNDEB em linguagem simples

Esta é a seção mais importante para quem é leigo. Depois dela, todo o resto do manual fica fácil.

### 2.1 O que é o FUNDEB

**FUNDEB** é o *Fundo de Manutenção e Desenvolvimento da Educação Básica e de Valorização dos Profissionais da Educação*. É o principal mecanismo que **financia as escolas públicas** — de creches ao ensino médio — em todo o país.

> **Analogia da vaquinha:** cada estado organiza uma grande vaquinha. O governo estadual e os municípios daquele território colocam dinheiro na caixinha e, depois, esse dinheiro volta para eles conforme **quantos alunos cada um atende**. Quem atende mais alunos recebe uma fatia maior.

Existe **um fundo por estado, mais o Distrito Federal** — 27 fundos. Dentro de cada fundo, o dinheiro é repartido entre o governo estadual e seus municípios.

### 2.2 De onde vem o dinheiro

Cada fundo estadual tem duas fontes:

1. **Estados e municípios**, que destinam ao fundo cerca de **20% de determinados impostos** (ICMS, IPVA, FPM, FPE, ITR, IPI-exp, ITCMD). É automático, definido em lei.
2. **A União**, que acrescenta a **complementação federal** — até 23% do total do fundo. É justamente esta parcela que o simulador permite ajustar.

A complementação não é distribuída de qualquer jeito: ela se divide em **três fatias com objetivos diferentes**.

### 2.3 As três fatias: VAAF, VAAT e VAAR

#### VAAF — Valor Aluno Ano do Fundeb

> **Pergunta que responde:** *"Quais fundos estaduais são mais fracos por aluno? Vamos reforçá-los primeiro."*

O VAAF olha para o **valor por aluno de cada fundo estadual**, considerando apenas aquela contribuição de ~20% dos impostos. Estados mais ricos juntam mais por aluno; os mais pobres, menos. A União usa a fatia VAAF para **elevar os fundos mais pobres até um patamar comum**. É uma equalização **entre estados**.

#### VAAT — Valor Aluno Ano Total

> **Pergunta que responde:** *"Considerando todas as receitas de educação, quais entes ainda ficam abaixo do mínimo? Vamos complementá-los um a um."*

O VAAT é mais abrangente: soma **todas as receitas** que o ente tem para a educação (não só a parcela do FUNDEB) e verifica o valor total por aluno. A União complementa **cada ente individualmente** que ficar abaixo do mínimo nacional. É uma equalização **nacional, no nível de cada ente**.

#### VAAR — Valor Aluno Ano Resultado

> **Pergunta que responde:** *"Quais entes cumpriram condições de boa gestão e melhoraram a aprendizagem? Vamos premiá-los."*

O VAAR é a fatia do **mérito**. Não corrige desigualdade de arrecadação: recompensa quem atingiu metas de qualidade e equidade. Funciona como bônus por desempenho.

| Fatia | Foco | Compara | Objetivo |
|-------|------|---------|----------|
| **VAAF** | Fundos estaduais | Estados entre si | Nivelar os fundos estaduais mais pobres |
| **VAAT** | Cada ente | Todos os municípios e estados | Garantir um mínimo total por aluno |
| **VAAR** | Resultado | Desempenho educacional | Premiar quem melhora e cumpre condições |

### 2.4 Matrícula, matrícula ponderada e fatores de ponderação

Aqui está a origem do nome do sistema.

**Matrícula** é um aluno matriculado. Mas nem toda matrícula custa o mesmo: uma vaga de **creche em tempo integral** exige muito mais recursos do que uma de **ensino médio parcial**. Contar as duas como "1 aluno" seria injusto.

Por isso, cada tipo de matrícula recebe um **fator de ponderação** (um peso):

```
matrícula ponderada = número de alunos × peso do tipo de matrícula
```

**Exemplo:** creche integral com peso 1,30 e ensino médio parcial com peso 1,00.

- 100 alunos em creche integral → 100 × 1,30 = **130 matrículas ponderadas**
- 100 alunos no ensino médio parcial → 100 × 1,00 = **100 matrículas ponderadas**

Os dois têm 100 alunos "de cabeça", mas a creche pesa mais no rateio porque custa mais para funcionar. **É a matrícula ponderada — não a bruta — que entra nas fórmulas de distribuição.**

Esses pesos aparecem na tela **Ponderações** e podem ser alterados por administradores para simular políticas.

### 2.5 Os ponderadores de contexto: NSE, NF e DREC

Além do peso do *tipo* de matrícula, o cálculo aplica dois ajustes que dependem **do ente**, não da etapa de ensino:

- **NSE — Nível Socioeconômico.** Favorece entes com população em situação mais vulnerável: onde as famílias têm menos recursos, a escola pública precisa de mais apoio. Entra no **VAAF e no VAAT**.
- **NF / DREC — disponibilidade de recursos.** Ajusta pela **capacidade fiscal** do ente. No exercício **2024** chama-se **NF** e pode ser reescalonado dentro de um intervalo; a partir de **2025** foi substituído pelo ponderador oficial **DREC**, usado como valor fixo. Entra **apenas no VAAF**.

> **Por que existem?** Tratar todos os entes como iguais ignoraria que uns arrecadam muito e outros quase nada. Os ponderadores fazem o dinheiro "pesar mais" onde a necessidade é maior.

### 2.6 Equalização — a ideia dos copos d'água

**Equalização** descreve *como* a complementação da União é distribuída.

> **Analogia dos copos:** imagine vários copos com níveis diferentes de água. Cada copo é um estado (no VAAF) ou um ente (no VAAT), e o nível de água é o valor por aluno. Você tem uma jarra com quantidade **limitada** (a complementação). A regra: **encha primeiro os copos mais vazios**, subindo-os até o nível do próximo, e siga subindo todos juntos **até a jarra acabar**. Os copos já cheios não recebem nada; os mais vazios chegam a uma **linha comum**.

Na prática:

1. Ordenam-se os entes do **menor** valor por aluno para o **maior**.
2. Despeja-se a complementação nos mais pobres, elevando-os.
3. Continua até o dinheiro acabar. Quem estava acima da linha final não recebe complementação.

É exatamente o que a função `equaliza_fundo` faz ([simulador.py:93](simulador.py#L93)), detalhada na seção 11.

### 2.7 Entes inabilitados ao VAAT

Nem todo ente tem direito à complementação VAAT. O FNDE publica, a cada exercício, a **lista oficial de entes habilitados e inabilitados** — a inabilitação decorre do descumprimento de condicionalidades legais (cadastros, prestação de contas, decisões judiciais etc.).

No simulador, os inabilitados:

- **não entram no ordenamento** da equalização VAAT (ou seja, não influenciam o cálculo do VAAT-MIN);
- **recebem complementação VAAT igual a zero**;
- continuam participando normalmente do **VAAF** e do **VAAR**.

Para 2026, o sistema lê a lista oficial do arquivo `ListadosenteshabilitadoseinabilitadosaoVAAT2026...xlsm` ([dados/fundeb_dataset.py:412](dados/fundeb_dataset.py#L412)). Quando não existe lista oficial para o exercício, o sistema recorre a um critério de reserva: considera inabilitado quem não tem matrícula VAAT de referência.

### 2.8 Cenário de referência

O **cenário de referência** (chamado no código de "cenário atual") é a foto do exercício calculada com os parâmetros oficiais: pesos publicados, ponderadores sem reescalonamento e os montantes das planilhas de receita. O simulador o usa como **régua**: ao rodar uma simulação, o sistema mostra quanto o cenário hipotético ganha ou perde em relação a essa referência. Assim, nenhum número é olhado no vácuo.

---

# Parte II — Usar

## 3. Instalação e execução

> Se alguém já instalou o sistema para você e basta abrir o navegador, pule para a [seção 4](#4-login-e-perfis-de-acesso).

### 3.1 Pré-requisitos

- **Python 3.10 ou superior**.
- Windows, Linux ou macOS.
- Não é preciso internet para operar: o sistema roda localmente, em `localhost`.

### 3.2 Instalação

Comandos digitados no terminal (PowerShell, no Windows):

```powershell
cd simulador-fundeb-v2               # entra na pasta do projeto
python -m venv .venv                 # cria um ambiente isolado
.\.venv\Scripts\Activate.ps1         # ativa o ambiente (Windows)
# source .venv/bin/activate          # equivalente no Linux/macOS
pip install -r requirements.txt      # instala as dependências
```

> **O que é o "ambiente isolado" (venv)?** Uma gaveta separada com as ferramentas de *este* projeto, sem bagunçar o resto do computador.

Dependências principais: `fastapi`, `uvicorn`, `pandas`, `numpy`, `openpyxl`, `odfpy`, `pyarrow`, `pyreadr`, `pypdf`, `pydantic`, `bcrypt`, `python-jose`, `pytest`, `httpx`.

### 3.3 Ligar o servidor

```powershell
python main.py
```

Abra o navegador em **http://localhost:8000**.

Na primeira execução o sistema:

- cria o banco de usuários (`data/usuarios.db`);
- cadastra um **administrador inicial**, se não houver nenhum usuário (seção 4.2);
- carrega os dados de 2024 na inicialização e os de 2025/2026 sob demanda — **a primeira carga pode levar de 30 a 90 segundos**;
- grava caches em `data/{ano}/dataset.pkl`, deixando as próximas execuções bem mais rápidas.

### 3.4 Variáveis de ambiente

Ajustes que podem ser definidos **antes** de ligar o sistema, sem mexer no código. Todos têm valor padrão.

| Variável | O que controla | Padrão |
|----------|----------------|--------|
| `FUNDEB_SECRET_KEY` | Chave que assina o token de login | `dev-fundeb-secret-altere-em-producao` |
| `FUNDEB_ADMIN_CPF` | CPF do administrador criado no primeiro uso | `52998224725` |
| `FUNDEB_ADMIN_SENHA` | Senha desse administrador | `admin123` |
| `FUNDEB_USERS_DB` | Caminho do banco de usuários | `data/usuarios.db` |
| `FUNDEB_TOKEN_HOURS` | Validade da sessão, em horas | `12` |
| `FUNDEB_RELOAD` | Recarrega o servidor a cada alteração (só desenvolvimento) | desativado |

> **Atenção à segurança:** a chave secreta e as credenciais padrão são públicas (estão neste manual). Em qualquer uso real, defina uma `FUNDEB_SECRET_KEY` própria e **troque a senha do administrador logo após o primeiro login**.

### 3.5 Estrutura de pastas

```
simulador-fundeb-v2/
├── main.py                 # Servidor FastAPI, rotas de 2024 e páginas
├── api_simulacao.py        # Rotas e handlers dos exercícios 2025 e 2026
├── simulador.py            # Motor de cálculo do FUNDEB
├── validacao.py            # Conferências automáticas (RF-10)
├── auth/                   # Login, perfis e banco de usuários
├── dados/
│   └── fundeb_dataset.py   # ETL: lê e organiza as planilhas
├── data/                   # Dados de 2024 (.rda) + caches por exercício
├── 20252026/               # Planilhas brutas de 2025 e 2026
├── static/                 # Frontend (HTML, CSS, JS)
├── tests/                  # Testes automatizados
├── apresentacao/           # Material e capturas de tela
└── manual-do-sistema.md    # Este documento
```

> **O que é "ETL"?** *Extract, Transform, Load* — o processo de **pegar os dados das planilhas, limpá-los e organizá-los** num formato que o sistema entenda.

---

## 4. Login e perfis de acesso

### 4.1 Como entrar

1. Abra `http://localhost:8000`.
2. Sem sessão ativa, o sistema redireciona para `/login.html`.
3. Informe **CPF** (11 dígitos, com ou sem pontuação) e **senha**.
4. Se estiver correto, o servidor grava um cookie seguro (`fundeb_token`, `HttpOnly`).
5. O simulador é liberado.

> **O que é esse cookie?** É como a pulseira de um evento: depois de entrar, você não precisa mostrar documento em cada porta. A pulseira vale 12 horas (por padrão) e depois expira, exigindo novo login.

O CPF é validado pelos **dígitos verificadores** — um número inventado é recusado com erro 422 antes mesmo de consultar o banco.

### 4.2 Primeiro acesso

| Campo | Valor padrão |
|-------|--------------|
| CPF | `529.982.247-25` |
| Senha | `admin123` |

> **Importante:** troque a senha logo após o primeiro login, na tela **Usuários** (`/admin.html`).

### 4.3 Perfis: administrador e usuário comum

| Ação | Administrador | Usuário comum |
|------|:-------------:|:-------------:|
| Ver o simulador e todas as abas | Sim | Sim |
| Rodar simulações (VAAF/VAAT/VAAR/municipal) | Sim | Sim |
| **Editar** os pesos de ponderação | Sim | Não (somente leitura) |
| Enviar pesos personalizados pela API | Sim | Não (usa os oficiais) |
| Cadastrar, editar e excluir usuários | Sim | Não |
| Ver o menu **Usuários** | Sim | Menu oculto |

> **A restrição é real, não cosmética:** a recusa de pesos personalizados acontece **no servidor**, na função `preparar_pesos` ([api_simulacao.py:74](api_simulacao.py#L74)). Mesmo que alguém manipule a página no navegador ou chame a API diretamente, o servidor descarta os pesos e usa os oficiais.

### 4.4 Sair

Clique em **Sair**, no rodapé do menu lateral. O cookie é apagado e a sessão encerrada.

---

## 5. As telas do sistema

### 5.1 Menu lateral

```
┌─────────────────────────────────────┐
│  FUNDEB — Simulador v2              │
│  [nome do usuário / perfil]         │
├─────────────────────────────────────┤
│  Página Principal                   │
├─ FUNDEB 2024 ───────────────────────┤
│  Simulação Principal                │
│  Ponderações                        │
│  Simulação VAAR                     │
│  Simulação Municipal                │
│  Análise Regional                   │
├─ FUNDEB 2026 ───────────────────────┤
│  Simulação 2026                     │
│  Ponderações 2026                   │
│  VAAR 2026                          │
│  Município 2026                     │
├─ FUNDEB 2025 ───────────────────────┤
│  Simulação 2025                     │
│  Ponderações 2025                   │
│  VAAR 2025                          │
│  Município 2025                     │
├─────────────────────────────────────┤
│  Documentação                       │
│  Usuários (somente admin)           │
├─────────────────────────────────────┤
│  Sair                               │
└─────────────────────────────────────┘
```

As abas de 2025 e 2026 são geradas dinamicamente por `static/js/app_multi_ano.js`. O rótulo da aba de simulação de cada ano muda conforme a resposta de `GET /api/{ano}/meta`: fica **"Simulação {ano}"** quando os dados estão completos e **"Consulta {ano}"** quando falta algum arquivo oficial. Em celulares e tablets, o menu recolhe e abre pelo botão de três linhas.

### 5.2 Página Principal

Tela de boas-vindas. Explica a composição do fundo, o que são VAAF/VAAT/VAAR, a evolução da complementação federal e como as matrículas são contadas. **Não faz cálculos** — é uma versão resumida da seção 2 deste manual.

### 5.3 Simulação Principal

A tela mais usada, dividida em dois lados.

**Parâmetros (lado esquerdo):**

| Campo | O que você define |
|-------|-------------------|
| Montante VAAF (R$) | Quanto a União destina à equalização **entre fundos estaduais** |
| Montante VAAT (R$) | Quanto vai à equalização **nacional**, ente a ente |
| Montante VAAR (R$) | Quanto vai ao prêmio **por resultado** |
| NF máximo / mínimo | *(apenas 2024)* Intervalo de reescalonamento do NF no VAAF |

Nos exercícios 2025 e 2026 não há controle de NF: o DREC é oficial e fixo.

**Resultados (lado direito), após clicar em Simular:**

- **Caixas-resumo** com VAAF-MIN e VAAT-MIN simulados versus o cenário de referência, complementação destinada a municípios e a estados, e percentual de entes complementados;
- **Selo da validação automática** (RF-10): "OK" ou "Falhou";
- **Gráficos 2D** (Plotly): VAAF e VAAT médios por UF, diferença de complementação por UF, complementação por modalidade e por categoria administrativa;
- **Tabelas** de resultados positivos e negativos por região, em relação ao cenário de referência;
- **Gráficos 3D** cruzando VAAF, VAAT e complementação.

### 5.4 Ponderações

Lista todos os tipos de matrícula agrupados por **família** (Creche, Pré-escola, Ensino Fundamental etc.) em formato de acordeão. Cada segmento tem dois campos: **peso VAAF** e **peso VAAT**.

| Perfil | O que vê |
|--------|----------|
| Administrador | Campos editáveis; a alteração passa a valer nas próximas simulações da sessão |
| Usuário comum | Campos bloqueados, com aviso de somente leitura |

### 5.5 Simulação VAAR

Detalha a fatia de mérito: distribuição por UF, participação do VAAR no total da complementação de cada estado e tabela dos 50 entes com maior valor. Usa a rota `POST /api/simular/completo` (ou a equivalente do exercício).

### 5.6 Simulação Municipal e de entes estaduais

É a funcionalidade que melhor demonstra o efeito dominó do FUNDEB.

> **Pergunta que responde:** *"Se eu mudar as matrículas deste município (ou governo estadual), o que acontece com ele e com todos os outros entes do mesmo estado?"*

**Passo a passo:**

1. Escolha a **UF** (a lista vem agrupada por região).
2. Escolha o **ente**: o governo estadual aparece primeiro (ex.: *Acre (12)*), depois os municípios em ordem alfabética.
3. Veja e edite as **matrículas por segmento** no acordeão. Nas abas 2025/2026, o botão **"Mostrar segmentos sem matrícula"** exibe ou oculta os segmentos zerados.
4. Se quiser, ajuste os **montantes** VAAF/VAAT/VAAR.
5. Clique em **Simular**.

**Como identificar estados e municípios pelo código IBGE:**

| Código IBGE | Tipo | Exemplo |
|-------------|------|---------|
| Menor que 100 (2 dígitos) | Governo estadual | `12` = Acre |
| 7 dígitos | Município | `1200054` = Assis Brasil/AC |

Os 27 governos estaduais estão disponíveis em 2024, 2025 e 2026, com o nome padronizado (ex.: "Acre", e não "GOVERNO DO ESTADO DO ACRE").

**Por que o sistema recalcula tudo:** alterar as matrículas de um ente muda a participação dele no fundo estadual, o que altera o rateio para todos os demais. Para medir esse efeito, o sistema roda a simulação **duas vezes** — original e ajustada — e compara.

**O que aparece nos resultados:**

| Painel | Conteúdo |
|--------|----------|
| **Cards** | Cenário original e cenário ajustado, linha a linha (detalhados na seção 7) |
| **Explicação textual** | Narrativa em português do cálculo, gerada por `static/js/explicacao.js` |
| **Tabela de impacto** | Efeito da mudança sobre os demais entes do mesmo estado |
| **Gráficos** | Comparativos 2D e 3D |

### 5.7 Análise Regional (2024)

Organiza os resultados por UF: VAAF e VAAT médios, complementação total e por modalidade, recursos do FUNDEB no estado. Ao abrir o app, uma simulação com os parâmetros padrão já é executada, então há dados prontos para explorar.

> A Análise Regional ainda não foi implementada para 2025 e 2026.

### 5.8 Documentação (aba interna)

Texto de apoio dentro do próprio app, com links para portarias e para o portal do FNDE. Complementa este manual.

---

## 6. Os exercícios 2024, 2025 e 2026

O sistema trabalha com três anos, cada um em suas próprias abas, porque as regras e as fontes oficiais mudaram ao longo do tempo.

### 6.1 O que muda de um ano para o outro

| Aspecto | 2024 | 2025 | 2026 |
|---------|------|------|------|
| Tipos de matrícula | 41 etapas | 319 segmentos | 319 segmentos |
| Ponderador fiscal no VAAF | NF (reescalonável) | DREC (oficial, fixo) | DREC (oficial, fixo) |
| Ponderador social (NSE) | Sim | Sim | Sim |
| Fonte dos dados | Arquivos `.rda` + PDF | Planilhas FNDE/STN | Planilhas FNDE |
| Lista oficial de inabilitados ao VAAT | Do arquivo legado | Critério de reserva | Lista oficial FNDE |
| Montantes padrão | Legado | Soma da planilha de receita | Soma da planilha de receita |
| Prefixo da API | `/api/...` | `/api/2025/...` | `/api/2026/...` |

> **Por que 41 etapas em 2024 e 319 segmentos depois?** Porque a classificação ficou mais detalhada: categorias amplas passaram a ser subdivididas por rede, localização, tempo integral/parcial e modalidade. Mais segmentos significam mais precisão no rateio.

### 6.2 As fórmulas de cada ano

A diferença é apenas **qual ponderador fiscal** entra no VAAF:

**2024 (NF reescalonado):**
```
matriculas_vaaf = (matrículas × pesos_vaaf) × NSE × NF
matriculas_vaat = (matrículas × pesos_vaat) × NSE
```

**2025 e 2026 (DREC):**
```
matriculas_vaaf = (matrículas × pesos_vaaf) × NSE × DREC
matriculas_vaat = (matrículas × pesos_vaat) × NSE
```

Em português: a matrícula ponderada do VAAF é o número de alunos multiplicado pelos pesos e ajustado pelo nível socioeconômico e pela disponibilidade de recursos. O VAAT é igual, **sem** o ponderador fiscal.

### 6.3 Habilitação condicional da simulação

Cada exercício só habilita a simulação se **todos** os arquivos auxiliares estiverem disponíveis — receita, NSE, DREC e memória de cálculo do VAAT. A verificação está em `dados_auxiliares_completos` ([dados/fundeb_dataset.py](dados/fundeb_dataset.py)) e o estado é publicado em `GET /api/{ano}/meta`.

- **Dados completos:** aba habilitada, rótulo "Simulação {ano}".
- **Falta algum arquivo:** aba em modo consulta (matrículas e pesos), rótulo "Consulta {ano}", banner de aviso e erro **HTTP 503** em qualquer tentativa de simular.

Atualmente **2025 e 2026 estão habilitados**. O documento `checklist-dados-2025.md` descreve como obter e nomear cada arquivo caso seja necessário refazer a carga.

---

## 7. Como ler os cards de cenário

Na simulação municipal/estadual, dois cards mostram o mesmo conjunto de linhas: **Cenário original** (com as matrículas oficiais) e **Cenário ajustado** (com as suas alterações). Os rótulos seguem a nomenclatura das publicações oficiais do FNDE, para facilitar a conferência lado a lado.

| Linha do card | O que representa | Origem do número |
|---------------|------------------|------------------|
| **Matrículas VAAF** | Matrículas informadas, **sem nenhuma ponderação** | Soma de todos os segmentos do ente |
| **Matrículas ponderadas VAAF** | Matrículas após pesos, NSE e DREC/NF | `matriculas_vaaf` |
| **Matrículas ponderadas VAAT** | Matrículas após pesos VAAT e NSE | `matriculas_vaat` |
| **Matrículas ponderadas VAAF do Fundo** | Total ponderado de **todo o fundo estadual** | Soma da UF |
| **Receitas VAAF Fundo [UF]** | Receita da contribuição de todo o fundo estadual | Soma da UF |
| **Complemento VAAF Fundo [UF]** | Complementação VAAF recebida pelo fundo estadual inteiro | Soma da UF |
| **Receita da contribuição de estados e municípios ao Fundeb** | A parcela de impostos que **este ente** aporta ao fundo | `recursos_vaaf` |
| **Receitas VAAT** | Todas as receitas de educação do ente, base do VAAT | `recursos_vaat` |
| **VAAF-MIN** | Menor VAAF final do país após a equalização | Mínimo nacional |
| **VAAT-MIN** | Menor VAAT final entre os entes **habilitados** | Mínimo nacional (exclui inabilitados) |
| **VAAF (antes da complementação)** | Valor por aluno só com a contribuição do fundo | `recursos_vaaf / matriculas_vaaf` |
| **VAAT (antes da complementação)** | Valor por aluno com todas as receitas, antes da União | `vaat_pre` |
| **Coeficiente (matrículas ente / fundo)** | Participação do ente no fundo estadual, com **8 casas decimais** | `matriculas_vaaf` do ente ÷ do fundo |
| **VAAF Final** | Valor por aluno após a equalização VAAF | `vaaf_final` |
| **VAAT Final** | Valor por aluno após a equalização VAAT | `vaat_final` |
| **Complemento VAAF** | Quanto o ente recebeu da União pela fatia VAAF | `complemento_vaaf` |
| **Complemento VAAT** | Quanto recebeu pela fatia VAAT (zero, se inabilitado) | `complemento_vaat` |
| **Complemento VAAR** | Quanto recebeu pela fatia de resultado | `complemento_vaar` |
| **Total Complementação** | Soma das três fatias | `complemento_uniao` |
| **Receita Total do Fundeb** | Contribuição própria + toda a complementação da União | `recursos_fundeb` |

> **Por que o coeficiente tem 8 casas decimais?** Porque a participação de um município pequeno em um fundo estadual grande é um número muito pequeno. Com poucas casas, valores distintos apareceriam arredondados de forma idêntica e a comparação com as planilhas oficiais ficaria impossível.

As linhas do fundo estadual (matrículas ponderadas, receitas e complemento) permitem verificar o **contexto** em que o ente está inserido: um mesmo município pode ganhar ou perder conforme o comportamento do fundo do seu estado.

---

## 8. Administração de usuários

A tela `/admin.html` só aparece e só funciona para administradores.

### 8.1 Cadastrar um usuário

| Campo | Regra |
|-------|-------|
| CPF | 11 dígitos e **CPF válido** (dígitos verificadores conferidos) |
| Nome | Opcional |
| Senha | Mínimo de 6 caracteres |
| Perfil | `usuario` (padrão) ou `admin` |

### 8.2 Gerenciar usuários existentes

| Ação | O que faz |
|------|-----------|
| Editar | Altera nome, perfil, status (ativo/inativo) e, se quiser, a senha |
| Redefinir senha | Atalho para definir uma nova senha |
| Ativar / desativar | Bloqueia ou libera o acesso sem excluir o cadastro |
| Excluir | Remove o usuário definitivamente |

**Travas de segurança aplicadas pelo servidor:**

- não é possível **desativar ou excluir a si mesmo** (evita ficar trancado para fora);
- não é possível **remover, rebaixar ou desativar o último administrador ativo**;
- usuário **inativo** recebe **HTTP 403** ao tentar entrar;
- senhas são gravadas apenas como hash bcrypt — nem o administrador consegue lê-las, só redefini-las.

---

# Parte III — Manter

## 9. Arquitetura técnica

> Daqui em diante o conteúdo é técnico. Quem apenas usa o sistema pode parar na seção 8.

```
┌──────────────┐     cookie JWT      ┌─────────────────────────────────┐
│   Browser    │ ◄──────────────────►│  FastAPI (main.py)              │
│  index.html  │   /api/* JSON       │  ├── auth/routes.py             │
│  app.js      │                     │  ├── api_simulacao.py (2025/26) │
│  auth.js     │                     │  └── rotas 2024 em main.py      │
└──────────────┘                     └──────────────┬──────────────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────┐
                    ▼                               ▼                       ▼
            ┌───────────────┐              ┌──────────────┐        ┌─────────────┐
            │ simulador.py  │              │ fundeb_      │        │ usuarios.db │
            │ (motor)       │◄─────────────│ dataset.py   │        │ (SQLite)    │
            └───────────────┘              │ (ETL/cache)  │        └─────────────┘
                    ▲                      └──────────────┘
                    │
            ┌───────────────┐
            │ validacao.py  │
            └───────────────┘
```

Em palavras: o navegador envia um pedido; o FastAPI valida o cookie JWT, obtém os dados já preparados pelo ETL, aciona o motor de cálculo, roda as conferências e devolve JSON para a tela desenhar tabelas e gráficos.

### 9.1 Arquivos principais

| Arquivo | Responsabilidade |
|---------|------------------|
| `main.py` | Sobe o FastAPI, carrega 2024, registra as rotas de 2024 e serve as páginas |
| `api_simulacao.py` | Handlers compartilhados e rotas dos exercícios 2025/2026 |
| `simulador.py` | Motor: `simula_fundeb` e as funções de equalização |
| `dados/fundeb_dataset.py` | ETL: lê XLSX/ODS/PDF/RDA, monta os datasets e gerencia o cache |
| `validacao.py` | Conferências RF-10 e comparação com dados oficiais (CA-05) |
| `auth/` | JWT, bcrypt, banco de usuários e dependências de permissão |
| `static/js/app.js` | Telas do exercício 2024 |
| `static/js/app_multi_ano.js` | Telas dos exercícios 2025 e 2026 |
| `static/js/auth.js` | Sessão, `apiFetch` e redirecionamento em 401 |
| `static/js/explicacao.js` | Narrativa textual da simulação municipal |
| `static/js/charts3d.js` | Gráficos 3D |

### 9.2 O caminho de uma simulação

1. A tela envia `POST /api/simular` (ou `/api/{ano}/simular`) com os parâmetros em JSON.
2. `get_current_user` valida o cookie JWT e confirma que o usuário está ativo.
3. `_checar_simulacao` verifica se o exercício está habilitado (senão, HTTP 503).
4. `preparar_pesos` decide entre pesos oficiais e personalizados, conforme o perfil.
5. `executar_simulacao` chama `simula_fundeb`.
6. `validar_interno` roda as conferências RF-10.
7. `gerar_resumo`, `gerar_dados_por_uf` e `gerar_vencedores_perdedores` montam os agregados.
8. `sanitize_for_json` troca `NaN`/`inf` por `null` e a resposta volta em JSON.
9. O Plotly desenha os gráficos e as tabelas.

---

## 10. Fontes de dados e cache

Os números do simulador vêm de arquivos oficiais. Esta seção diz de onde sai cada coisa.

### 10.1 Exercício 2024 (pasta `data/`)

| Arquivo | Conteúdo |
|---------|----------|
| `pesos.rda` | Pesos VAAF/VAAT das 41 etapas |
| `matriculas.rda` | Matrículas por etapa e por ente |
| `complementar.rda` | Receitas, NF, peso VAAR e flag de inabilitados ao VAAT |
| `cenario_atual*.rda` | Cenário oficial de referência (por ente, agregado e por UF) |
| `PonderadorNSE 2024.pdf` | NSE por código IBGE, extraído do PDF oficial |

> **Observação para quem for mexer no código:** a pasta contém também `dados_unificados.xlsx`, e o `main.py` mantém funções auxiliares para lê-lo (`carregar_matriculas_da_planilha`, `carregar_campos_tecnicos_xlsx`). Elas são **remanescentes de uma versão anterior e não são chamadas**: o dataset de 2024 em uso é montado inteiramente a partir dos arquivos `.rda` e do PDF de NSE, em `carregar_dataset_2024` ([dados/fundeb_dataset.py](dados/fundeb_dataset.py)).

### 10.2 Exercícios 2025 e 2026 (pasta `20252026/`)

O mapa de arquivos por exercício está em `RAW_ARQUIVOS` ([dados/fundeb_dataset.py:37](dados/fundeb_dataset.py#L37)).

| Arquivo | Exercício | Uso |
|---------|-----------|-----|
| `Matrículas Fundeb 2026.xlsx` | 2026 | Matrículas (aba `Detalhadas`) e pesos (aba `FPs`) |
| `Matrículas Fundeb 2025 e 2026.xlsx` | 2025 | Matrículas filtradas por `ANO = 2025` e pesos |
| `1-receita-total-do-fundeb-por-ente-federado.xlsx` | 2026 | Receita da contribuição, complementações oficiais e peso VAAR |
| `1-receita-total-do-fundeb-por-ente-federado-2025.xlsx` | 2025 | Idem, para 2025 |
| `ponderador-de-nivel-socioeconomico.xlsx` | 2026 | NSE |
| `PonderadorNSEFundeb2025.pdf` | 2025 | NSE (o FNDE não publicou XLSX para 2025) |
| `ponderador-de-disponibilidade-de-recursos.xlsx` | 2026 | DREC |
| `PonderadorDRecFundeb2025.pdf` | 2025 | DREC |
| `MemriadeClculoVAAT2026 (2).xlsx` | 2026 | Memória de cálculo do VAAT |
| `Receita STN 2023 VAAT 2025 para publicação.xlsx` | 2025 | Memória de cálculo do VAAT (aba `COM CORREÇÃO`) |
| `ListadosenteshabilitadoseinabilitadosaoVAAT2026...xlsm` | 2026 | Lista oficial de inabilitados ao VAAT |
| `Receitas Fundos 2026.ods` | 2026 | Anexo STN usado no teste de regressão por UF |

**Três decisões do ETL que vale conhecer:**

1. **Receita do fundo:** o VAAF usa a coluna `recursos_contribuicao` da planilha de receita (Anexo I/Portaria). A coluna equivalente da memória de cálculo do VAAT é base VAAT e **não** substitui a contribuição oficial.
2. **Peso VAAR:** é derivado da participação de cada ente na complementação VAAR oficial da planilha de receita.
3. **Montantes padrão:** são a **soma das colunas oficiais** da planilha de receita do exercício. As constantes `COMPLEMENTACAO_2025` e `COMPLEMENTACAO_2026` no código funcionam apenas como reserva, caso a soma resulte em zero.

> **Ponto de atenção:** as constantes de reserva de 2026 estão exatamente no dobro dos valores somados da planilha (R$ 60,25 bi contra R$ 30,12 bi de VAAF, por exemplo). Como o sistema usa a soma da planilha, isso não afeta os resultados hoje, mas as constantes devem ser revistas na próxima atualização de portaria para não induzirem a erro se algum dia forem acionadas.

### 10.3 Cache do ETL

Depois da primeira carga, o resultado já preparado é gravado em disco para evitar reler as planilhas:

- `data/2025/dataset.pkl`
- `data/2026/dataset.pkl`

O arquivo guarda a constante `DATASET_CACHE_VERSION` (hoje **8**). Se a versão gravada não bate com a do código, o cache é descartado e os dados são relidos. **Sempre que alterar o ETL ou trocar uma planilha, incremente essa constante ou apague os `.pkl`** — caso contrário, o sistema continuará exibindo os dados antigos.

### 10.4 Banco de usuários

- Arquivo: `data/usuarios.db` (SQLite).
- Tabela `users`: CPF (chave primária), hash da senha, perfil (`admin`/`usuario`), nome, status ativo e data de criação.

---

## 11. Motor de simulação, passo a passo

Tudo acontece em `simula_fundeb` ([simulador.py:175](simulador.py#L175)).

### Etapa 0 — Separar os inabilitados ao VAAT

A lista de entes inabilitados é extraída da tabela complementar e reservada para uso na etapa 7.

### Etapa 1 — Matrículas ponderadas por etapa

```
matriculas_vaaf = Σ (matrículas da etapa × peso VAAF da etapa)
matriculas_vaat = Σ (matrículas da etapa × peso VAAT da etapa)
```

O símbolo `Σ` significa "some tudo". Tecnicamente é uma multiplicação de matrizes: matriz de matrículas × vetor de pesos.

### Etapa 2 — Ponderadores de contexto

Aplica **NSE** (VAAF e VAAT) e **NF ou DREC** (só VAAF). No modo NF, o vetor é reescalonado antes, dentro do intervalo informado pelo usuário.

### Etapa 3 — Agregação por fundo estadual

```
vaaf_estado_inicial = recursos do estado (VAAF) / matrículas ponderadas do estado (VAAF)
```

É o "nível de água" inicial de cada copo.

### Etapa 4 — Equalização do VAAF entre estados

`equaliza_fundo` ordena os fundos do menor valor por aluno para o maior, calcula quanto seria preciso para elevar cada nível acumulado e distribui a complementação VAAF até esgotá-la. Fundos já acima da linha final mantêm seus recursos originais.

### Etapa 5 — Redistribuição dentro de cada estado

```
recursos_vaaf_final = matriculas_vaaf × (recursos do estado após equalização / matrículas do estado)
vaaf_final          = recursos_vaaf_final / matriculas_vaaf
```

O total do fundo é repartido entre seus entes na proporção das matrículas ponderadas.

### Etapa 6 — VAAT antes da complementação

```
vaat_pre = recursos_vaat / matriculas_vaat
```

### Etapa 7 — Equalização do VAAT em nível nacional

Mesmo algoritmo, agora **ente a ente** (chave `ibge`) e em âmbito nacional, **excluindo os inabilitados**: eles ficam fora do ordenamento e mantêm os recursos originais, sem complementação VAAT.

### Etapa 8 — VAAR

```
complemento_vaar = peso_vaar × complementacao_vaar
```

### Etapa 9 — Totais finais

```
complemento_vaaf  = recursos_vaaf_final - recursos_vaaf
complemento_vaat  = recursos_vaat_final - recursos_vaat
complemento_uniao = complemento_vaaf + complemento_vaat + complemento_vaar
recursos_fundeb   = recursos_vaaf + complemento_uniao
```

Em português: o complemento de cada modalidade é o quanto o ente ganhou graças à União; a complementação total é a soma das três fatias; e a receita total do FUNDEB é a contribuição própria mais tudo o que a União acrescentou.

---

## 12. Validação automática (RF-10)

Depois de cada simulação, `validar_interno` ([validacao.py:23](validacao.py#L23)) refaz as contas por outro caminho — como conferir o troco.

| # | Verificação | Erro que detecta |
|---|-------------|------------------|
| 1 | Soma de `recursos_vaaf` por UF = total do fundo estadual | Falha ao juntar ou agrupar dados |
| 2 | `vaaf_final` = `recursos_vaaf_final / matriculas_vaaf` | Fórmula inconsistente |
| 3 | Participações VAAF dentro do estado somam 100% | Erro no rateio interno |
| 4 | `recursos_fundeb` = `recursos_vaaf + complemento_uniao` | Erro nas colunas finais |

Resposta da API:

```json
"validacao": {
  "valido": true,
  "erros": [],
  "avisos": [],
  "checagens": ["UF SP: soma recursos = total estadual OK", "..."]
}
```

Se `valido` for `false`, os resultados continuam sendo exibidos, mas com alerta visível para que os números sejam investigados antes de qualquer uso.

Há ainda `comparar_com_oficial` ([validacao.py:79](validacao.py#L79)), que calcula as diferenças médias e máximas entre a simulação e uma tabela oficial. É usado em auditorias pontuais, fora do fluxo automático das telas.

---

## 13. API REST

> Seção voltada a desenvolvedores que queiram integrar o simulador a outros sistemas.

Todas as rotas `/api/*` — exceto o login — exigem o cookie `fundeb_token`.

### 13.1 Autenticação

| Método | Rota | Função |
|--------|------|--------|
| POST | `/api/auth/login` | Recebe `{cpf, senha}` e grava o cookie |
| POST | `/api/auth/logout` | Apaga o cookie |
| GET | `/api/auth/me` | Retorna `{cpf, cpf_formatado, role, nome}` |

### 13.2 Administração (somente admin)

| Método | Rota | Função |
|--------|------|--------|
| GET | `/api/admin/usuarios` | Lista os usuários |
| POST | `/api/admin/usuarios` | Cria um usuário |
| PATCH | `/api/admin/usuarios/{cpf}` | Atualiza nome, perfil, status ou senha |
| DELETE | `/api/admin/usuarios/{cpf}` | Remove um usuário |

### 13.3 Exercício 2024

| Método | Rota | Função |
|--------|------|--------|
| GET | `/api/estados` | UFs e regiões |
| GET | `/api/municipios?uf=XX` | Entes da UF (estado primeiro, depois municípios) |
| GET | `/api/pesos` | Pesos por etapa, com a família |
| GET | `/api/etapas` | Nomes amigáveis das etapas |
| GET | `/api/municipio/{ibge}/matriculas` | Matrículas e dados do ente |
| GET | `/api/cenario-atual/resumo` | Cenário de referência |
| POST | `/api/simular` | Simulação agregada (resumo, gráficos, validação) |
| POST | `/api/simular/completo` | Uma linha por ente |
| POST | `/api/simular/municipio` | Comparativo original × ajustado |

### 13.4 Exercícios 2025 e 2026

Mesma estrutura, com o ano no caminho:

| Método | Rota | Função |
|--------|------|--------|
| GET | `/api/{ano}/meta` | Estado do exercício, montantes padrão, ponderador, nº de etapas e famílias |
| GET | `/api/{ano}/estados` | UFs e regiões |
| GET | `/api/{ano}/municipios?uf=XX` | Entes da UF |
| GET | `/api/{ano}/pesos` | Pesos por segmento |
| GET | `/api/{ano}/etapas` | `{etapas, familias}` |
| GET | `/api/{ano}/municipio/{ibge}/matriculas` | Matrículas do ente |
| GET | `/api/{ano}/cenario-atual/resumo` | Cenário de referência |
| POST | `/api/{ano}/simular` | Simulação agregada |
| POST | `/api/{ano}/simular/completo` | Dados completos por ente |
| POST | `/api/{ano}/simular/municipio` | Simulação municipal |

> **Diferença sutil:** `GET /api/etapas` (2024) devolve um dicionário simples `{etapa: nome}`, enquanto `GET /api/{ano}/etapas` devolve `{etapas, familias}`.

### 13.5 Corpo das requisições

Simulação:

```json
{
  "complementacao_vaaf": 30124926956.49,
  "complementacao_vaat": 31631173304.31,
  "complementacao_vaar": 7531231739.12,
  "max_nse": 1.1,
  "min_nse": 1.0,
  "max_nf": 1.0,
  "min_nf": 1.0,
  "pesos_vaaf": [1.0, 1.2],
  "pesos_vaat": [1.0, 1.1]
}
```

Simulação municipal (acrescenta o ente e as matrículas alteradas):

```json
{
  "ibge": 1200054,
  "matriculas_ajustadas": {
    "creche_integral_rede_publica": 500,
    "pre_escola_parcial_rede_publica": 1200
  }
}
```

> `pesos_vaaf` e `pesos_vaat` só têm efeito para administradores, e apenas se o tamanho da lista coincidir com o número de etapas do exercício. Para usuários comuns, são ignorados.

### 13.6 Códigos de erro

| Código | Quando ocorre |
|--------|---------------|
| 401 | Sem cookie, sessão expirada ou usuário inativo |
| 403 | Rota de administrador acessada por usuário comum; login de usuário inativo |
| 404 | Ente não encontrado no exercício |
| 409 | CPF já cadastrado |
| 422 | Corpo inválido (por exemplo, CPF sem dígitos verificadores válidos) |
| 503 | Exercício sem dados completos para simular |

### 13.7 Exemplo com `curl`

```powershell
# 1) Login, salvando o cookie
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"cpf":"52998224725","senha":"admin123"}'

# 2) Simular 2026 usando o cookie
curl -b cookies.txt -X POST http://localhost:8000/api/2026/simular `
  -H "Content-Type: application/json" `
  -d '{"complementacao_vaaf":30124926956.49,"complementacao_vaat":31631173304.31}'
```

---

## 14. Testes automatizados

```powershell
python -m pytest tests/ -v
```

| Arquivo | O que verifica |
|---------|----------------|
| `tests/test_requisitos.py` | Rateio proporcional (CA-02), redistribuição em cascata (RN-03) e validação interna (RF-10), com dados sintéticos |
| `tests/test_dataset_2025.py` | Carga do exercício 2025, mapeamento de arquivos e coerência entre modo consulta e modo simulação |
| `tests/test_dataset_2026.py` | Carga do exercício 2026, consistência do VAAF e conferência das receitas por UF contra o Anexo STN (`Receitas Fundos 2026.ods`) |
| `tests/test_auth.py` | Login, CPF inválido, usuário inativo, restrição de rotas de admin e bloqueio de pesos personalizados |

O arquivo `test_app.py`, na raiz, é um conjunto legado de verificações do exercício 2024 e não faz parte da suíte principal.

> **Por que isso importa mesmo para quem não programa?** Porque, sempre que alguém altera o sistema, esses testes avisam na hora se algum cálculo saiu do lugar — funcionam como alarme de fumaça para o código.

---

## 15. Operação e manutenção

### 15.1 Atualizar uma planilha de matrículas

1. Substitua o arquivo em `20252026/` mantendo exatamente o nome esperado em `RAW_ARQUIVOS`.
2. Incremente `DATASET_CACHE_VERSION` em `dados/fundeb_dataset.py` **ou** apague o `data/{ano}/dataset.pkl` correspondente.
3. Reinicie o servidor.
4. Rode `python -m pytest tests/test_dataset_2026.py -v` (ou o teste do ano alterado).

### 15.2 Atualizar a lista de inabilitados ao VAAT

1. Substitua o `.xlsm` da lista oficial em `20252026/`, mantendo o nome mapeado em `RAW_ARQUIVOS` (ou ajustando o mapeamento).
2. Invalide o cache, como no item anterior.
3. Reinicie e confira o total de inabilitados; a leitura considera inabilitado todo ente cuja coluna de verificação **não** contenha "Habilitado".

### 15.3 Atualizar os montantes de complementação

Os valores iniciais das telas vêm da soma das colunas oficiais da planilha de receita. Para adotar outra portaria, basta substituir a planilha de receita e invalidar o cache — não é preciso editar código. As constantes `COMPLEMENTACAO_2025`/`COMPLEMENTACAO_2026` só entram em cena se a soma resultar em zero.

### 15.4 Colocar em produção

- Defina uma `FUNDEB_SECRET_KEY` própria e forte.
- Troque a senha do administrador inicial e, se possível, defina `FUNDEB_ADMIN_CPF`/`FUNDEB_ADMIN_SENHA` antes da primeira execução.
- Sirva o sistema atrás de HTTPS: o cookie é `HttpOnly` e `SameSite=Lax`, mas trafega sem criptografia se o transporte não for seguro.
- Restrinja `allow_origins` do CORS em `main.py`, hoje aberto para qualquer origem.
- Faça backup periódico de `data/usuarios.db`.

---

## 16. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---------|----------------|-------------|
| O sistema volta sozinho para a tela de login | Sessão expirada ou cookie removido | Faça login novamente; para sessões mais longas, ajuste `FUNDEB_TOKEN_HOURS` |
| Erro HTTP 503 ao simular | Exercício sem todos os arquivos oficiais | Confira `GET /api/{ano}/meta` e o `checklist-dados-2025.md` |
| Primeira carga muito lenta | O ETL está lendo planilhas grandes e PDFs | Aguarde; as execuções seguintes usam o cache `.pkl` |
| Alterei uma planilha e nada mudou | O cache antigo continua válido | Incremente `DATASET_CACHE_VERSION` ou apague `data/{ano}/dataset.pkl` |
| Ente estadual não aparece na lista | Página em cache no navegador | Ctrl+F5; se persistir, invalide o cache do dataset |
| Validação RF-10 falhou | Parâmetros extremos ou dados inconsistentes | Leia `validacao.erros` na resposta da simulação |
| `ModuleNotFoundError` na inicialização | Dependências não instaladas ou venv inativo | Ative o venv e rode `pip install -r requirements.txt` |
| Administrador não consegue editar pesos | Perfil não é admin | Confira se `role` é `admin` em `GET /api/auth/me` |
| Erro 422 ao criar usuário | CPF sem dígitos verificadores válidos ou senha curta | Use CPF válido e senha com pelo menos 6 caracteres |

---

## 17. Glossário

| Termo | Significado |
|-------|-------------|
| **FUNDEB** | Fundo que financia a educação básica pública no Brasil |
| **Ente** | Município ou governo estadual que participa do fundo |
| **IBGE** | Código que identifica cada ente (`12` = AC; `1200054` = Assis Brasil/AC) |
| **VAAF** | Valor Aluno Ano do Fundeb — equaliza entre os fundos estaduais |
| **VAAT** | Valor Aluno Ano Total — equaliza entre todos os entes, considerando todas as receitas |
| **VAAR** | Valor Aluno Ano Resultado — prêmio por desempenho educacional |
| **VAAF-MIN / VAAT-MIN** | Menor valor por aluno alcançado após a equalização |
| **NSE** | Ponderador de nível socioeconômico |
| **NF** | Ponderador de disponibilidade de recursos usado em 2024 |
| **DREC** | Disponibilidade de Recursos — substitui o NF no VAAF a partir de 2025 |
| **FP** | Fator de ponderação: o peso de cada tipo de matrícula |
| **Segmento / etapa** | Categoria de matrícula (ex.: creche integral urbana) |
| **Família** | Agrupamento de segmentos usado na interface |
| **Matrícula ponderada** | Matrícula × peso × NSE × (NF/DREC, no VAAF) |
| **Coeficiente** | Participação do ente no total de matrículas ponderadas do fundo estadual |
| **Equalização** | Algoritmo que distribui a complementação começando pelos mais pobres |
| **Inabilitado ao VAAT** | Ente que, por regra, fica fora da complementação VAAT |
| **Cenário de referência** | Resultado calculado com os parâmetros oficiais, usado para comparação |
| **RF-10** | Conjunto de conferências automáticas da matemática da simulação |
| **ETL** | Processo de ler, limpar e organizar os dados das planilhas |
| **JWT / cookie** | Credencial que comprova o login durante a sessão |

---

## 18. Referências

### Legislação

- [Lei nº 14.113/2020](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/L14113.htm) — marco legal do FUNDEB

### Dados oficiais

- [FNDE — FUNDEB](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb)
- [Matrículas da educação básica](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/matriculas-da-educacao-basica)
- [FUNDEB 2025](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2025)
- Portarias interministeriais MEC/MF com os montantes da complementação de cada exercício

### Documentação complementar no repositório

| Arquivo | Conteúdo |
|---------|----------|
| `README.md` | Visão geral e início rápido |
| `documentacao2.md` | Guia didático detalhado |
| `documentacao.md` | Referência técnica resumida |
| `explicacao.md` | Roteiro para apresentações |
| `checklist-dados-2025.md` | Checklist de arquivos oficiais do exercício 2025 |
| `alteracoes.md` | Histórico de alterações no pipeline de dados |
| `melhorias.md` | Melhorias planejadas |

### Créditos

- **Desenvolvimento:** IFCE — prof. João Cláudio Nunes Carvalho
- **Motor original:** pacote R [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2)
