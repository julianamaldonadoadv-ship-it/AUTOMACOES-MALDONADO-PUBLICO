# -*- coding: utf-8 -*-
"""
Triagem de Controladoria - Maldonado Advogados
================================================
Classificador de 1a passada para intimacoes/publicacoes do DJEN, aplicado ao
nicho do escritorio (divida rural bancaria). Faz o trabalho MECANICO
(extrair tipo de ato, calcular prazo preliminar, sinalizar candidata a tese)
via regex/palavra-chave - e' rapido e 100% auditavel, mas e' so a 1a passada.

Casos ambiguos (o classificador nao tem certeza, ou o texto e' complexo) sao
sinalizados como "REVISAO_MANUAL" e devem ser colados no agente Claude
`.claude/agents/maldonado-controladoria.md` para leitura fina - o classificador
NUNCA decide sozinho qual das 3 teses cabe quando o texto for ambiguo (mesma
regra de ouro do agente).

Nao protocola, nao cria tarefa - so classifica. A criacao de tarefa no ADVBOX
e feita por quem chama este modulo (OPERACIONAL/main.py, comando `triagem`),
sempre com confirmacao explicita.
"""
import re
from datetime import datetime, timedelta


# ============================================================
# 1. TIPO DE ATO (a partir do campo tipoComunicacao + texto)
# ============================================================

# ATENCAO: "julgamento antecipado" NAO entra aqui. Decisao saneadora/ordinatoria
# costuma dizer "as partes poderao se manifestar pelo julgamento antecipado do
# merito" so para ordenar fase futura - isso ja fez o classificador rotular uma
# decisao de tutela como sentenca (processo 0000000-00.0000.0.00.0000, 08/09/2026)
# e, com isso, apontar o prazo errado.
_PALAVRAS_SENTENCA = ("sentença", "sentenca", "julgo procedente", "julgo improcedente",
                       "julgo parcialmente", "julgo extinto", "resolvo o mérito",
                       "resolvo o merito", "art. 487")
_PALAVRAS_DECISAO = ("decisão", "decisao", "indefiro", "defiro", "tutela de urgência",
                      "tutela de urgencia", "agravo de instrumento")

# Marcadores de decisao INTERLOCUTORIA sobre tutela - tem precedencia sobre
# qualquer outro marcador, porque e' a hipotese recorrivel do art. 1.015, I, CPC.
_MARCADORES_TUTELA = ("indefiro, por ora, a tutela", "indefiro a tutela",
                       "indefiro o pedido de tutela", "defiro a tutela",
                       "defiro em parte a tutela", "defiro parcialmente a tutela",
                       "concedo a tutela", "revogo a tutela")
_PALAVRAS_AUDIENCIA = ("audiência", "audiencia", "designo audiência", "designo audiencia")
_PALAVRAS_CIENCIA = ("ciência", "ciencia", "dar-se ciência", "tomar ciência",
                      "arquivamento", "baixa definitiva")
_PALAVRAS_PRAZO = ("prazo de", "manifeste-se", "intime-se para", "no prazo",
                    "apresente", "junte", "cumpra")


_CIENCIA_PURA = (
    "arquivem-se", "arquive-se", "arquivem se", "ao arquivo",
    "ciencia da expedicao", "ciência da expedição",
    "intimada acerca da expedicao", "intimada acerca da expedição",
    "expedicao do oficio", "expedição do ofício",
    "ordem de transferencia dos valores", "ordem de transferência dos valores",
    "nada mais havendo",
)

# O ato manda a PARTE CONTRARIA se manifestar - nao corre prazo para nos.
# Ex.: "Ao exequente para se manifestar quanto a excecao de pre-executividade"
# (0000000-00.0000, 10/09/2026), em que o escritorio esta no polo executado.
_ATO_DA_PARTE_CONTRARIA = (
    "ao exequente para se manifestar", "ao exequente para manifestar",
    "intime-se o exequente para", "intime-se a exequente para",
    "vistas a parte exequente", "vista a parte exequente",
    "ao autor para se manifestar", "ao requerente para se manifestar",
)


