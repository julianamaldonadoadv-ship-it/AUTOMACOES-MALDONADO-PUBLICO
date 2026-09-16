"""
=============================================================================
  KPI DE EXITO JURIDICO PONDERADO - MALDONADO ADVOGADOS
=============================================================================

  Apura a Taxa de Exito Juridico Ponderado a partir das intimacoes capturadas
  no DJEN.

  FONTE DA REGUA: "7 - MANUAL DO EXITO JURIDICO KPI", v1.0, maio/2026
  (Google Doc no Drive do
  escritorio) - CEO Dr. Renan Maldonado e GJ Dra. Juliana de Lara. E' ele que
  define os 4 KPIs, os pesos, o que entra e o que fica de fora. O relatorio
  "Taxa de Exito por Advogado - Jun-Jul-Ago 2026" e' aplicacao da regua a uma
  competencia, nao a regua - onde os dois divergirem, vale o manual (foi o caso
  da meta: 20% no manual, 30% no relatorio de jun-jul).

    Taxa Ponderada = SOMA(peso x favoravel) / SOMA(peso)

    favoravel: Exito = 1,0 | Parcial = 0,5 | Inexito = 0,0

    KPI 1 - Merito (sentenca/acordao) ................ peso 1,0
    KPI 2 - Tutela de 1o grau (liminar) .............. peso 0,4
    KPI 3 - Tutela recursal (efeito suspensivo) ...... peso 0,5
    KPI 4 - Acordo / exito negocial .................. peso 0,5 a 2,0 (humano)

  Meta: 20% por KPI e 20% na taxa geral ponderada (manual, item "Apresentacao
  do modelo") - "geral" DENTRO da carteira: a taxa e' sempre ponderada
  individualmente por carteira, nunca uma taxa do escritorio somando as duas
  (Dra. Juliana, 14/09/2026). Objeto acessorio - gratuidade, custas, honorarios sucumbenciais
  - nao entra em KPI nenhum: o manual mede merito, tutela de 1o grau, tutela
  recursal e exito negocial. Ver `objeto_acessorio()`.

  Recorte oficial: so a carteira de DIVIDAS RURAIS compoe o indicador da
  Presidencia. Processo de outra natureza vai para a CARTEIRA DIVERSA, apurada
  a parte pelo Regulamento de Bonificacao por Exito (regua distinta) - as duas
  saem no relatorio, nunca somadas na mesma taxa.

  -------------------------------------------------------------------------
  O QUE ESTE MODULO E' E O QUE ELE NAO E'
  -------------------------------------------------------------------------
  E' uma PRE-CLASSIFICACAO por palavra-chave sobre o texto do DJEN: palpite,
  nao laudo. Ele diz "isto parece um KPI 2 com resultado inexito, porque o
  dispositivo diz 'indefiro a tutela de urgencia' e o nosso cliente e' autor".
  Quem fecha o numero oficial continua sendo a Gerencia Juridica.

  Por isso toda linha sai com `confianca` e com a `evidencia` (o trecho do
  dispositivo que motivou a classificacao), e o relatorio separa o que esta
  ALTA (pode conferir por amostragem) do que esta A CONFERIR (tem de ser
  lido um a um antes de entrar na planilha).

  Nada e' gravado no ADVBOX nem no Drive. Somente leitura.
=============================================================================
"""
import re
import html
import unicodedata
from collections import defaultdict, OrderedDict

# ============================================================
# 1. REGUA OFICIAL (pesos e classificacao)
# ============================================================

PESOS = OrderedDict([
    ("KPI 1", 1.0),   # merito - sentenca / acordao
    ("KPI 2", 0.4),   # tutela de 1o grau - liminar
    ("KPI 3", 0.5),   # tutela recursal - efeito suspensivo / tutela recursal
    ("KPI 4", None),  # acordo - 0,5 a 2,0 conforme o impacto: a GJ arbitra
])

ROTULO_KPI = {
    "KPI 1": "Merito (sentenca/acordao)",
    "KPI 2": "Tutela de 1o grau (liminar)",
    "KPI 3": "Tutela recursal (efeito suspensivo)",
    "KPI 4": "Acordo / exito negocial",
}

FAVORAVEL = {"exito": 1.0, "parcial": 0.5, "inexito": 0.0}

# Peso default do acordo quando a GJ ainda nao arbitrou. Nao entra na taxa:
# o item sobe como pendencia, porque 0,5 e 2,0 mudam o resultado do mes.
PESO_ACORDO_A_ARBITRAR = None


# ============================================================
# 2. NORMALIZACAO DO TEXTO
# ============================================================

def normalizar(texto):
    """HTML -> texto plano, sem acento, minusculo, espacos colapsados.

    O DJEN devolve TJPR/TJRO em tabela HTML (<table>, &Ccedil;...) e os demais
    em texto corrido. Sem desescapar o HTML antes, 'DECIS&Atilde;O' nunca casa
    com 'decisao'.
    """
    t = html.unescape(texto or "")
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>", " ", t)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().lower()


# Marcadores que abrem o DISPOSITIVO. A leitura do resultado e' feita SO daqui
# para frente: no corpo da decisao o juiz transcreve a decisao agravada, a
# ementa da jurisprudencia citada e o pedido da parte - todos cheios de
# "recurso provido" e "julgo procedente" que nao sao o resultado deste ato.
# (Ex.: 0000000-00.0000.0.00.0000, em que "recurso provido" so aparece dentro
#  de um acordao do TJ-MS citado pela parte.)
_ABERTURAS_DISPOSITIVO = (
    "ante o exposto", "diante do exposto", "do exposto", "isso posto",
    "posto isso", "pelo exposto", "por todo o exposto", "3. dispositivo",
    "iii. dispositivo", "dispositivo ante", "assim, decido", "decido:",
    "em face do exposto", "por tais razoes", "pelas razoes expostas",
    "ex positis",
)

# Em acordao do TJRO/TJPR o resultado vem no campo "decisao:" do cabecalho
# ("decisao:\"...recurso nao provido...\"") ou no fecho da ementa.
_ABERTURA_ACORDAO = re.compile(r"\bdecis[ao]o\s*:\s*[\"']?", re.IGNORECASE)


# Quando nao ha marcador nenhum, lemos so o FECHO do ato - nunca o texto
# inteiro. Decisao monocratica de relator costuma terminar direto no comando
# ("...assim, indefiro o pedido de efeito suspensivo ativo. comunique-se...")
# sem abrir com "ante o exposto"; ja' a jurisprudencia citada e a decisao
# recorrida transcrita ficam no MEIO do texto, no relatorio. Ler so o fecho
# alcanca a primeira sem cair na segunda.
_TAMANHO_FECHO = 1200


def extrair_dispositivo(texto_normalizado):
    """Devolve (trecho_dispositivo, origem).

    origem: 'marcador' (abertura explicita de dispositivo) | 'ementa'
    (acordao publicado so como ementa) | 'fecho' (ultimos caracteres do ato) |
    'texto' (nao deu para recortar nada).

    Prefere a ULTIMA abertura de dispositivo do texto - decisao que resolve
    varios pedidos costuma ter mais de um "ante o exposto", e o que vale e' o
    fecho.
    """
    t = texto_normalizado or ""
    pos = -1
    for marcador in _ABERTURAS_DISPOSITIVO:
        p = t.rfind(marcador)
        if p > pos:
            pos = p
    if pos >= 0:
        return t[pos:], "marcador"

    m = None
    for m in _ABERTURA_ACORDAO.finditer(t):
        pass
    if m:
        return t[m.start():], "marcador"

    # TJPR publica o acordao como ementa pura, sem campo "decisao:" e sem
    # "ante o exposto" - e a ementa FECHA com o resultado ("... RECURSO NAO
    # PROVIDO."). Ai a ementa e' o dispositivo (0000000-00.0000.0.00.0000).
    p = t.find("ementa:")
    if p < 0:
        p = t.find("ementa ")
    if p >= 0:
        return t[p:], "ementa"

    if len(t) > _TAMANHO_FECHO:
        return t[-_TAMANHO_FECHO:], "fecho"
    return t, "texto"


# ============================================================
# 3. POLO DO ESCRITORIO (de que lado estamos)
# ============================================================
#
# Sem isto nao ha como ler o resultado: "recurso nao provido" e' inexito se o
# recurso e' nosso e EXITO se e' do banco. O relatorio da GJ registra os dois
# casos ("AI da parte contraria nao provido" = Exito, Anexo A, jun/2026).

_PAPEIS_ATIVOS = ("autor", "autora", "requerente", "exequente", "embargante",
                  "agravante", "apelante", "impetrante", "recorrente",
                  "reclamante", "suscitante")
_PAPEIS_PASSIVOS = ("reu", "re", "requerido", "requerida", "executado",
                    "executada", "embargado", "embargada", "agravado",
                    "agravada", "apelado", "apelada", "impetrado",
                    "recorrido", "recorrida", "reclamado", "reclamada")

# Quanto texto olhar para tras do nome/OAB para achar o papel. 260 caracteres
# cobrem o bloco "AUTOR: FULANO ADVOGADOS DO AUTOR: ..." sem invadir o bloco
# da parte contraria.
_JANELA_PAPEL = 260


