# -*- coding: utf-8 -*-
"""
Base de julgados e perfil decisorio por orgao (jurimetria) - TJRO primeiro
=========================================================================
Guarda localmente o que o DJEN publica sobre credito rural e bancario, le
cada ato com `jurisprudencia.analisar()` e escreve o perfil de cada orgao
julgador no vault Obsidian - gabinete de desembargador no 2o grau, vara no
1o grau com os juizes que assinaram (decisao da Dra. Juliana, 17/09/2026).

    python OPERACIONAL/main.py base coletar                  # TJRO desde 09/2024, incremental
    python OPERACIONAL/main.py base status
    python OPERACIONAL/main.py base perfil                   # simula as notas
    python OPERACIONAL/main.py base perfil --gravar          # grava (pede s/N)

Onde fica
---------
  _trabalho/jurisprudencia/base_julgados.sqlite   publicacoes cruas + analise
      (gitignored: nome de parte). A base e' a fonte; a nota e' derivada e
      reconstruida inteira a cada rodada, nao fundida.
  BASE_CONHECIMENTO/07 - JURIMETRIA/ORGAOS/<TRIB>/<TRIB - orgao>.md   perfil
  BASE_CONHECIMENTO/07 - JURIMETRIA/EMENTARIO/<TRIB>/<TRIB data sigla processo>.md
  BASE_CONHECIMENTO/07 - JURIMETRIA/_PAINEL-<TRIB>.md e _EMENTARIO-<TRIB>.md
      Pasta PROPRIA, separada de `01 - MAGISTRADOS` (Dra. Juliana, 17/09/2026): jurimetria
      estuda decisoes de todas as partes e nao pode se confundir com o KPI do escritorio.
      A automacao so e' dona do bloco `<!-- inicio:jurimetria -->`; texto humano nunca e' tocado.

Regras e armadilhas (nao desfazer):
- **A API casa palavras soltas.** "credito rural" traz toda publicacao com
  "credito" e "rural" em qualquer lugar; o ato so entra na base analisada se o
  texto tiver marca real do tema (`_MARCAS_TEMA`). "prorrogacao" ficou fora:
  1.329 publicacoes/mes no TJRO, quase tudo prorrogacao de prazo.
- **Mes fechado nao e' recoletado; mes corrente sempre e'.** Mes que voltou
  vazio nao e' dado como completo: e' mais provavel o falso-vazio do DJEN.
- **A analise tem versao** (`VERSAO_ANALISE`). Mudou regra em
  `jurisprudencia.py`? Suba a versao e a base e' relida sem nova coleta.
- **Taxa favoravel = (favoravel + 0,5 x parcial) / (atos com lado lido).**
  "A conferir" nao entra no denominador, e abaixo de `AMOSTRA_MINIMA` a taxa
  sai marcada como amostra insuficiente - nunca como tendencia.
- **Sinais de derrota sao termos presentes no texto, nao motivo lido.** Sai
  sempre a frequencia nas desfavoraveis ao lado da frequencia nas favoraveis:
  termo que aparece igual nas duas nao explica nada.
- **Perfil por orgao, nao por pessoa** (regra do vault). No 2o grau o orgao do
  DJEN ja e' o gabinete do desembargador; acordao publicado sem gabinete no
  `nomeOrgao` nao e' atribuido a ninguem - sobe na contagem "sem orgao".
- Somente leitura no DJEN. So escreve na base local e, com --gravar e "s/N",
  dentro de BASE_CONHECIMENTO/.
"""

import json
import os
import re
import sqlite3
import sys
from collections import Counter, OrderedDict, defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.dirname(__file__))

import comunica_djen  # noqa: E402
import jurisprudencia as juris  # noqa: E402
import kpi_exito  # noqa: E402
import vault_obsidian as vault  # noqa: E402

CAMINHO_BASE = os.path.join(juris.PASTA_SAIDA, 'base_julgados.sqlite')
VERSAO_ANALISE = 13
AMOSTRA_MINIMA = 10
DESDE_PADRAO = '2024-09-01'

TERMOS_PADRAO = ('crédito rural', 'cédula rural', 'alongamento', 'Súmula 298',
                 'descaracterização da mora')

# Sem "produtor rural" / "atividade rural" soltos: a qualificacao da parte
# ("agricultor") levava para a base acao de consumo contra Banco PAN e
# financiamento de veiculo (amostra de 30 atos, 17/09/2026).
_MARCAS_TEMA = re.compile(
    r'credito rural|cedula rural|cedula de produto rural|\bcpr\b|'
    r'manual de credito rural|\bmcr\b|sumula 298|pronaf|pronamp|\bfno\b|'
    r'alongamento d[ae] (?:divida|debito)|prorrogacao d[ae] (?:divida|debito)s? rura|'
    r'financiamento rural|custeio agricola|custeio pecuario')
# "descaracterizacao da mora" saiu da lista de proposito: sozinha, trazia para a
# base milhares de decisoes do STJ sobre financiamento de veiculo (2.454 de 4.301),
# em que o recorrente costuma ser o banco - e o "favoravel ao produtor" inflava.
# A tese da mora so conta em ato com marca de CREDITO RURAL (17/09/2026).

# Tribunal que abrange varios estados: no 1o grau so interessam as varas onde o
# escritorio atua. TRF1 no ADVBOX (17/09/2026): 105 processos na SJRO (4100),
# 15 nas subsecoes de RO (4101-4103), 21 no proprio TRF1, 5 de outros estados.
# O 2o grau entra inteiro - a apelacao de Rondonia vai para qualquer gabinete.
FILTRO_1O_GRAU = {
    'TRF1': r'\bsjro\b|-ro\b|rondonia|porto velho|ji-parana|vilhena|guajara-mirim',
}

