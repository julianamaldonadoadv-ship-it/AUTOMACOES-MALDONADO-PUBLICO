# -*- coding: utf-8 -*-
"""
Controle de Despachos — rotina diaria da Controladoria (POP-CJ-DESP-001)
=========================================================================

Regra da Dra. Juliana: **peticao inicial, agravo de instrumento e embargos a
execucao tem que ser despachados** — o agendamento nasce em 1 dia util apos o
protocolo. Este modulo mantem, no Drive do escritorio, a planilha que permite
acompanhar isso sem garimpo manual.

O que ele faz, todo dia:

1. le no ADVBOX os **protocolos-gatilho** concluidos no periodo (tarefa
   PROTOCOLO D-3/D-2/D-1/PRAZO FATAL cuja nota indica inicial, emenda a inicial
   (so cobra despacho se o processo nao foi despachado antes), agravo ou
   embargos a execucao);
2. le as **tarefas de despacho** (AGENDAR DESPACHO, DESPACHO COM JUIZ, DESPACHO
   COM O DESEMBARGADOR, DESPACHO REALIZADO), concluidas e pendentes;
3. classifica cada processo em **rural / a confirmar**, pelo grupo do cadastro;
4. escreve na planilha, **sem apagar o que a equipe anotou**.

Decisoes de desenho (13/09/2026), para nao se perderem:

- **Uma aba de despachos, com coluna `Situacao`**, e nao duas (realizados x
  pendentes). Linha que muda de aba levaria junto a anotacao da controller.
- **A chave de cada linha e o id da tarefa no ADVBOX.** Reexecutar o dia nao
  duplica linha: atualiza a que ja existe.
- **As duas ultimas colunas (`Confere?` e `Observacao`) sao da equipe** — a
  rotina nunca as sobrescreve.
- **Escopo:** a GJ definiu auditoria so de credito rural. O grupo do ADVBOX
  as vezes traz a classe processual ("ACAO CIVEL", "AGRAVO DE INSTRUMENTO"), que
  nao diz a tese — nesse caso a linha sai como `a confirmar`, nunca como "nao
  rural" (ver CLAUDE.md, secao do KPI: `group` nao e taxonomia de tese).
- **Somente leitura no ADVBOX.** A unica escrita e' na planilha do Drive.
"""
import os
import re
import sys
import json
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import advbox_integration as advbox
import google_integration as g
import prazos
import equipe

IDS_CONTROLLERS = {c['id'] for c in equipe.CONTROLLERS.values()}

NOME_PLANILHA = 'CONTROLE DE DESPACHOS - CONTROLADORIA'
PASTA_ZEUS = ['CONTROLADORIA', 'CONTROLE DE DESPACHOS']
CACHE = os.path.join(os.path.dirname(__file__), '..', '_trabalho',
                     'auditoria_despachos', 'cache_lawsuits.json')

TIPOS_PROTOCOLO = {'PROTOCOLO D-3': 8941168, 'PROTOCOLO D-2': 10177444,
                   'PROTOCOLO D-1': 10177445, 'PROTOCOLO - PRAZO FATAL': 10177446}
TIPOS_DESPACHO = {'AGENDAR DESPACHO': 9222516, 'DESPACHO COM JUIZ': 2596498,
                  'DESPACHO COM O DESEMBARGADOR': 2596538, 'DESPACHO REALIZADO': 10349941}

# Grupos do ADVBOX que nomeiam a TESE (e portanto definem escopo rural).
GRUPOS_RURAIS = ('ALONGAMENTO', 'DESCARACTERIZA', 'REVISIONAL', 'CREDITO RURAL', 'CRÉDITO RURAL')

ABA_PROTOCOLOS = 'PROTOCOLOS (GATILHO)'
ABA_DESPACHOS = 'DESPACHOS'
ABA_DIVERGENCIAS = 'DIVERGENCIAS'

CAB_PROTOCOLOS = ['Data protocolo', 'Peca', 'Processo protocolado', 'Cliente',
                  'Advogado responsavel', 'Escopo', 'Despacho', 'Data do despacho',
                  'Processo do despacho', 'Agendado em ate 1 dia util?', 'id tarefa',
                  'Confere?', 'Observacao']
