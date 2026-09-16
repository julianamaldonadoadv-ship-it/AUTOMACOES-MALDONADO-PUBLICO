# -*- coding: utf-8 -*-
"""
Gera o papel timbrado do escritorio (faixa 2026)
================================================

FONTE VERSIONADA do `DOCS_MODELOS/timbrado_modelo.docx`. O `.docx` e' artefato:
nao editar a mao, editar aqui e regerar.

Por que este modulo existe
--------------------------
Ate 11/09/2026 o quadro de advogados vivia RASTERIZADO dentro de
`timbrado-maldonado-2026.jpeg`. Consequencia pratica: incluir advogado exigia
editar imagem, e por isso CINCO advogados ativos (Josue, Heloisa, Agenor,
Taynara, Ana Sheila) nunca chegaram ao papel - metade da carteira de intimacoes
era tratada por gente que o proprio timbrado nao reconhecia. Descoberto ao
assinar o agravo de um cliente.

E nao era so preguica: a faixa tem 4,38 cm de altura e as 8 linhas antigas
ocupavam 2,97 cm, a 0,37 cm por linha. Com 12 nomes o bloco pediria 4,44 cm,
mais do que a faixa inteira. Editar a imagem simplesmente NAO CABIA.

A solucao foi separar arte de dado:
  - `timbrado-2026-friso.png`  (1682x76)  friso dourado e a aba preta, largura total
  - `timbrado-2026-logo.png`   (1050x278) a logo, com o branco ao redor
  - o quadro de advogados virou TEXTO, lido de `config/equipe.py`

Ganhos: incluir advogado e' uma linha de dado; nome e OAB ficam pesquisaveis e
copiaveis no PJe (mesma doutrina do `visual_law`: nada e' imagem); e a
entrelinha passa a ser controlavel, o que e' o que permite caber mais nomes.

Geometria (medida na peca real, nao inventada - ver skill `timbrado`)
--------------------------------------------------------------------
    pagina           A4, 21,0 x 29,7 cm
    faixa            y 1,27 -> 5,65 cm, largura 20,83 cm (borda a borda)
    margens          sup 5,33 | esq 2,54 | dir 2,44 | inf 2,5 cm
    rodape           vazio

A faixa e' mais larga que a area util, entao cabecalho e tabela levam RECUO
NEGATIVO igual as margens. Sem isso a arte fica confinada entre as margens e
sai estreita e descentralizada - era o defeito do timbrado de 2024.
"""
import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "config"))
import equipe  # noqa: E402

ASSETS = os.path.join(BASE, ".claude", "skills", "timbrado", "assets")
FRISO = os.path.join(ASSETS, "timbrado-2026-friso.png")
LOGO = os.path.join(ASSETS, "timbrado-2026-logo.png")

LARGURA_FAIXA = 20.83     # cm, borda a borda
LARGURA_LOGO = 13.00      # cm, 1050/1682 da faixa
ALTURA_FRISO = 0.94       # cm, 76/1682 da largura
ALTURA_LOGO = 3.44        # cm, 278/1050 da largura da logo
FONTE_QUADRO = "Arial"    # o corpo e' Arial Narrow; a faixa sempre foi Arial
CORPO_QUADRO = 8.5        # pt
ENTRELINHA_QUADRO = 9.2   # pt, exata
ESPACO_ANTES_QUADRO = 4   # pt, o texto original comeca 0,35 cm abaixo do friso
RECUO_ESQ = -2.54         # cm
RECUO_DIR = -2.44         # cm

# Quanto o quadro de nomes pode crescer sem mexer no resto da peca
# ---------------------------------------------------------------
# Quem manda na altura da faixa e' a LOGO (3,44 cm), nao os nomes: ela esta
# na mesma linha da tabela. Enquanto a coluna de nomes for mais baixa que a
# logo, incluir advogado nao desloca UMA LINHA do corpo - a faixa continua
# indo de 1,27 a 5,65 cm, que e' a medida da peca real protocolada.
#
# Passando disso, a tabela cresce, o cabecalho empurra o corpo para baixo e
# TODA peca do escritorio muda de diagramacao (a margem superior de 5,33 cm
# ja' e' menor que a faixa: e o cabecalho que fixa onde o texto comeca).
# Por isso `_conferir_altura` e' erro, nao aviso: o estouro sairia silencioso
# no .docx e so' apareceria no protocolo.
#
# Com 9,2 pt de entrelinha cabem 10 nomes (3,39 cm). Para o 11o: reduzir a
# entrelinha ou quebrar o quadro em duas colunas.
ALTURA_MAXIMA_QUADRO = ALTURA_LOGO


def altura_quadro(quantidade):
    """Altura em cm que o quadro de advogados ocupa com N nomes."""
    pontos = ESPACO_ANTES_QUADRO + quantidade * ENTRELINHA_QUADRO
    return pontos * 2.54 / 72.0


