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
assinar o agravo do Sr. Cliente V.

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
    faixa            comeca em y 1,27 cm, largura 20,83 cm (borda a borda)
    margens          sup 7,37 (calculada) | esq 2,54 | dir 2,44 | inf 2,5 cm
                     (sup era 5,33 ate 15/09/2026: ver "Layout do quadro")
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
# A logo original tem 13 cm de largura, mas o desenho termina aos 8,4 cm: o resto
# e' branco. O recorte (x 0-720 de 1050 px, altura inteira) tira so' esse branco
# e deixa a celula dos nomes mais larga. Mesma escala, mesma altura.
LOGO = os.path.join(ASSETS, "timbrado-2026-logo-recortada.png")

LARGURA_FAIXA = 20.83     # cm, borda a borda
LARGURA_LOGO = 8.91       # cm, 720 px na escala da arte (1050 px = 13 cm)
ALTURA_FRISO = 0.94       # cm, 76/1682 da largura
ALTURA_LOGO = 3.44        # cm, 278 px na mesma escala
DISTANCIA_CABECALHO = 1.27  # cm, do topo do papel ao friso
FONTE_QUADRO = "Arial"    # o corpo e' Arial Narrow; a faixa sempre foi Arial
CORPO_QUADRO = 9          # pt
ENTRELINHA_QUADRO = 11    # pt, exata
RECUO_DIR_QUADRO = 0.30   # cm, o texto termina onde a arte antiga terminava
CAPACIDADE_QUADRO = 12    # nomes que cabem sem mexer na margem superior
FOLGA_CORPO = 0.50        # cm, entre o ultimo nome e a primeira linha do corpo
RECUO_ESQ = -2.54         # cm
RECUO_DIR = -2.44         # cm

# Layout do quadro (Dra. Juliana, 16/09/2026)
# -------------------------------------------
# Ate 15/09/2026: uma coluna, 8,5 pt, e a faixa presa a altura da logo (3,44 cm),
# o que limitava o quadro a 10 nomes. Com o 11o a letra caiu para 7,5 pt e ficou
# miuda; duas colunas foram testadas e recusadas. Decisao: UMA coluna, preta e
# em negrito como sempre foi, e o CABECALHO CRESCE para a letra voltar a 9 pt.
#   - Dr. Renan primeiro, os demais em ORDEM ALFABETICA (a ordem vem do codigo,
#     nao da lista: advogado novo cai no lugar certo sozinho);
#   - a margem superior e' calculada para CAPACIDADE_QUADRO nomes, nao para os
#     de hoje: incluir advogado ate' esse numero nao desloca uma linha do corpo.
#     Passando dele, `_conferir_altura` falha: o estouro empurraria o corpo de
#     toda peca para baixo em silencio.
ALTURA_MAXIMA_QUADRO = CAPACIDADE_QUADRO * ENTRELINHA_QUADRO * 2.54 / 72.0
MARGEM_SUPERIOR = round(DISTANCIA_CABECALHO + ALTURA_FRISO + ALTURA_MAXIMA_QUADRO
                        + FOLGA_CORPO, 2)


def ordenar_quadro(advogados):
    """Dr. Renan primeiro; os demais em ordem alfabetica (sem acento/caixa)."""
    import unicodedata

    def chave(item):
        return unicodedata.normalize("NFKD", item[0]).encode("ascii", "ignore").decode().lower()

    primeiro = [a for a in advogados if a[0].startswith("Renan")]
    return primeiro + sorted([a for a in advogados if a not in primeiro], key=chave)


def altura_quadro(quantidade):
    """Altura em cm que o quadro de advogados ocupa com N nomes."""
    return quantidade * ENTRELINHA_QUADRO * 2.54 / 72.0


