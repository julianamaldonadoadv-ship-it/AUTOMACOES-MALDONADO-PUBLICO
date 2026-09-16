# -*- coding: utf-8 -*-
"""Componentes de visual law para as peças do escritório (python-docx).

Implementa os "marcadores de estilo obrigatórios" que a skill
`descaracterizacao-mora` (seção 10) já prescrevia mas que nenhuma peça produzida
chegou a usar — cabeçalho de seção em faixa âmbar, badge de força do precedente,
quadro comparativo de institutos, linha do tempo com marcação da fase contratual,
diagrama da cadeia de dois elos e caixas de resultado/alerta.

Três regras de projeto, que valem para qualquer componente novo:

1. **Nada é imagem.** Todo elemento é tabela + texto real, para continuar
   pesquisável no PJe e legível por leitor de tela. Peça com argumento dentro de
   um .png é peça com argumento que o juízo não consegue copiar para a sentença.
2. **Tudo degrada em preto e branco.** A cor é redundante, nunca o único
   portador da informação: o rótulo textual ("VINCULANTE", "NORMALIDADE") diz
   sozinho o que a cor reforça. Metade dos autos é impressa em monocromático.
3. **Nenhum componente calcula nada.** Restrição Absoluta nº 15: quando a tese é
   a ausência de taxa explícita, a célula correspondente diz "não consta" — nunca
   um número derivado pelo escritório, que entregaria ao banco o argumento de que
   a taxa era determinável.

Uso típico, sempre sobre o timbrado (skill `timbrado`):

    from docx import Document
    from OPERACIONAL import visual_law as vl

    doc = Document('DOCS_MODELOS/timbrado_modelo.docx')
    vl.titulo_secao(doc, 'I', 'DA NATUREZA DA AÇÃO')
    vl.paragrafo(doc, 'Trata-se de ação de natureza estritamente declaratória...')
"""

import re

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

# --------------------------------------------------------------------------
# Paleta — a da seção 10 da skill, sem invenção de cor nova
# --------------------------------------------------------------------------
LARANJA = "f6b26b"        # faixa de cabeçalho de seção
LARANJA_ESCURO = "c55a11"  # badge de tribunal estadual
SALMAO = "fce4d6"         # fundo de badge estadual
AZUL = "2e5d9c"           # badge STJ / precedente vinculante
AZUL_CLARO = "dce6f1"     # fundo de badge STJ
VERDE = "e2efda"          # resultado / conclusão do Tema 28
VERMELHO = "ffe6e6"       # alerta documental
CINZA = "f2f2f2"          # cabeçalho de tabela neutra
AMARELO_SUAVE = "fff2cc"  # caixa que amarra o recorte à tese (não é realce de texto)
BORDA = "bfbfbf"

FONTE = "Arial Narrow"
PT_CORPO = 12
PT_TABELA = 10
PT_ROTULO = 9


# --------------------------------------------------------------------------
# Primitivas de baixo nível
# --------------------------------------------------------------------------
def _shade(cell, cor):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), cor)
    cell._tc.get_or_add_tcPr().append(shd)


def _bordas(tabela, cor=BORDA, tamanho=4, estilo="single"):
    tblPr = tabela._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:%s" % lado)
        el.set(qn("w:val"), estilo)
        el.set(qn("w:sz"), str(tamanho))
        el.set(qn("w:color"), cor)
        borders.append(el)
    tblPr.append(borders)


def _sem_bordas(tabela):
    _bordas(tabela, estilo="none", tamanho=0)


def _largura_util(doc):
    s = doc.sections[0]
    return s.page_width - s.left_margin - s.right_margin


def _tabela(doc, linhas, colunas, larguras=None):
    """Tabela de largura total, com bordas discretas e autofit desligado."""
    t = doc.add_table(rows=linhas, cols=colunas)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _bordas(t)
    util = _largura_util(doc)
    if larguras is None:
        larguras = [1.0 / colunas] * colunas
    for linha in t.rows:
        for i, cel in enumerate(linha.cells):
            cel.width = int(util * larguras[i])
    return t


def _escrever(cel, texto, negrito=False, italico=False, tamanho=PT_TABELA,
              cor=None, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, fundo=None):
    """Escreve no primeiro parágrafo da célula. `texto` pode ter '\n'."""
    if fundo:
        _shade(cel, fundo)
    p = cel.paragraphs[0]
    p.alignment = alinhamento
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    for i, bloco in enumerate(str(texto).split("\n")):
        alvo = p if i == 0 else cel.add_paragraph()
        if alvo is not p:
            alvo.alignment = alinhamento
            alvo.paragraph_format.space_before = Pt(0)
            alvo.paragraph_format.space_after = Pt(2)
            alvo.paragraph_format.line_spacing = 1.15
        _runs(alvo, bloco, tamanho=tamanho, negrito=negrito, italico=italico,
              cor=cor)
    return cel


