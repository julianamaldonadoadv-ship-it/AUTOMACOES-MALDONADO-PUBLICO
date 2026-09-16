# -*- coding: utf-8 -*-
"""
Planilha do KPI de exito - uma por competencia, com o mes aberto por semana
==========================================================================

Pedido da Dra. Juliana (15/09/2026): "uma unica planilha em que eu consiga ver
os resultados de setembro, por semana". Os PDFs do `kpi --pdf` continuam
existindo para circular; a planilha e' o painel de acompanhamento do mes.

Uma planilha por competencia ("KPI DE EXITO - SETEMBRO 2026"), na pasta do
Drive indicada pela GJ (`config/equipe.py` -> KPI_PLANILHA_PASTA_ID). Cada rodada
REESCREVE as abas com a apuracao acumulada do mes - a taxa so faz sentido
acumulada, e reescrever evita linha duplicada quando a mesma decisao volta.

Abas:
  POR SEMANA     carteira rural e carteira diversa em blocos SEPARADOS, uma
                 linha por semana + o mes; KPI 1, 2 e 3 e o total de cada
                 carteira. Regra da GJ (14/09/2026): a taxa e' sempre ponderada
                 por carteira, nunca somando as duas.
  POR ADVOGADO   taxa de cada advogado por semana e no mes, dentro de cada
                 carteira, com a quebra por KPI do mes.
  DECISOES       uma linha por decisao que entrou na taxa (e' a base das duas
                 abas acima).
  A CONFERIR     decisoes dentro do escopo que ainda dependem da GJ.

As taxas das duas primeiras abas sao FORMULAS (SOMASES sobre DECISOES): quem
abre a planilha confere cada numero celula por celula, sem precisar confiar no
script. Somente a planilha e' gravada; ADVBOX e DJEN seguem so leitura.
"""
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

import kpi_exito

try:
    import equipe
except ImportError:
    equipe = None

MESES = ['JANEIRO', 'FEVEREIRO', 'MARCO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO',
         'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']
KPIS = ('KPI 1', 'KPI 2', 'KPI 3')
CARTEIRAS = (('rural', 'CARTEIRA RURAL (indicador oficial da Presidencia)'),
             ('diversa', 'CARTEIRA DIVERSA (Regulamento de Bonificacao - a parte)'))
META = 0.20

CAB_DECISOES = ['Data', 'Semana', 'Cliente', 'Processo', 'Advogado', 'Carteira', 'KPI',
                'Resultado', 'Peso', 'Favoravel', 'Contribuicao', 'Confianca',
                'Decisao da GJ', 'Dispositivo lido', 'Orgao', 'Link DJEN']
# colunas de DECISOES usadas nas formulas (letras fixas - mudar CAB_DECISOES
# exige mudar aqui)
COL = {'semana': 'B', 'advogado': 'E', 'carteira': 'F', 'kpi': 'G',
       'peso': 'I', 'contrib': 'K'}


# ------------------------------------------------------------------ semanas

def semanas_da_competencia(ano, mes):
    """[(rotulo, inicio, fim)] - semana de segunda a domingo, numerada a partir da
    que contem o dia 1o (mesma regra de kpi_exito.numerar_semanas). A primeira e
    a ultima podem ser parciais, porque a competencia comeca no dia 1o."""
    ini = date(ano, mes, 1)
    ultimo = (date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))
    out, n, cur = [], 1, ini
    while cur <= ultimo:
        fim = min(cur + timedelta(days=6 - cur.weekday()), ultimo)
        out.append((f'Semana {n:02d}', cur, fim))
        cur, n = fim + timedelta(days=1), n + 1
    return out


def _rotulo_semana(data_iso, semanas):
    d = datetime.strptime(str(data_iso)[:10], '%Y-%m-%d').date()
    for rot, ini, fim in semanas:
        if ini <= d <= fim:
            return rot
    return ''


# ------------------------------------------------------------------ montagem

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return ''