CAB_DESPACHOS = ['Data', 'Situacao', 'Tipo da tarefa', 'Processo', 'Cliente',
                 'Advogado responsavel', 'Grupo/peca', 'Escopo', 'Registro',
                 'id tarefa', 'Confere?', 'Observacao']
CAB_DIVERGENCIAS = ['Apurado em', 'Onde', 'Processo', 'Cliente', 'Divergencia',
                    'O que o ADVBOX mostra', 'Confere?', 'Observacao']

COLUNAS_DA_EQUIPE = 2   # as duas ultimas colunas de cada aba nunca sao sobrescritas


# ============================================================
# LEITURA DO ADVBOX
# ============================================================

def _texto(valor):
    return re.sub(r'\s+', ' ', str(valor or '')).strip()


def _lawsuit(t):
    l = t.get('lawsuit')
    if isinstance(l, str):
        try:
            l = json.loads(l.replace("'", '"'))
        except Exception:
            l = {}
    return l or {}


def _concluida_em(t, exigir_controller=False):
    """Data de conclusao da tarefa. Em PROTOCOLO vale a conclusao da CONTROLLER
    (criterio da GJ, 13/09/2026): o advogado marca a parte dele quando entrega a
    peca, antes do protocolo. Dois clientes (15/09) sairam como protocolados
    so porque o advogado concluiu; a controller nao tinha protocolado."""
    usuarios = t.get('users') or []
    if exigir_controller and any(u.get('user_id') in IDS_CONTROLLERS for u in usuarios):
        usuarios = [u for u in usuarios if u.get('user_id') in IDS_CONTROLLERS]
    for u in usuarios:
        if u.get('completed'):
            return str(u['completed'])[:10]
    return None


def classificar_peca(nota):
    """Le a nota da tarefa de protocolo e diz qual gatilho e'. None = fora do gatilho."""
    n = _texto(nota).lower()
    if 'agravo' in n:
        return 'agravo de instrumento'
    if 'embargos a execu' in n or 'embargos à execu' in n:
        return 'embargos a execucao'
    # Emenda antes de "inicial": "Emenda À Inicial" contava como peticao inicial.
    # E' gatilho proprio (Dra. Juliana, 16/09/2026): se o processo nao foi
    # despachado antes, despacha-se depois da emenda.
    if 'emenda' in n:
        return 'emenda a inicial'
    if 'inicial' in n or re.search(r'protocolar (a )?(a[çc][ãa]o|peticao|petição)', n):
        return 'peticao inicial'
    return None


def _cache():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {}


def _salvar_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(c, open(CACHE, 'w'), ensure_ascii=False)


def dados_do_processo(numero, cache, lawsuit_id=None):
    """Grupo, responsavel e clientes — com cache em disco, para a rodada diaria
    nao gastar o rate limit do ADVBOX repetindo consulta.

    Aceita `lawsuit_id` porque **ha cadastro sem numero de processo**: o de um cliente
    (lawsuit_id 00000000) existe desde 10/06, antes da distribuicao, com `process_number`
    nulo. Buscar so pelo numero devolvia linha vazia, quando o ADVBOX tinha grupo,
    responsavel e cliente — levantado pela Dra. Juliana em 13/09/2026."""
    chave = ''.join(filter(str.isdigit, numero or '')) or (f'id:{lawsuit_id}' if lawsuit_id else '')
    if not chave:
        return {'grupo': '', 'responsavel': '', 'clientes': '', 'criado': ''}
    if chave in cache:
        return cache[chave]
    achados = []
    try:
        if ''.join(filter(str.isdigit, numero or '')):
            achados = advbox.buscar_processo(numero_processo=numero) or []
        elif lawsuit_id:
            p = advbox.obter_processo(lawsuit_id)
            if p:
                d = p.get('data', p) if isinstance(p, dict) else p
                achados = [d[0] if isinstance(d, list) else d]
    except Exception:
        achados = []
    reg = {'grupo': '', 'responsavel': '', 'clientes': '', 'criado': ''}
    for c in achados:
        if c.get('stage') == 'CRIADO EQUIVOCADAMENTE':
            continue
        reg = {'grupo': c.get('group') or '',
               'responsavel': c.get('responsible') or '',
               'clientes': ', '.join(x.get('name', '') for x in (c.get('customers') or [])),
               # a data de cadastro e' o que distingue o processo NOVO (nascido do
               # protocolo) dos outros processos antigos do mesmo cliente
               'criado': str(c.get('created_at') or '')[:10]}
        break
    cache[chave] = reg
    return reg


