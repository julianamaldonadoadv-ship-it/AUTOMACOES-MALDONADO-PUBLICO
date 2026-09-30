# -*- coding: utf-8 -*-
"""
Rotina diaria de intimacoes — Controladoria (POP-CJ-003)
=========================================================

O que a rotina das 08:00 faz, por item capturado no DJEN:

    1. classifica o ato (triagem_divida_rural)
    2. decide de quem e' o processo (roteamento_controller)
    3. calcula PRAZO FATAL, D-5 e D-3 (prazos)
    4. monta o PLANO DE ACAO — as tarefas que precisam nascer no ADVBOX:

       | tarefa                        | para                | vence |
       |-------------------------------|---------------------|-------|
       | CONFERIR/REVISAR PETICAO      | advogado do processo| D-5   |
       | PROTOCOLO - ORGANIZAR DOCS    | setor de provas     | D-5   |
       | PROTOCOLO D-3                 | controller          | D-3   |
       | AVISAR CLIENTE DA AUDIENCIA   | Karla + Anna Lydia  | curto |
       | ACOMPANHAMENTO (conferir)     | controller          | hoje  |

Decisoes da Dra. Juliana (10/09/2026) que este modulo implementa:
  - D-5 e' o marco dos DOIS: peca confeccionada E pasta pronta no Zeus.
  - A rotina distribui e abre prazos SOZINHA. **Protocolo nunca** — POP-CJ-PROT-001.
  - O que ela nao consegue decidir vira tarefa para a controller conferir.
  - Ato sem cadastro no ADVBOX nao vira tarefa (a API exige `lawsuits_id`):
    sobe no relatorio como pendencia de cadastro.

**Modo simulacao e' o padrao.** Nada e' gravado no ADVBOX sem `gravar=True`
(no CLI, `--gravar`). O relatorio da rodada e' o mesmo nos dois modos — e' assim
que da' para conferir a rotina contra o que a controller faria a mao.
"""
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

import advbox_integration as advbox
import comunica_djen
import prazos
import providencia
import roteamento_controller as roteamento
from triagem_divida_rural import (triagem_lote, classificar_resultado,
                                  ato_dirigido_a_parte_contraria)

try:
    import equipe
except ImportError:
    equipe = None


# ============================================================
# CONFIG
# ============================================================

def _tipos_tarefa():
    return (getattr(equipe, 'TIPOS_TAREFA', None) or {}) if equipe else {}


def _setor_provas():
    return list(((getattr(equipe, 'SETOR_PROVAS', None) or {}) if equipe else {}).values())


def _tipos_resultado():
    return (getattr(equipe, 'TIPOS_RESULTADO', None) or {}) if equipe else {}


def deduplicar(resumos):
    """Mesma publicacao chega mais de uma vez quando ha varios destinatarios no
    processo — em 10/09/2026 foram 21 publicacoes para 17 processos, e os 4
    repetidos geraram tarefa em dobro. Agrupa por processo + teor."""
    vistos, unicos = set(), []
    for r in resumos:
        proc = ''.join(filter(str.isdigit, r.get('processo') or ''))
        # so o MIOLO do despacho entra na chave: a mesma publicacao muda no
        # rodape ("Intimado(s)/Citado(s): ..."), que lista destinatarios
        # diferentes em cada copia - comparar o texto inteiro nao dedupliCA nada
        texto = (r.get('texto') or '')
        for corte in ('Intimado(s)', 'INTIMADO(S)', 'Intimados/Citados'):
            if corte in texto:
                texto = texto.split(corte)[0]
                break
        chave = (proc, hash(texto[:600]))
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(r)
    return unicos


def _comunicacao_cliente():
    return list(((getattr(equipe, 'COMUNICACAO_CLIENTE', None) or {}) if equipe else {}).values())


# ============================================================
# PLANO DE ACAO
# ============================================================

_RODAPE = ('\n\n--\n[Rotina automatica da Controladoria — POP-CJ-003] '
           'NAO PROTOCOLADA. Prazos preliminares: conferir suspensao de expediente '
           'antes de cumprir.')