def montar_decisoes(linhas, semanas):
    apur = kpi_exito.apurar(linhas)
    comp = sorted(apur['computadas'], key=lambda l: (str(l.get('data')), l.get('carteira') or '',
                                                      l.get('advogado_responsavel') or ''))
    dec = [CAB_DECISOES]
    for l in comp:
        dec.append([
            str(l.get('data'))[:10], _rotulo_semana(l.get('data'), semanas),
            l.get('cliente') or '', l.get('processo') or '', l.get('advogado_responsavel') or '',
            l.get('carteira') or '', l.get('kpi') or '', l.get('resultado') or '',
            _num(l.get('peso')), _num(l.get('favoravel')), _num(l.get('contribuicao')),
            l.get('confianca') or '', l.get('decisao_gj') or '',
            (l.get('evidencia') or '')[:300], l.get('orgao') or '', l.get('link_djen') or '',
        ])
    conferir = [['Data', 'Semana', 'Cliente', 'Processo', 'Advogado', 'Carteira', 'KPI',
                 'Proposta da automacao', 'O que falta', 'Link DJEN']]
    pend = list(apur['pendentes']) + [l for l in comp if l.get('confirmar_resultado') in (True, 'True')]
    for l in sorted(pend, key=lambda l: str(l.get('data'))):
        conferir.append([
            str(l.get('data'))[:10], _rotulo_semana(l.get('data'), semanas),
            l.get('cliente') or '', l.get('processo') or '', l.get('advogado_responsavel') or '',
            l.get('carteira') or '', l.get('kpi') or '', l.get('resultado') or '(sem resultado)',
            (l.get('evidencia') or l.get('kpi_motivo') or '')[:300], l.get('link_djen') or '',
        ])
    return dec, conferir, apur


# A planilha nasce em pt_BR (virgula decimal) e, nesse locale, o Sheets so aceita
# `;` como separador de argumento - com `,` toda formula vira #ERROR! (foi o que
# aconteceu na primeira publicacao, 15/09/2026).
SEP = ';'


def _somases(col, criterios):
    """SUMIFS sobre DECISOES. criterios = [(coluna, valor)]."""
    faixa = f"DECISOES!${COL[col]}$2:${COL[col]}$2000"
    partes = [faixa] + [f'DECISOES!${COL[c]}$2:${COL[c]}$2000{SEP}"{v}"' for c, v in criterios]
    return 'SUMIFS(' + SEP.join(partes) + ')'


def _contses(criterios):
    return 'COUNTIFS(' + SEP.join(f'DECISOES!${COL[c]}$2:${COL[c]}$2000{SEP}"{v}"'
                                  for c, v in criterios) + ')'


def _taxa(num, den):
    return f'=IF({den}=0{SEP}"-"{SEP}{num}/{den})'


def montar_por_semana(semanas, nome_mes, periodo):
    """Blocos por carteira; linhas = semanas + mes; formulas sobre DECISOES."""
    linhas = [[f'KPI DE EXITO JURIDICO - {nome_mes}', '', f'Apurado de {periodo}'],
              ['Taxa = soma(peso x favoravel) / soma(peso), sempre por carteira. Meta: 20%. '
               'Pesos: KPI 1 = 1,0 | KPI 2 = 0,4 | KPI 3 = 0,5. KPI 4 (acordo) e transito em julgado: lancamento manual da GJ.'],
              []]
    cab = ['Semana', 'Periodo', 'Decisoes',
           'KPI 1 soma', 'KPI 1 peso', 'KPI 1 taxa',
           'KPI 2 soma', 'KPI 2 peso', 'KPI 2 taxa',
           'KPI 3 soma', 'KPI 3 peso', 'KPI 3 taxa',
           'TOTAL soma', 'TOTAL peso', 'TOTAL taxa', 'Meta 20%?']
    faixas_pct, faixas_cab, faixas_total = [], [], []
    for cart, titulo in CARTEIRAS:
        linhas.append([titulo])
        faixas_cab.append(len(linhas) - 1)
        linhas.append(cab)
        faixas_cab.append(len(linhas) - 1)
        itens = [(rot, f"{ini.strftime('%d/%m')} a {fim.strftime('%d/%m')}", [('semana', rot)])
                 for rot, ini, fim in semanas]
        itens.append((f'MES ({nome_mes.split()[0]})', f"{semanas[0][1].strftime('%d/%m')} a {semanas[-1][2].strftime('%d/%m')}", []))
        for rot, per, filtro in itens:
            r = len(linhas) + 1               # linha (1-based) desta linha na aba
            base = filtro + [('carteira', cart)]
            linha = [rot, per, '=' + _contses(base)]
            for k in KPIS:
                c = base + [('kpi', k)]
                linha += ['=' + _somases('contrib', c), '=' + _somases('peso', c), None]
            linha += ['=' + _somases('contrib', base), '=' + _somases('peso', base), None, None]
            # taxas referenciam as celulas vizinhas (soma/peso) - auditavel
            for i, (cn, cd, ct) in enumerate((('D', 'E', 5), ('G', 'H', 8), ('J', 'K', 11), ('M', 'N', 14))):
                linha[ct] = _taxa(f'{cn}{r}', f'{cd}{r}')
            linha[15] = (f'=IF(O{r}="-"{SEP}"-"{SEP}'
                         f'IF(O{r}>={int(META * 100)}%{SEP}"SIM"{SEP}"NAO"))')
            linhas.append(linha)
            faixas_pct.append(len(linhas) - 1)
            if rot.startswith('MES'):
                faixas_total.append(len(linhas) - 1)
        linhas.append([])
    return linhas, faixas_pct, faixas_cab, faixas_total