def escopo(grupo):
    """rural quando o grupo nomeia a tese; 'a confirmar' quando so traz a classe."""
    g_ = (grupo or '').upper()
    if any(m in g_ for m in GRUPOS_RURAIS):
        return 'rural'
    return 'a confirmar'


def coletar(de, ate):
    """Devolve protocolos-gatilho e tarefas de despacho do periodo."""
    protocolos, despachos = [], []
    for nome, tid in TIPOS_PROTOCOLO.items():
        for t in (advbox.listar_tarefas(task_id=tid, completed_start=de, completed_end=ate) or []):
            c = _concluida_em(t, exigir_controller=True)
            if not c or not (de <= c <= ate):
                continue
            peca = classificar_peca(t.get('notes'))
            if not peca:
                continue
            protocolos.append({'data': c, 'peca': peca, 'tarefa': t})
    for nome, tid in TIPOS_DESPACHO.items():
        for t in (advbox.listar_tarefas(task_id=tid, completed_start=de, completed_end=ate) or []):
            c = _concluida_em(t)
            if c and de <= c <= ate:
                despachos.append({'tipo': nome, 'quando': c, 'pendente': False, 'tarefa': t})
        for t in (advbox.listar_tarefas(task_id=tid) or []):
            despachos.append({'tipo': nome, 'quando': str(t.get('date'))[:10],
                              'pendente': True, 'tarefa': t})
        # Despachos realizados ANTES do periodo: nao entram na aba, servem so para
        # saber se o processo da emenda ja tinha sido despachado (Cliente A,
        # 0000000-00: despacho em 31/08, emenda em 14/09).
        antes = (datetime.strptime(de, '%Y-%m-%d').date() - timedelta(days=120)).isoformat()
        vespera = (datetime.strptime(de, '%Y-%m-%d').date() - timedelta(days=1)).isoformat()
        for t in (advbox.listar_tarefas(task_id=tid, completed_start=antes, completed_end=vespera) or []):
            c = _concluida_em(t)
            if c and c < de:
                despachos.append({'tipo': nome, 'quando': c, 'pendente': False,
                                  'tarefa': t, 'anterior': True})
    return protocolos, despachos


# ============================================================
# MONTAGEM DAS LINHAS
# ============================================================

def _situacao(d):
    if not d['pendente']:
        return 'REALIZADO' if d['tipo'] in ('DESPACHO REALIZADO', 'DESPACHO COM JUIZ',
                                            'DESPACHO COM O DESEMBARGADOR') else 'AGENDAMENTO PEDIDO'
    if d['tipo'] in ('DESPACHO COM JUIZ', 'DESPACHO COM O DESEMBARGADOR'):
        return 'AGENDADO'
    return 'A AGENDAR'


def _clientes_id(t):
    """IDs de cliente do processo da tarefa — é por eles que protocolo e despacho
    se ligam quando o numero do processo muda."""
    return {c.get('customer_id') for c in (_lawsuit(t).get('customers') or [])
            if c.get('customer_id')}


def _justica(numero):
    """Segmento J.TR do numero CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO): '401' = TRF1, '822' = TJRO."""
    d = ''.join(filter(str.isdigit, numero or ''))
    return d[13:16] if len(d) == 20 else ''