MARCA_J_INICIO = '<!-- inicio:jurimetria base_julgados.py - nao editar a mao -->'
MARCA_J_FIM = '<!-- fim:jurimetria -->'

NOTAS_TESE = OrderedDict((nota, rotulo) for nota, rotulo, _ in vault.TESES)

# Termos cuja presenca vale olhar nas decisoes desfavoraveis. Calibrados pelo
# diagnostico de 104 decisoes de alongamento (00 - TEMAS/Diagnostico-Vitorias-
# Derrotas-Alongamento): laudo unilateral foi o 1o motivo de derrota.
SINAIS = OrderedDict([
    ('laudo unilateral', r'laudo[^.]{0,60}(?:unilateral|contratado p(?:or|el)|particular)|'
                         r'prova unilateral|produzid[oa] unilateralmente'),
    ('necessidade de dilação probatória', r'dilacao probatoria|cognicao sumaria|instrucao probatoria'),
    ('sem pedido prévio ao banco', r'(?:ausencia|falta|inexistencia) de (?:previo )?(?:pedido|requerimento|'
                                   r'solicitacao)|previo requerimento administrativo'),
    ('pedido fora do prazo / após o vencimento', r'extemporane|apos o vencimento|depois do vencimento'),
    ('incapacidade de pagamento não provada', r'(?:nao|sem) (?:ha |houve |restou |foi )?'
                                              r'(?:prova|comprova|demonstra)[^.]{0,80}'
                                              r'(?:incapacidade|capacidade de pagamento|frustracao|prejuizo)'),
    ('requisitos do MCR não preenchidos', r'requisitos[^.]{0,80}nao (?:foram )?(?:comprovados|preenchidos|'
                                          r'demonstrados)'),
    ('recursos de fundo (FNO/fundos)', r'\bfno\b|fundo constitucional|recursos de fundos'),
    ('sem garantia do juízo', r'garantia do juizo|juizo (?:nao )?(?:esta )?garantido'),
    ('natureza rural contestada', r'(?:nao|sem)[^.]{0,40}(?:natureza|finalidade|destinacao) rural'),
])
_SINAIS_RX = OrderedDict((k, re.compile(v)) for k, v in SINAIS.items())


# ============================================================
# 1. BASE LOCAL
# ============================================================

def conectar(caminho=CAMINHO_BASE):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    con = sqlite3.connect(caminho)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS publicacoes (
            id INTEGER PRIMARY KEY, tribunal TEXT, data TEXT, processo TEXT,
            item_json TEXT, termos TEXT, coletado_em TEXT);
        CREATE INDEX IF NOT EXISTS ix_pub_trib_data ON publicacoes(tribunal, data);
        CREATE TABLE IF NOT EXISTS coletas (
            tribunal TEXT, termo TEXT, mes TEXT, total INTEGER, completo INTEGER,
            coletado_em TEXT, PRIMARY KEY (tribunal, termo, mes));
        CREATE TABLE IF NOT EXISTS analises (
            id INTEGER PRIMARY KEY, versao INTEGER, relevante INTEGER,
            analise_json TEXT);
    """)
    return con


def coletar(con, tribunal='TJRO', termos=TERMOS_PADRAO, desde=DESDE_PADRAO, ate=None,
            refazer=False, log=print):
    """Baixa as publicacoes mes a mes. Mes fechado e completo nao e' rebaixado."""
    ate = ate or date.today().isoformat()
    hoje = date.today()
    novas_total = 0
    for ini, fim in juris.janelas_mensais(desde, ate):
        mes = ini[:7]
        for termo in termos:
            ja = con.execute('SELECT completo FROM coletas WHERE tribunal=? AND termo=? AND mes=?',
                             (tribunal, termo, mes)).fetchone()
            if ja and ja[0] and not refazer:
                continue
            try:
                itens = comunica_djen.consultar(sigla_tribunal=tribunal, data_inicio=ini,
                                                data_fim=fim, texto=termo, limite=20000)
            except RuntimeError as e:
                log(f'  {mes} "{termo}": AVISO {e}')
                continue
            novas = 0
            for it in itens:
                cur = con.execute('SELECT termos FROM publicacoes WHERE id=?', (it.get('id'),)).fetchone()
                if cur:
                    ts = set(json.loads(cur[0]))
                    if termo not in ts:
                        ts.add(termo)
                        con.execute('UPDATE publicacoes SET termos=? WHERE id=?',
                                    (json.dumps(sorted(ts), ensure_ascii=False), it.get('id')))
                    continue
                con.execute('INSERT INTO publicacoes VALUES (?,?,?,?,?,?,?)',
                            (it.get('id'), (it.get('siglaTribunal') or tribunal).upper(),
                             it.get('data_disponibilizacao'),
                             it.get('numeroprocessocommascara') or it.get('numero_processo'),
                             json.dumps(it, ensure_ascii=False),
                             json.dumps([termo], ensure_ascii=False), hoje.isoformat()))
                novas += 1
            fechado = datetime.strptime(fim, '%Y-%m-%d').date() < hoje - timedelta(days=2)
            completo = int(fechado and len(itens) > 0)
            con.execute('INSERT OR REPLACE INTO coletas VALUES (?,?,?,?,?,?)',
                        (tribunal, termo, mes, len(itens), completo, hoje.isoformat()))
            con.commit()
            novas_total += novas
            log(f'  {mes} "{termo}": {len(itens)} publicacao(oes), {novas} nova(s)'
                + ('' if completo else ' (mes aberto ou vazio: sera recoletado)'))
    return novas_total