def _tokens_nome(nome):
    n = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode().lower()
    ignorar = {"de", "da", "do", "dos", "das", "e", "s", "a", "sa", "ltda", "me", "eireli"}
    return [p for p in re.findall(r"[a-z]{3,}", n) if p not in ignorar]


# O ADVBOX cadastra o banco/cooperativa como "customer" do processo, ao lado do
# cliente de verdade. Sem separar os dois, o KPI leria o polo do banco.
_MARCAS_INSTITUICAO = ("banco", "cooperativa", "sicredi", "sicoob", "cresol",
                       "credisis", "caixa economica", "bradesco", "itau",
                       "santander", "bmg", "safra", "brde", "basa",
                       "banco da amazonia", "financeira", "s/a", "s.a",
                       "credito", "administradora", "securitizadora",
                       "ministerio publico", "fazenda", "municipio", "estado de")


def clientes_do_escritorio(lawsuit):
    """Separa, entre os `customers` do processo, quem e' o cliente do escritorio.

    O banco tambem entra como customer no ADVBOX; se ele passar por cliente, o
    polo sai invertido e o exito vira inexito.
    """
    todos = (lawsuit or {}).get("customers") or []
    proprios = []
    for c in todos:
        nome = c.get("name") or ""
        n = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
        if any(m in n for m in _MARCAS_INSTITUICAO):
            continue
        proprios.append(c)
    return proprios or todos


def polo_pelas_partes_djen(partes_polo, clientes):
    """Polo a partir do campo `destinatarios[].polo` do DJEN ("A"/"P").

    E' a ancora mais confiavel: vem estruturada do CNJ, nao depende da redacao
    do tribunal e existe ate quando a publicacao e' so a ementa (TJPR).
    """
    if not partes_polo or not clientes:
        return None

    alvos = []
    for c in clientes:
        toks = _tokens_nome(c.get("name"))
        if toks:
            alvos.append((c.get("name"), set(toks)))
    if not alvos:
        return None

    for nome_cli, toks_cli in alvos:
        for p in partes_polo:
            toks_parte = set(_tokens_nome(p.get("nome")))
            if not toks_parte:
                continue
            comuns = toks_cli & toks_parte
            # nome de pessoa: 2 tokens iguais ja' identificam; nome de 1 token
            # so casa se for identico
            minimo = 2 if min(len(toks_cli), len(toks_parte)) >= 2 else 1
            if len(comuns) >= minimo:
                polo = {"A": "ativo", "P": "passivo"}.get((p.get("polo") or "").upper())
                if polo:
                    return {"polo": polo, "confianca": "alta",
                            "evidencia": f"DJEN destinatarios: '{p.get('nome')}' "
                                         f"polo={p.get('polo')} (cliente {nome_cli})"}
    return None


def detectar_polo(texto_normalizado, oabs_escritorio=None, nome_cliente=None):
    """Descobre se o escritorio esta no polo ativo ou passivo DESTE processo.

    Fallback textual, usado quando `polo_pelas_partes_djen` nao resolve:
      1. a OAB do escritorio no texto (o DJEN lista o advogado ao lado da parte);
      2. o nome do cliente do ADVBOX.

    Retorna dict com polo ('ativo'/'passivo'/None), confianca e evidencia.
    """
    t = texto_normalizado or ""
    oabs = oabs_escritorio or []

    ancoras = []
    for numero, uf in oabs:
        # "ro5769", "ro 5769", "ro5769a" (o 'a' de advogado de outro estado),
        # "oab ro005769" (TRF2 zera a esquerda)
        padrao = re.compile(
            r"(?:oab\s*n?o?\s*)?%s\s*0*%s\s*a?\b" % (uf.lower(), numero)
            + r"|" +
            r"%s\s*-\s*%s\b" % (numero, uf.lower()),
            re.IGNORECASE)
        for m in padrao.finditer(t):
            ancoras.append(("oab", m.start()))

    if nome_cliente:
        toks = _tokens_nome(nome_cliente)
        if toks:
            # exige os dois primeiros tokens juntos para nao casar "maria" solto
            alvo = r"\s+".join(re.escape(x) for x in toks[:2])
            for m in re.finditer(alvo, t):
                ancoras.append(("cliente", m.start()))

    if not ancoras:
        return {"polo": None, "confianca": "baixa",
                "evidencia": "OAB do escritorio e nome do cliente nao localizados no texto"}

    votos = defaultdict(int)
    evidencias = []
    for origem, pos in ancoras:
        janela = t[max(0, pos - _JANELA_PAPEL):pos]
        # o papel mais PROXIMO do nome e' o que vale.
        # OBRIGATORIO casar com fronteira de palavra: por substring, "re" (reu)
        # casa dentro de "renan", "recurso" e "requerente", e o polo passivo
        # vencia praticamente todo processo.
        melhor, melhor_pos, melhor_lado = None, -1, None
        for papel, lado in ([(p, "ativo") for p in _PAPEIS_ATIVOS] +
                            [(p, "passivo") for p in _PAPEIS_PASSIVOS]):
            for m in re.finditer(r"\b%s\b" % re.escape(papel), janela):
                if m.start() > melhor_pos:
                    melhor, melhor_pos, melhor_lado = papel, m.start(), lado
        if melhor_lado:
            peso = 2 if origem == "oab" else 1
            votos[melhor_lado] += peso
            evidencias.append(f"{melhor} ({origem})")

    if not votos:
        return {"polo": None, "confianca": "baixa",
                "evidencia": "ancora encontrada, mas sem papel processual identificavel ao lado"}

    ativo, passivo = votos.get("ativo", 0), votos.get("passivo", 0)
    if ativo == passivo:
        # Acontece em processo com reconvencao, litisconsorcio ou quando o
        # escritorio aparece nos dois blocos. Nao chuta.
        return {"polo": None, "confianca": "baixa",
                "evidencia": f"polo ambiguo (ativo={ativo}, passivo={passivo}): " +
                             ", ".join(sorted(set(evidencias))[:4])}

    polo = "ativo" if ativo > passivo else "passivo"
    confianca = "alta" if abs(ativo - passivo) >= 2 else "media"
    return {"polo": polo, "confianca": confianca,
            "evidencia": ", ".join(sorted(set(evidencias))[:4])}


def detectar_recorrente(texto_normalizado, polo):
    """Em ato de 2o grau, diz se o RECURSO e' nosso ou da parte contraria.

    E' o que inverte a leitura de "recurso nao provido". Trabalha sobre o polo
    ja' detectado: se somos 'agravante'/'apelante', o recurso e' nosso.
    """
    t = texto_normalizado or ""
    if polo == "ativo":
        # No 2o grau, o polo ativo do recurso e' agravante/apelante/recorrente.
        if re.search(r"\b(agravante|apelante|recorrente|embargante)\b", t):
            return "nosso"
    if polo == "passivo":
        if re.search(r"\b(agravado|apelado|recorrido)\b", t):
            return "da parte contraria"
    return None


# ============================================================
# 4. EM QUE KPI O ATO SE ENQUADRA
# ============================================================

# Marcas de JULGAMENTO COLEGIADO (acordao). Cuidado com o que NAO entra aqui:
# "camara civel" aparece no ENDERECO do tribunal no cabecalho ("rua
# desembargador homero mafra..., 2a camara civel" - TJES) e "relator" aparece em
# toda monocratica. Os dois faziam decisao monocratica de tutela recursal ser
# lida como acordao de merito (0000000-00.0000.0.00.0000).
_MARCAS_COLEGIADO = ("por unanimidade", "por maioria", "acordam os",
                     "acordam em", "data do julgamento", "orgao julgador",
                     "voto do relator")
# Sem a palavra "sentenca" solta: ela aparece em TODA intimacao de
# "cumprimento de sentenca", e classificava despacho de execucao como merito
# (30 falsos positivos na captura de 01-10/09/2026). So dispositivo conta.
_MARCAS_SENTENCA = ("art. 487", "artigo 487", "art. 485", "artigo 485",
                    "resolucao do merito", "resolucao de merito",
                    "julgo procedente", "julgo improcedente",
                    "julgo parcialmente procedente", "julgo extinto")
_MARCAS_TUTELA = ("tutela de urgencia", "tutela de evidencia",
                  "tutela provisoria", "tutela antecipada", "liminar",
                  "art. 300", "artigo 300")
_MARCAS_TUTELA_RECURSAL = ("efeito suspensivo", "tutela recursal",
                           "antecipacao da tutela recursal",
                           "antecipacao dos efeitos da tutela recursal",
                           "efeito ativo")
_MARCAS_ACORDO = ("homologo o acordo", "homologo a transacao",
                  "homologo o presente acordo", "acordo celebrado entre as partes",
                  "homologo, por sentenca, o acordo", "autocomposicao homologada")
# "relator" sozinho NAO serve: o cabecalho de sentenca de 1o grau do TJMT traz
# "sentenca 1. relatorio" e a palavra casava, fazendo o modulo tratar sentenca
# como recurso e inverter o sinal (0000000-00.0000.0.00.0000).
_MARCAS_2O_GRAU = ("agravo de instrumento", "agravo interno", "apelacao civel",
                   "desembargador", "desembargadora", "relator(a)")