def _e_ciencia_pura(texto_junto: str) -> bool:
    return any(p in texto_junto for p in _CIENCIA_PURA)


def _tem_conteudo_decisorio(texto_junto: str) -> bool:
    return (any(p in texto_junto for p in _MARCADORES_TUTELA)
            or any(p in texto_junto for p in _PALAVRAS_SENTENCA))


def ato_dirigido_a_parte_contraria(texto: str) -> bool:
    """Indicio de que a providencia e' da outra parte. Nao e' conclusao: o
    classificador nao sabe em que polo o escritorio esta - quem confirma e' o
    campo `partes_polo` do DJEN ou a leitura humana.

    So vale em despacho CURTO (ate 1.200 caracteres). Em despacho longo o mesmo
    texto costuma intimar os dois lados - o de cumprimento de sentenca manda o
    executado pagar em 15 dias E dar vista ao exequente para atualizar o debito;
    marcar aquilo como "ato da outra parte" esconderia o prazo do nosso cliente."""
    t = (texto or "").lower()
    if len(t) > 1200:
        return False
    return any(p in t for p in _ATO_DA_PARTE_CONTRARIA)


# ============================================================
# RESULTADO DO ATO (marcador de KPI - POP-CJ-002)
# ============================================================
# So classifica quando o resultado esta EXPLICITO. Ambiguidade devolve None e
# sobe como pendencia - regra da Dra. Juliana (10/09/2026): a rotina nao chuta
# resultado, porque KPI errado e' pior que KPI faltando.
_RESULTADOS = (
    # (chave em equipe.TIPOS_RESULTADO, marcadores no texto)
    ("LIMINAR_PARCIAL", ("defiro parcialmente a tutela", "defiro em parte a tutela",
                         "parcialmente deferida a tutela", "tutela parcialmente deferida")),
    ("LIMINAR_INDEFERIDA", ("indefiro a tutela", "indefiro o pedido de tutela",
                            "indefiro a liminar", "indefiro o pedido liminar",
                            "nao defiro a tutela", "não defiro a tutela",
                            "ausentes os requisitos para a concessao da tutela",
                            "ausentes os requisitos para a concessão da tutela")),
    ("LIMINAR_DEFERIDA", ("defiro a tutela", "defiro o pedido de tutela",
                          "concedo a tutela", "defiro a liminar", "concedo a liminar")),
    ("SENTENCA_EXTINCAO", ("julgo extinto o processo", "extingo o processo",
                           "julgo extinta a execucao", "julgo extinta a execução")),
    ("SENTENCA_PARCIAL", ("julgo parcialmente procedente", "procedente em parte o pedido")),
    ("SENTENCA_IMPROCEDENTE", ("julgo improcedente", "julgo improcedentes")),
    ("SENTENCA_PROCEDENTE", ("julgo procedente", "julgo procedentes")),
    ("ACORDAO_PARCIAL", ("recurso parcialmente provido", "deram parcial provimento",
                         "parcialmente provido nos termos do voto")),
    ("ACORDAO_IMPROCEDENTE", ("recurso nao provido", "recurso não provido",
                              "negaram provimento", "nego provimento",
                              "recurso desprovido", "improvido")),
    ("ACORDAO_PROCEDENTE", ("recurso provido", "deram provimento", "dou provimento")),
    ("ACORDO_CELEBRADO", ("homologo o acordo", "acordo homologado")),
)


def classificar_resultado(texto: str):
    """Devolve a chave do marcador de resultado (equipe.TIPOS_RESULTADO) ou None.

    A ordem importa: 'parcialmente provido' tem que casar antes de 'provido',
    e 'indefiro a tutela' antes de 'defiro a tutela'.
    """
    t = _sem_acento_min(texto)
    for chave, marcadores in _RESULTADOS:
        if any(_sem_acento_min(m) in t for m in marcadores):
            return chave
    return None