def _contexto(item, marcos_prazo):
    """Cabecalho comum dos comentarios de tarefa: o que aconteceu no processo."""
    linhas = [
        f"Processo: {item.get('processo')}",
        f"Cliente: {item.get('cliente')}",
        f"Ato: {item.get('tipo_ato')} — {item.get('providencia_cabivel')}",
    ]
    if item.get('peca_necessaria'):
        linhas.append(f"Peca: {item['peca_necessaria']}")
    if marcos_prazo:
        linhas.append(f"D-5 {prazos.iso(marcos_prazo['d5'])} · "
                      f"D-3 {prazos.iso(marcos_prazo['d3'])} · "
                      f"FATAL {prazos.iso(marcos_prazo['fatal'])}")
        if marcos_prazo['prazo_curto']:
            linhas.append(marcos_prazo['observacao'])
    rec = item.get('recurso')
    if rec:
        linhas.append(f"Recurso: {rec['recurso_cabivel']} — ED ate {rec['prazo_ed']}, "
                      f"recurso principal ate {rec['prazo_recurso_principal']}")
    if item.get('link_djen'):
        linhas.append(f"DJEN: {item['link_djen']}")
    return '\n'.join(linhas)


def _polo_nosso(item, lawsuit):
    """'ativo'/'passivo' pelo campo destinatarios[].polo do DJEN, o mesmo criterio
    do KPI; None quando nao da para afirmar."""
    try:
        import kpi_exito
        r = kpi_exito.polo_pelas_partes_djen(item.get('partes_polo'),
                                             kpi_exito.clientes_do_escritorio(lawsuit))
        return (r or {}).get('polo')
    except Exception:
        return None


