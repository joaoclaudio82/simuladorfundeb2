# Manual completo — Simulador FUNDEB v2

**Versão:** maio/2026  
**Público:** gestores educacionais, analistas, professores, técnicos e desenvolvedores — inclusive quem nunca ouviu falar em FUNDEB  
**Autor:** IFCE — prof. João Cláudio Nunes Carvalho

---

## Como ler este manual

Este documento foi escrito para ser lido **do começo ao fim por qualquer pessoa**, mesmo sem conhecimento técnico ou de finanças públicas. A ideia é que, ao terminar, você entenda:

- **O que** o sistema faz e por que ele existe (seções 1 e 2);
- **Como usar** cada tela, passo a passo (seções 3 a 8);
- **Como o sistema funciona por dentro** — para quem quiser ir mais fundo (seções 9 a 14).

Se você é **gestor, professor ou analista** e quer apenas *usar* o simulador, leia as seções **1 a 8** — elas bastam. As seções **9 em diante** são para quem precisa manter, integrar ou auditar o sistema.

> 💡 **Dica de leitura:** sempre que aparecer uma sigla (VAAF, NSE, DREC…), não se assuste. A **seção 2** explica cada uma delas em linguagem do dia a dia, e há um **glossário** no fim (seção 16) para consulta rápida.

---

## Índice

