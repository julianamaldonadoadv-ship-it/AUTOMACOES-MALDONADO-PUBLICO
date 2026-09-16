"""
=============================================================================
  SQUAD CONTROLADORIA + DIVIDA RURAL - MALDONADO ADVOGADOS
=============================================================================

  Prioridade do projeto: comando `triagem` (Squad Controladoria) — elimina a
  distribuicao manual de intimacoes hoje feita por 2 controllers.

  Uso:
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py triagem --dias 7
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py triagem --dias 7 --criar-tarefa
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py intake --dias 7
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py intake --dias 7 --integrar --com-drive
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py intake --inspecionar
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py tarefas
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py processos
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py prazos
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py advbox        # diagnostico da integracao
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py triagem --dias 7 --fonte sync
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py sync          # diagnostico do SYNC
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py sync intimacoes --dias 1
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py sync prazos --de 2026-09-01 --ate 2026-09-30
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py sync autos 7001234-56.2026.8.22.0001 -o autos.md
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py criar-tarefa <lawsuit_id> <tipo> --mensagem "..."
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py drive autenticar
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py drive sair
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py drive testar
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py drive cliente "NOME DO CLIENTE"
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py drive enviar peca.docx --cliente "NOME" --subpasta "DOC PESSOAL"
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py drive peca peca.docx --cliente "NOME" --processo "7001234-56.2026.8.22.0001"
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py anexos conferir --cliente "NOME" --acao-peca mora
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py anexos baixar --cliente "NOME" --acao-peca mora
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py anexos placeholders inicial.docx
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py anexos recorte cedula.pdf --tipo cedula --saida recorte.png
    cd MALDONADO_ADVOGADOS && python OPERACIONAL/main.py anexos inserir inicial.docx -m "INSERIR UMA IMAGEM." -i recorte.png -l "Imagem 03. Cédula ..., fl. 2 (grifo nosso)"
=============================================================================
"""
import sys, os, io, json, argparse
from datetime import datetime, timedelta
from collections import defaultdict

# line_buffering=True: sem isso a saida fica presa no buffer ate o fim do comando —
# o link do OAuth e o progresso da triagem so apareceriam no final.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

import advbox_integration as advbox
import comunica_djen
import sync_integration as sync
from triagem_divida_rural import triagem_lote, imprimir_triagem
import anexos_inicial as anexos
import roteamento_controller as roteamento
import rotina_diaria
import despachos_controle

try:
    import equipe
except ImportError:
    equipe = None


def _usuarios():
    """Le config/equipe.py (fonte principal) com fallback pro .env."""
    if equipe and equipe.USUARIOS_ADVBOX:
        return equipe.USUARIOS_ADVBOX
    return {
        'RESPONSAVEL': os.getenv('ADVBOX_USER_RESPONSAVEL'),
        'OUTRO_ADVOGADO': os.getenv('ADVBOX_USER_OUTRO_ADVOGADO'),
        'GERENCIA_JURIDICA': os.getenv('ADVBOX_USER_GERENCIA_JURIDICA'),
    }


def _oabs_monitoradas():
    if equipe and equipe.OABS_MONITORADAS:
        return equipe.OABS_MONITORADAS
    lista = os.getenv('DJEN_OAB_LISTA', '')
    oabs = []
    for par in lista.split(','):
        par = par.strip()
        if '-' in par:
            num, uf = par.split('-', 1)
            oabs.append((num.strip(), uf.strip()))
    return oabs


# ============================================================
# COMANDO PRIORITARIO: triagem - Squad Controladoria
# ============================================================

def cmd_triagem(args):
    print('=' * 80)
    print('  TRIAGEM DE CONTROLADORIA - MALDONADO ADVOGADOS')
    print('=' * 80)

    fonte = getattr(args, 'fonte', None) or 'djen'
    dias = int(args.dias or 1)
    fim = datetime.now().date()
    inicio = fim - timedelta(days=dias - 1)

    oabs = _oabs_monitoradas()
    if fonte in ('djen', 'ambas') and not oabs:
        print('\n  ERRO: nenhuma OAB configurada em config/equipe.py (OABS_MONITORADAS)')
        print('  ou config/.env (DJEN_OAB_LISTA). Sem isso nao ha o que buscar no DJEN.')
        return

    print(f'\n  Periodo: {inicio.isoformat()} a {fim.isoformat()}')
    print(f'  Fonte de captura: {fonte.upper()}')
    if fonte in ('djen', 'ambas'):
        print(f'  OABs monitoradas: {", ".join(f"{n}/{uf}" for n, uf in oabs)}')

    todos_resumos = []
    if fonte in ('djen', 'ambas'):
        todos_resumos.extend(_capturar_djen(oabs, inicio, fim))
    if fonte in ('sync', 'ambas'):
        todos_resumos.extend(_capturar_sync(dias))

    if fonte == 'ambas':
        todos_resumos = _deduplicar_intimacoes(todos_resumos)

    if not todos_resumos:
        if fonte == 'sync':
            print('\n  Nenhuma intimacao pendente no Sync no periodo.')
        else:
            print('\n  Nenhuma intimacao/publicacao encontrada no periodo. '
                  '(Se isso for inesperado, a API DJEN pode ter dado falso-vazio - tente novamente.)')
        return

    # Cross-reference com o ADVBOX pelo numero do processo (1 consulta por item)
    print('\n  Cruzando com processos no ADVBOX...')
    lawsuits_por_processo = {}
    for r in todos_resumos:
        proc = r.get('processo') or ''
        proc_norm = ''.join(filter(str.isdigit, proc))
        if not proc_norm or proc_norm in lawsuits_por_processo:
            continue
        try:
            achados = advbox.buscar_processo(numero_processo=proc)
        except Exception as e:
            print(f'    Aviso: falha ao buscar processo {proc} no ADVBOX: {e}')
            continue
        if achados:
            lawsuits_por_processo[proc_norm] = achados[0]

    itens_triagem = triagem_lote(todos_resumos, lawsuits_por_processo)
    _anotar_controller(itens_triagem, lawsuits_por_processo)
    imprimir_triagem(itens_triagem)

    if args.criar_tarefa:
        _criar_tarefas_da_triagem(itens_triagem)


def _capturar_djen(oabs, inicio, fim):
    """Captura pela fonte historica: DJEN/Comunica (CNJ), OAB a OAB."""
    resumos_total = []
    for numero_oab, uf_oab in oabs:
        print(f'\n  Consultando DJEN para OAB {numero_oab}/{uf_oab}...')
        try:
            itens = comunica_djen.consultar(
                oab_numero=numero_oab, oab_uf=uf_oab,
                data_inicio=inicio.isoformat(), data_fim=fim.isoformat(),
            )
        except RuntimeError as e:
            print(f'  Aviso: falha ao consultar DJEN para {numero_oab}/{uf_oab}: {e}')
            continue
        resumos = [comunica_djen.resumir(i) for i in itens]
        for r in resumos:
            r.setdefault('_fonte', 'djen')
        print(f'    {len(resumos)} comunicacao(oes) encontrada(s)')
        resumos_total.extend(resumos)
    return resumos_total


def _capturar_sync(dias):
    """Captura pelo Sync (Atende Direito): a carteira monitorada, ja deduplicada
    por ato e com o teor integral de cada intimacao.

    Nao usa OABS_MONITORADAS: quem define o que o Sync acompanha sao os MONITORES
    cadastrados la (`sync monitores`). Se a carteira do Sync estiver menor que a
    do escritorio, a triagem enxerga menos - por isso o aviso abaixo."""
    print(f'\n  Consultando Sync (intimacoes pendentes dos ultimos {dias} dia(s))...')
    if not os.getenv('SYNC_API_TOKEN'):
        print('  Aviso: SYNC_API_TOKEN nao configurado - nada capturado pelo Sync. '
              'Rode "python OPERACIONAL/main.py sync" para o diagnostico.')
        return []
    try:
        resumos = sync.intimacoes_para_triagem(dias=dias, acionaveis=True)
    except sync.SyncError as e:
        print(f'  Aviso: falha ao consultar o Sync: {e}')
        return []
    print(f'    {len(resumos)} intimacao(oes) acionavel(is)')

    sem_polo = sum(1 for r in resumos if r.get('polo_indisponivel'))
    if sem_polo:
        print(f'    Atencao: {sem_polo} item(ns) sem o polo da parte. O KPI de exito '
              f'depende do polo para saber se "recurso nao provido" e exito ou inexito - '
              f'esses itens nao servem para apuracao sem conferencia humana.')
    return resumos


#  Quantos caracteres iniciais iguais bastam para dizer que DJEN e Sync estao
#  falando do MESMO ato. Nao se compara o texto inteiro: o DJEN publica o texto
#  da comunicacao e o Sync devolve o teor integral do documento, de tamanhos
#  diferentes - o que coincide e' a ABERTURA.
_PREFIXO_MESMO_ATO = 60


def _deduplicar_intimacoes(resumos):
    """Com --fonte ambas, o mesmo ato chega duas vezes: pela publicacao no DJEN
    e pela captura do Sync.

    O casamento e' CONSERVADOR de proposito. Agrupa por (processo, dia) e so
    funde quando a abertura do texto coincide - porque o mesmo processo pode ter
    dois atos DIFERENTES no mesmo dia (foi o caso de uma cliente, que teve
    "defiro o pedido" e "defiro a dilacao de prazo" na mesma semana). Na duvida
    MANTEM OS DOIS e avisa: duplicata repetida na triagem e' incomodo visivel;
    intimacao fundida por engano e' prazo perdido em silencio.

    Ganhando o par, fica a versao com POLO (insubstituivel para o KPI de exito);
    empatado, fica a do Sync, que vem com o teor integral."""
    def normalizar_texto(r):
        return ''.join((r.get('texto') or '').split()).upper()

    grupos = defaultdict(list)
    for r in resumos:
        proc = ''.join(filter(str.isdigit, r.get('processo') or ''))
        dia = str(r.get('data') or '')[:10]
        grupos[(proc, dia)].append(r)

    finais = []
    fundidos = 0
    ambiguos = 0
    for (proc, dia), itens in grupos.items():
        if len(itens) == 1 or not proc:
            finais.extend(itens)
            continue
        pendentes = list(itens)
        while pendentes:
            base = pendentes.pop(0)
            texto_base = normalizar_texto(base)
            par = None
            for outro in pendentes:
                texto_outro = normalizar_texto(outro)
                if base.get('_fonte') == outro.get('_fonte'):
                    continue  # duas publicacoes da MESMA fonte nao sao duplicata
                curto = min(len(texto_base), len(texto_outro))
                if curto >= _PREFIXO_MESMO_ATO and \
                        texto_base[:_PREFIXO_MESMO_ATO] == texto_outro[:_PREFIXO_MESMO_ATO]:
                    par = outro
                    break
            if par is None:
                finais.append(base)
                continue
            pendentes.remove(par)
            finais.append(_melhor_versao(base, par))
            fundidos += 1
        # Sobrou mais de um item do mesmo processo/dia que NAO casou: sao atos
        # distintos (ou o texto nao deu para comparar). Ambos seguem.
        if len([f for f in finais if ''.join(filter(str.isdigit, f.get('processo') or '')) == proc
                and str(f.get('data') or '')[:10] == dia]) > 1:
            ambiguos += 1

    if fundidos:
        print(f'\n  Dedup DJEN x Sync: {fundidos} ato(s) que chegaram pelas duas fontes '
              f'foram unificados.')
    if ambiguos:
        print(f'  {ambiguos} processo(s) com mais de um ato no mesmo dia sem abertura de '
              f'texto coincidente: mantidos SEPARADOS (podem ser atos distintos) - '
              f'confira antes de agendar.')
    return finais


