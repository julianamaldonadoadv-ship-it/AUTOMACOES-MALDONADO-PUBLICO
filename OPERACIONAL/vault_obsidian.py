#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VAULT OBSIDIAN - banco de teses alimentado pela automacao
=========================================================

Enche as duas pastas que o vault tinha vazias (`01 - MAGISTRADOS/` e
`02 - CASOS/`) com o que a automacao ja le todo dia: a apuracao de KPI
(DJEN -> dispositivo lido -> ADVBOX -> cliente, advogado responsavel, grupo).

O que gera
----------
  02 - CASOS/[CLIENTE] - [Nº PROCESSO].md    uma nota por processo com ato
        decidido, com a tabela dos atos lidos e [[link]] para tese e orgao.
  01 - MAGISTRADOS/<foro>/<orgao>.md         uma nota por orgao julgador, com
        os casos e resultados observados ali - a base real do perfil decisorio.
  _PAINEL-CASOS.md / _PAINEL-ORGAOS.md       indices navegaveis do vault.

Guard-rails (mesmo espirito do resto do repositorio)
-----------------------------------------------------
* **A automacao so e' dona do bloco entre marcadores.** O que estiver fora
  dele - fatos, prognostico, analise de perfil - e' texto humano e nunca e'
  sobrescrito. Nota que nao tenha o marcador nao e' tocada de jeito nenhum.
* **A tabela de atos e' lida de volta antes de ser reescrita.** Rodar o
  gerador com o CSV de outubro nao apaga os atos de setembro que ja estavam
  na nota: os dois conjuntos sao fundidos por (data, KPI, dispositivo).
* **Nada e' gravado sem `--gravar` e sem confirmacao "s/N"** no terminal.
* **Nao inventa magistrado.** O DJEN nao entrega o nome em campo estruturado -
  so `nomeOrgao`. O nome do juiz so aparece quando o proprio ato assina, e sai
  sempre com a origem ao lado, para conferencia. Sem assinatura, fica vazio.
* **Nao inventa tese.** O KPI classifica `rural`/`diversa`, que nao e' tese. O
  link para a nota de tema vem do grupo do ADVBOX ou do texto do ato; batendo
  em duas teses ou em nenhuma, a nota sobe como TESE A CONFIRMAR.