def _sem_acento_min(texto: str) -> str:
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFD", str(texto or ""))
                if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def classificar_tipo_ato(texto: str, tipo_comunicacao: str = "") -> str:
    """Classifica o ato em uma categoria ampla, a partir de palavras-chave.

    Retorna uma das strings: 'sentenca', 'decisao', 'audiencia',
    'intimacao_com_prazo', 'ciencia', 'indefinido'.
    """
    t = (texto or "").lower()
    tc = (tipo_comunicacao or "").lower()
    junto = f"{tc} {t}"

    # "cumprimento de sentenca" e' FASE, nao e' sentenca - sem isso todo despacho
    # de cumprimento entrava como ato decisorio e abria a janela dos ED a toa
    # (levantado nas publicacoes de 10/09/2026).
    junto_sem_fase = junto.replace("cumprimento de sentença", " ").replace(
        "cumprimento de sentenca", " ")

    # Ciencia PURA vem antes de tudo: ato que so comunica (arquivamento,
    # expedicao de oficio, transferencia de valores) nao abre D-5/D-3. Sem isso
    # esses itens caiam em "indefinido" e geravam tarefa a toa - levantado na
    # leitura das 21 publicacoes de 10/09/2026.
    # Ciencia pura so vale se NAO houver ato decisorio no mesmo texto: uma
    # decisao longa que termina com "arquivem-se" continua sendo decisao.
    if _e_ciencia_pura(junto) and not _tem_conteudo_decisorio(junto_sem_fase):
        return "ciencia"

    # Decisao sobre tutela vem PRIMEIRO: e' o ato recorrivel por agravo
    # (art. 1.015, I) e nao pode ser mascarado por "audiencia"/"julgamento
    # antecipado" citados de passagem no mesmo despacho.
    if any(p in junto for p in _MARCADORES_TUTELA):
        return "decisao"
    if any(p in junto_sem_fase for p in _PALAVRAS_SENTENCA):
        return "sentenca"
    if any(p in junto for p in _PALAVRAS_AUDIENCIA):
        return "audiencia"
    if any(p in junto for p in _PALAVRAS_DECISAO):
        return "decisao"
    if any(p in junto for p in _PALAVRAS_PRAZO):
        return "intimacao_com_prazo"
    if any(p in junto for p in _PALAVRAS_CIENCIA):
        return "ciencia"
    return "indefinido"


# ============================================================
# 2. PRAZO (extração de "N dias" do texto + cálculo preliminar)
# ============================================================

_REGEX_PRAZO_DIAS = re.compile(r"prazo\s+de\s+(\d{1,3})\s*\(?[a-z]*\)?\s*dias", re.IGNORECASE)


def extrair_prazo_dias(texto: str):
    """Tenta extrair o numero de dias do prazo citado no texto. Retorna int ou None."""
    if not texto:
        return None
    m = _REGEX_PRAZO_DIAS.search(texto)
    return int(m.group(1)) if m else None


def calcular_data_limite(data_disponibilizacao: str, dias: int, dias_uteis: bool = True):
    """Calcula uma data-limite PRELIMINAR a partir da data de disponibilizacao.

    ATENCAO: e' um calculo aproximado (so pula sabado/domingo quando
    dias_uteis=True; nao considera feriados forenses nem o inicio de contagem
    no 1o dia util seguinte). Sempre rotular como "preliminar, sujeito a
    conferencia" na saida - nunca apresentar como definitivo.
    """
    if not data_disponibilizacao or not dias:
        return None
    try:
        data = datetime.strptime(data_disponibilizacao[:10], "%Y-%m-%d")
    except ValueError:
        return None

    if not dias_uteis:
        return (data + timedelta(days=dias)).strftime("%Y-%m-%d")

    restantes = dias
    while restantes > 0:
        data += timedelta(days=1)
        if data.weekday() < 5:  # 0-4 = seg-sex
            restantes -= 1
    return data.strftime("%Y-%m-%d")


