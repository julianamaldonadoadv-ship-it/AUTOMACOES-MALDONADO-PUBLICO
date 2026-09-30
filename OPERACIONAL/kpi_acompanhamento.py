# -*- coding: utf-8 -*-
"""
Acompanhamento de casos por semana - formato da planilha da GJ
==============================================================

A Dra. Juliana acompanha a competencia na planilha "Acompanhamento_Casos_Maldonado_<Mes>"
(15/09/2026: "eu acho bacana porque esta por semana e ja tem o diagnostico da
decisao"). Este modulo gera a competencia nesse formato:

  Semana DD.MM-DD.MM      uma aba por semana util, uma linha por decisao, com as
                          colunas da GJ (Processo, Cliente, Advogado Responsavel,
                          Categoria, Parte Adversa / Orgao, Situacao Processual e
                          Fundamentos, Diagnostico, Despacho, Estrategia, Probabilidade)
                          + as colunas do KPI (carteira, KPI, classificacao, peso,
                          contribuicao, publicacao, link).
  Taxa Exito Rural <Mes>  blocos por KPI, subtotais, nao contabilizados, taxa geral,
                          taxa POR SEMANA e POR ADVOGADO, notas - layout da aba de agosto.
  Carteira Diversa <Mes>  a mesma estrutura, separada (as carteiras nunca se somam).

O diagnostico nao sai de regex: e escrito lendo o ato inteiro e fica em
`_trabalho/kpi_diagnosticos_AAAA-MM.json` (dado de cliente, gitignored). Decisao
que entra no KPI e ainda nao tem diagnostico sai com "A elaborar" - aparece, nao some.

Os numeros do KPI (KPI, resultado, peso, carteira) vem da apuracao
(kpi_exito + DECISOES_GJ), nunca do arquivo de diagnostico. Atribuicao por advogado:
a quem atuou no ato (regra da GJ, 15/09/2026), nao ao responsavel atual do ADVBOX -
`advogado_kpi` no diagnostico; vazio sobe como "A confirmar".
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

import kpi_exito
import prazos

MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto',
         'Setembro', 'Outubro', 'Novembro', 'Dezembro']
MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

# Carteira logo depois da Categoria: a GJ quer ver rural x diversa na linha (15/09/2026).
CAB_SEMANA = ['Processo', 'Cliente', 'Advogado Responsável', 'Categoria', 'Carteira', 'Parte Adversa / Órgão',
              'Situação Processual e Fundamentos da Decisão', 'Diagnóstico (Leitura Estratégica)',
              'Despacho', 'Estratégia / Próximo Passo', 'Probabilidade',
              'Pontuação (proposta)', 'Rubrica aplicada',
              'KPI', 'Classificação', 'Peso', 'Contribuição', 'Publicação (DJEN)', 'Link']
LARGURAS = [153, 181, 125, 111, 90, 314, 454, 314, 279, 279, 139, 95, 300, 60, 130, 55, 85, 95, 120]
COL_CLASSIF = CAB_SEMANA.index('Classificação')
CARTEIRA_ROTULO = {'rural': 'Rural', 'diversa': 'Diversa'}

ROTULO = {'KPI 1': 'KPI 1 — Mérito (peso 1,0 cada)', 'KPI 2': 'KPI 2 — Tutela 1º Grau (peso 0,4 cada)',
          'KPI 3': 'KPI 3 — Tutela Recursal (peso 0,5 cada)'}
CLASSIF = {'exito': 'Êxito', 'parcial': 'Parcial', 'inexito': 'Inêxito'}

# nome curto usado nas planilhas da GJ ("Dr. Arilson")
_CURTOS = [('ARILSON', 'Dr. Arilson'), ('MAILSON', 'Dr. Mailson'), ('KALEBE', 'Dr. Kalebe'),
           ('HELOISA', 'Dra. Heloisa'), ('AGENOR', 'Dr. Agenor'), ('BRUNO VIN', 'Dr. Bruno'),
           ('FELIPE DA CONCEI', 'Dr. Felipe'), ('FELIPE DA SILVA', 'Dr. Felipe Gonçalves'),
           ('MATHEUS', 'Dr. Matheus'), ('TAYNARA', 'Dra. Taynara'), ('ANA SHEILA', 'Dra. Ana Sheila'),
           ('BRUNA', 'Dra. Bruna'), ('RENAN', 'Dr. Renan'), ('NATALY', 'Dra. Nataly'), ('MANUELLE', 'Dra. Manuelle')]


def nome_curto(nome):
    n = kpi_exito._norm(nome or '').upper() if hasattr(kpi_exito, '_norm') else (nome or '').upper()
    n = ''.join(c for c in __import__('unicodedata').normalize('NFD', (nome or '').upper())
                if __import__('unicodedata').category(c) != 'Mn')
    for chave, curto in _CURTOS:
        if chave.replace('Í', 'I').replace('Ç', 'C') in n:
            return curto
    return (nome or '').title() or '-'


def _dig(s):
    return ''.join(filter(str.isdigit, s or ''))


def _br(x, casas=2):
    return f'{x:.{casas}f}'.replace('.', ',')


def _pct(num, den):
    return '—' if not den else f'{100 * num / den:.1f}%'.replace('.', ',')


# Pontuacao de bonificacao: proposta registrada no arquivo de diagnostico, sempre
# sujeita a validacao da GJ (Plano de Carreira, 12.1: nenhum ponto negativo e'
# aplicado automaticamente). Sem proposta, sai "a lancar (GJ)".
def _pts(x):
    if x is None:
        return 'a lançar (GJ)'
    return ('+' if x > 0 else '') + f'{x:.2f}'.replace('.', ',')


def pontos_total(r):
    ps = r.get('pontos') or []
    return round(sum(p['valor'] for p in ps), 2) if ps else None


def _soma_pts(rs):
    vals = [pontos_total(r) for r in rs if pontos_total(r) is not None]
    return round(sum(vals), 2) if vals else None


def rubrica_txt(r):
    ps = r.get('pontos') or []
    if not ps:
        return 'a lançar (GJ)'
    txt = '; '.join(f"{p['rubrica']} ({_pts(p['valor'])})" for p in ps)
    return txt + (f". {r['pontos_obs']}" if r.get('pontos_obs') else '')


# ------------------------------------------------------------------ semanas uteis

def semanas_uteis(ano, mes):
    """[(rotulo_aba, inicio, fim)] - segunda a sexta, recortadas ao mes, rotulo no
    padrao das abas da GJ ("Semana 01.09-04.09")."""
    ini, out = date(ano, mes, 1), []
    ultimo = date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)
    cur = ini
    while cur <= ultimo:
        seg = cur - timedelta(days=cur.weekday())
        a, b = max(seg, ini), min(seg + timedelta(days=4), ultimo)
        if a <= b:
            out.append((f"Semana {a.strftime('%d.%m')}-{b.strftime('%d.%m')}", a, b))
        cur = seg + timedelta(days=7)
    return out


def semana_da_data(data_iso, semanas):
    d = datetime.strptime(str(data_iso)[:10], '%Y-%m-%d').date()
    for rot, a, b in semanas:
        if a <= d <= b:
            return rot
    # fim de semana: vai para a semana util anterior
    for rot, a, b in reversed(semanas):
        if a <= d:
            return rot
    return semanas[0][0]


# ------------------------------------------------------------------ despacho (ADVBOX)
#
# Pedido da GJ (15/09/2026): o relatorio tem que dizer se houve agendamento de
# despacho e se foi realizado. Fonte: as 4 tarefas de despacho do ADVBOX (mesmos
# tipos da auditoria de despachos). Ligacao SO pelo numero do processo da decisao
# e pelos numeros citados na linha (origem, embargos, execucao): ligar pelo nome do
# cliente trazia os despachos de todos os outros processos do mesmo cliente.

_RE_CNJ = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')


def _d(iso):
    return datetime.strptime(iso[:10], '%Y-%m-%d').strftime('%d/%m/%Y')


def numeros_do_registro(r):
    txt = ' '.join([r.get('processo') or '', r.get('situacao') or ''])
    return {_dig(m) for m in _RE_CNJ.findall(txt)} | {r.get('chave_dig') or _dig(r.get('processo'))}


def levantar_despachos(de, ate):
    """Tarefas de despacho concluidas entre `de` e `ate` (mes a mes) + as pendentes."""
    import time
    import advbox_integration as advbox
    import despachos_controle as dc
    ini = datetime.strptime(de, '%Y-%m-%d').date()
    fim = datetime.strptime(ate, '%Y-%m-%d').date()
    janelas, cur = [], ini
    while cur <= fim:
        prox = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        janelas.append((cur.isoformat(), min(prox - timedelta(days=1), fim).isoformat()))
        cur = prox

    def evento(nome, quando, pendente, t):
        law = dc._lawsuit(t)
        return {'tipo': nome, 'quando': quando, 'situacao': dc._situacao({'tipo': nome, 'pendente': pendente}),
                'processo': _dig(law.get('process_number')), 'processo_fmt': law.get('process_number') or '',
                'para': ', '.join(u.get('name', '') for u in (t.get('users') or []) if isinstance(u, dict)),
                'nota': re.sub(r'\s+', ' ', t.get('notes') or '')[:180]}

    eventos = []
    for nome, tid in dc.TIPOS_DESPACHO.items():
        for a, b in janelas:
            lst = []
            for _ in range(3):
                try:
                    lst = advbox.listar_tarefas(task_id=tid, completed_start=a, completed_end=b, limit=100) or []
                    break
                except Exception:
                    time.sleep(5)
            for t in lst:
                c = dc._concluida_em(t)
                if c and a <= c <= b:
                    eventos.append(evento(nome, c, False, t))
        try:
            pend = advbox.listar_tarefas(task_id=tid, limit=100) or []
        except Exception:
            pend = []
        eventos += [evento(nome, str(t.get('date'))[:10], True, t) for t in pend]
    return eventos


def resumo_despacho(evs, data_pub):
    """(texto da coluna Despacho, status curto) para a decisao publicada em data_pub."""
    if not evs:
        return 'ADVBOX: sem agendamento de despacho registrado.', 'Sem agendamento'
    evs = sorted(evs, key=lambda e: e['quando'])
    # Os rotulos vem de despachos_controle._situacao, que em 24/09/2026 passou a
    # usar as 3 categorias pedidas pela GJ (SOLICITADO -> AGENDADO -> REALIZADO).
    # Este resumo ainda procurava os nomes antigos ('AGENDAMENTO PEDIDO', 'A
    # AGENDAR'), que nao existem mais: toda decisao saia como "sem agendamento" e
    # a planilha perdia o historico de despacho a cada rodada.
    real = [e for e in evs if e['situacao'] == 'REALIZADO' and e['quando'] <= data_pub]
    pedidos = [e for e in evs if e['situacao'] == 'SOLICITADO' and e['quando'] <= data_pub]
    depois = [e for e in evs if e['situacao'] == 'REALIZADO' and e['quando'] > data_pub]
    pend = [e for e in evs if e['situacao'] == 'AGENDADO']
    partes = []
    if real:
        quem = sorted({p.strip().title() for e in real if e['tipo'] != 'DESPACHO REALIZADO'
                       for p in e['para'].split(',') if p.strip()})
        rel = next((e['nota'] for e in reversed(real) if e['tipo'] == 'DESPACHO REALIZADO' and e['nota']), '')
        partes.append(f"despacho REALIZADO antes da decisão em {', '.join(sorted({_d(e['quando']) for e in real}))}"
                      + (f" ({', '.join(quem)})" if quem else '') + (f'. Registro: "{rel}"' if rel else ''))
        status = 'Realizado'
    elif pedidos:
        partes.append(f"agendamento pedido {len(pedidos)} vez(es), de {_d(pedidos[0]['quando'])} a "
                      f"{_d(pedidos[-1]['quando'])}, SEM despacho realizado antes da decisão")
        status = 'Pedido, não realizado'
    else:
        partes.append('sem agendamento de despacho antes da decisão')
        status = 'Sem agendamento'
    if depois:
        partes.append(f"despacho realizado depois da publicação em {', '.join(sorted({_d(e['quando']) for e in depois}))}")
    if pend:
        partes.append(f"pendente: {pend[-1]['tipo'].lower()} ({_d(pend[-1]['quando'])})")
    procs = sorted({e['processo_fmt'] for e in evs if e['processo_fmt']})
    return 'ADVBOX: ' + '; '.join(partes) + (f". Tarefa(s) no processo {', '.join(procs)}." if procs else '.'), status


# ------------------------------------------------------------------ categoria PMP
#
# A categoria do plano (PMP Start/Plus/Gold/Platinum) fica no campo "Pasta" do
# processo no ADVBOX (`folder` na API), em regra no PROC. MAE do cliente - o
# agravo e o incidente costumam vir com a Pasta vazia (levantamento de 15/09/2026:
# 22 de 23 decisoes resolvidas assim). Sem a Pasta, a fonte e' o contrato de
# honorarios. Cache em _trabalho/ para a rodada diaria nao repetir consultas.

def categoria_pmp(texto):
    m = re.search(r'START|PLUS|GOLD|PLATINUM', texto or '', re.I)
    return m.group(0).title() if m else None


def preencher_categorias(linhas, diagnosticos):
    import time
    import advbox_integration as advbox
    cam = os.path.join(os.path.dirname(__file__), '..', '_trabalho', 'kpi_pmp_cache.json')
    try:
        cache = json.load(open(cam, encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    ja = {_dig(d['processo_chave']) for d in diagnosticos if d.get('categoria') not in (None, '', 'A confirmar')}
    for l in kpi_exito.apurar(linhas)['computadas']:
        dig = _dig(l['processo'])
        if dig in ja or cache.get(dig):
            continue
        cat = None
        try:
            law = (advbox.buscar_processo(numero_processo=l['processo']) or [None])[0]
            time.sleep(2.1)
            cat = categoria_pmp((law or {}).get('folder'))
            for c in ([] if cat or not law else (law.get('customers') or [])):
                outros = advbox.buscar_processo(cliente_id=c.get('customer_id')) or []
                time.sleep(2.1)
                cat = next((categoria_pmp(o.get('folder')) for o in outros if categoria_pmp(o.get('folder'))), None)
                if cat:
                    break
        except Exception:
            cat = None
        cache[dig] = cat
    json.dump(cache, open(cam, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return cache


# ------------------------------------------------------------------ montagem

def carregar_diagnosticos(caminho):
    try:
        return json.load(open(caminho, encoding='utf-8')).get('linhas', [])
    except (OSError, ValueError):
        return []


def montar_registros(linhas, diagnosticos, semanas, despachos=None, categorias=None):
    """Une a apuracao (numeros) com o diagnostico (texto). Devolve lista de dicts."""
    apur = kpi_exito.apurar(linhas)
    comput = apur['computadas']
    diag_por = {(_dig(d['processo_chave']), d['data']): d for d in diagnosticos}
    usados, regs = set(), []

    for l in comput:
        chave = (_dig(l['processo']), str(l['data'])[:10])
        d = diag_por.get(chave, {})
        usados.add(chave)
        adv_kpi = d.get('advogado_kpi') or ''
        regs.append({
            'pontua': True, 'data': chave[1],
            'semana': d.get('semana') or semana_da_data(chave[1], semanas),
            'processo': d.get('processo') or l['processo'],
            'cliente': d.get('cliente') or (l.get('cliente') or '').title(),
            'advogado': d.get('advogado') or (f"A confirmar (ADVBOX: {nome_curto(l.get('advogado_responsavel'))})"),
            'advogado_kpi': adv_kpi or f"A confirmar ({nome_curto(l.get('advogado_responsavel'))})",
            'categoria': (d.get('categoria') if d.get('categoria') not in (None, '', 'A confirmar')
                          else (categorias or {}).get(chave[0])) or 'A confirmar (ver contrato de honorários)',
            'parte_orgao': d.get('parte_orgao') or l.get('orgao') or '',
            'situacao': d.get('situacao') or f"A elaborar. Dispositivo lido: {l.get('evidencia') or '-'}",
            'diagnostico': d.get('diagnostico') or 'A elaborar.',
            'despacho_manual': d.get('despacho') or '', 'chave_dig': chave[0],
            'estrategia': d.get('estrategia') or 'A elaborar.',
            'probabilidade': d.get('probabilidade') or 'A elaborar.',
            'carteira': l['carteira'], 'kpi': l['kpi'],
            'classificacao': CLASSIF.get(l['resultado'], l['resultado']),
            'peso': l['peso'], 'contrib': l['contribuicao'], 'link': l.get('link_djen') or '',
            'pontos': d.get('pontos') or [], 'pontos_obs': d.get('pontos_obs', ''),
        })
    # linhas so de rastreabilidade (ja computadas no mes anterior, pendentes da GJ)
    for d in diagnosticos:
        chave = (_dig(d['processo_chave']), d['data'])
        if chave in usados or d.get('pontua'):
            continue
        regs.append({
            'pontua': False, 'data': d['data'], 'semana': d.get('semana') or semana_da_data(d['data'], semanas),
            'processo': d['processo'], 'cliente': d['cliente'], 'advogado': d.get('advogado') or 'A confirmar',
            'advogado_kpi': d.get('advogado_kpi') or '', 'categoria': d.get('categoria') or 'A confirmar',
            'parte_orgao': d.get('parte_orgao', ''), 'situacao': d.get('situacao', ''),
            'diagnostico': d.get('diagnostico', ''), 'despacho_manual': d.get('despacho', ''), 'chave_dig': chave[0],
            'estrategia': d.get('estrategia', ''), 'probabilidade': d.get('probabilidade', ''),
            'carteira': d.get('carteira', ''), 'kpi': '', 'classificacao': d.get('classificacao', 'Não pontua'),
            'peso': None, 'contrib': None, 'link': '', 'pontos': [], 'pontos_obs': '',
        })
    for r in regs:
        manual = (r.get('despacho_manual') or '').strip()
        if manual in ('—', 'Não mencionado — a confirmar.', 'A confirmar.'):
            manual = ''
        if despachos is None:
            r['despacho'], r['despacho_status'] = (manual or 'Não mencionado — a confirmar.'), ''
            continue
        nums = numeros_do_registro(r)
        # Processo relacionado (origem, embargos) so conta perto da decisao: o
        # despacho de junho na acao de origem da Cliente AB nao foi sobre o agravo
        # decidido em setembro. No proprio processo, vale o historico inteiro.
        corte = (datetime.strptime(r['data'], '%Y-%m-%d').date() - timedelta(days=45)).isoformat()
        evs = [e for e in despachos if e['processo'] == r['chave_dig']
               or (e['processo'] in nums and e['quando'] >= corte)]
        texto, status = resumo_despacho(evs, r['data'])
        r['despacho'] = texto + (f' Controladoria: {manual}' if manual else '')
        r['despacho_status'] = status
    regs.sort(key=lambda r: (r['semana'], r['data'], not r['pontua']))
    return regs, apur


def linhas_semana(regs, rot):
    out = [CAB_SEMANA]
    for r in [x for x in regs if x['semana'] == rot]:
        out.append([r['processo'], r['cliente'], r['advogado'], r['categoria'],
                    CARTEIRA_ROTULO.get(r['carteira'], r['carteira'] or 'A confirmar'), r['parte_orgao'],
                    r['situacao'], r['diagnostico'], r['despacho'], r['estrategia'], r['probabilidade'],
                    _pts(pontos_total(r)) if r['pontua'] else '—', rubrica_txt(r) if r['pontua'] else '—',
                    r['kpi'] or '—', r['classificacao'],
                    _br(r['peso'], 1) if r['peso'] is not None else '—',
                    _br(r['contrib'], 2) if r['contrib'] is not None else '—',
                    datetime.strptime(r['data'], '%Y-%m-%d').strftime('%d/%m/%Y'), r['link']])
    return out


def aba_taxa(regs, carteira, semanas, nome_mes, periodo, titulo):
    """Layout da aba 'Taxa Exito Rural Ago.2026'. Devolve (linhas, marcas de formato)."""
    L, fmt = [], {'titulo': [], 'bloco': [], 'cab': [], 'total': []}

    def add(linha, tipo=None):
        L.append(linha)
        if tipo:
            fmt[tipo].append(len(L) - 1)

    deste = [r for r in regs if r['pontua'] and r['carteira'] == carteira]
    fora = [r for r in regs if not r['pontua'] and r['carteira'] in (carteira, '')]
    add([titulo], 'titulo')
    add([f'Apurado de {periodo} — atualizado automaticamente a partir das intimações do DJEN, com as decisões da GJ aplicadas.'])
    add([])
    num_t = den_t = 0.0
    for k in ('KPI 1', 'KPI 2', 'KPI 3'):
        rs = [r for r in deste if r['kpi'] == k]
        add([f'{ROTULO[k]} — {len(rs)} decisões'], 'bloco')
        add(['Processo', 'Cliente', 'Advogado', 'KPI', 'Classificação', 'Peso', 'Pontos Bonif.', 'Semana', 'Despacho', 'Rubrica aplicada (proposta)'], 'cab')
        n = sum(r['contrib'] for r in rs)
        d = sum(r['peso'] for r in rs)
        num_t, den_t = num_t + n, den_t + d
        for r in rs:
            add([r['processo'].split(' ')[0], r['cliente'], r['advogado_kpi'], k, r['classificacao'],
                 _br(r['peso'], 1), _pts(pontos_total(r)), r['semana'], r.get('despacho_status') or '—', rubrica_txt(r)])
        add([f"Subtotal {k} — Numerador: {_br(n, 1)} ({sum(1 for r in rs if r['classificacao'] == 'Êxito')} êxitos) | "
             f"Denominador: {_br(d, 1)} | {k} = {_pct(n, d)} | Pontos: {_pts(_soma_pts(rs))}"], 'total')
        add([])
    if fora:
        add(['Não contabilizados nesta competência (rastreabilidade)'], 'bloco')
        for r in fora:
            add([f"{r['processo']} — {r['cliente']}: {r['classificacao']}"])
        add([])
    add([f'TAXA GERAL PONDERADA — {titulo.split("—", 1)[-1].strip().upper()}'], 'bloco')
    add([f'Numerador: {_br(num_t, 2)} | Denominador: {_br(den_t, 2)} | Taxa Geral Ponderada = {_pct(num_t, den_t)} '
         f'| Meta: 20% | {"ATINGIDA" if den_t and num_t / den_t >= 0.2 else "NÃO ATINGIDA" if den_t else "—"}'], 'total')
    cont = defaultdict(int)
    for r in deste:
        cont[r.get('despacho_status') or 'não levantado'] += 1
    add(['Despacho antes da decisão (ADVBOX): ' + ' | '.join(f'{k}: {v}' for k, v in sorted(cont.items()))])
    add([])
    # por semana
    add([f'TAXA POR SEMANA — {nome_mes.upper()}'], 'bloco')
    add(['Semana', 'Decisões', 'Numerador', 'Denominador', 'Taxa Ponderada', 'KPI 1', 'KPI 2', 'KPI 3', 'Meta 20%'], 'cab')
    for rot, _, _ in semanas:
        rs = [r for r in deste if r['semana'] == rot]
        n, d = sum(r['contrib'] for r in rs), sum(r['peso'] for r in rs)
        por_k = []
        for k in ('KPI 1', 'KPI 2', 'KPI 3'):
            rk = [r for r in rs if r['kpi'] == k]
            nk, dk = sum(r['contrib'] for r in rk), sum(r['peso'] for r in rk)
            por_k.append(f'{_pct(nk, dk)} ({_br(nk, 1)}/{_br(dk, 1)})' if dk else '—')
        add([rot, str(len(rs)), _br(n, 2), _br(d, 2), _pct(n, d)] + por_k +
            ['—' if not d else ('SIM' if n / d >= 0.2 else 'NÃO')])
    add([f'TOTAL {nome_mes.upper()}', str(len(deste)), _br(num_t, 2), _br(den_t, 2), _pct(num_t, den_t)], 'total')
    add([])
    # por advogado
    add([f'TAXA DE ÊXITO PONDERADA POR ADVOGADO — {nome_mes.upper()}'], 'bloco')
    add(['Advogado', 'Decisões', 'Numerador', 'Denominador', 'Taxa Ponderada', 'Saldo de pontos', 'Detalhamento por KPI', 'Despacho realizado'], 'cab')
    por_adv = defaultdict(list)
    for r in deste:
        por_adv[r['advogado_kpi']].append(r)
    for adv in sorted(por_adv, key=lambda a: (a.startswith('A confirmar'), a)):
        rs = por_adv[adv]
        n, d = sum(r['contrib'] for r in rs), sum(r['peso'] for r in rs)
        det = ' · '.join(f"{k}: {_br(sum(r['contrib'] for r in rs if r['kpi'] == k), 1)}/"
                         f"{_br(sum(r['peso'] for r in rs if r['kpi'] == k), 1)}"
                         for k in ('KPI 1', 'KPI 2', 'KPI 3') if any(r['kpi'] == k for r in rs))
        add([adv, str(len(rs)), _br(n, 2), _br(d, 2), _pct(n, d), _pts(_soma_pts(rs)), det,
             f"{sum(1 for r in rs if r.get('despacho_status') == 'Realizado')} de {len(rs)}"])
    add([f'TOTAL CARTEIRA {"RURAL" if carteira == "rural" else "DIVERSA"}', str(len(deste)),
         _br(num_t, 2), _br(den_t, 2), _pct(num_t, den_t), _pts(_soma_pts(deste)), ''], 'total')
    add([])
    add([f'CONSOLIDAÇÃO DE PONTOS DE BONIFICAÇÃO POR ADVOGADO — {nome_mes.upper()} (PROPOSTA PARA VALIDAÇÃO DA GJ)'], 'bloco')
    add(['Advogado', 'Decisões', 'Pontos positivos', 'Pontos negativos', 'Saldo líquido',
         'Despachos antes da decisão', 'Situação'], 'cab')
    for adv in sorted(por_adv, key=lambda a: (a.startswith('A confirmar'), a)):
        rs = por_adv[adv]
        vals = [pontos_total(r) for r in rs if pontos_total(r) is not None]
        pos = round(sum(v for v in vals if v > 0), 2)
        neg = round(sum(v for v in vals if v < 0), 2)
        feitos = sum(1 for r in rs if r.get('despacho_status') == 'Realizado')
        taxa_d = feitos / len(rs) if rs else 0
        if len(vals) < len(rs):
            sit = 'Pontuação incompleta (a lançar pela GJ)'
        elif pos + neg < 0:
            sit = 'Saldo negativo — variável bloqueada'
        elif taxa_d < 0.9:
            sit = 'Não habilitado — despachos abaixo de 90% (Plano, item 5, I)'
        else:
            sit = 'Habilitado (pendente D3, retrabalho, projetos e margem)'
        add([adv, str(len(rs)), _pts(pos), _pts(neg), _pts(round(pos + neg, 2)),
             f'{feitos} de {len(rs)} ({round(100 * taxa_d)}%)', sit])
    add([])
    add(['Notas metodológicas'], 'bloco')
    notas = [
        '1. Fonte: intimações capturadas no DJEN pelas OABs monitoradas, classificadas pela automação (kpi_exito) e ajustadas pelas decisões da GJ registradas em docs/kpi_exito/DECISOES_GJ_AAAA-MM.json. A carteira rural e a diversa são apuradas separadamente e nunca se somam.',
        '2. Semana: aba por semana útil (segunda a sexta), pela data de disponibilização no DJEN, salvo quando a GJ já lançou a decisão em outra semana (ex.: 0000055-00, decisão de 01/09 registrada na aba Semana 01.09-04.09).',
        '3. Decisão já computada no mês anterior não pontua de novo, ainda que republicada no DJEN nesta competência (comparação pela data do ato).',
        '4. Atribuição por advogado: o resultado é de quem conduziu o ato que gerou a decisão, não do responsável atual no ADVBOX (orientação da GJ de 15/09/2026). "A confirmar (X)" indica o responsável atual do ADVBOX ainda não conferido contra o histórico do processo.',
        '5. Pontos de bonificação (PROPOSTA, validação da GJ): carteira rural pelo Plano de Carreira v2 (item 10: liminar relevante +1, sentença de mérito +2, suspensão relevante +1 a +2, decisão com utilidade real +0,5; item 12.1: derrota aceitável -0,5 conforme padrão de agosto/Presidência, ponto técnico -1, estratégia insuficiente -1 a -2, falha técnica relevante -2 a -3, omissão grave -5); carteira diversa pelo Regulamento v3 (-0,50 derrota aceitável por decisão da Presidência; ausência de prova -0,20 a -0,50). Sem despacho antes da decisão: -0,5 nas derrotas rurais (tipo B) e -0,10 proposto nas diversas; nos êxitos, conta só para a taxa de despachos, que precisa chegar a 90% para habilitar a variável (Plano, item 5, I). D3, retrabalho, projetos e margem financeira não constam desta base.',
        '6. Diagnóstico, estratégia e probabilidade: leitura integral de cada ato; "A elaborar" indica decisão nova ainda sem leitura.',
        '7. Despacho: tarefas AGENDAR DESPACHO, DESPACHO COM JUIZ, DESPACHO COM O DESEMBARGADOR e DESPACHO REALIZADO do ADVBOX, ligadas pelo número do processo da decisão e pelos números citados na linha (origem, embargos, execução). "Realizado" considera só o que foi concluído até a data da publicação.',
    ]
    for nt in notas:
        add([nt])
    return L, fmt


# ------------------------------------------------------------------ Sheets

AZUL = {'red': 0.12156863, 'green': 0.30588236, 'blue': 0.47058824}
ROSA = {'red': 1, 'green': 0.78039217, 'blue': 0.80784315}
VERM = {'red': 0.6117647, 'green': 0, 'blue': 0.023529412}
CINZA = {'red': 0.93, 'green': 0.93, 'blue': 0.93}
AZUL_CLARO = {'red': 0.85, 'green': 0.9, 'blue': 0.96}
VERDE = {'red': 0.85, 'green': 0.92, 'blue': 0.83}


def publicar(linhas, diagnosticos, inicio, fim, spreadsheet_id, titulo_planilha=None, despachos=None, categorias=None):
    import planilha_conferencia as pc
    sheets = pc._sheets()
    semanas = semanas_uteis(inicio.year, inicio.month)
    semanas = [s for s in semanas if s[1] <= fim]
    nome_mes = f'{MESES[inicio.month - 1]}/{inicio.year}'
    periodo = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    regs, apur = montar_registros(linhas, diagnosticos, semanas, despachos, categorias)
    abrev = f'{MESES_ABREV[inicio.month - 1]}.{inicio.year}'

    abas = []
    for rot, _, _ in semanas:
        abas.append((rot, 'semana', linhas_semana(regs, rot), None))
    for cart, nome, tit in (('rural', f'Taxa Êxito Rural {abrev}',
                             f'Taxa de Êxito Jurídico Ponderado — Carteira de Dívidas Rurais — {nome_mes}'),
                            ('diversa', f'Carteira Diversa {abrev}',
                             f'Taxa de Êxito Jurídico Ponderado — Carteira Diversa — {nome_mes}')):
        L, fmt = aba_taxa(regs, cart, semanas, nome_mes, periodo, tit)
        abas.append((nome, 'taxa', L, fmt))

    meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existentes = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    novos = [n for n, *_ in abas if n not in existentes]
    req = [{'addSheet': {'properties': {'title': n}}} for n in novos]
    if titulo_planilha:
        req.append({'updateSpreadsheetProperties': {'properties': {'title': titulo_planilha}, 'fields': 'title'}})
    if req:
        sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': req}).execute()
    meta = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    gids = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
    # abas antigas deste gerador (formato anterior) saem; abas de terceiros ficam
    velhas = [t for t in gids if t in ('POR SEMANA', 'POR ADVOGADO', 'DECISOES', 'A CONFERIR')]
    ordem = [n for n, *_ in abas]
    req = [{'deleteSheet': {'sheetId': gids[t]}} for t in velhas]
    req += [{'updateSheetProperties': {'properties': {'sheetId': gids[n], 'index': i}, 'fields': 'index'}}
            for i, n in enumerate(ordem)]
    sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': req}).execute()

    for nome, *_ in abas:
        sheets.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=f"'{nome}'!A1:Z1000").execute()
    sheets.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body={
        'valueInputOption': 'RAW',
        'data': [{'range': f"'{nome}'!A1", 'values': vals} for nome, _, vals, _ in abas]}).execute()

    req = []

    def fmt_cel(gid, r0, r1, c0, c1, f, campos):
        req.append({'repeatCell': {'range': {'sheetId': gid, 'startRowIndex': r0, 'endRowIndex': r1,
                                             'startColumnIndex': c0, 'endColumnIndex': c1},
                                   'cell': {'userEnteredFormat': f}, 'fields': campos}})

    for nome, tipo, vals, fmt in abas:
        gid = gids[nome]
        req.append({'unmergeCells': {'range': {'sheetId': gid}}})
        fmt_cel(gid, 0, 1000, 0, 20, {'textFormat': {'fontFamily': 'Arial', 'fontSize': 10, 'bold': False,
                                                     'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}},
                                      'backgroundColor': {'red': 1, 'green': 1, 'blue': 1},
                                      'wrapStrategy': 'WRAP' if tipo == 'semana' else 'OVERFLOW_CELL',
                                      'verticalAlignment': 'TOP', 'horizontalAlignment': 'LEFT'},
                'userEnteredFormat(textFormat,backgroundColor,wrapStrategy,verticalAlignment,horizontalAlignment)')
        if tipo == 'semana':
            fmt_cel(gid, 0, 1, 0, len(CAB_SEMANA), {'backgroundColor': AZUL, 'horizontalAlignment': 'CENTER',
                                                    'verticalAlignment': 'MIDDLE', 'wrapStrategy': 'WRAP',
                                                    'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                                                                   'fontFamily': 'Arial', 'fontSize': 11, 'bold': True}},
                    'userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)')
            for i, v in enumerate(vals[1:], 1):
                if v[COL_CLASSIF].startswith('Não pontua') or v[COL_CLASSIF].startswith('A definir'):
                    fmt_cel(gid, i, i + 1, 0, len(CAB_SEMANA),
                            {'backgroundColor': ROSA, 'textFormat': {'foregroundColor': VERM, 'fontFamily': 'Arial',
                                                                     'fontSize': 10, 'bold': True}},
                            'userEnteredFormat(backgroundColor,textFormat)')
            for c, w in enumerate(LARGURAS):
                req.append({'updateDimensionProperties': {'range': {'sheetId': gid, 'dimension': 'COLUMNS',
                                                                    'startIndex': c, 'endIndex': c + 1},
                                                          'properties': {'pixelSize': w}, 'fields': 'pixelSize'}})
            req.append({'updateSheetProperties': {'properties': {'sheetId': gid, 'gridProperties': {'frozenRowCount': 1}},
                                                  'fields': 'gridProperties.frozenRowCount'}})
        else:
            for r in fmt['titulo']:
                fmt_cel(gid, r, r + 1, 0, 11, {'textFormat': {'bold': True, 'fontSize': 13, 'fontFamily': 'Arial'}},
                        'userEnteredFormat.textFormat')
            for r in fmt['bloco']:
                fmt_cel(gid, r, r + 1, 0, 11, {'textFormat': {'bold': True, 'fontFamily': 'Arial', 'fontSize': 10},
                                              'backgroundColor': AZUL_CLARO},
                        'userEnteredFormat(textFormat,backgroundColor)')
            for r in fmt['cab']:
                fmt_cel(gid, r, r + 1, 0, 11, {'backgroundColor': AZUL, 'textFormat': {
                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'bold': True, 'fontFamily': 'Arial', 'fontSize': 10}},
                        'userEnteredFormat(backgroundColor,textFormat)')
            for r in fmt['total']:
                fmt_cel(gid, r, r + 1, 0, 11, {'textFormat': {'bold': True, 'fontFamily': 'Arial', 'fontSize': 10},
                                              'backgroundColor': VERDE},
                        'userEnteredFormat(textFormat,backgroundColor)')
            for c, w in enumerate([190, 260, 150, 70, 170, 110, 110, 150, 150, 420]):
                req.append({'updateDimensionProperties': {'range': {'sheetId': gid, 'dimension': 'COLUMNS',
                                                                    'startIndex': c, 'endIndex': c + 1},
                                                          'properties': {'pixelSize': w}, 'fields': 'pixelSize'}})
    sheets.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': req}).execute()
    n_pont = sum(1 for r in regs if r['pontua'])
    return (f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit', n_pont,
            sum(1 for r in regs if not r['pontua']), [n for n, *_ in abas])


def publicar_competencia(linhas, inicio, fim, pasta_id=None):
    """Acha (ou cria) a planilha da competencia na pasta da GJ e a reescreve.

    E' o que o `kpi --planilha` chama todo dia. `linhas` ja com as decisoes da GJ
    aplicadas; o diagnostico vem de _trabalho/kpi_diagnosticos_AAAA-MM.json."""
    import google_integration as g
    import planilha_conferencia as pc
    try:
        import equipe
    except ImportError:
        equipe = None
    pasta_id = pasta_id or getattr(equipe, 'KPI_PLANILHA_PASTA_ID', None)
    if not pasta_id:
        raise RuntimeError('KPI_PLANILHA_PASTA_ID nao configurado em config/equipe.py')
    titulo = f'Acompanhamento_Casos_Maldonado_{MESES[inicio.month - 1]}_{inicio.year}'
    drive, _ = g.autenticar_google()
    achados = g._listar(drive, f"'{pasta_id}' in parents and name = '{g._escapar(titulo)}' and trashed = false",
                        limite=1)
    if achados:
        sid = achados[0]['id']
    else:
        sheets = pc._sheets()
        sid = sheets.spreadsheets().create(body={'properties': {
            'title': titulo, 'locale': 'pt_BR', 'timeZone': 'America/Porto_Velho'}},
            fields='spreadsheetId').execute()['spreadsheetId']
        atual = drive.files().get(fileId=sid, fields='parents', supportsAllDrives=True).execute()
        drive.files().update(fileId=sid, addParents=pasta_id, removeParents=','.join(atual.get('parents', [])),
                             supportsAllDrives=True).execute()
    diag = carregar_diagnosticos(os.path.join(os.path.dirname(__file__), '..', '_trabalho',
                                              f'kpi_diagnosticos_{inicio.strftime("%Y-%m")}.json'))
    despachos = levantar_despachos((inicio - timedelta(days=120)).isoformat(), fim.isoformat())
    categorias = preencher_categorias(linhas, diag)
    return publicar(linhas, diag, inicio, fim, sid, titulo_planilha=titulo, despachos=despachos, categorias=categorias)


if __name__ == '__main__':
    # python OPERACIONAL/kpi_acompanhamento.py kpi.csv 2026-09-01 2026-09-15 <spreadsheet_id>
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    import kpi_planilha
    arq, de, ate, sid = sys.argv[1:5]
    ini = datetime.strptime(de, '%Y-%m-%d').date()
    fim = datetime.strptime(ate, '%Y-%m-%d').date()
    linhas = kpi_planilha._ler_csv(arq)
    kpi_exito.aplicar_decisoes_gj(linhas, kpi_exito.carregar_decisoes_gj(os.path.join(
        os.path.dirname(__file__), '..', 'docs', 'kpi_exito', f'DECISOES_GJ_{ini.strftime("%Y-%m")}.json')))
    diag = carregar_diagnosticos(os.path.join(os.path.dirname(__file__), '..', '_trabalho',
                                              f'kpi_diagnosticos_{ini.strftime("%Y-%m")}.json'))
    titulo = f'Acompanhamento_Casos_Maldonado_{MESES[ini.month - 1]}_{ini.year}'
    despachos = levantar_despachos((ini - timedelta(days=120)).isoformat(), fim.isoformat())
    link, n, nf, abas = publicar(linhas, diag, ini, fim, sid, titulo_planilha=titulo, despachos=despachos)
    print(f'{link}\n  {n} decisao(oes) na taxa | {nf} so rastreabilidade | abas: {abas}')
