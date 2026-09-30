# -*- coding: utf-8 -*-
"""
Briefing estrategico de jurimetria para a peca - foro, tese e caminho ate o STJ
===============================================================================
Antes de redigir (mandamental, cautelar, inicial, recurso), le a base de
julgados (`base_julgados.py`) e devolve o que muda a chance de exito NAQUELE
foro e NAQUELA tese:

  1. O juizo de origem: taxa da vara por tipo de ato, juizes que assinam, e as
     decisoes favoraveis que a propria vara ja deu (precedente do mesmo juizo).
  2. O que derruba a tese ali: termos que aparecem mais nas derrotas que nas
     vitorias, ordenados pela diferenca - e' o que a peca tem de neutralizar
     com prova, nao com argumento.
  3. O 2o grau: gabinetes do tribunal na tese e as ementas favoraveis mais
     recentes (ementario), mais as contrarias recentes para fazer distincao.
  4. O STJ: como a Corte tem decidido a materia e QUAIS OBICES barram o
     recurso (Sumula 7, 5, 211, 283/284, 83) - para a inicial ja nascer com os
     fatos provados por documento e as questoes federais prequestionadas.

    python OPERACIONAL/main.py jurimetria --tese alongamento --comarca Ariquemes
    python OPERACIONAL/main.py jurimetria --tese mora --processo 7001234-56.2026.8.22.0002 --md
    python OPERACIONAL/main.py jurimetria --tese alongamento --comarca "Porto Velho" --tribunal TJRO --peca recurso

Guard-rails (nao desfazer):
- **Estrategia, nao peca.** Nada daqui entra na peca como "perfil do juiz".
  Taxa e sinal de derrota orientam a construcao; o que entra na peca e' prova,
  fundamento e precedente CONFERIDO no inteiro teor.
- **Nao escolhe juiz.** Comarca com varias varas mostra todas: a distribuicao
  e' livre, e a peca tem de funcionar em qualquer uma.
- Tese vem do usuario (mesmas chaves de `anexos_inicial.ACOES`), nunca e'
  adivinhada. Taxa abaixo de `AMOSTRA_MINIMA` sai como amostra insuficiente.
- Somente leitura. Separado do KPI do escritorio (07 - JURIMETRIA).
"""

import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.dirname(__file__))

import base_julgados as base  # noqa: E402
import jurisprudencia as juris  # noqa: E402
import kpi_exito  # noqa: E402

TESES = {
    'alongamento': ('MCR-2.6.4-Alongamento', 'Prorrogação / alongamento (MCR 2-6-4, Súmula 298/STJ)',
                    'Súmula 298'),
    'mora': ('Tema28-STJ-Descaracterizacao-Mora', 'Descaracterização da mora (Tema 28/STJ)',
             'descaracterização da mora'),
    'mora-assistencia': ('Falha-Assistencia-Tecnica-Justica-Federal',
                         'Mora c/c falha na assistência técnica', 'assistência técnica'),
    'revisional': ('Revisional-Contrato-Bancario-Rural', 'Revisional de contrato bancário rural',
                   'cédula rural'),
}

# Tipos de ato que importam para cada peca
PECAS = {
    'inicial': ('liminar', 'sentenca'),        # mandamental / cautelar / declaratoria
    'recurso': ('tutela-recursal', 'acordao', 'monocratica'),
    'embargos': ('liminar', 'sentenca'),
}

