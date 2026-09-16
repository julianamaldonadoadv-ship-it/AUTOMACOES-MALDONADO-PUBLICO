"""
=============================================================================
  RELATORIOS DE KPI EM PDF - MALDONADO ADVOGADOS
=============================================================================

  Monta, a partir da apuracao de `kpi_exito`, os tres documentos que a
  Gerencia Juridica precisa para fechar a competencia:

    1. RELATORIO  - executivo: funil do periodo, quadro consolidado por
                    carteira e por advogado, composicao por KPI, ressalvas.
    2. DECISOES   - o diario do periodo: dia a dia, cada decisao com o
                    dispositivo e o LINK da publicacao no DJEN. E' o documento
                    que responde "o que saiu no dia 04".
    3. ANEXO      - processo a processo: as decisoes computadas com o
                    dispositivo que as classificou, as que ficaram a conferir
                    e os atos fora de escopo com o motivo da exclusao.
    4. FICHAS     - uma ficha por advogado, com as decisoes dele e a
                    composicao da taxa.

  Os quatro saem em Markdown (fonte versionada) e viram PDF pelo
  `md_para_pdf.py` - mesmo motor Chrome headless do resto do projeto.

  Por que quatro documentos e nao um: o executivo circula na direcao, o diario
  e' o que se abre para ver o que foi decidido num dia, o anexo permite auditar
  linha a linha contra o ADVBOX e a ficha vai para a conversa individual com o
  advogado. Junta-los faria o executivo ter 40 paginas e ninguem leria a
  ressalva da pagina 2.

  Somente leitura: nao toca ADVBOX nem Drive.
=============================================================================
"""
import os
from collections import defaultdict

import kpi_exito


# ============================================================
# FORMATACAO
# ============================================================

# Meta oficial: "7 - MANUAL DO EXITO JURIDICO KPI" (v1.0, mai/2026) - cada KPI e
# a taxa geral tem meta de 20% ("Global | Taxa Geral Ponderada | >= 20% mensal").
# NAO sao os 30% que os relatorios de jun-jul/2026 reportavam.
META = 0.20


def pct(x, casas=1):
    if x is None:
        return "—"
    return f"{x * 100:.{casas}f}%".replace(".", ",")


def num(x, casas=2):
    if x is None:
        return "—"
    return f"{x:.{casas}f}".replace(".", ",")


ROTULO_RESULTADO = {"exito": "**Êxito**", "parcial": "Parcial", "inexito": "Inêxito"}
ROTULO_CONFIANCA = {"alta": "alta", "media": "média", "baixa": "baixa"}

# Os motivos de exclusao vivem no codigo em ASCII sem acento (o modulo compara
# texto normalizado). Documento que circula na direcao nao pode sair com
# "extincao de cumprimento de sentenca" — daqui sai a versao para leitura.
_MOTIVO_ROTULO = {
    "ato sem dispositivo decisorio identificavel (despacho/expediente)":
        "Ato sem dispositivo decisório (despacho, expediente, certidão)",
    "despacho de mero expediente / impulso":
        "Despacho de mero expediente / impulso processual",
    "embargos de declaracao - nao contam (regra da GJ, 10/09/2026)":
        "Embargos de declaração — não contam (regra da GJ, 10/09/2026): o mérito "
        "já foi pontuado na decisão embargada",
    "homologacao de desistencia / cancelamento de distribuicao":
        "Homologação de desistência / cancelamento de distribuição",
    "extincao de cumprimento de sentenca por pagamento (art. 924, II)":
        "Extinção de cumprimento de sentença por pagamento (art. 924, II)",
    "questao acessoria (gratuidade / custas / honorarios isolados)":
        "Questão acessória (gratuidade, custas ou honorários isolados)",
    "acordao / julgamento colegiado do recurso":
        "Acórdão / julgamento colegiado do recurso",
    "decisao sobre efeito suspensivo / tutela recursal":
        "Decisão sobre efeito suspensivo / tutela recursal",
    "decisao sobre tutela de 1o grau": "Decisão sobre tutela de 1º grau",
    "sentenca de merito (art. 487, I)": "Sentença de mérito (art. 487, I)",
    "sentenca (extincao com/sem resolucao de merito)":
        "Sentença (extinção com ou sem resolução de mérito)",
    "homologacao de acordo": "Homologação de acordo",
}


def motivo(texto):
    return _MOTIVO_ROTULO.get(texto, texto)


# kpi_exito.ROTULO_KPI vive em ASCII (o modulo compara texto normalizado); o
# documento que circula na direcao usa a versao acentuada.
ROTULO_KPI = {
    "KPI 1": "Mérito (sentença/acórdão)",
    "KPI 2": "Tutela de 1º grau (liminar)",
    "KPI 3": "Tutela recursal (efeito suspensivo)",
    "KPI 4": "Acordo / êxito negocial",
}


def rotulo_kpi(k):
    return ROTULO_KPI.get(k, kpi_exito.ROTULO_KPI.get(k, k))


def _res(r):
    return ROTULO_RESULTADO.get(r, "—")


def _conf(c):
    return ROTULO_CONFIANCA.get(c, c or "—")


def proc(numero):
    """Numero de processo em uma linha so - senao a coluna quebra no meio do
    CNJ ('0812063-' / '30.2026.8.22.0000') e fica ilegivel na tabela."""
    return f'<span class="proc">{numero}</span>'


def _titulo_adv(nome):
    """'MAILSON SANTOS MONTEIRO' -> 'Mailson Santos Monteiro'."""
    if not nome:
        return "—"
    return " ".join(p.capitalize() if len(p) > 2 else p.lower()
                    for p in nome.split())


_PARTICULAS = {"de", "da", "do", "dos", "das", "e"}
# "Neto", "Filho", "Junior" nao sao sobrenome: sao sufixo de geracao. Cortar o
# nome em "Agenor Neto" perde justamente a parte que identifica a pessoa, entao
# o sufixo entra junto com o sobrenome que o precede.
_SUFIXOS = {"neto", "filho", "junior", "jr", "sobrinho", "segundo", "netto"}