# ============================================================
# 3. TESE DE DÍVIDA RURAL (candidata, via palavra-chave — 1a passada)
# ============================================================

_PALAVRAS_PRORROGACAO = ("prorrogação", "prorrogacao", "alongamento", "cédula de crédito rural",
                          "cedula de credito rural", "cpr", "manual de crédito rural", "súmula 298",
                          "sumula 298")
_PALAVRAS_MORA = ("descaracterização da mora", "descaracterizacao da mora", "tema 28",
                   "declaratória", "declaratoria")
_PALAVRAS_REVISIONAL = ("ação revisional", "acao revisional", "revisão de contrato",
                         "revisao de contrato", "capitalização", "capitalizacao",
                         "juros abusivos", "súmula 539", "sumula 539", "súmula 541", "sumula 541")


def classificar_tese_candidata(texto: str):
    """1a passada por palavra-chave. Retorna uma tupla (tese, confianca).

    tese: 'prorrogacao' | 'descaracterizacao_mora' | 'revisional' | None
    confianca: 'baixa' (so 1 sinal fraco) | 'media' (varios sinais) — NUNCA 'alta':
      confirmação definitiva da tese fica para leitura humana/IA fina, nunca
      só para o classificador mecânico (mesmo guard-rail do agente
      maldonado-divida-rural.md: nunca escolher a tese sozinho em caso ambíguo).
    """
    t = (texto or "").lower()
    pontos = {
        "prorrogacao": sum(1 for p in _PALAVRAS_PRORROGACAO if p in t),
        "descaracterizacao_mora": sum(1 for p in _PALAVRAS_MORA if p in t),
        "revisional": sum(1 for p in _PALAVRAS_REVISIONAL if p in t),
    }
    tese, pts = max(pontos.items(), key=lambda kv: kv[1])
    if pts == 0:
        return None, None
    confianca = "media" if pts >= 2 else "baixa"
    return tese, confianca


_PECA_POR_TESE = {
    "prorrogacao": "Ação de prorrogação compulsória de contratos rurais c/c tutela cautelar antecedente",
    "descaracterizacao_mora": "Ação declaratória de descaracterização de mora (Tema 28/STJ)",
    "revisional": "Ação revisional de contrato bancário rural c/c tutela de urgência",
}


# ============================================================
# 3.5 RECURSO CABIVEL — triagem obrigatoria ED x AGRAVO
# ============================================================
# REGRA DA DRA. JULIANA (definida em 08/09/2026, vale para TODO ato decisorio):
#
#   Antes de assumir que o recurso e' agravo de instrumento, e' OBRIGATORIO
#   cotejar a PETICAO INICIAL (ou a ultima manifestacao da parte) com a DECISAO
#   e verificar se ha, quanto ao (in)deferimento da tutela:
#       (a) CONTRADICAO  - a decisao briga com ela mesma ou com os autos;
#       (b) OBSCURIDADE  - nao da' pra saber o que foi decidido / com que alcance;
#       (c) OMISSAO      - deixou de enfrentar pedido, documento ou argumento
#                          concreto da inicial (inclui a fundamentacao generica
#                          do art. 489, §1o, III e IV, do CPC).
#   Havendo QUALQUER um dos tres -> EMBARGOS DE DECLARACAO (5 dias uteis,
#   art. 1.023), que INTERROMPEM o prazo do agravo (art. 1.026).
#   Nao havendo nenhum dos tres -> AGRAVO DE INSTRUMENTO (15 dias uteis,
#   art. 1.015, I).
#
# Este modulo NAO decide isso sozinho: ele nao le a inicial. O que ele faz e'
# (1) marcar o ato como pendente desse cotejo, (2) levantar INDICIOS de vicio
# no texto da decisao, e (3) devolver as DUAS datas — porque a janela dos ED
# fecha muito antes da do agravo, e quem so' anota o prazo do agravo perde o ED
# em silencio.