1. [Introdução — o que é e para que serve](#1-introdução--o-que-é-e-para-que-serve)
2. [Conceitos essenciais do FUNDEB (em linguagem simples)](#2-conceitos-essenciais-do-fundeb-em-linguagem-simples)
3. [Instalação e execução](#3-instalação-e-execução)
4. [Autenticação e perfis de acesso](#4-autenticação-e-perfis-de-acesso)
5. [Interface do usuário](#5-interface-do-usuário)
6. [Funcionalidades por exercício (2024, 2025 e 2026)](#6-funcionalidades-por-exercício-2024-2025-e-2026)
7. [Simulação municipal e entes estaduais](#7-simulação-municipal-e-entes-estaduais)
8. [Administração de usuários](#8-administração-de-usuários)
9. [Arquitetura técnica](#9-arquitetura-técnica)
10. [Fontes de dados](#10-fontes-de-dados)
11. [Motor de simulação (algoritmo, passo a passo)](#11-motor-de-simulação-algoritmo-passo-a-passo)
12. [Validação automática](#12-validação-automática)
13. [API REST](#13-api-rest)
14. [Testes automatizados](#14-testes-automatizados)
15. [Solução de problemas](#15-solução-de-problemas)
16. [Glossário](#16-glossário)
17. [Referências](#17-referências)

---

## 1. Introdução — o que é e para que serve

### 1.1 O que é o sistema, em uma frase

O **Simulador de Fatores de Ponderação do FUNDEB v2** é um **programa de computador que funciona no navegador** e que **imita as contas oficiais de distribuição do dinheiro da educação básica** no Brasil. Ele permite fazer perguntas do tipo *"e se…?"* e ver a resposta em números e gráficos.

> **Uma analogia:** pense num simulador de voo. O piloto pode treinar decolagens e pousos sem colocar um avião de verdade no ar. Aqui é parecido: o gestor pode "brincar" com os parâmetros da distribuição de recursos — mudar valores, pesos e matrículas — e ver o resultado **sem mexer no dinheiro real**. É um laboratório seguro para testar ideias e entender consequências.

O sistema reproduz a lógica prevista na **Lei nº 14.113/2020** (a lei que rege o FUNDEB) e no pacote de cálculo original escrito em linguagem R. A seção 2 explica o que é o FUNDEB; por enquanto, basta saber que é o fundo que financia escolas públicas de creche até o ensino médio.

### 1.2 Por que ele existe (o problema que resolve)

A distribuição do FUNDEB envolve **milhares de municípios, 27 unidades da federação, dezenas de tipos de matrícula e vários "pesos" diferentes**. Fazer essa conta "na mão", numa planilha, é lento e propenso a erros. Além disso, uma pequena mudança num município pode, por efeito dominó, afetar todos os outros do mesmo estado.

Este simulador resolve isso oferecendo:

- **Rapidez:** a conta que levaria horas numa planilha roda em segundos;
- **Segurança:** ninguém precisa arriscar cálculos manuais sobre dinheiro público real;
- **Transparência:** o sistema mostra o passo a passo e ainda **confere a própria matemática** (a "validação automática", seção 12);
- **Experimentação:** dá para testar políticas públicas antes de propô-las (por exemplo: "e se valorizássemos mais a creche integral?").

### 1.3 O que você pode fazer

| Funcionalidade | O que ela faz, em linguagem simples |
|----------------|--------------------------------------|
| **Simulação principal** | Recalcula o país inteiro com os valores que você escolher para a complementação federal (VAAF, VAAT, VAAR — explicados na seção 2). |
| **Ponderações** | Mostra (e, para administradores, permite mudar) o "peso" de cada tipo de matrícula. |
| **Simulação VAAR** | Foca especificamente na fatia que premia resultados educacionais. |
| **Simulação municipal** | Muda as matrículas de **um** município ou governo estadual e mostra o efeito nele **e em todos os vizinhos do mesmo estado**. |
| **Análise regional** | Mostra os resultados organizados por estado (UF). |
| **Exercícios 2024, 2025 e 2026** | Abas separadas, cada uma com os dados oficiais daquele ano. |
| **Validação automática** | Confere se as contas fecham (o chamado "RF-10"). |
| **Gestão de usuários** | Controla quem entra no sistema (login por CPF) e o que cada um pode fazer. |

### 1.4 Tecnologias (visão geral, sem jargão)

Você **não precisa** entender esta tabela para usar o sistema — ela é para curiosos e técnicos. Em resumo: o "cérebro" que faz as contas é escrito em **Python**, os dados vêm de **planilhas Excel** e o que você vê na tela é uma **página web comum**.

| Camada (parte do sistema) | Tecnologia | Para que serve |
|--------|------------|----------------|
| Backend (servidor) | Python 3.10+, FastAPI, Uvicorn | Recebe os pedidos e faz as contas |
| Motor de cálculo | `simulador.py` | O "coração" que reproduz a fórmula do FUNDEB |
| Leitura de dados | Pandas, Excel (openpyxl), PDF (pypdf), arquivos R legados (`.rda`) | Lê as planilhas oficiais |
| Autenticação (login) | SQLite, bcrypt, JWT | Guarda usuários e senhas com segurança |
| Frontend (a tela) | HTML, Bootstrap 5, JavaScript, Plotly.js | O que aparece no navegador, incluindo os gráficos |
| Testes | pytest | Programas que conferem se o sistema está correto |

> O motor de cálculo é uma **reescrita em Python** do pacote original em R chamado [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2). "Reescrita" significa que a mesma lógica foi traduzida de uma linguagem de programação para outra, mantendo os resultados idênticos.

---

## 2. Conceitos essenciais do FUNDEB (em linguagem simples)

Esta é a seção mais importante para quem é leigo. Leia com calma: depois dela, todo o resto do manual fica fácil. Vamos construir o entendimento **tijolo por tijolo**.

### 2.1 O que é o FUNDEB

**FUNDEB** significa *Fundo de Manutenção e Desenvolvimento da Educação Básica e de Valorização dos Profissionais da Educação*. É o principal mecanismo que **financia as escolas públicas** — de creches ao ensino médio — em todo o Brasil.

> **Analogia da "vaquinha":** imagine que cada estado organiza uma grande vaquinha (uma "caixinha coletiva"). Estados e municípios daquele território colocam dinheiro na caixinha; depois, esse dinheiro é dividido de volta entre eles conforme **quantos alunos cada um atende**. Quem tem mais alunos matriculados recebe uma fatia maior. O FUNDEB é essa vaquinha, com regras precisas de quanto entra e como se divide.

Existe **um fundo para cada estado** (mais o Distrito Federal), ou seja, 27 fundos estaduais. Dentro de cada fundo, o dinheiro é repartido entre o governo do estado e seus municípios.

### 2.2 De onde vem o dinheiro do fundo

Cada fundo estadual é abastecido por duas fontes:

1. **Os próprios estados e municípios**, que destinam ao fundo cerca de **20% de alguns impostos** (como ICMS, IPVA, FPM, FPE). Isso é automático, definido em lei.
2. **A União (governo federal)**, que acrescenta uma quantia extra chamada **complementação da União** — hoje até **23% do total** do fundo. É justamente essa complementação que o simulador permite ajustar.

A complementação da União não é jogada "de qualquer jeito". Ela é dividida em **três fatias com objetivos diferentes**: VAAF, VAAT e VAAR. Vamos a elas.

### 2.3 As três fatias da complementação: VAAF, VAAT e VAAR

Este é o conceito central. As três siglas parecem intimidadoras, mas cada uma responde a uma pergunta simples.

#### VAAF — Valor Aluno Ano do Fundeb

> **Pergunta que responde:** *"Quais estados têm o fundo mais fraco por aluno? Vamos reforçá-los primeiro."*

O VAAF olha para o **valor que cada fundo estadual tem por aluno**, considerando só aquela contribuição de ~20% dos impostos. Alguns estados são mais ricos e conseguem juntar mais dinheiro por aluno; outros, mais pobres, juntam menos. A fatia VAAF usa dinheiro da União para **elevar os estados mais pobres até um patamar mínimo comum**. É uma equalização **entre estados** (veja a analogia dos copos, na seção 2.5).

#### VAAT — Valor Aluno Ano Total

> **Pergunta que responde:** *"Considerando TODAS as receitas de educação (não só os 20%), quais entes ainda ficam abaixo do mínimo? Vamos complementá-los, um a um."*

O VAAT é mais abrangente. Ele soma **todas as receitas** que um município ou estado tem para a educação (não apenas a parcela do FUNDEB) e verifica o valor total por aluno. Aí a União complementa **cada ente individualmente** (município por município, estado por estado) que ainda estiver abaixo do mínimo nacional. É uma equalização **nacional e no nível de cada ente**, e não apenas entre estados.

#### VAAR — Valor Aluno Ano Resultado

> **Pergunta que responde:** *"Quais entes cumpriram condições de boa gestão e melhoraram os resultados de aprendizagem? Vamos premiá-los."*

O VAAR é a fatia do **mérito**. Não corrige desigualdade de arrecadação: recompensa quem atingiu **metas de qualidade e equidade** (por exemplo, melhora no aprendizado e redução de desigualdades internas). Funciona como um **bônus por desempenho**.

**Resumo das três em uma tabela:**

| Fatia | Foco | Compara… | Objetivo |
|-------|------|----------|----------|
| **VAAF** | Fundos estaduais | Estados entre si | Nivelar os fundos estaduais mais pobres |
| **VAAT** | Cada ente | Todos os municípios e estados | Garantir um mínimo total por aluno a cada ente |
| **VAAR** | Resultado | Desempenho educacional | Premiar quem melhora e cumpre condições |

### 2.4 Matrícula, matrícula ponderada e fatores de ponderação

Aqui entra o motivo do nome do sistema — "**Fatores de Ponderação**".

**Matrícula** é simplesmente um aluno matriculado. Mas nem toda matrícula "custa" o mesmo. Uma vaga em **creche em tempo integral** exige muito mais recursos (profissionais, alimentação, estrutura) do que uma vaga no **ensino médio parcial**, por exemplo. Seria injusto contar as duas como "1 aluno" cada.

Para corrigir isso, cada tipo de matrícula recebe um **fator de ponderação** (um "peso"). A conta fica assim:

```
matrícula ponderada = número de alunos × peso do tipo de matrícula
```

**Exemplo numérico simples:** suponha que a creche integral tenha peso **1,30** e o ensino médio parcial tenha peso **1,00**.

- 100 alunos em creche integral → 100 × 1,30 = **130 matrículas ponderadas**
- 100 alunos no ensino médio parcial → 100 × 1,00 = **100 matrículas ponderadas**

Ou seja: embora ambos tenham 100 alunos "de cabeça", a creche "vale" mais na hora de dividir o dinheiro, porque custa mais para funcionar. **É a matrícula ponderada — e não a bruta — que entra nas fórmulas de rateio.**

No sistema, esses pesos aparecem na tela **Ponderações**. Administradores podem alterá-los para simular políticas (por exemplo: "e se valorizássemos mais a educação do campo?").

### 2.5 Os ponderadores de contexto: NSE, NF e DREC

Além do peso do *tipo* de matrícula, o cálculo aplica outros dois ajustes que dependem **do ente** (do município/estado), não da etapa de ensino:

- **NSE — Nível Socioeconômico.** Dá um empurrão a favor de entes com população em situação socioeconômica mais vulnerável. A ideia: onde as famílias têm menos recursos, a escola pública precisa de mais apoio. Usado no VAAF e no VAAT.

- **NF / DREC — Disponibilidade de recursos.** Ajusta pela **capacidade fiscal** do ente (o quanto ele consegue arrecadar sozinho). No exercício **2024**, esse ponderador se chama **NF** e pode ser "reescalonado" (ajustado dentro de um intervalo). A partir de **2025**, ele foi substituído por um ponderador oficial chamado **DREC** (Disponibilidade de Recursos), usado como valor fixo. Ambos entram **apenas no VAAF**.

> **Por que existem esses ajustes?** Porque tratar todos os entes como iguais ignoraria que uns são mais pobres e outros mais ricos. Os ponderadores fazem o dinheiro "pesar mais" onde a necessidade é maior.

### 2.6 Equalização — a ideia dos copos d'água

A palavra **equalização** aparece o tempo todo neste manual. Ela descreve **como** a complementação da União é distribuída, e é mais simples do que parece.

> **Analogia dos copos d'água:** imagine vários copos com diferentes níveis de água — cada copo é um estado (no VAAF) ou um ente (no VAAT), e o nível de água é o "valor por aluno". Você tem uma jarra com uma quantidade **limitada** de água (a complementação da União). A regra é: **encha primeiro os copos mais vazios**, subindo o nível deles até chegar ao nível do próximo copo, e continue subindo todos juntos **até a jarra acabar**. Os copos que já estavam cheios não recebem nada; os mais vazios sobem até uma **linha comum**.

Traduzindo para o FUNDEB:

1. Ordena-se os entes do **menor** valor por aluno para o **maior**.
2. Começa-se a "despejar" a complementação nos mais pobres, elevando-os.
3. Isso continua até o dinheiro acabar. Quem estava acima da linha final não recebe complementação; quem estava abaixo é puxado para cima até um patamar comum.

É exatamente isso que a função `equaliza_fundo` faz no código ([simulador.py:93](simulador.py#L93)), como veremos na seção 11.

### 2.7 Cenário atual (dado de referência)

O **cenário atual** é a "foto oficial" — os números que o governo efetivamente publicou para aquele ano. O simulador o usa como **régua de comparação**: quando você roda uma simulação, o sistema mostra o quanto o seu cenário hipotético **ganha ou perde** em relação ao oficial. Assim você não olha os números no vácuo — sempre há uma referência real ao lado.

---

## 3. Instalação e execução

> Esta seção é para quem vai **instalar** o sistema num computador. Se alguém já instalou para você e basta abrir o navegador, pule para a [seção 4](#4-autenticação-e-perfis-de-acesso).

### 3.1 O que você precisa

- **Python 3.10 ou superior** instalado (o Python é o programa que "roda" o sistema).
- Um computador com **Windows, Linux ou macOS**.
- Não precisa de internet para funcionar: o sistema roda **localmente**, na própria máquina (em `localhost`).

### 3.2 Instalação, passo a passo

Os comandos abaixo são digitados no **terminal** (PowerShell, no Windows). Cada linha faz uma coisa; os comentários (`#`) explicam.

```powershell
cd simulador-fundeb-v2               # entra na pasta do projeto
python -m venv .venv                 # cria um "ambiente isolado" para o projeto
.\.venv\Scripts\Activate.ps1         # ativa esse ambiente (Windows)
# source .venv/bin/activate          # (equivalente no Linux/macOS)
pip install -r requirements.txt      # baixa e instala tudo que o sistema precisa
```

> **O que é esse "ambiente isolado" (venv)?** É uma caixinha separada onde ficam as peças de que *este* projeto precisa, sem bagunçar o resto do computador. Pense numa gaveta exclusiva para as ferramentas deste sistema.

**Peças principais que serão instaladas:** `fastapi`, `uvicorn`, `pandas`, `openpyxl`, `numpy`, `pyreadr`, `pypdf`, `bcrypt`, `python-jose`, `pytest`, `httpx`.

### 3.3 Ligar o servidor

```powershell
python main.py
```

Depois, abra o navegador em: **http://localhost:8000**

**Na primeira vez que você liga**, o sistema faz alguns preparativos automáticos:

- Cria o banco de usuários (`data/usuarios.db`);
- Se não houver nenhum usuário, cadastra um **administrador inicial** (veja a [seção 4](#4-autenticação-e-perfis-de-acesso));
- Carrega as planilhas dos anos 2024, 2025 e 2026. **Essa primeira carga pode levar de 30 a 90 segundos** — é normal, tenha paciência;
- Salva "atalhos" (caches) em `data/{ano}/dataset.pkl` para que as próximas vezes sejam bem mais rápidas.

### 3.4 Variáveis de ambiente (configuração opcional)

"Variáveis de ambiente" são **ajustes que você pode definir antes de ligar o sistema**, sem mexer no código. Todas têm um valor padrão, então funcionam mesmo se você não configurar nada — mas em produção algumas devem ser mudadas por segurança.

| Variável | O que controla | Padrão |
|----------|----------------|--------|
| `FUNDEB_SECRET_KEY` | Chave secreta que assina o login (troque em produção!) | *(obrigatório em produção)* |
| `FUNDEB_ADMIN_CPF` | CPF do administrador criado no primeiro uso | `52998224725` |
| `FUNDEB_ADMIN_SENHA` | Senha desse administrador | `admin123` |
| `FUNDEB_USERS_DB` | Onde fica o arquivo de usuários | `data/usuarios.db` |
| `FUNDEB_TOKEN_HOURS` | Por quantas horas o login continua válido | `12` |
| `FUNDEB_RELOAD` | Recarrega o sistema sozinho a cada mudança (só para desenvolvimento) | desativado |

> ⚠️ **Segurança:** o CPF e a senha padrão do administrador são públicos (estão neste manual!). Em qualquer uso real, **troque a senha logo após o primeiro login** e defina uma `FUNDEB_SECRET_KEY` própria.

### 3.5 Estrutura de pastas (o que é cada coisa)

```
simulador-fundeb-v2/
├── main.py                 # Programa principal: liga o servidor e cuida do ano 2024
├── api_simulacao.py        # Trata os anos 2025 e 2026
├── simulador.py            # O "coração": faz as contas do FUNDEB
├── validacao.py            # Confere se as contas fecham (RF-10)
├── auth/                   # Tudo sobre login e usuários
├── dados/
│   └── fundeb_dataset.py   # Lê e organiza as planilhas (o "ETL")
├── data/                   # Dados de 2024 + atalhos (cache)
├── 20252026/               # Planilhas brutas de 2025 e 2026
├── static/                 # A parte visual (páginas, estilos, gráficos)
├── tests/                  # Programas que testam o sistema
├── apresentacao/           # Material para apresentações
└── manual-do-sistema.md    # Este documento
```

> **O que é "ETL"?** É a sigla para *Extract, Transform, Load* (Extrair, Transformar, Carregar). É o processo de **pegar os dados das planilhas, limpá-los e organizá-los** num formato que o sistema entenda. Toda vez que este manual falar em ETL, pense em "a parte que lê e prepara as planilhas".

---

## 4. Autenticação e perfis de acesso

### 4.1 Como entrar (login)

O sistema é protegido por senha. Ninguém acessa as telas sem entrar antes. O processo é:

1. Abra `http://localhost:8000`.
2. Se você ainda não entrou, o sistema **redireciona automaticamente** para a tela de login (`/login.html`).
3. Digite seu **CPF** (11 dígitos, com ou sem pontos e traço) e a **senha**.
4. O sistema confere os dados e, se estiverem certos, guarda um "crachá digital" no navegador (um cookie seguro chamado `fundeb_token`).
5. Pronto: o simulador é liberado.

> **O que é esse "crachá digital" (token)?** É como uma pulseira de acesso de um evento: depois de entrar, você recebe uma pulseira que prova que já foi autorizado, e não precisa mostrar o documento de novo a cada porta. O crachá vale por algumas horas (12, por padrão) e depois expira, exigindo novo login.

### 4.2 Primeiro acesso (ambiente de desenvolvimento)

Na primeira vez, use as credenciais padrão do administrador:

| Campo | Valor padrão |
|-------|--------------|
| CPF | `529.982.247-25` |
| Senha | `admin123` |

> ⚠️ **Importante:** troque a senha logo após o primeiro login, na tela **Usuários** (`/admin.html`). A senha padrão é conhecida por qualquer pessoa que leia este manual.

### 4.3 Perfis: administrador × usuário comum

Existem **dois tipos de usuário**, com permissões diferentes:

| O que pode fazer | Administrador | Usuário comum |
|------------------|:-------------:|:-------------:|
| Ver o simulador e todas as abas | ✅ Sim | ✅ Sim |
| Rodar simulações (VAAF/VAAT/VAAR/Municipal) | ✅ Sim | ✅ Sim |
| **Editar** os pesos de ponderação | ✅ Sim | ❌ Não (só vê) |
| Enviar pesos personalizados pela API | ✅ Sim | ❌ Não (usa os oficiais) |
| Cadastrar, editar e excluir usuários | ✅ Sim | ❌ Não |
| Ver o menu **Usuários** | ✅ Visível | ❌ Oculto |

Em outras palavras: **todos podem simular e explorar**, mas **só o administrador muda os pesos e gerencia quem entra**.

> **Segurança de verdade, não só aparência:** a proibição de usar pesos personalizados é feita **no servidor** (na função `preparar_pesos`, em `api_simulacao.py`), não apenas escondendo botões na tela. Ou seja, mesmo que alguém tente burlar a página no navegador, o servidor recusa pesos não autorizados.

### 4.4 Sair da sessão

Clique em **Sair**, no rodapé do menu lateral. O crachá digital é apagado e a sessão é encerrada. Para voltar, é preciso fazer login de novo.

---

## 5. Interface do usuário

### 5.1 O menu lateral

Todas as telas são acessadas pelo **menu à esquerda**, organizado por ano:

```
┌─────────────────────────────────────┐
│  FUNDEB — Simulador v2              │
│  [nome do usuário / perfil]         │
├─────────────────────────────────────┤
│  🏠 Página Principal                │
├─ FUNDEB 2024 ───────────────────────┤
│  🧮 Simulação Principal             │
│  ⚖️  Ponderações                    │
│  🏆 Simulação VAAR                  │
│  📍 Simulação Municipal             │
│  🗺️  Análise Regional              │
├─ FUNDEB 2026 ───────────────────────┤
│  🧮 Simulação 2026                  │
│  ⚖️  Ponderações 2026               │
│  🏆 VAAR 2026                       │
│  📍 Município 2026                  │
├─ FUNDEB 2025 ───────────────────────┤
│  📅 Consulta / Simulação 2025       │
│  ⚖️  Ponderações 2025               │
├─────────────────────────────────────┤
│  📖 Documentação                    │
│  👥 Usuários (só admin)             │
├─────────────────────────────────────┤
│  🚪 Sair                            │
└─────────────────────────────────────┘
```

As abas **2025** e **2026** aparecem automaticamente (são geradas pelo arquivo `app_multi_ano.js`). Em **celulares e tablets**, o menu fica escondido e abre com o botão ☰ (as "três listrinhas").

### 5.2 Página Principal

É a tela de boas-vindas. Ela **explica o FUNDEB** — como o fundo é composto, o que são VAAF/VAAT/VAAR, como a complementação federal cresceu de 2021 a 2026 e como as matrículas são contadas. **Não faz cálculos**; serve para situar o usuário. É, em essência, uma versão resumida da nossa [seção 2](#2-conceitos-essenciais-do-fundeb-em-linguagem-simples).

### 5.3 Simulação Principal

Esta é a tela mais usada. Ela tem dois lados.

**Do lado esquerdo, você define os parâmetros:**

| Campo | O que você está escolhendo |
|-------|----------------------------|
| Montante VAAF (R$) | Quanto a União vai destinar à equalização **entre fundos estaduais** |
| Montante VAAT (R$) | Quanto vai à equalização **nacional** (todos os entes) |
| Montante VAAR (R$) | Quanto vai ao prêmio **por resultado** |
| NF máximo / mínimo | *(só 2024)* O intervalo de ajuste do ponderador NF no VAAF |

**Do lado direito, depois de clicar em "Simular", aparecem os resultados:**

- **Caixas-resumo** com os números-chave: menor VAAF/VAAT, comparação com o cenário oficial, quanto foi para municípios versus estados;
- O **selo da validação automática** (RF-10): "OK" (contas fecham) ou "Falhou";
- **Gráficos 2D** (feitos com a biblioteca Plotly): VAAF/VAAT por estado, diferenças, complementação por modalidade;
- **Tabelas** de "maiores ganhadores" e "maiores perdedores" em relação ao cenário oficial;
- **Gráficos 3D**: um "cubo" que cruza VAAF × VAAT × complementação, para uma visão espacial.

### 5.4 Ponderações

Mostra a lista de **todos os tipos de matrícula**, agrupados por **família** (Creche, Pré-escola, Ensino Fundamental etc.), num formato de "sanfona" (acordeão) que você expande e recolhe.

Cada tipo de matrícula tem dois pesos:

- **Peso VAAF** — quanto essa matrícula pesa no cálculo do VAAF;
- **Peso VAAT** — quanto pesa no cálculo do VAAT.

| Perfil | O que vê |
|--------|----------|
| Administrador | Campos **editáveis**: qualquer mudança passa a valer nas próximas simulações |
| Usuário comum | Campos **bloqueados**, com um aviso de "somente leitura" |

### 5.5 Simulação VAAR

Foca exclusivamente na fatia de **mérito** (VAAR). Mostra como esse prêmio se distribui por estado, a participação de cada um no total e tabelas detalhadas. Tecnicamente, usa a rota `POST /api/simular/completo` (ou a equivalente do ano).

### 5.6 Análise Regional *(2024)*

Apresenta os resultados **organizados por estado (UF)**. Quando o app abre, ele já roda uma simulação com valores padrão, então há dados prontos para explorar. Basta escolher a UF para ver o resumo de recursos e complementação daquele estado.

> A Análise Regional dos anos 2025/2026 ainda **não** foi implementada.

### 5.7 Documentação (aba interna)

Um texto de apoio, dentro do próprio app, com links para portarias e para o site do FNDE. Complementa este manual.

---

## 6. Funcionalidades por exercício (2024, 2025 e 2026)

O sistema trabalha com **três anos** de dados, cada um numa aba própria. Os anos não são idênticos porque as regras e as fontes oficiais mudaram com o tempo.

### 6.1 O que muda de um ano para o outro

| Aspecto | 2024 | 2025 | 2026 |
|---------|------|------|------|
| Tipos de matrícula | **41** etapas | **319** segmentos | **319** segmentos |
| Ponderador fiscal do VAAF | **NF** (ajustável) | **DREC** (oficial) | **DREC** (oficial) |
| Ponderador social (NSE) | Sim | Sim | Sim |
| Simulação disponível? | Sempre | **Só se os dados estiverem completos** | Sim |
| Valores padrão | Legado de 2024 | Portaria / receita STN | Portaria MEC/MF nº 6/2026 |
| Endereços da API | `/api/...` | `/api/2025/...` | `/api/2026/...` |

> **Por que 41 "etapas" em 2024 e 319 "segmentos" em 2025/2026?** Porque a classificação das matrículas ficou mais detalhada. Onde antes havia uma categoria ampla, passou a haver várias subdivisões (por rede, localização, tempo integral/parcial etc.). Mais segmentos = mais precisão.

**Atenção ao ano 2025 — simulação condicional:** a simulação de 2025 só liga se **todos** os arquivos auxiliares (receita, NSE, DREC e VAAT oficiais) estiverem presentes na pasta `20252026/`. Se faltar algum, a aba permite apenas **consultar** matrículas e pesos, e qualquer tentativa de simular retorna um erro "HTTP 503" (serviço indisponível). O documento `checklist-dados-2025.md` lista o que é preciso.

### 6.2 As fórmulas de cada ano

Não se assuste com as fórmulas — elas apenas resumem o que já explicamos na seção 2. A diferença entre os anos é só **qual ponderador fiscal** entra (NF ou DREC):

**Ano 2024 (usa NF reescalonado):**
```
matriculas_vaaf = (matrículas × pesos_vaaf) × NSE × NF
matriculas_vaat = (matrículas × pesos_vaat) × NSE
```

**Anos 2025 e 2026 (usam DREC):**
```
matriculas_vaaf = (matrículas × pesos_vaaf) × NSE × DREC
matriculas_vaat = (matrículas × pesos_vaat) × NSE
```

Lendo em português: *"a matrícula ponderada do VAAF é o número de alunos, multiplicado pelos pesos, ajustado pelo nível socioeconômico (NSE) e pela disponibilidade de recursos (NF ou DREC)"*. O VAAT é igual, mas **sem** o ponderador fiscal.

### 6.3 As abas de 2026

São equivalentes às de 2024, com estas particularidades:

- Os valores padrão de complementação vêm da rota `GET /api/2026/meta`;
- O DREC é mostrado como um **valor fixo** (não há o controle deslizante do NF);
- A tela de Ponderações lista os **319 segmentos**;
- A simulação municipal tem um botão **"Mostrar segmentos sem matrícula"**, para incluir ou ocultar tipos de matrícula com zero alunos.

### 6.4 As abas de 2025

- **Consulta / Simulação 2025:** só habilita a simulação quando todos os arquivos auxiliares estão presentes (veja 6.1);
- **Ponderações 2025:** somente leitura para o usuário comum;
- As matrículas são filtradas de uma planilha unificada (as linhas onde a coluna `ANO = 2025`).

---

## 7. Simulação municipal e entes estaduais

Esta é uma das funcionalidades mais interessantes — e a que melhor mostra o **efeito dominó** do FUNDEB.

### 7.1 A pergunta que ela responde

> *"Se eu mudar as matrículas deste município (ou governo estadual), o que acontece com ele **e com todos os outros entes do mesmo estado**?"*

### 7.2 Passo a passo na tela

1. **Escolha a UF** (a lista vem agrupada por região).
2. **Escolha o ente** no menu suspenso:
   - O **governo estadual** aparece primeiro (ex.: *Acre (12)*);
   - Depois vêm os **municípios**, em ordem alfabética.
3. **Veja e edite** as matrículas por segmento no acordeão.
4. Se quiser, **ajuste os montantes** VAAF/VAAT/VAAR.
5. Clique em **Simular**.

### 7.3 Entes estaduais e o código IBGE

Cada ente é identificado por um **código do IBGE**. Um truque simples permite saber se é um estado ou um município: **o tamanho do número**.

| Código IBGE | Tipo | Exemplo |
|-------------|------|---------|
| Menor que 100 (2 dígitos) | Governo estadual | `12` = Acre |
| Maior que 100 (7 dígitos) | Município | `1200054` = Assis Brasil/AC |

Os **27 governos estaduais** estão disponíveis em **2024, 2025 e 2026**. O nome aparece no padrão oficial (ex.: "Acre", e não "GOVERNO DO ESTADO DO ACRE").

### 7.4 Por que o sistema recalcula o país inteiro

Pode parecer exagero recalcular tudo só porque um município mudou. Mas é necessário, por causa da equalização (lembre-se dos copos d'água, seção 2.6):

1. Mudar as matrículas de um município **muda a participação dele** no fundo estadual;
2. Isso **altera como o fundo estadual se reparte** entre todos;
3. Portanto, pode afetar **todos os entes daquele estado**, em cascata.

Para medir esse efeito, o sistema roda a simulação **duas vezes** — uma com os números originais e outra com os ajustados — e **compara as duas**.

### 7.5 O que aparece nos resultados

| Painel | O que mostra |
|--------|--------------|
| **Cards** | VAAF, VAAT, complementos e recursos, **antes e depois** da sua mudança |
| **Explicação textual** | Um passo a passo em português (gerado por `explicacao.js`): matrículas ponderadas, coeficiente do ente no estado, o valor mínimo do VAAF etc. |
| **Tabela de impacto** | O efeito da sua mudança **sobre os outros entes** do mesmo estado |
| **Gráficos** | Comparativos em 2D e 3D |

> A "explicação textual" é ótima para quem está aprendendo: em vez de só mostrar números, o sistema **narra** o que aconteceu, quase como um professor comentando a conta.

---

## 8. Administração de usuários

Esta tela (`/admin.html`) só aparece e só funciona para **administradores**.

### 8.1 Cadastrar um novo usuário

| Campo | Regra |
|-------|-------|
| CPF | 11 dígitos, e precisa ser um CPF **válido** (o sistema confere os dígitos verificadores) |
| Nome | Opcional |
| Senha | No mínimo 6 caracteres |
| Perfil | `usuario` (padrão) ou `admin` |

### 8.2 Gerenciar usuários existentes

| Botão | O que faz |
|-------|-----------|
| ✏️ Editar | Abre uma janela para mudar nome, perfil, status (ativo/inativo) e, opcionalmente, a senha |
| 🔑 Reset de senha | Um atalho rápido para definir uma nova senha |
| 🚫 / ✓ | Desativa ou reativa o usuário |
| 🗑️ Excluir | Remove o usuário de vez |

**Regras de segurança que o sistema impõe automaticamente:**

- Você **não pode** desativar nem excluir a **si mesmo** (evita ficar trancado para fora);
- **Não é permitido** remover o **último administrador ativo** (senão ninguém mais poderia administrar);
- Um usuário **inativo** que tentar entrar recebe erro "HTTP 403" (acesso proibido).

---

## 9. Arquitetura técnica

> A partir daqui, o manual fica mais técnico. Se você só quer *usar* o sistema, pode parar na seção 8. As seções seguintes são para quem **mantém, integra ou audita** o sistema.

O diagrama abaixo mostra como as partes conversam. À esquerda, o **navegador** (o que o usuário vê); à direita, o **servidor** (onde as contas acontecem); embaixo, os **componentes internos**.

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

Em palavras: o navegador manda um pedido (por exemplo, "simule com estes valores"); o FastAPI recebe, confere o crachá (JWT), pega os dados já preparados pelo ETL, entrega ao motor de cálculo, valida o resultado e devolve tudo em formato JSON para a tela desenhar os gráficos.

### 9.1 Arquivos principais

| Arquivo | De que é responsável |
|---------|----------------------|
| `main.py` | Liga o servidor FastAPI, cuida das rotas de 2024 e serve as páginas |
| `api_simulacao.py` | Rotas dos anos 2025/2026, executa a simulação e monta o resumo |
| `simulador.py` | O motor: `simula_fundeb` e as funções de equalização |
| `dados/fundeb_dataset.py` | O ETL: lê Excel/RDA/PDF, organiza tudo e guarda cache |
| `validacao.py` | As conferências RF-10 |
| `auth/*` | Login (JWT + bcrypt) e o banco de usuários |
| `static/js/app.js` | A tela do exercício 2024 |
| `static/js/app_multi_ano.js` | As telas de 2025/2026 |
| `static/js/auth.js` | Controle de sessão e comunicação segura com a API |
| `static/js/explicacao.js` | A narrativa da simulação municipal |
| `static/js/charts3d.js` | Os gráficos em 3D |

### 9.2 O caminho de uma simulação, do clique ao gráfico

1. A tela envia um `POST /api/simular` (ou `/api/2026/simular`) com os parâmetros em JSON;
2. O servidor **confere o crachá** (cookie JWT);
3. `preparar_pesos` decide quais pesos usar: os oficiais ou os personalizados (só admin);
4. `executar_simulacao` chama o motor `simula_fundeb`;
5. `validar_interno` roda as conferências RF-10;
6. `gerar_resumo` monta as caixas-resumo e os agrupamentos;
7. O resultado, já "limpo", volta em JSON para a tela;
8. O Plotly desenha os gráficos e as tabelas.

---

## 10. Fontes de dados

Os números do simulador **não são inventados**: vêm de planilhas e arquivos oficiais. Esta seção lista de onde sai cada coisa.

### 10.1 Exercício 2024 (pasta `data/`)

| Arquivo | O que contém |
|---------|--------------|
| `dados_unificados.xlsx` | Matrículas, receitas e a chave de identificação (IBGE) |
| `pesos.rda` | Os pesos VAAF/VAAT das 41 etapas |
| `complementar.rda` | NF, inabilitados do VAAT e peso do VAAR |
| `matriculas.rda` | Reserva para etapas ausentes na planilha |
| `cenario_atual*.rda` | O cenário oficial de referência |
| `PonderadorNSE 2024.pdf` | O NSE por código IBGE |

> **Política híbrida:** as matrículas oficiais vêm do arquivo `matriculas.rda`; a planilha Excel fornece as receitas e campos extras. Isso combina a fonte mais confiável de cada dado.

### 10.2 Exercícios 2025 e 2026 (pasta `20252026/`)

| Arquivo | Ano | Uso |
|---------|-----|-----|
| `Matrículas Fundeb 2026.xlsx` | **2026** | Matrículas + pesos (aba FPs) — fonte dedicada |
| `Matrículas Fundeb 2025 e 2026.xlsx` | **2025** | Matrículas (`ANO=2025`) + pesos |
| `1-receita-total-do-fundeb-por-ente-federado.xlsx` | 2026 | Receitas e peso VAAR |
| `1-receita-total-do-fundeb-por-ente-federado-2025.xlsx` | 2025 | Receitas |
| `ponderador-de-nivel-socioeconomico.xlsx` | 2026 | NSE |
| `ponderador-de-nivel-socioeconomico-2025.xlsx` | 2025 | NSE |
| `ponderador-de-disponibilidade-de-recursos.xlsx` | 2026 | DREC |
| `ponderador-de-disponibilidade-de-recursos-2025.xlsx` | 2025 | DREC |
| `MemriadeClculoVAAT2026 (2).xlsx` | 2026 | Memória de cálculo do VAAT, inabilitados |
| `Receita STN 2023 VAAT 2025 para publicação.xlsx` | 2025 | Memória de cálculo do VAAT |

### 10.3 O cache do ETL (por que a segunda vez é mais rápida)

Depois da primeira carga, o sistema **guarda o resultado já preparado** em arquivos `.pkl`, para não precisar reler as planilhas toda vez:

- `data/2024/` — preparado no início, em `main.py`;
- `data/2025/dataset.pkl`;
- `data/2026/dataset.pkl`.

Existe uma "versão do cache" (`DATASET_CACHE_VERSION`, em `fundeb_dataset.py`). **Sempre que você mudar o ETL ou trocar uma planilha**, aumente esse número **ou** apague os arquivos `.pkl` — assim o sistema entende que precisa reler os dados novos. (Se esquecer disso, o sistema continuará mostrando os dados antigos do cache.)

### 10.4 Banco de usuários

- Arquivo: `data/usuarios.db` (banco SQLite);
- Tabela `users`: guarda CPF, senha (criptografada com bcrypt), perfil (`role`), nome, status (ativo) e data de criação.

> **A senha nunca é guardada "em texto puro".** O bcrypt transforma a senha num código embaralhado e irreversível ("hash"). Nem o administrador consegue ler a senha de um usuário — só pode redefini-la.

---

## 11. Motor de simulação (algoritmo, passo a passo)

Toda a mágica acontece na função **`simula_fundeb`** ([simulador.py:175](simulador.py#L175)). Vamos percorrê-la em etapas, sempre traduzindo a matemática para o português.

### Etapa 1 — Transformar matrículas em matrículas ponderadas

```
matriculas_vaaf = Σ (matrícula da etapa × peso VAAF da etapa)
matriculas_vaat = Σ (matrícula da etapa × peso VAAT da etapa)
```

O símbolo `Σ` (sigma) significa apenas "some tudo". Para cada ente, multiplicamos as matrículas de cada etapa pelo peso correspondente e somamos. (Tecnicamente é uma multiplicação de matrizes: `matriz @ vetor_pesos`.)

### Etapa 2 — Aplicar NSE e NF/DREC

Multiplica-se as matrículas ponderadas pelo **NSE** (no VAAF e no VAAT) e pelo **NF ou DREC** (só no VAAF). É aqui que o contexto social e a capacidade fiscal entram na conta.

### Etapa 3 — Juntar por estado (UF)

```
vaaf_estado_inicial = recursos do estado (VAAF) / matrículas do estado (VAAF)
```

Ou seja: quanto cada estado tem por aluno **antes** de qualquer complementação. É o "nível de água" inicial de cada copo (seção 2.6).

### Etapa 4 — Equalização do VAAF (entre estados)

Aqui entra o algoritmo `equaliza_fundo`. Ele ordena os estados do menor valor por aluno para o maior e **despeja** a complementação `complementacao_vaaf` nos mais pobres, elevando-os até um patamar comum, **até o dinheiro acabar**. Estados que já estavam acima da linha final mantêm seus recursos originais. (É a analogia dos copos d'água em ação.)

### Etapa 5 — Redistribuir dentro de cada estado

```
recursos_vaaf_final = matriculas_vaaf × (recursos do estado após equalização / matrículas do estado)
vaaf_final          = recursos_vaaf_final / matriculas_vaaf
```

Depois de definir quanto **cada estado** ficou tendo, reparte-se esse total **entre os entes daquele estado**, na proporção das matrículas ponderadas de cada um.

### Etapa 6 — Calcular o VAAT antes da complementação

```
vaat_pre = recursos_vaat / matriculas_vaat
```

O valor total por aluno de cada ente **antes** da complementação nacional.

### Etapa 7 — Equalização do VAAT (nacional)

Mesmo algoritmo dos copos, mas agora **ente por ente** (por código `ibge`) e em nível nacional, **excluindo os entes inabilitados** do VAAT (aqueles que, por regra, não têm direito a essa complementação).

### Etapa 8 — VAAR (o prêmio por resultado)

```
complemento_vaar = peso_vaar × complementacao_vaar
```

Distribui o prêmio conforme o peso de resultado de cada ente.

### Etapa 9 — Somar tudo (totais finais)

```
complemento_vaaf  = recursos_vaaf_final - recursos_vaaf
complemento_vaat  = recursos_vaat_final - recursos_vaat
complemento_uniao = complemento_vaaf + complemento_vaat + complemento_vaar
recursos_fundeb   = recursos_vaaf + complemento_uniao
```

Em português: **o complemento** de cada modalidade é o quanto o ente ganhou a mais graças à União; a **complementação total da União** é a soma das três fatias; e os **recursos finais do FUNDEB** são os recursos próprios mais tudo o que a União acrescentou.

---

## 12. Validação automática

Como confiar que o sistema não errou uma conta? Ele **confere a si mesmo**. Depois de cada simulação, o `validacao.py` roda quatro verificações — o conjunto apelidado de **RF-10**:

| # | O que verifica | Que erro isso pegaria |
|---|----------------|-----------------------|
| 1 | A soma dos `recursos_vaaf` de um estado bate com o total daquele estado | Erro ao juntar/agrupar dados |
| 2 | `vaaf_final` é mesmo igual a `recursos_vaaf_final ÷ matriculas_vaaf` | Fórmula inconsistente |
| 3 | As participações VAAF dentro do estado somam 100% | Erro no rateio interno |
| 4 | `recursos_fundeb` é mesmo `recursos_vaaf + complemento_uniao` | Erro nas colunas finais |

Pense nisso como a **conferência do troco**: depois de fazer as contas, o sistema refaz algumas somas por outro caminho para garantir que tudo fecha.

**Como o resultado aparece na resposta da API:**

```json
"validacao": {
  "valido": true,
  "erros": [],
  "avisos": [],
  "checagens": ["UF SP: soma recursos = total estadual OK", "..."]
}
```

> Se `valido` for `false`, os resultados **ainda são exibidos**, mas com um alerta bem visível para você desconfiar dos números e investigar (por exemplo, parâmetros extremos ou dados inconsistentes).

---

## 13. API REST

> Esta seção interessa a **desenvolvedores** que queiram integrar o simulador a outros sistemas. Se você só usa a tela, pode pular.

Uma "API REST" é a **porta de entrada programável** do sistema: em vez de clicar em botões, outro programa pode enviar pedidos diretamente. Todas as rotas que começam com `/api/*` (menos o login) exigem o crachá `fundeb_token`.

### 13.1 Autenticação

| Método | Rota | O que faz |
|--------|------|-----------|
| POST | `/api/auth/login` | Recebe `{cpf, senha}` e devolve o cookie |
| POST | `/api/auth/logout` | Apaga o cookie |
| GET | `/api/auth/me` | Diz quem você é: `{cpf, role, nome}` |

### 13.2 Administração

| Método | Rota | O que faz |
|--------|------|-----------|
| GET | `/api/admin/usuarios` | Lista os usuários |
| POST | `/api/admin/usuarios` | Cria um usuário |
| PATCH | `/api/admin/usuarios/{cpf}` | Atualiza nome, perfil, status ou senha |
| DELETE | `/api/admin/usuarios/{cpf}` | Remove um usuário |

### 13.3 FUNDEB 2024

| Método | Rota | O que faz |
|--------|------|-----------|
| GET | `/api/estados` | Lista UFs e regiões |
| GET | `/api/municipios?uf=XX` | Entes da UF (estado primeiro, depois municípios) |
| GET | `/api/pesos` | Pesos por etapa |
| GET | `/api/etapas` | Nomes amigáveis das etapas |
| GET | `/api/municipio/{ibge}/matriculas` | Matrículas e dados de um ente |
| GET | `/api/cenario-atual/resumo` | O cenário oficial de referência |
| POST | `/api/simular` | Simulação agregada (resumo + gráficos) |
| POST | `/api/simular/completo` | Uma linha por ente |
| POST | `/api/simular/municipio` | Comparativo original × ajustado |

### 13.4 Por exercício (`/api/2025/...`, `/api/2026/...`)

A mesma estrutura, só que com o ano no endereço:

| Método | Rota | O que faz |
|--------|------|-----------|
| GET | `/api/{ano}/meta` | Metadados, valores padrão, se a simulação está habilitada |
| GET | `/api/{ano}/estados` | UFs e regiões |
| GET | `/api/{ano}/municipios?uf=XX` | Entes da UF |
| GET | `/api/{ano}/pesos` | Pesos por segmento |
| GET | `/api/{ano}/etapas` | Nomes das etapas |
| GET | `/api/{ano}/municipio/{ibge}/matriculas` | Matrículas de um ente |
| GET | `/api/{ano}/cenario-atual/resumo` | Cenário de referência |
| POST | `/api/{ano}/simular` | Simulação agregada |
| POST | `/api/{ano}/simular/completo` | Dados completos por ente |
| POST | `/api/{ano}/simular/municipio` | Simulação municipal |

### 13.5 Como é o pedido de uma simulação

O corpo de um pedido de simulação é um JSON assim (os valores são exemplos):

```json
{
  "complementacao_vaaf": 60249853912.98,
  "complementacao_vaat": 63262346608.62,
  "complementacao_vaar": 0,
  "max_nse": 1.1,
  "min_nse": 1.0,
  "max_nf": 1.0,
  "min_nf": 1.0,
  "pesos_vaaf": [1.0, 1.2],
  "pesos_vaat": [1.0, 1.1]
}
```

A simulação **municipal** acrescenta o ente e as matrículas alteradas:

```json
{
  "ibge": 1200054,
  "matriculas_ajustadas": {
    "creche_integral_rede_publica": 500,
    "pre_escola_parcial_rede_publica": 1200
  }
}
```

> Os campos `pesos_vaaf` e `pesos_vaat` **só têm efeito para administradores**. Se um usuário comum enviá-los, o servidor os ignora e usa os pesos oficiais.

### 13.6 Exemplo prático com `curl` (depois do login)

```powershell
# 1) Fazer login e salvar o cookie num arquivo
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"cpf":"52998224725","senha":"admin123"}'

# 2) Simular 2026 usando o cookie salvo
curl -b cookies.txt -X POST http://localhost:8000/api/2026/simular `
  -H "Content-Type: application/json" `
  -d '{"complementacao_vaaf":60249853912.98,"complementacao_vaat":63262346608.62}'
```

---

## 14. Testes automatizados

O projeto vem com **testes** — pequenos programas que verificam, sozinhos, se o sistema continua correto depois de qualquer mudança. Para rodá-los:

```powershell
python -m pytest tests/ -v
```

| Arquivo | O que verifica |
|---------|----------------|
| `test_requisitos.py` | Regras de participação (CA-02), redistribuição (RN-03) e a validação RF-10 |
| `test_dataset_2025.py` | A leitura dos dados de 2025 e os entes estaduais |
| `test_dataset_2026.py` | A leitura dos dados de 2026 e o arquivo dedicado de matrículas |
| `test_auth.py` | Login, perfis e a proibição de pesos personalizados |

> **Por que isso importa para um leigo?** Porque significa que, sempre que alguém melhora o sistema, esses testes avisam **na hora** se algo quebrou — como um alarme de fumaça para o código.

---

## 15. Solução de problemas

| Problema | Causa provável | O que fazer |
|----------|----------------|-------------|
| O sistema volta para a tela de login sozinho | Sessão expirou ou o cookie sumiu | Faça login novamente |
| Erro "HTTP 503" ao simular 2025 | Faltam arquivos de dados de 2025 | Consulte `checklist-dados-2025.md` |
| A primeira carga está muito lenta | O ETL está lendo planilhas grandes | Aguarde; nas próximas vezes o cache `.pkl` acelera |
| O menu de município não mostra o estado | Cache ou página desatualizada | Aperte Ctrl+F5; se preciso, apague `data/2026/dataset.pkl` |
| A validação RF-10 falhou | Dados inconsistentes ou valores extremos | Veja o campo `validacao.erros` na resposta |
| `ModuleNotFoundError: pypdf` | As dependências não foram instaladas | Rode `pip install -r requirements.txt` |
| Administrador não consegue editar pesos | O perfil não é de admin | Confirme se `role: admin` aparece em `/api/auth/me` |

### 15.1 Como atualizar a planilha de matrículas de 2026

1. Substitua o arquivo `20252026/Matrículas Fundeb 2026.xlsx` pela versão nova;
2. Aumente `DATASET_CACHE_VERSION` em `dados/fundeb_dataset.py` **ou** apague `data/2026/dataset.pkl` (para o sistema reler os dados);
3. Reinicie o servidor;
4. Rode `pytest tests/test_dataset_2026.py` para confirmar que está tudo certo.

---

## 16. Glossário

| Termo | Significado em uma frase |
|-------|---------------------------|
| **FUNDEB** | O fundo que financia a educação básica pública no Brasil |
| **Ente** | Um município ou um governo estadual que participa do fundo |
| **IBGE** | O código que identifica cada ente (`12` = AC; `1200054` = Assis Brasil/AC) |
| **VAAF** | Valor Aluno Ano do Fundeb — equaliza **entre os fundos estaduais** |
| **VAAT** | Valor Aluno Ano Total — equaliza **entre todos os entes**, considerando todas as receitas |
| **VAAR** | Valor Aluno Ano Resultado — o **prêmio por desempenho** educacional |
| **NSE** | Ponderador de Nível Socioeconômico — favorece contextos mais vulneráveis |
| **NF** | Ponderador de disponibilidade de recursos (modelo de 2024) |
| **DREC** | Disponibilidade de Recursos — substitui o NF no VAAF a partir de 2025 |
| **FP** | Fator de Ponderação — o "peso" de cada tipo de matrícula |
| **Segmento / etapa** | Uma categoria de matrícula (ex.: creche integral urbana) |
| **Família** | Um agrupamento visual de segmentos na tela |
| **Matrícula ponderada** | Matrícula × peso × (NSE e, no VAAF, NF/DREC) |
| **Equalização** | O algoritmo que distribui a complementação "do mais pobre para o mais rico" |
| **Cenário atual** | Os dados oficiais publicados, usados como comparação |
| **RF-10** | O conjunto de conferências automáticas da matemática |
| **Inabilitados VAAT** | Entes que, por regra, não recebem a complementação VAAT |
| **ETL** | O processo de ler, limpar e organizar os dados das planilhas |
| **JWT / cookie** | O "crachá digital" que prova que você já fez login |

---

## 17. Referências

### Legislação

- [Lei nº 14.113/2020](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/L14113.htm) — o marco legal do FUNDEB

### Dados oficiais

- [FNDE — FUNDEB](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb)
- [Matrículas da educação básica](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/matriculas-da-educacao-basica)
- [FUNDEB 2025](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2025)
- Portaria MEC/MF nº 6/2026 — montantes da complementação de 2026

### Documentação complementar no repositório

| Arquivo | Conteúdo |
|---------|----------|
| `README.md` | Visão geral e início rápido |
| `documentacao2.md` | Guia didático detalhado (complementar) |
| `documentacao.md` | Referência técnica resumida |
| `explicacao.md` | Roteiro para apresentações |
| `checklist-dados-2025.md` | Checklist de arquivos para habilitar 2025 |
| `alteracoes.md` | Histórico de alterações no pipeline de dados |

### Créditos

- **Desenvolvimento:** IFCE — prof. João Cláudio Nunes Carvalho
- **Motor original:** pacote R [simulador.fundeb](https://github.com/mellohenrique/simulador.fundeb2)

---

*Manual gerado para o Simulador FUNDEB v2 — branch maio2026.*