def _nome_curto(nome):
    """'FELIPE DA CONCEICAO SOUZA NARCISO' -> 'Felipe Narciso'.

    A tabela do executivo tem 8 colunas; nome inteiro faz a linha ocupar tres
    alturas de texto. O nome completo continua no anexo e na ficha.
    """
    if not nome:
        return "—"
    partes = [p for p in nome.split() if p.lower() not in _PARTICULAS]
    if len(partes) <= 2:
        return _titulo_adv(" ".join(partes))
    if partes[-1].lower() in _SUFIXOS and len(partes) >= 3:
        return _titulo_adv(f"{partes[0]} {partes[-2]} {partes[-1]}")
    return _titulo_adv(f"{partes[0]} {partes[-1]}")


def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def curto(texto, limite=90):
    """Corta na fronteira de palavra - o corte cru partia a evidencia no meio
    ('tese central acolhida: descaracterizac')."""
    t = (texto or "").strip()
    if len(t) <= limite:
        return t
    corte = t[:limite].rsplit(" ", 1)[0]
    return corte.rstrip(" ,;.") + "…"


def data(iso):
    """'2026-09-01' -> '01/09/2026', sem quebrar linha na coluna estreita."""
    if not iso or len(iso) < 10:
        return iso or "—"
    a, m, d = iso[:4], iso[5:7], iso[8:10]
    return f'<span class="proc">{d}/{m}/{a}</span>'


ROTULO_POLO = {"ativo": "Ativo", "passivo": "Passivo"}
ROTULO_RECURSO = {"nosso": "nosso", "da parte contraria": "da parte contrária"}


# ============================================================
# GRAFICO DE BARRAS (HTML inline)
# ============================================================
#
# O relatorio da GJ de jun-ago/2026 le por grafico de barras horizontal, e a
# equipe ja esta acostumada com esse formato. Markdown nao faz grafico, mas o
# conversor deixa HTML cru passar - entao a barra e' CSS puro, sem biblioteca
# e sem imagem externa (que o Chrome headless nao carregaria de file://).

_ESTILO = """
<style>
.gr { margin: 10pt 0 16pt; -webkit-print-color-adjust: exact;
      print-color-adjust: exact; }
.gr .linha { display: flex; align-items: center; margin: 0 0 5pt;
             page-break-inside: avoid; break-inside: avoid; }
.gr .rot { width: 34%; font-size: 8.6pt; padding-right: 8pt; text-align: right;
           color: #333; }
.gr .trilho { flex: 1; height: 13pt; background: #efece9; border-radius: 2pt;
              position: relative; display: block; }
/* display:block e' OBRIGATORIO nos dois: sao <span>, e em elemento inline o
   Chrome ignora width/height - a barra saia sempre vazia no PDF. */
.gr .fill { display: block; height: 100%; border-radius: 2pt; background: #7a1f2b; }
.gr .fill.zero { background: #d8d3ce; }
.gr .meta { display: block; position: absolute; top: -2pt; bottom: -2pt; width: 0;
            border-left: 1pt dashed #c9a227; }
.gr .val { width: 16%; font-size: 8.6pt; padding-left: 8pt; color: #333;
           font-variant-numeric: tabular-nums; }
.gr .legenda { font-size: 7.6pt; color: #8a8a8a; margin-top: 6pt;
               text-align: right; }
.caixa { background: #f6f4f2; border-left: 3pt solid #c9a227; padding: 8pt 11pt;
         margin: 11pt 0; font-size: 9.2pt; page-break-inside: avoid; }
.caixa .tit, .alerta .tit { font-weight: 700; display: block; margin-bottom: 3pt; }
.alerta { background: #fdf3f1; border-left: 3pt solid #7a1f2b; padding: 8pt 11pt;
          margin: 11pt 0; font-size: 9.2pt; page-break-inside: avoid; }
.disp { font-size: 8.3pt; color: #555; font-style: italic; }
.proc { white-space: nowrap; font-variant-numeric: tabular-nums; }
/* Ficha de decisao: tabela sem cabecalho, rotulo a esquerda. */
table.ficha { width: 100%; border-collapse: collapse; margin: 6pt 0 8pt;
              font-size: 9pt; }
table.ficha td { border: .5pt solid #e2dedb; padding: 4pt 8pt; }
table.ficha td:first-child { width: 32%; color: #6b6b6b; background: #faf9f8; }
table.ficha tr:nth-child(even) td { background: #fff; }
table.ficha tr:nth-child(even) td:first-child { background: #faf9f8; }
.quebra { page-break-before: always; break-before: page; }
</style>
"""


def barras(itens, meta=None, legenda=None):
    """itens: lista de (rotulo, taxa 0..1, texto_do_valor)."""
    linhas = ['<div class="gr">']
    for rotulo, taxa, valor in itens:
        largura = 0 if not taxa else min(taxa, 1.0) * 100
        classe = "fill zero" if not taxa else "fill"
        marca = (f'<span class="meta" style="left:{min(meta,1.0)*100:.1f}%"></span>'
                 if meta else "")
        linhas.append(
            f'<div class="linha"><span class="rot">{rotulo}</span>'
            f'<span class="trilho">{marca}'
            f'<span class="{classe}" style="width:{largura:.1f}%"></span></span>'
            f'<span class="val">{valor}</span></div>')
    if legenda:
        linhas.append(f'<div class="legenda">{legenda}</div>')
    linhas.append("</div>")
    return "\n".join(linhas)


# ============================================================
# BLOCOS REAPROVEITADOS
# ============================================================