def e_do_tema(norm, r):
    """O tema tem de estar no OBJETO do ato, nao citado de passagem.

    "cedula rural pignoraticia" aparece como prova de atividade rural em acao
    contra o INSS e como registro na matricula em promessa de compra e venda -
    nenhuma das duas e' precedente de credito rural (2a amostra, 17/09/2026).
    Vale: no inicio do texto (qualificacao, "trata-se de"), na ementa, no
    dispositivo, ou 3+ vezes no corpo.
    """
    # Previdenciario: "declaracao de aptidao ao Pronaf" e' prova de segurado especial,
    # nao credito rural (TRF1, juizados federais). So entra se o dispositivo ou a
    # ementa tratarem do credito.
    if re.search(r'instituto nacional do seguro social|\binss\b|segurado especial|beneficio previdenciario|'
                 r'aposentadoria por idade rural', norm):
        return any(t and _MARCAS_TEMA.search(kpi_exito.normalizar(t)) for t in (r.get('ementa'), r.get('dispositivo')))
    if _MARCAS_TEMA.search(norm[:2500]):
        return True
    for trecho in (r.get('ementa'), r.get('dispositivo')):
        if trecho and _MARCAS_TEMA.search(kpi_exito.normalizar(trecho)):
            return True
    return len(_MARCAS_TEMA.findall(norm)) >= 3


def teses_do_ato(norm, r):
    """Todas as teses que o ato trata - nao so a unica.

    `inferir_tese` devolve None quando o ato cita duas teses, e e' o caso mais
    comum no escritorio: alongamento pedido junto com descaracterizacao da mora.
    Sem esta lista o ato nao contava em NENHUMA das duas no briefing. Para nao
    pegar citacao de passagem, a marca tem de estar na ementa, no dispositivo ou
    no inicio do ato (objeto), como em `e_do_tema`.
    """
    regiao = ' '.join([norm[:2500], kpi_exito.normalizar(r.get('ementa') or ''),
                       kpi_exito.normalizar(r.get('dispositivo') or '')])
    return [nota for nota, _, marcas in vault.TESES if any(m in regiao for m in marcas)]


def analisar_pendentes(con, log=print):
    """(Re)le toda publicacao sem analise da versao atual."""
    linhas = con.execute("""
        SELECT p.id, p.item_json FROM publicacoes p
        LEFT JOIN analises a ON a.id = p.id
        WHERE a.id IS NULL OR a.versao <> ?""", (VERSAO_ANALISE,)).fetchall()
    for n, (pid, item_json) in enumerate(linhas, 1):
        item = json.loads(item_json)
        r = juris.analisar(item)
        norm = r.pop('_norm')
        relevante = e_do_tema(norm, r) and not r['sem_conteudo']
        tese, _origem, _conf = vault.inferir_tese(norm)
        r['tese'] = tese
        r['teses'] = teses_do_ato(norm, r)
        r['sinais'] = [k for k, rx in _SINAIS_RX.items() if rx.search(norm)]
        r['chave'] = list(juris._chave_dedupe(r))
        con.execute('INSERT OR REPLACE INTO analises VALUES (?,?,?,?)',
                    (pid, VERSAO_ANALISE, int(relevante), json.dumps(r, ensure_ascii=False)))
        if n % 500 == 0:
            con.commit()
            log(f'  analisadas {n}/{len(linhas)}')
    con.commit()
    return len(linhas)


def carregar_julgados(con, tribunal='TJRO', desde=None):
    """Julgados relevantes, um por ato (as copias por destinatario sao fundidas)."""
    sql = """SELECT a.analise_json FROM analises a JOIN publicacoes p ON p.id = a.id
             WHERE a.relevante = 1 AND a.versao = ? AND p.tribunal = ?"""
    params = [VERSAO_ANALISE, tribunal]
    if desde:
        sql += ' AND p.data >= ?'
        params.append(desde)
    vistos = {}
    for (js,) in con.execute(sql, params):
        r = json.loads(js)
        chave = tuple(r['chave'])
        if chave not in vistos or (r['data'] or '') > (vistos[chave]['data'] or ''):
            vistos[chave] = r
    return list(vistos.values())


def status(con):
    pubs = con.execute('SELECT tribunal, COUNT(*), MIN(data), MAX(data) FROM publicacoes GROUP BY tribunal').fetchall()
    rel = con.execute('SELECT COUNT(*), SUM(relevante) FROM analises WHERE versao=?', (VERSAO_ANALISE,)).fetchone()
    abertos = con.execute('SELECT tribunal, termo, mes FROM coletas WHERE completo=0 ORDER BY mes').fetchall()
    return {'publicacoes': pubs, 'analisadas': rel[0] or 0, 'relevantes': rel[1] or 0,
            'meses_abertos': abertos}


# ============================================================
# 2. PERFIL
# ============================================================

def orgao_do_julgado(r):
    """Nome do orgao para o perfil, ou None.

    2o grau: so gabinete ("Gabinete Des. Fulano") - acordao sem gabinete no DJEN
    nao e' atribuido por nome lido no texto (a grafia nao casaria com a nota).
    1o grau: a vara, como o DJEN nomeia.
    """
    orgao = (r.get('orgao') or '').strip()
    if not orgao:
        return None
    if r['grau'] != '1o grau':
        # "Gabinete Des. Fulano" (TJRO) ou "Gab. 15 - DESEMBARGADOR FEDERAL FULANO" (TRF1)
        return orgao if re.match(r'gab(?:inete)?\b\.?', orgao, re.I) else None
    if re.search(r'coordenadoria|central de processos|secretaria|distribui', orgao, re.I):
        return None
    filtro = FILTRO_1O_GRAU.get((r.get('tribunal') or '').upper())
    if filtro and not re.search(filtro, kpi_exito.normalizar(orgao)):
        return None
    return orgao