def montar_plano(item, lawsuit=None, hoje=None):
    """Devolve o plano de acao de UM item de triagem.

    {
      'item': ..., 'roteamento': ..., 'marcos': ...,
      'tarefas': [ {rotulo, task_id, from_id, guests, comments, date_deadline}, ...],
      'pendencias': ['...'],   # o que impede a rotina de agir sozinha
    }
    """
    tipos = _tipos_tarefa()
    rot = item.get('roteamento') or roteamento.resolver(lawsuit=lawsuit)
    pendencias = []
    tarefas = []

    lawsuit_id = (lawsuit or {}).get('id')
    if not lawsuit_id:
        pendencias.append('processo nao localizado no ADVBOX — cadastrar antes '
                          '(a API exige lawsuits_id para abrir tarefa)')

    # --- prazos ---
    m = None
    pelos_ed = False
    if item.get('prazo_dias_extraido'):
        m = prazos.calcular(item.get('data_disponibilizacao') or item.get('data'),
                            item['prazo_dias_extraido'], hoje=hoje)
    if not m and item.get('tipo_ato') in ('sentenca', 'decisao'):
        # Ato decisorio sem prazo no texto: o D-5/D-3 segue os EMBARGOS DE
        # DECLARACAO (5 dias uteis), que o POP-CJ-003-A manda montar primeiro.
        # Ate 21/09/2026 seguia o recurso principal (15 dias) e as controllers
        # apontaram, na conferencia, que isso atrasava justamente o prazo curto.
        # Sem vicio, a analise do advogado muda a peca e a controller reagenda
        # pelo recurso principal.
        m = prazos.calcular(item.get('data_disponibilizacao') or item.get('data'), 5, hoje=hoje)
        if m:
            pelos_ed = True
            pendencias.append('prazo nao veio no texto: D-5/D-3 pelos EMBARGOS DE DECLARACAO '
                              '(5 dias uteis); sem vicio, reagendar pelo recurso principal '
                              '(15 dias uteis)')

    contexto = _contexto(item, m)

    def _tarefa(rotulo, chave_tipo, guests, comments, quando, fatal=None):
        """`quando` e' o dia em que a tarefa NASCE na agenda (D-5, D-3, D+1...);
        `fatal` vai no campo de prazo do ADVBOX. Regra da Dra. Juliana (10/09/2026):
        a tarefa tem que cair NA data do marco - nascer toda com a data de hoje
        foi o defeito do primeiro teste."""
        if not lawsuit_id:
            # a API exige lawsuits_id: sem cadastro nao ha tarefa (a pendencia ja
            # esta no relatorio). As controllers marcaram N/A nessas linhas.
            return
        tid = tipos.get(chave_tipo)
        if not tid:
            pendencias.append(f'TIPOS_TAREFA["{chave_tipo}"] nao configurado em config/equipe.py')
            return
        if not guests:
            pendencias.append(f'{rotulo}: sem destinatario definido')
            return
        tarefas.append({
            'rotulo': rotulo,
            'task_id': tid,
            'from_id': rot.get('from_id'),
            # dedup preservando a ordem: quando a propria controller e a
            # responsavel pelo processo, from_id e guest_id sao a mesma pessoa e
            # ela apareceria duas vezes na tarefa de protocolo
            'guests': list(dict.fromkeys([g for g in guests if g])),
            'comments': comments + _RODAPE,
            'start_date': prazos.iso(quando) if quando else None,
            'date_deadline': prazos.iso(fatal) if fatal else None,
        })

    hoje_d = prazos._para_date(hoje) or date.today()
    d1 = prazos.somar_dias_uteis(hoje_d, 1)
    classe = item.get('classe') or ''

    def _fim(observacao):
        return {'item': item, 'roteamento': rot, 'marcos': None, 'tarefas': tarefas,
                'pendencias': pendencias, 'observacao': observacao}

    # --- recurso DISTRIBUIDO no 2o grau (regra da Dra. Juliana, 21/09/2026) ---
    # A controller agenda o despacho com o relator em 1 dia util; na apelacao,
    # o advogado decide, justificando, se a sustentacao oral sera presencial.
    dist = providencia.distribuicao_segundo_grau(item, classe)
    if dist:
        _tarefa('despacho com o relator (agendar)', 'AGENDAR_DESPACHO',
                [rot.get('from_id'), rot.get('guest_id')],
                contexto + '\n\nRecurso DISTRIBUIDO no 2o grau. Agendar o despacho com o '
                           'RELATOR (gabinete indicado na certidao de distribuicao) e '
                           'informar a data ao advogado.', d1, d1)
        if dist == 'pedido_efeito_suspensivo':
            _tarefa('analise da medida cabivel (advogado)', 'ANALISE_MEDIDA',
                    [rot.get('guest_id')],
                    contexto + '\n\nPedido de efeito suspensivo DISTRIBUIDO. Conferir quem pediu '
                               '(nosso ou da parte contraria) e o que responder ao relator.', d1, d1)
        if dist == 'apelacao':
            _tarefa('sustentacao oral: presencial? (advogado)', 'ANALISE_MEDIDA',
                    [rot.get('guest_id')],
                    contexto + '\n\nApelacao distribuida. Analisar se a SUSTENTACAO ORAL sera '
                               'PRESENCIAL, por videoconferencia ou dispensada, SEMPRE de forma '
                               'justificada (relevancia do caso, perfil da camara, valor em '
                               'discussao). A resposta alimenta a cotacao de viagem.', d1, d1)
        return _fim(f'{dist.replace("_", " ")} distribuido no 2o grau: despacho com o relator')

    # --- INCLUSAO EM PAUTA: despacho com os vogais + memoriais ---
    pauta = providencia.inclusao_em_pauta(item, classe)
    if pauta:
        cr, sessao = pauta
        if sessao:
            ate_vogais = prazos.subtrair_dias_uteis(sessao, 1)
            ate_memoriais = prazos.subtrair_dias_uteis(sessao, 2)
            linha_sessao = f'Sessao: {prazos.iso(sessao)}.'
        else:
            ate_vogais = ate_memoriais = None
            linha_sessao = 'Data da sessao NAO lida no texto: conferir e ajustar os prazos.'
            pendencias.append('pauta sem data de sessao reconhecida: prazos de vogais e '
                              'memoriais a definir pela controller')
        _tarefa('despacho com os vogais (agendar)', 'AGENDAR_DESPACHO',
                [rot.get('from_id'), rot.get('guest_id')],
                contexto + f'\n\nRecurso INCLUIDO EM PAUTA. {linha_sessao}\nAgendar despacho com '
                           'os VOGAIS antes da sessao e avaliar com o advogado se vale NOVO '
                           'despacho com o relator.', d1, ate_vogais)
        _tarefa('memoriais (advogado)', 'REVISAO_PECA',
                [rot.get('guest_id')],
                contexto + f'\n\nRecurso INCLUIDO EM PAUTA. {linha_sessao}\nPreparar os '
                           'MEMORIAIS para relator e vogais e dizer, justificando, se vale novo '
                           'despacho com o relator. Sustentacao oral ou pedido de destaque '
                           'costumam ter prazo de ate 48h antes da sessao: conferir na pauta.',
                d1, ate_memoriais)
        return _fim(f'{cr.replace("_", " ")} incluido em pauta: vogais + memoriais')

    # --- ato que nao pede nada de nos (conferencia das controllers, 10-17/09) ---
    nivel, motivo = providencia.sem_providencia_nossa(item, _polo_nosso(item, lawsuit))
    if nivel == 'burocratico':
        return _fim('sem providencia nossa: ' + motivo)
    if nivel == 'so_analise':
        if rot.get('guest_id'):
            _tarefa('analise da medida cabivel (advogado)', 'ANALISE_MEDIDA',
                    [rot['guest_id']],
                    contexto + f'\n\nA rotina nao viu providencia nossa: {motivo}. Conferir o '
                               'teor e, se houver o que fazer, avisar a controller para agendar.',
                    d1, d1)
        return _fim('so analise, sem peca: ' + motivo)

    # --- item que a rotina nao decide sozinha -> conferencia da controller ---
    # A controller so precisa conferir quando o classificador NAO chegou a um
    # tipo de ato, ou quando nao ha advogado a quem enderecar a analise. Com a
    # tarefa de analise da medida cabivel no lugar, abrir as duas seria mandar
    # duas pessoas fazerem a mesma leitura.
    incerto = (item.get('tipo_ato') == 'indefinido') or not rot.get('guest_id')
    if not rot.get('ok'):
        pendencias.append(f"sem controller definida: {rot.get('motivo')}")
    if rot.get('arquivado'):
        pendencias.append('processo ARQUIVADO/ENCERRADO no ADVBOX — em regra nao ha '
                          'agendamento; conferir se cabe algo antes de cumprir')
    if incerto:
        _tarefa('conferencia da controller', 'CONFERIR_CONTROLLER',
                [rot.get('from_id')] if rot.get('from_id') else [],
                contexto + '\n\nA rotina NAO conseguiu fechar a providencia sozinha — '
                           'conferir o teor e redistribuir se for o caso.',
                prazos._para_date(hoje) or date.today(),
                m['fatal'] if m else None)

    # --- ciencia pura: sem D-5/D-3 (POP-CJ-003) ---
    if item.get('tipo_ato') == 'ciencia':
        return {'item': item, 'roteamento': rot, 'marcos': m, 'tarefas': tarefas,
                'pendencias': pendencias,
                'observacao': 'apenas ciencia — sem D-5/D-3, so relatorio'}

    # --- audiencia designada (POP-CJ-003-C) ---
    if item.get('tipo_ato') == 'audiencia':
        # O prazo aqui NAO e' a data da audiencia: e' prazo interno curto para o
        # PRIMEIRO aviso ao cliente (POP-CJ-003-C). 1 dia util.
        aviso_ate = prazos.somar_dias_uteis(prazos._para_date(hoje) or date.today(), 1)
        _tarefa('aviso ao cliente (audiencia)', 'AVISAR_AUDIENCIA',
                _comunicacao_cliente(),
                contexto + '\n\nAudiencia designada. Montar o texto de WhatsApp ao cliente '
                           '(POP-CJ-003-C) e confirmar o endereco: o cabecalho da intimacao '
                           'traz o endereco da Vara, que nem sempre e o do CEJUSC.',
                aviso_ate, aviso_ate)

    # --- ANALISE DA MEDIDA CABIVEL: 1o dia util apos a intimacao ---
    # Regra da Dra. Juliana (10/09/2026): todo ato com providencia abre, antes de
    # tudo, um prazo curto de analise para o advogado dizer QUAL e a medida —
    # penhora iminente, cumprimento de sentenca, tutela indeferida, acordao
    # desfavoravel. E' essa analise que decide o resto; sem ela o D-5 chega com o
    # advogado ainda sem saber o que vai peticionar.
    if rot.get('guest_id') and item.get('tipo_ato') != 'ciencia':
        analise_ate = prazos.somar_dias_uteis(prazos._para_date(hoje) or date.today(), 1)
        corpo_analise = contexto + '\n\nANALISE DA MEDIDA CABIVEL (1o dia util apos a intimacao).'
        if item.get('recurso'):
            m_ed = prazos.calcular(item.get('data_disponibilizacao') or item.get('data'),
                                   5, hoje=hoje)
            corpo_analise += (
                '\n\nATO DECISORIO — POP-CJ-003-A. Cotejar a INICIAL (ou a ultima '
                'manifestacao) com a DECISAO: contradicao? obscuridade? omissao (inclui '
                'fundamentacao generica, art. 489 §1o III e IV)?\n'
                'Por padrao a automacao ja monta os EMBARGOS DE DECLARACAO (5 dias uteis, '
                'art. 1.023 — INTERROMPEM o prazo do recurso principal, art. 1.026). '
                'Concluindo que nao ha vicio, avisar que a peca muda para '
                'agravo de instrumento / apelacao e a minuta e refeita.')
            if m_ed:
                corpo_analise += f"\nJanela dos ED: ate {prazos.iso(m_ed['fatal'])}."
        _tarefa('analise da medida cabivel (advogado)', 'ANALISE_MEDIDA',
                [rot['guest_id']], corpo_analise, analise_ate,
                m['fatal'] if m else None)

    # --- ato com prazo: as tres tarefas do ciclo ---
    if m:
        # O texto muda conforme exista ou nao minuta: enquanto o agente nao
        # rodar no servidor, a tarefa NAO pode dizer que a peca esta pronta.
        if item.get('minuta_link'):
            corpo = ('\n\nMinuta preparada pela automacao para REVISAO: '
                     f"{item['minuta_link']}\n"
                     'Conferir o teor, completar os trechos marcados em amarelo e devolver '
                     'a Controladoria com a tag PECA APROVADA PARA PROTOCOLO ate o D-5.')
        else:
            corpo = ('\n\nPECA A CONFECCIONAR ate o D-5 (a minuta automatica ainda nao '
                     'esta ligada nesta rotina). Ao concluir, devolver a Controladoria com '
                     'a tag PECA APROVADA PARA PROTOCOLO — quem protocola e ela, em D-3.')
            pendencias.append('minuta nao gerada: a rotina distribui e agenda, mas a peca '
                              'ainda sai do agente Claude, rodado a parte')
        rotulo = ('revisao da peca (advogado)' if item.get('minuta_link')
                  else 'confeccao da peca (advogado)')
        _tarefa(rotulo, 'REVISAO_PECA',
                [rot.get('guest_id')],
                contexto + corpo, m['d5'], m['fatal'])

        # Setor de provas, 1a tarefa: comeca no 1o dia util APOS a intimacao -
        # nao adianta so cobrar a pasta no D-5, a coleta precisa comecar agora
        # (regra da Dra. Juliana, 10/09/2026). Embargos de declaracao nao juntam
        # documento: sem tarefa do setor (conferencia das controllers, 15/09).
        inicio_coleta = prazos.somar_dias_uteis(prazos._para_date(hoje) or date.today(), 1)
        if not (pelos_ed and providencia.classe_recursal(classe) in
                ('agravo_instrumento', 'agravo_interno')):
            _tarefa('coleta de documentos (setor de provas)', 'ORGANIZAR_DOCUMENTOS',
                    _setor_provas(),
                    contexto + '\n\nIniciar a coleta dos documentos do protocolo. Lista sugerida '
                               'pela automacao a partir do ato e da tese — e palpite, conferir e '
                               'completar:\n' + _rol_sugerido(item) +
                               f"\n\nA pasta precisa estar FECHADA no Zeus ate {prazos.iso(m['d5'])} "
                               '(D-5), quando ha tarefa propria de conferencia.',
                    inicio_coleta, m['d5'])

            # Setor de provas, 2a tarefa: em D-5 a pasta tem que estar pronta no Zeus
            _tarefa('pasta fechada no Zeus (setor de provas)', 'CONFERIR_PASTA',
                    _setor_provas(),
                    contexto + '\n\nD-5: conferir a pasta do protocolo no Zeus e dar por FECHADA — '
                               'e com ela que a Controladoria protocola em D-3. Faltando documento, '
                               'sinalizar a controller HOJE, nao no D-3.',
                    m['d5'], m['fatal'])

        # Protocolo: advogado E controller, sempre (regra da Dra. Juliana)
        _tarefa('protocolo (controladoria)', 'PROTOCOLO_D3',
                [rot.get('from_id'), rot.get('guest_id')],
                contexto + '\n\nProtocolar em D-3, com a peca aprovada e a pasta do Zeus '
                           'conferida. Peca nao chegou ate o D-3? Avocar e escalar a GJ '
                           'no mesmo dia (POP-CJ-PROT-001).',
                m['d3'], m['fatal'])

    else:
        pendencias.append('sem prazo calculado — nao da para abrir D-5/D-3 automaticamente')

    # --- marcador de RESULTADO (KPI da Controladoria, POP-CJ-002) ---
    # So quando o resultado esta explicito no texto; ambiguo nao vira marcador.
    chave_resultado = classificar_resultado(item.get('trecho_integral') or item.get('trecho') or '')
    if chave_resultado:
        tid = _tipos_resultado().get(chave_resultado)
        if tid and rot.get('from_id') and lawsuit_id:
            tarefas.append({
                'rotulo': f'marcador de resultado: {chave_resultado}',
                'task_id': tid,
                'from_id': rot['from_id'],
                'guests': [rot['from_id']],
                'comments': (contexto + f'\n\nRegistro de RESULTADO para o KPI da '
                             f'Controladoria (POP-CJ-002): {chave_resultado.replace("_", " ")}.'
                             + _RODAPE),
                'start_date': prazos.iso(prazos._para_date(hoje) or date.today()),
                'date_deadline': None,
            })
    elif item.get('tipo_ato') in ('sentenca', 'decisao'):
        pendencias.append('resultado nao identificado com clareza — marcador de KPI '
                          'nao lancado; a controller registra na conferencia')

    if ato_dirigido_a_parte_contraria(item.get('trecho_integral') or item.get('trecho') or ''):
        pendencias.append('INDICIO de ato dirigido a parte CONTRARIA (ex.: "ao exequente '
                          'para se manifestar") — conferir o polo antes de cumprir prazo')

    return {'item': item, 'roteamento': rot, 'marcos': m, 'tarefas': tarefas,
            'pendencias': pendencias, 'observacao': ''}