def _melhor_versao(a, b):
    """Entre as duas capturas do mesmo ato, escolhe a que serve para decidir:
    primeiro quem tem POLO (o KPI depende dele), depois a do Sync (teor integral)."""
    if bool(a.get('partes_polo')) != bool(b.get('partes_polo')):
        vencedor, perdedor = (a, b) if a.get('partes_polo') else (b, a)
    else:
        vencedor, perdedor = (a, b) if a.get('_fonte') == 'sync' else (b, a)
    # Guarda de onde mais o ato veio, para o relatorio nao esconder a origem.
    vencedor = dict(vencedor)
    vencedor['_fontes'] = sorted({a.get('_fonte') or '?', b.get('_fonte') or '?'})
    # Se o vencedor tem texto mais curto que o descartado, aproveita o maior:
    # ler dispositivo em texto cortado da conclusao errada.
    if len(perdedor.get('texto') or '') > len(vencedor.get('texto') or ''):
        vencedor['texto'] = perdedor['texto']
        vencedor['texto_truncado'] = False
    return vencedor


def _anotar_controller(itens_triagem, lawsuits_por_processo):
    """Anexa a cada item quem lanca e quem recebe a tarefa: a controller do
    advogado responsavel pelo processo (regra da Dra. Juliana, 10/09/2026 -
    config/equipe.py -> CONTROLLERS). Item sem controller resolvida sobe no
    relatorio como "CONTROLLER A DEFINIR" e nao vira tarefa."""
    for it in itens_triagem:
        proc_norm = ''.join(filter(str.isdigit, it.get('processo') or ''))
        lawsuit = (lawsuits_por_processo or {}).get(proc_norm)
        res = roteamento.resolver(lawsuit=lawsuit)
        it['roteamento'] = res
        it['roteamento_descricao'] = roteamento.descrever(res)


def _criar_tarefas_da_triagem(itens_triagem):
    """Para itens de prioridade alta com peca/providencia identificada, oferece
    criar a tarefa no ADVBOX - sempre com confirmacao manual, nunca em lote sem revisao.

    Quem lanca (`from`) e' a CONTROLLER do advogado responsavel pelo processo;
    quem recebe (`guests`) e' o proprio advogado responsavel. Sem controller
    resolvida, a tarefa NAO e' criada - o item sobe como pendencia.
    """
    candidatos = [it for it in itens_triagem if it['prioridade'] == 'alta'
                  and it.get('cliente') and 'NAO ENCONTRADO' not in it['cliente']]

    if not candidatos:
        print('\n  Nenhum item de prioridade alta com processo identificado no ADVBOX para criar tarefa.')
        return

    prontos = [it for it in candidatos if (it.get('roteamento') or {}).get('ok')]
    pendentes = [it for it in candidatos if not (it.get('roteamento') or {}).get('ok')]

    if pendentes:
        print(f'\n  {len(pendentes)} item(ns) de prioridade alta SEM controller definida '
              f'- nao serao criados (conferir com a Dra. Juliana):')
        for it in pendentes:
            print(f"    - {it['processo']} | {it['cliente']}")
            print(f"      {(it.get('roteamento') or {}).get('motivo') or 'motivo nao informado'}")

    if not prontos:
        print('\n  Nenhum item com controller definida para criar tarefa.')
        return

    print(f'\n  {len(prontos)} item(ns) de prioridade alta prontos para virar tarefa:')
    for it in prontos:
        rot = it['roteamento']
        print(f"\n  Processo: {it['processo']} | Cliente: {it['cliente']}")
        if rot.get('arquivado'):
            print('  ATENCAO: processo ARQUIVADO/ENCERRADO no ADVBOX - em regra nao ha '
                  'agendamento. Conferir se cabe algo antes de criar a tarefa.')
        print(f"  Providencia: {it['providencia_cabivel']}")
        print(f"  Lanca: {rot['controller_nome']} (ID {rot['from_id']}) "
              f"-> Para: {rot['advogado'] if rot['guest_id'] != rot['from_id'] else 'ela mesma'} "
              f"(ID {rot['guest_id']}) | regra: {rot['regra']}")
        resp = input('  Criar tarefa no ADVBOX para este item? (s/N): ').strip().lower()
        if resp != 's':
            print('  Pulado.')
            continue
        # Aqui e' necessario o lawsuit_id do ADVBOX - buscamos de novo por seguranca.
        achados = advbox.buscar_processo(numero_processo=it['processo'])
        if not achados:
            print('  Processo nao encontrado no ADVBOX no momento da criacao - pulado.')
            continue
        lawsuit_id = achados[0].get('id')
        settings = advbox.carregar_settings()
        task_id = advbox.buscar_id_por_nome('tasks', 'ACOMPANHAMENTO') or (settings.get('tasks') or [{}])[0].get('id')
        try:
            resultado = advbox.criar_publicacao(
                lawsuit_id=lawsuit_id, task_id=task_id, guest_ids=[rot['guest_id']],
                comments=f"[Triagem automatica] {it['providencia_cabivel']} - {it.get('peca_necessaria') or ''}",
                from_id=rot['from_id'], urgent=True,
            )
            print(f'  Tarefa criada: {resultado}')
        except Exception as e:
            print(f'  Erro ao criar tarefa: {e}')


# ============================================================
# COMANDO: rotina - rodada diaria da Controladoria (08:00)
# ============================================================

def cmd_rotina(args):
    """Rodada diaria completa: captura -> triagem -> prazos -> plano de tarefas
    -> relatorio. Simulacao por padrao; `--gravar` e' o que autoriza escrever no
    ADVBOX (a rotina agendada no servidor roda com --gravar)."""
    resultado = rotina_diaria.rodar(dias=int(args.dias or 1), gravar=bool(args.gravar))
    texto = rotina_diaria.relatorio_texto(resultado)
    print(texto)

    if args.planilha:
        try:
            import planilha_conferencia
            sid, link, qa, qi = planilha_conferencia.publicar(resultado)
            print(f'\n  Planilha de conferencia atualizada: {link}')
            print(f'    +{qa} agendamento(s) e +{qi} intimacao(oes) nesta rodada')
        except Exception as e:
            print(f'\n  Aviso: nao consegui atualizar a planilha de conferencia: {e}')

    entrega = rotina_diaria.publicar_relatorio(
        resultado, texto=texto, gravar=bool(args.gravar),
        drive=not args.sem_drive)
    print('\n  Relatorio:')
    for d in entrega['destinos']:
        print(f'    - {d}')
    if not args.gravar:
        print('\n  MODO SIMULACAO: nada foi gravado no ADVBOX. '
              'Use --gravar quando a rodada estiver conferida.')


# ============================================================
# COMANDO: despachos - controle de despachos (POP-CJ-DESP-001)
# ============================================================

def cmd_despachos(args):
    """Alimenta a planilha CONTROLE DE DESPACHOS no Drive. Simulacao e' o padrao;
    `--gravar` e' o que autoriza escrever na planilha (nada e gravado no ADVBOX)."""
    from datetime import date, timedelta
    if args.de and args.ate:
        de, ate = args.de, args.ate
    else:
        fim = date.today()
        ini = fim - timedelta(days=int(args.dias or 1) - 1)
        de, ate = ini.isoformat(), fim.isoformat()
    resultado = despachos_controle.rodar(de, ate, gravar=bool(args.gravar))
    print(despachos_controle.relatorio(resultado))
    if not args.gravar:
        print('\n  MODO SIMULACAO: a planilha do Drive nao foi tocada. Use --gravar.')


# ============================================================
# COMANDO: intake - Squad Comercial (Atende Direito -> ADVBOX)
# ============================================================

def cmd_intake(args):
    import intake_atende_direito as intake
    import atende_direito_integration as atende

    if args.inspecionar:
        print('=' * 80)
        print('  ATENDE DIREITO - PAYLOAD CRU (calibracao do mapa de campos)')
        print('=' * 80)
        atende.inspecionar(quantidade=int(args.inspecionar_qtd or 1))
        return

    leads, inicio, fim = intake.coletar_leads(dias=args.dias, etapa=args.etapa)
    if not leads:
        print('\n  Nenhum lead retornado pelo Atende Direito no periodo.')
        print('  Se isso for inesperado, confira ATENDE_DIREITO_ETAPA_QUALIFICADO '
              'e os endpoints no config/.env (rode --inspecionar).')
        return

    analisados = intake.analisar(leads)
    intake.imprimir_relatorio(analisados, inicio, fim)

    if args.integrar:
        intake.integrar(
            analisados,
            com_drive=bool(args.com_drive),
            tipo_processo=args.tipo_processo,
            criar_tarefa=not args.sem_tarefa,
        )
    else:
        novos = sum(1 for a in analisados if a['situacao'] == 'novo')
        if novos:
            print(f'\n  {novos} lead(s) novo(s). Rode com --integrar para cadastrar '
                  'no ADVBOX (pede confirmacao lead a lead).')


# ============================================================
# COMANDO: tarefas - Lista tarefas pendentes
# ============================================================

def cmd_tarefas(args):
    print('=' * 80)
    print('  TAREFAS PENDENTES - MALDONADO ADVOGADOS')
    print('=' * 80)

    dias_frente = int(args.dias) if args.dias else 14
    inicio = datetime.now() - timedelta(days=30)
    fim = datetime.now() + timedelta(days=dias_frente)

    todas = advbox.listar_tarefas(
        date_start=inicio.strftime('%Y-%m-%d'),
        date_end=fim.strftime('%Y-%m-%d'),
    )

    pendentes = [t for t in todas if any(not u.get('completed') for u in t.get('users', []))]

    por_resp = defaultdict(list)
    for t in pendentes:
        for u in t.get('users', []):
            if not u.get('completed'):
                nome = u.get('name', 'SEM RESPONSAVEL')
                por_resp[nome].append(t)

    print(f'\n  Total pendentes: {len(pendentes)}')

    for resp in sorted(por_resp.keys()):
        tarefas = por_resp[resp]
        print(f'\n  --- {resp} ({len(tarefas)} tarefas) ---')
        for t in sorted(tarefas, key=lambda x: x.get('date_deadline') or x.get('date', '') or '9'):
            lawsuit = t.get('lawsuit', {}) or {}
            cli = lawsuit['customers'][0].get('name', '') if lawsuit.get('customers') else ''
            prazo = t.get('date_deadline', '')
            prazo_str = f' | PRAZO: {prazo[:10]}' if prazo else ''
            urg = ' [URGENTE]' if any(u.get('urgent') for u in t.get('users', [])) else ''
            notes = (t.get('notes') or '')[:50]
            print(f'    {t.get("date","")[:10]} | {t.get("task","")[:25]:25} | {cli[:25]:25}{urg}{prazo_str}')
            if notes:
                print(f'      {notes}')