CABECALHO_REGUA = """Régua aplicada: a do relatório da Gerência Jurídica *Taxa de Êxito por
Advogado — Jun-Jul-Ago 2026*, extraída da pasta **9. TAXA DE ÊXITO DO ESCRITÓRIO** (ZEUS).

```
Taxa Ponderada = Σ(peso × favorável) ÷ Σ(peso)
favorável:  Êxito = 1,0  ·  Parcial = 0,5  ·  Inêxito = 0,0

KPI 1 — Mérito (sentença/acórdão) ............ peso 1,0
KPI 2 — Tutela de 1º grau (liminar) .......... peso 0,4
KPI 3 — Tutela recursal (efeito suspensivo) .. peso 0,5
KPI 4 — Acordo / êxito negocial .............. peso 0,5 a 2,0 (arbitrado pela GJ)
```

Só a **carteira de dívidas rurais** compõe o indicador oficial da Presidência. Processo de outra
natureza vai para a **carteira diversa**, apurada à parte pelo Regulamento de Bonificação por
Êxito — régua distinta, nunca somada na mesma taxa.
"""

RODAPE_METODO = """
---

<div class="alerta">
<span class="tit">O que este documento é, e o que não é</span>
Pré-classificação automática por palavra-chave sobre o texto publicado no DJEN — <b>palpite,
não laudo</b>. Cada linha traz o trecho do dispositivo que motivou a classificação e o nível de
confiança, para conferência. <b>O número oficial da competência continua sendo fechado pela
Gerência Jurídica.</b> A automação não lança na planilha, não protocola e não grava nada no
ADVBOX nem no Drive.
</div>
"""


def _meta_doc(periodo, oabs, gerado_em):
    oabs_txt = " · ".join(f"{n}/{uf}" for n, uf in (oabs or []))
    return (f"**Período:** {periodo} · **Fonte:** DJEN/Comunica (CNJ), OAB {oabs_txt}, "
            f"cruzado com o ADVBOX · **Gerado em:** {gerado_em} · Uso interno\n")


def _por_advogado_ordenado(apuracao, carteira):
    """[(advogado, bloco)] ordenado por taxa desc, sem denominador zero."""
    saida = []
    for adv, cs in apuracao["por_advogado"].items():
        b = cs.get(carteira)
        if b and b["den"]:
            saida.append((adv, b))
    return sorted(saida, key=lambda x: (-(x[1]["num"] / x[1]["den"]), -x[1]["den"]))


# ============================================================
# 1. RELATORIO EXECUTIVO
# ============================================================

