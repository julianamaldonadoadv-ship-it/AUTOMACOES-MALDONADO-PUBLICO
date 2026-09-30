# -*- coding: utf-8 -*-
"""
Busca de jurisprudencia no DJEN (CNJ) - todos os tribunais, sem login
=====================================================================
O DJEN publica o teor integral de decisao, sentenca e acordao de todos os
tribunais que usam o Diario de Justica Eletronico Nacional - inclusive o STJ -
e a API aceita busca por texto (`texto`). Isso vira pesquisa de jurisprudencia
por tema, publica e gratuita, que roda na VPS sem depender de navegador.

    python OPERACIONAL/main.py jurisprudencia "Sumula 298"
    python OPERACIONAL/main.py jurisprudencia "Sumula 298" --tambem "frustracao de safra" --favoravel
    python OPERACIONAL/main.py jurisprudencia "descaracterizacao da mora" --tribunal TJRO,STJ --meses 12

Regras e armadilhas (nao desfazer):
- **A API casa palavras soltas, nao a frase** (com ou sem aspas, mesmo count).
  A frase e os termos de `--tambem` sao conferidos aqui, no texto normalizado.
- **Nem toda ementa do texto e' do julgado publicado.** Tres origens:
    propria   -> acordao cuja ementa e' a dele (TJRO: "DECISAO: ... Ementa:")
    recorrida -> decisao do STJ que transcreve o acordao de origem ("acordao
                 assim ementado"): e' ementa do TJ, NUNCA citar como STJ
    citada    -> jurisprudencia transcrita no corpo, com a referencia entre
                 parenteses: serve de pista, a citacao sai da fonte original
  So a `propria` vira citacao sugerida.
- **O resultado e' lido so do dispositivo** (`kpi_exito.extrair_dispositivo`),
  pelo mesmo motivo do KPI: o corpo transcreve decisao recorrida e ementas.
- **Favoravel ao produtor e' leitura automatica**: sai de quem recorreu/ajuizou
  (banco ou nao) e do verbo do dispositivo. Sem lado identificado, "a conferir".
- **CPF e CNPJ sao mascarados** na saida - o teor do DJEN traz a qualificacao.
- Somente leitura. A saida em Markdown vai para `_trabalho/jurisprudencia/`
  (gitignored: tem nome de parte). Toda citacao sai marcada "conferir inteiro
  teor" - a peca so leva ementa conferida no tribunal de origem.
"""

import html
import json
import os
import re
import sys
import time
import unicodedata
from collections import OrderedDict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.dirname(__file__))

import comunica_djen  # noqa: E402
import kpi_exito  # noqa: E402
import vault_obsidian  # noqa: E402

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PASTA_SAIDA = os.path.join(RAIZ, '_trabalho', 'jurisprudencia')

# Ramos que nao interessam a divida rural: "Sumula 298" no TRT e' a do TST
# (acao rescisoria), e a busca sem tribunal traz centenas delas.
_RAMOS_EXCLUIDOS = re.compile(r'^(TRT\d+|TST|TRE-?[A-Z]{2}|TSE|STM|TJM[A-Z]{2})$')

_TIPOS_SEM_CONTEUDO = ('despacho', 'certidao', 'ato ordinatorio', 'edital', 'pauta', 'ata de distribuicao',
                       'vista a')


def _tipo_sem_conteudo(tipo_doc):
    # O STJ rotula toda decisao monocratica como "DESPACHO / DECISAO": sem a
    # ressalva, 7.895 decisoes do STJ saiam da base como despacho (17/09/2026).
    if 'decisao' in tipo_doc or 'acordao' in tipo_doc or 'sentenca' in tipo_doc:
        return False
    return any(t in tipo_doc for t in _TIPOS_SEM_CONTEUDO)


# ============================================================
# 1. TEXTO
# ============================================================

def texto_plano(bruto):
    """HTML do DJEN -> texto corrido preservando caixa e acento (para citar)."""
    t = html.unescape(bruto or '')
    t = re.sub(r'<br\s*/?>|</(?:p|tr|div|li)>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\s*\n\s*', '\n', t).strip()


def normalizar_com_mapa(plano):
    """Normaliza como `kpi_exito.normalizar` e guarda, para cada caractere do
    resultado, a posicao no texto original - assim o trecho achado no texto
    normalizado e' recortado do original, com acento e caixa."""
    saida, mapa = [], []
    espaco = False
    for i, c in enumerate(plano):
        n = unicodedata.normalize('NFKD', c).encode('ascii', 'ignore').decode().lower()
        if not n:
            continue
        if n.isspace():
            if espaco or not saida:
                continue
            n, espaco = ' ', True
        else:
            espaco = False
        for ch in n:
            saida.append(ch)
            mapa.append(i)
    return ''.join(saida), mapa


def _original(plano, mapa, ini, fim):
    if ini >= len(mapa):
        return ''
    a = mapa[ini]
    b = mapa[fim - 1] + 1 if fim - 1 < len(mapa) else len(plano)
    return plano[a:b].strip()


def _padrao_termo(termo):
    """Frase normalizada com espaco flexivel ('sumula 298' casa 'Súmula  298')."""
    partes = kpi_exito.normalizar(termo).split()
    return re.compile(r'\b' + r'\s+'.join(re.escape(p) for p in partes) + r'\b')


