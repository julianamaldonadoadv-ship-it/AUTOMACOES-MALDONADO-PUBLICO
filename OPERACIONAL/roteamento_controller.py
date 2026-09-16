# -*- coding: utf-8 -*-
"""
Roteamento CONTROLLER x ADVOGADO RESPONSAVEL - Maldonado Advogados
==================================================================

Regra da Dra. Juliana (10/09/2026): a tarefa de intimacao no ADVBOX nao e' mais
lancada em nome do Dr. Renan. Quem lanca (campo `from` do /posts) e' a
CONTROLLER do advogado responsavel pelo processo; quem recebe (guests) e' o
proprio advogado responsavel.

    Controller NATALY   -> Arilson, Mailson, Josue Kalebe, Heloisa, Agenor
    Controller MANUELLE -> Bruno, Felipe Narcisio, Matheus, Taynara, Ana Sheila

O mapa vive em `config/equipe.py` (CONTROLLERS) - este modulo so resolve.

Duas coisas que este modulo NUNCA faz:
  - chutar controller quando o advogado responsavel nao esta no mapa, esta
    ambiguo ou o processo esta sem responsavel no ADVBOX. Devolve ok=False com
    o motivo, e quem chamou decide (na triagem, nao cria a tarefa e sinaliza);
  - gravar qualquer coisa no ADVBOX. So le settings/lawsuits.
"""
import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

import advbox_integration as advbox

try:
    import equipe
except ImportError:
    equipe = None


# ============================================================
# NORMALIZACAO E MATCH DE NOME
# ============================================================

def _norm(texto):
    """Sem acento, caixa alta, espacos colapsados. Nome de usuario no ADVBOX
    vem com acentuacao inconsistente e espaco sobrando - mesma politica do
    google_integration para pasta do Drive."""
    if not texto:
        return ''
    sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    )
    return ' '.join(sem_acento.upper().split())


def _tokens(texto):
    return [t for t in _norm(texto).split(' ') if t]


def _casa_nome(apelido, nome_completo):
    """True se TODOS os tokens do apelido aparecem no nome completo.
    "FELIPE NARCISIO" casa com "Felipe Narcisio da Silva"; "BRUNO" casa com
    "Bruno Vinicius de Souza Faustino". Token e' comparado inteiro (nao
    substring) pra "ANA" nao casar com "ANALICE"."""
    alvo = set(_tokens(nome_completo))
    pedidos = _tokens(apelido)
    return bool(pedidos) and all(p in alvo for p in pedidos)


# ============================================================
# MAPA CONTROLLERS (config/equipe.py)
# ============================================================

def _controllers():
    return (getattr(equipe, 'CONTROLLERS', None) or {}) if equipe else {}


def _entrada_advogado(item):
    """Uma entrada de CONTROLLERS[x]["advogados"] e' {"nome":..., "id":...} (o
    caso normal, com o ID conferido na conta) ou so a string do nome (white-label
    ainda nao calibrado). Devolve sempre (nome, id_ou_None)."""
    if isinstance(item, dict):
        return item.get('nome') or '', item.get('id')
    return item or '', None


def controller_do_advogado(nome_advogado, advogado_id=None):
    """Devolve (chave_da_controller, motivo). chave None quando nao da' pra
    decidir - motivo explica por que (para sair no relatorio).

    O ID manda: se o processo trouxe o ID do responsavel e ele esta no mapa, a
    grafia do nome nao importa. So sem ID e' que o match cai no nome."""
    controllers = _controllers()
    if not controllers:
        return None, 'config/equipe.py -> CONTROLLERS vazio'

    if advogado_id:
        for chave, dados in controllers.items():
            for entrada in dados.get('advogados', []):
                _, uid = _entrada_advogado(entrada)
                if uid and str(uid) == str(advogado_id):
                    return chave, ''

    if not nome_advogado:
        if advogado_id:
            return None, (f'advogado ID {advogado_id} nao esta em CONTROLLERS '
                          f'(config/equipe.py)')
        return None, 'processo sem advogado responsavel no ADVBOX'

    achados = []
    for chave, dados in controllers.items():
        for entrada in dados.get('advogados', []):
            nome_mapa, _ = _entrada_advogado(entrada)
            if _casa_nome(nome_mapa, nome_advogado) or _casa_nome(nome_advogado, nome_mapa):
                achados.append(chave)
                break

    if not achados:
        return None, f'advogado "{nome_advogado}" nao esta em CONTROLLERS (config/equipe.py)'
    if len(achados) > 1:
        return None, (f'advogado "{nome_advogado}" casou com mais de uma controller '
                      f'({", ".join(achados)}) - desambiguar em config/equipe.py')
    return achados[0], ''