def montar_relatorio(linhas, apuracao, periodo, oabs, gerado_em, ressalvas_extra=""):
    computadas = apuracao["computadas"]
    pendentes = apuracao["pendentes"]
    fora = apuracao["fora_escopo"]

    motivos = defaultdict(int)
    for l in fora:
        motivos[l["kpi_motivo"]] += 1

    p = [_ESTILO, "# Taxa de Êxito Ponderado — apuração das intimações", "",
         _meta_doc(periodo, oabs, gerado_em), "", CABECALHO_REGUA, "", "---", "",
         "## 1. O funil do período", ""]

    total = apuracao["total_linhas"]
    nao_class = len(fora) + len(pendentes)
    p += ["| | Atos |", "|---|---:|",
          f"| Comunicações capturadas no DJEN (após deduplicação) | **{total}** |",
          f"| Fora do escopo dos KPIs | {len(fora)} |",
          f"| **Decisões classificadas e computadas na taxa** | **{len(computadas)}** |",
          f"| Decisões no escopo que a automação não fechou sozinha | {len(pendentes)} |",
          ""]

    if total:
        prop = nao_class / total
        p += [f'<div class="caixa"><span class="tit">O tamanho do garimpo</span>',
              f"{nao_class} dos {total} atos do período ({pct(prop, 0)}) não são decisão "
              f"classificável. Para achar as {len(computadas)} decisões que entram no KPI, "
              f"alguém precisaria ler as {total} publicações uma a uma.</div>", ""]

    p += ["### Por que cada ato ficou de fora", "", "| Motivo da exclusão | Atos |", "|---|---:|"]
    for m, n in sorted(motivos.items(), key=lambda x: -x[1]):
        p.append(f"| {motivo(m)} | {n} |")
    p.append("")

    # ---- carteiras ----
    for carteira, titulo, subtitulo in (
            ("rural", "2. Carteira de dívidas rurais",
             "indicador oficial da Presidência"),
            ("diversa", "3. Carteira diversa",
             "régua do Regulamento de Bonificação por Êxito — apurada à parte")):
        deste = [l for l in computadas if l["carteira"] == carteira]
        if not deste:
            continue
        tot = apuracao["por_carteira"][carteira]
        p += ["---", "", f"## {titulo}", "", f"*{subtitulo}*", "",
              f'<div class="caixa"><span class="tit">TOTAL — {pct(tot["taxa"])}</span>'
              f'{num(tot["num"])} ÷ {num(tot["den"])} sobre '
              f'{_plural(tot["n"], "decisão", "decisões")} no período.</div>', "",
              "| Cliente | Processo | Advogado responsável | KPI | Resultado | Peso | Contrib. | Conf. |",
              "|---|---|---|---|---|---:|---:|---|"]
        for l in sorted(deste, key=lambda x: (x["advogado_responsavel"], x["data"])):
            p.append(f"| {_titulo_adv(l['cliente'])} | {proc(l['processo'])} | "
                     f"{_nome_curto(l['advogado_responsavel'])} | {l['kpi']} | "
                     f"{_res(l['resultado'])} | {num(l['peso'])} | "
                     f"{num(l['contribuicao'])} | {_conf(l['confianca'])} |")
        p.append("")

        ordenado = _por_advogado_ordenado(apuracao, carteira)
        if ordenado:
            p += [f"### Por advogado — carteira {carteira}", "",
                  "| Advogado | Num. | Den. | Taxa | Decisões |", "|---|---:|---:|---:|---:|"]
            for adv, b in ordenado:
                p.append(f"| {_titulo_adv(adv)} | {num(b['num'])} | {num(b['den'])} | "
                         f"**{pct(b['num'] / b['den'])}** | {b['n']} |")
            p.append(f"| **TOTAL {carteira.upper()}** | **{num(tot['num'])}** | "
                     f"**{num(tot['den'])}** | **{pct(tot['taxa'])}** | **{tot['n']}** |")
            p.append("")
            p.append(barras(
                [(_titulo_adv(a), b["num"] / b["den"],
                  f"{pct(b['num'] / b['den'])} <span style='color:#999'>({num(b['den'])})</span>")
                 for a, b in ordenado],
                meta=META,
                legenda="Barra = taxa ponderada do período. Entre parênteses, o denominador. "
                        "Tracejado = meta de 20% do Manual de Êxito Jurídico (v1.0, mai/2026)."))
            p.append("")

            denominadores = [b["den"] for _, b in ordenado]
            if denominadores and max(denominadores) < 5:
                menor = min(denominadores)
                referencia = (" Em agosto/2026 a competência inteira desta carteira fechou "
                              "com denominador 15,10." if carteira == "rural" else "")
                p += ['<div class="alerta"><span class="tit">Base pequena — leitura de fluxo, '
                      'não avaliação</span>',
                      f"O maior denominador individual do período é {num(max(denominadores))}; "
                      f"o menor, {num(menor)}.{referencia} Uma única decisão troca a posição de "
                      f"qualquer advogado desta tabela — estes números descrevem o fluxo do "
                      f"período, e não sustentam conclusão sobre desempenho individual.</div>", ""]

    # ---- por semana e por dia ----
    semanas = sorted(n for n in apuracao.get("por_semana", {}) if n)
    if semanas:
        p += ["---", "", "## 4. Evolução — por semana e por dia", "",
              "Semana de **segunda a domingo**, numerada a partir da que contém o primeiro dia "
              "da competência (não é a semana ISO do ano). A tabela abre por carteira porque só "
              "a rural é o indicador oficial.", "",
              "| Semana | Período | Rural | Diversa | Decisões |",
              "|---|---|---:|---:|---:|"]
        for n in semanas:
            ini, fim = kpi_exito.intervalo_da_semana(linhas, n)
            b = apuracao["por_semana"][n]
            rur, div, tot = b.get("rural"), b.get("diversa"), b.get("total")
            periodo_sem = (f"{ini.strftime('%d/%m')} a {fim.strftime('%d/%m')}"
                           if ini and fim else "—")
            p.append(f"| **{kpi_exito.rotular_semana(n)}** | {periodo_sem} | "
                     + (f"{pct(rur['taxa'])} ({num(rur['num'])}/{num(rur['den'])}) | "
                        if rur else "— | ")
                     + (f"{pct(div['taxa'])} ({num(div['num'])}/{num(div['den'])}) | "
                        if div else "— | ")
                     + f"{tot['n'] if tot else 0} |")
        p.append("")

        rurais = [(kpi_exito.rotular_semana(n), apuracao["por_semana"][n].get("rural"))
                  for n in semanas]
        rurais = [(r, b) for r, b in rurais if b and b["den"]]
        if rurais:
            p.append(barras([(r, b["taxa"], f"{pct(b['taxa'])} "
                              f"<span style='color:#999'>({num(b['den'])})</span>")
                             for r, b in rurais], meta=META,
                            legenda="Carteira rural por semana. Entre parênteses, o "
                                    "denominador. Tracejado = meta de 20%."))
            p.append("")
            if len(rurais) > 1:
                pior = min(rurais, key=lambda x: x[1]["taxa"])
                melhor = max(rurais, key=lambda x: x[1]["taxa"])
                if melhor[1]["taxa"] - pior[1]["taxa"] >= 0.20:
                    p += ['<div class="alerta"><span class="tit">A média do período esconde '
                          'as semanas</span>',
                          f"{pior[0]} fechou em {pct(pior[1]['taxa'])} e {melhor[0]} em "
                          f"{pct(melhor[1]['taxa'])} — {pct(melhor[1]['taxa'] - pior[1]['taxa'])} "
                          "de diferença. Com denominadores desta ordem, uma semana inteira é "
                          "decidida por duas ou três decisões; a leitura semanal serve para "
                          "acompanhar o fluxo, não para comparar semanas entre si.</div>", ""]

        # dia a dia
        dias = sorted(d for d in apuracao.get("por_dia", {}) if d)
        if dias:
            p += ["### Dia a dia", "",
                  "| Dia | Semana | Rural | Diversa | Decisões |", "|---|---|---:|---:|---:|"]
            for d in dias:
                b = apuracao["por_dia"][d]
                rur, div, tot = b.get("rural"), b.get("diversa"), b.get("total")
                sem = next((l.get("semana_rotulo") for l in linhas if l.get("data") == d), "—")
                p.append(f"| {data(d)} | {sem} | "
                         + (f"{pct(rur['taxa'])} ({num(rur['num'])}/{num(rur['den'])}) | "
                            if rur else "— | ")
                         + (f"{pct(div['taxa'])} ({num(div['num'])}/{num(div['den'])}) | "
                            if div else "— | ")
                         + f"{tot['n'] if tot else 0} |")
            p.append("")

    # ---- por KPI, dentro de cada carteira ----
    # Regra da Dra. Juliana (14/09/2026): a taxa e' sempre ponderada por
    # carteira. Nenhuma tabela soma rural com diversa.
    if apuracao["por_kpi"]:
        p += ["---", "", "## 5. Composição por KPI — por carteira", "",
              "*Cada carteira ponderada individualmente; rural e diversa nunca são somadas "
              "na mesma taxa.*", ""]
        for carteira in ("rural", "diversa"):
            kpis = apuracao["por_kpi"].get(carteira)
            if not kpis:
                continue
            tot = apuracao["por_carteira"][carteira]
            p += [f"### Carteira {carteira}", "",
                  "| KPI | Num. | Den. | Taxa | Decisões |", "|---|---:|---:|---:|---:|"]
            for k in kpi_exito.PESOS:
                b = kpis.get(k)
                if b:
                    p.append(f"| {k} — {rotulo_kpi(k)} | {num(b['num'])} | "
                             f"{num(b['den'])} | **{pct(b['taxa'])}** | {b['n']} |")
            p.append(f"| **TOTAL {carteira.upper()}** | **{num(tot['num'])}** | "
                     f"**{num(tot['den'])}** | **{pct(tot['taxa'])}** | **{tot['n']}** |")
            p.append("")
            p.append(barras(
                [(f"{k} — {rotulo_kpi(k).split('(')[0].strip()}",
                  kpis[k]["taxa"],
                  f"{pct(kpis[k]['taxa'])} "
                  f"<span style='color:#999'>({kpis[k]['n']})</span>")
                 for k in kpi_exito.PESOS if k in kpis],
                meta=META,
                legenda=f"Carteira {carteira}. Entre parênteses, o número de decisões."))
            p.append("")

    # ---- confianca ----
    altas = [l for l in computadas if l["confianca"] == "alta"]
    p += ["---", "", "## 6. Confiança da classificação", ""]
    if computadas:
        p += [f"{len(altas)} das {len(computadas)} linhas saíram com confiança **alta** — "
              "dispositivo com marcador explícito e polo do escritório confirmado pelo campo "
              "`destinatarios[].polo` do CNJ.", ""]
    so_alta = kpi_exito.apurar(linhas, somente_confianca=["alta"])
    if so_alta["por_carteira"]:
        p += ["Recalculando **só com as linhas de confiança alta**, para ver se as demais estão "
              "puxando o número para algum lado:", "",
              "| Carteira | Todas as linhas | Só confiança alta |", "|---|---:|---:|"]
        maior_gap, carteira_gap, maior_den = 0.0, None, -1.0
        for c, b in apuracao["por_carteira"].items():
            b2 = so_alta["por_carteira"].get(c)
            p.append(f"| {c} | {pct(b['taxa'])} ({num(b['num'])}/{num(b['den'])}) | "
                     + (f"{pct(b2['taxa'])} ({num(b2['num'])}/{num(b2['den'])}) |"
                        if b2 else "— |"))
            # Escolhe a carteira de maior DENOMINADOR, nao a de maior diferenca:
            # a diversa tem 4 decisoes e produz diferencas enormes que nao
            # descrevem o indicador oficial.
            if b2 and b["taxa"] is not None and b2["taxa"] is not None:
                if b["den"] > maior_den:
                    maior_den = b["den"]
                    maior_gap, carteira_gap = abs(b["taxa"] - b2["taxa"]), c
        p.append("")
        # A diferenca so merece explicacao quando e' grande. Ela aparece quando
        # as decisoes de maior peso sao justamente as de leitura menos direta -
        # o que acontece sempre que uma procedencia parcial vira exito pela
        # regra da tese, porque essa leitura nunca sai como confianca alta.
        if maior_gap >= 0.05:
            p += ['<div class="alerta"><span class="tit">A diferença entre as duas colunas '
                  'não é ruído</span>',
                  f"Na carteira {carteira_gap} as duas leituras separam "
                  f"{pct(maior_gap)} — o corte por confiança alta derruba justamente as "
                  "decisões de maior peso, que são as de leitura menos direta (procedência "
                  "parcial resolvida pela régua da tese, acórdão publicado só como ementa). "
                  "A coluna da esquerda é a apuração; a da direita mede quanto do número "
                  "depende de leitura que a Gerência ainda precisa referendar — e é por isso "
                  "que as linhas abaixo estão listadas uma a uma.</div>", ""]

    confirmar = [l for l in computadas if l.get("confirmar_resultado")]
    if confirmar:
        p += ['<div class="alerta"><span class="tit">'
              f'{_plural(len(confirmar), "linha computada que precisa", "linhas computadas que precisam")}'
              ' da palavra da GJ</span>',
              "Decisão em que o texto da sentença e a régua do escritório apontam para lados "
              "diferentes — tipicamente a procedência parcial em que a tese central foi acolhida "
              "mas o juízo fixou sucumbência recíproca. Está computada pela régua da tese; "
              "mudar para Parcial é decisão da Gerência.</div>", "",
              "| Processo | Cliente | KPI | Computado como | Motivo |", "|---|---|---|---|---|"]
        for l in confirmar:
            p.append(f"| {proc(l['processo'])} | {_titulo_adv(l['cliente'])} | {l['kpi']} | "
                     f"{_res(l['resultado'])} | *{curto(l['evidencia'], 90)}* |")
        p.append("")

    medias = [l for l in computadas if l["confianca"] != "alta"]
    if medias:
        p += ["### Linhas computadas com confiança abaixo de alta", "",
              "| Processo | Cliente | KPI | Resultado | Dispositivo lido |",
              "|---|---|---|---|---|"]
        for l in medias:
            p.append(f"| {proc(l['processo'])} | {_titulo_adv(l['cliente'])} | "
                     f"{l['kpi']} | {_res(l['resultado'])} | "
                     f"*{curto(l['evidencia'], 70)}* |")
        p.append("")

    if ressalvas_extra:
        p += ["---", "", ressalvas_extra, ""]

    p.append(RODAPE_METODO)
    return "\n".join(p)