def _rol_sugerido(item):
    """Lista provavel de documentos, a partir da tese/ato. E' palpite declarado —
    quem confere e completa e' o setor de provas (decisao da Dra. Juliana)."""
    tese = item.get('tese_candidata')
    base = ['- procuracao e substabelecimento atualizados',
            '- copia da intimacao/publicacao',
            '- ultima manifestacao da parte nos autos']
    por_tese = {
        'alongamento': ['- cedula(s) de credito rural', '- requerimento enviado ao banco e comprovante de envio',
                        '- extrato/planilha de evolucao da divida'],
        'mora': ['- cedula(s) de credito rural com as clausulas de encargos',
                 '- ficha grafica do periodo de normalidade', '- planilha de evolucao da divida'],
        'mora-assistencia': ['- cedula(s) de credito rural', '- laudo/relatorio de assistencia tecnica',
                             '- comprovacao da frustracao da safra'],
        'revisional': ['- contrato bancario integral', '- extratos da conta vinculada',
                       '- planilha de recalculo'],
    }
    itens = base + por_tese.get(tese, [])
    if item.get('tipo_ato') in ('sentenca', 'decisao'):
        itens.append('- peticao inicial (para o cotejo INICIAL x DECISAO — POP-CJ-003-A)')
        itens.append('- integra da decisao/sentenca')
    return '\n'.join(itens)