def _conferir_altura(advogados):
    altura = altura_quadro(len(advogados))
    if altura > ALTURA_MAXIMA_QUADRO:
        raise ValueError(
            "quadro de advogados nao cabe na faixa: %d nomes ocupam %.2f cm e o "
            "limite e' %.2f cm (%d nomes). Incluir mais um nome empurraria o corpo "
            "de toda peca para baixo. Aumente CAPACIDADE_QUADRO (a margem superior "
            "acompanha) ou reduza ENTRELINHA_QUADRO." % (len(advogados), altura, ALTURA_MAXIMA_QUADRO, CAPACIDADE_QUADRO))
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


def _grade_fixa(tabela, larguras_cm):
    """Largura das colunas na grade e layout fixo.

    So' a largura da celula nao basta: o Google Docs le a grade (`tblGrid`), e
    com a grade dividida por igual cortava a logo e quebrava os nomes em duas
    linhas.
    """
    for col, largura in zip(tabela._tbl.tblGrid.findall(qn("w:gridCol")), larguras_cm):
        col.set(qn("w:w"), str(int(round(largura * 566.93))))
    tblPr = tabela._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)


def _fonte_quadro(run, negrito, cor):
    run.font.name = FONTE_QUADRO
    run.font.size = Pt(CORPO_QUADRO)
    run.font.bold = negrito
    run.font.color.rgb = cor
    rfonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    rfonts.set(qn("w:cs"), FONTE_QUADRO)


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
    s.top_margin, s.bottom_margin = Cm(MARGEM_SUPERIOR), Cm(2.5)
    s.left_margin, s.right_margin = Cm(2.54), Cm(2.44)
    s.header_distance = Cm(DISTANCIA_CABECALHO)
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

    # 2) logo a esquerda, quadro de advogados a direita, em uma coluna
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    t = header.add_table(rows=1, cols=2, width=Cm(LARGURA_FAIXA))
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    _sem_bordas_nem_margens(t)
    _recuo_negativo_tabela(t, RECUO_ESQ)

    cel_logo, cel_nomes = t.rows[0].cells
    larguras = [LARGURA_LOGO, LARGURA_FAIXA - LARGURA_LOGO]
    cel_logo.width, cel_nomes.width = Cm(larguras[0]), Cm(larguras[1])
    _grade_fixa(t, larguras)
    # o quadro e' mais alto que a logo: ela fica centrada na altura dele
    cel_logo.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    p_logo = _paragrafo_colado(cel_logo.paragraphs[0])
    p_logo.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_logo.add_run().add_picture(LOGO, width=Cm(LARGURA_LOGO))

    for k, (nome, oab) in enumerate(ordenar_quadro(advogados)):
        p = _paragrafo_colado(cel_nomes.paragraphs[0] if k == 0 else cel_nomes.add_paragraph())
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.line_spacing = Pt(ENTRELINHA_QUADRO)
        p.paragraph_format.right_indent = Cm(RECUO_DIR_QUADRO)
        r = p.add_run("%s - %s" % (nome, oab))
        _fonte_quadro(r, negrito=True, cor=RGBColor(0x00, 0x00, 0x00))

    doc.save(destino)
    return destino


# --------------------------------------------------------------------------
# Modelo para os advogados (distribuicao)
# --------------------------------------------------------------------------
# O `timbrado_modelo.docx` e' a folha em branco que a AUTOMACAO usa. Os
# advogados precisam de outra coisa: abrir no Word e escrever a peca sem
# refazer a formatacao na mao. Por isso este modelo leva as regras da skill
# `timbrado` como ESTILOS do Word (galeria "Estilos"), mais um esqueleto de
# peca com os campos a preencher em amarelo. Sai em .docx e em .dotx (o .dotx,
# aberto com dois cliques, cria um documento novo e preserva o modelo).
#
# Nao ha' travessao em nenhum texto daqui (regra de 14/09/2026). Caixa alta vai
# escrita no texto, nao como formatacao: o Google Docs troca "todas maiusculas"
# por versalete, e parte da equipe abre o .docx por la'.
NOME_MODELO_ADVOGADOS = "TIMBRADO MALDONADO ADVOGADOS 2026"
FONTE_CORPO = "Arial Narrow"