def mascarar_documentos(texto):
    t = re.sub(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '***.***.***-**', texto or '')
    return re.sub(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b', '**.***.***/****-**', t)


# ============================================================
# 2. EMENTA - de quem ela e'
# ============================================================

_ANUNCIO_RECORRIDA = re.compile(
    r'(?:acordao|aresto|julgado)\s+(?:recorrido\s+)?(?:assim|ementado|com a seguinte|nos seguintes)|'
    r'assim ementad[oa]|ementad[oa] nos seguintes termos|acordao recorrido|'
    r'cuja ementa|seguinte ementa|guarda os seguintes termos|nos termos da ementa|'
    r'segue (?:abaixo )?transcrita|no que ha de relevante')
_FIM_EMENTA = re.compile(
    r'\b(?:relatorio\b|vistos,? relatados|acordam\b|voto\b|e o relatorio|'
    r'publique-se|intime-se|intimem-se|trata-se de)')
# Referencia de precedente entre parenteses: "(TJ-RO - AGRAVO...)", "(STJ, AgInt...)"
_REFERENCIA = re.compile(
    r'\((?:tj-?[a-z]{2}|stj|stf|trf-?\d|tj[a-z]{2}|resp|agint|aresp|ai n)[^()]{10,400}\)')
_ABRE_CITACAO = re.compile(
    r'(?:a proposito|nesse sentido|neste sentido|confira-se|veja-se|cito|colaciono|'
    r'in verbis|segue|seguinte julgado|jurisprudencia)\s*:')


def ementa_propria(norm, plano, mapa):
    """Ementa do proprio acordao, ou None.

    E' propria quando aparece no cabecalho (primeiros ~3.000 caracteres), sem
    anuncio de acordao recorrido antes dela e sem referencia de outro julgado
    logo depois. Acordao do TJRO traz o campo "decisao:" e a ementa em seguida.
    """
    m = re.search(r'\bementa\s*[:\-]?\s', norm[:3000])
    if not m:
        return None
    # A janela inclui a propria palavra "ementa": "contra acordao cuja ementa segue
    # transcrita" (ED no TRF1) so casa o anuncio com ela dentro.
    antes = norm[max(0, m.start() - 400):m.end() + 40]
    if _ANUNCIO_RECORRIDA.search(antes) or _ABRE_CITACAO.search(antes) or \
            re.search(r'embargos de declaracao opostos', norm[:m.start()]):
        return None
    cabecalho = norm[:m.start()]
    if not ('acordao' in cabecalho or 'decisao:' in cabecalho or m.start() < 400):
        return None
    ini = m.end()
    fim_m = _FIM_EMENTA.search(norm, ini + 80)
    fim = min(fim_m.start() if fim_m else len(norm), ini + 6000)
    return _original(plano, mapa, ini, fim)


def ementas_recorridas(norm, plano, mapa):
    """Ementa do acordao de origem transcrita em decisao de tribunal superior."""
    saida = []
    for m in _ANUNCIO_RECORRIDA.finditer(norm):
        ini = norm.find(':', m.end(), m.end() + 200)
        if ini < 0:
            continue
        fim_m = re.search(r'\b(?:opostos? embargos|nas razoes|nas razoes do recurso|'
                          r'a parte (?:agravante|recorrente)|alega(?:-se)?|sustenta|'
                          r'e o relatorio|decido)\b', norm[ini + 1:ini + 8000])
        fim = ini + 1 + (fim_m.start() if fim_m else min(3000, len(norm) - ini - 1))
        trecho = _original(plano, mapa, ini + 1, fim)
        if len(trecho) > 60 and trecho not in saida:
            saida.append(trecho)
    return saida[:2]


def ementas_citadas(norm, plano, mapa, limite=5):
    """Precedentes transcritos no corpo, com a referencia que o proprio ato deu.

    Pista para pesquisa, nao citacao: a transcricao pode estar cortada ou
    adaptada pelo juizo, e a referencia pode estar errada.
    """
    saida = []
    ultimo_fim = 0
    for ref in _REFERENCIA.finditer(norm):
        janela_ini = max(ultimo_fim, ref.start() - 2500)
        abre = None
        for a in _ABRE_CITACAO.finditer(norm, janela_ini, ref.start()):
            abre = a
        e = norm.rfind('ementa', janela_ini, ref.start())
        if abre:
            ini = abre.end()
        elif e >= 0:
            ini = e + len('ementa')
        else:
            continue
        corpo = _original(plano, mapa, ini, ref.start()).strip(' :.-"“”')
        referencia = _original(plano, mapa, ref.start() + 1, ref.end() - 1)
        ultimo_fim = ref.end()
        if len(corpo) < 80:
            continue
        saida.append({'ementa': corpo, 'referencia': referencia})
        if len(saida) >= limite:
            break
    return saida


# ============================================================
# 3. DISPOSITIVO E RESULTADO
# ============================================================

# Redacoes que o `kpi_exito._PADROES_RESULTADO` nao cobre porque o KPI nao le
# tribunal superior: o STJ escreve "negar-lhe provimento", "nao conheco".
_PADROES_EXTRA = [
    (r'\bnegar-lhe provimento', 'inexito'),
    (r'\bnegar provimento', 'inexito'),
    (r'\bdar-lhe (?:parcial )?provimento', 'exito'),
    (r'\bdar (?:parcial )?provimento', 'exito'),
    (r'\bnao conheco d[oa] (?:agravo|recurso)', 'inexito'),
    (r'\bnao conhecer d[oa] (?:agravo|recurso)', 'inexito'),
    (r'\brecurso nao provido', 'inexito'),
    (r'\brecurso provido', 'exito'),
    (r'\bsentenca cassada', 'exito'),
    (r'\bnego-lhe provimento', 'inexito'),
    (r'\bdou-lhe parcial provimento', 'parcial'),
    (r'\bdou-lhe provimento', 'exito'),
    (r'\bjulgo (?:o pedido |os pedidos )?procedentes? em partes?\b', 'parcial'),
    (r'\bprocedentes? em partes? os pedidos', 'parcial'),
    (r'\bnego seguimento', 'inexito'),
    (r'\bnao admito o recurso', 'inexito'),
    (r'\bconcedo (?:o )?efeito (?:ativo|suspensivo)', 'exito'),
    (r'\b(?:rejeito|julgo improcedentes?) (?:os|o) (?:pedidos?|presentes embargos a execucao|'
     r'embargos a execucao)(?! de declaracao)', 'inexito'),
    (r'\bacolho (?:os|o) (?:pedidos?|embargos a execucao)', 'exito'),
]


def ler_resultado(dispositivo_norm, segundo_grau):
    """'exito' | 'parcial' | 'inexito' para quem recorreu/ajuizou, ou None.

    Em ato de tribunal vale o ULTIMO enunciado; em 1o grau, o PRIMEIRO -
    mesma regra do KPI. Sobreposicao: vence o trecho mais longo.
    """
    achados = []
    for rx, _lado, res in kpi_exito._PADROES_RESULTADO:
        for m in re.finditer(rx, dispositivo_norm):
            achados.append((m.start(), m.end(), res))
    for rx, res in _PADROES_EXTRA:
        for m in re.finditer(rx, dispositivo_norm):
            achados.append((m.start(), m.end(), res))
    if not achados:
        return None
    achados.sort(key=lambda a: (a[0], -(a[1] - a[0])))
    filtrados = []
    for a in achados:
        if filtrados and a[0] < filtrados[-1][1]:
            continue
        filtrados.append(a)
    return (filtrados[-1] if segundo_grau else filtrados[0])[2]


_PAPEL_ATIVO_2G = re.compile(
    r'\b(?:agravante|apelante|recorrente|embargante|polo ativo)s?\s*:\s*(.{3,160}?)'
    r'(?=\s+representante|\s+polo passivo|,|\s+cpf|\s+cnpj|\s*advogad|\s+procurador|\s+repr|\s+(?:agravad|apelad|recorrid|embargad)|$)')
_PAPEL_ATIVO_1G = re.compile(
    r'\b(?:autor|autora|requerente|embargante|exequente|impetrante)s?\s*:\s*(.{3,160}?)'
    r'(?=,|\s+cpf|\s+cnpj|\s*advogad|\s+procurador|\s+(?:reu|re|requerid|embargad|executad|impetrad)|$)')


# Parte nao produtora que nao e' banco: no TRF1 o polo ativo e' IBAMA, Uniao, INSS...
_ENTES_PUBLICOS = ('uniao', 'uniao federal', 'fazenda nacional', 'ibama', 'inss', 'incra', 'conab',
                   'instituto nacional', 'instituto brasileiro', 'agencia nacional', 'autarquia')


def _e_instituicao(nome):
    # Com fronteira: "s.a" solto casava dentro de "i. u. h. s.advogado(a)" e o
    # produtor virava banco (0000052-88.2025.8.22.0015).
    n = kpi_exito.normalizar(nome)
    return any(re.search(r'(?<![a-z0-9])' + re.escape(m) + r'(?![a-z0-9])', n) for m in _ENTES_PUBLICOS) or any(re.search(r'(?<![a-z0-9])' + re.escape(m) + r'(?![a-z0-9])', n)
               for m in kpi_exito._MARCAS_INSTITUICAO)


_SO_INICIAIS = re.compile(r'^(?:[a-z]\.\s*-?\.?\s*)+$')


def _so_iniciais(nome):
    """'c. d. c. d. l. a. d. v. d. m. -. c.' - parte com nome mascarado pelo tribunal."""
    return bool(_SO_INICIAIS.match(kpi_exito.normalizar(nome).strip()))


def lado_ativo(norm, item, segundo_grau):
    nome, inst = _lado_ativo(norm, item, segundo_grau)
    if nome and _so_iniciais(re.sub(r'\s*\((?:executado|credor.*)\)$', '', nome)):
        # Iniciais nao dizem se e' banco: "c. d. c. d. l. a..." era cooperativa de
        # credito e virou produtor (0000054-00). Tenta o nome do destinatario.
        ativos = [d.get('nome', '') for d in item.get('destinatarios') or []
                  if d.get('polo') == 'A' and not _so_iniciais(d.get('nome', ''))]
        if len(ativos) == 1:
            return ativos[0], _e_instituicao(ativos[0])
        return nome, None
    return nome, inst


def _lado_ativo(norm, item, segundo_grau):
    """(nome de quem recorreu/ajuizou, e_instituicao) - ou (None, None)."""
    classe = kpi_exito.normalizar(item.get('nomeClasse') or '')
    if not segundo_grau and re.search(r'busca e apreensao|monitoria|reintegracao de posse', classe):
        # O autor e' o credor, e o DJEN costuma publicar o nome dele so com as
        # iniciais ("b. r. b. s."), que nao casam com marca de banco.
        ativos = [d.get('nome', '') for d in item.get('destinatarios') or [] if d.get('polo') == 'A']
        return (ativos[0] if ativos else 'credor (autor)'), True
    if not segundo_grau and re.search(r'^execucao|cumprimento de sentenca', classe):
        # Na execucao, quem pede (excecao, suspensao, impenhorabilidade) e' o
        # executado: "indefiro" e' contra ele, nao contra o banco exequente.
        passivos = [d.get('nome', '') for d in item.get('destinatarios') or [] if d.get('polo') == 'P']
        if passivos:
            inst = {_e_instituicao(n) for n in passivos}
            if len(inst) == 1:
                return passivos[0] + ' (executado)', inst.pop()
        return None, None
    rx = _PAPEL_ATIVO_2G if segundo_grau else _PAPEL_ATIVO_1G
    m = rx.search(norm[:4000])
    if m:
        nome = m.group(1).strip()
        return nome, _e_instituicao(nome)
    if segundo_grau:
        # "...do Agravo de Instrumento interposto pelo Banco do Brasil S.A., ..."
        m = re.search(r'\binterpost[oa]s? (?:pelo|pela|pelos|pelas|por) (.{3,120}?)'
                      r'(?=,| contra| em face| em desfavor| nos autos|\.|$)', norm)
        if m:
            nome = m.group(1).strip()
            return nome, _e_instituicao(nome)
    else:
        ativos = [d.get('nome', '') for d in item.get('destinatarios') or [] if d.get('polo') == 'A']
        if ativos:
            inst = {_e_instituicao(n) for n in ativos}
            if len(inst) == 1:
                return ativos[0], inst.pop()
    return None, None


def favoravel_ao_produtor(resultado, ativo_instituicao):
    if resultado is None or ativo_instituicao is None:
        return 'a conferir'
    if resultado == 'parcial':
        return 'parcial'
    ganhou_ativo = resultado == 'exito'
    return 'favoravel' if ganhou_ativo != ativo_instituicao else 'desfavoravel'


# Tipo do ato, na mesma regua do KPI (kpi_exito.classificar_kpi): KPI 2 = tutela
# de 1o grau, KPI 3 = tutela recursal, KPI 1 = merito. O KPI junta sentenca e
# acordao; aqui eles se separam, e a decisao monocratica do relator que resolve
# o recurso ("nego provimento", "nego seguimento") ganha tipo proprio - pesa
# menos como precedente que o colegiado.
TIPOS = OrderedDict([
    ('liminar', 'Liminar / tutela de 1º grau'),
    ('tutela-recursal', 'Tutela recursal (efeito suspensivo / ativo)'),
    ('sentenca', 'Mérito em sentença'),
    ('acordao', 'Acórdão (colegiado)'),
    ('monocratica', 'Decisão monocrática que resolve o recurso'),
    ('admissibilidade', 'Admissibilidade de REsp / RE'),
    ('outro', 'Outro ato decisório'),
])


_RESOLVE_RECURSO = re.compile(
    r'\bnego seguimento|\bnego(?:-lhe)? provimento|\bdou(?:-lhe)? (?:parcial )?provimento|'
    r'\bnao conheco d[oa] (?:agravo|recurso)|\bnao admito o recurso|\bjulgo prejudicad[oa] o (?:agravo|recurso)')
_TUTELA_RECURSAL = re.compile(r'efeito (?:suspensivo|ativo)|tutela recursal|antecipacao da tutela recursal')


def tipo_de_ato(norm, disp_norm, item, grau, resultado, ementa_propria_existe=False):
    classe = kpi_exito.normalizar(item.get('nomeClasse') or '')
    k = kpi_exito.classificar_kpi(norm, disp_norm, classe)
    motivo = k.get('motivo') or ''
    if motivo.startswith('embargos de declaracao') or \
            re.search(r'embargos de declaracao (?:nao )?(?:providos|acolhidos|rejeitados|conhecidos)',
                      disp_norm[:400]) or \
            (ementa_propria_existe and re.match(r'\s*embargos de declaracao', norm[norm.find('ementa') + 6:][:60])):
        return 'embargos-declaracao'
    if grau != '1o grau' and re.search(
            r'(?:nego seguimento|nao admito|admito|inadmito)[^.]{0,40}recurso(?:s)? (?:especial|extraordinario)',
            disp_norm):
        return 'admissibilidade'
    if grau == 'superior':
        # Monocratica do STJ transcreve o acordao recorrido ("por unanimidade"):
        # la' so e' acordao o que o DJEN rotula assim ou abre com "acordam".
        tipo_doc = kpi_exito.normalizar(item.get('tipoDocumento') or '')
        colegiado = 'acordao' in tipo_doc or bool(re.search(r'\bacordam\b', norm[:1500]))
    elif grau != '1o grau':
        colegiado = ementa_propria_existe or bool(_SINAL_COLEGIADO.search(norm)) or \
            'acordao' in norm[:400]
    if grau != '1o grau':
        if colegiado:
            return 'acordao'
        # "nego seguimento ao agravo... prejudicada a tutela recursal": resolve o
        # recurso, e a tutela so' aparece como prejudicada.
        if _RESOLVE_RECURSO.search(disp_norm):
            return 'monocratica'
        if k.get('kpi') in ('KPI 2', 'KPI 3') or _TUTELA_RECURSAL.search(disp_norm):
            return 'tutela-recursal'
        return 'monocratica' if resultado else 'outro'
    if re.search(r'\bjulgo (?:totalmente |parcialmente )?(?:im)?procedentes?\b|\bart(?:igo)?\.? 487', disp_norm):
        return 'sentenca'
    # Liminar que nao diz "tutela": "defiro o pedido... retirada do nome dos cadastros...
    # ate o final da demanda, sob pena de multa"
    if resultado and re.search(r'ate o (?:final|deslinde|julgamento)|abstenha|suspensao da exigibilidade|'
                               r'suspender a exigibilidade|retirada d[eo] (?:seu )?nome', disp_norm[:700]):
        return 'liminar'
    # Efeito suspensivo aos embargos a execucao (art. 919, § 1o) e' tutela de 1o grau
    if k.get('kpi') == 'KPI 2' or re.search(r'efeito suspensivo', disp_norm[:600]):
        return 'liminar'
    if k.get('kpi') == 'KPI 1' or 'sentenca' in kpi_exito.normalizar(item.get('tipoDocumento') or ''):
        return 'sentenca'
    if re.search(r'\bart(?:igo)?\.? 487', disp_norm) and resultado:
        return 'sentenca'
    return 'outro'


# ============================================================
# 4. METADADOS DE CITACAO
# ============================================================

_RELATOR = re.compile(
    r'\brelator[a]?\s*:\s*((?:des(?:embargador[a]?)?\.?|ministr[oa]|juiz[a]?(?: convocad[oa])?)'
    r'\s+[a-z][a-z .]{4,70}?)(?=\s+(?:data|agravante|apelante|recorrente|advogad|origem|processo|'
    r'distribu|revisor|orgao|interpost|agravad|apelad|recorrid|embarg|impetr|relatorio|gabinete|'
    r'vistos|decisao|acordao|ementa|null|rua|av|avenida|cep|sala|\d)|[,;(]|$)')
_GABINETE = re.compile(r'\bgabinete (?:do |da )?(des(?:embargador[a]?)?\.? [a-z][a-z ]{4,60}?)(?= null|,| -|\s{2}|\s+cep|$)')
_DATA_JULG = re.compile(
    r'data d[eo] julgamento\s*:?\s*(?:sessao[^0-9]{0,40}\d*\s*de\s*)?(\d{2}/\d{2}/\d{4})'
    r'(?:\s*a\s*(\d{2}/\d{2}/\d{4}))?')

_MINUSCULAS = {'de', 'do', 'da', 'dos', 'das', 'e', 'em', 'a', 'o', 'ao', 'por', 'com'}


def titulo(texto):
    palavras = (texto or '').lower().split()
    return ' '.join(p if (i and p in _MINUSCULAS) else p[:1].upper() + p[1:]
                    for i, p in enumerate(palavras))


_GAB_FEDERAL = re.compile(
    r'^\s*Gab\.?\s*\d+\s*-\s*(Desembargadora? Federal|Ju[ií]za? Federal Convocad[oa])\s+(.+)$', re.I)


def magistrado(item, norm, plano, mapa, grau):
    """(nome, origem) - conservador, como no vault: nome errado estraga o perfil.

    Ordem: orgao que se nomeia no DJEN ("Gabinete Des. Raduan Miguel") ->
    relator declarado no CABECALHO -> assinatura no FIM do ato. Nunca o corpo
    inteiro: ali estao os relatores dos precedentes citados.
    """
    # TRF1: "Gab. 15 - DESEMBARGADOR FEDERAL ALEXANDRE VASCONCELOS" (ou juiz convocado)
    m = _GAB_FEDERAL.match(item.get('nomeOrgao') or '')
    if m:
        cargo = 'Desa.' if m.group(1).lower().endswith('a federal') or 'desembargadora' in m.group(1).lower() \
            else ('Juiz(a) conv.' if 'juiz' in m.group(1).lower() else 'Des.')
        return f"{cargo} {vault_obsidian._titulo_nome(m.group(2).strip().lower())}", 'orgao no DJEN'
    nome, origem = vault_obsidian.magistrado_do_orgao(item.get('nomeOrgao') or '')
    if nome:
        cargo = re.match(r'\s*Gabinete\s+(Desa?\.|Desembargadora?)', item.get('nomeOrgao') or '', re.I)
        prefixo = ''
        if cargo:
            prefixo = 'Desa. ' if cargo.group(1).lower().startswith('desa') or \
                cargo.group(1).lower().endswith('dora') else 'Des. '
        return prefixo + vault_obsidian._titulo_nome(nome), 'orgao no DJEN'
    if grau != '1o grau':
        m = _RELATOR.search(norm[:1500])
        if m:
            return titulo(_original(plano, mapa, m.start(1), m.end(1))), 'relator no cabecalho'
    nome, origem = vault_obsidian.extrair_magistrado(plano[-1500:])
    if nome:
        return nome, 'assinatura do ato'
    return None, origem


def data_julgamento(norm):
    m = _DATA_JULG.search(norm[:3000])
    if not m:
        return None
    return f'{m.group(1)} a {m.group(2)}' if m.group(2) else m.group(1)


_CLASSE_RECURSAL = re.compile(r'agravo|apelacao|recurso|embargos infringentes|mandado de seguranca civel')
_SINAL_COLEGIADO = re.compile(r'\bacordam\b|\bpor unanimidade\b|\bpor maioria\b|voto d[oa] relator')


def _grau(item, norm, ementa=None):
    """'superior' | '2o grau' | '1o grau'.

    A classe recursal decide; sem ela, so sinal forte de tribunal no cabecalho.
    `kpi_exito.e_ato_de_segundo_grau` sozinho nao basta aqui: ele procura
    "desembargador" nos primeiros 1.200 caracteres, e sentenca que cita
    precedente logo no inicio virava 2o grau. O inverso tambem existe - o DJEN
    publica acordao com a classe do processo de origem ("Procedimento Comum").
    """
    trib = (item.get('siglaTribunal') or '').upper()
    if trib in ('STJ', 'STF', 'TST'):
        return 'superior'
    classe = kpi_exito.normalizar(item.get('nomeClasse') or '')
    if _CLASSE_RECURSAL.search(classe):
        return '2o grau'
    cabecalho = norm[:1500]
    if ementa and re.search(r'\b(?:apelacao|agravo|recurso)\b', kpi_exito.normalizar(ementa[:400])):
        return '2o grau'
    if 'acordao' in cabecalho[:400] or 'decisao:' in cabecalho or \
            (_SINAL_COLEGIADO.search(norm) and re.search(r'\brelator', cabecalho)) or \
            re.search(r'\bgabinete (?:do |da )?des', cabecalho):
        return '2o grau'
    return '1o grau'


def _data_br(iso):
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return iso or ''


def citacao_sugerida(r):
    """Linha de fonte no padrao do escritorio (sem travessao)."""
    partes = [r['tribunal'], f"{r['classe']} {r['processo']}"]
    if r['relator']:
        partes.append(f"{'Rel.' if r['grau'] != '1o grau' else 'Juízo de'} {r['relator']}")
    if r['data_julgamento']:
        partes.append(('julgado em sessão de ' if ' a ' in r['data_julgamento'] else 'julgado em ')
                      + r['data_julgamento'])
    partes.append(f"DJEN {_data_br(r['data'])}")
    return f"({partes[0]} - " + ', '.join(partes[1:]) + ')'


# ============================================================
# 5. ANALISE DE UM ITEM
# ============================================================

def analisar(item):
    plano = mascarar_documentos(texto_plano(item.get('texto')))
    norm, mapa = normalizar_com_mapa(plano)
    tipo_doc = kpi_exito.normalizar(item.get('tipoDocumento') or '')
    ementa = ementa_propria(norm, plano, mapa)
    if (item.get('siglaTribunal') or '').upper() in ('STJ', 'STF') and \
            'acordao' not in kpi_exito.normalizar(item.get('tipoDocumento') or ''):
        # Decisao monocratica do STJ transcreve a ementa do TJ de origem ("contra acordao
        # do TJSP cuja ementa guarda os seguintes termos"). 537 ementas de TJ entraram no
        # ementario como se fossem do STJ (18/09/2026). La', so o "EMENTA / ACORDAO" e' proprio.
        ementa = None
    grau = _grau(item, norm, ementa)
    segundo = grau != '1o grau'

    disp_norm, origem_disp = kpi_exito.extrair_dispositivo(norm)
    if origem_disp == 'ementa' and not ementa:
        # "Ementa" achada no corpo e' de precedente citado, nao dispositivo deste ato
        disp_norm, origem_disp = norm[-1200:], 'fecho'
    refs = list(_REFERENCIA.finditer(disp_norm))
    if refs and len(disp_norm) - refs[-1].end() > 80:
        # O trecho lido passa por um precedente citado ("... Recurso desprovido. (TJ-RJ -
        # APELACAO ...)") - o resultado do ato e' o que vem depois da referencia
        # (monitoria 0000053-78.2026.8.22.0002 saia com o resultado do TJRJ).
        disp_norm = disp_norm[refs[-1].end():]
    ini_disp = len(norm) - len(disp_norm)
    fim_disp = re.search(r'\b(?:publique-se|intime-se|intimem-se|cumpra-se|arquivem-se|'
                         r'apos o transito)', norm[ini_disp:])
    fim = ini_disp + (fim_disp.start() if fim_disp else min(900, len(disp_norm)))
    corte_ementa = re.search(r'\bementa\b', norm[ini_disp + 10:fim])
    if corte_ementa:
        fim = ini_disp + 10 + corte_ementa.start()
    dispositivo = _original(plano, mapa, ini_disp, min(fim, ini_disp + 900))

    recorridas = [] if ementa else ementas_recorridas(norm, plano, mapa)
    resultado = ler_resultado(disp_norm, segundo)
    if resultado is None and ementa:
        resultado = ler_resultado(kpi_exito.normalizar(ementa)[-600:], True)
    ativo, ativo_inst = lado_ativo(norm, item, segundo)
    tipo = tipo_de_ato(norm, disp_norm, item, grau, resultado, bool(ementa))
    # Gratuidade, custas, honorarios: nao e' precedente de tese (mesma regra do KPI)
    acessorio = kpi_exito.objeto_acessorio(norm, disp_norm)

    r = {
        'id': item.get('id'),
        'data': item.get('data_disponibilizacao'),
        'tribunal': (item.get('siglaTribunal') or '').upper(),
        'orgao': item.get('nomeOrgao') or '',
        'classe': titulo(html.unescape(item.get('nomeClasse') or '')),
        'tipo_documento': item.get('tipoDocumento') or '',
        'processo': item.get('numeroprocessocommascara') or item.get('numero_processo') or '',
        'link': item.get('link') or '',
        'grau': grau,
        'relator': None,
        'magistrado_origem': None,
        'data_julgamento': data_julgamento(norm),
        'tipo': tipo,
        'ementa': re.sub(r'\s+', ' ', ementa) if ementa else None,
        'ementas_recorridas': recorridas,
        'ementas_citadas': ementas_citadas(norm, plano, mapa),
        'dispositivo': dispositivo,
        'origem_dispositivo': origem_disp,
        'resultado': resultado,
        'recorrente_ou_autor': ativo,
        'ativo_e_instituicao': ativo_inst,
        'produtor': favoravel_ao_produtor(resultado, ativo_inst),
        'objeto_acessorio': acessorio,
        'sem_conteudo': bool(acessorio) or _tipo_sem_conteudo(tipo_doc) or
                        tipo == 'embargos-declaracao' or (resultado is None and not ementa),
        '_norm': norm,
    }
    r['relator'], r['magistrado_origem'] = magistrado(item, norm, plano, mapa, grau)
    r['citacao'] = citacao_sugerida(r)
    return r


# ============================================================
# 6. BUSCA
# ============================================================

def termo_mais_seletivo(termos, inicio, fim, tribunal=None):
    """Das frases exigidas, a que o DJEN conta menos vezes.

    A API nao faz E entre frases ("Sumula 298 frustracao de safra" da 0), entao
    so uma vai para a consulta e as outras sao conferidas aqui. Mandar a mais
    rara corta o volume - e o limite por mes deixa de truncar o periodo.
    """
    if len(termos) < 2:
        return termos[0]
    contagens = []
    for t in termos:
        params = {'texto': t, 'dataDisponibilizacaoInicio': str(inicio),
                  'dataDisponibilizacaoFim': str(fim), 'itensPorPagina': 1, 'pagina': 1}
        if tribunal:
            params['siglaTribunal'] = tribunal
        try:
            n = comunica_djen._requisitar(params, exigir_dados=True).get('count') or 0
        except RuntimeError:
            n = 0
        # count 0 aqui e' mais provavel falso-vazio que frase inexistente
        contagens.append((n if n else float('inf'), t))
    return min(contagens)[1]


def janelas_mensais(inicio, fim):
    """[(ini, fim)] em ISO, um por mes civil, cobrindo inicio..fim."""
    a = datetime.strptime(str(inicio), '%Y-%m-%d').date()
    z = datetime.strptime(str(fim), '%Y-%m-%d').date()
    saida = []
    while a <= z:
        prox = date(a.year + (a.month == 12), a.month % 12 + 1, 1)
        saida.append((a.isoformat(), min(z, prox - timedelta(days=1)).isoformat()))
        a = prox
    return list(reversed(saida))


def _chave_dedupe(r):
    proc = ''.join(filter(str.isdigit, r['processo']))
    base = kpi_exito.normalizar(r['ementa'] or r['dispositivo'])[:300]
    return proc, base


def buscar(consulta, tribunais=None, inicio=None, fim=None, tambem=(), excluir=(),
           limite=1000, incluir_trabalhista=False, incluir_sem_conteudo=False, tipos=None,
           log=print):
    """Consulta o DJEN, confere os termos no texto e devolve os julgados analisados.

    tribunais: lista de siglas, ou None/vazio = todos (uma consulta so, com os
    ramos trabalhista/eleitoral/militar descartados localmente).
    """
    consultas = [t.upper() for t in tribunais] if tribunais else [None]
    termo_api = termo_mais_seletivo([consulta] + [t for t in tambem if t], inicio, fim,
                                    consultas[0] if len(consultas) == 1 else None)
    brutos = []
    cortes = []
    for trib in consultas:
        rotulo = trib or 'todos os tribunais'
        log(f'  DJEN: "{termo_api}" em {rotulo}, {inicio} a {fim}')
        # Uma consulta por mes: a API devolve do mais recente para o mais antigo,
        # e com um limite so o periodo inteiro sairia cortado no comeco sem aviso.
        for ini_j, fim_j in janelas_mensais(inicio, fim):
            t0 = time.time()
            try:
                itens = comunica_djen.consultar(sigla_tribunal=trib, data_inicio=ini_j,
                                                data_fim=fim_j, texto=termo_api, limite=limite)
            except RuntimeError as e:
                log(f'    {ini_j[:7]}: AVISO {e} - mes fora desta rodada.')
                cortes.append(f'{rotulo} {ini_j[:7]} (API indisponivel)')
                continue
            cortado = bool(limite and len(itens) >= limite)
            if cortado:
                cortes.append(f'{rotulo} {ini_j[:7]} (limite de {limite})')
            log(f'    {ini_j[:7]}: {len(itens)} publicacao(oes) em {time.time() - t0:.0f}s'
                + (' - LIMITE ATINGIDO, mes incompleto' if cortado else ''))
            brutos.extend(itens)

    obrigatorios = [_padrao_termo(consulta)] + [_padrao_termo(t) for t in tambem if t]
    proibidos = [_padrao_termo(t) for t in excluir if t]

    contagem = {'publicacoes': len(brutos), 'ramo_excluido': 0, 'sem_termo': 0,
                'sem_conteudo': 0, 'duplicado': 0, 'cortes': cortes}
    vistos = {}
    for item in brutos:
        sigla = (item.get('siglaTribunal') or '').upper()
        if not incluir_trabalhista and _RAMOS_EXCLUIDOS.match(sigla):
            contagem['ramo_excluido'] += 1
            continue
        r = analisar(item)
        if not all(p.search(r['_norm']) for p in obrigatorios) or \
                any(p.search(r['_norm']) for p in proibidos):
            contagem['sem_termo'] += 1
            continue
        if r['sem_conteudo'] and not incluir_sem_conteudo:
            contagem['sem_conteudo'] += 1
            continue
        if tipos and r['tipo'] not in tipos:
            contagem['outro_tipo'] = contagem.get('outro_tipo', 0) + 1
            continue
        chave = _chave_dedupe(r)
        atual = vistos.get(chave)
        if atual:
            contagem['duplicado'] += 1
            if len(r['_norm']) <= len(atual['_norm']):
                continue
        vistos[chave] = r

    ordem_tipo = {t: i for i, t in enumerate(list(TIPOS) + ['embargos-declaracao'])}
    ordem_grau = {'superior': 0, '2o grau': 1, '1o grau': 2}
    julgados = sorted(vistos.values(),
                      key=lambda r: (ordem_tipo[r['tipo']], ordem_grau[r['grau']], r['ementa'] is None,
                                     -int((r['data'] or '0').replace('-', '') or 0)))
    for r in julgados:
        r.pop('_norm', None)
    contagem['julgados'] = len(julgados)
    return julgados, contagem


# ============================================================
# 7. SAIDA
# ============================================================

_ROTULO_PRODUTOR = {'favoravel': 'FAVORAVEL ao produtor', 'desfavoravel': 'desfavoravel ao produtor',
                    'parcial': 'parcial', 'a conferir': 'lado a conferir'}


def imprimir(julgados, contagem, maximo=30):
    print(f"\n  {contagem['publicacoes']} publicacoes -> {contagem['julgados']} julgados "
          f"(fora: {contagem['sem_termo']} sem o termo exato, {contagem['sem_conteudo']} despacho/"
          f"sem resultado, {contagem['duplicado']} duplicados, {contagem['ramo_excluido']} "
          f"trabalhista/eleitoral)")
    por_tipo = {}
    for r in julgados:
        por_tipo[r['tipo']] = por_tipo.get(r['tipo'], 0) + 1
    print('  Por tipo: ' + ', '.join(f"{TIPOS.get(t, t)} {n}" for t, n in por_tipo.items()))
    if contagem.get('cortes'):
        print('  ATENCAO, periodo incompleto em: ' + '; '.join(contagem['cortes']))
    por_trib = {}
    for r in julgados:
        por_trib[r['tribunal']] = por_trib.get(r['tribunal'], 0) + 1
    if por_trib:
        print('  Por tribunal: ' + ', '.join(f'{k} {v}' for k, v in
                                             sorted(por_trib.items(), key=lambda kv: -kv[1])))
    tipo_atual = None
    for n, r in enumerate(julgados[:maximo], 1):
        if r['tipo'] != tipo_atual:
            tipo_atual = r['tipo']
            print(f"\n  ---- {TIPOS.get(tipo_atual, tipo_atual).upper()} ----")
        print(f"\n  [{n}] {r['tribunal']} {r['grau']} | {r['classe']} {r['processo']} | "
              f"DJEN {_data_br(r['data'])}")
        print(f"      {r['orgao']}" + (f" | Rel. {r['relator']}" if r['relator'] else ''))
        print(f"      Resultado: {r['resultado'] or '?'} para {r['recorrente_ou_autor'] or '?'} "
              f"-> {_ROTULO_PRODUTOR[r['produtor']]}")
        if r['ementa']:
            print(f"      Ementa: {r['ementa'][:300]}...")
        elif r['ementas_recorridas']:
            print('      (sem ementa propria; transcreve o acordao RECORRIDO - nao citar como '
                  f"{r['tribunal']})")
        print(f"      Dispositivo: {r['dispositivo'][:220]}")
    if len(julgados) > maximo:
        print(f"\n  ... e mais {len(julgados) - maximo}. Use --md para o relatorio completo.")


def gerar_markdown(julgados, contagem, consulta, periodo, tambem=()):
    L = [f'# Jurisprudência no DJEN: "{consulta}"', '']
    filtros = f'Período {periodo}' + (f' · também: {", ".join(tambem)}' if tambem else '')
    L += [f'{filtros} · gerado em {date.today().strftime("%d/%m/%Y")}', '',
          '> **Leitura automática, não é pesquisa conferida.** Toda ementa abaixo tem de ser '
          'conferida no inteiro teor, no site do tribunal de origem, antes de entrar na peça. '
          '"Favorável ao produtor" é inferido de quem recorreu e do verbo do dispositivo.', '',
          f"{contagem['publicacoes']} publicações → **{contagem['julgados']} julgados** "
          f"({contagem['sem_termo']} sem o termo exato, {contagem['sem_conteudo']} despacho ou sem "
          f"resultado, {contagem['duplicado']} duplicados, {contagem['ramo_excluido']} "
          'trabalhista/eleitoral).', '']
    if contagem.get('cortes'):
        L += ['> **Período incompleto** em: ' + '; '.join(contagem['cortes'])
              + '. Rode de novo com busca mais específica (`--tambem`) ou por tribunal.', '']
    rot = {'favoravel': 'Favorável ao produtor', 'desfavoravel': 'Desfavorável ao produtor',
           'parcial': 'Parcial', 'a conferir': 'Lado a conferir'}
    tipo_atual = None
    for n, r in enumerate(julgados, 1):
        if r['tipo'] != tipo_atual:
            tipo_atual = r['tipo']
            qtd = sum(1 for x in julgados if x['tipo'] == tipo_atual)
            L += [f"# {TIPOS.get(tipo_atual, tipo_atual)} ({qtd})", '']
        L += [f"## {n}. {r['tribunal']} · {r['classe']} {r['processo']}", '',
              f"- **Órgão:** {r['orgao']}" + (f" · Rel. {r['relator']}" if r['relator'] else ''),
              f"- **Grau:** {r['grau']} · **Publicado no DJEN:** {_data_br(r['data'])}"
              + (f" · **Julgamento:** {r['data_julgamento']}" if r['data_julgamento'] else ''),
              f"- **Resultado:** {r['resultado'] or 'não identificado'} para "
              f"{r['recorrente_ou_autor'] or 'parte não identificada'} → **{rot[r['produtor']]}**",
              f"- **Publicação:** {r['link']}", '']
        if r['ementa']:
            L += ['**Ementa do próprio julgado** (citação sugerida, conferir inteiro teor):', '',
                  f"> *{r['ementa']}*", '>', f"> ***{r['citacao']}***", '']
        for e in r['ementas_recorridas']:
            L += [f"**Ementa do acórdão recorrido, transcrita pelo {r['tribunal']}** (não citar "
                  f"como {r['tribunal']}; buscar o acórdão de origem):", '', f'> {e[:1500]}', '']
        L += ['**Dispositivo:**', '', f"> {r['dispositivo']}", '']
        for c in r['ementas_citadas']:
            L += [f"**Precedente citado no ato** ({c['referencia']}); pista, conferir na fonte:", '',
                  f"> {c['ementa'][:1200]}", '']
        L.append('---')
        L.append('')
    return '\n'.join(L)


def _slug(texto):
    return re.sub(r'[^a-z0-9]+', '-', kpi_exito.normalizar(texto)).strip('-')[:50]


def salvar(julgados, contagem, consulta, periodo, tambem=(), md=None, js=None):
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    base = os.path.join(PASTA_SAIDA, f'{_slug(consulta)}_{date.today().isoformat()}')
    caminhos = []
    if md is not None:
        caminho = md or base + '.md'
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(gerar_markdown(julgados, contagem, consulta, periodo, tambem))
        caminhos.append(caminho)
    if js is not None:
        caminho = js or base + '.json'
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({'consulta': consulta, 'periodo': periodo, 'contagem': contagem,
                       'julgados': julgados}, f, ensure_ascii=False, indent=1)
        caminhos.append(caminho)
    return caminhos


# ============================================================
# 8. AUTOTESTE (as tres origens de ementa e o lado)
# ============================================================

def autoteste():
    casos = []

    acordao = ('PODER JUDICIÁRIO Tribunal de Justiça do Estado de Rondônia ACÓRDÃO Data de Julgamento: '
               'Sessão Eletrônica n. 430 de 31/08/2026 a 04/09/2026 APELAÇÃO (PJE) APELANTE: FULANO '
               'LEITE DA SILVA ADVOGADO(A): FULANO APELADO(A): BASA - BANCO DA AMAZÔNIA SA RELATOR: '
               'DESEMBARGADOR RADUAN MIGUEL FILHO DATA DA DISTRIBUIÇÃO: 03/07/2026 DECISÃO: “RECURSO '
               'PROVIDO NOS TERMOS DO VOTO DO RELATOR, POR UNANIMIDADE.” Ementa: DIREITO AGRÁRIO. '
               'APELAÇÃO. PRORROGAÇÃO COMPULSÓRIA DE CRÉDITO RURAL. SÚMULA 298 DO STJ. RECURSO PROVIDO. '
               'I. CASO EM EXAME Apelação contra sentença que indeferiu a inicial. IV. DISPOSITIVO E '
               'TESE Recurso provido. Sentença cassada.')
    r = analisar({'texto': acordao, 'siglaTribunal': 'TJRO', 'nomeClasse': 'APELAÇÃO CÍVEL',
                  'data_disponibilizacao': '2026-09-10', 'numeroprocessocommascara': '0000038-73.2026.8.22.0014'})
    casos.append(('acordao TJRO: ementa propria', bool(r['ementa']) and r['ementa'].startswith('DIREITO')))
    casos.append(('acordao TJRO: relator', r['relator'] == 'Desembargador Raduan Miguel Filho'))
    casos.append(('acordao TJRO: julgamento', r['data_julgamento'] == '31/08/2026 a 04/09/2026'))
    casos.append(('acordao TJRO: favoravel ao produtor apelante', r['produtor'] == 'favoravel'))

    stj = ('AREsp 3245761/RS RELATORA : MINISTRA MARIA ISABEL GALLOTTI AGRAVANTE : JOSE '
           'MACHADO DE SOUZA ADVOGADO : EDUARDO AGRAVADO : BANCO DO BRASIL SA DECISÃO Trata-se de '
           'agravo interposto contra decisão que não admitiu recurso especial manejado em face de '
           'acórdão assim ementado (fls. 424-425): APELAÇÃO CÍVEL. CÉDULA DE CRÉDITO RURAL. AÇÃO DE '
           'PRORROGAÇÃO. RECURSO DESPROVIDO. Nas razões do recurso especial, alega violação. '
           'Em face do exposto, conheço do agravo para conhecer em parte do recurso especial e, '
           'nessa extensão, negar-lhe provimento. Intimem-se.')
    r = analisar({'texto': stj, 'siglaTribunal': 'STJ', 'nomeClasse': 'AGRAVO EM RECURSO ESPECIAL'})
    casos.append(('STJ: ementa transcrita NAO e propria', r['ementa'] is None))
    casos.append(('STJ: ementa recorrida identificada', len(r['ementas_recorridas']) == 1))
    casos.append(('STJ: negar-lhe provimento = inexito', r['resultado'] == 'inexito'))
    casos.append(('STJ: desfavoravel ao produtor agravante', r['produtor'] == 'desfavoravel'))

    mono = ('Gabinete Des. Kiyochi Mori null, CEP 76801-330 AGRAVANTE: FULANO DE SOUZA, CPF nº '
            '12345678909 AGRAVADO: BANCO DO BRASIL SA DECISÃO Vistos. Trata-se de agravo. A propósito: '
            'Ementa Agravo de instrumento. Tutela provisória. Prorrogação compulsória de dívida. '
            'Ausência dos requisitos do art. 300. Recurso não provido. (TJ-RO - AGRAVO DE INSTRUMENTO: '
            '08093955720248220000, Relator: Des. Sansão Saldanha, Data de Julgamento: 10/10/2024) '
            'À luz do exposto, nego provimento ao recurso. Publique-se.')
    r = analisar({'texto': mono, 'siglaTribunal': 'TJRO', 'nomeClasse': 'AGRAVO DE INSTRUMENTO'})
    casos.append(('monocratica: ementa citada NAO e propria', r['ementa'] is None))
    casos.append(('monocratica: precedente citado com referencia',
                  len(r['ementas_citadas']) == 1 and 'Sansão' in r['ementas_citadas'][0]['referencia']))
    casos.append(('monocratica: CPF mascarado', '12345678909' not in json.dumps(r, ensure_ascii=False)))
    casos.append(('monocratica: resultado do dispositivo, nao da ementa citada', r['resultado'] == 'inexito'))
    casos.append(('1o grau: REJEITO os pedidos da inicial = inexito',
                  ler_resultado(kpi_exito.normalizar('Isso posto, com fundamento no art. 487, I do CPC, '
                                                     'REJEITO os pedidos formulados na inicial.'), False) == 'inexito'))
    casos.append(('relator: nego seguimento = inexito',
                  ler_resultado('ante o exposto, nego seguimento ao agravo de instrumento', True) == 'inexito'))
    casos.append(('ED rejeitados nao viram resultado de merito',
                  ler_resultado('ante o exposto, nao acolho os embargos de declaracao', True) is None))
    r = analisar({'texto': acordao, 'siglaTribunal': 'TJRO', 'nomeClasse': 'APELAÇÃO CÍVEL'})
    casos.append(('tipo: acordao', r['tipo'] == 'acordao'))
    r = analisar({'texto': mono, 'siglaTribunal': 'TJRO', 'nomeClasse': 'AGRAVO DE INSTRUMENTO'})
    casos.append(('tipo: monocratica que nega provimento', r['tipo'] == 'monocratica'))
    lim = ('AUTOR: JOAO DA SILVA RÉU: BANCO DO BRASIL SA DECISÃO Vistos. Ante o exposto, defiro a tutela '
           'de urgência para suspender a exigibilidade da cédula. Cite-se.')
    r = analisar({'texto': lim, 'siglaTribunal': 'TJRO', 'nomeClasse': 'PROCEDIMENTO COMUM CÍVEL',
                  'tipoDocumento': 'Decisão'})
    casos.append(('tipo: liminar de 1o grau, favoravel ao autor produtor',
                  r['tipo'] == 'liminar' and r['produtor'] == 'favoravel'))
    ts = ('Gabinete Des. Fulano AGRAVANTE: MARIA SOUZA AGRAVADO: SICOOB DECISÃO Vistos. Ante o exposto, '
          'indefiro o pedido de efeito suspensivo. Intime-se.')
    r = analisar({'texto': ts, 'siglaTribunal': 'TJRO', 'nomeClasse': 'AGRAVO DE INSTRUMENTO'})
    casos.append(('tipo: tutela recursal', r['tipo'] == 'tutela-recursal' and r['produtor'] == 'desfavoravel'))
    casos.append(('sentenca: REJEITO os pedidos = sentenca',
                  analisar({'texto': 'EMBARGANTE: JOSE EMBARGADO: BANCO X SENTENÇA Isso posto, com fundamento '
                            'no art. 487, I do CPC, REJEITO os pedidos formulados na inicial.',
                            'siglaTribunal': 'TJRO', 'nomeClasse': 'EMBARGOS À EXECUÇÃO',
                            'tipoDocumento': 'Sentença'})['tipo'] == 'sentenca'))
    casos.append(('instituicao com fronteira: "s.advogado" nao e banco',
                  not _e_instituicao('i. u. h. s.advogado(a): fabio') and _e_instituicao('Banco X S.A.')))
    r = analisar({'texto': 'RECORRENTE: JOSE AGRAVADO: BANCO DO BRASIL SA DECISÃO Pelo exposto, nego seguimento '
                           'ao recurso especial, com fundamento no art. 1.030, I, do CPC.',
                  'siglaTribunal': 'TJRO', 'nomeClasse': 'APELAÇÃO CÍVEL'})
    casos.append(('admissibilidade de REsp tem tipo proprio', r['tipo'] == 'admissibilidade'))
    casos.append(('DOU-LHE PROVIMENTO = exito', ler_resultado('conheco do recurso e dou-lhe provimento', True) == 'exito'))
    casos.append(('procedentes em partes = parcial',
                  ler_resultado('julgo procedentes em partes os pedidos formulados', False) == 'parcial'))
    r = analisar({'texto': 'AGRAVANTE: C. D. C. D. L. A. D. V. D. M. AGRAVADO: J. S. DECISÃO Ante o exposto, '
                           'indefiro o pedido de efeito suspensivo. Intime-se.',
                  'siglaTribunal': 'TJRO', 'nomeClasse': 'AGRAVO DE INSTRUMENTO'})
    casos.append(('parte so com iniciais: lado a conferir, nao adivinha', r['produtor'] == 'a conferir'))
    casos.append(('STJ "DESPACHO / DECISAO" nao e despacho', not _tipo_sem_conteudo('despacho / decisao')
                  and _tipo_sem_conteudo('despacho') and _tipo_sem_conteudo('ata de distribuicao')))
    r = analisar({'texto': 'AREsp 1/RO AGRAVANTE : JOSE AGRAVADO : BANCO DO BRASIL SA DECISÃO Trata-se de agravo contra '
                           'acórdão assim ementado: APELAÇÃO. CRÉDITO RURAL. RECURSO DESPROVIDO POR UNANIMIDADE. '
                           'Nas razões, alega violação. Ante o exposto, conheço do agravo para negar provimento ao recurso especial.',
                  'siglaTribunal': 'STJ', 'nomeClasse': 'AGRAVO EM RECURSO ESPECIAL', 'tipoDocumento': 'DESPACHO / DECISÃO'})
    casos.append(('STJ: monocratica que transcreve "por unanimidade" nao e acordao', r['tipo'] == 'monocratica'))
    r = analisar({'texto': 'CLASSE: AGRAVO DE INSTRUMENTO (202) POLO ATIVO: BANCO DO BRASIL SA REPRESENTANTE(S) POLO ATIVO: '
                           'NELSON - MT8656-A POLO PASSIVO:FULANO DE TAL RELATOR(A):ALEXANDRE VASCONCELOS Ante o exposto, '
                           'nego provimento ao agravo de instrumento.',
                  'siglaTribunal': 'TRF1', 'nomeClasse': 'AGRAVO DE INSTRUMENTO'})
    casos.append(('TRF1 "POLO ATIVO:" banco recorrente desprovido = favoravel', r['produtor'] == 'favoravel'))
    casos.append(('ente publico nao e produtor', _e_instituicao('INSTITUTO BRASILEIRO DO MEIO AMBIENTE - IBAMA')))
    r = analisar({'texto': 'AREsp 1/SP DECISÃO Trata-se de agravo contra acórdão do TJSP cuja ementa guarda os '
                           'seguintes termos (fl. 40): Agravo de instrumento. Cédula rural. Recurso desprovido. '
                           'Ante o exposto, conheço do agravo para negar provimento ao recurso especial.',
                  'siglaTribunal': 'STJ', 'nomeClasse': 'AGRAVO EM RECURSO ESPECIAL', 'tipoDocumento': 'DESPACHO / DECISÃO'})
    casos.append(('STJ: ementa do TJ transcrita NUNCA vira ementa do STJ', r['ementa'] is None))
    r = analisar({'texto': 'RELATÓRIO O EXMO. SR. DESEMBARGADOR FEDERAL (RELATOR): Trata-se de embargos de declaração '
                           'opostos pela FAZENDA NACIONAL contra acórdão cuja ementa segue abaixo transcrita: '
                           'PROCESSUAL CIVIL. CÉDULA RURAL. Recurso provido. É o relatório.',
                  'siglaTribunal': 'TRF1', 'nomeClasse': 'APELAÇÃO CÍVEL', 'tipoDocumento': 'Acórdão'})
    casos.append(('TRF1: ementa do acordao embargado nao e propria do ED', r['ementa'] is None))
    casos.append(('frase com espaco flexivel', bool(_padrao_termo('Súmula 298').search('a sumula  298 do stj'))))

    falhas = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  [{'ok' if ok else 'FALHOU'}] {n}")
    print(f'\n  {len(casos) - len(falhas)}/{len(casos)} casos')
    return not falhas


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    if '--autoteste' in sys.argv:
        sys.exit(0 if autoteste() else 1)
    print('Use: python OPERACIONAL/main.py jurisprudencia "termo"  |  --autoteste')