def _teses(r):
    """Lista de teses do ato (analise v7+); cai para a tese unica das versoes antigas."""
    return r.get('teses') if r.get('teses') is not None else ([r['tese']] if r.get('tese') else [])


def _taxa(julgados):
    fav = sum(1 for r in julgados if r['produtor'] == 'favoravel')
    par = sum(1 for r in julgados if r['produtor'] == 'parcial')
    des = sum(1 for r in julgados if r['produtor'] == 'desfavoravel')
    conf = sum(1 for r in julgados if r['produtor'] == 'a conferir')
    base = fav + par + des
    return {'n': len(julgados), 'fav': fav, 'par': par, 'des': des, 'conf': conf, 'base': base,
            'taxa': (fav + 0.5 * par) / base if base else None}


def _fmt_taxa(t):
    if t['taxa'] is None:
        return '—'
    pct = f"{100 * t['taxa']:.0f}%".replace('.', ',')
    return pct if t['base'] >= AMOSTRA_MINIMA else f'{pct} (amostra insuficiente)'


def _linha_taxa(rotulo, t):
    return f"| {rotulo} | {t['n']} | {t['fav']} | {t['par']} | {t['des']} | {t['conf']} | **{_fmt_taxa(t)}** |"


_CAB_TAXA = ('| | Atos | Favorável | Parcial | Desfavorável | A conferir | Taxa favorável ao produtor |\n'
             '|---|---|---|---|---|---|---|')


def _data_br(iso):
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return iso or '—'


def _destaque(r):
    base = (f"- **{juris.TIPOS.get(r['tipo'], r['tipo'])}** · {r['classe']} "
            f"[{r['processo']}]({r['link']}) · DJEN {_data_br(r['data'])}")
    if r.get('ementa'):
        base += f" · [[{nome_ementa(r)}|ementa]]"
    if r.get('relator') and r['grau'] == '1o grau':
        base += f" · {r['relator']}"
    trecho = r['ementa'] or r['dispositivo'] or ''
    trecho = re.sub(r'\s+', ' ', trecho)
    if len(trecho) > 420:
        trecho = trecho[:419] + '…'
    return base + f"\n  > {trecho}"


def _chave_nome(nome):
    return ' '.join(p for p in kpi_exito.normalizar(nome).split() if p not in vault._CONECTIVOS)


def bloco_perfil(orgao, julgados, grau):
    datas = sorted(r['data'] for r in julgados if r['data'])
    periodo = f'{_data_br(datas[0])} a {_data_br(datas[-1])}' if datas else '—'
    L = ['', '## Perfil decisório — base de julgados do DJEN (jurimetria)', '',
         f'Base: **{len(julgados)} ato(s) decisório(s)** sobre crédito rural e bancário publicados de '
         f'{periodo}, de todas as partes (não só do escritório). O DJEN só ganha volume no TJRO a partir '
         'de 2024: o que vem antes disso é amostra do diário, não do tribunal.', '']

    if grau == '1o grau':
        # Mesma pessoa, grafias diferentes na assinatura ("Marcus Vinicius dos Santos
        # Oliveira" x "Marcus Vinícius dos Santos de Oliveira"): agrupa pelo nome sem
        # acento e sem conectivo, e mostra a grafia mais usada.
        grupos = defaultdict(list)
        for r in julgados:
            if r.get('relator'):
                grupos[_chave_nome(r['relator'])].append(r)
        if grupos:
            L.append('**Magistrado(s) que assinaram nesta vara** (assinatura do ato; conferir):')
            L.append('')
            for _, xs in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
                nome = Counter(r['relator'] for r in xs).most_common(1)[0][0]
                ds = sorted(r['data'] for r in xs)
                L.append(f'- {nome}: {len(xs)} ato(s), de {_data_br(ds[0])} a {_data_br(ds[-1])}')
            sem = sum(1 for r in julgados if not r.get('relator'))
            if sem:
                L.append(f'- sem assinatura reconhecível: {sem} ato(s)')
            L.append('')

    L += ['### Por tipo de ato', '', _CAB_TAXA]
    for tipo, rotulo in juris.TIPOS.items():
        xs = [r for r in julgados if r['tipo'] == tipo]
        if xs:
            L.append(_linha_taxa(rotulo, _taxa(xs)))
    L.append(_linha_taxa('**Todos**', _taxa(julgados)))
    L.append('')

    L += ['### Por tese (palpite pelo texto do ato; ato com duas teses conta nas duas)', '', _CAB_TAXA]
    for nota, rotulo in NOTAS_TESE.items():
        xs = [r for r in julgados if nota in _teses(r)]
        if xs:
            L.append(_linha_taxa(f'[[{nota}\\|{rotulo}]]', _taxa(xs)))
    xs = [r for r in julgados if not _teses(r)]
    if xs:
        L.append(_linha_taxa('tese não identificada', _taxa(xs)))
    L.append('')

    des = [r for r in julgados if r['produtor'] == 'desfavoravel']
    fav = [r for r in julgados if r['produtor'] in ('favoravel', 'parcial')]
    if des:
        L += ['### Termos presentes nas decisões desfavoráveis', '',
              '> Indício, não motivo lido: compare com a coluna das favoráveis.', '',
              '| Termo no texto | Nas desfavoráveis | Nas favoráveis/parciais |', '|---|---|---|']
        for sinal in SINAIS:
            nd = sum(1 for r in des if sinal in r.get('sinais', []))
            nf = sum(1 for r in fav if sinal in r.get('sinais', []))
            if nd:
                pf = f'{nf} de {len(fav)} ({100 * nf / len(fav):.0f}%)' if fav else '—'
                L.append(f'| {sinal} | {nd} de {len(des)} ({100 * nd / len(des):.0f}%) | {pf} |')
        L.append('')

    def recentes(xs, n=3):
        # acordao com ementa primeiro: e' o que se cita; dentro disso, o mais recente
        return sorted(xs, key=lambda r: (r['ementa'] is not None, r['data'] or ''), reverse=True)[:n]

    if fav:
        L += ['### Decisões favoráveis mais recentes', '']
        L += [_destaque(r) for r in recentes(fav)]
        L.append('')
    if des:
        L += ['### Decisões desfavoráveis mais recentes', '']
        L += [_destaque(r) for r in recentes(des)]
        L.append('')

    L += [f'> Gerado por `OPERACIONAL/base_julgados.py` em {date.today().strftime("%d/%m/%Y")}. '
          '**Leitura automática do dispositivo e de quem pediu, não laudo.** Taxa com menos de '
          f'{AMOSTRA_MINIMA} atos lidos não é tendência. Ementa só vai para peça depois de conferida '
          'no inteiro teor.', '']
    return '\n'.join(L)