def montar(protocolos, despachos, cache):
    # A tarefa de PROTOCOLO fica no processo de ORIGEM (PROC MAE / 1o grau) e o
    # despacho acontece no processo NOVO: a inicial de um cliente foi protocolada na
    # tarefa do 0000000-01 e despachada no 0000000-02. Ligar so pelo numero do
    # processo marcava 7 de 9 protocolos como "SEM DESPACHO" — falso.
    # Por isso a ligacao e' pelo CLIENTE, e a planilha mostra em qual processo o
    # despacho saiu, para a controller conferir o vinculo.
    por_processo = {}
    for d in despachos:
        n = ''.join(filter(str.isdigit, _lawsuit(d['tarefa']).get('process_number') or ''))
        por_processo.setdefault(n, []).append(d)

    linhas_p = []
    # Cada protocolo gerou UM processo novo: processo ja casado com um protocolo
    # anterior nao pode ser reaproveitado por outro. Sem isso, o protocolo de
    # 08/09 do Cliente A casava com o agravo de 02/09, que ja tinha dono.
    ja_usados = set()
    for p in sorted(protocolos, key=lambda x: x['data']):
        numero = _lawsuit(p['tarefa']).get('process_number') or ''
        info = dados_do_processo(numero, cache, p['tarefa'].get('lawsuits_id'))
        # ultima reserva: o nome do cliente vem na propria tarefa, mesmo quando o
        # cadastro nao tem numero de processo
        if not info.get('clientes'):
            info = {**info, 'clientes': ', '.join(
                c.get('name', '') for c in (_lawsuit(p['tarefa']).get('customers') or []))}
        clientes_p = _clientes_id(p['tarefa'])

        # candidatos: despacho do MESMO cliente, a partir da data do protocolo.
        candidatos = [d for d in despachos
                      if clientes_p and (_clientes_id(d['tarefa']) & clientes_p)
                      and (d['quando'] or '') >= p['data']]
        # Emenda: o despacho e' no PROPRIO processo; e o que importa e' se ja houve
        # despacho realizado nele antes da emenda.
        despachado_antes = ''
        if p['peca'] == 'emenda a inicial':
            dig_p = ''.join(filter(str.isdigit, numero))
            candidatos = [d for d in candidatos
                          if ''.join(filter(str.isdigit, _lawsuit(d['tarefa']).get('process_number') or '')) == dig_p]
            anteriores = sorted(d['quando'] for d in despachos
                                if not d['pendente'] and d['quando'] and d['quando'] < p['data']
                                and _situacao(d) == 'REALIZADO'
                                and ''.join(filter(str.isdigit, _lawsuit(d['tarefa']).get('process_number') or '')) == dig_p)
            despachado_antes = anteriores[-1] if anteriores else ''
        candidatos.sort(key=lambda x: x['quando'] or '')

        # Cliente com varios processos (o Cliente A tem 3 agravos e 2 de 1o grau) faria
        # o protocolo de um agravo casar com o despacho de outro. Por isso escolhe-se
        # primeiro o PROCESSO ALVO, pelo tipo da peca protocolada, e so entao se mede
        # situacao e prazo dentro dele.
        alvo, tarefas_alvo = '', []
        if candidatos:
            por_num = {}
            for d in candidatos:
                por_num.setdefault(_lawsuit(d['tarefa']).get('process_number') or '', []).append(d)
            esperado = {'agravo de instrumento': 'AGRAVO',
                        'embargos a execucao': 'EMBARGOS'}.get(p['peca'])
            melhores = []
            for n_desp, ds in por_num.items():
                info_desp = dados_do_processo(n_desp, cache) if n_desp else {}
                grupo_desp = (info_desp.get('grupo') or '').upper()
                mesmo = (''.join(filter(str.isdigit, n_desp))
                         == ''.join(filter(str.isdigit, numero)))
                if p['peca'] == 'emenda a inicial':
                    casa = mesmo
                elif esperado:
                    casa = esperado in grupo_desp
                else:
                    # Peticao inicial: o despacho sai no processo NOVO, que nao e' o
                    # da tarefa de protocolo. Nao da' para ir alem disso com os dados
                    # do ADVBOX: o cadastro costuma nascer quando o caso entra, nao
                    # quando a peca e' protocolada, entao "criado perto do protocolo"
                    # nao distingue o processo novo do antigo (testado em 13/09/2026).
                    casa = (not mesmo) and 'AGRAVO' not in grupo_desp
                melhores.append((0 if casa else 1, min(d['quando'] or '' for d in ds), n_desp, ds))
            melhores.sort()
            # Cliente com mais de um processo elegivel: o vinculo nao se deduz dos
            # dados (o Cliente B tem duas acoes de descaracterizacao da mora). Nesse
            # caso a planilha NAO escolhe — pede conferencia e lista os candidatos.
            qualificados = [m for m in melhores if m[0] == 0]
            if not esperado and len(qualificados) > 1:
                # Desempate pela justica: a inicial nasce por dependencia no mesmo
                # segmento do processo da tarefa. A do Cliente B foi protocolada na
                # execucao federal 0000000-03 e virou o 0000000-04 (TRF1); as outras
                # duas acoes dele sao do TJRO. Continuando empatado, nao escolhe.
                mesma = [m for m in qualificados
                         if _justica(m[2]) and _justica(m[2]) == _justica(numero)]
                melhores = mesma if len(mesma) == 1 else []
            for casa, _, n_desp, ds in melhores:
                if casa != 0:
                    break
                chave_desp = ''.join(filter(str.isdigit, n_desp))
                if chave_desp and chave_desp in ja_usados:
                    continue
                alvo, tarefas_alvo = n_desp, ds
                if chave_desp:
                    ja_usados.add(chave_desp)
                break

        sit, quando, onde, dentro = 'SEM DESPACHO', '', '', ''
        if tarefas_alvo:
            tarefas_alvo.sort(key=lambda x: x['quando'] or '')
            # O gatilho se cumpre com o PRIMEIRO despacho realizado apos o protocolo.
            # Tarefa de despacho posterior no mesmo processo e' outro ciclo (no
            # Cliente B, o AGENDAR de 15/09 e' o despacho dos embargos de declaracao)
            # e nao pode fazer o despacho de 04/09 voltar a "a agendar".
            realizados = [d for d in tarefas_alvo if _situacao(d) == 'REALIZADO']
            ref = realizados[0] if realizados else tarefas_alvo[-1]
            sit, quando = _situacao(ref), ref['quando'] or ''
            onde = alvo if (''.join(filter(str.isdigit, alvo))
                            != ''.join(filter(str.isdigit, numero))) else 'mesmo processo'
            # o POP-CJ-DESP-001 cobra AGENDAR em 1 dia util: vale o primeiro
            # movimento de despacho NESSE processo, nao o ultimo
            try:
                limite = prazos.somar_dias_uteis(prazos._para_date(p['data']), 1)
                dentro = 'sim' if prazos._para_date(tarefas_alvo[0]['quando']) <= limite else 'nao'
            except Exception:
                dentro = ''
        elif despachado_antes:
            # ja despachado antes da emenda: nao e' falta, fica informado com a data
            sit, quando, onde = 'DESPACHADO ANTES DA EMENDA', despachado_antes, 'mesmo processo'
        elif candidatos:
            sit = 'CONFERIR VINCULO'
            onde = ', '.join(sorted({_lawsuit(d['tarefa']).get('process_number') or '?'
                                     for d in candidatos})[:3])

        # O processo novo costuma nomear a tese que o processo-mae nao nomeia
        # (o 0000000-01 de um cliente e' "ACAO CIVEL"; o 0000000-02, que nasceu do
        # protocolo, e' "DESCARACTERIZACAO DA MORA"). Fica FORA do elif: vale
        # justamente quando o vinculo e' unico, que e' quando ha alvo.
        if escopo(info['grupo']) != 'rural' and alvo:
            grupo_alvo = dados_do_processo(alvo, cache).get('grupo') or ''
            if escopo(grupo_alvo) == 'rural':
                info = {**info, 'grupo': grupo_alvo}

        # celula vazia esconde o problema: cadastro sem numero sai dito com todas
        # as letras, para a controladoria corrigir o cadastro
        numero = numero or f"(cadastro {p['tarefa'].get('lawsuits_id')} sem n. de processo)"
        linhas_p.append([p['data'], p['peca'], numero,
                         info['clientes'][:70], info['responsavel'], escopo(info['grupo']),
                         sit, quando, onde, dentro, str(p['tarefa'].get('id'))])

    linhas_d = []
    for d in sorted((d for d in despachos if not d.get('anterior')), key=lambda x: (x['quando'] or '')):
        l = _lawsuit(d['tarefa'])
        numero = l.get('process_number') or ''
        info = dados_do_processo(numero, cache, d['tarefa'].get('lawsuits_id'))
        if not info.get('clientes'):
            info = {**info, 'clientes': ', '.join(c.get('name', '') for c in (l.get('customers') or []))}
        numero = numero or f"(cadastro {d['tarefa'].get('lawsuits_id')} sem n. de processo)"
        linhas_d.append([d['quando'] or '', _situacao(d), d['tipo'], numero,
                         info['clientes'][:70], info['responsavel'],
                         info['grupo'], escopo(info['grupo']),
                         _texto(d['tarefa'].get('notes'))[:180], str(d['tarefa'].get('id'))])
    return linhas_p, linhas_d