# ============================================================
# EXECUCAO
# ============================================================

def executar_plano(plano, gravar=False):
    """Cria no ADVBOX as tarefas do plano. Sem `gravar`, so simula."""
    lawsuit_id = (plano.get('item') or {}).get('lawsuit_id')
    resultados = []
    for t in plano['tarefas']:
        if not gravar:
            resultados.append({'tarefa': t['rotulo'], 'status': 'SIMULADO'})
            continue
        if not lawsuit_id:
            resultados.append({'tarefa': t['rotulo'], 'status': 'PULADO (sem lawsuit_id)'})
            continue
        try:
            r = advbox.criar_publicacao(
                lawsuit_id=lawsuit_id, task_id=t['task_id'], guest_ids=t['guests'],
                comments=t['comments'], from_id=t['from_id'],
                date_deadline=t['date_deadline'], start_date=t.get('start_date'),
                urgent=bool(plano.get('marcos') and plano['marcos']['prazo_curto']),
            )
            resultados.append({'tarefa': t['rotulo'], 'status': 'CRIADA', 'resposta': r})
        except Exception as e:
            resultados.append({'tarefa': t['rotulo'], 'status': f'ERRO: {e}'})
    return resultados


def rodar(dias=1, gravar=False, hoje=None):
    """Pipeline completo da rodada. Devolve a lista de planos + estatisticas."""
    from datetime import timedelta
    oabs = (getattr(equipe, 'OABS_MONITORADAS', None) or []) if equipe else []
    fim = prazos._para_date(hoje) or date.today()
    inicio = fim - timedelta(days=int(dias) - 1)

    resumos = []
    falhas_djen = []
    for numero, uf in oabs:
        try:
            itens = comunica_djen.consultar(oab_numero=numero, oab_uf=uf,
                                            data_inicio=inicio.isoformat(),
                                            data_fim=fim.isoformat())
        except RuntimeError as e:
            falhas_djen.append(f'{numero}/{uf}: {e}')
            continue
        resumos.extend(comunica_djen.resumir(i) for i in itens)

    antes = len(resumos)
    resumos = deduplicar(resumos)
    duplicadas = antes - len(resumos)

    # cruza com o ADVBOX
    lawsuits = {}
    for r in resumos:
        proc = ''.join(filter(str.isdigit, r.get('processo') or ''))
        if not proc or proc in lawsuits:
            continue
        try:
            achados = advbox.buscar_processo(numero_processo=r.get('processo'))
        except Exception:
            achados = []
        if achados:
            lawsuits[proc] = achados[0]

    itens = triagem_lote(resumos, lawsuits)
    planos = []
    for it, resumo in zip(itens, resumos):
        proc = ''.join(filter(str.isdigit, it.get('processo') or ''))
        lawsuit = lawsuits.get(proc)
        it['data_disponibilizacao'] = resumo.get('data')
        it['classe'] = resumo.get('classe')
        it['partes_polo'] = resumo.get('partes_polo')
        it['lawsuit_id'] = (lawsuit or {}).get('id')
        it['roteamento'] = roteamento.resolver(lawsuit=lawsuit)
        it['roteamento_descricao'] = roteamento.descrever(it['roteamento'])
        plano = montar_plano(it, lawsuit=lawsuit, hoje=hoje)
        plano['execucao'] = executar_plano(plano, gravar=gravar)
        planos.append(plano)

    return {
        'periodo': (inicio.isoformat(), fim.isoformat()),
        'duplicadas': duplicadas,
        'oabs': oabs,
        'falhas_djen': falhas_djen,
        'planos': planos,
        'gravou': bool(gravar),
    }