# Atos que NAO sao decisao classificavel. Ficam de fora com motivo escrito -
# nunca sao apagados em silencio, porque e' aqui que mora o falso negativo.
_FORA_DE_ESCOPO = (
    ("despacho de mero expediente / impulso",
     ("intimem-se as partes para que", "manifestem-se sobre a peticao",
      "especifiquem as provas", "quais provas pretendem produzir",
      "cumpra-se", "ciente da interposicao", "determino o prosseguimento")),
    ("homologacao de desistencia / cancelamento de distribuicao",
     ("homologo a desistencia", "cancelo a distribuicao",
      "cancelamento da distribuicao")),
    ("extincao de cumprimento de sentenca por pagamento (art. 924, II)",
     ("art. 924, inciso ii", "art. 924, ii", "artigo 924, ii")),
    # A GJ deixou "impugnacao a gratuidade e agravo interno" fora do escopo dos
    # KPIs em ago/2026 (Anexo C). O criterio e' o OBJETO do ato: recurso que
    # discute so gratuidade/custas nao mede exito na tese.
    ("questao acessoria (gratuidade / custas / honorarios isolados)",
     ("impugnacao a gratuidade", "impugnacao ao beneficio da gratuidade",
      "gratuidade da justica. hipossuficiencia", "indeferimento do beneficio",
      "parcelamento das custas processuais")),
    # REGRA FECHADA pela Dra. Juliana em 10/09/2026: embargos de declaracao NAO
    # contam, nem em 1o grau nem em acordao. O item 1.2 do manual cita "acordao
    # em apelacao, embargos, RESP, RE" - "embargos" ali NAO alcanca os de
    # declaracao. A razao e' a que ja' se via nos anexos de jun-ago/2026: o
    # merito discutido no ED ja' foi pontuado na sentenca ou no acordao
    # embargado, e conta-lo de novo pontuaria o mesmo ato duas vezes.
    ("embargos de declaracao - nao contam (regra da GJ, 10/09/2026)",
     ("embargos de declaracao rejeitados", "embargos rejeitados",
      "rejeito os embargos", "rejeito-os", "acolho os embargos",
      "acolho parcialmente os embargos", "embargos de declaracao acolhidos",
      "conheco dos embargos de declaracao")),
)


# ------------------------------------------------------------
# OBJETO ACESSORIO - gratuidade, custas, honorarios: fora do KPI
# ------------------------------------------------------------
#
# Regra do "7 - MANUAL DO EXITO JURIDICO KPI" (v1.0, mai/2026), confirmada pela
# Dra. Juliana em 10/09/2026: os KPIs medem MERITO (KPI 1), TUTELA DE 1o GRAU
# (KPI 2), TUTELA RECURSAL (KPI 3) e EXITO NEGOCIAL (KPI 4). Decisao cujo
# objeto e' gratuidade da justica, custas ou honorarios sucumbenciais nao mede
# tese nenhuma - fica de fora, mesmo quando a forma do ato e' de efeito
# suspensivo ou de acordao de apelacao.
#
# O teste NAO pode ser a mera mencao da palavra: quase todo acordao cita
# gratuidade de passagem ("gratuidade da justica deferida para o ato. no
# merito, recurso nao provido"), e um agravo sobre penhora pode trazer a
# gratuidade como questao incidental. O que decide e' a frase que identifica o
# OBJETO do ato - o que a decisao recorrida decidiu, ou o que a parte pede.
_OBJETO_ACESSORIO = (
    ("gratuidade da justica",
     (r"revogou a gratuidade", r"revogacao da gratuidade",
      r"indeferiu (?:o pedido de )?(?:a )?gratuidade",
      r"impugnacao a gratuidade", r"impugnacao ao beneficio da gratuidade",
      r"acolheu a impugnacao[^.]{0,80}gratuidade",
      r"restabelecimento do beneficio",
      r"indefiro o pedido de justica gratuita",
      r"indefiro o pedido de gratuidade",
      r"gratuidade da justica\. hipossuficiencia")),
    ("custas / honorarios sucumbenciais",
     (r"pretende exclusivamente a reforma dos onus sucumbenciais",
      r"exclusivamente[^.]{0,40}onus sucumbenciais",
      r"objeto[^.]{0,30}(?:apenas|somente)[^.]{0,30}honorarios",
      r"parcelamento das custas processuais")),
)


# Pedido PRINCIPAL que, listado junto de um acessorio na regiao do objeto, impede
# a exclusao do ato (ver objeto_acessorio). Frases especificas de proposito:
# "efeito suspensivo" sozinho aparece no agravo cujo unico objeto e' a gratuidade.
_OBJETO_PRINCIPAL = (
    "efeito suspensivo aos embargos",
    "tutela provisoria de urgencia",
    "tutela de urgencia cautelar",
    "suspensao da exigibilidade do debito",
    "suspensao da execucao",
    "suspensao dos atos executivos",
)


def _regiao_do_objeto(texto_normalizado):
    """So o trecho que IDENTIFICA o objeto: cabecalho, 'trata-se de' e ementa.

    Varrer o texto inteiro nao serve: uma sentenca de 18 mil caracteres cita
    gratuidade no meio da fundamentacao e as duas sentencas de uma cliente
    foram excluidas por isso na primeira tentativa desta regra.
    """
    t = texto_normalizado or ""
    partes = [t[:2000]]
    for marcador in ("trata-se", "ementa", "i. caso em exame", "caso em exame"):
        i = t.find(marcador)
        if i >= 0:
            partes.append(t[i:i + 900])
    return " ".join(partes)


def objeto_acessorio(texto_normalizado, dispositivo=None):
    """Devolve o motivo, se o OBJETO do ato for questao acessoria; senao None.

    Duas condicoes, cumulativas:
      1. a frase que identifica o objeto aparece na REGIAO DO OBJETO, e
      2. o dispositivo NAO acolhe nenhuma tese central do escritorio.
    A segunda salva a sentenca de merito que apenas concede gratuidade de
    passagem no mesmo ato.
    """
    regiao = _regiao_do_objeto(texto_normalizado)
    d = dispositivo or ""

    for _, marcas in _TESES_CENTRAIS:
        if any(m in d for m in marcas):
            return None

    for rotulo, padroes in _OBJETO_ACESSORIO:
        for padrao in padroes:
            m = re.search(padrao, regiao)
            if m:
                # Objeto MISTO: o pedido acessorio aparece listado ao lado de um
                # pedido principal. Nos embargos de um cliente (0000000-00, 11/09/2026)
                # a decisao resume "requer o parcelamento das custas processuais e
                # a atribuicao de efeito suspensivo aos embargos" - e o dispositivo
                # indefere o efeito suspensivo. A regra existe para o ato cujo UNICO
                # objeto e' acessorio (0000000-01, 0000000-02); objeto que tambem
                # pede tutela ou suspensao da execucao continua no KPI.
                if any(p in regiao for p in _OBJETO_PRINCIPAL):
                    continue
                return (f"objeto acessorio ({rotulo}) - o manual mede merito, tutela de "
                        f"1o grau, tutela recursal e exito negocial; "
                        f"trecho: \"{m.group(0)[:70]}\"")
    return None


def e_ato_de_segundo_grau(texto_normalizado, classe=""):
    """Diz se o ato e' de tribunal (recurso), e nao de 1o grau.

    Serve para dois cortes distintos: se o `recorrente` faz sentido, e se um
    dispositivo de 1o grau lido no texto e' provavel transcricao da decisao
    recorrida.
    """
    c = (classe or "").lower()
    if any(m in c for m in ("agravo", "apelacao", "apelaç")):
        return True
    return any(m in (texto_normalizado or "")[:1200] for m in _MARCAS_2O_GRAU)