# ============================================================
# PLANILHA NO DRIVE
# ============================================================

def _servicos():
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    creds = Credentials.from_authorized_user_file(os.path.join(config_dir, 'token.json'), g.SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds), build('sheets', 'v4', credentials=creds)


def _pasta(drive):
    pai = g._zeus_id(drive)
    for nome in PASTA_ZEUS:
        achada = g.buscar_subpasta(drive, pai, nome) or g.criar_pasta(drive, nome, pai)
        pai = achada['id'] if isinstance(achada, dict) else achada
    return pai


def _criar(drive, sheets, pasta_id):
    corpo = {'properties': {'title': NOME_PLANILHA},
             'sheets': [{'properties': {'title': ABA_PROTOCOLOS}},
                        {'properties': {'title': ABA_DESPACHOS}},
                        {'properties': {'title': ABA_DIVERGENCIAS}}]}
    ss = sheets.spreadsheets().create(body=corpo, fields='spreadsheetId').execute()
    sid = ss['spreadsheetId']
    atual = drive.files().get(fileId=sid, fields='parents', supportsAllDrives=True).execute()
    drive.files().update(fileId=sid, addParents=pasta_id,
                         removeParents=','.join(atual.get('parents', [])),
                         supportsAllDrives=True).execute()
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=sid, body={'valueInputOption': 'RAW', 'data': [
            {'range': f"'{ABA_PROTOCOLOS}'!A1", 'values': [CAB_PROTOCOLOS]},
            {'range': f"'{ABA_DESPACHOS}'!A1", 'values': [CAB_DESPACHOS]},
            {'range': f"'{ABA_DIVERGENCIAS}'!A1", 'values': [CAB_DIVERGENCIAS]}]}).execute()
    pedidos = []
    for aba in sheets.spreadsheets().get(spreadsheetId=sid).execute()['sheets']:
        gid = aba['properties']['sheetId']
        pedidos += [
            {'repeatCell': {'range': {'sheetId': gid, 'startRowIndex': 0, 'endRowIndex': 1},
                            'cell': {'userEnteredFormat': {
                                'textFormat': {'bold': True},
                                'backgroundColor': {'red': .93, 'green': .93, 'blue': .93}}},
                            'fields': 'userEnteredFormat(textFormat,backgroundColor)'}},
            {'updateSheetProperties': {'properties': {'sheetId': gid,
                                                      'gridProperties': {'frozenRowCount': 1}},
                                       'fields': 'gridProperties.frozenRowCount'}}]
    sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={'requests': pedidos}).execute()
    return sid