PASTA_JURIMETRIA = '07 - JURIMETRIA'
_AVISO_SEPARACAO = ('> **Jurimetria, não métrica do escritório.** Esta base lê decisões de **todas as partes** '
                    'publicadas no DJEN para estudar o órgão e o magistrado. Resultado dos nossos casos e KPI '
                    'ficam em `01 - MAGISTRADOS` e `docs/kpi_exito/`; os números não se misturam.')


def _inserir_bloco(atual, bloco):
    """Conteudo com o bloco de jurimetria atualizado, ou None (nota sem marcador: nao tocar)."""
    i, f = atual.find(MARCA_J_INICIO), atual.find(MARCA_J_FIM)
    if i == -1 or f < i:
        return None
    return atual[:i] + MARCA_J_INICIO + bloco + MARCA_J_FIM + atual[f + len(MARCA_J_FIM):]


def _montar(caminho, bloco, esqueleto):
    """(conteudo, status) - a automacao so e' dona do bloco; o resto e' humano."""
    if not os.path.exists(caminho):
        return esqueleto(MARCA_J_INICIO + bloco + MARCA_J_FIM), 'criada'
    atual = open(caminho, encoding='utf-8').read()
    final = _inserir_bloco(atual, bloco)
    if final is None:
        return atual, 'ignorada (sem marcador)'
    if final == atual:
        return atual, 'inalterada'
    return vault._carimbar(final, date.today().isoformat()), 'atualizada'


def _esqueleto_orgao(nome, tribunal, orgao, grau):
    def montar(bloco):
        return '\n'.join([
            '---', 'tipo: jurimetria-orgao', f'tribunal: {tribunal}', f'orgao: "{orgao}"',
            f'grau: {grau}', 'fonte: base_julgados.py (DJEN, todas as partes)',
            f'atualizado_em: {date.today().isoformat()}', '---', '', f'# {nome}', '',
            _AVISO_SEPARACAO, '', bloco, '', '## Leitura humana do perfil',
            '> Tendência, estilo de fundamentação, o que costuma pesar. Nunca estatística fabricada.', '',
            '## Observações práticas', '', f'[[_PAINEL-{tribunal}]] · [[_EMENTARIO-{tribunal}]]', ''])
    return montar


_SIGLAS_CLASSE = (('agravo interno', 'AgInt'), ('agravo de instrumento', 'AI'), ('apelacao', 'AC'),
                  ('embargos de declaracao', 'ED'), ('recurso especial', 'REsp'),
                  ('agravo em recurso especial', 'AREsp'), ('mandado de seguranca', 'MS'))


def nome_ementa(r):
    if r.get('_nome_ementa'):
        return r['_nome_ementa']
    c = kpi_exito.normalizar(r['classe'])
    sigla = next((s_ for chave, s_ in _SIGLAS_CLASSE if chave in c), 'Acórdão')
    return vault.nome_de_arquivo(f"{r['tribunal']} {r['data']} {sigla} {r['processo']}")


def _link_orgao(r, tribunal):
    o = orgao_do_julgado(r)
    return f'[[{vault.nome_do_orgao(tribunal, o)}]]' if o else (r.get('orgao') or '—')