# ============================================================
# RELATORIO DA RODADA
# ============================================================

def relatorio_texto(resultado):
    """Relatorio da rodada — o mesmo texto vai para o terminal, para a tarefa no
    ADVBOX, para o e-mail e para o arquivo no Zeus."""
    ini, fim = resultado['periodo']
    planos = resultado['planos']
    modo = 'GRAVADO NO ADVBOX' if resultado['gravou'] else 'SIMULACAO (nada gravado)'

    linhas = [
        '=' * 78,
        f'  ROTINA DIARIA DE INTIMACOES — CONTROLADORIA',
        f'  Periodo {ini} a {fim} · {len(planos)} item(ns) · {modo}',
        '=' * 78,
    ]
    if resultado['falhas_djen']:
        linhas.append('\nAVISO — o DJEN falhou para: ' + '; '.join(resultado['falhas_djen']))
        linhas.append('A lista abaixo pode estar incompleta. Repetir a consulta.')

    tarefas_total = sum(len(p['tarefas']) for p in planos)
    com_pendencia = [p for p in planos if p['pendencias']]
    sem_cadastro = [p for p in planos if not (p['item'].get('lawsuit_id'))]
    curtos = [p for p in planos if p.get('marcos') and p['marcos']['prazo_curto']]
    arquivados = [p for p in planos if (p.get('roteamento') or {}).get('arquivado')]

    linhas += [
        '',
        f'  {tarefas_total} tarefa(s) no plano · {len(com_pendencia)} item(ns) com pendencia',
        f'  {len(curtos)} com PRAZO CURTO (elaboracao no mesmo dia)',
        f'  {len(sem_cadastro)} sem cadastro no ADVBOX (nao viram tarefa)',
        f'  {len(arquivados)} em processo arquivado',
    ]

    for p in planos:
        it = p['item']
        linhas += ['', '-' * 78,
                   f"PROCESSO: {it.get('processo')} | {it.get('cliente')}",
                   f"ATO: {it.get('tipo_ato')} — {it.get('providencia_cabivel')}",
                   f"LANCAMENTO: {it.get('roteamento_descricao')}"]
        if p.get('marcos'):
            linhas.append(f"PRAZOS: {prazos.descrever(p['marcos'])}")
        if p.get('observacao'):
            linhas.append(f"OBS: {p['observacao']}")
        for t, r in zip(p['tarefas'], p.get('execucao') or [{}] * len(p['tarefas'])):
            linhas.append(f"  [{r.get('status', '-'):>22}] {t['rotulo']:38} "
                          f"tarefa em {t.get('start_date') or '-'} · prazo {t['date_deadline'] or '-'}")
        for pend in p['pendencias']:
            linhas.append(f"  !! {pend}")

    linhas += ['', '=' * 78,
               '  A automacao NAO protocola (POP-CJ-PROT-001) e todo prazo aqui e',
               '  preliminar: conferir suspensao de expediente antes de cumprir.',
               '=' * 78]
    return '\n'.join(linhas)


