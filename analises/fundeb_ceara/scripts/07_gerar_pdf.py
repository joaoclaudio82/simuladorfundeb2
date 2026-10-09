"""Gera RESULTADOS.pdf a partir de RESULTADOS.md e das figuras."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ANALISE = ROOT / "analises" / "fundeb_ceara"
MD = ANALISE / "RESULTADOS.md"
PDF = ANALISE / "RESULTADOS.pdf"
FIG = ANALISE / "figuras"

FONT_DIR = Path(sys.prefix) / "lib" / "python3.12" / "site-packages" / "matplotlib" / "mpl-data" / "fonts" / "ttf"
if not (FONT_DIR / "DejaVuSans.ttf").exists():
    import matplotlib
    FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"

pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuBold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))

PAGE = landscape(A4)
MARGIN = 12 * mm

AZUL = colors.HexColor("#1f4a63")
AZUL_CLARO = colors.HexColor("#e8eef2")
CINZA = colors.HexColor("#f4f4f4")
LINHA = colors.HexColor("#b8c4cc")


def estilos():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        "CapaTitulo", fontName="DejaVuBold", fontSize=18, leading=22,
        textColor=AZUL, alignment=TA_CENTER, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        "CapaSub", fontName="DejaVu", fontSize=10, leading=14,
        textColor=colors.HexColor("#333333"), alignment=TA_CENTER, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        "H1doc", fontName="DejaVuBold", fontSize=13, leading=16,
        textColor=AZUL, spaceBefore=12, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        "H2doc", fontName="DejaVuBold", fontSize=11, leading=14,
        textColor=AZUL, spaceBefore=9, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        "H3doc", fontName="DejaVuBold", fontSize=10, leading=13,
        textColor=colors.HexColor("#3b6d8c"), spaceBefore=7, spaceAfter=3,
    ))
    ss.add(ParagraphStyle(
        "Corpo", fontName="DejaVu", fontSize=8.5, leading=12,
        alignment=TA_JUSTIFY, spaceAfter=5,
    ))
    ss.add(ParagraphStyle(
        "Aviso", fontName="DejaVu", fontSize=8.5, leading=12,
        textColor=colors.HexColor("#6a3a12"), backColor=colors.HexColor("#fff6e8"),
        borderPadding=4, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        "Celula", fontName="DejaVu", fontSize=6.2, leading=8, alignment=TA_LEFT,
    ))
    ss.add(ParagraphStyle(
        "CelulaCab", fontName="DejaVuBold", fontSize=6.2, leading=8, alignment=TA_LEFT,
        textColor=colors.white,
    ))
    ss.add(ParagraphStyle(
        "Rodape", fontName="DejaVu", fontSize=7, leading=9,
        textColor=colors.HexColor("#666666"), alignment=TA_CENTER,
    ))
    ss.add(ParagraphStyle(
        "Caption", fontName="DejaVu", fontSize=7.5, leading=10,
        textColor=colors.HexColor("#444444"), alignment=TA_CENTER, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        "ItemLista", fontName="DejaVu", fontSize=8.5, leading=12,
    ))
    return ss


def md_inline(texto: str) -> str:
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = re.sub(r"`([^`]+)`", r"<font face='DejaVu' color='#1f4a63'><i>\1</i></font>", texto)
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", texto)
    return texto


def parse_md(path: Path) -> list[tuple]:
    blocos = []
    linhas = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha.strip():
            i += 1
            continue
        if linha.startswith("# "):
            blocos.append(("h1", linha[2:].strip()))
        elif linha.startswith("## "):
            blocos.append(("h2", linha[3:].strip()))
        elif linha.startswith("### "):
            blocos.append(("h3", linha[4:].strip()))
        elif linha.startswith("**") and linha.endswith("**") and linha.count("**") == 2:
            blocos.append(("h3", linha.strip("*").strip()))
        elif linha.startswith("|"):
            tabela = []
            while i < len(linhas) and linhas[i].startswith("|"):
                raw = [c.strip() for c in linhas[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in raw):
                    tabela.append(raw)
                i += 1
            blocos.append(("table", tabela))
            continue
        elif linha.startswith("- "):
            itens = []
            while i < len(linhas) and linhas[i].startswith("- "):
                itens.append(linhas[i][2:].strip())
                i += 1
            blocos.append(("ul", itens))
            continue
        else:
            blocos.append(("p", linha.strip()))
        i += 1
    return blocos


FIGURAS_POR_SECAO = {
    "7. Resultados": [
        (FIG / "comparacao_anos_ganho_percentual.png",
         "Comparação entre exercícios — ganho percentual máximo da melhor transição individual."),
        (FIG / "2026" / "01_percentual_delta.png",
         "Gráfico 1 (2026): percentual convertido × Δ recursos FUNDEB, por transformação."),
        (FIG / "2026" / "04_heatmap.png",
         "Gráfico 4 (2026): heatmap município × transformação (melhor Δ%)."),
    ],
    "8. Melhor transformação de cada município": [
        (FIG / "2026" / "02_ganho_percentual.png",
         "Gráfico 2 (2026): ganho percentual máximo por município."),
        (FIG / "2026" / "03_ganho_por_aluno.png",
         "Gráfico 3 (2026): ganho por aluno convertido."),
        (FIG / "2026" / "06_baseline_vs_otimo.png",
         "Gráfico 6 (2026): recursos baseline × ótimo factível."),
    ],
    "11. Impacto sobre os demais municípios": [
        (FIG / "2026" / "05_spillover_ce.png",
         "Gráfico 5 (2026): efeito intraestadual a 50% da melhor transição."),
    ],
    "14. Linearidade e tamanho da rede": [
        (FIG / "2026" / "07_tamanho_vs_ganho.png",
         "Tamanho da rede × ganho percentual máximo (2026)."),
    ],
}


def tabela_flowable(linhas: list[list[str]], styles) -> Table:
    cab = [Paragraph(md_inline(c), styles["CelulaCab"]) for c in linhas[0]]
    corpo = [
        [Paragraph(md_inline(c), styles["Celula"]) for c in row]
        for row in linhas[1:]
    ]
    data = [cab] + corpo
    ncols = max(len(r) for r in data)
    for r in data:
        while len(r) < ncols:
            r.append(Paragraph("", styles["Celula"]))
    largura = PAGE[0] - 2 * MARGIN
    pesos = [max(len(linhas[0][j]) if j < len(linhas[0]) else 4, 4) for j in range(ncols)]
    # colunas de texto longo (transformação, fonte) ganham mais espaço
    for j, nome in enumerate(linhas[0]):
        n = nome.lower()
        if any(k in n for k in ("transform", "origem", "destino", "fonte", "cenario")):
            pesos[j] *= 2
    total = sum(pesos) or 1
    col_w = [largura * p / total for p in pesos]
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVuBold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, AZUL_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.25, LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def figura(path: Path, caption: str, styles) -> list:
    if not path.exists():
        return [Paragraph(f"[Figura ausente: {path.name}]", styles["Caption"])]
    max_w = PAGE[0] - 2 * MARGIN
    max_h = 95 * mm
    img = Image(str(path))
    scale = min(max_w / img.imageWidth, max_h / img.imageHeight, 1)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    img.hAlign = "CENTER"
    return [Spacer(1, 4), img, Paragraph(caption, styles["Caption"])]


def cabecalho_rodape(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(AZUL)
    canvas.rect(0, PAGE[1] - 8 * mm, PAGE[0], 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("DejaVu", 7)
    canvas.drawString(MARGIN, PAGE[1] - 5.5 * mm, "Simulador FUNDEB — estudo contrafactual · Ceará")
    canvas.drawRightString(PAGE[0] - MARGIN, PAGE[1] - 5.5 * mm, "IFCE")
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.setFont("DejaVu", 7)
    canvas.drawString(MARGIN, 6 * mm, "Não é recomendação para reclassificar alunos.")
    canvas.drawRightString(PAGE[0] - MARGIN, 6 * mm, f"Página {doc.page}")
    canvas.restoreState()


def construir() -> Path:
    styles = estilos()
    blocos = parse_md(MD)
    story = []

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "Impacto da composição das matrículas escolares sobre as transferências do FUNDEB",
        styles["CapaTitulo"],
    ))
    story.append(Paragraph(
        "Análise contrafactual de municípios cearenses — resultados computacionais",
        styles["CapaSub"],
    ))
    story.append(Paragraph(
        "Exercícios 2024, 2025 e 2026 · 10 municípios · 12.666 cenários válidos · motor <i>simula_fundeb</i>",
        styles["CapaSub"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Os números deste PDF foram lidos de <i>RESULTADOS.md</i> e dos CSVs em "
        "<i>analises/fundeb_ceara/resultados/</i>. O experimento contrafactual indica "
        "incentivos financeiros implícitos nos fatores de ponderação. "
        "<b>Não se trata de recomendação para reclassificar alunos.</b>",
        styles["Aviso"],
    ))

    secao_atual = ""

    def flush_figuras(nome: str) -> None:
        for path, cap in FIGURAS_POR_SECAO.get(nome, []):
            story.extend(figura(path, cap, styles))

    for tipo, conteudo in blocos:
        if tipo == "h1":
            continue
        if tipo == "h2":
            flush_figuras(secao_atual)
            secao_atual = conteudo
            story.append(Paragraph(md_inline(conteudo), styles["H1doc"]))
        elif tipo == "h3":
            story.append(Paragraph(md_inline(conteudo), styles["H2doc"]))
        elif tipo == "p":
            story.append(Paragraph(md_inline(conteudo), styles["Corpo"]))
        elif tipo == "ul":
            itens = [
                ListItem(Paragraph(md_inline(item), styles["ItemLista"]), leftIndent=8)
                for item in conteudo
            ]
            story.append(ListFlowable(itens, bulletType="bullet", start="•", leftIndent=12))
            story.append(Spacer(1, 3))
        elif tipo == "table" and conteudo:
            story.append(Spacer(1, 2))
            story.append(tabela_flowable(conteudo, styles))
            story.append(Spacer(1, 5))
    flush_figuras(secao_atual)

    def on_page(canvas, doc):
        cabecalho_rodape(canvas, doc)

    doc = SimpleDocTemplate(
        str(PDF),
        pagesize=PAGE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title="Resultados — FUNDEB Ceará (estudo contrafactual)",
        author="IFCE — Simulador FUNDEB v2",
        subject="Análise contrafactual da composição de matrículas e repasses do FUNDEB",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return PDF


if __name__ == "__main__":
    path = construir()
    print(f"PDF gerado: {path} ({path.stat().st_size / 1024:.0f} KB)")