# Obices do STJ: o que faz o REsp nao ser conhecido. Contados nas decisoes do
# STJ desfavoraveis ao produtor - dizem o que a inicial precisa preparar.
OBICES_STJ = [
    ('Súmula 7 (reexame de prova)', r'sumula (?:n\.? ?o? ?)?7\b(?!\d)|sumula 7/stj|reexame (?:do conjunto )?(?:fatico|de provas)',
     'Fato decisivo provado por documento desde a inicial (laudo com ART, extratos, requerimento); '
     'a tese para o STJ tem de ser de direito, não de valoração de prova.'),
    ('Súmula 5 (interpretação de cláusula)', r'sumula (?:n\.? ?o? ?)?5\b(?!\d)|interpretacao de clausula',
     'Enquadrar a questão como violação de norma (MCR/lei), não como leitura do contrato.'),
    ('Súmula 211 / 282 / 356 (falta de prequestionamento)', r'sumula (?:n\.? ?o? ?)?211|sumula 282|sumula 356|prequestionamento',
     'Nomear na inicial os dispositivos de lei federal da tese (a skill da tese traz a âncora legal) e opor '
     'ED se o acórdão silenciar (art. 1.025).'),
    ('Súmula 283 / 284 STF (fundamento não atacado / deficiência)', r'sumula 283|sumula 284|fundamentacao deficiente',
     'Atacar todos os fundamentos autônomos da decisão recorrida, cada um com o dispositivo violado.'),
    ('Súmula 83 (acórdão conforme jurisprudência do STJ)', r'sumula (?:n\.? ?o? ?)?83\b',
     'Mostrar distinção do caso ou divergência atual na própria Corte.'),
    ('Súmula 518 / súmula não é lei federal', r'sumula 518|enunciado de sumula nao se enquadra',
     'Nunca apontar só súmula (298, 539, 541) como violada: o REsp precisa de lei federal.'),
]
_OBICES_RX = [(n, re.compile(rx), dica) for n, rx, dica in OBICES_STJ]


# ============================================================
# 1. LOCALIZAR O FORO
# ============================================================

def comarca_de(orgao):
    """'Ariquemes - 3ª Vara Cível' -> 'Ariquemes'."""
    return (orgao or '').split(' - ')[0].strip()


_FORA_DO_CIVEL = re.compile(r'criminal|infancia|familia|execucoes penais|violencia domestica')


def orgaos_da_comarca(julgados, comarca):
    alvo = kpi_exito.normalizar(comarca)
    return sorted({r['orgao'] for r in julgados
                   if r['grau'] == '1o grau' and base.orgao_do_julgado(r)
                   and alvo in kpi_exito.normalizar(r['orgao'])
                   and not _FORA_DO_CIVEL.search(kpi_exito.normalizar(r['orgao']))})


def comarca_do_processo(julgados, processo):
    """Pelo codigo de origem do CNJ (ultimos 4 digitos) - a vara mais frequente na base."""
    digitos = ''.join(filter(str.isdigit, processo or ''))
    if len(digitos) != 20:
        return None
    origem, jtr = digitos[-4:], digitos[13:16]
    cont = Counter()
    for r in julgados:
        d = ''.join(filter(str.isdigit, r['processo'] or ''))
        if len(d) == 20 and d[13:16] == jtr and d[-4:] == origem and r['grau'] == '1o grau':
            cont[comarca_de(r['orgao'])] += 1
    return cont.most_common(1)[0][0] if cont else None


# ============================================================
# 2. MONTAR O BRIEFING
# ============================================================

def _da_tese(julgados, nota):
    # `teses` (lista): ato de alongamento c/c descaracterizacao da mora conta nas duas
    return [r for r in julgados if nota in (r.get('teses') or [r.get('tese')])]


def sinais_de_derrota(xs):
    """[(sinal, n_des, pct_des, n_fav, pct_fav, diferenca)] ordenado pela diferenca."""
    des = [r for r in xs if r['produtor'] == 'desfavoravel']
    fav = [r for r in xs if r['produtor'] in ('favoravel', 'parcial')]
    saida = []
    for s in base.SINAIS:
        nd = sum(1 for r in des if s in r.get('sinais', []))
        nf = sum(1 for r in fav if s in r.get('sinais', []))
        pd = nd / len(des) if des else 0
        pf = nf / len(fav) if fav else 0
        if nd:
            saida.append((s, nd, pd, nf, pf, pd - pf))
    return sorted(saida, key=lambda t: -t[5]), len(des), len(fav)