# Feriados nacionais/forenses fixos. Nao cobre feriado local nem suspensao de
# expediente do tribunal - por isso toda data sai rotulada como "conferir".
_FERIADOS = {
    "01-01", "04-21", "05-01", "09-07", "10-12", "11-02", "11-15", "11-20", "12-25",
}


def _e_dia_util(d) -> bool:
    return d.weekday() < 5 and d.strftime("%m-%d") not in _FERIADOS


def _somar_dias_uteis(data_inicio, dias: int):
    """Soma N dias uteis excluindo o dia do comeco (art. 224, caput, CPC)."""
    d = data_inicio
    restantes = dias
    while restantes > 0:
        d += timedelta(days=1)
        if _e_dia_util(d):
            restantes -= 1
    return d


def calcular_prazo_recursal(data_disponibilizacao: str, dias: int):
    """Prazo recursal a partir da DISPONIBILIZACAO no DJEN.

    Aplica art. 224, §3o (publicacao = 1o dia util seguinte a disponibilizacao)
    e conta em dias uteis (art. 219). Preliminar: nao conhece feriado local nem
    suspensao de prazo do tribunal — sempre conferir.
    """
    if not data_disponibilizacao or not dias:
        return None
    try:
        disp = datetime.strptime(data_disponibilizacao[:10], "%Y-%m-%d")
    except ValueError:
        return None
    pub = disp + timedelta(days=1)
    while not _e_dia_util(pub):
        pub += timedelta(days=1)
    return _somar_dias_uteis(pub, dias).strftime("%Y-%m-%d")


# Indicios TEXTUAIS de vicio. Nao provam nada sozinhos — a confirmacao so sai do
# cotejo com a inicial. Servem para dizer a controladoria "olha aqui primeiro".
_INDICIOS_OMISSAO = (
    # fundamentacao generica: motivo que serviria para qualquer decisao
    ("nao demonstram a verossimilhanca", "fundamentacao generica: nao diz QUAL documento nem QUAL alegacao (art. 489, §1o, III)"),
    ("não demonstram a verossimilhança", "fundamentacao generica: nao diz QUAL documento nem QUAL alegacao (art. 489, §1o, III)"),
    ("ausentes os requisitos", "fundamentacao generica: nao indica qual requisito do art. 300 faltou"),
    ("nao vislumbro", "fundamentacao generica sem enfrentamento do caso concreto"),
    ("não vislumbro", "fundamentacao generica sem enfrentamento do caso concreto"),
    ("por ora", "decisao provisoria/condicionada: conferir se o pedido foi apreciado ou apenas adiado"),
    ("necessidade de formacao do contraditorio", "postergou a tutela sem enfrentar o periculum alegado na inicial"),
    ("necessidade de formação do contraditório", "postergou a tutela sem enfrentar o periculum alegado na inicial"),
)
_INDICIOS_CONTRADICAO = (
    ("nao acarretara para o autor dano", "afirma ausencia de perigo de dano: cotejar com o perigo concreto narrado na inicial"),
    ("não acarretará para o autor dano", "afirma ausencia de perigo de dano: cotejar com o perigo concreto narrado na inicial"),
    ("poder discricionario", "trata tutela de urgencia como discricionariedade: cotejar, art. 300 e' vinculado aos requisitos"),
    ("poder discricionário", "trata tutela de urgencia como discricionariedade: cotejar, art. 300 e' vinculado aos requisitos"),
)