def _fonte(estilo, tamanho, negrito=None, italico=None):
    f = estilo.font
    f.name = FONTE_CORPO
    f.size = Pt(tamanho)
    f.color.rgb = RGBColor(0x00, 0x00, 0x00)
    if negrito is not None:
        f.bold = negrito
    if italico is not None:
        f.italic = italico
    # sem isto o Word usa a fonte do tema em texto com acento/leste asiatico
    rpr = estilo.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for att in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(att), FONTE_CORPO)


def _estilo(doc, nome, tamanho, alinhamento, entrelinha, antes=0, depois=6,
            negrito=None, italico=None, recuo_esq=None,
            manter_com_proximo=False):
    from docx.enum.style import WD_STYLE_TYPE
    est = doc.styles.add_style(nome, WD_STYLE_TYPE.PARAGRAPH)
    est.base_style = doc.styles["Normal"]
    est.quick_style = True
    _fonte(est, tamanho, negrito, italico)
    pf = est.paragraph_format
    pf.alignment = alinhamento
    pf.line_spacing = entrelinha
    pf.space_before = Pt(antes)
    pf.space_after = Pt(depois)
    pf.keep_with_next = manter_com_proximo
    if recuo_esq is not None:
        pf.left_indent = Cm(recuo_esq)
    return est


def _linha(doc, estilo, partes):
    """partes: texto simples ou (texto, 'campo'|'negrito'). Campo sai em amarelo."""
    from docx.enum.text import WD_COLOR_INDEX
    p = doc.add_paragraph(style=estilo)
    for parte in partes:
        texto, tipo = (parte, None) if isinstance(parte, str) else parte
        r = p.add_run(texto)
        if tipo == "campo":
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        elif tipo == "negrito":
            r.font.bold = True
    return p


def _virar_dotx(origem, destino):
    """O .dotx e' o mesmo pacote com outro content type na parte principal."""
    import zipfile
    doc_ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
    dot_ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
    with zipfile.ZipFile(origem) as zin, \
            zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            dados = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                dados = dados.replace(doc_ct.encode(), dot_ct.encode())
            zout.writestr(item, dados)


