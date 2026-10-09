"""Gera RELATORIO.pdf em A4 retrato, no formato de artigo."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ANALISE = Path(__file__).resolve().parent
MD = ANALISE / "RELATORIO.md"
PDF = ANALISE / "RELATORIO.pdf"

import matplotlib

FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuBold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuItalic", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("Serif", str(FONT_DIR / "DejaVuSerif.ttf")))
pdfmetrics.registerFont(TTFont("SerifBold", str(FONT_DIR / "DejaVuSerif-Bold.ttf")))
pdfmetrics.registerFont(TTFont("SerifItalic", str(FONT_DIR / "DejaVuSerif-Italic.ttf")))

PAGE = A4
MARGIN = 18 * mm
AZUL = colors.HexColor("#1f4a63")
AZUL_CLARO = colors.HexColor("#eef3f6")
CREME = colors.HexColor("#f7f4ee")
LINHA = colors.HexColor("#b8c4cc")
CINZA = colors.HexColor("#444444")


def estilos():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        "Instituicao", fontName="DejaVu", fontSize=8, leading=11,
        textColor=AZUL, alignment=TA_CENTER, spaceAfter=2, tracking=0.6,
    ))
    ss.add(ParagraphStyle(
        "CapaTitulo", fontName="SerifBold", fontSize=13.5, leading=17.5,
        textColor=AZUL, alignment=TA_CENTER, spaceAfter=8, spaceBefore=4,
    ))
    ss.add(ParagraphStyle(
        "CapaSub", fontName="SerifItalic", fontSize=9, leading=12,
        textColor=CINZA, alignment=TA_CENTER, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        "SecaoResumo", fontName="SerifBold", fontSize=10, leading=13,
        textColor=AZUL, spaceBefore=8, spaceAfter=4, alignment=TA_LEFT,
    ))
    ss.add(ParagraphStyle(
        "Resumo", fontName="Serif", fontSize=8.7, leading=12,
        alignment=TA_JUSTIFY, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        "H1doc", fontName="SerifBold", fontSize=11.5, leading=15,
        textColor=AZUL, spaceBefore=11, spaceAfter=5,
    ))
    ss.add(ParagraphStyle(
        "H2doc", fontName="SerifBold", fontSize=10, leading=13,
        textColor=colors.HexColor("#3b6d8c"), spaceBefore=8, spaceAfter=3,
    ))
    ss.add(ParagraphStyle(
        "Corpo", fontName="Serif", fontSize=9.4, leading=13.4,
        alignment=TA_JUSTIFY, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        "Aviso", fontName="SerifItalic", fontSize=8, leading=11,
        textColor=colors.HexColor("#6a3a12"), alignment=TA_JUSTIFY, spaceAfter=8, spaceBefore=2,
    ))
    ss.add(ParagraphStyle(
        "Celula", fontName="DejaVu", fontSize=6.4, leading=8.2, alignment=TA_LEFT,
    ))
    ss.add(ParagraphStyle(
        "CelulaCab", fontName="DejaVuBold", fontSize=6.2, leading=8,
        textColor=colors.white, alignment=TA_LEFT,
    ))
    ss.add(ParagraphStyle(
        "Caption", fontName="SerifItalic", fontSize=8, leading=10.5,
        alignment=TA_JUSTIFY, textColor=CINZA, spaceBefore=2, spaceAfter=9,
    ))
    ss.add(ParagraphStyle(
        "TabCaption", fontName="SerifBold", fontSize=8, leading=10.5,
        alignment=TA_LEFT, textColor=AZUL, spaceBefore=7, spaceAfter=3,
    ))
    ss.add(ParagraphStyle(
        "ItemLista", fontName="Serif", fontSize=8.8, leading=12.2, alignment=TA_JUSTIFY,
    ))
    ss.add(ParagraphStyle(
        "Tese", fontName="SerifItalic", fontSize=9.2, leading=13,
        alignment=TA_JUSTIFY, textColor=AZUL, leftIndent=8, rightIndent=8,
        spaceBefore=4, spaceAfter=8,
    ))
    return ss


def md_inline(texto: str) -> str:
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", texto)
    texto = re.sub(r"`([^`]+)`", r"<i>\1</i>", texto)
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", texto)
    return texto


def parse_md(path: Path):
    blocos = []
    linhas = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha.strip():
            i += 1
            continue
        if linha.startswith("![") and "](" in linha:
            m = re.search(r"!\[([^\]]*)\]\(([^)]+)\)", linha)
            if m:
                blocos.append(("img", m.group(2), m.group(1)))
        elif linha.startswith("# "):
            blocos.append(("h1", linha[2:].strip()))
        elif linha.startswith("## "):
            blocos.append(("h2", linha[3:].strip()))
        elif linha.startswith("### "):
            blocos.append(("h3", linha[4:].strip()))
        elif linha.startswith("|"):
            tab = []
            while i < len(linhas) and linhas[i].startswith("|"):
                raw = [c.strip() for c in linhas[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in raw):
                    tab.append(raw)
                i += 1
            blocos.append(("table", tab))
            continue
        elif linha.startswith("- "):
            itens = []
            while i < len(linhas) and linhas[i].startswith("- "):
                itens.append(linhas[i][2:].strip())
                i += 1
            blocos.append(("ul", itens))
            continue
        elif linha.startswith(">"):
            blocos.append(("quote", linha.lstrip("> ").strip()))
        else:
            blocos.append(("p", linha.strip()))
        i += 1
    return blocos


CABECALHOS = {
    "regiao": "Região",
    "uf": "UF",
    "municipio": "Município",
    "ibge": "IBGE",
    "alunos_movidos": "Alunos",
    "base_mi": "Baseline (R$ mi)",
    "delta_mi": "Δ R$ mi",
    "delta_r_percentual": "Δ %",
    "delta_r": "Δ R$",
    "total_matriculas": "Matrículas",
    "recursos_fundeb": "FUNDEB",
    "complemento_uniao": "União",
    "delta_alvo": "Δ alvo",
    "delta_demais_mun": "Δ demais mun.",
    "delta_ente_estadual": "Δ ente est.",
    "delta_uf_total": "Δ UF",
    "n_prejudicados": "Mun. −",
}


def rotulo_cab(c: str) -> str:
    return CABECALHOS.get(c, c)


def tabela(linhas, styles):
    cab_raw = [rotulo_cab(c) for c in linhas[0]]
    cab = [Paragraph(md_inline(c), styles["CelulaCab"]) for c in cab_raw]
    data = [cab] + [[Paragraph(md_inline(c), styles["Celula"]) for c in r] for r in linhas[1:]]
    ncols = max(len(r) for r in data)
    for r in data:
        while len(r) < ncols:
            r.append(Paragraph("", styles["Celula"]))
    largura = PAGE[0] - 2 * MARGIN
    pesos = []
    for j in range(ncols):
        nome = linhas[0][j].lower() if j < len(linhas[0]) else ""
        if nome in {"municipio", "regiao"}:
            pesos.append(2.2)
        elif nome in {"transformacao"}:
            pesos.append(3.0)
        elif nome in {"uf", "ibge"}:
            pesos.append(0.8)
        elif "percentual" in nome or nome in {"n_prejudicados"}:
            pesos.append(1.0)
        else:
            pesos.append(1.6)
    col_w = [largura * p / sum(pesos) for p in pesos]
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, AZUL_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.25, LINHA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.2),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
    ]))
    return t


def figura(rel, caption, styles, n_fig: int):
    path = ANALISE / rel
    if not path.exists():
        return [Paragraph(f"[figura ausente: {rel}]", styles["Caption"])]
    img = Image(str(path))
    max_w = PAGE[0] - 2 * MARGIN
    max_h = 108 * mm
    sc = min(max_w / img.imageWidth, max_h / img.imageHeight, 1)
    img.drawWidth = img.imageWidth * sc
    img.drawHeight = img.imageHeight * sc
    img.hAlign = "CENTER"
    cap = Paragraph(f"<b>Figura {n_fig}.</b> {md_inline(caption)}", styles["Caption"])
    return [KeepTogether([Spacer(1, 3), img, cap])]


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(AZUL)
    canvas.rect(0, PAGE[1] - 9 * mm, PAGE[0], 9 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("DejaVu", 7)
    canvas.drawString(MARGIN, PAGE[1] - 6 * mm, "Artigo · composição de matrículas e FUNDEB · cinco regiões")
    canvas.drawRightString(PAGE[0] - MARGIN, PAGE[1] - 6 * mm, "IFCE")
    canvas.setStrokeColor(LINHA)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 11 * mm, PAGE[0] - MARGIN, 11 * mm)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.setFont("DejaVu", 7)
    canvas.drawString(MARGIN, 6.5 * mm, "Estudo contrafactual. Não é recomendação para reclassificar alunos.")
    canvas.drawRightString(PAGE[0] - MARGIN, 6.5 * mm, f"{doc.page}")
    canvas.restoreState()


def _eh_caption_tabela(texto: str) -> bool:
    t = texto.lstrip("*").strip()
    return t.startswith("Tabela ")


def construir() -> Path:
    styles = estilos()
    blocos = parse_md(MD)
    titulo = next((b[1] for b in blocos if b[0] == "h1"), "Composição das matrículas e FUNDEB")

    story = [
        Spacer(1, 3 * mm),
        Paragraph("INSTITUTO FEDERAL DO CEARÁ  ·  SIMULADOR FUNDEB", styles["Instituicao"]),
        HRFlowable(width="100%", thickness=0.6, color=AZUL, spaceAfter=4 * mm, spaceBefore=1 * mm),
        Paragraph(md_inline(titulo), styles["CapaTitulo"]),
        Paragraph("Artigo de resultados computacionais  ·  exercícios 2024, 2025 e 2026", styles["CapaSub"]),
        Paragraph("Dez municípios  ·  dez estados  ·  cinco regiões  ·  motor <i>simula_fundeb</i>", styles["CapaSub"]),
        Spacer(1, 2 * mm),
        Paragraph(
            "Os números foram lidos dos CSVs em <i>analises/fundeb_regioes/resultados/</i>. "
            "O experimento mede incentivos implícitos nos fatores de ponderação. "
            "<b>Não é recomendação para reclassificar alunos.</b>",
            styles["Aviso"],
        ),
    ]

    n_fig = 0
    secoes_resumo = {"resumo", "abstract", "palavras-chave", "keywords"}
    em_resumo = False

    for bloco in blocos:
        tipo = bloco[0]
        if tipo == "h1":
            continue
        if tipo == "h2":
            nome = bloco[1]
            em_resumo = nome.lower() in secoes_resumo
            estilo = styles["SecaoResumo"] if em_resumo else styles["H1doc"]
            if not em_resumo:
                story.append(CondPageBreak(40 * mm))
            story.append(Paragraph(md_inline(nome), estilo))
        elif tipo == "h3":
            story.append(Paragraph(md_inline(bloco[1]), styles["H2doc"]))
        elif tipo == "p":
            if _eh_caption_tabela(bloco[1]):
                story.append(Paragraph(md_inline(bloco[1]), styles["TabCaption"]))
            else:
                estilo_p = styles["Resumo"] if em_resumo else styles["Corpo"]
                story.append(Paragraph(md_inline(bloco[1]), estilo_p))
        elif tipo == "quote":
            story.append(Paragraph(md_inline(bloco[1]), styles["Tese"]))
        elif tipo == "ul":
            story.append(ListFlowable(
                [ListItem(Paragraph(md_inline(i), styles["ItemLista"]), leftIndent=6) for i in bloco[1]],
                bulletType="bullet", start="•", leftIndent=12,
            ))
            story.append(Spacer(1, 3))
        elif tipo == "table" and bloco[1]:
            story.append(KeepTogether([tabela(bloco[1], styles), Spacer(1, 6)]))
        elif tipo == "img":
            n_fig += 1
            story.append(CondPageBreak(70 * mm))
            story.extend(figura(bloco[1], bloco[2], styles, n_fig))

    doc = SimpleDocTemplate(
        str(PDF),
        pagesize=PAGE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=16 * mm,
        bottomMargin=15 * mm,
        title="Composição das matrículas e transferências do FUNDEB",
        author="IFCE — Simulador FUNDEB v2",
        subject="Artigo contrafactual: composição de matrículas e FUNDEB nas cinco regiões",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return PDF


if __name__ == "__main__":
    print(construir())