def _levantar_indicios(texto: str) -> list:
    t = (texto or "").lower()
    achados = []
    for marcador, motivo in _INDICIOS_OMISSAO:
        if marcador in t:
            achados.append(("possivel OMISSAO / fundamentacao deficiente", motivo))
    for marcador, motivo in _INDICIOS_CONTRADICAO:
        if marcador in t:
            achados.append(("possivel CONTRADICAO", motivo))
    # dedup preservando ordem
    vistos, unicos = set(), []
    for a in achados:
        if a[1] not in vistos:
            vistos.add(a[1])
            unicos.append(a)
    return unicos


CHECKLIST_ED = (
    "CONTRADICAO: a decisao afirma algo que briga com outro trecho dela mesma "
    "ou com documento/fato incontroverso dos autos?",
    "OBSCURIDADE: da' pra saber exatamente o que foi decidido e com que alcance "
    "(o que ficou deferido, o que ficou indeferido, o que ficou para depois)?",
    "OMISSAO: a decisao enfrentou TODOS os pedidos, documentos e argumentos "
    "concretos da inicial sobre a tutela — ou usou motivo generico que serviria "
    "para qualquer processo (art. 489, §1o, III e IV)?",
)


def avaliar_recurso_cabivel(texto: str, tipo_ato: str, data_disponibilizacao: str = None) -> dict:
    """Aplica a regra ED x Agravo. NAO conclui — devolve a triagem pendente.

    Retorna None quando o ato nao e' decisorio (ciencia, mero expediente).
    """
    if tipo_ato not in ("decisao", "sentenca"):
        return None

    if tipo_ato == "sentenca":
        recurso_se_sem_vicio = "APELACAO (15 dias uteis, art. 1.003, §5o)"
        dias_recurso = 15
    else:
        recurso_se_sem_vicio = "AGRAVO DE INSTRUMENTO (15 dias uteis, art. 1.015, I)"
        dias_recurso = 15

    return {
        # A regra e' explicita: o classificador NUNCA fecha isso sozinho.
        "recurso_cabivel": "A DEFINIR — exige cotejo INICIAL x DECISAO",
        "regra": "Dra. Juliana (08/09/2026): so' se descarta ED depois de conferir "
                 "contradicao, obscuridade e omissao quanto a tutela.",
        "checklist_ed": list(CHECKLIST_ED),
        "indicios_de_vicio": _levantar_indicios(texto),
        "se_houver_vicio": "EMBARGOS DE DECLARACAO (5 dias uteis, art. 1.023) — "
                           "interrompem o prazo do recurso principal (art. 1.026)",
        "se_nao_houver_vicio": recurso_se_sem_vicio,
        "prazo_ed": calcular_prazo_recursal(data_disponibilizacao, 5),
        "prazo_recurso_principal": calcular_prazo_recursal(data_disponibilizacao, dias_recurso),
        "documento_necessario": "peticao inicial (ou ultima manifestacao da parte) "
                                "+ integra da decisao",
    }


# ============================================================
# 4. MONTAGEM DO ITEM DE TRIAGEM (saída padrão)
# ============================================================