def planejar(julgados, tribunal='TJRO', raiz_vault=vault.VAULT_PADRAO):
    raiz = os.path.join(raiz_vault, PASTA_JURIMETRIA)
    por_orgao = defaultdict(list)
    sem_orgao = 0
    for r in julgados:
        if r['tipo'] == 'admissibilidade':
            continue  # Vice-Presidencia filtrando REsp nao e' perfil do gabinete
        o = orgao_do_julgado(r)
        if o:
            por_orgao[o].append(r)
        else:
            sem_orgao += 1

    plano = []
    for orgao, xs in sorted(por_orgao.items()):
        nome = vault.nome_do_orgao(tribunal, orgao)
        grau = Counter(r['grau'] for r in xs).most_common(1)[0][0]
        caminho = os.path.join(raiz, 'ORGAOS', tribunal, nome + '.md')
        conteudo, status_ = _montar(caminho, bloco_perfil(orgao, xs, grau),
                                    _esqueleto_orgao(nome, tribunal, orgao, grau))
        plano.append({'tipo': 'orgao', 'nome': nome, 'caminho': caminho, 'conteudo': conteudo,
                      'status': status_, 'atos': len(xs), 'grau': grau, 'taxa': _taxa(xs)})

    plano.extend(planejar_ementario(julgados, tribunal, raiz))
    plano.append(_painel(plano, tribunal, raiz, len(julgados), sem_orgao))
    return plano, sem_orgao


# ============================================================
# 2b. EMENTARIO - uma nota por acordao com ementa propria
# ============================================================

_ROT_PRODUTOR = {'favoravel': 'favorável ao produtor', 'desfavoravel': 'desfavorável ao produtor',
                 'parcial': 'parcial', 'a conferir': 'lado a conferir'}


def planejar_ementario(julgados, tribunal, raiz):
    plano = []
    com_ementa = sorted((r for r in julgados if r.get('ementa') and r['tipo'] != 'admissibilidade'),
                        key=lambda r: (r['data'] or '', r['id'] or 0))
    # Dois acordaos do mesmo processo no mesmo dia (agravo interno + AI) davam o
    # mesmo nome, e um sobrescrevia o outro na gravacao (839 -> 838, 17/09/2026).
    usados = Counter()
    for r in com_ementa:
        r.pop('_nome_ementa', None)
        base_nome = nome_ementa(r)
        usados[base_nome] += 1
        r['_nome_ementa'] = base_nome if usados[base_nome] == 1 else f'{base_nome} ({usados[base_nome]})'
    for r in com_ementa:
        nome = nome_ementa(r)
        caminho = os.path.join(raiz, 'EMENTARIO', tribunal, nome + '.md')
        tese = ' · '.join(f'[[{t}]]' for t in _teses(r)) or 'a confirmar'
        bloco = '\n'.join([
            '', f"**{r['classe']} {r['processo']}** · {_link_orgao(r, tribunal)}"
            + (f" · Rel. {r['relator']}" if r.get('relator') else ''),
            f"Publicado no DJEN em {_data_br(r['data'])}"
            + (f" · julgamento {r['data_julgamento']}" if r.get('data_julgamento') else '')
            + f" · [publicação]({r['link']})", '',
            f"**Resultado (leitura automática):** {r['resultado'] or 'não identificado'} para "
            f"{r['recorrente_ou_autor'] or 'parte não identificada'} → **{_ROT_PRODUTOR[r['produtor']]}** "
            f"· **Tese:** {tese}", '',
            '## Ementa', '', f"> *{r['ementa']}*", '>', f"> ***{r['citacao']}***", '',
            '## Dispositivo', '', f"> {re.sub(chr(10), ' ', r['dispositivo'])}", '',
            '> Ementa extraída do DJEN. **Conferir o inteiro teor no tribunal antes de citar.**', ''])

        def esqueleto(b, r=r, nome=nome):
            return '\n'.join([
                '---', 'tipo: ementa', f"tribunal: {r['tribunal']}", f"processo: {r['processo']}",
                f"classe: \"{r['classe']}\"", f"orgao: \"{r.get('orgao') or ''}\"",
                f"relator: \"{r.get('relator') or ''}\"", f"publicado: {r['data']}",
                f"teses: [{', '.join(_teses(r))}]", f"resultado_produtor: {r['produtor']}",
                f"tipo_ato: {r['tipo']}", f'atualizado_em: {date.today().isoformat()}', '---', '',
                f'# {nome}', '', b, '', '## Nota de uso (escritório)',
                '> Onde serve, onde não serve, peças em que já foi citada.', ''])
        conteudo, status_ = _montar(caminho, bloco, esqueleto)
        plano.append({'tipo': 'ementa', 'nome': nome, 'caminho': caminho, 'conteudo': conteudo,
                      'status': status_, 'atos': 1})

    # Indice por tese e resultado
    L = ['', f'**{len(com_ementa)} ementas** de acórdãos do {tribunal} sobre crédito rural e bancário, '
         'extraídas do DJEN. Leitura automática: conferir o inteiro teor antes de citar.', '']
    for nota, rotulo in list(NOTAS_TESE.items()) + [(None, 'Tese não identificada')]:
        xs = [r for r in com_ementa if (nota in _teses(r) if nota else not _teses(r))]
        if not xs:
            continue
        L += [f'## {rotulo} ({len(xs)})', '']
        for prod, titulo in (('favoravel', 'Favoráveis ao produtor'), ('parcial', 'Parciais'),
                             ('desfavoravel', 'Desfavoráveis ao produtor'), ('a conferir', 'Lado a conferir')):
            ys = sorted((r for r in xs if r['produtor'] == prod), key=lambda r: r['data'], reverse=True)
            if not ys:
                continue
            L += [f'### {titulo} ({len(ys)})', '']
            for r in ys:
                resumo = re.sub(r'\s+', ' ', r['ementa'])[:160]
                L.append(f"- [[{nome_ementa(r)}]] · {_link_orgao(r, tribunal)} · {resumo}…")
            L.append('')
    caminho = os.path.join(raiz, f'_EMENTARIO-{tribunal}.md')
    cab = (f'---\ntipo: indice-ementario\ntribunal: {tribunal}\natualizado_em: {date.today().isoformat()}\n'
           f'---\n\n# Ementário — {tribunal}\n\n')
    conteudo, status_ = vault.montar_painel(caminho, '\n'.join(L) + '\n', cab)
    plano.append({'tipo': 'painel', 'nome': f'_EMENTARIO-{tribunal}', 'caminho': caminho,
                  'conteudo': conteudo, 'status': status_, 'atos': len(com_ementa)})
    return plano