# ============================================================
# RESOLUCAO DE ID NO ADVBOX
# ============================================================

_cache_id_por_nome = {}
_settings_indisponivel = False


def id_usuario_por_nome(nome):
    """ID ADVBOX a partir do nome, pelas settings da conta. Match por tokens,
    e ambiguidade (dois usuarios casando) devolve None de proposito - lancar
    tarefa no ID errado e' pior que nao lancar.

    Nao confundir com advbox.buscar_id_por_nome, que faz substring e devolve o
    primeiro que casar."""
    global _settings_indisponivel
    chave = _norm(nome)
    if not chave or _settings_indisponivel:
        return None
    if chave in _cache_id_por_nome:
        return _cache_id_por_nome[chave]

    try:
        usuarios = advbox.listar_settings_tipo('users') or []
    except (Exception, SystemExit):
        # sem token/conexao o advbox_integration chama sys.exit(1) - aqui isso
        # nao pode derrubar a triagem inteira, so impede resolver o ID pelo nome.
        # Marca a indisponibilidade para nao repetir a tentativa (e o ruido) a
        # cada item da triagem.
        _settings_indisponivel = True
        return None

    casaram = [u for u in usuarios if _casa_nome(nome, u.get('name', ''))]
    uid = casaram[0].get('id') if len(casaram) == 1 else None
    _cache_id_por_nome[chave] = uid
    return uid


def id_da_controller(chave):
    """ID ADVBOX da controller: o de config/equipe.py se preenchido, senao
    resolvido pelo nome nas settings."""
    dados = _controllers().get(chave) or {}
    if dados.get('id'):
        return dados['id'], ''
    nome = dados.get('nome') or chave
    uid = id_usuario_por_nome(nome)
    if not uid:
        return None, (f'controller {chave}: nao achei "{nome}" nos usuarios do ADVBOX '
                      f'(ou ha mais de um com esse nome) - preencher "id" em config/equipe.py')
    return uid, ''


# ============================================================
# ADVOGADO RESPONSAVEL DO PROCESSO (payload do /lawsuits)
# ============================================================

def responsavel_do_lawsuit(lawsuit):
    """Extrai (nome, id) do advogado responsavel pelo processo.

    No GET /lawsuits conferido na conta do escritorio (10/09/2026) vem o par
    `responsible` (nome, string) + `responsible_id` (int) - nao `users_id`,
    que e' o campo de ESCRITA do cadastro de processo. Aceita tambem dict e
    lista porque outras rotas da API devolvem o responsavel aninhado."""
    if not lawsuit:
        return None, None

    for campo, campo_id in (('responsible', 'responsible_id'),
                            ('user', 'user_id'),
                            ('lawyer', 'lawyer_id')):
        valor = lawsuit.get(campo)
        if isinstance(valor, dict):
            return valor.get('name'), valor.get('id')
        if isinstance(valor, str) and valor.strip():
            return valor.strip(), (lawsuit.get(campo_id) or lawsuit.get('users_id'))

    usuarios = lawsuit.get('users')
    if isinstance(usuarios, list) and usuarios:
        primeiro = usuarios[0]
        if isinstance(primeiro, dict):
            return primeiro.get('name'), primeiro.get('id')

    users_id = lawsuit.get('responsible_id') or lawsuit.get('users_id')
    if users_id:
        try:
            todos = advbox.listar_settings_tipo('users') or []
        except (Exception, SystemExit):
            todos = []
        for u in todos:
            if str(u.get('id')) == str(users_id):
                return u.get('name'), u.get('id')
        return None, users_id

    return None, None


# ============================================================
# RESOLUCAO COMPLETA (o que main.py e intake usam)
# ============================================================

# ============================================================
# PROCESSO ARQUIVADO
# ============================================================

def processo_arquivado(lawsuit):
    """Processo arquivado/encerrado no ADVBOX.

    Levantado na carteira real (3.004 processos, 10/09/2026): o ADVBOX marca
    isso em dois campos que nem sempre concordam - `step` (agrupador macro,
    "ARQUIVAMENTO") e `stage` (a fase, "ARQUIVADO/ENCERRADO", "ARQUIVADO POR
    DESINTERESSE CLIENTE", "ARQUIVADO - RESCISAO"...). Ha 55 processos com
    step=ARQUIVAMENTO e stage que nao comeca com ARQUIVAD (48 deles
    "CRIADO EQUIVOCADAMENTE") - esses tambem nao devem gerar agendamento,
    por isso o OR e nao o AND.

    `status_closure` (data de encerramento) NAO serve sozinho: 648 processos
    tem data e continuam fora do arquivamento."""
    if not lawsuit:
        return False
    if _norm(lawsuit.get('step')) == 'ARQUIVAMENTO':
        return True
    return _norm(lawsuit.get('stage')).startswith('ARQUIVAD')