_CAMPO = re.compile(r"(\[\[[^\]]+\]\])")


def _runs(paragrafo, texto, tamanho=PT_CORPO, negrito=False, italico=False,
          cor=None):
    """Escreve o texto num parágrafo, realçando os campos `[[ASSIM]]` em amarelo.

    Campo de modelo é sempre visível: o guard-rail da skill `timbrado` manda que
    todo trecho dependente de documento não lido saia destacado, e o mesmo vale
    para o que ainda precisa ser preenchido pelo advogado. Modelo cujos
    placeholders passam despercebidos é como a peça vai para o protocolo com
    "[[NOME DO CLIENTE]]" no corpo.
    """
    for pedaco in _CAMPO.split(str(texto)):
        if not pedaco:
            continue
        r = paragrafo.add_run(pedaco)
        r.font.name = FONTE
        r.font.size = Pt(tamanho)
        r.bold = negrito
        r.italic = italico
        if cor:
            from docx.shared import RGBColor
            r.font.color.rgb = RGBColor.from_string(cor.upper())
        if _CAMPO.fullmatch(pedaco):
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return paragrafo


def _espaco(doc, pontos=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(pontos)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    # O run precisa ser CRIADO: parágrafo novo não tem run nenhum, e iterar
    # `p.runs` aqui não encolhia coisa alguma — o espaçador herdava 12 pt com
    # entrelinha 1,5 (quase 1 cm cada) e a peça ganhava uma página de vão.
    r = p.add_run("")
    r.font.name = FONTE
    r.font.size = Pt(1)
    return p


# --------------------------------------------------------------------------
# Corpo de texto
# --------------------------------------------------------------------------
def paragrafo(doc, texto, negrito=False, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY):
    """Parágrafo do corpo: Arial Narrow 12, justificado, entrelinha 1,5."""
    p = doc.add_paragraph()
    p.alignment = alinhamento
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(6)
    _runs(p, texto, tamanho=PT_CORPO, negrito=negrito)
    return p


def pendencia(doc, texto):
    """Placeholder destacado em amarelo — guard-rail da skill `timbrado`.

    Trecho que depende de documento não lido nunca é preenchido por suposição.
    """
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run("[PENDENTE] " + texto)
    r.font.name = FONTE
    r.font.size = Pt(PT_TABELA)
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p


# --------------------------------------------------------------------------
# Marcador de print — SEMPRE em par: a imagem e o texto dela
# --------------------------------------------------------------------------
def marcador_print(doc, numero, o_que, transcrever=None):
    """Par de marcadores do recorte: onde entra a IMAGEM e onde entra o TEXTO.

    Regra da Dra. Juliana (10/09/2026): **todo print da peça entra acompanhado
    da transcrição do que ele mostra.** Nunca só a imagem.

    O porquê é prático, não estético. O recorte é a única imagem admitida na peça
    (regra 1 da seção 10ter — "nada é imagem"), porque é prova. Mas imagem, no
    PJe, não é pesquisável nem copiável: o juiz que quiser levar a cláusula para
    o dispositivo não consegue selecioná-la, o leitor de tela não a lê, e a busca
    textual dos autos não a encontra. Se o recorte sair ilegível na conversão
    para PDF ou na impressão monocromática, o argumento morre junto com ele.
    Transcrito ao lado, o conteúdo sobrevive a tudo isso — e o recorte passa a
    fazer o que só ele faz, que é provar que aquilo está mesmo no documento.

    Emite dois marcadores amarelos numerados:

        [[INSERIR PRINT 01 — ...]]      <- slot da imagem
        [[TEXTO DO PRINT 01 — ...]]     <- slot da transcrição

    O primeiro casa com os padrões de `anexos_inicial._PADROES_IMAGEM`, de modo
    que `anexos placeholders` o lista e `anexos inserir` o preenche. O segundo é
    preenchido à mão, com o texto lido no documento — nunca de memória.

    `varrer_marcadores_print(doc)` confere que nenhum dos dois ficou órfão.
    """
    n = "%02d" % int(numero) if not isinstance(numero, str) else numero

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("[[INSERIR PRINT %s: %s]]" % (n, o_que))
    r.font.name = FONTE
    r.font.size = Pt(PT_TABELA)
    r.bold = True
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW

    if transcrever is False:
        # A transcrição já está formatada logo acima, num badge de cláusula
        # contratual que carrega o marcador [[TEXTO DO PRINT nn]]. Emitir outro
        # aqui duplicaria o slot e a varredura acusaria par repetido.
        return p, None

    pt = doc.add_paragraph()
    pt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pt.paragraph_format.line_spacing = 1.15
    pt.paragraph_format.space_after = Pt(8)
    rt = pt.add_run("[[TEXTO DO PRINT %s: %s]]" % (
        n, transcrever or "transcrever literalmente o trecho que o recorte "
                          "mostra, sem grifo do escritório e sem corte que "
                          "altere o sentido"))
    rt.font.name = FONTE
    rt.font.size = Pt(PT_TABELA)
    rt.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p, pt


# O separador depois do número pode ser ":" ou travessão — a Restrição nº 8 baniu
# o travessão do corpo da peça, e o marcador acompanhou.
_RE_PRINT_IMG = re.compile(r'\[\[INSERIR PRINT ([^\s\]:—-]+)', re.I)
_RE_PRINT_TXT = re.compile(r'\[\[TEXTO DO PRINT ([^\s\]:—-]+)', re.I)


def varrer_marcadores_print(doc):
    """Confere que todo print tem o marcador de texto, e vice-versa.

    Print sem transcrição vira prova que o juiz não consegue copiar; transcrição
    sem print vira afirmação sem documento — o mesmo vício que a skill `timbrado`
    persegue ("conforme documento anexo" sem documento). Devolve lista de
    (numero, o_que_falta). Lista vazia = limpo.
    """
    textos = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for linha in t.rows:
            for cel in linha.cells:
                textos.append(cel.text)
    juntos = "\n".join(textos)
    imgs = set(m.group(1) for m in _RE_PRINT_IMG.finditer(juntos))
    txts = set(m.group(1) for m in _RE_PRINT_TXT.finditer(juntos))
    faltas = [(n, "falta [[TEXTO DO PRINT %s]]" % n) for n in sorted(imgs - txts)]
    faltas += [(n, "falta [[INSERIR PRINT %s]]" % n) for n in sorted(txts - imgs)]
    return faltas


# --------------------------------------------------------------------------
# 1. Cabeçalho de seção — faixa âmbar
# --------------------------------------------------------------------------
def titulo_secao(doc, romano, titulo):
    """Faixa âmbar de largura total. Substitui o título em negrito solto.

    Mantém a regra da Dra. Juliana (caixa alta, negrito, margem esquerda,
    numeração romana) e acrescenta só a faixa, que dá ao juízo a régua visual
    para navegar a peça.
    """
    _espaco(doc, 4)
    t = _tabela(doc, 1, 1)
    _bordas(t, cor=LARANJA_ESCURO, tamanho=4)
    _escrever(t.cell(0, 0), "%s. %s" % (romano, titulo.upper()),
              negrito=True, tamanho=PT_CORPO, fundo=LARANJA)
    _espaco(doc, 4)
    return t


# --------------------------------------------------------------------------
# 2. Quadro de identificação — abre a peça
# --------------------------------------------------------------------------
def quadro_identificacao(doc, linhas, titulo="IDENTIFICAÇÃO DA DEMANDA"):
    """Quadro rótulo/valor da abertura.

    Não é enfeite: é onde a linha "Execução conexa" obriga o redator a declarar
    se já existe execução sobre o mesmo título — a verificação que a Restrição
    Absoluta nº 20 exige e cuja omissão custou a reconversão da declaratória em
    embargos nos autos 0000000-00.0000.0.00.0000.
    """
    t = _tabela(doc, len(linhas) + 1, 2, larguras=[0.30, 0.70])
    c = t.cell(0, 0).merge(t.cell(0, 1))
    _escrever(c, titulo, negrito=True, tamanho=PT_TABELA, fundo=LARANJA,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (rotulo, valor) in enumerate(linhas, start=1):
        _escrever(t.cell(i, 0), rotulo, negrito=True, fundo=CINZA)
        _escrever(t.cell(i, 1), valor)
    _espaco(doc)
    return t


# --------------------------------------------------------------------------
# 3. Síntese de abertura — o que o juízo lê primeiro
# --------------------------------------------------------------------------
def sintese_da_controversia(doc, o_que_se_pede, por_que, o_que_nao_se_pede):
    """Caixa de três linhas na primeira página.

    O ganho real não é estético: a linha "o que NÃO se pede" antecipa, antes de
    qualquer fundamentação, a confusão que mais custa caro nessas ações — tratar
    a declaratória como revisional e exigir depósito do incontroverso ou perícia
    de saldo devedor.
    """
    t = _tabela(doc, 4, 2, larguras=[0.26, 0.74])
    c = t.cell(0, 0).merge(t.cell(0, 1))
    _escrever(c, "EM SÍNTESE", negrito=True, fundo=AZUL_CLARO,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (rotulo, valor, fundo) in enumerate([
        ("O que se pede", o_que_se_pede, None),
        ("Por que é devido", por_que, None),
        ("O que NÃO se pede", o_que_nao_se_pede, VERMELHO),
    ], start=1):
        _escrever(t.cell(i, 0), rotulo, negrito=True, fundo=CINZA)
        _escrever(t.cell(i, 1), valor, fundo=fundo)
    _espaco(doc)
    return t


# --------------------------------------------------------------------------
# 4. Linha do tempo — ancora o encargo na normalidade
# --------------------------------------------------------------------------
FASE_NORMALIDADE = ("NORMALIDADE", VERDE)
FASE_INADIMPLEMENTO = ("INADIMPLEMENTO", VERMELHO)


def linha_do_tempo(doc, eventos, titulo="LINHA DO TEMPO DA OPERAÇÃO"):
    """Data | Evento | Fase | Documento.

    A coluna "Fase" é o motivo de existir do componente: o Elo 1 do Tema 28 só
    se configura se o encargo abusivo foi exigido no período de NORMALIDADE, e
    o Passo 6 do Protocolo 4.3-A exige que essa amarração temporal fique
    registrada. Em prosa ela se dilui num parágrafo; aqui o juízo vê a fase de
    cada lançamento sem precisar reconstruir a cronologia.

    `eventos`: lista de (data, evento, fase, documento), com `fase` sendo
    FASE_NORMALIDADE, FASE_INADIMPLEMENTO ou None.
    """
    t = _tabela(doc, len(eventos) + 2, 4, larguras=[0.15, 0.45, 0.20, 0.20])
    c = t.cell(0, 0)
    for j in (1, 2, 3):
        c = c.merge(t.cell(0, j))
    _escrever(c, titulo, negrito=True, fundo=LARANJA,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for j, cab in enumerate(["Data", "Evento", "Fase contratual", "Documento"]):
        _escrever(t.cell(1, j), cab, negrito=True, fundo=CINZA,
                  alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (data, evento, fase, documento) in enumerate(eventos, start=2):
        _escrever(t.cell(i, 0), data, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        _escrever(t.cell(i, 1), evento)
        if fase:
            rotulo, cor = fase
            _escrever(t.cell(i, 2), rotulo, negrito=True, fundo=cor,
                      tamanho=PT_ROTULO, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        else:
            _escrever(t.cell(i, 2), "não consta", alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        _escrever(t.cell(i, 3), documento, tamanho=PT_ROTULO,
                  alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    _espaco(doc)
    return t


# --------------------------------------------------------------------------
# 5. Quadro comparativo de institutos — a marca do escritório
# --------------------------------------------------------------------------
def quadro_comparativo(doc, titulo, coluna_a, coluna_b, linhas, linha_erro=None):
    """Contraposição de dois institutos, coluna a coluna.

    O uso canônico é juros compostos × capitalização (Tema 247 / REsp
    973.827/RS). `linha_erro`, quando presente, é destacada em vermelho: é a
    linha "ERRO FATAL" do modelo mestre, que nomeia a confusão que o banco vai
    tentar e a fecha antes que ele a faça.

    `linhas`: lista de (aspecto, valor_a, valor_b).
    """
    total = len(linhas) + (1 if linha_erro else 0)
    t = _tabela(doc, total + 2, 3, larguras=[0.24, 0.38, 0.38])
    c = t.cell(0, 0)
    for j in (1, 2):
        c = c.merge(t.cell(0, j))
    _escrever(c, titulo, negrito=True, fundo=LARANJA,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    _escrever(t.cell(1, 0), "Aspecto", negrito=True, fundo=CINZA,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    _escrever(t.cell(1, 1), coluna_a, negrito=True, fundo=AZUL_CLARO,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    _escrever(t.cell(1, 2), coluna_b, negrito=True, fundo=SALMAO,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    i = 2
    for aspecto, va, vb in linhas:
        _escrever(t.cell(i, 0), aspecto, negrito=True, fundo=CINZA)
        _escrever(t.cell(i, 1), va)
        _escrever(t.cell(i, 2), vb)
        i += 1
    if linha_erro:
        aspecto, va, vb = linha_erro
        _escrever(t.cell(i, 0), aspecto, negrito=True, fundo=VERMELHO)
        _escrever(t.cell(i, 1), va, fundo=VERMELHO, italico=True)
        _escrever(t.cell(i, 2), vb, fundo=VERMELHO, italico=True)
    _espaco(doc)
    return t


# --------------------------------------------------------------------------
# 6. Quadro "o título declara × o título omite" — núcleo do Protocolo 4.3-A
# --------------------------------------------------------------------------
def quadro_declara_omite(doc, declara, omite,
                         titulo="O QUE O TÍTULO DECLARA E O QUE O TÍTULO OMITE"):
    """Os dois planos do Protocolo 4.3-A, lado a lado.

    É o componente mais importante da peça: separa o plano do EVENTO da
    capitalização (que o título costuma declarar, e cuja licitude não se
    discute) do plano da TAXA correspondente (que o título omite, e é onde mora
    a abusividade). Em prosa esses dois planos se embaralham, e é dessa
    confusão que nascem as decisões que rejeitam a tese dizendo "a capitalização
    estava pactuada".

    ATENÇÃO — Restrição Absoluta nº 15: a coluna "omite" registra "não consta".
    Jamais um percentual calculado pelo escritório a partir dos lançamentos.

    `declara` e `omite`: listas de (item, transcrição/observação).
    """
    total = max(len(declara), len(omite))
    t = _tabela(doc, total + 2, 2, larguras=[0.5, 0.5])
    c = t.cell(0, 0).merge(t.cell(0, 1))
    _escrever(c, titulo, negrito=True, fundo=LARANJA,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    _escrever(t.cell(1, 0), "O título DECLARA\n(plano do evento, lícito)",
              negrito=True, fundo=AZUL_CLARO,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    _escrever(t.cell(1, 1), "O título OMITE\n(plano da taxa, abusivo)",
              negrito=True, fundo=VERMELHO,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i in range(total):
        for j, fonte in enumerate((declara, omite)):
            if i >= len(fonte):
                continue
            item, obs = fonte[i]
            cel = t.cell(i + 2, j)
            _escrever(cel, item, negrito=True)
            if obs:
                p = cel.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(2)
                _runs(p, obs, tamanho=PT_ROTULO, italico=True)
    _espaco(doc)
    return t


# --------------------------------------------------------------------------
# 7. Cadeia de dois elos — o diagrama da tese
# --------------------------------------------------------------------------
def cadeia_dois_elos(doc, elo1, elo2, efeito,
                     titulo="A CADEIA DO TEMA 28/STJ"):
    """Elo 1 → (consequência automática) → Elo 2 → efeito processual.

    Torna visível o que a tese tem de mais forte e que a prosa esconde: entre um
    elo e o outro não há juízo de conveniência do julgador. O verbo da Orientação
    2 é indicativo, não permissivo.
    """
    blocos = [
        ("ELO 1: pressuposto", elo1, AZUL_CLARO),
        ("↓  consequência automática e vinculante (art. 927, III, CPC)", None, None),
        ("ELO 2: consequência", elo2, VERDE),
        ("↓  efeito processual", None, None),
        ("RESULTADO", efeito, VERDE),
    ]
    t = _tabela(doc, len(blocos) + 1, 1)
    _escrever(t.cell(0, 0), titulo, negrito=True, fundo=LARANJA,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (rotulo, texto, cor) in enumerate(blocos, start=1):
        cel = t.cell(i, 0)
        if texto is None:
            _escrever(cel, rotulo, italico=True, tamanho=PT_ROTULO,
                      alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
            continue
        _escrever(cel, rotulo, negrito=True, tamanho=PT_ROTULO, fundo=cor,
                  alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        p = cel.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(3)
        _runs(p, texto, tamanho=PT_TABELA)
    _espaco(doc)
    return t


# --------------------------------------------------------------------------
# 8. Precedente com badge de força
# --------------------------------------------------------------------------
VINCULANTE = ("PRECEDENTE VINCULANTE (art. 927, III, do CPC)", AZUL, AZUL_CLARO)
STJ = ("SUPERIOR TRIBUNAL DE JUSTIÇA", AZUL, AZUL_CLARO)
TRIBUNAL = ("TRIBUNAL DE ORIGEM", LARANJA_ESCURO, SALMAO)
SUMULA = ("SÚMULA", AZUL, AZUL_CLARO)
TITULO_CONTRATUAL = ("TRANSCRIÇÃO DA CLÁUSULA DO TÍTULO", "595959", CINZA)


def _runs_realce(paragrafo, texto, realces, tamanho=PT_TABELA, italico=True):
    """Escreve o texto realçando em amarelo os trechos de `realces`.

    O realce vai na TRANSCRIÇÃO, nunca na imagem do recorte. A distinção não é
    de estilo: o recorte é prova, e prova realçada pelo escritório é prova
    editada — o banco confere contra o original e usa a diferença. A transcrição
    é texto nosso, argumentativo, e nele o destaque é legítimo e esperado: é o
    equivalente escrito de apontar o dedo para a linha que interessa.
    """
    if not realces:
        return _runs(paragrafo, texto, tamanho=tamanho, italico=italico)
    padrao = re.compile("(" + "|".join(re.escape(r) for r in realces) + ")", re.I)
    for pedaco in padrao.split(str(texto)):
        if not pedaco:
            continue
        r = paragrafo.add_run(pedaco)
        r.font.name = FONTE
        r.font.size = Pt(tamanho)
        r.italic = italico
        if padrao.fullmatch(pedaco):
            r.bold = True
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return paragrafo


def precedente(doc, texto, fonte, forca=STJ, realce=None):
    """Badge de força + citação recuada em itálico + fonte centralizada.

    `realce` recebe a lista de trechos a destacar em amarelo dentro da citação —
    usado na transcrição da cláusula, para que o juízo veja de imediato as
    palavras que configuram a abusividade. Ver `_runs_realce`.

    A citação em si obedece à regra confirmada pela Dra. Juliana em 08/09/2026
    (recuo à direita, todo em itálico, 10 pt; fonte centralizada em negrito +
    itálico) — o componente não a altera. O que ele acrescenta é a tarja acima do
    bloco, que informa ao juízo, antes da leitura, se aquele julgado é de
    observância obrigatória ou meramente persuasivo. Rejeitar o primeiro exige
    distinguishing fundamentado (art. 489, § 1º, VI, do CPC); o segundo, não.
    """
    rotulo, cor_texto, cor_fundo = forca
    t = _tabela(doc, 1, 1)
    _bordas(t, cor=cor_texto, tamanho=4)
    _escrever(t.cell(0, 0), rotulo, negrito=True, tamanho=PT_ROTULO,
              cor=cor_texto, fundo=cor_fundo,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Cm(4)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    _runs_realce(p, texto, realce, tamanho=PT_TABELA, italico=True)

    pf = doc.add_paragraph()
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.paragraph_format.line_spacing = 1.15
    pf.paragraph_format.space_after = Pt(8)
    _runs(pf, fonte, tamanho=PT_TABELA, negrito=True, italico=True)
    return t


# --------------------------------------------------------------------------
# 9. Caixas de conclusão e de alerta
# --------------------------------------------------------------------------
def caixa(doc, rotulo, texto, cor=VERDE):
    t = _tabela(doc, 2, 1)
    _escrever(t.cell(0, 0), rotulo, negrito=True, tamanho=PT_ROTULO, fundo=cor,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    _escrever(t.cell(1, 0), texto, tamanho=PT_TABELA,
              alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY)
    _espaco(doc)
    return t


def realcar_em(doc, trechos, comeca_com=None):
    """Realça em amarelo os `trechos` numa peça JÁ PREENCHIDA.

    `precedente(realce=...)` só funciona quando o texto final passa pelo
    componente. Peça montada a partir do modelo tem o texto colado por cima do
    placeholder, e nesse caminho o realce se perde — este primitivo repõe.

    `comeca_com` restringe aos parágrafos que começam com aquele texto, para o
    destaque não se espalhar pela peça: amarelo em toda página deixa de ser
    destaque e vira ruído. Devolve quantos parágrafos foram tratados.
    """
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    def paragrafos():
        for ch in doc.element.body.iterchildren():
            if ch.tag.endswith('}p'):
                yield Paragraph(ch, doc)
            elif ch.tag.endswith('}tbl'):
                for linha in Table(ch, doc).rows:
                    for cel in linha.cells:
                        for p in cel.paragraphs:
                            yield p

    tratados = 0
    for p in paragrafos():
        texto = p.text
        if not texto.strip():
            continue
        if comeca_com and not texto.strip().startswith(comeca_com):
            continue
        if not any(t.lower() in texto.lower() for t in trechos):
            continue
        modelo = p.runs[0] if p.runs else None
        tamanho = modelo.font.size.pt if (modelo and modelo.font.size) else PT_TABELA
        italico = bool(modelo.italic) if modelo else False
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        _runs_realce(p, texto, trechos, tamanho=tamanho, italico=italico)
        tratados += 1
    return tratados


def caixa_prova(doc, texto, rotulo="O QUE O DOCUMENTO ACIMA PROVA"):
    """Caixa que amarra o recorte à tese, logo abaixo da imagem.

    Documento colado sem dizer o que ele prova vira ilustração. Esta caixa faz o
    trabalho que o realce na imagem faria — sem editar a prova.
    """
    return caixa(doc, rotulo, texto, AMARELO_SUAVE)


def caixa_conclusao(doc, texto):
    return caixa(doc, "CONCLUSÃO DO TÓPICO", texto, VERDE)


def quadro_distinguishing(doc, itens,
                          titulo="ÔNUS ARGUMENTATIVO PARA AFASTAR O PRECEDENTE"):
    """O que o juízo precisa demonstrar, ponto a ponto, para não aplicar a tese.

    Componente de pressão argumentativa, e não de decoração: explicita que a
    rejeição de precedente vinculante sem enfrentamento específico é decisão não
    fundamentada (art. 489, § 1º, VI, do CPC) e, portanto, atacável — deixando
    o ônus onde ele efetivamente está, que é com o banco.
    """
    t = _tabela(doc, len(itens) + 1, 1)
    _escrever(t.cell(0, 0), titulo, negrito=True, fundo=LARANJA,
              alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, item in enumerate(itens, start=1):
        _escrever(t.cell(i, 0), "•  " + item)
    _espaco(doc)
    return t


# --------------------------------------------------------------------------
# 9-bis. Prova em destaque — índice e bloco de prova
# --------------------------------------------------------------------------
def indice_de_provas(doc, provas,
                     titulo="ÍNDICE DAS PROVAS: O QUE ESTÁ NOS AUTOS E O QUE CADA DOCUMENTO DEMONSTRA"):
    """Tabela de abertura com todas as provas da peça.

    Pedido da Dra. Juliana (13/09/2026): o que o juiz quer ver quando abre o
    processo são as provas. O índice diz, antes de qualquer argumento, o que
    está nos autos, onde está e para que serve — e amarra cada documento ao
    requisito que ele satisfaz. É o mapa que o juiz e o assessor usam para
    conferir a peça contra os autos.

    `provas`: lista de (numero, documento, o_que_demonstra, requisito_ou_topico).
    """
    t = _tabela(doc, len(provas) + 2, 4, larguras=[0.09, 0.29, 0.40, 0.22])
    c = t.cell(0, 0)
    for j in (1, 2, 3):
        c = c.merge(t.cell(0, j))
    _escrever(c, titulo, negrito=True, fundo=LARANJA, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for j, cab in enumerate(["Prova", "Documento", "O que demonstra", "Requisito · tópico"]):
        _escrever(t.cell(1, j), cab, negrito=True, fundo=CINZA, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (numero, documento, demonstra, requisito) in enumerate(provas, start=2):
        n = "%02d" % int(numero) if not isinstance(numero, str) else numero
        _escrever(t.cell(i, 0), n, negrito=True, fundo=AZUL_CLARO, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        _escrever(t.cell(i, 1), documento, tamanho=PT_ROTULO)
        _escrever(t.cell(i, 2), demonstra, tamanho=PT_ROTULO)
        _escrever(t.cell(i, 3), requisito, tamanho=PT_ROTULO)
    _espaco(doc)
    return t


def bloco_prova(doc, numero, titulo, documento, requisito, recortar, grifar=None,
                transcrever=None, o_que_prova="", foto=False):
    """A prova emoldurada: cabeçalho, imagem, transcrição e o que ela prova.

    Um quadro de uma coluna, com moldura azul espessa nas laterais, em quatro
    faixas:

      1. PROVA nn · TÍTULO — documento/folha · requisito que a prova satisfaz
      2. [[INSERIR PRINT nn: ...]] — onde a automação cola o recorte grifado
      3. TRANSCRIÇÃO DO TRECHO GRIFADO — [[TEXTO DO PRINT nn: ...]]
         (em foto: DESCRIÇÃO OBJETIVA — data, local, o que se vê)
      4. O QUE ESTA PROVA DEMONSTRA — a ponte entre o documento e a tese

    Mantém as regras que já valiam para o recorte (`marcador_print` e skill
    `inicial-anexos`): o print entra SEMPRE em par com a transcrição; o grifo
    amarelo é feito no render (anexos_inicial.recortar, `realcar=`) e só é
    legítimo DECLARADO — a legenda traz "grifo nosso"; o documento original
    não é alterado; a imagem recebe borda fina (anexos_inicial._contornar).

    Os marcadores não usam colchete aninhado de propósito: "[[" dentro de "[["
    quebraria a detecção de campo e a de print órfão.
    """
    n = "%02d" % int(numero) if not isinstance(numero, str) else numero
    t = _tabela(doc, 4, 1)
    _bordas(t, cor=AZUL, tamanho=12)

    cab = t.cell(0, 0)
    _escrever(cab, "PROVA %s  ·  %s" % (n, titulo.upper()), negrito=True, cor=AZUL,
              fundo=AZUL_CLARO, alinhamento=WD_ALIGN_PARAGRAPH.LEFT)
    p = cab.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    _runs(p, "%s   ·   %s" % (documento, requisito), tamanho=PT_ROTULO)

    slot = t.cell(1, 0).paragraphs[0]
    slot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    slot.paragraph_format.space_before = Pt(8)
    slot.paragraph_format.space_after = Pt(8)
    instr = "recortar: %s" % recortar
    if grifar:
        instr += "; grifar em amarelo: %s" % "; ".join('"%s"' % g for g in grifar)
    instr += "; legenda ACIMA da imagem: Imagem NN, documento, folha%s" % ("" if foto or not grifar else " e (grifo nosso)")
    r = slot.add_run("[[INSERIR PRINT %s: %s]]" % (n, instr))
    r.font.name = FONTE
    r.font.size = Pt(PT_TABELA)
    r.bold = True
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW

    rot = "DESCRIÇÃO OBJETIVA DO QUE A FOTO MOSTRA" if foto else "TRANSCRIÇÃO DO TRECHO GRIFADO"
    tr = t.cell(2, 0)
    _escrever(tr, rot, negrito=True, tamanho=PT_ROTULO, fundo=CINZA)
    ptx = tr.add_paragraph()
    ptx.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    ptx.paragraph_format.space_after = Pt(4)
    rt = ptx.add_run("[[TEXTO DO PRINT %s: %s]]" % (
        n, transcrever or ("data, local e o que se vê, sem adjetivo" if foto else
                           "transcrever literalmente o trecho grifado, sem corte que altere o sentido")))
    rt.font.name = FONTE
    rt.font.size = Pt(PT_TABELA)
    rt.italic = True
    rt.font.highlight_color = WD_COLOR_INDEX.YELLOW

    dm = t.cell(3, 0)
    _escrever(dm, "O QUE ESTA PROVA DEMONSTRA", negrito=True, tamanho=PT_ROTULO, fundo=AMARELO_SUAVE)
    pd = dm.add_paragraph()
    pd.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pd.paragraph_format.space_after = Pt(4)
    _runs(pd, o_que_prova, tamanho=PT_TABELA)
    _espaco(doc, 8)
    return t


# --------------------------------------------------------------------------
# 10. Rol de pedidos
# --------------------------------------------------------------------------
def rol_de_pedidos(doc, pedidos):
    """Lista alfabética recuada. Deliberadamente SEM tabela e SEM cor.

    O rol de pedidos é a parte da peça que o juízo copia para o dispositivo e o
    cartório transcreve no PJe: qualquer formatação que atrapalhe a seleção do
    texto trabalha contra a peça. Aqui o visual law entra pela restrição, não
    pelo acréscimo.
    """
    saida = []
    for letra, texto in pedidos:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(6)
        r = p.add_run("%s) " % letra)
        r.font.name = FONTE
        r.font.size = Pt(PT_CORPO)
        r.bold = True
        _runs(p, texto, tamanho=PT_CORPO)
        saida.append(p)
    return saida


# --------------------------------------------------------------------------
# 11. Varredura léxica — Restrição Absoluta nº 19
# --------------------------------------------------------------------------
TERMOS_DE_EMBARGOS = [
    "embargos à execução", "embargos a execucao", "presentes embargos",
    "embargante", "embargado", "efeito suspensivo",
    "art. 919", "919, §", "garantia do juízo", "ora embargada",
    "sobrestamento da execução",
]
# "919" solto ficaria fora: casaria com número de processo e afogaria o achado
# real em ruído. "embargos" solto também: embargos de declaração são cabíveis na
# declaratória e não são o vício que a Restrição nº 19 persegue.


def varrer_lexico_embargos(doc):
    """Devolve as ocorrências de vocabulário de embargos numa declaratória.

    Restrição Absoluta nº 19. Um único pedido residual de "efeito suspensivo aos
    presentes embargos à execução", remanescente de modelo reaproveitado, foi o
    trecho que o juízo transcreveu para converter de ofício a ação declaratória
    em embargos nos autos 0000000-00.0000.0.00.0000. Rodar sempre antes de
    entregar a minuta para revisão.

    O quadro de instruções do modelo (aquele que começa com "MODELO — APAGUE
    ESTE QUADRO") é ignorado: ele cita os termos proibidos justamente para
    adverti-los, e sai da peça antes da entrega. Se o quadro continuar lá na hora
    da revisão, quem avisa é o próprio revisor — não a varredura.

    Devolve lista de (índice do parágrafo, termo, trecho). Lista vazia = limpo.
    """
    achados = []
    textos = [(i, p.text) for i, p in enumerate(doc.paragraphs)]
    for t in doc.tables:
        if "APAGUE ESTE QUADRO" in t.cell(0, 0).text.upper():
            continue
        for linha in t.rows:
            for cel in linha.cells:
                textos.append((-1, cel.text))
    for i, texto in textos:
        baixo = texto.lower()
        for termo in TERMOS_DE_EMBARGOS:
            if termo in baixo:
                pos = baixo.index(termo)
                achados.append((i, termo, texto[max(0, pos - 60):pos + 80].strip()))
    return achados