def montar_por_advogado(apur, semanas, nome_mes):
    linhas = [[f'TAXA POR ADVOGADO - {nome_mes}', '',
               'Base pequena: uma decisao muda a taxa inteira. Serve para acompanhar, nao para avaliar desempenho.'],
              []]
    rots = [s[0] for s in semanas]
    cab = ['Advogado', 'Decisoes'] + [f'{r} taxa' for r in rots] + \
          ['MES soma', 'MES peso', 'MES taxa', 'KPI 1 taxa', 'KPI 2 taxa', 'KPI 3 taxa']
    faixas_pct, faixas_cab = [], []
    for cart, titulo in CARTEIRAS:
        advs = sorted(a for a, cs in apur['por_advogado'].items() if cart in cs)
        if not advs:
            continue
        linhas.append([titulo]); faixas_cab.append(len(linhas) - 1)
        linhas.append(cab); faixas_cab.append(len(linhas) - 1)
        for adv in advs:
            base = [('advogado', adv), ('carteira', cart)]
            linha = [adv, '=' + _contses(base)]
            for rot in rots:
                c = base + [('semana', rot)]
                linha.append(_taxa(_somases('contrib', c), _somases('peso', c)))
            r = len(linhas) + 1
            n = len(rots)
            col_soma = chr(ord('C') + n)
            col_peso = chr(ord('C') + n + 1)
            linha += ['=' + _somases('contrib', base), '=' + _somases('peso', base),
                      _taxa(f'{col_soma}{r}', f'{col_peso}{r}')]
            for k in KPIS:
                c = base + [('kpi', k)]
                linha.append(_taxa(_somases('contrib', c), _somases('peso', c)))
            linhas.append(linha)
            faixas_pct.append(len(linhas) - 1)
        linhas.append([])
    return linhas, faixas_pct, faixas_cab, len(rots)


# ------------------------------------------------------------------ Drive/Sheets

def _servicos():
    import google_integration as g
    import planilha_conferencia as pc
    drive, _ = g.autenticar_google()
    return g, drive, pc._sheets()


def _achar_ou_criar(g, drive, sheets, nome, pasta_id):
    existentes = g._listar(
        drive, f"'{pasta_id}' in parents and name = '{g._escapar(nome)}' and trashed = false", limite=1)
    if existentes:
        return existentes[0]['id'], False
    corpo = {'properties': {'title': nome, 'locale': 'pt_BR', 'timeZone': 'America/Porto_Velho'},
             'sheets': [{'properties': {'title': t}} for t in
                        ('POR SEMANA', 'POR ADVOGADO', 'DECISOES', 'A CONFERIR')]}
    sid = sheets.spreadsheets().create(body=corpo, fields='spreadsheetId').execute()['spreadsheetId']
    atual = drive.files().get(fileId=sid, fields='parents', supportsAllDrives=True).execute()
    drive.files().update(fileId=sid, addParents=pasta_id,
                         removeParents=','.join(atual.get('parents', [])),
                         supportsAllDrives=True).execute()
    return sid, True