def _controller_pelo_id(advogado_id):
    """A propria controller como responsavel pelo processo (Nataly responde por
    186 processos, Manuelle por 80). Nesse caso ela lanca para si mesma."""
    if not advogado_id:
        return None
    for chave, dados in _controllers().items():
        if dados.get('id') and str(dados['id']) == str(advogado_id):
            return chave
    return None


def _e_direcao(advogado_id, nome_advogado):
    """Dr. Renan / Dra. Juliana como responsaveis pelo processo
    (config/equipe.py -> RESPONSAVEIS_DIRECAO)."""
    ids = [str(i) for i in ((getattr(equipe, 'RESPONSAVEIS_DIRECAO', None) or [])
                            if equipe else [])]
    if not ids:
        return False
    if advogado_id and str(advogado_id) in ids:
        return True
    # Sem ID no processo: resolve o ID pelo nome antes de comparar - nome de
    # direcao nao entra em CONTROLLERS, entao nao ha risco de conflito.
    if nome_advogado:
        uid = id_usuario_por_nome(nome_advogado)
        return bool(uid) and str(uid) in ids
    return False


def id_do_advogado_no_mapa(chave_controller, nome_advogado):
    """ID do advogado direto do mapa de config/equipe.py, quando o processo nao
    trouxe o ID junto."""
    dados = _controllers().get(chave_controller) or {}
    for entrada in dados.get('advogados', []):
        nome_mapa, uid = _entrada_advogado(entrada)
        if uid and (_casa_nome(nome_mapa, nome_advogado) or _casa_nome(nome_advogado, nome_mapa)):
            return uid
    return None


def resolver(lawsuit=None, nome_advogado=None, advogado_id=None):
    """Resolve quem lanca e quem recebe a tarefa de um processo.

    Ordem das regras (Dra. Juliana, 10/09/2026):
      1. responsavel = controller -> ela lanca para si mesma
      2. responsavel = direcao    -> a controller da direcao assume (Dr. Renan e
                                     Dra. Juliana nao tratam intimacao)
      3. responsavel no mapa      -> a controller dele lanca, ele recebe
      4. qualquer outro caso      -> a controller de fallback assume

    O tratamento de intimacao e' SEMPRE de uma controller. A gerencia juridica
    (Dra. Juliana) nao entra em nenhuma dessas rotas.

    Processo arquivado nao muda o destino - so acende a flag `arquivado`, que o
    relatorio mostra para a controller conferir antes de agendar.

    Devolve dict:
        ok               True so quando ha quem lance E quem receba
        controller       chave da controller ('NATALY'/'MANUELLE') ou None
        controller_nome  nome para o relatorio
        from_id          ID ADVBOX de quem lanca (campo 'from' do /posts)
        advogado         nome do advogado responsavel pelo processo
        guest_id         ID ADVBOX de quem recebe a tarefa
        arquivado        processo arquivado/encerrado no ADVBOX
        regra            qual das regras acima decidiu
        motivo           por que nao deu, quando ok=False
    """
    if lawsuit is not None and not nome_advogado:
        nome_advogado, advogado_id = responsavel_do_lawsuit(lawsuit)

    saida = {
        'ok': False, 'controller': None, 'controller_nome': None,
        'from_id': None, 'advogado': nome_advogado, 'guest_id': advogado_id,
        'arquivado': processo_arquivado(lawsuit), 'regra': None, 'motivo': '',
        'observacao': '',
    }

    # O nome so serve para o relatorio quando ha ID - a busca vai pelo ID.
    if not nome_advogado and advogado_id:
        saida['advogado'] = f'ID {advogado_id}'

    # 1. A propria controller e' a responsavel pelo processo
    chave_ctrl = _controller_pelo_id(advogado_id) or (
        _controller_pelo_nome(nome_advogado) if not advogado_id else None)
    if chave_ctrl:
        dados = _controllers().get(chave_ctrl) or {}
        saida.update({
            'ok': bool(dados.get('id')), 'controller': chave_ctrl,
            'controller_nome': dados.get('nome') or chave_ctrl,
            'from_id': dados.get('id'), 'guest_id': dados.get('id'),
            'regra': 'controller e a responsavel pelo processo',
        })
        if not saida['ok']:
            saida['motivo'] = f'controller {chave_ctrl} sem ID em config/equipe.py'
        return saida

    # 2. Direcao (Dr. Renan / Dra. Juliana) como responsavel: nenhum dos dois
    #    trata intimacao, entao a controller da direcao lanca e recebe
    if _e_direcao(advogado_id, nome_advogado):
        chave_dir = (getattr(equipe, 'CONTROLLER_DA_DIRECAO', None) if equipe else None)
        return _controller_assume(saida, chave_dir,
                                  'responsavel e a direcao/gerencia',
                                  'CONTROLLER_DA_DIRECAO')

    # 3. Advogado no mapa: a controller dele lanca, ele recebe
    chave, motivo = controller_do_advogado(nome_advogado, advogado_id)
    if not chave:
        # 4. Fallback: a controller de plantao assume (lanca e recebe)
        return _fallback(saida, motivo)

    saida['controller'] = chave
    saida['controller_nome'] = (_controllers().get(chave) or {}).get('nome') or chave
    saida['regra'] = 'controller do advogado responsavel'

    from_id, erro = id_da_controller(chave)
    if not from_id:
        saida['motivo'] = erro
        return saida
    saida['from_id'] = from_id

    if not saida['guest_id']:
        saida['guest_id'] = (id_do_advogado_no_mapa(chave, nome_advogado)
                             or id_usuario_por_nome(nome_advogado))
    if not saida['guest_id']:
        saida['motivo'] = (f'advogado "{nome_advogado}" sem ID no ADVBOX '
                           f'(nao achei nos usuarios da conta, ou ha homonimo)')
        return saida

    saida['ok'] = True
    return saida