def _painel(plano, tribunal, raiz, total, sem_orgao):
    caminho = os.path.join(raiz, f'_PAINEL-{tribunal}.md')
    L = ['', _AVISO_SEPARACAO, '',
         f'Base: **{total}** atos decisórios do {tribunal} sobre crédito rural e bancário, '
         f'**{sem_orgao}** sem órgão atribuível (acórdão publicado sem gabinete, coordenadoria). '
         f'Ementário: [[_EMENTARIO-{tribunal}]].', '']
    for grau, titulo in (('2o grau', 'Gabinetes (2º grau)'), ('1o grau', 'Varas (1º grau)')):
        itens = sorted((p for p in plano if p.get('grau') == grau), key=lambda p: -p['atos'])
        if not itens:
            continue
        L += [f'## {titulo}', '', '| Órgão | Atos | Favorável | Parcial | Desfavorável | Taxa |', '|---|---|---|---|---|---|']
        for p in itens:
            t = p['taxa']
            L.append(f"| [[{p['nome']}]] | {t['n']} | {t['fav']} | {t['par']} | {t['des']} | {_fmt_taxa(t)} |")
        L.append('')
    L.append('> Leitura automática. Órgão com menos de %d atos lidos não tem tendência.' % AMOSTRA_MINIMA)
    cab = (f'---\ntipo: painel-jurimetria\ntribunal: {tribunal}\natualizado_em: {date.today().isoformat()}\n---\n\n'
           f'# Painel de jurimetria — {tribunal}\n\n')
    conteudo, status_ = vault.montar_painel(caminho, '\n'.join(L) + '\n', cab)
    return {'tipo': 'painel', 'nome': f'_PAINEL-{tribunal}', 'caminho': caminho,
            'conteudo': conteudo, 'status': status_, 'atos': total}


_MOD_EMENTA = '## Nota de uso (escritório)\n> Onde serve, onde não serve, peças em que já foi citada.\n'


def _parte_humana_intacta(texto, sub):
    i, f = texto.find(MARCA_J_INICIO), texto.find(MARCA_J_FIM)
    if i == -1 or f < i:
        return False
    fora = texto[:i] + texto[f + len(MARCA_J_FIM):]
    if sub == 'EMENTARIO':
        return fora.rstrip().endswith(_MOD_EMENTA.rstrip())
    pos = fora.find('## Observações práticas')
    return ('> Tendência, estilo de fundamentação, o que costuma pesar. Nunca estatística fabricada.' in fora
            and pos != -1 and fora[pos + len('## Observações práticas'):].strip().startswith('[[_PAINEL'))


def obsoletas(plano, tribunal, raiz_vault=vault.VAULT_PADRAO):
    """Notas da automacao que sairam da base (reanalise) - [(caminho, pode_mover)].

    Sem isto, ementa que a regra nova descartou continuava no vault, fora do indice,
    parecendo valida (98 do TJRO e 537 "do STJ" que eram do TJ de origem, 18/09/2026).
    So move nota cuja parte humana ainda e' o modelo em branco.
    """
    previstos = {p['caminho'] for p in plano}
    saida = []
    for sub in ('ORGAOS', 'EMENTARIO'):
        pasta = os.path.join(raiz_vault, PASTA_JURIMETRIA, sub, tribunal)
        if not os.path.isdir(pasta):
            continue
        for f in sorted(os.listdir(pasta)):
            c = os.path.join(pasta, f)
            if c not in previstos and f.endswith('.md'):
                saida.append((c, sub, _parte_humana_intacta(open(c, encoding='utf-8').read(), sub)))
    return saida


def mover_para_lixeira(itens, tribunal, raiz_vault=vault.VAULT_PADRAO):
    """Move para a lixeira local do Obsidian (.trash) - recuperavel, nunca apaga."""
    import shutil
    lixo = os.path.join(raiz_vault, '.trash', f'{PASTA_JURIMETRIA} (limpeza {date.today().isoformat()})')
    n = 0
    for c, sub, pode in itens:
        if not pode:
            continue
        destino = os.path.join(lixo, sub, tribunal)
        os.makedirs(destino, exist_ok=True)
        shutil.move(c, os.path.join(destino, os.path.basename(c)))
        n += 1
    return n


def imprimir_plano(plano, sem_orgao):
    print('\n' + '-' * 100)
    for p in sorted((p for p in plano if p['tipo'] != 'ementa'), key=lambda x: (x['tipo'] != 'painel', -x['atos'])):
        marca = {'criada': '[+]', 'atualizada': '[~]', 'inalterada': '[=]'}.get(p['status'], '[!]')
        taxa = _fmt_taxa(p['taxa']) if p.get('taxa') else ''
        print(f"  {marca} {p['nome'][:58]:58} {p['status']:24} {p['atos']:5} ato(s)  {taxa}")
    em = Counter(p['status'] for p in plano if p['tipo'] == 'ementa')
    print(f"  [ementario] {sum(em.values())} nota(s) de ementa: " + ', '.join(f'{k} {v}' for k, v in em.items()))
    cont = Counter(p['status'] for p in plano)
    print('-' * 100)
    print('  ' + ' · '.join(f'{k}: {v}' for k, v in cont.items())
          + f' · atos sem orgao atribuivel: {sem_orgao}')