# ============================================================
# COMANDO: processos - Lista processos ativos
# ============================================================

def cmd_processos(args):
    print('=' * 80)
    print('  PROCESSOS ATIVOS - MALDONADO ADVOGADOS')
    print('=' * 80)

    todos = advbox.listar_processos()
    ativos = [p for p in todos if 'ARQUIV' not in (p.get('stage') or '').upper()
              and 'RENUNCI' not in (p.get('stage') or '').upper()]

    if args.responsavel:
        ativos = [p for p in ativos if args.responsavel.upper() in (p.get('responsible') or '').upper()]

    por_fase = defaultdict(list)
    for p in ativos:
        por_fase[p.get('stage') or 'SEM FASE'].append(p)

    print(f'\n  Total ativos: {len(ativos)}')

    for fase in sorted(por_fase.keys()):
        procs = por_fase[fase]
        print(f'\n  [{fase}] - {len(procs)} processo(s)')
        for p in sorted(procs, key=lambda x: x.get('created_at', ''), reverse=True):
            cli = p.get('customers', [{}])[0].get('name', '') if p.get('customers') else ''
            num = p.get('process_number') or 'S/N'
            resp = (p.get('responsible') or '')[:15]
            print(f'    {num[:35]:35} | {cli[:28]:28} | {resp}')


# ============================================================
# COMANDO: prazos - Lista prazos fatais proximos
# ============================================================

def cmd_prazos(args):
    print('=' * 80)
    print('  PRAZOS FATAIS - PROXIMOS 14 DIAS')
    print('=' * 80)

    inicio = datetime.now()
    fim = inicio + timedelta(days=14)

    tarefas = advbox.listar_tarefas(
        deadline_start=inicio.strftime('%Y-%m-%d'),
        deadline_end=fim.strftime('%Y-%m-%d'),
    )

    pendentes = [t for t in tarefas if any(not u.get('completed') for u in t.get('users', []))]
    pendentes.sort(key=lambda x: x.get('date_deadline') or '9999')

    print(f'\n  Prazos encontrados: {len(pendentes)}')

    for t in pendentes:
        lawsuit = t.get('lawsuit', {}) or {}
        cli = lawsuit['customers'][0].get('name', '') if lawsuit.get('customers') else ''
        prazo = (t.get('date_deadline') or '')[:10]
        resps = [u.get('name', '')[:20] for u in t.get('users', []) if not u.get('completed')]
        urg = ' [URGENTE]' if any(u.get('urgent') for u in t.get('users', [])) else ''
        notes = (t.get('notes') or '')[:60]

        dias_rest = (datetime.strptime(prazo, '%Y-%m-%d') - datetime.now()).days if prazo else '?'

        print(f'\n  PRAZO: {prazo} ({dias_rest} dias) {urg}')
        print(f'    {t.get("task","")[:30]} | {cli[:30]}')
        print(f'    Responsavel: {", ".join(resps)}')
        if notes:
            print(f'    {notes}')


# ============================================================
# COMANDO: criar-tarefa - Cria tarefa no ADVBOX manualmente
# ============================================================

def _lancador_manual(lawsuit_id):
    """Quem assina a tarefa (`from`) num comando manual: a controller do processo,
    pelas mesmas regras da triagem. Tratamento de intimacao e' sempre de uma
    controller - a gerencia juridica (Dra. Juliana) nao entra nessa fila."""
    lawsuit = None
    try:
        lawsuit = advbox.obter_processo(lawsuit_id)
    except Exception as e:
        print(f'  Aviso: nao consegui ler o processo {lawsuit_id} no ADVBOX ({e}).')

    res = roteamento.resolver(lawsuit=lawsuit)
    if res.get('arquivado'):
        print('  ATENCAO: processo ARQUIVADO/ENCERRADO no ADVBOX - em regra nao ha '
              'agendamento. Conferir antes de criar a tarefa.')
    if res['ok']:
        print(f"  Lanca: {res['controller_nome']} (ID {res['from_id']}) | regra: {res['regra']}")
        return res['from_id'], res

    print(f"  CONTROLLER A DEFINIR: {res['motivo']}")
    print('  Ajustar config/equipe.py (CONTROLLERS / CONTROLLER_FALLBACK) antes de lancar.')
    return None, res


def cmd_criar_tarefa(args):
    print('Criando tarefa no ADVBOX...')

    settings = advbox.carregar_settings()
    task_types = settings.get('tasks', [])
    task_id = None
    for tt in task_types:
        if args.tipo.upper() in tt.get('task', '').upper():
            task_id = tt['id']
            break
    if not task_id:
        print(f'Tipo de tarefa "{args.tipo}" nao encontrado.')
        print('Tipos disponiveis:')
        for tt in task_types[:20]:
            print(f'  {tt["task"]}')
        return

    from_id, rot = _lancador_manual(args.processo)
    if not from_id:
        print('  Cancelado - tarefa nao criada.')
        return

    usuarios = _usuarios()
    if args.para:
        guest_id = usuarios.get(args.para.upper())
        if not guest_id:
            print(f'Usuario "{args.para}" nao encontrado em config/equipe.py -> USUARIOS_ADVBOX.')
            return
        destino = f'{args.para} (ID: {guest_id})'
    else:
        # Sem --para: a tarefa vai para o advogado responsavel pelo processo
        guest_id = rot.get('guest_id')
        if not guest_id:
            print('  Processo sem advogado responsavel identificado no ADVBOX - '
                  'informe o destinatario (argumento "para").')
            return
        destino = f"{rot.get('advogado')} (ID: {guest_id})"

    print(f'  Processo: {args.processo}')
    print(f'  Tipo: {args.tipo}')
    print(f'  Para: {destino}')
    print(f'  Mensagem: {(args.mensagem or "")[:50]}')

    resp = input('\n  Confirma? (s/N): ').strip().lower()
    if resp != 's':
        print('  Cancelado.')
        return

    resultado = advbox.criar_publicacao(
        lawsuit_id=args.processo, task_id=task_id, guest_ids=[guest_id],
        comments=args.mensagem or '', from_id=from_id,
        date_deadline=args.prazo, urgent=bool(args.urgente),
    )
    print(f'  Tarefa criada! {resultado}')


# ============================================================
# COMANDO: drive - estrutura ZEUS no Google Drive
# ============================================================

def cmd_gmail(args):
    """Gmail somente leitura - localizar e baixar e-mails (ex.: ata de reuniao estrategica)."""
    import google_integration as g
    try:
        gmail, conta = g.autenticar_gmail()
    except RuntimeError as e:
        print(f'\n  {e}')
        return

    if args.acao == 'autenticar':
        print(f'\n  Gmail conectado (somente leitura): {conta}')
        print('  Token salvo em config/token_gmail.json (nao versionado).')
        return

    if args.acao == 'buscar':
        achados = g.buscar_emails(gmail, args.consulta, limite=args.limite)
        if not achados:
            print(f'\n  Nenhum e-mail para: {args.consulta}')
            return
        for m in achados:
            print(f"\n  [{m['id']}] {m['data']}")
            print(f"    De: {m['de']}")
            print(f"    Assunto: {m['assunto']}")
            if m['anexos']:
                print(f"    Anexos: {', '.join(m['anexos'])}")
            print(f"    {m['trecho'][:160]}")
        print('\n  Para baixar: python OPERACIONAL/main.py gmail baixar <id>')
        return

    if args.acao == 'baixar':
        destino = args.destino or os.path.join(
            os.path.dirname(__file__), '..', '_trabalho', 'emails', args.id)
        for caminho in g.baixar_email(gmail, args.id, destino):
            print(f'  gravado: {os.path.normpath(caminho)}')


def _drive():
    """Autentica e devolve so o service do Drive (import tardio: o CLI de triagem
    nao deve exigir credencial Google pra rodar)."""
    import google_integration as g
    drive_service, _ = g.autenticar_google()
    return g, drive_service