def _conferir_altura(advogados):
    altura = altura_quadro(len(advogados))
    if altura > ALTURA_MAXIMA_QUADRO:
        raise ValueError(
            "quadro de advogados nao cabe na faixa: %d nomes ocupam %.2f cm e o "
            "limite e' %.2f cm (altura da logo). Incluir mais um nome empurraria "
            "o corpo de toda peca para baixo. Reduza ENTRELINHA_QUADRO ou quebre "
            "o quadro em duas colunas." % (len(advogados), altura, ALTURA_MAXIMA_QUADRO))
    return altura


def _sem_bordas_nem_margens(tabela):
    """Tabela invisivel e colada na borda: a arte tem que encostar no papel."""
    tblPr = tabela._tbl.tblPr
    bordas = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + lado)
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        bordas.append(el)
    tblPr.append(bordas)
    margens = OxmlElement("w:tblCellMar")
    for lado in ("top", "left", "bottom", "right"):
        el = OxmlElement("w:" + lado)
        el.set(qn("w:w"), "0")
        el.set(qn("w:type"), "dxa")
        margens.append(el)
    tblPr.append(margens)


def _recuo_negativo_tabela(tabela, cm):
    """Puxa a tabela para fora da area util, como o cabecalho faz com a faixa."""
    ind = OxmlElement("w:tblInd")
    ind.set(qn("w:w"), str(int(round(cm * 566.93))))
    ind.set(qn("w:type"), "dxa")
    tabela._tbl.tblPr.append(ind)


def _paragrafo_colado(container):
    p = container.add_paragraph() if hasattr(container, "add_paragraph") else container
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.0
    return p


def gerar(destino=None, advogados=None):
    advogados = advogados or equipe.ADVOGADOS_TIMBRADO
    destino = destino or os.path.join(BASE, "DOCS_MODELOS", "timbrado_modelo.docx")
    _conferir_altura(advogados)

    doc = Document()
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.top_margin, s.bottom_margin = Cm(5.33), Cm(2.5)
    s.left_margin, s.right_margin = Cm(2.54), Cm(2.44)
    s.header_distance = Cm(1.27)
    s.footer_distance = Cm(1.25)

    # corpo do modelo: vazio, e' so a folha
    for p in list(doc.paragraphs):
        p._element.getparent().remove(p._element)

    header = s.header
    for p in list(header.paragraphs):
        p._element.getparent().remove(p._element)

    # 1) friso: largura total, encostado nas duas bordas
    p_friso = _paragrafo_colado(header)
    p_friso.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_friso.paragraph_format.left_indent = Cm(RECUO_ESQ)
    p_friso.paragraph_format.right_indent = Cm(RECUO_DIR)
    p_friso.add_run().add_picture(FRISO, width=Cm(LARGURA_FAIXA))

    # 2) logo a esquerda, quadro de advogados a direita
    t = header.add_table(rows=1, cols=2, width=Cm(LARGURA_FAIXA))
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    _sem_bordas_nem_margens(t)
    _recuo_negativo_tabela(t, RECUO_ESQ)

    cel_logo, cel_nomes = t.rows[0].cells
    cel_logo.width = Cm(LARGURA_LOGO)
    cel_nomes.width = Cm(LARGURA_FAIXA - LARGURA_LOGO)

    p_logo = _paragrafo_colado(cel_logo.paragraphs[0])
    p_logo.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_logo.add_run().add_picture(LOGO, width=Cm(LARGURA_LOGO))

    primeiro = True
    for nome, oab in advogados:
        p = cel_nomes.paragraphs[0] if primeiro else cel_nomes.add_paragraph()
        p = _paragrafo_colado(p)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        pf = p.paragraph_format
        pf.line_spacing = Pt(ENTRELINHA_QUADRO)
        if primeiro:
            pf.space_before = Pt(ESPACO_ANTES_QUADRO)
        # alinha a direita no mesmo ponto em que a arte antiga terminava
        pf.right_indent = Cm(0.30)
        r = p.add_run("%s - %s" % (nome, oab))
        r.font.name = FONTE_QUADRO
        r.font.size = Pt(CORPO_QUADRO)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
        primeiro = False

    doc.save(destino)
    return destino


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    caminho = gerar(alvo)
    print("timbrado gerado:", caminho)
    print("advogados no quadro: %d (%.2f cm de %.2f cm da faixa)"
          % (len(equipe.ADVOGADOS_TIMBRADO),
             altura_quadro(len(equipe.ADVOGADOS_TIMBRADO)), ALTURA_MAXIMA_QUADRO))
    if equipe.ADVOGADOS_SEM_OAB:
        print("fora do quadro (OAB pendente):")
        for nome, uid in equipe.ADVOGADOS_SEM_OAB:
            print("   %s (ADVBOX %s)" % (nome, uid))