def classificar_kpi(texto_normalizado, dispositivo, classe=""):
    """Diz em que KPI o ato entra, ou por que ele fica fora.

    Retorna dict: {kpi, rotulo, fora_escopo, motivo, confianca}.
    """
    t = texto_normalizado or ""
    d = dispositivo or t
    c = (classe or "").lower()

    for motivo, marcas in _FORA_DE_ESCOPO:
        if any(m in d for m in marcas):
            # ED sai sem excecao: o "julgo procedente" que aparece no dispositivo
            # de um ED e' a transcricao da sentenca embargada, nao um julgamento
            # novo. Deixar a excecao valer aqui recontaria o mesmo merito.
            if motivo.startswith("embargos de declaracao"):
                return {"kpi": None, "rotulo": None, "fora_escopo": True,
                        "motivo": motivo, "confianca": "media"}
            # Excecao: se o MESMO ato tambem resolve tutela ou merito, ele conta.
            tem_decisao = any(m in d for m in ("julgo procedente", "julgo improcedente",
                                               "julgo parcialmente procedente",
                                               "defiro a tutela", "indefiro a tutela",
                                               "indefiro o pedido de tutela",
                                               "defiro parcialmente o pedido de tutela",
                                               "recurso nao provido", "recurso provido"))
            if not tem_decisao:
                return {"kpi": None, "rotulo": None, "fora_escopo": True,
                        "motivo": motivo, "confianca": "media"}

    if any(m in d for m in _MARCAS_ACORDO):
        return {"kpi": "KPI 4", "rotulo": ROTULO_KPI["KPI 4"], "fora_escopo": False,
                "motivo": "homologacao de acordo", "confianca": "media"}

    segundo_grau = any(m in c for m in ("agravo", "apelacao")) or \
        any(m in t[:1200] for m in _MARCAS_2O_GRAU)
    colegiado = any(m in t for m in _MARCAS_COLEGIADO)

    # Acordao (julgamento colegiado do recurso) = MERITO, na regua da GJ.
    # A decisao MONOCRATICA sobre o pedido liminar do recurso e' que e' KPI 3.
    # (Anexo A jun/2026: "AI da parte contraria nao provido" entrou como
    #  Merito peso 1,0; "Tutela recursal indeferida", como peso 0,50.)
    #
    # A mencao a "efeito suspensivo" NAO tira o acordao do KPI 1: o acordao que
    # julga o AI costuma abrir dizendo que o pedido de efeito suspensivo ficou
    # prejudicado (0000000-00.0000.0.00.0000, apelacao lida como KPI 3 por
    # causa dessa frase). Quem decide e' o orgao: colegiado -> merito.
    if segundo_grau and colegiado:
        return {"kpi": "KPI 1", "rotulo": ROTULO_KPI["KPI 1"], "fora_escopo": False,
                "motivo": "acordao / julgamento colegiado do recurso", "confianca": "alta"}

    if segundo_grau and any(m in d for m in _MARCAS_TUTELA_RECURSAL):
        return {"kpi": "KPI 3", "rotulo": ROTULO_KPI["KPI 3"], "fora_escopo": False,
                "motivo": "decisao sobre efeito suspensivo / tutela recursal", "confianca": "alta"}

    if any(m in d for m in ("julgo procedente", "julgo improcedente",
                            "julgo parcialmente procedente")):
        return {"kpi": "KPI 1", "rotulo": ROTULO_KPI["KPI 1"], "fora_escopo": False,
                "motivo": "sentenca de merito (art. 487, I)", "confianca": "alta"}

    if any(m in d for m in _MARCAS_TUTELA):
        return {"kpi": "KPI 2", "rotulo": ROTULO_KPI["KPI 2"], "fora_escopo": False,
                "motivo": "decisao sobre tutela de 1o grau", "confianca": "alta"}

    if any(m in d for m in _MARCAS_SENTENCA):
        return {"kpi": "KPI 1", "rotulo": ROTULO_KPI["KPI 1"], "fora_escopo": False,
                "motivo": "sentenca (extincao com/sem resolucao de merito)", "confianca": "media"}

    return {"kpi": None, "rotulo": None, "fora_escopo": True,
            "motivo": "ato sem dispositivo decisorio identificavel (despacho/expediente)",
            "confianca": "baixa"}


# ============================================================
# 5. RESULTADO (exito / parcial / inexito)
# ============================================================
#
# Cada padrao vem com o "lado" que ele favorece: 'ativo' significa que o
# dispositivo favorece quem pediu (autor / recorrente). O resultado final e'
# esse lado cruzado com o nosso polo.

# ATENCAO AO \b INICIAL DOS "defiro": sem ele, "indefiro o pedido de tutela"
# casa com o padrao de DEFERIMENTO (a palavra termina em "defiro") e o
# indeferimento vira exito. Deu 2 inversoes na captura de 01-10/09/2026.
_PADROES_RESULTADO = [
    # (regex, lado favorecido, resultado_para_esse_lado)
    (r"\bjulgo (?:totalmente )?procedente", "ativo", "exito"),
    (r"\bjulgo (?:o )?(?:pedido |os pedidos )?parcialmente procedente", "ativo", "parcial"),
    (r"\bjulgo parcialmente procedente", "ativo", "parcial"),
    (r"\bparcialmente procedentes? os pedidos", "ativo", "parcial"),
    (r"\bjulgo (?:totalmente )?improcedente", "ativo", "inexito"),
    (r"\bimprocedentes? os pedidos", "ativo", "inexito"),
    (r"\bindefiro,? por ora,? (?:a|o pedido de) tutela", "ativo", "inexito"),
    (r"\bindefiro (?:a|o pedido de) tutela", "ativo", "inexito"),
    (r"\bindefiro o pedido de antecipacao", "ativo", "inexito"),
    # As monocraticas de relator variam muito a redacao do mesmo comando:
    # "indefiro o pedido de efeito suspensivo ativo" (0000000-03),
    # "indefiro o pedido de concessao do efeito suspensivo" (0000000-04),
    # "indefiro o pedido de efeito antecipatorio (ativo ou suspensivo)"
    # (0000000-05). As tres sao o mesmo KPI 3.
    (r"\bindefiro o (?:pedido de )?(?:concessao d[eo] )?efeito "
     r"(?:suspensivo|ativo|antecipatorio)", "ativo", "inexito"),
    (r"\bnego (?:o )?(?:pedido de )?efeito suspensivo", "ativo", "inexito"),
    (r"\bdefiro parcialmente (?:o pedido de )?(?:a )?tutela", "ativo", "parcial"),
    (r"\bdefiro em parte (?:o pedido de )?(?:a )?tutela", "ativo", "parcial"),
    (r"\bdefiro parcialmente o pedido de antecipacao", "ativo", "parcial"),
    (r"\bdefiro (?:a|o pedido de) tutela", "ativo", "exito"),
    (r"\bconcedo (?:a|o pedido de) tutela", "ativo", "exito"),
    # Nem toda liminar deferida diz "tutela" no dispositivo. A decisao que
    # suspendeu a execucao de uma cliente
    # (0000000-00.0000.0.00.0000) abre com "defiro o pedido formulado pela parte
    # autora" e so depois detalha o que suspende - e ficou fora do KPI por isso.
    # O guarda-negativo de `_DEFERIMENTO_PROCESSUAL` e' que impede este padrao de
    # capturar "defiro a dilacao de prazo" e "defiro a gratuidade".
    (r"\bdefiro o pedido formulado pel[ao] (?:parte )?"
     r"(?:autora|autor|exequente|embargante)", "ativo", "exito"),
    (r"\bdefiro,? (?:em parte|parcialmente),? o pedido formulado pel[ao] (?:parte )?"
     r"(?:autora|autor)", "ativo", "parcial"),
    (r"\bdefiro o (?:pedido de )?(?:concessao d[eo] )?efeito "
     r"(?:suspensivo|ativo|antecipatorio)", "ativo", "exito"),
    (r"\batribuo efeito suspensivo", "ativo", "exito"),
    (r"\brevogo a tutela", "ativo", "inexito"),
    # recurso: 'ativo' aqui = quem recorreu
    (r"recurso (?:conhecido,? (?:mas |e )?)?(?:nao provido|desprovido|improvido)", "ativo", "inexito"),
    (r"nego provimento", "ativo", "inexito"),
    (r"negaram provimento", "ativo", "inexito"),
    (r"agravo (?:interno |de instrumento )?(?:conhecido (?:e |mas )?)?"
     r"(?:nao provido|desprovido|improvido)", "ativo", "inexito"),
    (r"apelacao (?:conhecida (?:e |mas )?)?(?:nao provida|desprovida)", "ativo", "inexito"),
    (r"agravo (?:interno|de instrumento) (?:conhecido e )?provido", "ativo", "exito"),
    (r"apelacao (?:conhecida e )?provida", "ativo", "exito"),
    (r"recurso (?:conhecido e )?provido", "ativo", "exito"),
    (r"dou provimento", "ativo", "exito"),
    (r"deram provimento", "ativo", "exito"),
    (r"recurso parcialmente provido", "ativo", "parcial"),
    (r"provimento parcial", "ativo", "parcial"),
    (r"dou parcial provimento", "ativo", "parcial"),
    (r"homologo o acordo", "ativo", "exito"),
]

_INVERSO = {"exito": "inexito", "inexito": "exito", "parcial": "parcial"}


# ------------------------------------------------------------
# "Parcialmente procedente" NAO e' automaticamente Parcial
# ------------------------------------------------------------
#
# Regra da Dra. Juliana (10/09/2026), sobre as duas sentencas de uma
# cliente: o que decide entre Exito e Parcial nao e' o rotulo do dispositivo, e'
# se a TESE CENTRAL do escritorio foi acolhida. Sentenca que declara
# descaracterizada a mora, reconhece o direito ao alongamento ou anula a
# clausula discutida entregou ao cliente aquilo que ele veio buscar - ainda que
# o juiz rejeite um pedido acessorio e rotule tudo de "parcialmente procedente".
#
# Foi exatamente o caso: 0000000-06 (alongamento PRONAMP reconhecido, Sumula
# 298) e 0000000-07 (mora descaracterizada, CDI afastado, capitalizacao diaria
# afastada, seguro prestamista anulado) sairam como Parcial na primeira versao
# deste modulo, quando as duas sao Exito.
_TESES_CENTRAIS = (
    ("descaracterizacao da mora",
     ("declarar descaracterizada a mora", "declaro descaracterizada a mora",
      "descaracterizada a mora da parte autora", "descaracterizacao da mora")),
    ("alongamento / prorrogacao (MCR 2-6-4, Sumula 298/STJ)",
     ("direito subjetivo da autora a prorrogacao",
      "direito subjetivo do autor a prorrogacao",
      "direito a prorrogacao", "direito ao alongamento",
      "determinando aos reus que procedam a renegociacao",
      "prorrogacao pelo prazo maximo")),
    ("nulidade de clausula / do titulo",
     ("declarar a nulidade da cedula", "declarar a nulidade da clausula",
      "declarar a nulidade da cobranca", "declaro a nulidade")),
    ("revisao dos encargos",
     ("determinar a revisao da cedula", "declarando a inaplicabilidade do indice",
      "afastar a capitalizacao", "limitar os juros moratorios",
      "restabelecendo a natureza de operacao de credito rural",
      "restabelecimento das taxas oficiais de credito rural")),
    ("suspensao da exigibilidade / baixa de restricoes",
     ("suspensao definitiva da exigibilidade", "baixa/exclusao definitiva de restricoes",
      "exclusao definitiva de restricoes")),
)