def _upsert(sheets, sid, aba, cabecalho, linhas, col_chave, periodo=None):
    """Atualiza pela chave (id da tarefa) e acrescenta o que for novo.
    As COLUNAS_DA_EQUIPE ultimas colunas nunca sao tocadas.

    Com `periodo`, a linha do periodo que a rodada nao trouxe mais (tarefa de
    protocolo que o advogado concluiu e a controller nao) e' removida — mas so
    se a equipe nao escreveu nada nela; senao fica e sobe como `mantidas`."""
    atuais = sheets.spreadsheets().values().get(
        spreadsheetId=sid, range=f"'{aba}'!A2:Z5000").execute().get('values', [])
    indice = {}
    for i, r in enumerate(atuais):
        if len(r) > col_chave and r[col_chave]:
            indice[r[col_chave]] = i + 2
    chaves = {l[col_chave] for l in linhas}
    remover, mantidas = [], []
    if periodo:
        n = len(cabecalho)
        for i, r in enumerate(atuais):
            r = (r + [''] * n)[:n]
            if not r[col_chave] or r[col_chave] in chaves or not (periodo[0] <= r[0][:10] <= periodo[1]):
                continue
            if any(c.strip() for c in r[n - COLUNAS_DA_EQUIPE:]):
                mantidas.append(r)
            else:
                remover.append(i + 2)
    atualizacoes, novas = [], []
    fim = chr(ord('A') + len(cabecalho) - COLUNAS_DA_EQUIPE - 1)
    for linha in linhas:
        chave = linha[col_chave]
        if chave in indice:
            atualizacoes.append({'range': f"'{aba}'!A{indice[chave]}:{fim}{indice[chave]}",
                                 'values': [linha]})
        else:
            novas.append(linha)
    if atualizacoes:
        sheets.spreadsheets().values().batchUpdate(
            spreadsheetId=sid,
            body={'valueInputOption': 'RAW', 'data': atualizacoes}).execute()
    if novas:
        sheets.spreadsheets().values().append(
            spreadsheetId=sid, range=f"'{aba}'!A1", valueInputOption='RAW',
            insertDataOption='INSERT_ROWS', body={'values': novas}).execute()
    if remover:
        gid = next(s['properties']['sheetId'] for s in sheets.spreadsheets().get(
            spreadsheetId=sid, fields='sheets.properties').execute()['sheets']
            if s['properties']['title'] == aba)
        # de baixo para cima, para o indice das linhas de cima nao andar
        pedidos = [{'deleteDimension': {'range': {'sheetId': gid, 'dimension': 'ROWS',
                                                  'startIndex': l - 1, 'endIndex': l}}}
                   for l in sorted(remover, reverse=True)]
        sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={'requests': pedidos}).execute()
    return len(atualizacoes), len(novas), len(remover), mantidas


