# -*- coding: utf-8 -*-
"""
Prazos da Controladoria — D-5, D-3 e prazo fatal
=================================================

Regra da Dra. Juliana (10/09/2026), POP-CJ-003:

    INTIMACAO (dia 0)
       |
       +-- advogado confecciona a peca ............ vence D-5
       +-- setor de provas monta a pasta no Zeus .. vence D-5
       |
      D-5   peca pronta E pasta pronta
       |
      D-3   CONTROLADORIA PROTOCOLA (exclusivo dela)
       |
      PRAZO FATAL

D-5 e D-3 sao **dias uteis contados de tras para frente a partir do prazo fatal**
(confirmado pela Dra. Juliana em 10/09/2026). D-5 fica, portanto, 2 dias uteis
antes de D-3 — o "48h antes" do POP.

**Prazo curto** (embargos de declaracao, 5 dias uteis, e afins): D-5 e D-3 cairiam
no passado. A regra do escritorio e' que **a elaboracao fica para o mesmo dia, sem
prejuizo de D-5 e D-3** — entao os marcos sao trazidos para hoje e o item e'
marcado `prazo_curto`, para a controller ver que nasceu comprimido.

Todo calculo aqui e' PRELIMINAR: a lista de feriados cobre o que e' previsivel
(nacionais, estaduais de RO, municipais de Porto Velho e o recesso do art. 220),
mas **nao** conhece portaria de suspensao de expediente do TJRO. Quem confere
antes de protocolar e' a controladoria — a saida sempre diz isso.
"""
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

try:
    import equipe
except ImportError:
    equipe = None


# ============================================================
# FERIADOS
# ============================================================

def _pascoa(ano):
    """Domingo de Pascoa (algoritmo de Meeus/Butcher) - base dos feriados moveis."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


def feriados(ano):
    """Feriados sem expediente forense em Porto Velho/RO, por ano.

    Nacionais + Rondonia (4/1, criacao do Estado) + Porto Velho (2/10,
    aniversario da cidade; 8/12, padroeira). Carnaval e sexta-feira santa
    entram porque o Judiciario nao funciona - segunda e terca de carnaval
    inclusive.
    """
    p = _pascoa(ano)
    fixos = [
        date(ano, 1, 1),    # Confraternizacao Universal
        date(ano, 1, 4),    # Criacao do Estado de Rondonia
        date(ano, 4, 21),   # Tiradentes
        date(ano, 5, 1),    # Dia do Trabalho
        date(ano, 9, 7),    # Independencia
        date(ano, 10, 2),   # Aniversario de Porto Velho
        date(ano, 10, 12),  # Nossa Senhora Aparecida
        date(ano, 11, 2),   # Finados
        date(ano, 11, 15),  # Proclamacao da Republica
        date(ano, 11, 20),  # Consciencia Negra (feriado nacional desde 2024)
        date(ano, 12, 8),   # Nossa Senhora da Conceicao (padroeira de Porto Velho)
        date(ano, 12, 25),  # Natal
    ]
    moveis = [
        p - timedelta(days=48),  # segunda de carnaval
        p - timedelta(days=47),  # terca de carnaval
        p - timedelta(days=46),  # quarta de cinzas (expediente so a tarde; tratado como nao util)
        p - timedelta(days=2),   # sexta-feira santa
        p + timedelta(days=60),  # Corpus Christi
    ]
    extras = []
    for d in (getattr(equipe, 'FERIADOS_EXTRA', None) or []) if equipe else []:
        try:
            extras.append(datetime.strptime(str(d)[:10], '%Y-%m-%d').date())
        except ValueError:
            continue
    return set(fixos + moveis + extras)


def em_recesso(d):
    """Recesso forense: 20/12 a 20/01 (art. 220 do CPC suspende os prazos)."""
    return (d.month == 12 and d.day >= 20) or (d.month == 1 and d.day <= 20)


def e_dia_util(d):
    """Dia util forense: nao e' fim de semana, feriado nem recesso."""
    if isinstance(d, datetime):
        d = d.date()
    if d.weekday() >= 5:
        return False
    if em_recesso(d):
        return False
    return d not in feriados(d.year)