# Sinais que o proprio juiz da de que a derrota foi acessoria.
_MARCAS_DECAIMENTO_MINIMO = ("art. 86, paragrafo unico", "artigo 86, paragrafo unico",
                             "decaimento minimo", "parte minima do pedido",
                             "procedencia substancial", "sucumbencia recai "
                             "preponderantemente sobre os reus")
# ...e o sinal contrario, que exige confirmacao humana.
_MARCAS_SUCUMBENCIA_RECIPROCA = ("sucumbencia reciproca", "sucumbencia minima e reciproca",
                                 "reciprocamente sucumbentes")


def avaliar_procedencia(dispositivo, texto_normalizado):
    """Para sentenca 'parcialmente procedente': Exito ou Parcial?

    Retorna (resultado, evidencia, precisa_confirmar).
    """
    d = dispositivo or ""
    t = texto_normalizado or ""

    acolhidas = [nome for nome, marcas in _TESES_CENTRAIS
                 if any(m in d for m in marcas)]
    decaimento = [m for m in _MARCAS_DECAIMENTO_MINIMO if m in t]
    reciproca = [m for m in _MARCAS_SUCUMBENCIA_RECIPROCA if m in t]

    # O item 1.4 do manual e' expresso: "decisoes parcialmente procedentes NAO
    # sao classificadas automaticamente como Exito. Toda decisao parcial e'
    # objeto de analise substantiva do merito pela Controladoria em conjunto
    # com a Gerencia Juridica". Por isso TODA parcial sai marcada para
    # confirmacao - o que este modulo entrega e' a proposta fundamentada, nunca
    # a classificacao final.
    if acolhidas:
        evid = "tese central acolhida: " + "; ".join(acolhidas)
        if decaimento:
            evid += f" (o juizo reconhece {decaimento[0]})"
        if reciproca:
            evid += " — ATENCAO: sentenca fixa sucumbencia reciproca"
        return "exito", evid + " [analise obrigatoria, item 1.4 do manual]", True

    if decaimento:
        return ("exito",
                f"decaimento minimo reconhecido pelo juizo ({decaimento[0]}) "
                "[analise obrigatoria, item 1.4 do manual]", True)

    return ("parcial",
            "procedencia parcial sem tese central identificada no dispositivo "
            "[analise obrigatoria, item 1.4 do manual]", True)


# Enunciados que so fazem sentido em ato de recurso. Em ato de 2o grau, se o
# unico dispositivo reconhecido NAO for um destes, o mais provavel e' que a
# expressao venha da decisao agravada transcrita no relatorio do acordao -
# nao do que o tribunal decidiu.
_PADROES_RECURSAIS = ("provido", "provida", "provimento", "suspensivo",
                      "tutela recursal", "antecipatorio", "efeito ativo",
                      "ao recurso", "agravo")

# Deferimento que NAO e' merito nem tutela: e' expediente. Sem esta lista, o
# padrao generico "defiro o pedido formulado pela parte autora" transformaria
# "defiro a dilacao de prazo" (0000000-00.0000.0.00.0000, mesma cliente, mesma
# semana) num exito de KPI 2.
_DEFERIMENTO_PROCESSUAL = ("dilacao de prazo", "dilacao do prazo", "gratuidade",
                           "justica gratuita", "juntada", "desentranhamento",
                           "vista dos autos", "prazo suplementar", "habilitacao",
                           "expedicao de certidao", "producao de prova",
                           "parcelamento das custas", "prioridade na tramitacao")


def classificar_resultado(dispositivo, kpi, polo, recorrente=None, segundo_grau=False,
                          texto_normalizado=None):
    """Le o dispositivo e devolve exito / parcial / inexito na otica do cliente.

    Retorna dict {resultado, confianca, evidencia, padrao, confirmar}.
    """
    d = dispositivo or ""
    achados = []
    for regex, lado, resultado in _PADROES_RESULTADO:
        m = re.search(regex, d)
        if m:
            # "defiro o pedido..." de dilacao de prazo, gratuidade ou juntada e'
            # expediente, nao tutela deferida.
            trecho_pos = d[m.start():m.start() + len(m.group(0)) + 90]
            if "defiro" in m.group(0) and any(x in trecho_pos
                                              for x in _DEFERIMENTO_PROCESSUAL):
                continue
            achados.append((m.start(), regex, lado, resultado, m.group(0)))

    if not achados:
        return {"resultado": None, "confianca": "baixa", "padrao": None,
                "evidencia": "nenhum dispositivo reconhecido no trecho final do ato"}

    achados.sort()

    # O teste do carater recursal olha o ENTORNO, nao so o trecho casado: o
    # padrao "defiro parcialmente o pedido de antecipacao" para antes da
    # palavra que o qualifica ("...da tutela recursal"), e a decisao recursal
    # legitima caia como transcricao (0000000-00.0000.0.00.0000).
    def _recursal(a):
        pos, _, _, _, trecho = a
        return any(p in d[pos:pos + len(trecho) + 60] for p in _PADROES_RECURSAIS)

    if segundo_grau:
        # Em ato de tribunal o relator TRANSCREVE a decisao agravada antes de
        # decidir ("combate a decisao que deferiu parcialmente a tutela [...]
        # deste modo, indefiro o efeito suspensivo"). O primeiro enunciado do
        # trecho e', entao, a decisao de 1o grau; o comando do relator e' o
        # ULTIMO enunciado de carater recursal (0000000-00.0000.0.00.0000).
        recursais = [a for a in achados if _recursal(a)]
        if not recursais:
            trecho = achados[0][4]
            return {"resultado": None, "confianca": "baixa", "padrao": achados[0][1],
                    "evidencia": f"ato de 2o grau, mas o unico dispositivo lido "
                                 f"('{trecho}') e' de 1o grau - provavel transcricao "
                                 f"da decisao recorrida; conferir a mao"}
        escolhido = recursais[-1]
    else:
        # Em 1o grau o dispositivo ABRE com o verbo operativo ("ante o exposto,
        # julgo parcialmente procedente ... para: a) ... b) ..."), entao vale o
        # PRIMEIRO enunciado: pegar o ultimo faz o item "b)" de uma procedencia
        # parcial - quase sempre uma rejeicao acessoria - virar o resultado.
        escolhido = achados[0]

    _, regex, lado, resultado_ativo, trecho = escolhido

    # Quem e' o "ativo" deste dispositivo?
    #   - em ato de recurso: quem interpos o recurso;
    #   - em ato de 1o grau: quem pediu a tutela / quem e' autor.
    e_recurso = kpi in ("KPI 1", "KPI 3") and recorrente is not None

    if e_recurso:
        somos_o_ativo = (recorrente == "nosso")
    else:
        somos_o_ativo = (polo == "ativo")

    if polo is None and not e_recurso:
        return {"resultado": None, "confianca": "baixa", "padrao": regex,
                "evidencia": f"dispositivo lido ('{trecho}'), mas o polo do escritorio "
                             f"nao foi identificado - sem isso o sinal nao se define"}

    resultado = resultado_ativo if somos_o_ativo else _INVERSO[resultado_ativo]

    # Multiplos dispositivos concorrentes no mesmo trecho baixam a confianca:
    # e' o caso classico de decisao que indefere a tutela e defere a gratuidade.
    distintos = {a[3] for a in achados}
    confianca = "alta" if len(distintos) == 1 else "media"
    confirmar = False
    evidencia = trecho

    # KPI 2 e KPI 3 sao BINARIOS no manual (itens 2.3 e 3.3): so existe
    # "deferida -> Exito" e "indeferida -> Inexito". Nao ha categoria Parcial -
    # ela so existe no KPI 1, e la' com a analise obrigatoria do item 1.4.
    # Tutela deferida em parte e' tutela DEFERIDA: a medida foi concedida,
    # ainda que com alcance menor que o pedido.
    # Regra confirmada pela Dra. Juliana em 10/09/2026 sobre a tutela recursal
    # de um cliente (0000000-00.0000.0.00.0000), que saia
    # como Parcial 0,25 quando vale 0,50.
    if resultado == "parcial" and kpi in ("KPI 2", "KPI 3"):
        resultado = "exito" if somos_o_ativo else "inexito"
        evidencia = (f"{trecho} — deferimento parcial; o manual (itens 2.3 e 3.3) "
                     f"nao tem categoria Parcial em tutela: deferida e' Exito")
        return {"resultado": resultado, "confianca": confianca, "padrao": regex,
                "evidencia": evidencia, "confirmar": False}

    # Procedencia parcial: o rotulo nao decide: quem decide e' a tese acolhida.
    if resultado == "parcial" and somos_o_ativo and "procedente" in trecho:
        resultado, motivo_proc, confirmar = avaliar_procedencia(
            d, texto_normalizado or d)
        evidencia = f"{trecho} — {motivo_proc}"
        if confirmar:
            confianca = "media"

    return {"resultado": resultado, "confianca": confianca, "padrao": regex,
            "evidencia": evidencia, "confirmar": confirmar}


