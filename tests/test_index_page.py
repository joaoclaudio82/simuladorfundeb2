"""A página inicial montada permanece igual à referência e o menu tem um só exercício."""

from pathlib import Path

from app.ui.index_page import render_index_bytes


def test_index_html_preserva_a_referencia():
    golden = Path(__file__).parent / "golden" / "index.html"
    assert render_index_bytes() == golden.read_bytes()


def test_menu_tem_um_seletor_de_exercicio():
    texto = render_index_bytes().decode("utf-8")
    assert 'id="exercicio-ativo"' in texto
    barra = texto.split('id="sidebar"', 1)[1].split("</nav>", 1)[0]
    for rotulo in ("FUNDEB 2024", "FUNDEB 2025", "FUNDEB 2026"):
        assert rotulo not in barra
    assert "FUNDEB 2025" not in texto
    assert "FUNDEB 2026" not in texto