def rodar(de, ate, gravar=False):
    cache = _cache()
    protocolos, despachos = coletar(de, ate)
    linhas_p, linhas_d = montar(protocolos, despachos, cache)
    _salvar_cache(cache)

    resultado = {'protocolos': linhas_p, 'despachos': linhas_d, 'periodo': (de, ate)}
    if not gravar:
        resultado['planilha'] = None
        return resultado

    drive, sheets = _servicos()
    pasta_id = _pasta(drive)
    existentes = g._listar(
        drive, f"'{pasta_id}' in parents and name = '{g._escapar(NOME_PLANILHA)}' and trashed = false",
        limite=1)
    sid = existentes[0]['id'] if existentes else _criar(drive, sheets, pasta_id)
    (resultado['atualizadas_p'], resultado['novas_p'],
     resultado['removidas_p'], resultado['mantidas_p']) = _upsert(
        sheets, sid, ABA_PROTOCOLOS, CAB_PROTOCOLOS, linhas_p, 10, periodo=(de, ate))
    resultado['atualizadas_d'], resultado['novas_d'], _, _ = _upsert(
        sheets, sid, ABA_DESPACHOS, CAB_DESPACHOS, linhas_d, 9)
    resultado['planilha'] = f'https://docs.google.com/spreadsheets/d/{sid}/edit'
    return resultado


def relatorio(resultado):
    de, ate = resultado['periodo']
    linhas = [f"CONTROLE DE DESPACHOS — {de} a {ate}",
              f"  {len(resultado['protocolos'])} protocolo(s)-gatilho (inicial/agravo/embargos)",
              f"  {len(resultado['despachos'])} tarefa(s) de despacho"]
    sem = [p for p in resultado['protocolos'] if p[6] == 'SEM DESPACHO']
    fora = [p for p in resultado['protocolos'] if p[9] == 'nao']
    if sem:
        linhas.append(f"  ATENCAO: {len(sem)} protocolo(s) sem nenhuma tarefa de despacho:")
        for p in sem:
            linhas.append(f"     {p[0]} | {p[1]} | {p[2]} | {p[3][:40]}")
    if fora:
        linhas.append(f"  {len(fora)} agendamento(s) fora do 1 dia util do POP-CJ-DESP-001")
    if resultado.get('planilha'):
        linhas.append(f"  Planilha: {resultado['planilha']}")
        linhas.append(f"  (+{resultado.get('novas_p',0)} protocolos, +{resultado.get('novas_d',0)} despachos; "
                      f"{resultado.get('atualizadas_p',0)}/{resultado.get('atualizadas_d',0)} atualizados)")
        if resultado.get('removidas_p'):
            linhas.append(f"  {resultado['removidas_p']} protocolo(s) removido(s): a controller nao concluiu a tarefa")
        for r in resultado.get('mantidas_p') or []:
            linhas.append(f"  MANTIDO (tem anotacao da equipe, conferir): {r[0]} | {r[1]} | {r[2]} | {r[3][:40]}")
    return '\n'.join(linhas)
