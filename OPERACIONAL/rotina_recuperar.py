# -*- coding: utf-8 -*-
"""
Rodadas perdidas da rotina de intimacoes — recuperacao automatica
==================================================================

Problema real (22/09/2026): a rodada das 08:00 do Mac nao rodou por dias e
ninguem percebeu — o launchd nao repoe rodada perdida (`StartCalendarInterval`)
e, no Mac da Dra. Juliana, o macOS ainda bloqueia o agente por TCC (o projeto
esta em ~/Documents). Resultado: a planilha de conferencia ficou parada e a de
despachos tambem.

Este modulo guarda a **ultima rodada publicada** em
`_trabalho/logs/ultima_rodada_intimacoes.txt` e, na proxima vez que rodar (na
hora certa ou a mao), repoe **cada dia util que faltou**, um por vez, com a
data daquele dia — nao adianta varrer tudo numa rodada so, porque o D-5/D-3 e
a data em que a tarefa nasce sao contados a partir do dia da publicacao.

Somente leitura no ADVBOX (simulacao); a unica escrita e' a planilha de
conferencia. Uso:

    python OPERACIONAL/rotina_recuperar.py            # repoe o que faltou + hoje
    python OPERACIONAL/rotina_recuperar.py --ate 2026-09-22 --limite 10
"""
import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

try:                                     # o .env e' carregado pelo main.py; este
    from dotenv import load_dotenv        # modulo roda direto pelo agendamento e
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
except ImportError:                       # precisa carregar por conta propria
    pass

import prazos
import rotina_diaria

ESTADO = os.path.join(os.path.dirname(__file__), '..', '_trabalho', 'logs',
                      'ultima_rodada_intimacoes.txt')
# Teto de dias repostos numa chamada: cada dia e' uma varredura no DJEN + ADVBOX
# (rate limit de 30 GET/min). Faltando mais que isso, a rodada seguinte continua.
LIMITE_PADRAO = 7


def ultima_rodada():
    try:
        with open(ESTADO) as fh:
            return prazos._para_date(fh.read().strip())
    except (OSError, ValueError):
        return None


def registrar(dia):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    with open(ESTADO, 'w') as fh:
        fh.write(prazos.iso(dia))


def dias_a_repor(ate, limite=LIMITE_PADRAO):
    """Dias uteis sem rodada publicada, do mais antigo para o mais novo."""
    ate = prazos._para_date(ate) or date.today()
    ultima = ultima_rodada()
    if not ultima:
        return [ate] if prazos.e_dia_util(ate) else []
    dias, d = [], ultima + timedelta(days=1)
    while d <= ate:
        if prazos.e_dia_util(d):
            dias.append(d)
        d += timedelta(days=1)
    return dias[-limite:] if limite else dias


def rodar(ate=None, limite=LIMITE_PADRAO, publicar=True):
    resultados = []
    for dia in dias_a_repor(ate, limite):
        res = rotina_diaria.rodar(dias=1, gravar=False, hoje=prazos.iso(dia))  # SIMULACAO
        linha = {'dia': prazos.iso(dia), 'itens': len(res['planos']),
                 'tarefas': sum(len(p['tarefas']) for p in res['planos']),
                 'falhas_djen': res['falhas_djen']}
        if publicar:
            try:
                import planilha_conferencia
                _, _, qa, qi = planilha_conferencia.publicar(res)
                linha['publicado'] = f'{qi} intimacao(oes), {qa} agendamento(s)'
            except Exception as e:                      # planilha fora do ar nao
                linha['publicado'] = f'ERRO: {e}'       # derruba a rodada
        # Dia com falha no DJEN nao e' marcado como feito: a API alterna
        # falso-vazio, e gravar o marco esconderia a intimacao que nao veio.
        if not res['falhas_djen']:
            registrar(dia)
        resultados.append(linha)
    return resultados


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Repoe as rodadas perdidas da rotina de intimacoes')
    p.add_argument('--ate', help='Ultimo dia a repor (AAAA-MM-DD); default: hoje')
    p.add_argument('--limite', type=int, default=LIMITE_PADRAO)
    p.add_argument('--sem-planilha', action='store_true')
    a = p.parse_args()
    ultima = ultima_rodada()
    print(f"  Ultima rodada publicada: {prazos.iso(ultima) if ultima else '(nenhuma)'}")
    linhas = rodar(a.ate, a.limite, publicar=not a.sem_planilha)
    if not linhas:
        print('  Nada a repor — a rotina esta em dia.')
    for l in linhas:
        aviso = f" | DJEN falhou: {'; '.join(l['falhas_djen'])}" if l['falhas_djen'] else ''
        print(f"  {l['dia']}: {l['itens']} publicacao(oes), {l['tarefas']} tarefa(s) — "
              f"{l.get('publicado', 'sem planilha')}{aviso}")