# ============================================================
# 3. AUTOTESTE (escrita no vault - o risco real deste modulo)
# ============================================================

def autoteste():
    casos = []
    nota = _esqueleto_orgao('TJRO - Vara X', 'TJRO', 'Vara X', '1o grau')(MARCA_J_INICIO + 'PERFIL 1' + MARCA_J_FIM)
    humano = nota.replace('## Observações práticas', '## Observações práticas\nTexto da Dra. Juliana.')
    de_novo = _inserir_bloco(humano, 'PERFIL 2')
    casos.append(('segunda rodada substitui, nao duplica',
                  de_novo.count(MARCA_J_INICIO) == 1 and 'PERFIL 2' in de_novo and 'PERFIL 1' not in de_novo))
    casos.append(('texto humano preservado', 'Texto da Dra. Juliana.' in de_novo))
    casos.append(('nota sem marcador nao e tocada (inclusive nota do KPI em 01 - MAGISTRADOS)',
                  _inserir_bloco(vault.nota_orgao_nova('X', 'TJRO', 'TJRO', vault.bloco_orgao([])), 'x') is None))
    casos.append(('aviso de separacao do KPI na nota', 'não métrica do escritório' in nota))
    casos.append(('nome da ementa com data e sigla',
                  nome_ementa({'tribunal': 'TJRO', 'data': '2026-09-16', 'classe': 'Apelação Cível',
                               'processo': '0000038-73.2026.8.22.0014'}) == 'TJRO 2026-09-16 AC 0000038-73.2026.8.22.0014'))

    j = [{'produtor': 'favoravel'}] * 3 + [{'produtor': 'parcial'}] * 2 + \
        [{'produtor': 'desfavoravel'}] * 5 + [{'produtor': 'a conferir'}] * 4
    t = _taxa(j)
    casos.append(('taxa: a conferir fora do denominador', t['base'] == 10 and abs(t['taxa'] - 0.4) < 1e-9))
    casos.append(('amostra minima marcada', 'insuficiente' in _fmt_taxa(_taxa(j[:9]))))
    casos.append(('2o grau sem gabinete nao e atribuido',
                  orgao_do_julgado({'orgao': 'Coordenadoria Cível do 2º Grau', 'grau': '2o grau'}) is None))
    casos.append(('gabinete e o orgao do 2o grau',
                  orgao_do_julgado({'orgao': 'Gabinete Des. Raduan Miguel', 'grau': '2o grau'})
                  == 'Gabinete Des. Raduan Miguel'))
    casos.append(('tema citado de passagem no meio nao entra',
                  not e_do_tema('x' * 3000 + ' prova: cedula rural pignoraticia no 40 ' + 'y' * 2000,
                                {'ementa': None, 'dispositivo': 'julgo procedente o beneficio'})))
    casos.append(('tema no dispositivo entra',
                  e_do_tema('x' * 3000, {'ementa': None, 'dispositivo': 'alongamento da divida rural'})))
    casos.append(('mesmo juiz com grafias diferentes vira uma chave',
                  _chave_nome('Marcus Vinícius dos Santos de Oliveira') == _chave_nome('Marcus Vinicius dos Santos Oliveira')))
    casos.append(('TRF1: gabinete "Gab. 15 - DESEMBARGADOR FEDERAL" e orgao do 2o grau',
                  orgao_do_julgado({'orgao': 'Gab. 15 - DESEMBARGADOR FEDERAL ALEXANDRE VASCONCELOS',
                                    'grau': '2o grau', 'tribunal': 'TRF1'}) is not None))
    casos.append(('TRF1: vara de Goias fora, vara de Rondonia dentro',
                  orgao_do_julgado({'orgao': '4ª Vara Federal Cível da SJGO', 'grau': '1o grau', 'tribunal': 'TRF1'}) is None
                  and orgao_do_julgado({'orgao': 'Vara Federal Cível e Criminal da SSJ de Ji-Paraná-RO',
                                        'grau': '1o grau', 'tribunal': 'TRF1'}) is not None))
    casos.append(('descaracterizacao da mora sem credito rural nao entra (veiculo)',
                  not e_do_tema('descaracterizacao da mora em contrato de financiamento de veiculo',
                                {'ementa': None, 'dispositivo': ''})))
    casos.append(('INSS com Pronaf como prova de segurado especial nao entra',
                  not e_do_tema('reu: instituto nacional do seguro social - inss. declaracao de aptidao ao pronaf',
                                {'ementa': None, 'dispositivo': 'julgo procedente para conceder aposentadoria'})))
    ementa_nota = '---\n---\n# X\n' + MARCA_J_INICIO + 'x' + MARCA_J_FIM + '\n\n' + _MOD_EMENTA
    casos.append(('nota de ementa sem edicao humana pode ir para a lixeira', _parte_humana_intacta(ementa_nota, 'EMENTARIO')))
    casos.append(('nota de ementa com nota de uso escrita e preservada',
                  not _parte_humana_intacta(ementa_nota + 'Citada na peça do Cliente R.\n', 'EMENTARIO')))
    casos.append(('tema: credito rural entra, prorrogacao de prazo nao',
                  bool(_MARCAS_TEMA.search('cedula rural pignoraticia')) and
                  not _MARCAS_TEMA.search('defiro a prorrogacao do prazo por 15 dias')))

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
    print('Use: python OPERACIONAL/main.py base coletar|status|perfil  |  --autoteste')
