# -*- coding: utf-8 -*-
"""
O que a intimacao pede DE NOS — criterios da rotina de intimacoes (POP-CJ-003)
===============================================================================

Nasceu da conferencia das controllers (planilha CONFERENCIA DA ROTINA DE
INTIMACOES, rodadas de 10 a 17/09/2026). Os tres erros que mais apareceram:

1. **Ato sem providencia nossa recebia o pacote inteiro** (analise, peca, coleta,
   pasta e protocolo): remessa dos autos ao tribunal, migracao de sistema,
   Sisbajud deferido a nosso pedido, prazo dado a parte contraria. As controllers
   marcaram "Sem necessidade de providencia" em todos.
2. **Decisao sem prazo no texto ganhava 15 dias** (o do recurso principal). O
   POP-CJ-003-A manda montar primeiro os embargos de declaracao, que vencem em
   5 dias uteis — o marco tem que ser o dos ED.
3. **ED ganhava tarefa do setor de provas.** Embargos de declaracao nao juntam
   documento.

E as regras de 2o grau da Dra. Juliana (21/09/2026):

- **Apelacao distribuida no 2o grau:** a controller agenda despacho com o
  relator; e, 1 dia util depois da distribuicao, o advogado analisa, de forma
  justificada, se a sustentacao oral sera presencial (e' o que alimenta a
  cotacao de viagem).
- **Inclusao em pauta:** despacho com os vogais + memoriais, avaliando se vale
  novo despacho com o relator.

Tudo aqui e' leitura de texto — indicio, nao conclusao. O que a rotina nao
consegue fechar continua subindo como pendencia para a controller.
"""
import re
import unicodedata
from datetime import date

import prazos


def _norm(texto):
    t = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode().lower()
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', t)


# ------------------------------------------------------------------
# De que lado estamos
# ------------------------------------------------------------------
PAPEIS = {
    'ativo': ('exequente', 'autora', 'autor', 'requerente', 'embargante', 'agravante',
              'apelante', 'impetrante', 'reclamante', 'recorrente'),
    'passivo': ('executada', 'executado', 'requerida', 'requerido', 'embargada', 'embargado',
                'agravada', 'agravado', 'apelada', 'apelado', 'impetrado', 'reclamada',
                'reclamado', 'recorrida', 'recorrido', 'reu', 're'),
}
_PAPEL_RE = '|'.join(sorted({p for v in PAPEIS.values() for p in v}, key=len, reverse=True))
# Comando dirigido a uma parte. So conta com verbo de ordem: o cabecalho do ato
# ("ADVOGADO DO EMBARGADO: ...", "EXEQUENTE: ...") nao e' ordem, e le-lo como tal
# fazia a rotina achar que o banco estava sendo intimado em todo despacho.
_P = r'(?:a |o |as |os )?(?:parte |partes )?(?:ora )?(' + _PAPEL_RE + r'|partes|advogad[oa]|patrono|procurador)s?\b'
_COMANDO = re.compile(
    r'(?:intime-?se|intimem-?se|cite-?se|diga|digam|manifeste-?se|vistas? (?:a|ao|as|aos)|'
    r'intimad[ao]s?|manifestacao d[oa])\s+' + _P +
    r'|\b(?:ao|aos|as|a)\s+(?:parte )?(' + _PAPEL_RE + r')s?\s+para\b'
    r'|fica(?:m)?\s+(?:a |o )?(?:parte )?(' + _PAPEL_RE + r')s?\s+intimad')


def papel_do_lado(papel):
    if papel in ('partes', 'advogado', 'advogada', 'patrono', 'procurador'):
        return 'nosso'
    for lado, papeis in PAPEIS.items():
        if papel in papeis:
            return lado
    return None


def papeis_comandados(texto_norm):
    """Papeis processuais a quem o fecho do ato da uma ordem."""
    fecho = texto_norm[-1500:]
    return {next(g for g in m.groups() if g) for m in _COMANDO.finditer(fecho)}


# ------------------------------------------------------------------
# Ato sem providencia nossa
# ------------------------------------------------------------------
# Sinal de que houve decisao contra nos: aqui nunca se dispensa a analise.
_DESFAVORAVEL = re.compile(
    r'\bindefiro\b|\bindeferid[ao]\b|nego provimento|negou provimento|nao conhec|'
    r'\brejeito\b|\brejeitad[ao]s?\b|improcedente|\bjulgo\b|extingo|extint[ao]|'
    r'revogo|\bcondeno\b|mantenho a decisao|desprovid')