def cmd_drive(args):
    # 'sair' nao autentica (o objetivo e justamente descartar a credencial atual)
    if args.acao == 'sair':
        import google_integration as g
        print('  Isso desconecta a conta Google usada por este sistema')
        print('  (revoga o acesso no Google e apaga config/token.json).')
        if input('\n  Confirma? (s/N): ').strip().lower() != 's':
            print('  Cancelado.')
            return
        ok, detalhe = g.esquecer_credencial()
        print(f'\n  {detalhe}' if ok else f'\n  {detalhe}')
        if ok:
            print('  Para conectar a conta do escritorio: '
                  'python OPERACIONAL/main.py drive autenticar')
        return

    g, drive = _drive()

    if args.acao == 'autenticar':
        print('=' * 80)
        print('  GOOGLE - CONTA CONECTADA')
        print('=' * 80)
        atual = g.conta_autenticada(drive)
        esperada = g.conta_esperada()
        print(f'\n  Conta: {atual or "(nao identificada)"}')
        print(f'  Esperada (.env GOOGLE_CONTA_ESCRITORIO): {esperada or "(nao definida)"}')
        if not esperada:
            print('\n  Recomendado: defina GOOGLE_CONTA_ESCRITORIO em config/.env para o sistema')
            print('  recusar qualquer token que nao seja da conta do escritorio.')
        print('\n  Token salvo em config/token.json (nao versionado).')
        return

    if args.acao == 'testar':
        print('=' * 80)
        print('  GOOGLE DRIVE - TESTE DE ACESSO A ESTRUTURA ZEUS')
        print('=' * 80)
        clientes_id = g.pasta_clientes(drive)
        if not clientes_id:
            print("\n  ERRO: nao encontrei a pasta '01 CLIENTES'.")
            print('  Preencha DRIVE_PASTA_CLIENTES_ID (ou DRIVE_PASTA_ZEUS_ID) em config/.env,')
            print('  ou confirme que a conta autenticada tem acesso a pasta ZEUS do escritorio.')
            return
        print(f'\n  Pasta 01 CLIENTES: {clientes_id}')
        print(f'  {g.link_pasta(clientes_id)}')
        letras = g.listar_pasta(drive, clientes_id, apenas_pastas=True)
        print(f'\n  {len(letras)} pasta(s)-indice encontrada(s):')
        print('    ' + ', '.join(p['name'] for p in letras[:40]))
        return

    if args.acao == 'cliente':
        pasta = g.pasta_do_cliente(drive, args.nome)
        if pasta:
            print(f"\n  Cliente: {pasta['name']}")
            print(f"  Pasta:   {g.link_pasta(pasta['id'])}")
            conteudo = g.listar_pasta(drive, pasta['id'])
            print(f'\n  {len(conteudo)} item(ns):')
            for item in conteudo:
                marca = '[DIR]' if item['mimeType'] == g.MIME_PASTA else '     '
                print(f"    {marca} {item['name']}")
            return

        print(f"\n  Cliente '{args.nome}' nao encontrado na estrutura ZEUS.")
        if not args.criar:
            print('  Use --criar para criar a pasta do cliente com as 4 subpastas padrao.')
            return

        print('\n  Sera criado:')
        print(f"    [{g._letra_inicial(args.nome)}] > {args.nome.strip()}")
        for sub in g._subpastas_configuradas():
            print(f'        {sub}')
        if input('\n  Confirma a criacao no Drive do escritorio? (s/N): ').strip().lower() != 's':
            print('  Cancelado.')
            return
        cliente_id, subpastas = g.criar_estrutura_cliente(drive, args.nome)
        print(f'\n  Estrutura criada: {g.link_pasta(cliente_id)}')
        for nome_sub in subpastas:
            print(f'    {nome_sub}')
        return

    if args.acao == 'enviar':
        pasta = g.pasta_do_cliente(drive, args.cliente)
        if not pasta:
            print(f"\n  ERRO: cliente '{args.cliente}' nao encontrado na estrutura ZEUS.")
            print('  Rode primeiro:  python OPERACIONAL/main.py drive cliente "NOME" --criar')
            return

        destino_id, destino_nome = pasta['id'], pasta['name']
        if args.subpasta:
            sub = g.buscar_subpasta(drive, pasta['id'], args.subpasta)
            if not sub:
                existentes = [f['name'] for f in
                              g.listar_pasta(drive, pasta['id'], apenas_pastas=True)]
                print(f"\n  ERRO: subpasta '{args.subpasta}' nao existe em {pasta['name']}.")
                print(f"  Subpastas existentes: {', '.join(existentes) or '(nenhuma)'}")
                return
            destino_id = sub['id']
            destino_nome = f"{pasta['name']} / {sub['name']}"

        print(f'\n  Arquivo: {args.arquivo}')
        print(f'  Destino: {destino_nome}')
        if input('\n  Confirma o envio? (s/N): ').strip().lower() != 's':
            print('  Cancelado.')
            return
        enviado = g.enviar_arquivo(drive, args.arquivo, destino_id,
                                   converter_google_docs=bool(args.converter))
        print(f"\n  Enviado: {enviado['name']}")
        print(f"  {enviado.get('webViewLink', '')}")
        return


    if args.acao == 'peca':
        # ZEUS > PEÇAS AUTOMAÇÃO > [CLIENTE] - [Nº PROCESSO] > peca.docx
        # Convencao definida pela Dra. Juliana em 08/09/2026.
        nome_pasta = g.nome_pasta_peca(args.cliente, args.processo)
        raiz = g.pasta_pecas_automacao(drive)
        if not raiz:
            print(f"\n  ERRO: a pasta '{g.PASTA_PECAS_AUTOMACAO}' nao existe na raiz da ZEUS.")
            print('  Crie-a no Drive (ou preencha DRIVE_PASTA_PECAS_AUTOMACAO_ID em config/.env).')
            return

        ja_existe = g.buscar_subpasta(drive, raiz, nome_pasta)
        print(f'\n  Arquivo: {args.arquivo}')
        print(f'  Destino: {g.PASTA_PECAS_AUTOMACAO} / {nome_pasta}')
        if not ja_existe:
            print('           (a subpasta sera criada agora)')
        if not args.processo:
            print(f'\n  AVISO: sem numero de processo — a pasta vai como "{g.SEM_PROCESSO}".')
            print('         Renomeie quando sair a distribuicao.')

        if input('\n  Confirma o arquivamento? (s/N): ').strip().lower() != 's':
            print('  Cancelado.')
            return

        enviado, pasta_id = g.arquivar_peca(
            drive, args.arquivo, args.cliente, args.processo,
            converter_google_docs=bool(args.converter))
        print(f"\n  Arquivado: {enviado['name']}")
        print(f"  Pasta: {g.link_pasta(pasta_id)}")
        print(f"  {enviado.get('webViewLink', '')}")
        return


# ============================================================
# COMANDO: anexos - documentos da inicial (Squad Divida Rural)
# ============================================================
# Fecha o ciclo da peca inicial: acha os documentos do cliente na ZEUS, confere
# contra o rol da tese, recorta a clausula/pagina relevante e cola no placeholder
# do modelo. Nada aqui grava no Drive (o arquivamento continua em `drive peca`).

def _destino_padrao(cliente: str) -> str:
    limpo = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in cliente).strip()
    return os.path.join('_trabalho', 'anexos', limpo or 'CLIENTE')


def _imprimir_inventario(pasta, arquivos, g):
    print(f"\n  Cliente: {pasta['name']}")
    print(f"  Pasta:   {g.link_pasta(pasta['id'])}")
    print(f'\n  {len(arquivos)} arquivo(s) na pasta do cliente:\n')

    por_tipo = defaultdict(list)
    for arq in arquivos:
        por_tipo[arq['tipo']].append(arq)

    for slug in sorted((s for s in por_tipo if s), key=lambda s: anexos.rotulo(s)):
        print(f'  [{slug}] {anexos.rotulo(slug)}')
        for arq in por_tipo[slug]:
            local = f" — {arq['subpasta']}" if arq['subpasta'] else ''
            print(f"      {arq['nome']}{local}")
        print()

    if por_tipo.get(None):
        print('  [nao classificados] conferir na mao — o palpite e por nome de arquivo:')
        for arq in por_tipo[None]:
            local = f" — {arq['subpasta']}" if arq['subpasta'] else ''
            print(f"      {arq['nome']}{local}")
        print()


def cmd_anexos(args):
    # Acoes que so mexem em arquivo local nao precisam autenticar no Google.
    if args.acao == 'placeholders':
        print('=' * 80)
        print('  PLACEHOLDERS DA PECA')
        print('=' * 80)
        achados = anexos.localizar_placeholders(args.arquivo)
        if not achados:
            print('\n  Nenhum marcador encontrado. Se o modelo tem marcador em outro formato,')
            print('  avise para incluir o padrao em OPERACIONAL/anexos_inicial.py.')
            return
        for ph in achados:
            marca = 'IMAGEM' if ph['tipo'] == 'imagem' else 'TEXTO '
            print(f"\n  {ph['n']:02d}. [{marca}] {ph['onde']}")
            print(f"      marcador: {ph['texto'][:100]}")
            if ph['contexto']:
                print(f"      contexto: {ph['contexto'][:100]}")
            if ph['sugestao']:
                print(f"      provavel: [{ph['sugestao']}] {anexos.rotulo(ph['sugestao'])}")
        print('\n  Sugestao e palpite pelo texto do marcador — confirme o documento antes de colar.')
        return

    if args.acao == 'localizar':
        termos = tuple(args.buscar or ()) or anexos.termos_de_busca(args.tipo or '')
        if not termos:
            print('\n  ERRO: informe --buscar "termo" (ou --tipo, para usar os termos do tipo).')
            return
        print(f"\n  {args.arquivo}")
        print(f"  Procurando: {', '.join(termos)}\n")
        achados = anexos.paginas_com(args.arquivo, termos)
        if not achados:
            print('  Nenhum termo encontrado. PDF digitalizado sem OCR nao tem texto pesquisavel —')
            print('  nesse caso escolha a pagina na mao (--pagina N --pagina-inteira).')
            return
        for pagina, termo, quantas in achados:
            print(f'  pagina {pagina:>3}  "{termo}"  ({quantas}x)')
        return

    if args.acao == 'recorte':
        termos = tuple(args.buscar or ()) or anexos.termos_de_busca(args.tipo or '')
        saida, descricao = anexos.recortar(
            args.arquivo, args.saida,
            pagina=int(args.pagina) if args.pagina else None,
            buscar=termos or None, dpi=int(args.dpi),
            margem_cm=float(args.margem), pagina_inteira=bool(args.pagina_inteira),
            realcar=args.realcar, largura_total=bool(args.largura_total))
        print(f'\n  Recorte gerado: {saida}')
        print(f'  Origem: {os.path.basename(args.arquivo)} — {descricao}')
        print('\n  CONFIRA O RECORTE ANTES DE COLAR NA PECA. Recorte cortado no meio da')
        print('  clausula tira o contexto e enfraquece a prova.')
        return

    if args.acao == 'inserir':
        saida, original = anexos.inserir_recorte(
            args.arquivo, args.placeholder, args.imagem,
            legenda=args.legenda, saida=args.saida,
            largura_cm=float(args.largura) if args.largura else None)
        print(f'\n  Recorte inserido em: {saida}')
        print(f'  Placeholder substituido: "{original[:80]}"')
        if args.legenda:
            print(f'  Legenda: {args.legenda}')
        return

    if args.acao == 'pendencia':
        saida, original = anexos.marcar_pendencia(
            args.arquivo, args.placeholder, texto=args.texto, saida=args.saida)
        print(f'\n  Pendencia marcada em amarelo: {saida}')
        print(f'  Placeholder: "{original[:80]}"')
        return

    # Daqui pra baixo precisa do Drive.
    g, drive = _drive()

    pasta, arquivos = anexos.inventariar_cliente(g, drive, args.cliente)
    if not pasta:
        print(f"\n  ERRO: cliente '{args.cliente}' nao encontrado na estrutura ZEUS.")
        print('  Confira o nome com:  python OPERACIONAL/main.py drive cliente "NOME"')
        return

    if args.acao == 'inventario':
        print('=' * 80)
        print('  INVENTARIO DE DOCUMENTOS DO CLIENTE')
        print('=' * 80)
        _imprimir_inventario(pasta, arquivos, g)
        return

    if args.acao == 'conferir':
        conferencia = anexos.conferir_rol(arquivos, args.acao_peca)
        print('=' * 80)
        print('  CONFERENCIA DO ROL DE DOCUMENTOS')
        print('=' * 80)
        print(f"\n  Cliente: {pasta['name']}")
        print(f"  Tese:    {conferencia['rotulo']}")

        for titulo, chave in (('OBRIGATORIOS', 'obrigatorios'), ('RECOMENDADOS', 'recomendados')):
            print(f'\n  {titulo}')
            for slug, achados in conferencia[chave]:
                if achados:
                    nomes = ', '.join(a['nome'] for a in achados[:3])
                    extra = f' (+{len(achados) - 3})' if len(achados) > 3 else ''
                    print(f'    [OK]    {anexos.rotulo(slug)}')
                    print(f'            {nomes}{extra}')
                else:
                    print(f'    [FALTA] {anexos.rotulo(slug)}')

        print('\n  RECORTES QUE ESTA TESE PEDE NO CORPO DA PECA')
        for slug, achados in conferencia['recortes']:
            estado = 'ha documento' if achados else 'SEM DOCUMENTO — vira pendencia amarela'
            print(f'    - {anexos.rotulo(slug)}: {estado}')

        if conferencia['nao_classificados']:
            print(f"\n  {len(conferencia['nao_classificados'])} arquivo(s) que a heuristica nao")
            print('  reconheceu — pode haver documento util ai, confira:')
            for arq in conferencia['nao_classificados'][:15]:
                print(f"    {arq['nome']}")

        if conferencia['faltando']:
            print('\n  ATENCAO: faltam documentos OBRIGATORIOS desta tese.')
            print('  Peca ao cliente / a Controladoria antes de fechar a inicial.')
        return

    if args.acao == 'baixar':
        escolhidos = []
        if args.acao_peca:
            perfil = anexos.ACOES[args.acao_peca]
            desejados = set(perfil['obrigatorios']) | set(perfil['recomendados'])
        else:
            desejados = set(args.tipo or ())

        for arq in arquivos:
            if not desejados or (set(arq['tipos']) & desejados):
                escolhidos.append(arq)

        if not escolhidos:
            print('\n  Nenhum arquivo bate com o filtro pedido.')
            return

        destino = args.destino or _destino_padrao(pasta['name'])
        print(f'\n  {len(escolhidos)} arquivo(s) -> {destino}')
        baixados = anexos.baixar_documentos(g, drive, escolhidos, destino)
        for arq in baixados:
            if arq.get('caminho'):
                print(f"    OK    {os.path.basename(arq['caminho'])}  [{arq['tipo'] or '?'}]")
            else:
                print(f"    ERRO  {arq['nome']}: {arq.get('erro', '')}")
        return

