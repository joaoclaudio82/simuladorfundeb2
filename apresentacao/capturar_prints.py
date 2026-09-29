"""
Captura prints de todas as telas do Simulador FUNDEB v2 para uso em apresentações.

Uso (com o servidor rodando em http://localhost:8000):
    python apresentacao/capturar_prints.py

Saída: apresentacao/prints/*.png
"""
from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(os.path.dirname(__file__), "prints")
BASE_URL = os.environ.get("FUNDEB_URL", "http://localhost:8000")
ADMIN_CPF = os.environ.get("FUNDEB_ADMIN_CPF", "52998224725")
ADMIN_SENHA = os.environ.get("FUNDEB_ADMIN_SENHA", "admin123")

# Abas do simulador (id do data-tab → nome do arquivo)
ABAS_SIMULADOR = [
    ("00-login", None),  # página separada
    ("01-inicio", "inicio"),
    ("02-simulacao-principal-2024", "simulacao"),
    ("03-ponderacoes-2024", "pesos"),
    ("04-vaar-2024", "vaar"),
    ("05-municipio-2024", "municipio"),
    ("06-analise-regional-2024", "regional"),
    ("07-documentacao", "documentacao"),
    ("08-simulacao-2026", "simulacao-2026"),
    ("09-ponderacoes-2026", "pesos-2026"),
    ("10-vaar-2026", "vaar-2026"),
    ("11-municipio-2026", "municipio-2026"),
    ("12-consulta-2025", "simulacao-2025"),
    ("13-ponderacoes-2025", "pesos-2025"),
    ("99-admin-usuarios", None),
    ("98-simulacao-2024-resultados", "simulacao"),  # após simular
]


def login(page) -> None:
    page.goto(f"{BASE_URL}/login.html", wait_until="networkidle")
    page.fill("#login-cpf", ADMIN_CPF if len(ADMIN_CPF) > 11 else "529.982.247-25")
    page.fill("#login-senha", ADMIN_SENHA)
    page.click("#btn-login")
    page.wait_for_url(f"{BASE_URL}/**", timeout=15000)
    page.wait_for_timeout(1500)


def ativar_aba(page, tab_id: str) -> None:
    page.evaluate(f"window.activateFundebTab && window.activateFundebTab('{tab_id}')")
    page.wait_for_timeout(800)


def capturar(page, nome: str, full_page: bool = True) -> str:
    path = os.path.join(OUT_DIR, f"{nome}.png")
    page.screenshot(path=path, full_page=full_page)
    return path


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="pt-BR",
        )
        page = context.new_page()

        try:
            # Login
            page.goto(f"{BASE_URL}/login.html", wait_until="networkidle")
            capturar(page, "00-login", full_page=False)
            login(page)

            # Aguarda carregamento multi-ano
            page.wait_for_function(
                "() => document.querySelector('[data-tab=\"simulacao-2026\"]')",
                timeout=60000,
            )
            page.wait_for_timeout(2000)

            for arquivo, tab in ABAS_SIMULADOR:
                if arquivo == "99-admin-usuarios":
                    page.goto(f"{BASE_URL}/admin.html", wait_until="networkidle")
                    page.wait_for_timeout(2000)
                    capturar(page, arquivo)
                    page.goto(f"{BASE_URL}/", wait_until="networkidle")
                    page.wait_for_timeout(1500)
                    continue

                if arquivo == "98-simulacao-2024-resultados":
                    ativar_aba(page, tab)
                    btn = page.query_selector("#btn-simular")
                    if btn:
                        btn.click()
                        page.wait_for_selector("#resultados-simulacao:not(:empty)", timeout=120000)
                        page.wait_for_timeout(2000)
                    capturar(page, arquivo)
                    continue

                if tab:
                    ativar_aba(page, tab)
                    capturar(page, arquivo)

            print(f"Prints salvos em: {OUT_DIR}")
            for f in sorted(os.listdir(OUT_DIR)):
                if f.endswith(".png"):
                    print(f"  - {f}")
        except Exception as e:
            print(f"Erro: {e}", file=sys.stderr)
            print("Certifique-se de que o servidor está rodando: python main.py", file=sys.stderr)
            return 1
        finally:
            browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