# ============================================================
# 2. ANEXO PROCESSO A PROCESSO
# ============================================================

def montar_anexo(linhas, apuracao, periodo, oabs, gerado_em):
    p = [_ESTILO, "# Anexo — apuração de KPI processo a processo", "",
         _meta_doc(periodo, oabs, gerado_em), "",
         "Este anexo existe para auditoria direta contra o ADVBOX e o PJe: toda linha traz o "
         "trecho do **dispositivo** que motivou a classificação, o polo em que o escritório "
         "está e — quando o ato ficou de fora — o motivo da exclusão.", "",
         "---", "", "## A. Decisões computadas na taxa", ""]

    # Formato compacto, na mesma ordem de colunas dos Anexos A/B/C do relatorio
    # da GJ (advogado -> processo -> KPI -> classificacao -> peso -> contrib.),
    # com duas colunas a mais que so a automacao consegue oferecer: o POLO em
    # que o escritorio esta e o DISPOSITIVO que foi lido. Sao essas duas que
    # tornam a linha auditavel sem abrir o PJe.
    for carteira in ("rural", "diversa"):
        deste = [l for l in apuracao["computadas"] if l["carteira"] == carteira]
        if not deste:
            continue
        tot = apuracao["por_carteira"][carteira]
        p += [f"### Carteira {carteira} — {num(tot['num'])} / {num(tot['den'])} = "
              f"{pct(tot['taxa'])}", "",
              "| Advogado | Cliente | Processo | Data | KPI | Polo | Resultado | Peso | Contrib. | Conf. |",
              "|---|---|---|---|---|---|---|---:|---:|---|"]
        for l in sorted(deste, key=lambda x: (x["advogado_responsavel"], x["data"])):
            # De quem e' o recurso vai para a lista de dispositivos, logo
            # abaixo: na coluna, "ativo - rec. nosso" ocupava tres linhas.
            polo = ROTULO_POLO.get(l["polo"], "—")
            p.append(f"| {_nome_curto(l['advogado_responsavel'])} | "
                     f"{_titulo_adv(l['cliente'])} | {proc(l['processo'])} | "
                     f"{data(l['data'])} | {l['kpi']} | {polo} | "
                     f"{_res(l['resultado'])} | {num(l['peso'])} | "
                     f"{num(l['contribuicao'])} | {_conf(l['confianca'])} |")
        p.append("")
        p += ["**Dispositivos lidos** — o trecho exato que classificou cada linha acima:", ""]
        for l in sorted(deste, key=lambda x: (x["advogado_responsavel"], x["data"])):
            rec = ROTULO_RECURSO.get(l["recurso_de_quem"])
            p.append(f"- `{l['processo']}` — {motivo(l['kpi_motivo'])}"
                     + (f", recurso {rec}" if rec else "") + ". "
                     f'<span class="disp">Dispositivo: “{l["evidencia"]}”</span> '
                     f"Carteira: {l['origem_carteira']}.")
        p.append("")

    if apuracao["pendentes"]:
        p += ['<div class="quebra"></div>', "", "## B. Decisões a conferir à mão", "",
              "Atos que o classificador reconheceu como possível decisão mas **não fechou** — "
              "por prudência, ficam fora da taxa até leitura humana.", "",
              "| Data | Processo | Cliente | Advogado | KPI provável | O que faltou |",
              "|---|---|---|---|---|---|"]
        for l in sorted(apuracao["pendentes"], key=lambda x: x["data"]):
            p.append(f"| {data(l['data'])} | {proc(l['processo'])} | "
                     f"{_titulo_adv(l['cliente'])} | "
                     f"{_nome_curto(l['advogado_responsavel'])} | {l['kpi'] or '—'} | "
                     f"{l['evidencia']} |")
        p.append("")

    fora = apuracao["fora_escopo"]
    if fora:
        p += ['<div class="quebra"></div>', "", "## C. Atos fora do escopo dos KPIs", "",
              f"Os {len(fora)} atos abaixo foram capturados e descartados, com o motivo. "
              "Estão aqui para que a exclusão seja auditável — nenhum ato some em silêncio.", ""]
        por_motivo = defaultdict(list)
        for l in fora:
            por_motivo[l["kpi_motivo"]].append(l)
        for m, itens in sorted(por_motivo.items(), key=lambda x: -len(x[1])):
            p += [f"### {motivo(m)} ({len(itens)})", "",
                  "| Data | Processo | Cliente | Advogado | Classe |", "|---|---|---|---|---|"]
            for l in sorted(itens, key=lambda x: x["data"]):
                p.append(f"| {data(l['data'])} | {proc(l['processo'])} | "
                         f"{_titulo_adv(l['cliente'])} | "
                         f"{_nome_curto(l['advogado_responsavel'])} | "
                         f"{(l['classe'] or '').title()} |")
            p.append("")

    p.append(RODAPE_METODO)
    return "\n".join(p)