def _formatar(sheets, sid, gids, por_semana, por_adv, n_semanas, n_dec, n_conf):
    cinza = {'red': .93, 'green': .93, 'blue': .93}
    verde = {'red': .85, 'green': .92, 'blue': .83}
    pct = {'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}}
    dec2 = {'numberFormat': {'type': 'NUMBER', 'pattern': '0.00'}}
    req = []

    def celula(gid, r0, r1, c0, c1, fmt, campos):
        req.append({'repeatCell': {'range': {'sheetId': gid, 'startRowIndex': r0, 'endRowIndex': r1,
                                             'startColumnIndex': c0, 'endColumnIndex': c1},
                                   'cell': {'userEnteredFormat': fmt}, 'fields': campos}})

    # POR SEMANA
    g0 = gids['POR SEMANA']
    _, faixas_pct, faixas_cab, faixas_total = por_semana
    celula(g0, 0, 1, 0, 3, {'textFormat': {'bold': True, 'fontSize': 13}}, 'userEnteredFormat.textFormat')
    for r in faixas_cab:
        celula(g0, r, r + 1, 0, 16, {'textFormat': {'bold': True}, 'backgroundColor': cinza},
               'userEnteredFormat(textFormat,backgroundColor)')
    for r in faixas_pct:
        for c in (3, 4, 6, 7, 9, 10, 12, 13):
            celula(g0, r, r + 1, c, c + 1, dec2, 'userEnteredFormat.numberFormat')
        for c in (5, 8, 11, 14):
            celula(g0, r, r + 1, c, c + 1, pct, 'userEnteredFormat.numberFormat')
    for r in faixas_total:
        celula(g0, r, r + 1, 0, 16, {'textFormat': {'bold': True}, 'backgroundColor': verde},
               'userEnteredFormat(textFormat,backgroundColor)')
    # POR ADVOGADO
    g1 = gids['POR ADVOGADO']
    _, faixas_pct_a, faixas_cab_a, _ = por_adv
    celula(g1, 0, 1, 0, 3, {'textFormat': {'bold': True, 'fontSize': 13}}, 'userEnteredFormat.textFormat')
    for r in faixas_cab_a:
        celula(g1, r, r + 1, 0, 8 + n_semanas, {'textFormat': {'bold': True}, 'backgroundColor': cinza},
               'userEnteredFormat(textFormat,backgroundColor)')
    for r in faixas_pct_a:
        celula(g1, r, r + 1, 2, 2 + n_semanas, pct, 'userEnteredFormat.numberFormat')
        celula(g1, r, r + 1, 2 + n_semanas, 4 + n_semanas, dec2, 'userEnteredFormat.numberFormat')
        celula(g1, r, r + 1, 4 + n_semanas, 8 + n_semanas, pct, 'userEnteredFormat.numberFormat')
    # DECISOES / A CONFERIR: cabecalho congelado
    for aba in ('DECISOES', 'A CONFERIR'):
        celula(gids[aba], 0, 1, 0, 16, {'textFormat': {'bold': True}, 'backgroundColor': cinza},
               'userEnteredFormat(textFormat,backgroundColor)')
        req.append({'updateSheetProperties': {'properties': {'sheetId': gids[aba],
                    'gridProperties': {'frozenRowCount': 1}}, 'fields': 'gridProperties.frozenRowCount'}})
    for aba in ('POR SEMANA', 'POR ADVOGADO', 'DECISOES', 'A CONFERIR'):
        req.append({'autoResizeDimensions': {'dimensions': {'sheetId': gids[aba], 'dimension': 'COLUMNS',
                                                            'startIndex': 0, 'endIndex': 18}}})
    sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={'requests': req}).execute()