# ============================================================
# COMANDO: apontamentos - Base de apontamentos da Gerencia Juridica
# ============================================================

def cmd_apontamentos(args):
    """Levanta o que a Gerencia Juridica devolve nas pecas e classifica.

    Somente leitura. A autoria so existe em GET /history/{lawsuit_id}, que nao
    pagina e devolve ~20 itens por processo - por isso o relatorio imprime a
    cobertura por mes: e' piso, nunca "nao houve apontamento".
    """
    from apontamentos_gj import executar
    executar(dias=args.dias, de=args.de, ate=args.ate,
             csv_saida=args.csv, pausa=args.pausa)


# ============================================================
# COMANDO: kpi - Taxa de Exito Ponderado a partir das intimacoes
# ============================================================

def _capturar_djen_advbox(inicio, fim, oabs):
    """Captura as comunicacoes do periodo no DJEN e cruza com o ADVBOX.

    Extraida de `cmd_kpi` porque o vault (`cmd_vault`) precisa exatamente da
    mesma captura - e com o TEXTO INTEGRAL do ato, que o CSV nao carrega.
    Devolve (resumos, lawsuits_por_processo); ([], {}) quando nao vem nada.
    """
    resumos, vistos = [], set()
    for numero_oab, uf_oab in oabs:
        print(f'\n  Consultando DJEN para OAB {numero_oab}/{uf_oab}...')
        try:
            itens = comunica_djen.consultar(
                oab_numero=numero_oab, oab_uf=uf_oab,
                data_inicio=inicio.isoformat(), data_fim=fim.isoformat())
        except RuntimeError as e:
            print(f'  Aviso: falha ao consultar DJEN para {numero_oab}/{uf_oab}: {e}')
            continue
        novos = 0
        for i in itens:
            if i.get('id') in vistos:
                continue
            vistos.add(i.get('id'))
            resumos.append(comunica_djen.resumir(i))
            novos += 1
        print(f'    {len(itens)} comunicacao(oes), {novos} nova(s)')

    if not resumos:
        print('\n  Nenhuma intimacao no periodo. (A API DJEN da falso-vazio - '
              'se isso for inesperado, rode de novo.)')
        return [], {}

    print('\n  Cruzando com o ADVBOX (cliente, advogado responsavel, tese)...')
    lawsuits = {}
    for r in resumos:
        proc_norm = ''.join(filter(str.isdigit, r.get('processo') or ''))
        if not proc_norm or proc_norm in lawsuits:
            continue
        try:
            achados = advbox.buscar_processo(numero_processo=r.get('processo'))
        except Exception as e:
            print(f"    Aviso: falha ao buscar {r.get('processo')}: {e}")
            continue
        if achados:
            lawsuits[proc_norm] = achados[0]
    print(f'    {len(lawsuits)} processo(s) localizado(s) no ADVBOX')
    return resumos, lawsuits


def cmd_kpi(args):
    """Apura a Taxa de Exito Juridico Ponderado sobre as intimacoes do periodo.

    Somente leitura: nao grava no ADVBOX nem no Drive. A classificacao e'
    pre-classificacao por palavra-chave - quem fecha o mes e' a GJ.
    """
    import kpi_exito

    oabs = _oabs_monitoradas()
    if not oabs:
        print('\n  ERRO: nenhuma OAB configurada em config/equipe.py (OABS_MONITORADAS).')
        return

    if args.de:
        inicio = datetime.strptime(args.de, '%Y-%m-%d').date()
        fim = datetime.strptime(args.ate, '%Y-%m-%d').date() if args.ate else datetime.now().date()
    else:
        fim = datetime.now().date()
        inicio = fim - timedelta(days=int(args.dias or 1) - 1)

    print('=' * 100)
    print('  APURACAO DE KPI - TAXA DE EXITO PONDERADO')
    print('=' * 100)
    print(f'\n  Periodo: {inicio.isoformat()} a {fim.isoformat()}')
    print(f'  OABs monitoradas: {", ".join(f"{n}/{uf}" for n, uf in oabs)}')

    resumos, lawsuits = _capturar_djen_advbox(inicio, fim, oabs)
    if not resumos:
        return

    linhas = kpi_exito.avaliar_lote(resumos, lawsuits, oabs)

    # Decisoes da GJ da competencia, por cima da classificacao automatica.
    # Sem isto cada rodada (inclusive a diaria) desfazia o fechamento da GJ.
    caminho_dec = os.path.join(os.path.dirname(__file__), '..', 'docs', 'kpi_exito',
                               f'DECISOES_GJ_{inicio.strftime("%Y-%m")}.json')
    if os.path.exists(caminho_dec):
        aplicadas = kpi_exito.aplicar_decisoes_gj(linhas, kpi_exito.carregar_decisoes_gj(caminho_dec))
        print(f'\n  Decisoes da GJ aplicadas ({os.path.basename(caminho_dec)}): {len(aplicadas)}')
        for data_, proc_, nota_ in aplicadas:
            print(f'    {data_ or "-":10} | {proc_} | {nota_[:110]}')

    apuracao = kpi_exito.apurar(linhas)
    kpi_exito.imprimir_relatorio(linhas, apuracao,
                                 periodo=f'{inicio.isoformat()} a {fim.isoformat()}')

    if args.csv:
        kpi_exito.exportar_csv(linhas, args.csv)
        print(f'\n  Planilha gravada em {args.csv}')

    if getattr(args, 'planilha', False):
        # Unica escrita do KPI: a planilha da competencia no Drive (pedido da GJ,
        # 15/09/2026). Falha aqui nao derruba a apuracao nem os relatorios.
        # Formato da planilha da GJ (Acompanhamento_Casos_Maldonado_<Mes>): aba por
        # semana com diagnostico + abas de taxa rural e diversa (15/09/2026).
        import kpi_acompanhamento
        try:
            link, n_dec, n_rastro, abas = kpi_acompanhamento.publicar_competencia(linhas, inicio, fim)
            print(f"\n  Planilha de acompanhamento atualizada: {link}"
                  f"\n    {n_dec} decisao(oes) na taxa | {n_rastro} so rastreabilidade | abas: {', '.join(abas)}")
        except Exception as e:
            print(f'\n  [FALHA] planilha do KPI no Drive nao atualizada: {e}')

    if args.pdf:
        import kpi_relatorio
        pasta = args.pdf if isinstance(args.pdf, str) else 'docs/kpi_exito'
        sufixo = f'{inicio.isoformat()}_a_{fim.isoformat()}'
        print(f'\n  Gerando relatorios em {pasta}/ ...')
        ressalvas = ''
        if args.ressalvas:
            ressalvas = open(args.ressalvas, encoding='utf-8').read()
        for caminho_md, caminho_pdf in kpi_relatorio.gerar(
                linhas, apuracao, periodo=f'{inicio.strftime("%d/%m/%Y")} a '
                                          f'{fim.strftime("%d/%m/%Y")}',
                oabs=oabs, pasta=pasta, sufixo=sufixo,
                ressalvas_extra=ressalvas):
            print(f'    [ok] {os.path.basename(caminho_md)}'
                  + (f'  ->  {os.path.basename(caminho_pdf)}' if caminho_pdf else
                     '  (PDF nao gerado)'))


# ============================================================
# COMANDO: vault - Banco de teses (Obsidian) alimentado pela automacao
# ============================================================