def obices_stj(con, stj):
    """Obices contados no TEXTO INTEGRAL: a Sumula 7 vem na fundamentacao, nao no dispositivo."""
    import json
    des = [r for r in stj if r['produtor'] == 'desfavoravel']
    textos = {}
    for r in des:
        linha = con.execute('SELECT item_json FROM publicacoes WHERE id=?', (r['id'],)).fetchone()
        textos[r['id']] = kpi_exito.normalizar(json.loads(linha[0]).get('texto') if linha else '')
    cont = []
    for nome, rx, dica in _OBICES_RX:
        n = sum(1 for r in des if rx.search(textos[r['id']]))
        cont.append((nome, n, dica))
    return sorted(cont, key=lambda t: -t[1]), len(des)


def _pct(x):
    return f'{100 * x:.0f}%'


def _linha_julgado(r, com_ementa=True):
    trecho = re.sub(r'\s+', ' ', (r.get('ementa') if com_ementa and r.get('ementa') else r.get('dispositivo')) or '')
    if len(trecho) > 380:
        trecho = trecho[:379] + '…'
    link_ementa = f" · [[{base.nome_ementa(r)}|ementa]]" if r.get('ementa') else ''
    quem = f" · {r['relator']}" if r.get('relator') else ''
    return (f"- {juris.TIPOS.get(r['tipo'], r['tipo'])} · {r['classe']} [{r['processo']}]({r['link']}) · "
            f"DJEN {base._data_br(r['data'])}{quem}{link_ementa}\n  > {trecho}")