def montar_item_triagem(resumo_djen: dict, lawsuit_advbox: dict = None) -> dict:
    """Combina um item resumido do DJEN (ver comunica_djen.resumir) com o
    processo correspondente no ADVBOX (se encontrado) e devolve o bloco de
    triagem no formato descrito em .claude/agents/maldonado-controladoria.md.
    """
    texto = resumo_djen.get("texto", "")
    tipo_ato = classificar_tipo_ato(texto, resumo_djen.get("tipo", ""))
    tese, confianca = classificar_tese_candidata(texto)
    dias_prazo = extrair_prazo_dias(texto)
    data_limite = calcular_data_limite(resumo_djen.get("data"), dias_prazo) if dias_prazo else None
    recurso = avaliar_recurso_cabivel(texto, tipo_ato, resumo_djen.get("data"))

    if tipo_ato == "ciencia":
        providencia = "apenas ciencia"
        prioridade = "baixa"
        peca = None
    elif tipo_ato == "audiencia":
        providencia = "preparar audiencia"
        prioridade = "alta"
        peca = None
    elif tipo_ato in ("sentenca", "decisao"):
        # Regra da Dra. Juliana: ato decisorio NUNCA sai da triagem com o recurso
        # ja' definido. Prioridade e' sempre alta — a janela dos ED e' de 5 dias.
        providencia = ("REVISAO_MANUAL - ato decisorio: cotejar INICIAL x DECISAO "
                       "(contradicao/obscuridade/omissao) antes de definir ED ou "
                       "agravo/apelacao")
        prioridade = "alta"
        peca = _PECA_POR_TESE.get(tese) if tese else None
    elif tipo_ato == "intimacao_com_prazo":
        providencia = "REVISAO_MANUAL - ato com prazo/mérito, confirmar peça e prazo"
        prioridade = "alta" if data_limite else "media"
        peca = _PECA_POR_TESE.get(tese) if tese else None
    else:
        providencia = "REVISAO_MANUAL - tipo de ato nao identificado pelo classificador"
        prioridade = "media"
        peca = None

    cliente = None
    responsavel = None
    if lawsuit_advbox:
        clientes = lawsuit_advbox.get("customers") or []
        cliente = clientes[0].get("name") if clientes else None
        responsavel = lawsuit_advbox.get("responsible")

    return {
        "processo": resumo_djen.get("processo"),
        "cliente": cliente or "NAO ENCONTRADO NO ADVBOX - conferir numero do processo",
        "responsavel_advbox": responsavel,
        "tribunal": resumo_djen.get("tribunal"),
        "orgao": resumo_djen.get("orgao"),
        "tipo_ato": tipo_ato,
        "providencia_cabivel": providencia,
        "tese_candidata": tese,
        "confianca_tese": confianca,
        "peca_necessaria": peca,
        "prazo_dias_extraido": dias_prazo,
        "data_limite_preliminar": data_limite,
        "prioridade": prioridade,
        "recurso": recurso,
        "link_djen": resumo_djen.get("link"),
        "trecho": (texto or "")[:300],
        # o teor completo fica disponivel para quem precisa ler o dispositivo
        # (marcador de resultado do KPI, producao da peca) - o trecho de 300
        # caracteres nunca serve para decidir nada (POP-CJ-003-B, etapa 2)
        "trecho_integral": texto or "",
    }


def triagem_lote(resumos_djen: list, lawsuits_por_processo: dict = None) -> list:
    """Aplica montar_item_triagem em lote. lawsuits_por_processo: dict
    {numero_processo_normalizado: lawsuit_dict} vindo do ADVBOX (opcional).
    """
    lawsuits_por_processo = lawsuits_por_processo or {}
    itens = []
    for r in resumos_djen:
        proc_norm = "".join(filter(str.isdigit, r.get("processo") or ""))
        lawsuit = lawsuits_por_processo.get(proc_norm)
        itens.append(montar_item_triagem(r, lawsuit))
    return itens