# Ato puramente burocratico: nem analise precisa (as controllers marcaram
# "Nao" ate na analise da remessa ao STJ e da migracao de sistema).
_BUROCRATICO = (
    'subam os autos', 'remetam-se os autos', 'remessa dos autos',
    'publicacao automatica referente a migracao',
)
# Ato de andamento sem ordem para nos: sem peca nem protocolo, mas o advogado
# ainda passa o olho (Sisbajud deferido, "a CPE para que prossiga").
_ANDAMENTO = (
    'a cpe para que prossiga', 'prossiga com o feito', 'aguarde-se',
    'permanecam em cartorio', 'arquivem-se', 'arquive-se',
    'determinei a realizacao de pesquisas', 'repeticao programada',
    'retornem conclusos', 'tornem os autos conclusos', 'venham conclusos',
)


def sem_providencia_nossa(item, polo_nosso=None):
    """Classifica o que a intimacao pede do escritorio.

    Devolve (nivel, motivo):
      None           -> segue o fluxo normal (analise + peca + protocolo);
      'burocratico'  -> nenhuma tarefa, so relatorio;
      'so_analise'   -> so a analise do advogado, sem peca nem protocolo.

    Conservador de proposito: sentenca, sinal de decisao desfavoravel ou ordem
    dirigida ao nosso lado (ou as duas partes) devolvem None.
    """
    t = _norm(item.get('trecho_integral') or item.get('trecho') or '')
    if not t or item.get('tipo_ato') == 'sentenca':
        return None, ''
    fecho = t[-1500:]
    if any(p in fecho for p in _BUROCRATICO):
        achado = next(p for p in _BUROCRATICO if p in fecho)
        return 'burocratico', f'ato burocratico ("{achado}") — so relatorio'
    if _DESFAVORAVEL.search(t[-2500:]):
        return None, ''

    comandados = papeis_comandados(t)
    lados = {papel_do_lado(p) for p in comandados} - {None}
    if 'nosso' in lados:
        return None, ''
    if polo_nosso in ('ativo', 'passivo') and lados:
        if polo_nosso in lados:
            return None, ''
        return 'so_analise', ('ordem dirigida so a parte contraria (' + ', '.join(sorted(comandados)) +
                              f'; o escritorio esta no polo {polo_nosso})')
    if not comandados and not item.get('prazo_dias_extraido') and any(p in fecho for p in _ANDAMENTO):
        achado = next(p for p in _ANDAMENTO if p in fecho)
        return 'so_analise', f'ato de andamento sem ordem para nos ("{achado}")'
    return None, ''


# ------------------------------------------------------------------
# 2o grau: distribuicao e pauta
# ------------------------------------------------------------------
_DISTRIBUICAO = re.compile(
    r'(?:foi|processo|autos?)\s+(?:re)?distribuid[oa]|distribuid[oa] (?:automaticamente|por '
    r'(?:sorteio|prevencao|dependencia))|ata de distribuicao|certidao de (?:re)?distribuicao')


def classe_recursal(classe):
    c = _norm(classe)
    if 'embargos de declara' in c:
        return None
    if 'efeito suspensivo' in c:
        return 'pedido_efeito_suspensivo'
    if 'apela' in c:
        return 'apelacao'
    if 'agravo interno' in c:
        return 'agravo_interno'
    if 'agravo de instrumento' in c:
        return 'agravo_instrumento'
    return None


def distribuicao_segundo_grau(item, classe):
    """Classe recursal ('apelacao', 'agravo_instrumento'...) quando a publicacao
    e' a distribuicao do recurso no 2o grau; None caso contrario."""
    cr = classe_recursal(classe)
    if not cr:
        return None
    t = _norm(item.get('trecho_integral') or item.get('trecho') or '')
    # so a certidao/ato de distribuicao; decisao que cita "distribuido" no corpo nao conta
    if len(t) > 2500 or not _DISTRIBUICAO.search(t):
        return None
    return cr


_PAUTA = re.compile(
    r'incluid[oa]s? (?:em|na) pauta|inclusao (?:em|na) pauta|intimacao (?:da|de) pauta|'
    r'pauta de julgamentos?|edital-? ?pauta|julgamento designado para a sessao|'
    r'incluido na sessao de julgamento|pe[cç]o (?:dia|inclusao em pauta)|inclua-?se em pauta')

_MESES = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6,
          'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12}