def briefing(con, tese, tribunal='TJRO', comarca=None, processo=None, peca='inicial', stj=True):
    nota, rotulo, _termo = TESES[tese]
    todos = base.carregar_julgados(con, tribunal)
    if processo and not comarca:
        comarca = comarca_do_processo(todos, processo)
    tipos = PECAS.get(peca, PECAS['inicial'])
    L = [f'# Briefing de jurimetria: {rotulo}', '',
         f'Tribunal: **{tribunal}** · Foro: **{comarca or "não informado"}** · Peça: **{peca}** · '
         f'gerado em {date.today().strftime("%d/%m/%Y")}', '',
         '> **Uso interno, para construir a peça.** Nada deste briefing entra na petição como perfil de '
         'juiz. O que entra é prova, fundamento e precedente conferido no inteiro teor. Base: decisões de '
         'todas as partes publicadas no DJEN; leitura automática do dispositivo.', '']

    da_tese = _da_tese(todos, nota)
    L += [f'Base do {tribunal} na tese: **{len(da_tese)} atos** '
          f'(taxa favorável ao produtor: **{base._fmt_taxa(base._taxa(da_tese))}**). A tese é marcada pelo texto do '
          'ato (ementa, dispositivo ou objeto): ato que só menciona o MCR ou a Súmula 298 também conta, então a '
          'lista de "favoráveis" pode trazer decisão de outro objeto. Abrir antes de usar.', '']

    # --- 1. Juizo de origem
    if comarca:
        orgaos = orgaos_da_comarca(todos, comarca)
        L += [f'## 1. Juízo de origem: {comarca}', '']
        if not orgaos:
            L += ['Sem ato decisório da comarca na base. Usar o perfil do tribunal (seção 3).', '']
        for o in orgaos:
            xs = [r for r in todos if r['orgao'] == o and base.orgao_do_julgado(r)]
            xt = _da_tese(xs, nota)
            juizes = Counter(r['relator'] for r in xs if r.get('relator')).most_common(3)
            L += [f"### [[{base.vault.nome_do_orgao(tribunal, o)}|{o}]]", '',
                  'Juízes que mais assinaram: ' + (', '.join(f'{n} ({q})' for n, q in juizes) or 'sem assinatura lida'), '',
                  base._CAB_TAXA]
            for t in tipos:
                ys = [r for r in xs if r['tipo'] == t]
                if ys:
                    L.append(base._linha_taxa(f'{juris.TIPOS[t]} (todas as teses)', base._taxa(ys)))
                yt = [r for r in xt if r['tipo'] == t]
                if yt:
                    L.append(base._linha_taxa(f'{juris.TIPOS[t]} (nesta tese)', base._taxa(yt)))
            L.append('')
            fav = sorted((r for r in xt if r['produtor'] in ('favoravel', 'parcial')),
                         key=lambda r: r['data'], reverse=True)[:4]
            if fav:
                L += ['**Decisões favoráveis desta vara na tese** (precedente do próprio juízo; conferir e juntar):', '']
                L += [_linha_julgado(r, com_ementa=False) for r in fav]
                L.append('')
            sin, nd, nf = sinais_de_derrota(xt or xs)
            if sin:
                L += [f'**O que pesa contra aqui** ({nd} derrotas × {nf} vitórias'
                      f'{"" if xt else ", todas as teses"}):', '']
                for s, qd, pd, qf, pf, dif in sin[:5]:
                    if dif > 0:
                        L.append(f'- **{s}**: {_pct(pd)} das derrotas × {_pct(pf)} das vitórias')
                L.append('')

    # --- 2. O que neutralizar na peca (tribunal inteiro, na tese)
    sin, nd, nf = sinais_de_derrota(da_tese)
    L += [f'## 2. O que derruba a tese no {tribunal} e como neutralizar na peça', '',
          f'Diferença entre a frequência nas derrotas ({nd}) e nas vitórias ({nf}). Termo presente no texto é '
          'indício, não motivo lido.', '',
          '| Sinal | Derrotas | Vitórias | Diferença |', '|---|---|---|---|']
    for s, qd, pd, qf, pf, dif in sin:
        L.append(f'| {s} | {_pct(pd)} | {_pct(pf)} | **{"+" if dif >= 0 else ""}{_pct(dif)}** |')
    L += ['', '> Cada sinal com diferença positiva vira item de prova na inicial (ex.: laudo com ART e visita '
          'técnica para "laudo unilateral"; requerimento protocolado ou a tese da desnecessidade para "sem pedido '
          'prévio"; cronograma de capacidade de pagamento para "incapacidade não provada").', '']

    # --- 3. Segundo grau
    seg = [r for r in da_tese if r['grau'] != '1o grau' and base.orgao_do_julgado(r)]
    if seg:
        L += [f'## 3. Segundo grau do {tribunal} na tese', '', '| Gabinete | Atos | Taxa |', '|---|---|---|']
        por_gab = defaultdict(list)
        for r in seg:
            por_gab[r['orgao']].append(r)
        for g, xs in sorted(por_gab.items(), key=lambda kv: -len(kv[1])):
            L.append(f"| [[{base.vault.nome_do_orgao(tribunal, g)}|{g}]] | {len(xs)} | {base._fmt_taxa(base._taxa(xs))} |")
        L.append('')
        fav = sorted((r for r in seg if r.get('ementa') and r['produtor'] in ('favoravel', 'parcial')),
                     key=lambda r: r['data'], reverse=True)[:6]
        contra = sorted((r for r in seg if r.get('ementa') and r['produtor'] == 'desfavoravel'),
                        key=lambda r: r['data'], reverse=True)[:4]
        if fav:
            L += ['**Acórdãos favoráveis mais recentes** (candidatos a citação, conferir inteiro teor):', '']
            L += [_linha_julgado(r) for r in fav]
            L.append('')
        if contra:
            L += ['**Acórdãos contrários mais recentes** (a peça tem de fazer a distinção antes que o juiz os use):', '']
            L += [_linha_julgado(r) for r in contra]
            L.append('')

    # --- 4. STJ
    if stj:
        L += ['## 4. Pensando no STJ', '']
        stj_base = _da_tese(base.carregar_julgados(con, 'STJ'), nota)
        if not stj_base:
            L += ['Base do STJ ainda não coletada: `python OPERACIONAL/main.py base coletar --tribunal STJ`.', '']
        else:
            # A maioria dos recursos no STJ e' do banco: taxa unica mede o banco perdendo
            # recurso, nao a chance do produtor. Separa quem recorreu.
            prod_rec = [r for r in stj_base if r.get('ativo_e_instituicao') is False]
            banco_rec = [r for r in stj_base if r.get('ativo_e_instituicao') is True]
            L += [f'Decisões do STJ na base, nesta tese: **{len(stj_base)}**.', '',
                  '| Quem recorreu | Decisões | Favorável ao produtor |', '|---|---|---|',
                  f'| Produtor (nosso cenário no REsp) | {len(prod_rec)} | **{base._fmt_taxa(base._taxa(prod_rec))}** |',
                  f'| Banco / cooperativa | {len(banco_rec)} | {base._fmt_taxa(base._taxa(banco_rec))} |', '']
            stj_base_obices = prod_rec or stj_base
            obs, nd = obices_stj(con, stj_base_obices)
            L += [f'**Óbices que mais barram o recurso do produtor** ({nd} decisões desfavoráveis):', '',
                  '| Óbice | Decisões | O que a inicial prepara desde já |', '|---|---|---|']
            for nome, n, dica in obs:
                if n:
                    L.append(f'| {nome} | {n} ({_pct(n / nd) if nd else "—"}) | {dica} |')
            L.append('')
            # So o produtor recorrente que ganhou serve de precedente para o nosso REsp;
            # banco que perdeu por "nao conheco" nao ensina nada sobre a tese.
            fav = sorted((r for r in prod_rec if r['produtor'] in ('favoravel', 'parcial')),
                         key=lambda r: r['data'], reverse=True)[:6]
            if fav:
                L += ['**REsp/AREsp do produtor que deram certo** (conferir; ementa transcrita de TJ não é do STJ):', '']
                L += [_linha_julgado(r, com_ementa=False) for r in fav]
                L.append('')
        L += ['**Checklist de prequestionamento na inicial**', '',
              '- [ ] Dispositivos de lei federal nomeados (não só súmula): a skill da tese traz a âncora legal.',
              '- [ ] Fato decisivo provado por documento, não por alegação (evita Súmula 7 lá na frente).',
              '- [ ] Cada fundamento autônomo que o banco pode usar já enfrentado (evita Súmula 283).',
              '- [ ] Pedido de manifestação expressa sobre os dispositivos; ED se a decisão silenciar (arts. 1.022 e 1.025).',
              '']
    return '\n'.join(L), comarca