def cmd_vault(args):
    """Gera as notas de caso e de orgao julgador do vault em BASE_CONHECIMENTO/.

    Somente leitura em DJEN/ADVBOX/Drive; a unica escrita e' de arquivo .md
    dentro do vault, e so com --gravar e confirmacao. A automacao e' dona
    apenas do bloco marcado de cada nota - o texto humano nunca e' tocado.
    """
    import vault_obsidian

    if args.csv is not None:
        caminho = args.csv or vault_obsidian.ultimo_csv()
        if not caminho or not os.path.exists(caminho):
            print('\n  ERRO: nenhum CSV de KPI encontrado. Rode antes:')
            print('     python OPERACIONAL/main.py kpi --de AAAA-MM-DD --ate AAAA-MM-DD '
                  '--csv saida.csv')
            return
        print(f'\n  Lendo a apuracao ja gravada em {caminho}')
        print('  (CSV nao carrega o texto do ato: sem ele nao ha extracao de magistrado, '
              'e a tese so sai quando o grupo do ADVBOX a nomeia.)')
        linhas = vault_obsidian.carregar_csv(caminho)
        fonte = f'CSV de KPI: {caminho}'
    else:
        oabs = _oabs_monitoradas()
        if not oabs:
            print('\n  ERRO: nenhuma OAB configurada em config/equipe.py (OABS_MONITORADAS).')
            return
        if args.de:
            inicio = datetime.strptime(args.de, '%Y-%m-%d').date()
            fim = datetime.strptime(args.ate, '%Y-%m-%d').date() if args.ate else datetime.now().date()
        else:
            fim = datetime.now().date()
            inicio = fim - timedelta(days=int(args.dias or 7) - 1)

        print('=' * 100)
        print('  VAULT - CAPTURA AO VIVO (DJEN + ADVBOX)')
        print('=' * 100)
        print(f'\n  Periodo: {inicio.isoformat()} a {fim.isoformat()}')

        import kpi_exito
        resumos, lawsuits = _capturar_djen_advbox(inicio, fim, oabs)
        if not resumos:
            return
        linhas = kpi_exito.avaliar_lote(resumos, lawsuits, oabs)

        # O texto integral so existe aqui (o CSV nao o carrega) - e' dele que
        # saem o orgao, a tese pelo texto e a assinatura do magistrado.
        textos = {}
        for r in resumos:
            chave = (''.join(filter(str.isdigit, r.get('processo') or '')), r.get('data'))
            if len(r.get('texto') or '') > len(textos.get(chave) or ''):
                textos[chave] = r.get('texto')
        for l in linhas:
            chave = (''.join(filter(str.isdigit, l.get('processo') or '')), l.get('data'))
            l['_texto'] = textos.get(chave, '')
        fonte = f'DJEN ao vivo, {inicio.isoformat()} a {fim.isoformat()}'

    vault_obsidian.executar(linhas, vault=args.vault or vault_obsidian.VAULT_PADRAO,
                            incluir_fora_escopo=args.incluir_fora_escopo,
                            fonte=fonte, gravar_=args.gravar)


# ============================================================
# COMANDO: advbox - Diagnostico da integracao
# ============================================================

def cmd_advbox(args):
    """Confere token, conexao e se os IDs de config/equipe.py batem com a conta."""
    print('=' * 80)
    print('  DIAGNOSTICO DA INTEGRACAO ADVBOX')
    print('=' * 80)

    if not os.getenv('ADVBOX_API_TOKEN'):
        print('\n  [X] ADVBOX_API_TOKEN nao encontrado.')
        print('      Crie config/.env a partir de config/.env.example e cole o token')
        print('      fornecido pela ADVBOX na linha ADVBOX_API_TOKEN=')
        return
    print('\n  [ok] Token carregado do config/.env')

    if not advbox.testar_conexao():
        return

    # Os IDs em config/equipe.py sao usados como "from"/"guests" em toda tarefa
    # criada. Se estiverem errados, a API rejeita com 422 so na hora de gravar -
    # melhor descobrir aqui.
    settings = advbox.carregar_settings()
    ids_conta = {u['id']: u['name'] for u in settings.get('users', [])}
    print('\n  Conferindo config/equipe.py -> USUARIOS_ADVBOX:')
    for papel, uid in _usuarios().items():
        try:
            uid_int = int(uid)
        except (TypeError, ValueError):
            print(f'    [X] {papel:15} nao preenchido')
            continue
        if uid_int in ids_conta:
            print(f'    [ok] {papel:15} {uid_int} = {ids_conta[uid_int]}')
        else:
            print(f'    [X] {papel:15} {uid_int} NAO existe nesta conta ADVBOX')

    _conferir_controllers(ids_conta)


def cmd_sync(args):
    """Integracao SYNC (Atende Direito): monitoramento processual.

    Somente leitura. As rotas de escrita do Sync (ciencia de prazo, marcar
    intimacao como tratada, criar monitor, registrar webhook) ficam atras da
    trava SYNC_PERMITIR_ESCRITA e nao sao expostas aqui de proposito - ciencia
    e' ato da controller, nao da automacao."""
    acao = getattr(args, 'acao', None) or 'diagnostico'

    if acao == 'diagnostico':
        print('=' * 80)
        print('  DIAGNOSTICO DA INTEGRACAO SYNC (ATENDE DIREITO)')
        print('=' * 80)
        print()
        if not os.getenv('SYNC_API_TOKEN'):
            print('  [X] SYNC_API_TOKEN nao encontrado em config/.env')
            print('      1. Entre em https://sync.atendedireito.app (conta do escritorio)')
            print('      2. Aba API -> gerar chave (formato sk_live_...)')
            print('      3. Cole em config/.env na linha SYNC_API_TOKEN=')
            print()
            print('      Enquanto isso, a triagem segue capturando pelo DJEN como sempre.')
            return
        print('  [ok] Chave carregada do config/.env')
        if not sync.testar_conexao():
            return
        print()
        print('  Cobertura da carteira monitorada no Sync:')
        try:
            monitores = sync.listar_monitores()
            if not monitores:
                print('    [X] Nenhum monitor cadastrado: o Sync nao esta acompanhando nada.')
                print('        Sem monitor de OAB nao ha intimacao para capturar.')
            for m in monitores:
                achatado = sync._achatar(m)
                tipo = sync._primeiro(achatado, 'tipo') or '?'
                valor = sync._primeiro(achatado, 'valor') or '?'
                qtd = sync._primeiro(achatado, 'processos', 'total_processos', 'qtd') or '-'
                print(f'    [ok] {tipo}={valor}  ({qtd} processo(s))')
        except sync.SyncError as e:
            print(f'    Falha ao listar monitores: {e}')
        _conferir_oabs_no_sync()
        return

    if acao == 'inspecionar':
        sync.inspecionar(recurso=args.recurso, quantidade=int(args.quantidade or 1))
        return

    if acao == 'painel':
        _imprimir_painel_sync()
        return

    if acao == 'intimacoes':
        resumos = sync.intimacoes_para_triagem(
            dias=int(args.dias or 1), acionaveis=not args.todas,
            teor_integral=not args.rapido)
        if not resumos:
            print('\n  Nenhuma intimacao acionavel no periodo.')
            return
        print(f'\n  {len(resumos)} intimacao(oes):')
        for r in resumos:
            marca = ' [TEXTO CORTADO]' if r.get('texto_truncado') else ''
            print(f"\n  [{str(r['data'])[:10]}] {r['tribunal']} - {r['tipo']}{marca}")
            print(f"    Processo: {r['processo']}")
            if r.get('sync_data_fatal'):
                print(f"    Prazo Sync (CPC): {r['sync_data_fatal']} "
                      f"[{r.get('sync_obrigacao_estado') or '-'}] "
                      f"- NAO substitui o cotejo do ED (POP-CJ-003-A)")
            print(f"    Trecho:   {(r['texto'] or '')[:200].replace(chr(10), ' ')}...")
        return

    if acao == 'prazos':
        prazos = sync.listar_prazos(estado=args.estado, de=args.de, ate=args.ate)
        if not prazos:
            print('\n  Nenhum prazo no filtro informado.')
            return
        print(f'\n  {len(prazos)} prazo(s) [{args.estado}]:')
        print('  LEMBRETE: a data fatal abaixo e o prazo do recurso PRINCIPAL calculado')
        print('  pelo Sync. O POP-CJ-003-A exige cotejo INICIAL x DECISAO antes: havendo')
        print('  contradicao/obscuridade/omissao, o prazo que vale e o do ED (5 dias uteis).')
        for p in prazos:
            achatado = sync._achatar(p)
            print(f"\n    Fatal {sync._primeiro(achatado, 'data_fatal', 'vencimento') or '?'} "
                  f"| {sync._primeiro(achatado, 'estado', 'obrigacao_estado') or '-'}")
            print(f"      Processo: {sync._primeiro(achatado, 'processo', 'numero_processo') or '?'}")
            print(f"      Ato:      {sync._primeiro(achatado, 'tipo_ato', 'descricao', 'tipo') or '-'}")
        return

    if acao == 'autos':
        texto = sync.autos_markdown(args.processo)
        if args.saida:
            with open(args.saida, 'w', encoding='utf-8') as fh:
                fh.write(texto)
            print(f'  Autos salvos em {args.saida} ({len(texto)} caracteres).')
            print('  Lembre: e o espelho do Sync, nao certidao dos autos - citacao em')
            print('  peca se confere contra o processo.')
        else:
            print(texto[:6000])
            if len(texto) > 6000:
                print(f'\n  ... (+{len(texto) - 6000} caracteres; use --saida para o arquivo inteiro)')
        return

    if acao == 'webhooks':
        inscricoes = sync.listar_webhooks()
        if not inscricoes:
            print('\n  Nenhum webhook registrado.')
            print('  Registrar exige URL publica HTTPS + segredo HMAC e a trava')
            print('  SYNC_PERMITIR_ESCRITA=1. Ver docs/INTEGRACAO_SYNC.md.')
            return
        for w in inscricoes:
            achatado = sync._achatar(w)
            print(f"\n  {sync._primeiro(achatado, 'nome') or '(sem nome)'}")
            print(f"    URL:      {sync._primeiro(achatado, 'url')}")
            print(f"    Eventos:  {sync._primeiro(achatado, 'eventos') or 'todos'}")
            print(f"    Ativo:    {sync._primeiro(achatado, 'ativo')}")
            print(f"    Assinado: {'sim' if sync._primeiro(achatado, 'tem_secret', 'secret') else 'NAO - sem HMAC'}")
        return


def _conferir_oabs_no_sync():
    """As OABs de config/equipe.py sao as do DJEN. Confere se o Sync monitora as
    mesmas - carteira diferente significa triagem com cobertura diferente."""
    oabs = _oabs_monitoradas()
    if not oabs:
        return
    try:
        monitores = sync.listar_monitores()
    except sync.SyncError:
        return
    monitorados = set()
    for m in monitores:
        achatado = sync._achatar(m)
        if str(sync._primeiro(achatado, 'tipo')).lower() == 'oab':
            monitorados.add(''.join(filter(str.isalnum,
                            str(sync._primeiro(achatado, 'valor')).upper())))
    print('\n  OABS_MONITORADAS (config/equipe.py) x monitores do Sync:')
    for numero, uf in oabs:
        alvo = f'{uf}{numero}'.upper()
        alvo_inv = f'{numero}{uf}'.upper()
        if alvo in monitorados or alvo_inv in monitorados:
            print(f'    [ok] OAB {numero}/{uf} monitorada no Sync')
        else:
            print(f'    [X] OAB {numero}/{uf} NAO tem monitor no Sync - '
                  f'as intimacoes dela nao entram pela fonte Sync.')