# ============================================================
# 3. DIARIO DE DECISOES (cronologico, dia a dia)
# ============================================================
#
# O executivo agrupa por carteira e a ficha por advogado - nenhum dos dois
# responde "o que saiu no dia 04". Este documento e' o outro eixo: a linha do
# tempo do periodo, com o dispositivo de cada decisao e o LINK da publicacao no
# DJEN, para abrir o inteiro teor sem procurar no PJe.

_DIAS_SEMANA = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                "sexta-feira", "sábado", "domingo")


def _dias_do_periodo(linhas):
    """Todos os dias entre a primeira e a ultima publicacao, inclusive os
    vazios - dia sem decisao e' informacao, nao lacuna."""
    from datetime import date, timedelta
    datas = sorted({l["data"] for l in linhas if l.get("data")})
    if not datas:
        return []
    ini = date(*map(int, datas[0].split("-")))
    fim = date(*map(int, datas[-1].split("-")))
    saida, atual = [], ini
    while atual <= fim:
        saida.append(atual)
        atual += timedelta(days=1)
    return saida


def montar_decisoes(linhas, apuracao, periodo, oabs, gerado_em):
    from collections import defaultdict as _dd
    computadas, pendentes = _dd(list), _dd(list)
    capturados = _dd(int)
    for l in linhas:
        capturados[l.get("data")] += 1
    for l in apuracao["computadas"]:
        computadas[l["data"]].append(l)
    for l in apuracao["pendentes"]:
        pendentes[l["data"]].append(l)

    total = len(apuracao["computadas"])
    p = [_ESTILO, "# Decisões do período, dia a dia", "",
         _meta_doc(periodo, oabs, gerado_em), "",
         f"As **{total} decisões** que entraram no KPI, em ordem cronológica, com o trecho do "
         "dispositivo que classificou cada uma e o link para a publicação no DJEN — é por ele "
         "que se abre o inteiro teor, sem procurar no PJe.", "",
         "Dia sem decisão aparece assim mesmo: o KPI mede o que foi **decidido**, e saber em que "
         "dias nada foi decidido faz parte da leitura do período.", ""]

    # índice do período
    # A semana de cada dia vem do CALENDARIO, nao das linhas: 05 e 06/09 nao tem
    # publicacao e sairiam sem semana no indice, embora pertencam a Semana 01.
    dias_periodo = [d.isoformat() for d in _dias_do_periodo(linhas)]
    sem_por_dia = {iso: kpi_exito.rotular_semana(n)
                   for iso, n in kpi_exito.numerar_semanas(dias_periodo).items()}
    p += ["| Semana | Dia | Atos capturados | Decisões no KPI | A conferir |",
          "|---|---|---:|---:|---:|"]
    for d in _dias_do_periodo(linhas):
        iso = d.isoformat()
        n = len(computadas.get(iso, []))
        p.append(f"| {sem_por_dia.get(iso) or '—'} | "
                 f"{d.strftime('%d/%m')} ({_DIAS_SEMANA[d.weekday()][:3]}) | "
                 f"{capturados.get(iso, 0)} | {'**' + str(n) + '**' if n else '—'} | "
                 f"{len(pendentes.get(iso, [])) or '—'} |")
    p.append("")

    # Agrupamento por semana: a GJ acompanha "Semana 01", "Semana 02". A
    # numeracao vem de kpi_exito para ser a mesma do executivo e do CSV.
    semana_de = kpi_exito.numerar_semanas(dias_periodo)
    semana_atual = object()

    for i, d in enumerate(_dias_do_periodo(linhas)):
        iso = d.isoformat()
        itens = computadas.get(iso, [])
        pend = pendentes.get(iso, [])

        n_sem = semana_de.get(iso)
        if n_sem != semana_atual:
            semana_atual = n_sem
            ini, fim = kpi_exito.intervalo_da_semana(linhas, n_sem)
            b = (apuracao.get("por_semana", {}).get(n_sem) or {}).get("rural")
            periodo_sem = (f"{ini.strftime('%d/%m')} a {fim.strftime('%d/%m')}"
                           if ini and fim else "")
            resumo = (f" · carteira rural {pct(b['taxa'])} "
                      f"({num(b['num'])}/{num(b['den'])})" if b and b["den"] else "")
            p += ['<div class="quebra"></div>' if i else "", "",
                  f"# {kpi_exito.rotular_semana(n_sem)}"
                  + (f" — {periodo_sem}" if periodo_sem else ""), "",
                  f"*{_plural(sum(len(computadas.get(x.isoformat(), [])) for x in _dias_do_periodo(linhas) if semana_de.get(x.isoformat()) == n_sem), 'decisão', 'decisões')} no KPI{resumo}.*",
                  ""]

        p += ["",
              f"## {d.strftime('%d/%m/%Y')} — {_DIAS_SEMANA[d.weekday()]}", ""]

        if not itens and not pend:
            nota = ("sem publicações — fim de semana"
                    if d.weekday() >= 5 else
                    f"{capturados.get(iso, 0)} ato(s) capturado(s), nenhum classificável como "
                    "decisão")
            p += [f"*{nota}.*", ""]
            continue

        if itens:
            soma = sum(x["contribuicao"] for x in itens)
            base = sum(x["peso"] for x in itens)
            p += [f"*{capturados.get(iso, 0)} atos capturados · "
                  f"{_plural(len(itens), 'decisão', 'decisões')} no KPI · "
                  f"{num(soma)} de {num(base)} pontos no dia.*", ""]
            for l in itens:
                marca = " · **a confirmar**" if l.get("confirmar_resultado") else ""
                # Tabela em HTML, nao em Markdown: a tabela de Markdown exige
                # linha de cabecalho, e um cabecalho vazio vira uma faixa
                # escura sem texto em cima de cada decisao.
                confirma = (' · <b>a confirmar</b>' if l.get("confirmar_resultado") else "")
                p += [f"### {_titulo_adv(l['cliente'])} — {_res(l['resultado'])}", "",
                      '<table class="ficha">',
                      f"<tr><td>Processo</td><td>{proc(l['processo'])} "
                      f"({l['tribunal']} · {(l['classe'] or '').title()})</td></tr>",
                      f"<tr><td>Advogado responsável</td>"
                      f"<td>{_titulo_adv(l['advogado_responsavel'])}</td></tr>",
                      f"<tr><td>Carteira</td><td>{l['carteira']}</td></tr>",
                      f"<tr><td>KPI</td><td>{l['kpi']} — {rotulo_kpi(l['kpi'])}</td></tr>",
                      f"<tr><td>Peso × favorável</td><td>{num(l['peso'])} × "
                      f"{num(l['favoravel'])} = <b>{num(l['contribuicao'])}</b></td></tr>",
                      f"<tr><td>Confiança</td>"
                      f"<td>{_conf(l['confianca'])}{confirma}</td></tr>",
                      "</table>", "",
                      f'<div class="disp">Dispositivo lido: “{curto(l["evidencia"], 220)}”</div>',
                      ""]
                if l.get("link_djen"):
                    p += [f"[Abrir a publicação no DJEN]({l['link_djen']})", ""]

        if pend:
            p += [f"**A conferir neste dia ({len(pend)})** — ato que o classificador marcou como "
                  "possível decisão e não fechou:", ""]
            for l in pend:
                p.append(f"- {proc(l['processo'])} · {_titulo_adv(l['cliente'])} "
                         f"({l['kpi'] or 'KPI a definir'})"
                         + (f" — [publicação]({l['link_djen']})" if l.get("link_djen") else ""))
            p.append("")

    p.append(RODAPE_METODO)
    return "\n".join(p)


