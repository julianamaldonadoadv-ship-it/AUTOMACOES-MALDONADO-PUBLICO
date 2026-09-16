# -*- coding: utf-8 -*-
"""
Planilha de conferencia da rotina de intimacoes
================================================

Serve a semana de teste combinada com a Dra. Juliana (10/09/2026): a rotina roda
em SIMULACAO, monta tudo o que faria, e as controllers conferem linha a linha
contra o que fariam a mao. Onde divergir, a regra e' corrigida — so depois a
rotina ganha autonomia para gravar.

Duas abas, acumulativas (cada rodada ACRESCENTA linhas, nao apaga as anteriores —
a serie da semana inteira e' o dado que interessa):

  AGENDAMENTOS  uma linha por TAREFA que a rotina criaria
                (nasce em / prazo / para quem), com as colunas de conferencia
                "Confere?" e "Observacao" em branco, para a controller preencher.

  INTIMACOES    uma linha por publicacao capturada: ato, prazos D-5/D-3/fatal,
                controller, advogado, peca necessaria e as pendencias.

A planilha vive em ZEUS > CONTROLADORIA > RELATORIOS DIARIOS.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

import google_integration as g
import prazos

try:
    import equipe
except ImportError:
    equipe = None

NOME_PADRAO = 'CONFERENCIA DA ROTINA DE INTIMACOES'

CABECALHO_AGENDAMENTOS = [
    'Rodada', 'Processo', 'Cliente', 'Tarefa', 'Nasce em', 'Prazo',
    'Para quem', 'Lancada por', 'Confere?', 'Observacao da controller',
]
CABECALHO_INTIMACOES = [
    'Rodada', 'Processo', 'Cliente', 'Tribunal', 'Orgao', 'Tipo de ato',
    'Providencia', 'Peca necessaria', 'Prazo (dias)', 'D-5', 'D-3', 'Prazo fatal',
    'Controller', 'Advogado', 'Regra aplicada', 'Pendencias', 'Link DJEN',
]


def _sheets():
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    creds = Credentials.from_authorized_user_file(
        os.path.join(config_dir, 'token.json'), g.SCOPES)
    return build('sheets', 'v4', credentials=creds)


def _nomes(ids):
    """IDs do ADVBOX -> nomes conhecidos em config/equipe.py (sem ir a API)."""
    if not equipe:
        return ', '.join(str(i) for i in ids)
    mapa = {}
    for chave, dados in (getattr(equipe, 'CONTROLLERS', None) or {}).items():
        if dados.get('id'):
            mapa[dados['id']] = dados.get('nome') or chave
        for e in dados.get('advogados', []):
            if isinstance(e, dict) and e.get('id'):
                mapa[e['id']] = e.get('nome')
    for chave, uid in (getattr(equipe, 'SETOR_PROVAS', None) or {}).items():
        mapa[uid] = chave.replace('_', ' ')
    for chave, uid in (getattr(equipe, 'COMUNICACAO_CLIENTE', None) or {}).items():
        mapa[uid] = chave.replace('_', ' ')
    for papel, uid in (getattr(equipe, 'USUARIOS_ADVBOX', None) or {}).items():
        mapa.setdefault(uid, papel)
    return ', '.join(str(mapa.get(i, i)) for i in ids)


def montar_linhas(resultado):
    """Converte o resultado de rotina_diaria.rodar() nas linhas das duas abas."""
    rodada = resultado['periodo'][1]
    agendamentos, intimacoes = [], []

    for plano in resultado['planos']:
        it = plano['item']
        m = plano.get('marcos') or {}
        rot = plano.get('roteamento') or {}

        for t in plano['tarefas']:
            agendamentos.append([
                rodada, it.get('processo') or '', it.get('cliente') or '',
                t['rotulo'], t.get('start_date') or '', t.get('date_deadline') or '',
                _nomes(t['guests']), _nomes([t['from_id']] if t.get('from_id') else []),
                '', '',
            ])

        intimacoes.append([
            rodada, it.get('processo') or '', it.get('cliente') or '',
            it.get('tribunal') or '', it.get('orgao') or '', it.get('tipo_ato') or '',
            (it.get('providencia_cabivel') or '')[:120],
            it.get('peca_necessaria') or '',
            it.get('prazo_dias_extraido') or '',
            prazos.iso(m.get('d5')) or '', prazos.iso(m.get('d3')) or '',
            prazos.iso(m.get('fatal')) or '',
            rot.get('controller_nome') or '', rot.get('advogado') or '',
            rot.get('regra') or '',
            ' | '.join(plano.get('pendencias') or []),
            it.get('link_djen') or '',
        ])

    return agendamentos, intimacoes


def _pasta_relatorios(drive_service, criar=True):
    caminho = (getattr(equipe, 'RELATORIO_DIARIO_PASTA_ZEUS', None) or
               ['CONTROLADORIA', 'RELATORIOS DIARIOS']) if equipe else \
              ['CONTROLADORIA', 'RELATORIOS DIARIOS']
    pai = g._zeus_id(drive_service)
    for nome in caminho:
        achada = g.buscar_subpasta(drive_service, pai, nome)
        if not achada:
            if not criar:
                return None
            achada = g.criar_pasta(drive_service, nome, pai)
        pai = achada['id'] if isinstance(achada, dict) else achada
    return pai


def _criar_planilha(drive_service, sheets_service, nome, pasta_id):
    corpo = {'properties': {'title': nome},
             'sheets': [{'properties': {'title': 'AGENDAMENTOS'}},
                        {'properties': {'title': 'INTIMACOES'}}]}
    ss = sheets_service.spreadsheets().create(body=corpo, fields='spreadsheetId').execute()
    sid = ss['spreadsheetId']
    # move para a pasta certa da ZEUS
    atual = drive_service.files().get(fileId=sid, fields='parents',
                                      supportsAllDrives=True).execute()
    drive_service.files().update(
        fileId=sid, addParents=pasta_id,
        removeParents=','.join(atual.get('parents', [])),
        supportsAllDrives=True).execute()

    sheets_service.spreadsheets().values().batchUpdate(
        spreadsheetId=sid,
        body={'valueInputOption': 'RAW', 'data': [
            {'range': 'AGENDAMENTOS!A1', 'values': [CABECALHO_AGENDAMENTOS]},
            {'range': 'INTIMACOES!A1', 'values': [CABECALHO_INTIMACOES]},
        ]}).execute()

    # cabecalho em negrito e congelado nas duas abas
    metas = sheets_service.spreadsheets().get(spreadsheetId=sid).execute()['sheets']
    pedidos = []
    for aba in metas:
        gid = aba['properties']['sheetId']
        pedidos += [
            {'repeatCell': {
                'range': {'sheetId': gid, 'startRowIndex': 0, 'endRowIndex': 1},
                'cell': {'userEnteredFormat': {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.93, 'green': 0.93, 'blue': 0.93}}},
                'fields': 'userEnteredFormat(textFormat,backgroundColor)'}},
            {'updateSheetProperties': {
                'properties': {'sheetId': gid, 'gridProperties': {'frozenRowCount': 1}},
                'fields': 'gridProperties.frozenRowCount'}},
        ]
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sid, body={'requests': pedidos}).execute()
    return sid


def publicar(resultado, nome=None, drive_service=None):
    """Cria (ou reaproveita) a planilha da semana e ACRESCENTA a rodada.

    Devolve (spreadsheet_id, link, qtd_agendamentos, qtd_intimacoes).
    """
    nome = nome or NOME_PADRAO
    if drive_service is None:
        drive_service, _ = g.autenticar_google()
    sheets_service = _sheets()

    pasta_id = _pasta_relatorios(drive_service)
    existentes = g._listar(
        drive_service,
        f"'{pasta_id}' in parents and name = '{g._escapar(nome)}' and trashed = false",
        limite=1)
    sid = existentes[0]['id'] if existentes else _criar_planilha(
        drive_service, sheets_service, nome, pasta_id)

    agendamentos, intimacoes = montar_linhas(resultado)
    for aba, linhas in (('AGENDAMENTOS', agendamentos), ('INTIMACOES', intimacoes)):
        if not linhas:
            continue
        sheets_service.spreadsheets().values().append(
            spreadsheetId=sid, range=f'{aba}!A1',
            valueInputOption='RAW', insertDataOption='INSERT_ROWS',
            body={'values': linhas}).execute()

    link = f'https://docs.google.com/spreadsheets/d/{sid}/edit'
    return sid, link, len(agendamentos), len(intimacoes)
