# Prints do Simulador FUNDEB v2 — Apresentação PPT

Esta pasta reúne capturas de tela de **todas as telas** do aplicativo, numeradas na ordem sugerida para slides.

## Como gerar ou atualizar os prints

1. Inicie o servidor:
   ```powershell
   python main.py
   ```
2. Em outro terminal:
   ```powershell
   python apresentacao/capturar_prints.py
   ```

Variáveis opcionais: `FUNDEB_URL`, `FUNDEB_ADMIN_CPF`, `FUNDEB_ADMIN_SENHA`.

## Arquivos (ordem sugerida no PowerPoint)

| Arquivo | Tela |
|---------|------|
| `00-login.png` | Tela de login (CPF e senha) |
| `01-inicio.png` | Página principal — introdução ao FUNDEB |
| `02-simulacao-principal-2024.png` | Simulação principal 2024 (parâmetros) |
| `98-simulacao-2024-resultados.png` | Simulação 2024 com resultados, gráficos e validação |
| `03-ponderacoes-2024.png` | Ponderações 2024 (41 etapas) |
| `04-vaar-2024.png` | Simulação VAAR 2024 |
| `05-municipio-2024.png` | Simulação municipal 2024 |
| `06-analise-regional-2024.png` | Análise regional por UF |
| `07-documentacao.png` | Aba documentação no app |
| `08-simulacao-2026.png` | Simulação 2026 |
| `09-ponderacoes-2026.png` | Ponderações 2026 (319 segmentos) |
| `10-vaar-2026.png` | VAAR 2026 |
| `11-municipio-2026.png` | Município 2026 |
| `12-consulta-2025.png` | Consulta 2025 (somente leitura) |
| `13-ponderacoes-2025.png` | Ponderações 2025 |
| `99-admin-usuarios.png` | Cadastro e edição de usuários (admin) |

## Dica para o PowerPoint

- Use **Inserir → Imagens** e selecione todos os PNG desta pasta.
- A numeração no nome do arquivo (`01-`, `02-`…) mantém a ordem lógica da apresentação.
- Para slides de “menu”, recorte a barra lateral do print `01-inicio` ou `02-simulacao-principal-2024`.

## Documentação complementar

- `documentacao2.md` — explicação didática completa do sistema
- `explicacao.md` — roteiro resumido para apresentação oral