# ============================================================
# 4. FICHAS POR ADVOGADO
# ============================================================

def montar_fichas(linhas, apuracao, periodo, oabs, gerado_em):
    computadas = apuracao["computadas"]
    advogados = sorted({l["advogado_responsavel"] for l in computadas})

    p = [_ESTILO, "# Fichas individuais — apuração de KPI", "",
         _meta_doc(periodo, oabs, gerado_em), "",
         "Uma ficha por advogado com decisão classificada no período. **A ficha é insumo de "
         "conversa, não instrumento de avaliação**: o § 15 do Plano de Carreira avalia os "
         "últimos 12 meses, em janelas de junho e dezembro, e o § 7.1 é expresso em dizer que "
         "as metas são referências para progressão, não cortes automáticos.", ""]

    for i, adv in enumerate(advogados):
        deste = [l for l in computadas if l["advogado_responsavel"] == adv]
        p += ['<div class="quebra"></div>' if i else "", "",
              f"## {_titulo_adv(adv)}", ""]

        blocos = apuracao["por_advogado"][adv]
        p += ["| Carteira | Num. | Den. | Taxa | Decisões |", "|---|---:|---:|---:|---:|"]
        for c, b in sorted(blocos.items()):
            if b["den"]:
                p.append(f"| {c} | {num(b['num'])} | {num(b['den'])} | "
                         f"**{pct(b['num'] / b['den'])}** | {b['n']} |")
        p.append("")

        # composicao por KPI - dentro de cada carteira, nunca somadas
        por_kpi = defaultdict(lambda: defaultdict(lambda: {"num": 0.0, "den": 0.0, "n": 0}))
        for l in deste:
            b = por_kpi[l["carteira"]][l["kpi"]]
            b["num"] += l["contribuicao"]
            b["den"] += l["peso"]
            b["n"] += 1
        if sum(len(ks) for ks in por_kpi.values()) > 1:
            p += ["**Composição por KPI (por carteira)**", "",
                  "| Carteira | KPI | Num. | Den. | Taxa | Decisões |",
                  "|---|---|---:|---:|---:|---:|"]
            for c in ("rural", "diversa"):
                for k in kpi_exito.PESOS:
                    if k in por_kpi.get(c, {}):
                        b = por_kpi[c][k]
                        p.append(f"| {c} | {k} — {rotulo_kpi(k)} | {num(b['num'])} | "
                                 f"{num(b['den'])} | {pct(b['num'] / b['den'])} | {b['n']} |")
            p.append("")

        p += ["**Decisões do período**", "",
              "| Data | Cliente | Processo | Carteira | KPI | Resultado | Contrib. |",
              "|---|---|---|---|---|---|---:|"]
        for l in sorted(deste, key=lambda x: x["data"]):
            p.append(f"| {data(l['data'])} | {_titulo_adv(l['cliente'])} | "
                     f"{proc(l['processo'])} | {l['carteira']} | "
                     f"{l['kpi']} | {_res(l['resultado'])} | {num(l['contribuicao'])} |")
        p.append("")

        den_total = sum(b["den"] for b in blocos.values())
        if den_total < 5:
            p += ['<div class="alerta"><span class="tit">Base insuficiente para tendência</span>',
                  f"Denominador de {num(den_total)} no período. Uma única decisão em outro "
                  f"sentido move esta taxa em dezenas de pontos percentuais — o número descreve "
                  f"o que foi decidido nestes dias, não o desempenho do advogado.</div>", ""]

        pend_adv = [l for l in apuracao["pendentes"]
                    if l["advogado_responsavel"] == adv]
        if pend_adv:
            p += [f"**A conferir ({len(pend_adv)})** — atos que a automação não fechou:", ""]
            for l in pend_adv:
                p.append(f"- {data(l['data'])} · {proc(l['processo'])} · "
                         f"{_titulo_adv(l['cliente'])} ({l['kpi'] or 'KPI a definir'})")
            p.append("")

    p.append(RODAPE_METODO)
    return "\n".join(p)


