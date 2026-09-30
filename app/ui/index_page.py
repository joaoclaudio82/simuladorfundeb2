"""Monta a página inicial a partir dos fragmentos, na ordem do documento original."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARTIALS = ROOT / "static" / "partials"
ORDER = (
    "shell-head.html",
    "sidebar.html",
    "topbar.html",
    "tab-inicio.html",
    "tab-simulacao.html",
    "tab-pesos.html",
    "tab-vaar.html",
    "tab-municipio.html",
    "tab-cenario.html",
    "tab-regional.html",
    "tab-documentacao.html",
    "shell-scripts.html",
)


def render_index_bytes():
    return b"".join((PARTIALS / name).read_bytes() for name in ORDER)