def data_sessao(texto_norm):
    """Primeira data depois da mencao a pauta/sessao (dd/mm/aaaa ou '29 de julho de 2026')."""
    m = _PAUTA.search(texto_norm) or re.search(r'sessao', texto_norm)
    trecho = texto_norm[m.start():] if m else texto_norm
    d = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', trecho)
    e = re.search(r'(\d{1,2}) de (' + '|'.join(_MESES) + r') de (\d{4})', trecho)
    cands = []
    if d:
        cands.append((d.start(), date(int(d.group(3)), int(d.group(2)), int(d.group(1)))))
    if e:
        cands.append((e.start(), date(int(e.group(3)), _MESES[e.group(2)], int(e.group(1)))))
    return min(cands)[1] if cands else None


def inclusao_em_pauta(item, classe):
    """(classe_recursal, data_da_sessao|None) quando a publicacao inclui o recurso
    em pauta; None caso contrario. Acordao que menciona a sessao em que foi
    julgado NAO e' pauta."""
    cr = classe_recursal(classe)
    if cr not in ('apelacao', 'agravo_instrumento', 'agravo_interno'):
        return None
    t = _norm(item.get('trecho_integral') or item.get('trecho') or '')
    if not _PAUTA.search(t):
        return None
    inicio = t[:600]
    if 'acordao' in inicio or 'acordam' in t or item.get('tipo_ato') == 'sentenca':
        return None
    return cr, data_sessao(t)


if __name__ == '__main__':
    casos = [
        ({'trecho_integral': 'Certifico que o Processo nº 1 – Classe: APELAÇÃO CÍVEL – foi distribuído '
                             'automaticamente no sistema PJE ao Gabinete 1'}, 'APELAÇÃO CÍVEL', 'dist'),
        ({'trecho_integral': 'Intimação referente ao movimento (seq. 25) INCLUÍDO EM PAUTA PARA SESSÃO '
                             'VIRTUAL DE 24/08/2026 00:00 ATÉ 28/08/2026'}, 'AGRAVO DE INSTRUMENTO', 'pauta'),
        ({'trecho_integral': 'INTIMAÇÃO DE PAUTA DE JULGAMENTO Segunda Câmara Julgamento designado para a '
                             'Sessão Ordinária que será realizada entre 29 de Julho de 2026 a 31'},
         'AGRAVO DE INSTRUMENTO', 'pauta'),
        ({'trecho_integral': 'ACÓRDÃO Data de Julgamento: Sessão Presencial n. 1021 de 29/07/2026 '
                             'acordam os desembargadores'}, 'APELAÇÃO CÍVEL', 'nada'),
    ]
    ok = 0
    for it, classe, esperado in casos:
        d = distribuicao_segundo_grau(it, classe)
        p = inclusao_em_pauta(it, classe)
        obtido = 'dist' if d else ('pauta' if p else 'nada')
        ok += obtido == esperado
        print(obtido == esperado and 'ok ' or 'ERR', esperado, obtido, p)
    s1 = sem_providencia_nossa({'tipo_ato': 'decisao', 'trecho_integral':
         'antes de juntados os espelhos, intime-se a parte exequente para ofertar manifestação em 5 dias. '
         'Somente então, tornem os autos conclusos'}, 'passivo')
    s2 = sem_providencia_nossa({'tipo_ato': 'decisao', 'trecho_integral':
         'Subam os autos ao Tribunal competente para o processamento do agravo. Cumpra-se.'})
    s3 = sem_providencia_nossa({'tipo_ato': 'decisao', 'trecho_integral':
         'Diante do exposto, nego provimento ao agravo. Int.'})
    s4 = sem_providencia_nossa({'tipo_ato': 'intimacao_com_prazo', 'trecho_integral':
         'Fica a parte REQUERENTE intimada para, no prazo de 15 dias, manifestar-se'}, 'ativo')
    s5 = sem_providencia_nossa({'tipo_ato': 'decisao', 'trecho_integral':
         'ADVOGADO DO EMBARGADO: BRADESCO DESPACHO o processo podera continuar. A CPE para que prossiga com o feito.'})
    for nome, s, esp in (('contraria', s1, 'so_analise'), ('burocratico', s2, 'burocratico'),
                         ('desfavoravel', s3, None), ('ordem a nos', s4, None), ('cabecalho', s5, 'so_analise')):
        ok += s[0] == esp
        print(s[0] == esp and 'ok ' or 'ERR', nome, s)
    print(f'{ok}/9')