# ============================================================
# 6. CARTEIRA (rural x diversa) - o recorte oficial
# ============================================================

# CUIDADO: o campo `group` do ADVBOX NAO e' uma taxonomia de tese. Na carteira
# real (conferido em 10/09/2026) ele mistura tese ("ALONGAMENTO DE DIVIDA
# RURAL", "DESCARACTERIZACAO DA MORA") com classe processual ("ACAO CIVEL" 47x,
# "AGRAVO DE INSTRUMENTO" 18x, "EXECUCAO DE TITULO EXTRAJUDICIAL"). Ler "ACAO
# CIVEL" como carteira diversa jogaria fora quase metade da carteira rural -
# a maioria das acoes de Tema 28 esta cadastrada exatamente assim.
#
# Por isso: o grupo so decide quando nomeia a tese ou nomeia area claramente
# alheia; no resto, quem decide e' o texto do proprio ato.
_GRUPOS_RURAIS = ("alongamento", "descaracterizacao da mora", "divida rural",
                  "credito rural", "revisional", "prorrogacao",
                  "assistencia tecnica")
_GRUPOS_DIVERSOS = ("familia", "trabalhista", "criminal", "ambiental",
                    "inventario", "previdenciario", "consumidor", "parceiro",
                    "regularizacao fundiaria", "precatorio")

_TEXTO_RURAL = ("credito rural", "cedula rural", "cedula de credito rural",
                "cedula de produto rural", "cedula rural pignoraticia",
                "divida rural", "alongamento de divida", "prorrogacao da divida",
                "tema 28", "sumula 298", "pronaf", "manual de credito rural",
                "produtor rural", "atividade rural", "descaracterizacao da mora",
                "encargos da normalidade", "periodo de normalidade contratual")


def classificar_carteira(lawsuit, texto_normalizado):
    """'rural' | 'diversa', com a origem e a confianca da classificacao.

    Retorna (carteira, origem, confianca). O recorte importa porque so a
    carteira rural compoe o indicador oficial da Presidencia.
    """
    grupo = ((lawsuit or {}).get("group") or "")
    g = unicodedata.normalize("NFKD", grupo).encode("ascii", "ignore").decode().lower()
    t = texto_normalizado or ""

    if g and any(m in g for m in _GRUPOS_RURAIS):
        return "rural", f"ADVBOX group='{grupo}'", "alta"
    if g and any(m in g for m in _GRUPOS_DIVERSOS):
        return "diversa", f"ADVBOX group='{grupo}'", "alta"

    marcas = [m for m in _TEXTO_RURAL if m in t]
    if marcas:
        origem = f"texto do ato ({marcas[0]})"
        if g:
            origem += f" - group='{grupo}' e' classe processual, nao tese"
        return "rural", origem, "media"

    # "Diversa" por AUSENCIA de marca nao e' conclusao: o acordao de 2o grau
    # publicado so como ementa nao repete a origem rural do processo, e a mesma
    # cliente sai rural num ato e diversa no outro (Cliente C:
    # 0000000-05 rural, 0000000-08 diversa - as duas sao rurais na planilha da
    # GJ). Marcado como baixa para a Controladoria confirmar.
    return "diversa", ("sem marca rural no texto" +
                       (f" e group='{grupo}' nao nomeia tese rural" if g else "") +
                       " - classificacao por AUSENCIA, confirmar"), "baixa"


# ============================================================
# 7. AVALIACAO DE UM ATO
# ============================================================

def avaliar(resumo_djen, lawsuit=None, oabs_escritorio=None):
    """Avalia uma comunicacao do DJEN na regua do KPI.

    resumo_djen: saida de comunica_djen.resumir()
    lawsuit:     processo correspondente no ADVBOX (ou None)

    Devolve a linha do relatorio, sempre - inclusive quando fica fora do KPI.
    """
    texto = resumo_djen.get("texto") or ""
    t = normalizar(texto)
    dispositivo, origem_disp = extrair_dispositivo(t)

    proprios = clientes_do_escritorio(lawsuit)
    nome_cliente = proprios[0].get("name") if proprios else None
    responsavel = (lawsuit or {}).get("responsible")

    # Ancora estruturada do CNJ primeiro; texto so como reserva.
    polo = (polo_pelas_partes_djen(resumo_djen.get("partes_polo"), proprios)
            or detectar_polo(t, oabs_escritorio, nome_cliente))

    # "recorrente" so faz sentido em ato de tribunal. Em sentenca de 1o grau a
    # palavra "apelante" aparece por citacao de jurisprudencia, e a leitura do
    # resultado passava a inverter o sinal de uma procedencia (0000000-06).
    segundo_grau = e_ato_de_segundo_grau(t, resumo_djen.get("classe"))
    recorrente = detectar_recorrente(t, polo["polo"]) if segundo_grau else None
    kpi = classificar_kpi(t, dispositivo, resumo_djen.get("classe"))

    # Objeto acessorio derruba o ato de qualquer KPI, inclusive quando a FORMA
    # e' de efeito suspensivo (0000000-00.0000.0.00.0000: agravo cujo unico
    # objeto e' a revogacao da gratuidade) ou de acordao de apelacao
    # (0000000-00.0000.0.00.0000: apelacao so sobre onus sucumbenciais).
    if not kpi["fora_escopo"]:
        acessorio = objeto_acessorio(t, dispositivo)
        if acessorio:
            kpi = {"kpi": None, "rotulo": None, "fora_escopo": True,
                   "motivo": acessorio, "confianca": "media"}
    carteira, origem_carteira, conf_carteira = classificar_carteira(lawsuit, t)

    linha = {
        "data": resumo_djen.get("data"),
        "processo": resumo_djen.get("processo"),
        "tribunal": resumo_djen.get("tribunal"),
        # O orgao julgador (vara/camara) e' o unico recorte de "quem decidiu"
        # que o DJEN entrega estruturado - o nome do magistrado so existe no
        # corpo do ato, quando existe. E' a chave das notas de
        # `01 - MAGISTRADOS/` no vault (vault_obsidian.py).
        "orgao": resumo_djen.get("orgao"),
        "classe": resumo_djen.get("classe"),
        "cliente": nome_cliente or "NAO ENCONTRADO NO ADVBOX",
        "advogado_responsavel": responsavel or "SEM RESPONSAVEL NO ADVBOX",
        "carteira": carteira,
        "origem_carteira": origem_carteira,
        "carteira_confianca": conf_carteira,
        "kpi": kpi["kpi"],
        "kpi_rotulo": kpi["rotulo"],
        "kpi_motivo": kpi["motivo"],
        "fora_escopo": kpi["fora_escopo"],
        "polo": polo["polo"],
        "polo_evidencia": polo["evidencia"],
        "recurso_de_quem": recorrente,
        "resultado": None,
        "peso": None,
        "favoravel": None,
        "contribuicao": None,
        "evidencia": None,
        "confianca": "baixa",
        "confirmar_resultado": False,
        "link_djen": resumo_djen.get("link"),
        "no_advbox": bool(lawsuit),
    }

    if kpi["fora_escopo"]:
        linha["confianca"] = kpi["confianca"]
        linha["evidencia"] = kpi["motivo"]
        return linha

    if origem_disp == "texto":
        # Ato curto demais para recortar: a leitura cairia sobre o texto
        # inteiro, que contem a ementa da jurisprudencia citada e a decisao
        # recorrida transcrita. Foi assim que um embargos a execucao virou
        # "recurso conhecido e desprovido" a partir de um acordao do TJ-MS
        # colado na peca (0000000-00.0000.0.00.0000). Sobe a conferir.
        res = {"resultado": None, "confianca": "baixa", "padrao": None,
               "evidencia": "ato sem marcador de dispositivo e curto demais para "
                            "recortar o fecho - ler a mao"}
    else:
        res = classificar_resultado(dispositivo, kpi["kpi"], polo["polo"], recorrente,
                                    segundo_grau=segundo_grau, texto_normalizado=t)
    linha["resultado"] = res["resultado"]
    linha["evidencia"] = res["evidencia"]
    linha["confirmar_resultado"] = bool(res.get("confirmar"))

    peso = PESOS.get(kpi["kpi"])
    if kpi["kpi"] == "KPI 4":
        peso = PESO_ACORDO_A_ARBITRAR  # a GJ arbitra entre 0,5 e 2,0
    linha["peso"] = peso

    if res["resultado"] and peso is not None:
        linha["favoravel"] = FAVORAVEL[res["resultado"]]
        linha["contribuicao"] = round(peso * FAVORAVEL[res["resultado"]], 4)

    # A confianca da linha e' a MENOR das confiancas que a compoem, e cai mais
    # um degrau se o dispositivo nao foi isolado (leitura sobre o texto inteiro).
    escala = {"alta": 2, "media": 1, "baixa": 0}
    nivel = min(escala[kpi["confianca"]], escala[res["confianca"]],
                escala[polo["confianca"]] if polo["polo"] else 0)
    if origem_disp != "marcador":
        # Dispositivo inferido (ementa ou fecho do ato) nunca sai como alta:
        # e' leitura de posicao no texto, nao de comando explicito.
        nivel = min(nivel, 1)
    if not lawsuit:
        nivel = min(nivel, 1)  # sem ADVBOX nao ha cliente nem responsavel
    linha["confianca"] = {2: "alta", 1: "media", 0: "baixa"}[nivel]
    return linha


