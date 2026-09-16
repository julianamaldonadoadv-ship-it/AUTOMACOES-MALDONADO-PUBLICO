"""
=============================================================================
  SQUAD COMERCIAL/INTAKE - Atende Direito -> ADVBOX -> Drive
=============================================================================

  Pega os leads ja qualificados no Atende Direito e transforma em cliente +
  processo no ADVBOX, com a pasta do cliente na estrutura ZEUS do Drive.

  Regra de ouro do projeto: nada e gravado sem confirmacao explicita. O modo
  padrao e so relatorio; a gravacao exige --integrar E um "s" por lead.
=============================================================================
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

import advbox_integration as advbox
import atende_direito_integration as atende
import roteamento_controller as roteamento

try:
    import equipe
except ImportError:
    equipe = None


# ============================================================
# COLETA
# ============================================================

def coletar_leads(dias=7, etapa=None):
    """Busca no Atende Direito os leads dos ultimos N dias e normaliza."""
    fim = datetime.now().date()
    inicio = fim - timedelta(days=max(int(dias), 1) - 1)
    brutos = atende.listar_leads(
        etapa=etapa, desde=inicio.isoformat(), ate=fim.isoformat()
    )
    return [atende.normalizar_lead(b) for b in brutos], inicio, fim


def _cliente_existente(lead):
    """Procura o lead no ADVBOX por CPF (e, na falta dele, por nome exato)."""
    if lead.get('cpf'):
        achados = advbox.buscar_cliente(cpf=lead['cpf'])
        if achados:
            return achados[0]
    if lead.get('nome'):
        achados = advbox.buscar_cliente(nome=lead['nome'])
        for c in achados or []:
            if str(c.get('name', '')).strip().upper() == lead['nome'].strip().upper():
                return c
    return None


def analisar(leads):
    """
    Classifica cada lead em: 'ja_existe', 'pendente' (falta dado) ou 'novo'.
    Faz a consulta ao ADVBOX aqui para o relatorio sair completo antes de gravar.
    """
    analisados = []
    for lead in leads:
        pendencias = atende.validar_lead(lead)
        existente = None
        if not pendencias:
            try:
                existente = _cliente_existente(lead)
            except Exception as e:
                pendencias.append(f'falha ao consultar ADVBOX: {e}')

        if pendencias:
            situacao = 'pendente'
        elif existente:
            situacao = 'ja_existe'
        else:
            situacao = 'novo'

        analisados.append({
            'lead': lead,
            'situacao': situacao,
            'pendencias': pendencias,
            'cliente_advbox': existente,
        })
    return analisados


# ============================================================
# RELATORIO
# ============================================================

def imprimir_relatorio(analisados, inicio, fim):
    print('=' * 80)
    print('  INTAKE ATENDE DIREITO - MALDONADO ADVOGADOS')
    print('=' * 80)
    print(f'\n  Periodo: {inicio.isoformat()} a {fim.isoformat()}')
    print(f'  Leads recebidos: {len(analisados)}')

    for chave, rotulo in (('novo', 'NOVOS - prontos para cadastrar'),
                          ('ja_existe', 'JA CADASTRADOS no ADVBOX'),
                          ('pendente', 'PENDENTES - falta dado, nao cadastrar')):
        grupo = [a for a in analisados if a['situacao'] == chave]
        if not grupo:
            continue
        print(f'\n  --- {rotulo} ({len(grupo)}) ---')
        for item in grupo:
            lead = item['lead']
            print(f"\n    {lead['nome'] or '(sem nome)'}")
            print(f"      CPF: {lead['cpf'] or '-'} | Tel: {lead['telefone'] or '-'} "
                  f"| {lead['email'] or '-'}")
            print(f"      Etapa: {lead['etapa'] or '-'} | Origem: {lead['origem'] or '-'} "
                  f"| Lead ID: {lead['lead_id'] or '-'}")
            if lead.get('resumo'):
                print(f"      Resumo: {str(lead['resumo'])[:120]}")
            if item['cliente_advbox']:
                print(f"      >> Ja existe no ADVBOX (ID {item['cliente_advbox'].get('id')})")
            if item['pendencias']:
                print(f"      >> Pendencias: {'; '.join(item['pendencias'])}")


# ============================================================
# GRAVACAO (sempre com confirmacao)
# ============================================================

def _usuarios():
    if equipe and equipe.USUARIOS_ADVBOX:
        return equipe.USUARIOS_ADVBOX
    return {
        'RESPONSAVEL': os.getenv('ADVBOX_USER_RESPONSAVEL'),
        'OUTRO_ADVOGADO': os.getenv('ADVBOX_USER_OUTRO_ADVOGADO'),
        'GERENCIA_JURIDICA': os.getenv('ADVBOX_USER_GERENCIA_JURIDICA'),
    }


def _criar_pasta_drive(nome_cliente):
    """Cria a pasta do cliente na estrutura ZEUS. Import tardio: o intake sem
    --com-drive nao deve exigir credencial Google."""
    import google_integration as g
    drive_service, _ = g.autenticar_google()
    existente = g.pasta_do_cliente(drive_service, nome_cliente)
    if existente:
        print(f"      Pasta ja existe: {g.link_pasta(existente['id'])}")
        return existente['id']
    cliente_id, subpastas = g.criar_estrutura_cliente(drive_service, nome_cliente)
    print(f'      Pasta criada: {g.link_pasta(cliente_id)}')
    for sub in subpastas:
        print(f'        {sub}')
    return cliente_id


def integrar(analisados, com_drive=False, tipo_processo=None, criar_tarefa=True):
    """
    Para cada lead 'novo': cadastra cliente, cadastra processo, cria pasta no
    Drive (opcional) e abre tarefa de conferencia para a Controladoria.
    Cada lead pede confirmacao individual - nunca grava em lote.
    """
    usuarios = _usuarios()
    responsavel_id = usuarios.get('RESPONSAVEL')
    if not responsavel_id:
        print('\n  ERRO: config/equipe.py -> USUARIOS_ADVBOX["RESPONSAVEL"] nao preenchido. '
              'Sem isso nao da pra cadastrar nem criar tarefa.')
        return

    novos = [a for a in analisados if a['situacao'] == 'novo']
    if not novos:
        print('\n  Nenhum lead novo para integrar.')
        return

    tipo_processo = tipo_processo or os.getenv('ADVBOX_TIPO_PROCESSO_PADRAO', 'CIVEL')
    print(f'\n  {len(novos)} lead(s) novo(s) para integrar '
          f'(tipo de processo: {tipo_processo}).')

    for item in novos:
        lead = item['lead']
        print(f"\n  ------------------------------------------------------------")
        print(f"  Lead: {lead['nome']} | CPF {lead['cpf']}")
        print(f"  Sera criado no ADVBOX: cliente + processo ({tipo_processo})")
        if com_drive:
            print(f"  E a pasta do cliente na estrutura ZEUS do Drive")
        if criar_tarefa:
            print(f"  E uma tarefa de conferencia para a controller do processo")
        if input('  Confirma? (s/N): ').strip().lower() != 's':
            print('  Pulado.')
            continue

        try:
            resultado_cliente = advbox.cadastrar_cliente(lead, user_id=responsavel_id)
        except Exception as e:
            print(f'  Erro ao cadastrar cliente: {e}')
            continue
        if not resultado_cliente or not resultado_cliente.get('customers_id'):
            print('  Cliente nao foi cadastrado - lead pulado.')
            continue
        cliente_id = resultado_cliente['customers_id']

        dados_processo = {
            'tipo': tipo_processo,
            'notas': _nota_do_lead(lead),
        }
        lawsuit_id = None
        try:
            resultado_processo = advbox.cadastrar_processo(
                cliente_id, dados_processo, user_id=responsavel_id
            )
            lawsuit_id = (resultado_processo or {}).get('lawsuits_id')
        except Exception as e:
            print(f'  Erro ao cadastrar processo: {e}')

        if com_drive:
            try:
                _criar_pasta_drive(lead['nome'])
            except Exception as e:
                print(f'  Erro ao criar pasta no Drive: {e}')

        if criar_tarefa and lawsuit_id:
            try:
                # A conferencia do cadastro e' trabalho da Controladoria: quem
                # lanca e recebe e' a controller do processo (regra da Dra.
                # Juliana, 10/09/2026 - a gerencia juridica nao entra na fila).
                rot = roteamento.resolver(lawsuit=advbox.obter_processo(lawsuit_id))
                if not rot['ok']:
                    print(f"  Controller nao definida ({rot['motivo']}) - "
                          f"tarefa de conferencia NAO criada.")
                    raise RuntimeError('sem controller para a tarefa de conferencia')
                lancador_id = rot['from_id']
                destino_id = rot['guest_id']
                print(f"  Tarefa de conferencia: {rot['controller_nome']}.")
                settings = advbox.carregar_settings()
                task_id = (advbox.buscar_id_por_nome('tasks', 'ANALISE')
                           or advbox.buscar_id_por_nome('tasks', 'ACOMPANHAMENTO')
                           or (settings.get('tasks') or [{}])[0].get('id'))
                advbox.criar_publicacao(
                    lawsuit_id=lawsuit_id, task_id=task_id,
                    guest_ids=[destino_id],
                    comments=f'[Intake Atende Direito] Conferir cadastro e documentos.\n'
                             f'{_nota_do_lead(lead)}',
                    from_id=lancador_id,
                )
                print('  Tarefa de conferencia criada para a Controladoria.')
            except RuntimeError:
                pass          # motivo ja impresso acima
            except Exception as e:
                print(f'  Erro ao criar tarefa: {e}')

        if lead.get('lead_id'):
            try:
                atende.marcar_lead_integrado(
                    lead['lead_id'],
                    observacao=f'Cliente ADVBOX {cliente_id}'
                               + (f' / processo {lawsuit_id}' if lawsuit_id else ''),
                )
            except Exception as e:
                print(f'  Aviso: nao consegui marcar o lead como integrado: {e}')


def _nota_do_lead(lead):
    """Texto de rastreio: de onde veio o cliente, para a nota do processo/tarefa."""
    partes = [
        f"Origem: Atende Direito (lead {lead.get('lead_id') or 's/ID'})",
        f"Canal: {lead.get('origem') or '-'}",
        f"Etapa: {lead.get('etapa') or '-'}",
        f"Atendente: {lead.get('responsavel') or '-'}",
    ]
    if lead.get('criado_em'):
        partes.append(f"Criado em: {lead['criado_em']}")
    if lead.get('resumo'):
        partes.append(f"Resumo do atendimento: {lead['resumo']}")
    return ' | '.join(partes)