def gerar_modelo_advogados(pasta=None, advogados=None):
    pasta = pasta or os.path.join(BASE, "DOCS_MODELOS")
    base = os.path.join(pasta, NOME_MODELO_ADVOGADOS)
    gerar(base + ".docx", advogados)          # mesma faixa, mesmas margens

    doc = Document(base + ".docx")
    normal = doc.styles["Normal"]
    _fonte(normal, 12)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)

    J, C, E = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
    endereco = _estilo(doc, "Maldonado Endereçamento", 12, C, 1.5, depois=36,
                       negrito=True)
    titulo_acao = _estilo(doc, "Maldonado Título da Peça", 12, C, 1.5, antes=12,
                          depois=12, negrito=True,
                          manter_com_proximo=True)
    titulo = _estilo(doc, "Maldonado Título", 12, E, 1.5, antes=12, depois=6,
                     negrito=True, manter_com_proximo=True)
    subtitulo = _estilo(doc, "Maldonado Subtítulo", 12, E, 1.5, antes=6,
                        depois=6, negrito=True, manter_com_proximo=True)
    corpo = normal
    juris = _estilo(doc, "Maldonado Jurisprudência", 10, J, 1.15, antes=4,
                    depois=2, italico=True, recuo_esq=4)
    fonte_j = _estilo(doc, "Maldonado Fonte da Jurisprudência", 10, C, 1.15,
                      depois=12, negrito=True, italico=True)
    citacao = _estilo(doc, "Maldonado Citação Legal", 10, J, 1.15, antes=4,
                      depois=10, recuo_esq=4)
    centro = _estilo(doc, "Maldonado Centralizado", 12, C, 1.5)
    assin = _estilo(doc, "Maldonado Assinatura", 12, C, 1.0, depois=0,
                    negrito=True)
    assin_oab = _estilo(doc, "Maldonado Assinatura OAB", 12, C, 1.0, depois=18)

    campo = lambda t: (t, "campo")  # noqa: E731

    _linha(doc, endereco, ["EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DE DIREITO DA ",
                           campo("[__]"), " VARA CÍVEL DA COMARCA DE ",
                           campo("[COMARCA/UF]")])
    _linha(doc, corpo, ["Processo nº ", campo("[0000000-00.0000.0.00.0000]")])
    _linha(doc, corpo, [campo("[NOME DO CLIENTE]"),
                        ", já qualificado(a) nos autos em epígrafe, por seus advogados que "
                        "esta subscrevem, vem, respeitosamente, à presença de Vossa Excelência, "
                        "apresentar"])
    _linha(doc, titulo_acao, [campo("[NOME DA PEÇA]")])
    _linha(doc, corpo, ["em face de ", campo("[PARTE ADVERSA]"),
                        ", pelos fatos e fundamentos a seguir expostos."])

    _linha(doc, titulo, ["I. DOS FATOS"])
    _linha(doc, corpo, [campo("[Texto.]")])
    _linha(doc, titulo, ["II. DO DIREITO"])
    _linha(doc, subtitulo, ["II.1. ", campo("[Subtópico]")])
    _linha(doc, corpo, [campo("[Texto.]")])
    _linha(doc, citacao, [campo("[Transcrição do dispositivo legal, quando houver.]")])
    _linha(doc, corpo, ["Nesse sentido:"])
    _linha(doc, juris, [campo("[Ementa transcrita literalmente, conferida no inteiro teor.]")])
    _linha(doc, fonte_j, [campo("[TRIBUNAL, Classe e nº, Relator(a), julgado em dd/mm/aaaa]")])
    _linha(doc, titulo, ["III. DOS PEDIDOS"])
    _linha(doc, corpo, ["Ante o exposto, requer:"])
    _linha(doc, corpo, ["a) ", campo("[pedido]"), ";"])
    _linha(doc, corpo, ["b) ", campo("[pedido]"), "."])
    _linha(doc, corpo, ["Nestes termos, pede deferimento."])
    _linha(doc, centro, ["Porto Velho/RO, ", campo("[dia] de [mês] de [ano]"), "."])
    doc.paragraphs[-1].paragraph_format.space_after = Pt(36)

    _linha(doc, assin, ["RENAN GOMES MALDONADO DE JESUS"])
    _linha(doc, assin_oab, ["OAB/RO 5.769"])
    _linha(doc, assin, [campo("[NOME FORENSE COMPLETO DO(A) ADVOGADO(A)]")])
    _linha(doc, assin_oab, [campo("[OAB/UF nº]")])

    doc.core_properties.title = NOME_MODELO_ADVOGADOS
    doc.core_properties.author = "Maldonado Advogados"
    doc.save(base + ".docx")
    _virar_dotx(base + ".docx", base + ".dotx")
    return base + ".docx", base + ".dotx"


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    caminho = gerar(alvo)
    print("timbrado gerado:", caminho)
    if alvo is None:
        for c in gerar_modelo_advogados():
            print("modelo para os advogados:", c)
    print("margem superior: %.2f cm" % MARGEM_SUPERIOR)
    print("advogados no quadro: %d (%.2f cm de %.2f cm reservados)"
          % (len(equipe.ADVOGADOS_TIMBRADO),
             altura_quadro(len(equipe.ADVOGADOS_TIMBRADO)), ALTURA_MAXIMA_QUADRO))
    if equipe.ADVOGADOS_SEM_OAB:
        print("fora do quadro (OAB pendente):")
        for nome, uid in equipe.ADVOGADOS_SEM_OAB:
            print("   %s (ADVBOX %s)" % (nome, uid))