def publicar(linhas, inicio, fim, pasta_id=None):
    """Reescreve a planilha da competencia de `inicio` com a apuracao de `linhas`.

    `linhas` sao as de kpi_exito.avaliar_lote() JA com as decisoes da GJ
    aplicadas. Devolve (link, n_decisoes, n_a_conferir, criada)."""
    pasta_id = pasta_id or (getattr(equipe, 'KPI_PLANILHA_PASTA_ID', None) if equipe else None)
    if not pasta_id:
        raise RuntimeError('KPI_PLANILHA_PASTA_ID nao configurado em config/equipe.py')
    nome_mes = f'{MESES[inicio.month - 1]} {inicio.year}'
    nome = f'KPI DE EXITO - {nome_mes}'
    semanas = semanas_da_competencia(inicio.year, inicio.month)
    periodo = f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"

    dec, conferir, apur = montar_decisoes(linhas, semanas)
    por_semana = montar_por_semana(semanas, nome_mes, periodo)
    por_adv = montar_por_advogado(apur, semanas, nome_mes)

    g, drive, sheets = _servicos()
    sid, criada = _achar_ou_criar(g, drive, sheets, nome, pasta_id)
    metas = sheets.spreadsheets().get(spreadsheetId=sid).execute()['sheets']
    gids = {s['properties']['title']: s['properties']['sheetId'] for s in metas}
    faltam = [t for t in ('POR SEMANA', 'POR ADVOGADO', 'DECISOES', 'A CONFERIR') if t not in gids]
    if faltam:
        sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={'requests': [
            {'addSheet': {'properties': {'title': t}}} for t in faltam]}).execute()
        metas = sheets.spreadsheets().get(spreadsheetId=sid).execute()['sheets']
        gids = {s['properties']['title']: s['properties']['sheetId'] for s in metas}

    for aba in ('POR SEMANA', 'POR ADVOGADO', 'DECISOES', 'A CONFERIR'):
        sheets.spreadsheets().values().clear(spreadsheetId=sid, range=f"'{aba}'!A1:Z3000").execute()
    sheets.spreadsheets().values().batchUpdate(spreadsheetId=sid, body={
        'valueInputOption': 'USER_ENTERED', 'data': [
            {'range': "'DECISOES'!A1", 'values': dec},
            {'range': "'A CONFERIR'!A1", 'values': conferir},
            {'range': "'POR SEMANA'!A1", 'values': [[c if c is not None else '' for c in l] for l in por_semana[0]]},
            {'range': "'POR ADVOGADO'!A1", 'values': por_adv[0]},
        ]}).execute()
    _formatar(sheets, sid, gids, por_semana, por_adv, len(semanas), len(dec) - 1, len(conferir) - 1)
    return f'https://docs.google.com/spreadsheets/d/{sid}/edit', len(dec) - 1, len(conferir) - 1, criada


# ------------------------------------------------------------------ CLI (a partir de um CSV do kpi)

def _ler_csv(caminho):
    import csv
    linhas = list(csv.DictReader(open(caminho, encoding='utf-8-sig'), delimiter=';'))
    for l in linhas:
        for c in ('peso', 'favoravel', 'contribuicao'):
            l[c] = float(l[c]) if l.get(c) not in (None, '') else None
        l['fora_escopo'] = l.get('fora_escopo') == 'True'
        l['confirmar_resultado'] = l.get('confirmar_resultado') == 'True'
        for c in ('kpi', 'resultado'):
            l[c] = l.get(c) or None
        l.setdefault('polo_evidencia', '')
    return linhas


if __name__ == '__main__':
    # python OPERACIONAL/kpi_planilha.py kpi.csv 2026-09-01 2026-09-15
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    arq, de, ate = sys.argv[1], sys.argv[2], sys.argv[3]
    ini = datetime.strptime(de, '%Y-%m-%d').date()
    fim = datetime.strptime(ate, '%Y-%m-%d').date()
    link, n, nc, criada = publicar(_ler_csv(arq), ini, fim)
    print(f"{'Criada' if criada else 'Atualizada'}: {link}\n  {n} decisao(oes) na taxa | {nc} a conferir")