def salvar(texto, tese, comarca):
    os.makedirs(juris.PASTA_SAIDA, exist_ok=True)
    nome = f"briefing_{tese}_{juris._slug(comarca or 'sem-foro')}_{date.today().isoformat()}.md"
    caminho = os.path.join(juris.PASTA_SAIDA, nome)
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(texto)
    return caminho


def autoteste():
    casos = []
    casos.append(('comarca a partir do orgao', comarca_de('Ariquemes - 3ª Vara Cível') == 'Ariquemes'))
    rx = dict((n, r) for n, r, _ in _OBICES_RX)
    casos.append(('obice Sumula 7', bool(rx['Súmula 7 (reexame de prova)'].search('incide a sumula 7/stj'))))
    casos.append(('Sumula 7 nao casa Sumula 72', not rx['Súmula 7 (reexame de prova)'].search('sumula 72 do stj')))
    js = [{'produtor': 'desfavoravel', 'sinais': ['laudo unilateral']}] * 4 + \
         [{'produtor': 'favoravel', 'sinais': []}] * 4
    sin, nd, nf = sinais_de_derrota(js)
    casos.append(('sinal que so aparece nas derrotas vem primeiro', sin[0][0] == 'laudo unilateral' and sin[0][5] == 1.0))
    js = [{'grau': '1o grau', 'orgao': 'Ariquemes - 3ª Vara Cível', 'processo': '0000051-45.2025.8.22.0002',
           'tribunal': 'TJRO'}]
    casos.append(('comarca pelo codigo de origem do CNJ', comarca_do_processo(js, '7009999-99.2026.8.22.0002') == 'Ariquemes'))
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
    print('Use: python OPERACIONAL/main.py jurimetria --tese alongamento --comarca Ariquemes')