# ============================================================
# GERACAO
# ============================================================

def gerar(linhas, apuracao, periodo, oabs, pasta, sufixo, gerado_em=None,
          ressalvas_extra="", em_pdf=True):
    """Escreve os tres .md e (se em_pdf) converte cada um em PDF.

    Retorna lista de (caminho_md, caminho_pdf_ou_None).
    """
    from datetime import datetime
    gerado_em = gerado_em or datetime.now().strftime("%d/%m/%Y")
    os.makedirs(pasta, exist_ok=True)

    docs = [
        (f"RELATORIO_KPI_{sufixo}.md",
         montar_relatorio(linhas, apuracao, periodo, oabs, gerado_em, ressalvas_extra)),
        (f"DECISOES_KPI_{sufixo}.md",
         montar_decisoes(linhas, apuracao, periodo, oabs, gerado_em)),
        (f"ANEXO_KPI_{sufixo}.md",
         montar_anexo(linhas, apuracao, periodo, oabs, gerado_em)),
        (f"FICHAS_KPI_{sufixo}.md",
         montar_fichas(linhas, apuracao, periodo, oabs, gerado_em)),
    ]

    saidas = []
    for nome, conteudo in docs:
        caminho = os.path.join(pasta, nome)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        pdf = None
        if em_pdf:
            try:
                import md_para_pdf
                pdf = md_para_pdf.converter(caminho)
            except Exception as e:
                print(f"  Aviso: nao foi possivel gerar o PDF de {nome}: {e}")
        saidas.append((caminho, pdf))
    return saidas