def _imprimir_painel_sync():
    """Painel do dia do Sync, em uma chamada."""
    dados = sync.dashboard()
    print('=' * 80)
    print('  PAINEL DO DIA - SYNC')
    print('=' * 80)
    if not isinstance(dados, dict):
        print(dados)
        return
    # O painel e' um bloco consolidado; imprime o que vier, sem presumir o
    # nome exato de cada chave (o Swagger nao tipa a resposta).
    for chave, valor in dados.items():
        if isinstance(valor, (int, float, str)) or valor is None:
            print(f'\n  {chave}: {valor}')
        elif isinstance(valor, list):
            print(f'\n  {chave}: {len(valor)} item(ns)')
            for item in valor[:5]:
                print(f'    - {json.dumps(item, ensure_ascii=False)[:220]}')
        elif isinstance(valor, dict):
            print(f'\n  {chave}:')
            for k2, v2 in list(valor.items())[:12]:
                print(f'    {k2}: {json.dumps(v2, ensure_ascii=False)[:180]}')


def _conferir_controllers(ids_conta):
    """Confere o mapa CONTROLLERS de config/equipe.py contra os usuarios reais
    da conta: e' esse mapa que decide quem lanca (`from`) e quem recebe
    (`guests`) cada tarefa de intimacao."""
    controllers = getattr(equipe, 'CONTROLLERS', None) if equipe else None
    if not controllers:
        print('\n  [X] config/equipe.py -> CONTROLLERS vazio: nenhuma tarefa de '
              'intimacao sera criada (a automacao nao chuta controller).')
        return

    print('\n  Conferindo config/equipe.py -> CONTROLLERS (quem lanca a intimacao):')
    for chave, dados in controllers.items():
        uid, erro = roteamento.id_da_controller(chave)
        origem = 'id fixo' if (dados.get('id')) else 'resolvido pelo nome'
        if uid and int(uid) in ids_conta:
            print(f'    [ok] {chave:10} {uid} = {ids_conta[int(uid)]} ({origem})')
        elif uid:
            print(f'    [X] {chave:10} {uid} NAO existe nesta conta ADVBOX')
        else:
            print(f'    [X] {chave:10} {erro}')

        for entrada in dados.get('advogados', []):
            nome_mapa, adv_id = roteamento._entrada_advogado(entrada)
            adv_id = adv_id or roteamento.id_usuario_por_nome(nome_mapa)
            if adv_id and int(adv_id) in ids_conta:
                print(f'         [ok] {str(adv_id):>7} = {ids_conta[int(adv_id)]}')
            else:
                print(f'         [X] {nome_mapa:35} sem ID valido nos usuarios do ADVBOX - '
                      f'ajustar em config/equipe.py')


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Squad Controladoria + Divida Rural - Maldonado Advogados')
    subparsers = parser.add_subparsers(dest='comando')

    p_triagem = subparsers.add_parser('triagem', help='[PRIORIDADE] Triagem de intimacoes/publicacoes (DJEN ou Sync)')
    p_triagem.add_argument('--dias', '-d', default=7, help='Ultimos N dias (default: 7)')
    p_triagem.add_argument('--criar-tarefa', action='store_true',
                            help='Oferece criar tarefa no ADVBOX para itens de prioridade alta (com confirmacao)')
    p_triagem.add_argument('--fonte', choices=['djen', 'sync', 'ambas'], default='djen',
                            help='De onde vem a intimacao: djen (padrao, fonte historica), '
                                 'sync (Atende Direito, ja deduplicado por ato) ou ambas '
                                 '(captura nas duas e unifica o ato repetido)')

    p_rotina = subparsers.add_parser('rotina',
        help='[08:00] Rodada diaria da Controladoria: captura, triagem, prazos D-5/D-3, tarefas e relatorio')
    p_rotina.add_argument('--dias', '-d', default=1,
                          help='Ultimos N dias de publicacao (default: 1; na segunda, usar 3)')
    p_rotina.add_argument('--gravar', action='store_true',
                          help='Cria as tarefas no ADVBOX. Sem isso, so simula e imprime o plano')
    p_rotina.add_argument('--planilha', action='store_true',
                          help='Acrescenta a rodada na planilha de conferencia da ZEUS '
                               '(CONTROLADORIA > RELATORIOS DIARIOS) - usar na semana de teste')
    p_rotina.add_argument('--sem-drive', action='store_true',
                          help='Nao tocar no Google Drive (relatorio so local + ADVBOX)')

    p_desp = subparsers.add_parser('despachos',
        help='Controle de despachos (POP-CJ-DESP-001): protocolos-gatilho x despacho, na planilha do Drive')
    p_desp.add_argument('--dias', '-d', default=1, help='Ultimos N dias (default: 1)')
    p_desp.add_argument('--de', help='Data inicial AAAA-MM-DD')
    p_desp.add_argument('--ate', help='Data final AAAA-MM-DD')
    p_desp.add_argument('--gravar', action='store_true',
                        help='Escreve na planilha do Drive (sem isso, so simula)')

    p_intake = subparsers.add_parser('intake', help='Squad Comercial: leads do Atende Direito -> ADVBOX')
    p_intake.add_argument('--dias', '-d', default=7, help='Ultimos N dias (default: 7)')
    p_intake.add_argument('--etapa', help='Etapa/coluna do pipeline no Atende Direito '
                                          '(default: ATENDE_DIREITO_ETAPA_QUALIFICADO do .env)')
    p_intake.add_argument('--integrar', action='store_true',
                          help='Cadastra os leads novos no ADVBOX (confirmacao lead a lead)')
    p_intake.add_argument('--com-drive', action='store_true',
                          help='Tambem cria a pasta do cliente na estrutura ZEUS do Drive')
    p_intake.add_argument('--tipo-processo',
                          help='Tipo de processo no ADVBOX (default: ADVBOX_TIPO_PROCESSO_PADRAO)')
    p_intake.add_argument('--sem-tarefa', action='store_true',
                          help='Nao abrir tarefa de conferencia para a Controladoria')
    p_intake.add_argument('--inspecionar', action='store_true',
                          help='Imprime o JSON cru dos leads para calibrar o mapa de campos')
    p_intake.add_argument('--inspecionar-qtd', default=1, help='Quantos leads inspecionar (default: 1)')

    p_tarefas = subparsers.add_parser('tarefas', help='Listar tarefas pendentes')
    p_tarefas.add_argument('--dias', '-d', help='Dias a frente (default: 14)')

    p_procs = subparsers.add_parser('processos', help='Listar processos ativos')
    p_procs.add_argument('--responsavel', '-r', help='Filtrar por responsavel')

    subparsers.add_parser('prazos', help='Listar prazos fatais proximos')

    subparsers.add_parser('advbox', help='Diagnostico da integracao ADVBOX (token, conexao, IDs da equipe)')

    p_sync = subparsers.add_parser(
        'sync', help='SYNC (Atende Direito) - monitoramento processual: intimacoes, prazos, autos')
    sync_sub = p_sync.add_subparsers(dest='acao')
    sync_sub.add_parser('diagnostico', help='Confere chave, conta, monitores e cobertura das OABs (default)')
    sync_sub.add_parser('painel', help='Painel do dia do Sync numa chamada')

    p_sync_int = sync_sub.add_parser('intimacoes', help='Intimacoes acionaveis, com teor integral')
    p_sync_int.add_argument('--dias', '-d', default=1, help='Ultimos N dias (default: 1)')
    p_sync_int.add_argument('--todas', action='store_true',
                            help='Inclui o que ja teve ciencia ou decorreu')
    p_sync_int.add_argument('--rapido', action='store_true',
                            help='Nao abre cada intimacao (texto fica cortado em 600 caracteres)')

    p_sync_pz = sync_sub.add_parser('prazos', help='Prazos (obrigacoes) deduplicados por ato')
    p_sync_pz.add_argument('--estado', default='acionaveis',
                           choices=['acionaveis', 'abertas', 'vencidas', 'leitura'])
    p_sync_pz.add_argument('--de', help='Data fatal a partir de (AAAA-MM-DD)')
    p_sync_pz.add_argument('--ate', help='Data fatal ate (AAAA-MM-DD)')

    p_sync_au = sync_sub.add_parser('autos', help='Autos completos em Markdown (insumo de leitura/jurimetria)')
    p_sync_au.add_argument('processo', help='Numero do processo (CNJ, com ou sem mascara)')
    p_sync_au.add_argument('--saida', '-o', help='Salvar em arquivo .md')

    sync_sub.add_parser('webhooks', help='Lista os webhooks registrados na conta')

    p_sync_insp = sync_sub.add_parser('inspecionar', help='JSON cru do Sync (calibrar o adaptador)')
    p_sync_insp.add_argument('--recurso', default='intimacoes',
                             choices=['intimacoes', 'prazos', 'processos', 'monitores', 'webhooks'])
    p_sync_insp.add_argument('--quantidade', '-n', default=1, help='Quantos registros mostrar')

    p_apont = subparsers.add_parser(
        'apontamentos',
        help='Base de apontamentos da Gerencia Juridica (o que a GJ devolve nas pecas)')
    p_apont.add_argument('--dias', type=int, default=90, help='Periodo em dias (padrao: 90)')
    p_apont.add_argument('--de', help='Data inicial AAAA-MM-DD (sobrepoe --dias)')
    p_apont.add_argument('--ate', help='Data final AAAA-MM-DD')
    p_apont.add_argument('--csv', help='Grava a base classificada neste arquivo .csv')
    p_apont.add_argument('--pausa', type=float, default=2.1,
                         help='Segundos entre chamadas (GET 30/min na ADVBOX)')

    p_kpi = subparsers.add_parser(
        'kpi',
        help='Taxa de Exito Ponderado a partir das intimacoes do periodo (somente leitura)')
    p_kpi.add_argument('--dias', type=int, default=7, help='Periodo em dias (padrao: 7)')
    p_kpi.add_argument('--de', help='Data inicial AAAA-MM-DD (sobrepoe --dias)')
    p_kpi.add_argument('--ate', help='Data final AAAA-MM-DD')
    p_kpi.add_argument('--csv', help='Grava a apuracao linha a linha neste arquivo .csv')
    p_kpi.add_argument('--ressalvas', metavar='ARQUIVO.md',
                       help='Anexa este trecho de Markdown ao relatorio executivo (as '
                            'ressalvas da competencia, escritas pela GJ)')
    p_kpi.add_argument('--planilha', action='store_true',
                       help='Atualiza a planilha da competencia no Drive (por semana, por '
                            'carteira, por advogado) - config/equipe.py KPI_PLANILHA_PASTA_ID')
    p_kpi.add_argument('--pdf', nargs='?', const='docs/kpi_exito', metavar='PASTA',
                       help='Gera os tres relatorios (executivo, anexo, fichas) em .md e .pdf '
                            '(padrao: docs/kpi_exito)')

    p_vault = subparsers.add_parser(
        'vault',
        help='Banco de teses (Obsidian): gera notas de caso e de orgao julgador')
    p_vault.add_argument('--dias', type=int, default=7,
                         help='Periodo da captura ao vivo, em dias (padrao: 7)')
    p_vault.add_argument('--de', help='Data inicial AAAA-MM-DD (sobrepoe --dias)')
    p_vault.add_argument('--ate', help='Data final AAAA-MM-DD')
    p_vault.add_argument('--csv', nargs='?', const='', metavar='ARQUIVO.csv',
                         help='Le de um CSV de KPI ja gravado em vez de consultar o DJEN '
                              '(sem valor: o mais recente de docs/kpi_exito/)')
    p_vault.add_argument('--vault', metavar='PASTA',
                         help='Raiz do vault (padrao: BASE_CONHECIMENTO/)')
    p_vault.add_argument('--incluir-fora-escopo', action='store_true',
                         help='Tambem gera nota de despacho/expediente (padrao: so decisao)')
    p_vault.add_argument('--gravar', action='store_true',
                         help='Grava as notas (ainda pede confirmacao s/N)')

    p_criar = subparsers.add_parser('criar-tarefa', help='Criar tarefa no ADVBOX')
    p_criar.add_argument('processo', help='ID do processo no ADVBOX')
    p_criar.add_argument('tipo', help='Tipo da tarefa (ex: ACOMPANHAMENTO)')
    p_criar.add_argument('para', nargs='?',
                         help='Destinatario (chave em config/equipe.py, ex: RESPONSAVEL). '
                              'Omitido: vai para o advogado responsavel pelo processo')
    p_criar.add_argument('--mensagem', '-m', help='Comentario da tarefa')
    p_criar.add_argument('--prazo', '-p', help='Prazo fatal (YYYY-MM-DD)')
    p_criar.add_argument('--urgente', action='store_true', help='Marcar como urgente')

    p_drive = subparsers.add_parser('drive', help='Google Drive - estrutura ZEUS do escritorio')
    drive_sub = p_drive.add_subparsers(dest='acao')
    drive_sub.add_parser('autenticar', help='Conecta (ou confere) a conta Google do escritorio')
    drive_sub.add_parser('sair', help='Revoga o acesso e apaga config/token.json (trocar de conta)')
    drive_sub.add_parser('testar', help='Confere acesso a ZEUS > 03. CLIENTES > 01 CLIENTES')

    p_drive_cli = drive_sub.add_parser('cliente', help='Localiza (ou cria) a pasta de um cliente')
    p_drive_cli.add_argument('nome', help='Nome do cliente, como esta no Drive')
    p_drive_cli.add_argument('--criar', action='store_true',
                             help='Cria a pasta + 4 subpastas se nao existir (pede confirmacao)')

    p_drive_env = drive_sub.add_parser('enviar', help='Envia um arquivo para a pasta do cliente')
    p_drive_env.add_argument('arquivo', help='Caminho do arquivo local')
    p_drive_env.add_argument('--cliente', '-c', required=True, help='Nome do cliente')
    p_drive_env.add_argument('--subpasta', '-s',
                             help='Subpasta destino (ex: "DOC PESSOAL"); default = raiz do cliente')
    p_drive_env.add_argument('--converter', action='store_true',
                             help='Converte .docx para Google Docs no envio')

    p_drive_peca = drive_sub.add_parser(
        'peca', help='Arquiva a peca produzida em ZEUS > PEÇAS AUTOMAÇÃO > [CLIENTE] - [PROCESSO]')
    p_drive_peca.add_argument('arquivo', help='Caminho da peca produzida (.docx)')
    p_drive_peca.add_argument('--cliente', '-c', required=True, help='Nome do cliente')
    p_drive_peca.add_argument('--processo', '-p',
                              help='Numero do processo (CNJ). Sem ele, a pasta vai como SEM PROCESSO')
    p_drive_peca.add_argument('--converter', action='store_true',
                              help='Converter para Google Docs (revisao a varias maos)')

    p_gmail = subparsers.add_parser('gmail', help='Gmail (somente leitura) - buscar e baixar e-mails')
    gmail_sub = p_gmail.add_subparsers(dest='acao')
    gmail_sub.add_parser('autenticar', help='Autoriza a leitura do Gmail (token proprio)')
    p_gmail_busca = gmail_sub.add_parser('buscar', help='Busca com a sintaxe do Gmail')
    p_gmail_busca.add_argument('consulta', help='Ex.: "reuniao estrategica Agenor has:attachment"')
    p_gmail_busca.add_argument('-n', '--limite', type=int, default=20)
    p_gmail_baixa = gmail_sub.add_parser('baixar', help='Salva corpo e anexos em _trabalho/emails/<id>/')
    p_gmail_baixa.add_argument('id', help='ID da mensagem (sai no buscar)')
    p_gmail_baixa.add_argument('--destino', help='Pasta local de destino')

    # ---- anexos: documentos da peticao inicial (Squad Divida Rural) ----
    p_anx = subparsers.add_parser(
        'anexos', help='Documentos da inicial: inventario do cliente, recorte e montagem')
    anx_sub = p_anx.add_subparsers(dest='acao')

    p_anx_inv = anx_sub.add_parser('inventario',
                                   help='Lista e classifica os documentos da pasta do cliente')
    p_anx_inv.add_argument('--cliente', '-c', required=True, help='Nome do cliente na ZEUS')

    p_anx_conf = anx_sub.add_parser(
        'conferir', help='Cruza a pasta do cliente com o rol de documentos da tese')
    p_anx_conf.add_argument('--cliente', '-c', required=True, help='Nome do cliente na ZEUS')
    p_anx_conf.add_argument('--acao-peca', '-a', required=True, choices=sorted(anexos.ACOES),
                            help='Tese da inicial (define o rol exigido)')

    p_anx_bx = anx_sub.add_parser('baixar', help='Baixa os documentos para o diretorio de trabalho')
    p_anx_bx.add_argument('--cliente', '-c', required=True, help='Nome do cliente na ZEUS')
    p_anx_bx.add_argument('--acao-peca', '-a', choices=sorted(anexos.ACOES),
                          help='Baixar tudo que a tese pede (obrigatorios + recomendados)')
    p_anx_bx.add_argument('--tipo', '-t', action='append',
                          help='Baixar so um tipo (repetivel). Ex: --tipo cedula --tipo ficha-grafica')
    p_anx_bx.add_argument('--destino', '-d', help='Diretorio local (default: _trabalho/anexos/CLIENTE)')

    p_anx_ph = anx_sub.add_parser('placeholders',
                                  help='Lista os marcadores a preencher no modelo/peca (.docx)')
    p_anx_ph.add_argument('arquivo', help='Caminho do .docx')

    p_anx_loc = anx_sub.add_parser('localizar',
                                   help='Em que pagina do PDF esta o termo (antes de recortar)')
    p_anx_loc.add_argument('arquivo', help='Caminho do PDF')
    p_anx_loc.add_argument('--buscar', '-b', action='append', help='Termo a procurar (repetivel)')
    p_anx_loc.add_argument('--tipo', '-t', help='Usar os termos padrao do tipo (ex: cedula)')

    p_anx_rec = anx_sub.add_parser('recorte', help='Gera o PNG do documento para colar na peca')
    p_anx_rec.add_argument('arquivo', help='Caminho do PDF (ou imagem) de origem')
    p_anx_rec.add_argument('--saida', '-o', required=True, help='Caminho do PNG a gerar')
    p_anx_rec.add_argument('--pagina', '-p', help='Pagina do PDF (1-based)')
    p_anx_rec.add_argument('--buscar', '-b', action='append',
                           help='Recortar so a regiao ao redor do termo (repetivel)')
    p_anx_rec.add_argument('--tipo', '-t', help='Usar os termos padrao do tipo (ex: cedula)')
    p_anx_rec.add_argument('--pagina-inteira', action='store_true',
                           help='Renderizar a pagina toda, sem recortar a regiao')
    p_anx_rec.add_argument('--dpi', default=200, help='Resolucao (default: 200)')
    p_anx_rec.add_argument('--margem', default=1.0, help='Folga ao redor do termo, em cm (default: 1.0)')
    p_anx_rec.add_argument('--realcar', '-r', action='append',
                           help='Grifar este trecho em amarelo NA IMAGEM (repetivel). '
                                'A legenda TEM de trazer "grifo nosso".')
    p_anx_rec.add_argument('--largura-total', action='store_true',
                           help='Recortar so na vertical, mantendo a largura da pagina')

    p_anx_ins = anx_sub.add_parser('inserir', help='Troca o placeholder da peca pelo recorte')
    p_anx_ins.add_argument('arquivo', help='Caminho da peca (.docx)')
    p_anx_ins.add_argument('--placeholder', '-m', required=True,
                           help='Texto do marcador a substituir (ex: "INSERIR UMA IMAGEM.")')
    p_anx_ins.add_argument('--imagem', '-i', required=True, help='PNG do recorte')
    p_anx_ins.add_argument('--legenda', '-l', help='Legenda, inserida ACIMA da imagem (ex: "Imagem 03. Cédula ..., fl. 2 (grifo nosso)")')
    p_anx_ins.add_argument('--largura', help='Largura em cm (default: a mancha da pagina)')
    p_anx_ins.add_argument('--saida', '-o', help='Salvar em outro arquivo (default: sobrescreve)')

    p_anx_pen = anx_sub.add_parser(
        'pendencia', help='Documento inexistente: marca o placeholder em amarelo')
    p_anx_pen.add_argument('arquivo', help='Caminho da peca (.docx)')
    p_anx_pen.add_argument('--placeholder', '-m', required=True, help='Texto do marcador')
    p_anx_pen.add_argument('--texto', help='Texto da pendencia (default: aviso padrao)')
    p_anx_pen.add_argument('--saida', '-o', help='Salvar em outro arquivo (default: sobrescreve)')

    args = parser.parse_args()

    if args.comando == 'triagem':
        cmd_triagem(args)
    elif args.comando == 'rotina':
        cmd_rotina(args)
    elif args.comando == 'despachos':
        cmd_despachos(args)
    elif args.comando == 'intake':
        cmd_intake(args)
    elif args.comando == 'tarefas':
        cmd_tarefas(args)
    elif args.comando == 'processos':
        cmd_processos(args)
    elif args.comando == 'prazos':
        cmd_prazos(args)
    elif args.comando == 'advbox':
        cmd_advbox(args)
    elif args.comando == 'sync':
        try:
            cmd_sync(args)
        except sync.SyncError as e:
            print(f'\n  {e}')
    elif args.comando == 'apontamentos':
        cmd_apontamentos(args)
    elif args.comando == 'kpi':
        cmd_kpi(args)
    elif args.comando == 'vault':
        cmd_vault(args)
    elif args.comando == 'criar-tarefa':
        cmd_criar_tarefa(args)
    elif args.comando == 'drive':
        if not args.acao:
            p_drive.print_help()
        else:
            cmd_drive(args)
    elif args.comando == 'gmail':
        if not args.acao:
            p_gmail.print_help()
        else:
            cmd_gmail(args)
    elif args.comando == 'anexos':
        if not args.acao:
            p_anx.print_help()
        else:
            cmd_anexos(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