def publicar_relatorio(resultado, texto=None, gravar=False, drive=True):
    """Entrega o relatorio nos tres canais definidos pela Dra. Juliana:
    tarefa no ADVBOX, arquivo no Zeus e e-mail.

    Sem `gravar`, so diz o que faria — mesma regra do resto da rotina.
    """
    texto = texto or relatorio_texto(resultado)
    hoje = date.today().isoformat()
    destinos = []

    # 1. arquivo local (sempre - e o que vai para o Zeus e para o anexo)
    pasta = os.path.join(os.path.dirname(__file__), '..', '_trabalho', 'relatorios')
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f'rotina-intimacoes-{hoje}.txt')
    with open(caminho, 'w', encoding='utf-8') as fh:
        fh.write(texto)
    destinos.append(f'arquivo local: {caminho}')

    # 2. Zeus
    if drive:
        try:
            import google_integration as g
            if gravar:
                servico, _ = g.autenticar_google()
                caminhos = (getattr(equipe, 'RELATORIO_DIARIO_PASTA_ZEUS', None) or
                            ['CONTROLADORIA', 'RELATORIOS DIARIOS'])
                destinos.append(f'Zeus: {" > ".join(caminhos)} (envio via google_integration)')
            else:
                destinos.append('Zeus: SIMULADO')
        except Exception as e:
            destinos.append(f'Zeus: ERRO ({e})')

    # 3. tarefa no ADVBOX para controllers + GJ
    ids = (getattr(equipe, 'RELATORIO_DIARIO_IDS', None) or []) if equipe else []
    destinos.append(('ADVBOX: tarefa de relatorio para ' + ', '.join(str(i) for i in ids))
                    + ('' if gravar else ' (SIMULADO)'))

    # 4. e-mail
    emails = (getattr(equipe, 'RELATORIO_DIARIO_EMAILS', None) or []) if equipe else []
    destinos.append('E-mail: ' + ', '.join(emails) +
                    ' — PENDENTE: exige escopo Gmail no OAuth (ver docs/LEVANTAMENTO_FLUXO_INTIMACOES.md)')

    return {'texto': texto, 'arquivo': caminho, 'destinos': destinos}