# ============================================================
# SEMANAS DA COMPETENCIA
# ============================================================
#
# A GJ acompanha por dia e por semana ("Semana 01"). A semana e' de
# SEGUNDA A DOMINGO e numerada a partir da que contem o primeiro dia do
# periodo - nao e' a semana ISO do ano, que daria "Semana 36" e nao diz nada a
# quem fecha a competencia de setembro.
#
# Consequencia proposital: o periodo 01-10/09/2026 (terca a quinta) tem
# Semana 01 = 01 a 06/09 e Semana 02 = 07 a 13/09. A primeira semana pode
# comecar no meio, porque a competencia comeca no dia 1o e nao numa segunda.

def _para_data(iso):
    from datetime import date
    return date(*map(int, (iso or "")[:10].split("-"))) if iso else None


def inicio_da_semana(d):
    """Segunda-feira da semana de `d`."""
    from datetime import timedelta
    return d - timedelta(days=d.weekday())


def numerar_semanas(datas_iso):
    """{data_iso: numero_da_semana}, comecando em 1 na semana do 1o dia."""
    datas = sorted({d for d in datas_iso if d})
    if not datas:
        return {}
    base = inicio_da_semana(_para_data(datas[0]))
    mapa = {}
    for iso in datas:
        seg = inicio_da_semana(_para_data(iso))
        mapa[iso] = ((seg - base).days // 7) + 1
    return mapa


def rotular_semana(n):
    return f"Semana {n:02d}"


def anotar_semanas(linhas):
    """Escreve `semana` (int) e `semana_rotulo` em cada linha, in place."""
    mapa = numerar_semanas([l.get("data") for l in linhas])
    for l in linhas:
        n = mapa.get(l.get("data"))
        l["semana"] = n
        l["semana_rotulo"] = rotular_semana(n) if n else None
    return linhas


def intervalo_da_semana(linhas, numero):
    """(primeiro_dia, ultimo_dia) com publicacao naquela semana, como date."""
    datas = sorted(_para_data(l["data"]) for l in linhas
                   if l.get("semana") == numero and l.get("data"))
    return (datas[0], datas[-1]) if datas else (None, None)


def avaliar_lote(resumos_djen, lawsuits_por_processo=None, oabs_escritorio=None):
    """Aplica avaliar() em lote, deduplicando por (processo, data, dispositivo).

    O DJEN publica o MESMO ato uma vez por advogado intimado: o processo em que
    o Dr. Renan e o Dr. Bruno estao juntos volta duas vezes na captura por OAB.
    Contar as duas infla o denominador do mes.
    """
    lawsuits_por_processo = lawsuits_por_processo or {}
    linhas, vistos = [], set()
    for r in resumos_djen:
        proc_norm = "".join(filter(str.isdigit, r.get("processo") or ""))
        chave = (proc_norm, r.get("data"), normalizar(r.get("texto"))[:400])
        if chave in vistos:
            continue
        vistos.add(chave)
        linhas.append(avaliar(r, lawsuits_por_processo.get(proc_norm), oabs_escritorio))
    return anotar_semanas(linhas)


# ============================================================
# 8. APURACAO (a taxa em si)
# ============================================================

def apurar(linhas, somente_confianca=None):
    """Consolida as linhas na Taxa de Exito Ponderada.

    somente_confianca: lista de niveis a computar (ex.: ['alta']) para ver o
    numero so com o que a automacao leu com seguranca. None = tudo que tem
    peso e resultado.
    """
    def elegivel(l):
        if l["fora_escopo"] or l["contribuicao"] is None:
            return False
        if somente_confianca and l["confianca"] not in somente_confianca:
            return False
        return True

    computadas = [l for l in linhas if elegivel(l)]

    por_adv = defaultdict(lambda: defaultdict(lambda: {"num": 0.0, "den": 0.0, "n": 0}))
    por_carteira = defaultdict(lambda: {"num": 0.0, "den": 0.0, "n": 0})
    # Por KPI DENTRO de cada carteira. Taxa nunca soma rural com diversa -
    # regra da Dra. Juliana (14/09/2026): "sempre ponderada individual, por
    # carteira". Sao reguas distintas (Presidencia x Regulamento de Bonificacao).
    por_kpi = defaultdict(lambda: defaultdict(lambda: {"num": 0.0, "den": 0.0, "n": 0}))
    # A GJ acompanha por dia e por semana: as duas visoes saem da mesma
    # apuracao, e cada uma ainda se abre por carteira (so a rural e' o
    # indicador oficial).
    por_dia = defaultdict(lambda: defaultdict(lambda: {"num": 0.0, "den": 0.0, "n": 0}))
    por_semana = defaultdict(lambda: defaultdict(lambda: {"num": 0.0, "den": 0.0, "n": 0}))

    for l in computadas:
        adv, cart, kpi = l["advogado_responsavel"], l["carteira"], l["kpi"]
        alvos = [por_adv[adv][cart], por_carteira[cart], por_kpi[cart][kpi],
                 por_dia[l.get("data")][cart], por_dia[l.get("data")]["total"],
                 por_semana[l.get("semana")][cart], por_semana[l.get("semana")]["total"]]
        for alvo in alvos:
            alvo["num"] += l["contribuicao"]
            alvo["den"] += l["peso"]
            alvo["n"] += 1

    def taxa(bloco):
        return (bloco["num"] / bloco["den"]) if bloco["den"] else None

    return {
        "computadas": computadas,
        # comparacao por IDENTIDADE, nao por igualdade: duas linhas de dados
        # iguais (mesmo ato, dois advogados intimados) sao dicts iguais, e
        # `not in` derrubaria as duas do relatorio de pendencias.
        "pendentes": [l for l in linhas
                      if not l["fora_escopo"]
                      and not any(l is c for c in computadas)],
        "fora_escopo": [l for l in linhas if l["fora_escopo"]],
        "por_advogado": {a: {c: dict(v, taxa=taxa(v)) for c, v in cs.items()}
                         for a, cs in por_adv.items()},
        "por_carteira": {c: dict(v, taxa=taxa(v)) for c, v in por_carteira.items()},
        "por_kpi": {c: {k: dict(v, taxa=taxa(v)) for k, v in ks.items()}
                    for c, ks in por_kpi.items()},
        "por_dia": {d: {c: dict(v, taxa=taxa(v)) for c, v in cs.items()}
                    for d, cs in por_dia.items()},
        "por_semana": {n: {c: dict(v, taxa=taxa(v)) for c, v in cs.items()}
                       for n, cs in por_semana.items()},
        "total_linhas": len(linhas),
    }


# ============================================================
# 9. RELATORIO
# ============================================================

def _pct(x):
    return "-" if x is None else f"{x*100:.1f}%".replace(".", ",")


def _num(x):
    return "-" if x is None else f"{x:.2f}".replace(".", ",")


def imprimir_relatorio(linhas, apuracao, periodo=""):
    print("=" * 100)
    print("  TAXA DE EXITO JURIDICO PONDERADO - APURACAO AUTOMATICA DAS INTIMACOES")
    if periodo:
        print(f"  Periodo: {periodo}")
    print("=" * 100)
    print(f"\n  {apuracao['total_linhas']} ato(s) unico(s) capturado(s) no DJEN")
    print(f"  {len(apuracao['fora_escopo'])} fora do escopo dos KPIs "
          "(despacho, expediente, questao acessoria)")
    print(f"  {len(apuracao['computadas'])} computado(s) na taxa")
    if apuracao["pendentes"]:
        print(f"  {len(apuracao['pendentes'])} decisao(oes) DENTRO do escopo mas SEM "
              "classificacao fechada - conferir a mao")

    # ---- detalhamento por carteira -> advogado ----
    for carteira in ("rural", "diversa"):
        deste = [l for l in apuracao["computadas"] if l["carteira"] == carteira]
        if not deste:
            continue
        titulo = ("CARTEIRA DE DIVIDAS RURAIS (indicador oficial da Presidencia)"
                  if carteira == "rural"
                  else "CARTEIRA DIVERSA (regua do Regulamento de Bonificacao - a parte)")
        print("\n" + "-" * 100)
        print(f"  {titulo}")
        print("-" * 100)
        print(f"  {'CLIENTE':<34} {'PROCESSO':<26} {'ADVOGADO':<26} {'KPI':<6} "
              f"{'RESULT.':<9} {'PESO':>5} {'CONTR.':>6}  CONF.")
        for adv in sorted({l["advogado_responsavel"] for l in deste}):
            for l in sorted([x for x in deste if x["advogado_responsavel"] == adv],
                            key=lambda x: (x["kpi"], x["data"])):
                print(f"  {l['cliente'][:33]:<34} {l['processo']:<26} "
                      f"{l['advogado_responsavel'][:25]:<26} {l['kpi']:<6} "
                      f"{(l['resultado'] or '-'):<9} {_num(l['peso']):>5} "
                      f"{_num(l['contribuicao']):>6}  {l['confianca']}")
            b = apuracao["por_advogado"][adv][carteira]
            print(f"  {'':<34} {'':<26} {'>> ' + adv[:22]:<26} {'':<6} "
                  f"{'TAXA':<9} {_num(b['den']):>5} {_num(b['num']):>6}  "
                  f"= {_pct(b['num']/b['den'] if b['den'] else None)}")
        tot = apuracao["por_carteira"][carteira]
        print(f"\n  TOTAL {carteira.upper()}: {_num(tot['num'])} / {_num(tot['den'])} "
              f"= {_pct(tot['taxa'])}  ({tot['n']} decisoes)")

    # ---- por KPI, dentro de cada carteira (nunca somadas) ----
    for carteira in ("rural", "diversa"):
        kpis = apuracao["por_kpi"].get(carteira)
        if not kpis:
            continue
        print("\n" + "-" * 100)
        print(f"  POR KPI - CARTEIRA {carteira.upper()}")
        print("-" * 100)
        for k in PESOS:
            if k in kpis:
                b = kpis[k]
                print(f"  {k} - {ROTULO_KPI[k]:<38} {_num(b['num']):>6} / "
                      f"{_num(b['den']):<6} = {_pct(b['taxa'])}  ({b['n']} decisoes)")
        tot = apuracao["por_carteira"][carteira]
        print(f"  {'TOTAL ' + carteira.upper():<46} {_num(tot['num']):>6} / "
              f"{_num(tot['den']):<6} = {_pct(tot['taxa'])}  ({tot['n']} decisoes)")

    # ---- pendencias ----
    if apuracao["pendentes"]:
        print("\n" + "-" * 100)
        print("  DECISOES A CONFERIR - dentro do escopo, sem classificacao fechada")
        print("-" * 100)
        for l in apuracao["pendentes"]:
            print(f"  [{l['data']}] {l['processo']} | {l['cliente'][:40]}")
            print(f"      {l['kpi'] or '?'} - {l['kpi_motivo']}")
            print(f"      falta: {l['evidencia']}")
            if not l["polo"]:
                print(f"      polo: {l['polo_evidencia']}")

    a_confirmar = [l for l in apuracao["computadas"]
                   if l.get("carteira_confianca") == "baixa"]
    if a_confirmar:
        print("\n" + "-" * 100)
        print(f"  {len(a_confirmar)} decisao(oes) na CARTEIRA DIVERSA so por ausencia de "
              "marca rural no texto - confirmar")
        print("-" * 100)
        print("  Acordao publicado so como ementa nao repete a origem rural do processo. "
              "Se\n  a Controladoria confirmar que sao rurais, elas migram de carteira e "
              "mudam as duas taxas.")
        for l in a_confirmar:
            print(f"  {l['processo']} | {l['cliente'][:40]} | {l['kpi']} {l['resultado']}")

    baixas = [l for l in apuracao["computadas"] if l["confianca"] != "alta"]
    if baixas:
        print("\n" + "-" * 100)
        print(f"  {len(baixas)} linha(s) computada(s) com confianca ABAIXO de alta - "
              "conferir antes de fechar o mes")
        print("-" * 100)
        for l in baixas:
            print(f"  [{l['confianca']}] {l['processo']} | {l['cliente'][:36]} | "
                  f"{l['kpi']} {l['resultado']}")
            print(f"      dispositivo lido: \"{(l['evidencia'] or '')[:80]}\"")

    print("\n" + "=" * 100)
    print("  Pre-classificacao automatica por palavra-chave - palpite, nao laudo.")
    print("  O numero oficial do mes continua sendo fechado pela Gerencia Juridica.")
    print("=" * 100)


# ============================================================
# DECISOES DA GERENCIA JURIDICA (ajuste manual auditavel)
# ============================================================
#
# A classificacao automatica e' pre-classificacao: quem fecha a competencia e' a
# GJ. Sem este passo, cada rodada (inclusive a diaria das 08:20) reclassificava
# do zero e desfazia o que a Dra. Juliana decidiu - em 14/09/2026 a rural voltaria
# de 30,6% para 26,0%. As decisoes vivem em docs/kpi_exito/DECISOES_GJ_AAAA-MM.json
# e toda linha ajustada sai marcada em `decisao_gj`, para a correcao ser auditavel.

def carregar_decisoes_gj(caminho):
    import json
    try:
        return json.load(open(caminho, encoding="utf-8")).get("decisoes", [])
    except (OSError, ValueError):
        return []


def aplicar_decisoes_gj(linhas, decisoes):
    """Aplica as decisoes da GJ por cima da classificacao automatica.

    - `carteira`: vale para o processo inteiro (carteira e' do processo).
    - `fora_do_kpi` / `incluir`: valem so para a publicacao da `data` indicada,
      para nao excluir a decisao de merito que ainda vier no mesmo processo.
    Devolve a lista do que foi aplicado, para o relatorio dizer.
    """
    def dig(s):
        return "".join(filter(str.isdigit, s or ""))

    aplicadas = []
    for d in decisoes:
        alvo = dig(d.get("processo"))
        casou = False
        for l in linhas:
            if dig(l.get("processo")) != alvo:
                continue
            if (d.get("fora_do_kpi") or d.get("incluir")) and d.get("data") \
                    and str(l.get("data"))[:10] != d["data"]:
                continue
            casou = True
            nota = f"decisao da GJ ({d.get('decidido_por', 'GJ')}, {d.get('decidido_em', '')}): {d.get('motivo', '')}"
            if d.get("carteira"):
                l["carteira"] = d["carteira"]
                l["origem_carteira"] = nota
                l["carteira_confianca"] = "alta"
            # Polo confirmado pela GJ ("representamos a parte"): so registra; o
            # resultado vem junto em `incluir` quando a confirmacao muda a leitura.
            if d.get("polo"):
                l["polo"] = d["polo"]
            if d.get("recurso_de_quem"):
                l["recurso_de_quem"] = d["recurso_de_quem"]
            if d.get("fora_do_kpi"):
                l.update({"fora_escopo": True, "kpi": None, "kpi_rotulo": None,
                          "resultado": None, "peso": None, "favoravel": None,
                          "contribuicao": None, "confianca": "alta",
                          "confirmar_resultado": False, "kpi_motivo": nota, "evidencia": nota})
            if d.get("incluir") and d.get("kpi") and d.get("resultado"):
                peso = PESOS.get(d["kpi"])
                fav = FAVORAVEL.get(d["resultado"])
                l.update({"fora_escopo": False, "kpi": d["kpi"],
                          "kpi_rotulo": ROTULO_KPI.get(d["kpi"]), "resultado": d["resultado"],
                          "peso": peso, "favoravel": fav,
                          "contribuicao": round(peso * fav, 4) if peso is not None and fav is not None else None,
                          "confianca": "alta", "confirmar_resultado": False,
                          "kpi_motivo": nota,
                          "evidencia": f"{nota} | leitura automatica: {l.get('evidencia') or '-'}"})
            l["decisao_gj"] = nota
            aplicadas.append((l.get("data"), l.get("processo"), nota))
        if not casou and d.get("lancamento_manual") and d.get("incluir") \
                and d.get("kpi") and d.get("resultado") and d.get("data"):
            # Decisao que NAO passa pelo DJEN (intimacao eletronica so no PJe do
            # tribunal - caso de um cliente, TJES, 11/09/2026). Sem isto a GJ nao tinha
            # como lancar o ato: o `incluir` so ajusta publicacao que ja existe.
            nota = f"lancamento manual da GJ ({d.get('decidido_por', 'GJ')}, {d.get('decidido_em', '')}): {d.get('motivo', '')}"
            peso = PESOS.get(d["kpi"])
            fav = FAVORAVEL.get(d["resultado"])
            linhas.append({
                "data": d["data"], "semana_rotulo": "", "cliente": d.get("cliente", ""),
                "processo": d["processo"], "advogado_responsavel": d.get("advogado_responsavel", ""),
                "carteira": d.get("carteira") or "a confirmar", "kpi": d["kpi"],
                "kpi_rotulo": ROTULO_KPI.get(d["kpi"]), "resultado": d["resultado"],
                "peso": peso, "favoravel": fav,
                "contribuicao": round(peso * fav, 4) if peso is not None and fav is not None else None,
                "confianca": "alta", "polo": d.get("polo", ""), "recurso_de_quem": d.get("recurso_de_quem", ""),
                "fora_escopo": False, "kpi_motivo": nota, "evidencia": nota, "confirmar_resultado": False,
                "carteira_confianca": "alta", "origem_carteira": nota, "decisao_gj": nota,
                "tribunal": d.get("tribunal", ""), "orgao": d.get("orgao", ""), "classe": d.get("classe", ""),
                "no_advbox": True, "link_djen": "", "polo_evidencia": "",
            })
            aplicadas.append((d["data"], d["processo"], nota))
        elif not casou:
            aplicadas.append((d.get("data"), d.get("processo"),
                              "NAO APLICADA - publicacao nao encontrada no periodo"))
    return aplicadas


def exportar_csv(linhas, caminho):
    import csv
    campos = ["data", "semana_rotulo", "cliente", "processo",
              "advogado_responsavel", "carteira",
              "kpi", "kpi_rotulo", "resultado", "peso", "favoravel", "contribuicao",
              "confianca", "polo", "recurso_de_quem", "fora_escopo", "kpi_motivo",
              "evidencia", "confirmar_resultado", "carteira_confianca", "origem_carteira",
              "decisao_gj", "tribunal", "orgao", "classe", "no_advbox",
              "link_djen"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", delimiter=";")
        w.writeheader()
        for l in linhas:
            w.writerow(l)
    return caminho