* Somente leitura em ADVBOX/DJEN/Drive. So escreve dentro de BASE_CONHECIMENTO/.
"""

import csv
import os
import re
import unicodedata
from datetime import date, datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT_PADRAO = os.environ.get("VAULT_OBSIDIAN_DIR") or os.path.join(RAIZ, "BASE_CONHECIMENTO")

PASTA_CASOS = "02 - CASOS"
PASTA_MAGISTRADOS = "01 - MAGISTRADOS"
PASTA_TEMAS = "00 - TEMAS"

MARCA_INICIO = "<!-- inicio:automacao vault_obsidian.py - nao editar a mao -->"
MARCA_FIM = "<!-- fim:automacao -->"

# Foros do vault. O terceiro existe porque a carteira real nao cabe nos dois
# primeiros: so em 01-11/09/2026 apareceram TJPR, TJMT, TJRJ, TJMA e TRT14.
# Processo do Parana dentro de `TJRO/` seria erro de arquivo, nao organizacao.
FORO_TJRO = "TJRO"
FORO_FEDERAL = "JUSTICA_FEDERAL"
FORO_OUTROS = "OUTROS_TRIBUNAIS"


def _sem_acento(texto):
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()


def _norm(texto):
    return re.sub(r"\s+", " ", _sem_acento(texto).lower()).strip()


# ============================================================
# 1. TESE - o KPI nao classifica tese, entao aqui e' palpite rotulado
# ============================================================
#
# Cada entrada aponta para uma nota que JA EXISTE em `00 - TEMAS/`. Nunca
# apontar para nota inexistente: link quebrado no Obsidian parece dado e nao e'.

TESES = (
    ("MCR-2.6.4-Alongamento", "Prorrogacao / alongamento compulsorio",
     ("alongamento", "prorrogacao da divida", "prorrogacao de divida",
      "prorrogacao de dividas", "mcr 2.6.4", "manual de credito rural",
      "sumula 298")),
    ("Tema28-STJ-Descaracterizacao-Mora", "Descaracterizacao da mora",
     ("descaracterizacao da mora", "descaracterizar a mora", "tema 28",
      "encargos da normalidade", "periodo de normalidade")),
    ("Falha-Assistencia-Tecnica-Justica-Federal", "Mora c/c falha na assistencia tecnica",
     ("assistencia tecnica", "ater ")),
    ("Revisional-Contrato-Bancario-Rural", "Revisional de contrato bancario rural",
     ("revisional", "revisao contratual", "capitalizacao de juros")),
)


def _grupo_do_advbox(origem_carteira):
    """Recupera o `group` do ADVBOX de dentro da origem que o KPI registrou.

    O KPI grava a origem como "ADVBOX group='ALONGAMENTO'" - sem isso seria
    preciso outra chamada de API so para reler o que a linha ja carrega.
    """
    m = re.search(r"group='([^']*)'", origem_carteira or "")
    return m.group(1) if m else ""


def inferir_tese(texto_ato="", grupo_advbox="", classe=""):
    """Devolve (nota_da_tese, origem, confianca).

    Nota None quando nao da para afirmar - e' o caso mais comum e esperado.
    Nunca escolhe "a mais provavel" entre duas: tese ambigua e' confirmacao
    humana, mesma regra do `anexos_inicial.py`.
    """
    g = _norm(grupo_advbox)
    achadas_grupo = [nota for nota, _, marcas in TESES if any(m.strip() in g for m in marcas)]
    if len(achadas_grupo) == 1:
        return achadas_grupo[0], "ADVBOX group='%s'" % grupo_advbox, "alta"
    if len(achadas_grupo) > 1:
        return None, ("grupo do ADVBOX casa com %d teses (%s) - confirmar"
                      % (len(achadas_grupo), ", ".join(achadas_grupo))), "baixa"

    t = _norm(texto_ato)
    achadas = [nota for nota, _, marcas in TESES if any(m in t for m in marcas)]
    if len(achadas) == 1:
        return achadas[0], "texto do ato", "media"
    if len(achadas) > 1:
        return None, ("texto do ato cita %d teses (%s) - confirmar"
                      % (len(achadas), ", ".join(achadas))), "baixa"
    return None, "sem marca de tese no grupo do ADVBOX nem no texto do ato", "baixa"


# ============================================================
# 2. MAGISTRADO - so o que o ato assina; o resto fica vazio
# ============================================================

_NOME = (r"[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][A-Za-zÁÂÃÀÉÊÍÓÔÕÚÜÇáâãàéêíóôõúüç´']+"
         r"(?:\s+(?:d[aeoi]s?\s+|e\s+)?[A-ZÁÂÃÀÉÊÍÓÔÕÚÜÇ][A-Za-zÁÂÃÀÉÊÍÓÔÕÚÜÇáâãàéêíóôõúüç´']+){1,5}")
_CARGO = (r"Ju[ií]z(?:\(a\))?a?\s+(?:de\s+Direito|Federal)(?:\s+Substitut[oa])?"
          r"|Desembargador(?:\(a\))?a?")

# Palavra que denuncia que o "nome" capturado e' instituicao, nao pessoa.
_NAO_E_NOME = ("vara", "tribunal", "justica", "comarca", "poder", "juizado",
               "processo", "estado", "secao", "camara", "turma", "foro",
               "republica", "federal", "gabinete", "cartorio", "autos",
               "documento", "assinatura", "codigo", "sistema", "pje")

_PADROES_MAGISTRADO = (
    ("assinatura eletronica do ato",
     re.compile(r"assinad[oa]\s+(?:eletronicamente|digitalmente)\s+por[:\s]+(" + _NOME + ")")),
    # "Porto Velho, 10 de setembro de 2026 Rinaldo Forti da Silva Juiz de Direito":
    # no PJe o nome e o cargo saem na MESMA linha, so separados por espaco.
    # Exigir virgula ou quebra de linha aqui fazia a extracao falhar em 100%
    # dos atos de 1o grau do TJRO.
    ("nome imediatamente antes do cargo",
     re.compile(r"(" + _NOME + r")[\s,\n\r–—-]+(?:" + _CARGO + ")")),
    ("relator declarado no acordao",
     re.compile(r"Relator(?:\(a\))?a?\s*:?\s*(?:Des(?:embargador)?(?:\(a\))?a?\.?\s*)?(" + _NOME + ")")),
    ("cargo seguido do nome",
     re.compile(r"(?:" + _CARGO + r")\s*[:\-–]\s*(" + _NOME + ")")),
)


# O TJRO publica acordao com nomeOrgao = "Gabinete Des. Raduan Miguel": o
# relator vem de campo estruturado, sem depender de ler o corpo do ato.
_ORGAO_COM_NOME = re.compile(
    r"^Gabinete\s+(?:Des(?:embargador)?(?:\(a\))?a?\.?|Ju[ií]z(?:a)?\.?)\s+(" + _NOME + ")",
    re.I)


def magistrado_do_orgao(orgao):
    """Nome do magistrado quando o proprio orgao julgador o nomeia."""
    m = _ORGAO_COM_NOME.match((orgao or "").strip())
    if not m:
        return None, ""
    return m.group(1).strip(), "nome do orgao no DJEN (%s)" % orgao.strip()


_CONECTIVOS = ("da", "de", "di", "do", "das", "dos", "du", "e")


def _titulo_nome(nome):
    """Caixa de nome proprio brasileiro - `.title()` sozinho da "Forti Da Silva"."""
    palavras = []
    for i, p in enumerate(nome.split()):
        baixo = p.lower()
        palavras.append(baixo if i and baixo in _CONECTIVOS else p.capitalize())
    return " ".join(palavras)


def extrair_magistrado(texto):
    """Devolve (nome, origem) lidos da assinatura do ato, ou (None, motivo).

    Conservador de proposito: nome errado numa nota de perfil decisorio e'
    pior que nota sem nome - a nota inteira passa a descrever o juiz errado.
    """
    if not texto:
        return None, "texto do ato nao disponivel nesta fonte"
    for origem, padrao in _PADROES_MAGISTRADO:
        for m in padrao.finditer(texto):
            nome = re.sub(r"\s+", " ", m.group(1)).strip(" ,.-")
            if any(p in _norm(nome) for p in _NAO_E_NOME):
                continue
            if len(nome) < 8 or len(nome) > 70:
                continue
            return _titulo_nome(nome), origem
    return None, "o ato nao traz assinatura de magistrado em formato reconhecivel"


# ============================================================
# 3. FORO E NOME DE ARQUIVO
# ============================================================

def classificar_foro(tribunal, orgao=""):
    t = (tribunal or "").strip().upper()
    o = _norm(orgao)
    if t.startswith("TRF") or "secao judiciaria" in o or "juizado especial federal" in o:
        return FORO_FEDERAL
    if t == "TJRO":
        return FORO_TJRO
    return FORO_OUTROS


_PROIBIDOS = r'[\\/:*?"<>|#^\[\]]'


def nome_de_arquivo(texto):
    """Nome de nota valido no Obsidian (e no Finder), sem perder legibilidade."""
    limpo = re.sub(_PROIBIDOS, "-", (texto or "").strip())
    limpo = re.sub(r"\s+", " ", limpo).strip(" .-")
    return limpo[:120] or "SEM NOME"


def nome_do_orgao(tribunal, orgao):
    """`TJPR - 14ª Câmara Cível` - o tribunal faz parte do nome, nao e' enfeite.

    "14ª Câmara Cível" existe no TJPR e no TJRJ; "Primeira Câmara de Direito
    Privado", no TJMA e no TJMT. Sem o prefixo, dois tribunais diferentes
    cairiam na MESMA nota de perfil decisorio. O TJRO ja traz a comarca no
    proprio nome ("Porto Velho - 4ª Vara Cível"), entao nao ha o que somar.
    """
    orgao = (orgao or "").strip()
    if not orgao:
        return ""
    trib = (tribunal or "").strip().upper()
    if trib and not orgao.upper().startswith(trib):
        orgao = "%s - %s" % (trib, orgao)
    return nome_de_arquivo(orgao)


def nome_do_caso(cliente, processo):
    """[CLIENTE] - [Nº PROCESSO] - a mesma convencao da pasta PEÇAS AUTOMAÇÃO.

    O escritorio ja nomeia assim no Drive; o vault seguir outra convencao
    obrigaria a Dra. Juliana a traduzir o nome mentalmente a cada consulta.
    """
    c = (cliente or "").strip()
    if not c or c.upper().startswith("NAO ENCONTRADO"):
        c = "CLIENTE A IDENTIFICAR"
    return nome_de_arquivo("%s - %s" % (c, (processo or "SEM PROCESSO").strip()))


# ============================================================
# 4. TABELAS - renderizadas e LIDAS DE VOLTA (a fusao depende disso)
# ============================================================
#
# A nota e' o banco de dados dela mesma: o que a rodada anterior escreveu e'
# lido de volta, fundido com o da rodada de agora e reescrito em ordem. E' o
# que deixa o vault acumular competencia sobre competencia sem sidecar de JSON
# - e o que faz o bloco ser montado DEPOIS da fusao, nunca antes: o resumo do
# orgao precisa contar os atos da nota inteira, nao os desta rodada.

COLUNAS_ATOS = ("Data", "Semana", "KPI", "Resultado", "Confiança",
                "Dispositivo lido", "Publicação")
COLUNAS_ORGAO = ("Data", "Caso", "Tese", "KPI", "Resultado", "Confiança", "Magistrado")

VAZIO = "—"
SEM_KPI = "fora do KPI"


def _celula(texto):
    """Texto seguro dentro de celula de tabela Markdown."""
    return re.sub(r"\s+", " ", (texto or "").replace("|", "/")).strip() or VAZIO


def _deslink(valor):
    """`"[[Nota]]"` -> `Nota`. O frontmatter guarda o link; o codigo quer o nome."""
    m = re.match(r'^"?\[\[(.+?)\]\]"?$', (valor or "").strip())
    return m.group(1) if m else (valor or "").strip()


def _data_br(iso):
    try:
        return datetime.strptime((iso or "")[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return iso or VAZIO


def _data_iso(br):
    try:
        return datetime.strptime((br or "").strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return (br or "").strip()


def _tabela(colunas, linhas_celulas):
    saida = ["| " + " | ".join(colunas) + " |",
             "|" + "|".join(["---"] * len(colunas)) + "|"]
    for cels in linhas_celulas:
        saida.append("| " + " | ".join(cels) + " |")
    return "\n".join(saida)


def _ler_tabela(bloco, colunas):
    """Le de volta as linhas que a rodada anterior escreveu."""
    linhas = []
    cabecalho = "| " + " | ".join(colunas) + " |"
    dentro = False
    for linha in (bloco or "").splitlines():
        if linha.strip() == cabecalho:
            dentro = True
            continue
        if dentro:
            if not linha.strip().startswith("|"):
                dentro = False
                continue
            cels = [c.strip() for c in linha.strip().strip("|").split("|")]
            if len(cels) != len(colunas) or set("".join(cels)) <= set("- "):
                continue
            linhas.append(cels)
    return linhas


def _celulas_ato(ato):
    disp = _celula(ato.get("dispositivo"))
    if len(disp) > 90:
        disp = disp[:89] + "…"
    link = ato.get("link") or ""
    return (_data_br(ato.get("data")),
            _celula(ato.get("semana")),
            _celula(ato.get("kpi") or SEM_KPI),
            _celula(ato.get("resultado") or "a conferir"),
            _celula(ato.get("confianca")),
            '"%s"' % disp,
            "[DJEN](%s)" % link if link else VAZIO)


def _celulas_orgao(ato):
    tese = ato.get("tese")
    return (_data_br(ato.get("data")),
            "[[%s]]" % ato.get("caso"),
            "[[%s]]" % tese if tese else "a confirmar",
            _celula(ato.get("kpi") or SEM_KPI),
            _celula(ato.get("resultado") or "a conferir"),
            _celula(ato.get("confianca")),
            _celula(ato.get("magistrado")))


def _fundir(antigas, novas, chave):
    """Une o que ja estava na nota com o da rodada, sem duplicar nem perder.

    A linha nova vence a antiga de mesma chave - reclassificacao da GJ e'
    justamente o que se quer ver refletido.
    """
    por_chave = {}
    for cels in list(antigas) + list(novas):
        por_chave[chave(cels)] = cels
    return list(por_chave.values())


def _por_data(linhas):
    """Ordem canonica das tabelas. Aplicada na criacao E na fusao - se so uma
    das duas ordenasse, toda rodada marcaria a nota como alterada sem mudanca
    nenhuma de conteudo."""
    return sorted(linhas, key=lambda c: (_data_iso(c[0]), c[1:]))


_CHAVE_ATO = lambda c: (_data_iso(c[0]), c[2], c[5])
_CHAVE_ORGAO = lambda c: (_data_iso(c[0]), c[1], c[3])


# ============================================================
# 5. ESCRITA IDEMPOTENTE - a automacao so e' dona do bloco marcado
# ============================================================

def _fatiar(conteudo):
    """(antes, bloco, depois). bloco None quando a nota nao tem marcador."""
    i = conteudo.find(MARCA_INICIO)
    f = conteudo.find(MARCA_FIM)
    if i == -1 or f == -1 or f < i:
        return conteudo, None, ""
    return (conteudo[:i], conteudo[i + len(MARCA_INICIO):f],
            conteudo[f + len(MARCA_FIM):])


def _carimbar(conteudo, hoje):
    return re.sub(r"^atualizado_em:.*$", "atualizado_em: %s" % hoje,
                  conteudo, count=1, flags=re.M)


def montar_nota(caminho, colunas, chave, celulas_novas, construir_bloco, nota_nova):
    """Devolve (conteudo_final, status) sem gravar nada.

    `construir_bloco(linhas)` recebe as linhas JA FUNDIDAS e ordenadas - e' o
    que garante que o texto do bloco (contagens, magistrados observados) fale
    da nota inteira, e nao so do que esta rodada trouxe.

    status: 'criada' | 'atualizada' | 'inalterada' | 'ignorada (sem marcador)'
    """
    existe = os.path.exists(caminho)
    atual = open(caminho, encoding="utf-8").read() if existe else ""
    antes, bloco_antigo, depois = _fatiar(atual) if existe else ("", None, "")
    if existe and bloco_antigo is None:
        # Nota escrita a mao (ou de outra origem): a automacao nao entra.
        return atual, "ignorada (sem marcador)"

    linhas = _por_data(_fundir(_ler_tabela(bloco_antigo or "", colunas),
                               celulas_novas, chave))
    bloco = construir_bloco(linhas)
    if not existe:
        return nota_nova(bloco), "criada"

    final = antes + MARCA_INICIO + bloco + MARCA_FIM + depois
    if final == atual:
        return atual, "inalterada"
    # `atualizado_em` so anda quando o conteudo anda - senao toda rodada diaria
    # marcaria as 50 notas como alteradas so pela troca da data.
    return _carimbar(final, date.today().isoformat()), "atualizada"


def montar_painel(caminho, bloco, cabecalho):
    """Painel nao funde: e' derivado das notas, reconstruido inteiro a cada vez.

    Fundir aqui ressuscitaria no indice um caso que alguem apagou do vault.
    """
    if not os.path.exists(caminho):
        return cabecalho + MARCA_INICIO + bloco + MARCA_FIM + "\n", "criada"
    atual = open(caminho, encoding="utf-8").read()
    antes, antigo, depois = _fatiar(atual)
    if antigo is None:
        return atual, "ignorada (sem marcador)"
    final = antes + MARCA_INICIO + bloco + MARCA_FIM + depois
    if final == atual:
        return atual, "inalterada"
    return _carimbar(final, date.today().isoformat()), "atualizada"


# ============================================================
# 6. AS NOTAS
# ============================================================

_RODAPE = ("\n> Bloco acima gerado por `OPERACIONAL/vault_obsidian.py` a partir da apuração de "
           "KPI (DJEN → dispositivo lido → ADVBOX). **Pré-classificação por palavra-chave — "
           "palpite, não laudo.** Tudo que estiver fora do bloco é texto seu e nunca é "
           "sobrescrito.\n")


def bloco_caso(linhas, tese, tese_origem, orgao, foro):
    corpo = ["\n## Atos lidos no DJEN\n", _tabela(COLUNAS_ATOS, linhas), ""]
    corpo.append("**Tese:** " + ("[[%s]] — origem: %s" % (tese, tese_origem)
                                 if tese else "`TESE A CONFIRMAR` — %s" % tese_origem))
    corpo.append("**Órgão julgador:** " + ("[[%s]] (%s)" % (orgao, foro) if orgao
                                           else "não informado pela fonte"))
    corpo.append(_RODAPE)
    return "\n".join(corpo)


def nota_caso_nova(dados, bloco):
    """Nota nova = frontmatter + bloco automatico + o esqueleto de `_TEMPLATE-CASO`.

    O esqueleto humano e' o mesmo da nota-modelo que ja estava no vault, para
    caso gerado e caso escrito a mao terem a mesma cara.
    """
    fm = [
        "---",
        "cliente: %s" % (dados.get("cliente") or ""),
        "processo: %s" % (dados.get("processo") or ""),
        'tese: %s' % ('"[[%s]]"' % dados["tese"] if dados.get("tese") else ""),
        "tese_origem: %s" % (dados.get("tese_origem") or ""),
        "magistrado: %s" % (dados.get("magistrado") or ""),
        "magistrado_origem: %s" % (dados.get("magistrado_origem") or ""),
        'orgao: %s' % ('"[[%s]]"' % dados["orgao"] if dados.get("orgao") else ""),
        "foro: %s" % (dados.get("foro") or ""),
        "tribunal: %s" % (dados.get("tribunal") or ""),
        "carteira: %s" % (dados.get("carteira") or ""),
        "advogado_responsavel: %s" % (dados.get("advogado") or ""),
        "status: em andamento",
        "resultado: %s" % (dados.get("resultado_ultimo") or "aguardando"),
        "fonte: vault_obsidian.py (apuração de KPI)",
        "atualizado_em: %s" % date.today().isoformat(),
        "---",
        "",
        "# %s" % dados["caso"],
        "",
    ]
    humano = [
        "",
        "",
        "## Fatos-chave",
        "",
        "## Contrato",
        "- Cédula(s):",
        "- Banco / réu:",
        "- Data de celebração:",
        "- Taxa pactuada:",
        "- Cláusula expressa de capitalização? ( ) sim ( ) não",
        "- Garantia:",
        "",
        "## Tese aplicada",
        "",
        "## Prognóstico registrado (ANTES da decisão)",
        "> Estimativa profissional — faixa qualitativa (baixa / média / alta) + justificativa.",
        "> Nunca percentual fabricado.",
        "",
        "## Resultado real (APÓS a decisão)",
        "> Preencher quando sair. É isto que calibra o próximo prognóstico.",
        "",
        "## Ligações",
        "[[INDICE]] · [[_PAINEL-CASOS]]",
        "",
    ]
    return ("\n".join(l.rstrip() for l in fm) + MARCA_INICIO + bloco + MARCA_FIM
            + "\n".join(humano))


def _resumo_das_linhas(linhas):
    """Resumo do orgao lido das LINHAS DA NOTA - todas, nao so as desta rodada."""
    dentro = [c for c in linhas if c[3] != SEM_KPI]
    conta = lambda r: sum(1 for c in dentro if c[4] == r)
    return {
        "atos": len(linhas),
        "casos": len({c[1] for c in linhas}),
        "dentro_kpi": len(dentro),
        "exito": conta("êxito"),
        "parcial": conta("parcial"),
        "inexito": conta("inêxito"),
        "a_conferir": sum(1 for c in dentro if c[4] == "a conferir"),
        "magistrados": {c[6] for c in linhas if c[6] not in ("", VAZIO)},
        "teses": {_deslink(c[2]) for c in linhas if c[2].startswith("[[")},
    }


def bloco_orgao(linhas):
    resumo = _resumo_das_linhas(linhas)
    corpo = ["\n## Atos observados neste órgão\n", _tabela(COLUNAS_ORGAO, linhas), "",
             "## O que a base já mostra\n"]
    corpo.append("- Atos lidos: **%d** em **%d** caso(s)." % (resumo["atos"], resumo["casos"]))
    if resumo["dentro_kpi"]:
        corpo.append("- Dentro do KPI: **%d** — êxito %d · parcial %d · inêxito %d · "
                     "a conferir %d." % (resumo["dentro_kpi"], resumo["exito"],
                                         resumo["parcial"], resumo["inexito"],
                                         resumo["a_conferir"]))
    else:
        corpo.append("- Nenhum ato deste órgão entrou em KPI "
                     "(despacho/expediente não compõe indicador).")
    if resumo["magistrados"]:
        corpo.append("- Magistrado(s) identificado(s) nos atos lidos: "
                     + " · ".join(sorted(resumo["magistrados"]))
                     + ". **Conferir** — vem da assinatura do ato ou do nome do órgão.")
    else:
        corpo.append("- **Magistrado: sem dado.** Nenhum dos atos lidos traz assinatura em "
                     "formato reconhecível — o DJEN não entrega o nome em campo estruturado.")
    if resumo["teses"]:
        corpo.append("- Teses envolvidas: " + " · ".join("[[%s]]" % t
                                                         for t in sorted(resumo["teses"])) + ".")
    corpo.append("")
    corpo.append("> **%d ato(s) não é amostra de perfil decisório.** Isto é base bruta em "
                 "formação — a leitura de tendência é humana, e só depois de volume."
                 % resumo["atos"])
    corpo.append(_RODAPE)
    return "\n".join(corpo)


def nota_orgao_nova(orgao, foro, tribunal, bloco):
    fm = [
        "---",
        "tipo: orgao-julgador",
        "orgao: %s" % orgao,
        "foro: %s" % foro,
        "tribunal: %s" % (tribunal or ""),
        "magistrado_titular:",
        "fonte: vault_obsidian.py (apuração de KPI)",
        "atualizado_em: %s" % date.today().isoformat(),
        "---",
        "",
        "# %s" % orgao,
        "",
    ]
    humano = [
        "",
        "",
        "## Perfil decisório (análise humana)",
        "> Preencher com a leitura de tendência — **nunca com estatística fabricada**.",
        "> Se não houver dado suficiente, registrar exatamente isso.",
        "",
        "## Precedentes desta vara/câmara",
        "",
        "## Observações práticas",
        "> Ritmo de despacho, exigências formais recorrentes, o que costuma pesar.",
        "",
        "## Ligações",
        "[[INDICE]] · [[_PAINEL-ORGAOS]]",
        "",
    ]
    return ("\n".join(l.rstrip() for l in fm) + MARCA_INICIO + bloco + MARCA_FIM
            + "\n".join(humano))


# ============================================================
# 7. CARGA - do CSV do KPI ou das linhas em memoria (modo ao vivo)
# ============================================================

_ROTULO_RESULTADO = {"exito": "êxito", "inexito": "inêxito", "parcial": "parcial"}


def _bool(valor):
    if isinstance(valor, bool):
        return valor
    return str(valor or "").strip().lower() in ("true", "1", "sim", "s")


def ultimo_csv(pasta=None):
    """O CSV de KPI mais recente ja gerado - evita digitar o caminho."""
    pasta = pasta or os.path.join(RAIZ, "docs", "kpi_exito")
    if not os.path.isdir(pasta):
        return None
    achados = [os.path.join(pasta, n) for n in os.listdir(pasta)
               if n.startswith("kpi_") and n.endswith(".csv")]
    return max(achados, key=os.path.getmtime) if achados else None


def carregar_csv(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def preparar(linhas, incluir_fora_escopo=False):
    """Linha do KPI -> ato pronto para virar nota. Devolve (atos, descartados).

    Por padrao so entra ato DECIDIDO: das 112 intimacoes de 01-10/09/2026 so
    21 eram decisao classificavel. Despacho e expediente virariam 90 notas de
    caso sem resultado nenhum - ruido que enterra o sinal no vault.
    """
    atos, descartados = [], []
    for l in linhas:
        fora = _bool(l.get("fora_escopo"))
        if fora and not incluir_fora_escopo:
            descartados.append(l)
            continue
        processo = (l.get("processo") or "").strip()
        if not processo:
            descartados.append(l)
            continue

        texto = l.get("_texto") or ""
        grupo = _grupo_do_advbox(l.get("origem_carteira"))
        tese, tese_origem, tese_conf = inferir_tese(texto, grupo, l.get("classe"))
        orgao_bruto = (l.get("orgao") or "").strip()
        # O orgao que se nomeia ("Gabinete Des. X") vence a leitura do corpo do
        # ato: e' campo estruturado, nao heuristica sobre texto.
        magistrado, mag_origem = magistrado_do_orgao(orgao_bruto)
        if not magistrado:
            magistrado, mag_origem = extrair_magistrado(texto)
        resultado = (l.get("resultado") or "").strip()

        atos.append({
            "data": (l.get("data") or "")[:10],
            "semana": l.get("semana_rotulo") or "",
            "cliente": (l.get("cliente") or "").strip(),
            "processo": processo,
            "caso": nome_do_caso(l.get("cliente"), processo),
            "advogado": (l.get("advogado_responsavel") or "").strip(),
            "carteira": (l.get("carteira") or "").strip(),
            "kpi": l.get("kpi") or "",
            "kpi_rotulo": l.get("kpi_rotulo") or "",
            "resultado": _ROTULO_RESULTADO.get(resultado, resultado),
            "confianca": l.get("confianca") or "",
            "confirmar": _bool(l.get("confirmar_resultado")),
            "dispositivo": l.get("evidencia") or "",
            "link": l.get("link_djen") or "",
            "tribunal": (l.get("tribunal") or "").strip(),
            "orgao": nome_do_orgao(l.get("tribunal"), orgao_bruto),
            "foro": classificar_foro(l.get("tribunal"), orgao_bruto),
            "tese": tese,
            "tese_origem": tese_origem,
            "tese_confianca": tese_conf,
            "magistrado": magistrado,
            "magistrado_origem": mag_origem,
            "fora_escopo": fora,
        })
    return atos, descartados


# ============================================================
# 8. PLANO - o que seria escrito, antes de escrever
# ============================================================

def _frontmatter_arquivo(caminho):
    if not os.path.exists(caminho):
        return {}
    try:
        return _frontmatter(open(caminho, encoding="utf-8").read())
    except OSError:
        return {}


def _agrupar(atos, chave):
    grupos = {}
    for a in atos:
        k = chave(a)
        if k:
            grupos.setdefault(k, []).append(a)
    for k in grupos:
        grupos[k].sort(key=lambda a: a["data"])
    return grupos


def _o_que_a_nota_ja_sabe(do_caso, ja_sabido, campo, campo_origem, padrao_origem):
    """Valor + origem, preferindo o que ESTA rodada descobriu.

    Quando a rodada nao descobriu, vale o que a nota ja registrava. Sem isso,
    rodar `--csv` depois de uma rodada ao vivo rebaixaria a nota: o CSV nao
    carrega o texto do ato, e tese, orgao e magistrado "desapareceriam".
    """
    achado = next((a[campo] for a in reversed(do_caso) if a[campo]), None)
    if achado:
        return achado, next(a[campo_origem] for a in reversed(do_caso) if a[campo])
    # Rodada que nao descobriu nada nao mexe em nada: fica o valor E a origem
    # que a nota ja registrava. A origem importa tanto quanto o valor - "texto
    # do ato cita 2 teses (X, Y) - confirmar" diz o que conferir; "sem marca de
    # tese", que e' o que uma fonte sem texto devolve, nao diz.
    return (_deslink(ja_sabido.get(campo)) or None,
            (ja_sabido.get(campo_origem) or "").strip() or padrao_origem)


def planejar(atos, vault=VAULT_PADRAO):
    """Monta o conteudo final de cada nota. NAO grava - devolve o plano."""
    plano = []

    for caso, do_caso in sorted(_agrupar(atos, lambda a: a["caso"]).items()):
        ultimo = do_caso[-1]
        caminho = os.path.join(vault, PASTA_CASOS, caso + ".md")
        ja_sabido = _frontmatter_arquivo(caminho)

        # Tese/orgao/magistrado vem do ato mais recente que soube dizer - ato
        # antigo pode ser despacho generico, sem marca de tese nenhuma.
        tese, tese_origem = _o_que_a_nota_ja_sabe(
            do_caso, ja_sabido, "tese", "tese_origem", ultimo["tese_origem"])
        magistrado, mag_origem = _o_que_a_nota_ja_sabe(
            do_caso, ja_sabido, "magistrado", "magistrado_origem", ultimo["magistrado_origem"])
        orgao = (next((a["orgao"] for a in reversed(do_caso) if a["orgao"]), "")
                 or _deslink(ja_sabido.get("orgao")))
        foro = ultimo["foro"] or ja_sabido.get("foro", "")

        for a in do_caso:
            a["tese"] = a["tese"] or tese
            a["orgao"] = a["orgao"] or orgao
            a["magistrado"] = a["magistrado"] or magistrado

        dados = {"caso": caso, "cliente": ultimo["cliente"], "processo": ultimo["processo"],
                 "tese": tese, "tese_origem": tese_origem, "orgao": orgao,
                 "magistrado": magistrado, "magistrado_origem": mag_origem,
                 "foro": foro, "tribunal": ultimo["tribunal"],
                 "carteira": ultimo["carteira"], "advogado": ultimo["advogado"],
                 "resultado_ultimo": ultimo["resultado"] or "aguardando"}
        conteudo, status = montar_nota(
            caminho, COLUNAS_ATOS, _CHAVE_ATO, [_celulas_ato(a) for a in do_caso],
            lambda linhas, d=dados, f=foro: bloco_caso(linhas, d["tese"], d["tese_origem"],
                                                       d["orgao"], f),
            lambda bloco, d=dados: nota_caso_nova(d, bloco))
        plano.append({"tipo": "caso", "nome": caso, "caminho": caminho,
                      "conteudo": conteudo, "status": status, "atos": len(do_caso)})

    for orgao, do_orgao in sorted(_agrupar(atos, lambda a: a["orgao"]).items()):
        ultimo = do_orgao[-1]
        caminho = os.path.join(vault, PASTA_MAGISTRADOS, ultimo["foro"], orgao + ".md")
        conteudo, status = montar_nota(
            caminho, COLUNAS_ORGAO, _CHAVE_ORGAO, [_celulas_orgao(a) for a in do_orgao],
            bloco_orgao,
            lambda bloco, o=orgao, u=ultimo: nota_orgao_nova(o, u["foro"], u["tribunal"], bloco))
        plano.append({"tipo": "orgao", "nome": orgao, "caminho": caminho,
                      "conteudo": conteudo, "status": status, "atos": len(do_orgao)})

    plano.extend(_planejar_paineis(plano, vault))
    return plano


# ============================================================
# 9. PAINEIS - lidos do VAULT INTEIRO, nao so da rodada
# ============================================================
#
# Se o painel saisse so das notas desta rodada, rodar o gerador com o CSV de
# um mes faria sumir do indice todos os casos dos meses anteriores.

def _frontmatter(conteudo):
    m = re.match(r"^---\n(.*?)\n---", conteudo or "", re.S)
    if not m:
        return {}
    dados = {}
    for linha in m.group(1).splitlines():
        if ":" in linha and not linha.startswith(" "):
            chave, _, valor = linha.partition(":")
            dados[chave.strip()] = valor.strip().strip('"')
    return dados


def _notas_da_pasta(vault, subpasta, planejadas):
    """Uniao do que ja esta no disco com o que esta planejado (ainda nao gravado)."""
    notas = dict(planejadas)
    for pasta_atual, _, arquivos in os.walk(os.path.join(vault, subpasta)):
        for nome in arquivos:
            caminho = os.path.join(pasta_atual, nome)
            if not nome.endswith(".md") or nome.startswith("_") or caminho in notas:
                continue
            notas[caminho] = open(caminho, encoding="utf-8").read()
    return notas


def _cabecalho_painel(titulo, subtitulo):
    return ("---\ntipo: painel\nfonte: vault_obsidian.py\natualizado_em: %s\n---\n\n"
            "# %s\n\n%s\n\n" % (date.today().isoformat(), titulo, subtitulo))


def _planejar_paineis(plano, vault):
    hoje = date.today().strftime("%d/%m/%Y")
    saida = []

    # ---- casos ----
    casos = _notas_da_pasta(vault, PASTA_CASOS,
                            {p["caminho"]: p["conteudo"] for p in plano if p["tipo"] == "caso"})
    linhas = []
    for caminho, conteudo in casos.items():
        nome = os.path.splitext(os.path.basename(caminho))[0]
        if nome.startswith("_"):
            continue
        fm = _frontmatter(conteudo)
        atos = _ler_tabela(_fatiar(conteudo)[1] or "", COLUNAS_ATOS)
        ultimo = atos[-1] if atos else None
        linhas.append(("[[%s]]" % nome, fm.get("tese") or "a confirmar",
                       fm.get("orgao") or VAZIO, fm.get("carteira") or VAZIO,
                       str(len(atos)), ultimo[0] if ultimo else VAZIO,
                       ultimo[3] if ultimo else VAZIO))
    linhas.sort(key=lambda c: (_data_iso(c[5]), c[0]), reverse=True)
    colunas = ("Caso", "Tese", "Órgão", "Carteira", "Atos", "Último ato", "Último resultado")
    bloco = ("\n" + _tabela(colunas, linhas)
             + "\n\n**%d caso(s)** no vault. Atualizado em %s.\n" % (len(linhas), hoje)
             + _RODAPE)
    caminho = os.path.join(vault, PASTA_CASOS, "_PAINEL-CASOS.md")
    conteudo, status = montar_painel(caminho, bloco, _cabecalho_painel(
        "Painel de casos",
        "Uma linha por processo com ato decidido lido no DJEN.\n"
        "Modelo de nota escrita à mão: [[_TEMPLATE-CASO]] · Índice: [[INDICE]]"))
    saida.append({"tipo": "painel", "nome": "_PAINEL-CASOS", "caminho": caminho,
                  "conteudo": conteudo, "status": status, "atos": len(linhas)})

    # ---- orgaos ----
    orgaos = _notas_da_pasta(vault, PASTA_MAGISTRADOS,
                             {p["caminho"]: p["conteudo"] for p in plano if p["tipo"] == "orgao"})
    linhas = []
    for caminho_o, conteudo_o in orgaos.items():
        nome = os.path.splitext(os.path.basename(caminho_o))[0]
        if nome.startswith("_"):
            continue
        fm = _frontmatter(conteudo_o)
        atos = _ler_tabela(_fatiar(conteudo_o)[1] or "", COLUNAS_ORGAO)
        observados = sorted({a[6] for a in atos if a[6] not in ("", VAZIO)})
        linhas.append((fm.get("foro") or os.path.basename(os.path.dirname(caminho_o)),
                       "[[%s]]" % nome, fm.get("tribunal") or VAZIO,
                       fm.get("magistrado_titular") or (" · ".join(observados) or "sem dado"),
                       str(len(atos)), str(len({a[1] for a in atos}))))
    linhas.sort(key=lambda c: (c[0], -int(c[4]), c[1]))
    colunas = ("Foro", "Órgão julgador", "Tribunal", "Magistrado", "Atos", "Casos")
    bloco = ("\n" + _tabela(colunas, linhas)
             + "\n\n**%d órgão(s)** com ato observado. Atualizado em %s.\n" % (len(linhas), hoje)
             + "\n> *Magistrado* sai da assinatura do ato ou do nome do órgão "
               "(`Gabinete Des. X`) — **confira antes de usar**. Preenchendo "
               "`magistrado_titular` no frontmatter da nota, esse valor prevalece.\n"
             + _RODAPE)
    caminho_p = os.path.join(vault, PASTA_MAGISTRADOS, "_PAINEL-ORGAOS.md")
    conteudo_p, status_p = montar_painel(caminho_p, bloco, _cabecalho_painel(
        "Painel de órgãos julgadores",
        "Base bruta do perfil decisório: onde os atos do escritório foram proferidos.\n"
        "Índice: [[INDICE]]"))
    saida.append({"tipo": "painel", "nome": "_PAINEL-ORGAOS", "caminho": caminho_p,
                  "conteudo": conteudo_p, "status": status_p, "atos": len(linhas)})
    return saida


# ============================================================
# 10. GRAVACAO - so depois de "s/N"
# ============================================================

def gravar(plano):
    escritos = 0
    for item in plano:
        if item["status"] in ("inalterada", "ignorada (sem marcador)"):
            continue
        os.makedirs(os.path.dirname(item["caminho"]), exist_ok=True)
        with open(item["caminho"], "w", encoding="utf-8") as f:
            f.write(item["conteudo"])
        escritos += 1
    return escritos


# ============================================================
# 11. RELATORIO NA TELA
# ============================================================

def imprimir_plano(plano, atos, descartados, fonte, vault):
    print("=" * 100)
    print("  VAULT OBSIDIAN - BANCO DE TESES")
    print("=" * 100)
    print("\n  Vault:  %s" % vault)
    print("  Fonte:  %s" % fonte)
    print("  Atos aproveitados: %d   |   fora do KPI, nao viraram nota: %d"
          % (len(atos), len(descartados)))

    for tipo, titulo in (("caso", "CASOS"), ("orgao", "ORGAOS JULGADORES"),
                         ("painel", "PAINEIS")):
        itens = [p for p in plano if p["tipo"] == tipo]
        if not itens:
            continue
        print("\n" + "-" * 100)
        print("  %s (%d)" % (titulo, len(itens)))
        print("-" * 100)
        for p in sorted(itens, key=lambda x: (x["status"], x["nome"])):
            marca = {"criada": "[+]", "atualizada": "[~]", "inalterada": "[=]"}.get(
                p["status"], "[!]")
            print("  %s %-62s %-22s %d ato(s)"
                  % (marca, p["nome"][:62], p["status"], p["atos"]))

    pendencias = []
    sem_tese = sorted({a["caso"] for a in atos if not a["tese"]})
    if sem_tese:
        pendencias.append(("Caso(s) sem tese identificada - o link para a nota de tema fica "
                           "vazio ate alguem confirmar", sem_tese))
    sem_orgao = sorted({a["caso"] for a in atos if not a["orgao"]})
    if sem_orgao:
        pendencias.append(("Ato(s) sem orgao julgador na fonte - nao geram nota em "
                           "01 - MAGISTRADOS/ (CSV antigo nao traz a coluna `orgao`; "
                           "regere com `main.py kpi --csv`)", sem_orgao))
    confirmar = sorted({a["caso"] for a in atos if a["confirmar"]})
    if confirmar:
        pendencias.append(("Resultado marcado `confirmar_resultado` pelo KPI - decisao da GJ, "
                           "nao da automacao", confirmar))
    ignoradas = [p["nome"] for p in plano if p["status"].startswith("ignorada")]
    if ignoradas:
        pendencias.append(("Nota(s) existente(s) SEM o marcador da automacao - preservadas "
                           "intactas, nada foi escrito nelas", sorted(ignoradas)))

    if pendencias:
        print("\n" + "=" * 100)
        print("  A CONFERIR")
        print("=" * 100)
        for titulo, itens in pendencias:
            print("\n  %s (%d):" % (titulo, len(itens)))
            for i in itens[:12]:
                print("     - %s" % i)
            if len(itens) > 12:
                print("     ... e mais %d" % (len(itens) - 12))

    print("\n" + "=" * 100)
    print("  Classificacao de tese e leitura de dispositivo sao pre-classificacao por")
    print("  palavra-chave - palpite, nao laudo. Prognostico e perfil decisorio continuam")
    print("  sendo escritos a mao, fora do bloco automatico.")
    print("=" * 100)


def executar(linhas, vault=VAULT_PADRAO, incluir_fora_escopo=False, fonte="", gravar_=False,
             confirmar=None):
    """Fluxo completo: preparar -> planejar -> relatorio -> (confirmacao) -> gravar."""
    atos, descartados = preparar(linhas, incluir_fora_escopo)
    if not atos:
        print("\n  Nenhum ato aproveitavel na fonte informada.")
        print("  (Por padrao so entram atos DENTRO do KPI; use --incluir-fora-escopo "
              "para trazer despacho e expediente tambem.)")
        return []
    plano = planejar(atos, vault)
    imprimir_plano(plano, atos, descartados, fonte, vault)

    a_escrever = [p for p in plano if p["status"] in ("criada", "atualizada")]
    if not gravar_:
        print("\n  Simulacao: nada foi gravado. %d nota(s) seriam escritas."
              % len(a_escrever))
        print("  Para gravar de fato: repita o comando com --gravar")
        return plano
    if not a_escrever:
        print("\n  Nada a gravar - o vault ja esta em dia.")
        return plano

    print("\n  Serao escritas %d nota(s) em %s" % (len(a_escrever), vault))
    resposta = confirmar() if confirmar else input("  Confirma? (s/N): ")
    if (resposta or "").strip().lower() != "s":
        print("  Cancelado. Nada foi gravado.")
        return plano
    print("  %d nota(s) gravada(s)." % gravar(plano))
    return plano


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Gera as notas de caso e de orgao julgador do vault Obsidian "
                    "a partir da apuracao de KPI.")
    ap.add_argument("--csv", help="CSV do KPI (padrao: o mais recente de docs/kpi_exito/)")
    ap.add_argument("--vault", default=VAULT_PADRAO, help="Raiz do vault")
    ap.add_argument("--incluir-fora-escopo", action="store_true",
                    help="Tambem gera nota para despacho/expediente (padrao: so decisao)")
    ap.add_argument("--gravar", action="store_true",
                    help="Grava de fato (ainda pede confirmacao s/N)")
    args = ap.parse_args()

    caminho = args.csv or ultimo_csv()
    if not caminho or not os.path.exists(caminho):
        print("  ERRO: nenhum CSV de KPI encontrado. Rode antes:")
        print("     python OPERACIONAL/main.py kpi --de AAAA-MM-DD --ate AAAA-MM-DD "
              "--csv saida.csv")
        return 1
    executar(carregar_csv(caminho), vault=args.vault,
             incluir_fora_escopo=args.incluir_fora_escopo,
             fonte="CSV de KPI: %s" % caminho, gravar_=args.gravar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