def proximo_dia_util(d):
    while not e_dia_util(d):
        d += timedelta(days=1)
    return d


def somar_dias_uteis(d, n):
    """n dias uteis PARA FRENTE (contagem do art. 219: so dias uteis)."""
    for _ in range(n):
        d += timedelta(days=1)
        while not e_dia_util(d):
            d += timedelta(days=1)
    return d


def subtrair_dias_uteis(d, n):
    """n dias uteis PARA TRAS - e' assim que D-5 e D-3 saem do prazo fatal."""
    for _ in range(n):
        d -= timedelta(days=1)
        while not e_dia_util(d):
            d -= timedelta(days=1)
    return d


# ============================================================
# PRAZO FATAL E MARCOS D-5 / D-3
# ============================================================

def _para_date(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor)[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def prazo_fatal(data_disponibilizacao, dias):
    """Prazo fatal a partir da disponibilizacao no DJEN.

    art. 224, §3o: a publicacao e' o 1o dia util seguinte a disponibilizacao.
    art. 224, caput + 219: a contagem comeca no 1o dia util seguinte a
    publicacao e corre em dias uteis.
    """
    disp = _para_date(data_disponibilizacao)
    if not disp or not dias:
        return None
    publicacao = proximo_dia_util(disp + timedelta(days=1))
    return somar_dias_uteis(publicacao, int(dias))


def marcos(fatal, hoje=None):
    """D-5 e D-3 a partir do prazo fatal, em dias uteis para tras.

    Devolve dict com:
        fatal, d5, d3            (date)
        prazo_curto              (bool) - o calculo caiu no passado e foi trazido para hoje
        dias_uteis_ate_o_fatal   (int)
        observacao               (str)  - o que a controller precisa saber
    """
    fatal = _para_date(fatal)
    if not fatal:
        return None
    hoje = _para_date(hoje) or date.today()

    d3 = subtrair_dias_uteis(fatal, 3)
    d5 = subtrair_dias_uteis(fatal, 5)

    prazo_curto = d5 < hoje or d3 < hoje
    obs = ''
    if prazo_curto:
        # Regra da Dra. Juliana: em prazo curto (ED e afins) a elaboracao fica
        # para o mesmo dia, sem prejuizo de D-5 e D-3 - os marcos vem para hoje
        # em vez de nascerem vencidos.
        d5 = max(d5, hoje)
        d3 = max(d3, hoje)
        if d5 > d3:
            d5 = d3
        obs = ('PRAZO CURTO: D-5/D-3 nao cabem entre hoje e o fatal — '
               'elaboracao no MESMO DIA, sem prejuizo de D-5 e D-3.')

    # quantos dias uteis restam ate o fatal (util para priorizar)
    restantes, cursor = 0, hoje
    while cursor < fatal:
        cursor += timedelta(days=1)
        if e_dia_util(cursor):
            restantes += 1

    return {
        'fatal': fatal,
        'd5': d5,
        'd3': d3,
        'prazo_curto': prazo_curto,
        'dias_uteis_ate_o_fatal': restantes,
        'observacao': obs,
    }


def calcular(data_disponibilizacao, dias_prazo, hoje=None):
    """Atalho: da disponibilizacao ao pacote completo de marcos."""
    fatal = prazo_fatal(data_disponibilizacao, dias_prazo)
    if not fatal:
        return None
    return marcos(fatal, hoje=hoje)


def iso(d):
    return d.strftime('%Y-%m-%d') if d else None


def descrever(m):
    """Uma linha para o relatorio da controladoria."""
    if not m:
        return 'prazo nao calculado (intimacao sem prazo explicito)'
    txt = (f"D-5 {iso(m['d5'])} · D-3 {iso(m['d3'])} · FATAL {iso(m['fatal'])} "
           f"({m['dias_uteis_ate_o_fatal']} dias uteis) — preliminar, conferir "
           f"suspensao de expediente")
    if m['prazo_curto']:
        txt += f" | {m['observacao']}"
    return txt