def imprimir_triagem(itens: list):
    if not itens:
        print("Nenhum item para triagem no periodo informado.")
        return

    prioridades = {"alta": 0, "media": 0, "baixa": 0}
    revisao_manual = 0
    precisam_peca = 0
    pendentes_ed = 0
    sem_controller = 0
    arquivados = 0
    fallback = 0

    print(f"\n{'='*80}\n  TRIAGEM DE CONTROLADORIA — {len(itens)} item(ns)\n{'='*80}")
    for it in sorted(itens, key=lambda x: {"alta": 0, "media": 1, "baixa": 2}.get(x["prioridade"], 1)):
        prioridades[it["prioridade"]] = prioridades.get(it["prioridade"], 0) + 1
        if "REVISAO_MANUAL" in (it["providencia_cabivel"] or ""):
            revisao_manual += 1
        if it["peca_necessaria"]:
            precisam_peca += 1
        if it.get("recurso"):
            pendentes_ed += 1
        if it.get("roteamento") and not it["roteamento"].get("ok"):
            sem_controller += 1
        if (it.get("roteamento") or {}).get("arquivado"):
            arquivados += 1
        if (it.get("roteamento") or {}).get("regra", "").startswith("fallback"):
            fallback += 1

        print(f"\nPROCESSO: {it['processo']}")
        print(f"CLIENTE: {it['cliente']}")
        # Quem lanca a tarefa e' a controller do advogado responsavel (nao mais
        # o Dr. Renan) - ver OPERACIONAL/roteamento_controller.py
        if it.get("roteamento_descricao"):
            print(f"LANCAMENTO: {it['roteamento_descricao']}")
        print(f"TIPO DE ATO: {it['tipo_ato']}")
        print(f"PROVIDENCIA CABIVEL: {it['providencia_cabivel']}")
        if it["tese_candidata"]:
            print(f"TESE CANDIDATA: {it['tese_candidata']} (confianca: {it['confianca_tese']})")
        print(f"PECA NECESSARIA: {it['peca_necessaria'] or '-'}")
        if it["data_limite_preliminar"]:
            print(f"PRAZO (calculo preliminar, conferir): {it['data_limite_preliminar']}")

        rec = it.get("recurso")
        if rec:
            print(f"RECURSO CABIVEL: {rec['recurso_cabivel']}")
            print(f"  -> COM vicio: {rec['se_houver_vicio']}")
            print(f"     prazo ED (preliminar, conferir): {rec['prazo_ed']}")
            print(f"  -> SEM vicio: {rec['se_nao_houver_vicio']}")
            print(f"     prazo (preliminar, conferir): {rec['prazo_recurso_principal']}")
            print(f"  CHECKLIST OBRIGATORIO (precisa da {rec['documento_necessario']}):")
            for i, item in enumerate(rec["checklist_ed"], 1):
                print(f"    {i}. {item}")
            if rec["indicios_de_vicio"]:
                print("  INDICIOS NO TEXTO DA DECISAO (conferir contra a inicial):")
                for vicio, motivo in rec["indicios_de_vicio"]:
                    print(f"    - {vicio}: {motivo}")
            else:
                print("  INDICIOS NO TEXTO: nenhum marcador automatico — "
                      "conferir a inicial mesmo assim.")
        print(f"PRIORIDADE: {it['prioridade']}")
        print(f"LINK DJEN: {it['link_djen']}")
        if it["trecho"]:
            print(f"TRECHO: {it['trecho']}...")

    print(f"\n{'='*80}")
    print(f"  RESUMO: {prioridades['alta']} alta | {prioridades['media']} media | {prioridades['baixa']} baixa")
    print(f"  {revisao_manual} item(ns) marcados p/ REVISAO_MANUAL (colar no agente maldonado-controladoria)")
    print(f"  {precisam_peca} item(ns) com peca candidata identificada")
    if pendentes_ed:
        print(f"  {pendentes_ed} ato(s) decisorio(s) aguardando cotejo INICIAL x DECISAO "
              f"(ED x agravo/apelacao) — ATENCAO: a janela dos ED e' de 5 dias uteis")
    if arquivados:
        print(f"  {arquivados} item(ns) em processo ARQUIVADO/ENCERRADO no ADVBOX — "
              f"em regra nao ha agendamento: a controller confere se cabe algo antes de agendar")
    if fallback:
        print(f"  {fallback} item(ns) cujo responsavel esta fora do mapa de controllers — "
              f"assumidos pela controller de fallback (conferir se o processo tem dono certo)")
    if sem_controller:
        print(f"  {sem_controller} item(ns) SEM controller definida (advogado responsavel fora do "
              f"mapa, ambiguo ou processo sem responsavel) — nao viram tarefa automatica")
    print(f"{'='*80}\n")