def _controller_pelo_nome(nome_advogado):
    for chave, dados in _controllers().items():
        if _casa_nome(dados.get('nome') or chave, nome_advogado):
            return chave
    return None


def _controller_assume(saida, chave, regra, nome_da_config):
    """Rota em que a controller lanca E recebe (nao ha advogado a quem
    enderecar): direcao como responsavel, ou responsavel fora do mapa."""
    saida['regra'] = regra
    if not chave:
        saida['motivo'] = (saida.get('observacao') or
                           f'{nome_da_config} nao definido em config/equipe.py')
        return saida

    dados = _controllers().get(chave) or {}
    if not dados.get('id'):
        saida['motivo'] = (f'controller {chave} ({nome_da_config}) esta sem ID '
                           f'em config/equipe.py')
        return saida

    saida.update({
        'ok': True, 'controller': chave,
        'controller_nome': dados.get('nome') or chave,
        'from_id': dados['id'], 'guest_id': dados['id'],
    })
    return saida


def _fallback(saida, motivo):
    """Responsavel fora do mapa: a controller de fallback assume o item - ela
    lanca E recebe. O motivo original fica em `observacao`, para o relatorio
    dizer de quem era o processo."""
    saida['observacao'] = motivo
    chave = (getattr(equipe, 'CONTROLLER_FALLBACK', None) if equipe else None)
    return _controller_assume(saida, chave, 'fallback: responsavel fora do mapa',
                              'CONTROLLER_FALLBACK')


def descrever(resultado):
    """Uma linha para o relatorio de triagem."""
    prefixo = 'PROCESSO ARQUIVADO - ' if resultado.get('arquivado') else ''
    if resultado.get('ok'):
        if resultado.get('regra') == 'responsavel e a direcao/gerencia':
            return (f"{prefixo}Controller {resultado['controller_nome']} assume "
                    f"(processo da direcao/gerencia: {resultado.get('advogado') or '-'})")
        if resultado.get('regra') == 'controller e a responsavel pelo processo':
            return f"{prefixo}Controller {resultado['controller_nome']} lanca para si mesma"
        if resultado.get('regra') == 'fallback: responsavel fora do mapa':
            return (f"{prefixo}Controller {resultado['controller_nome']} assume "
                    f"(responsavel do processo: {resultado.get('advogado') or '-'}"
                    f" — fora do mapa de controllers)")
        return (f"{prefixo}Controller {resultado['controller_nome']} lanca para "
                f"{resultado['advogado']}")
    return (f"{prefixo}CONTROLLER A DEFINIR - "
            f"{resultado.get('motivo') or 'sem motivo informado'}")
