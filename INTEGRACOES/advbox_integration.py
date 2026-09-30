"""
Integração com API ADVBOX - Maldonado Advogados
Módulo para cadastro de clientes, processos e transações financeiras.

API Base: https://app.advbox.com.br/api/v1
Auth: Bearer Token
Rate limits: GET 30/min, POST 500/day
"""
import os
import sys
import time
import json
import unicodedata
import requests
from functools import lru_cache


def _sem_acento(texto):
    """Remove acentos e coloca em maiusculo para comparacoes robustas."""
    nfd = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').upper()


def formatar_amount(valor):
    """
    Converte um valor monetario para o formato que o POST/PUT /transactions exige.

    A API usa VIRGULA como separador decimal e DESCARTA o ponto:
    enviar 1500.50 (float JSON) vira 150050 no ADVBOX - erro de 100x.
    Ver doc v1.21.0 (createTransaction/updateTransaction).

    >>> formatar_amount(1500.5)
    '1.500,50'
    >>> formatar_amount('250,50')
    '250,50'
    """
    if isinstance(valor, str):
        v = valor.strip()
        # Ja veio no formato brasileiro ("1.500,50" ou "250,50") - repassa.
        if ',' in v:
            return v
        # String com ponto decimal ("1500.50") - converte.
        valor = float(v.replace('.', '') if v.count('.') > 1 else v)
    return '{:,.2f}'.format(float(valor)).replace(',', '#').replace('.', ',').replace('#', '.')


def formatar_telefone(valor):
    """
    Normaliza telefone para o formato aceito pelo POST /customers.

    A API quer o numero LOCAL com DDD, sem o codigo do pais: com '+55' o
    contato e' criado, mas o telefone vira 'ERROR'; sem DDD retorna 422.
    Ver doc v1.22.0 (createCustomer).

    Retorna (digitos, campo_api) onde campo_api e' 'phone' (fixo, 10 digitos)
    ou 'cellphone' (celular, 11 digitos). Retorna (None, None) se invalido.
    """
    digitos = ''.join(filter(str.isdigit, str(valor)))
    # Remove o codigo do pais quando presente (55 + 10 ou 11 digitos)
    if len(digitos) in (12, 13) and digitos.startswith('55'):
        digitos = digitos[2:]
    if len(digitos) == 11:
        return digitos, 'cellphone'
    if len(digitos) == 10:
        return digitos, 'phone'
    return None, None


ADVBOX_BASE_URL = 'https://app.advbox.com.br/api/v1'

# Cache local do settings (IDs de referência)
_settings_cache = None
_settings_timestamp = 0
CACHE_TTL = 3600  # 1 hora


def _get_token():
    token = os.getenv('ADVBOX_API_TOKEN')
    if not token:
        print('ERRO: ADVBOX_API_TOKEN nao encontrado no .env')
        sys.exit(1)
    return token


def _headers():
    return {
        'Authorization': f'Bearer {_get_token()}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Maldonado-Advogados/1.0',
    }


def _request(method, endpoint, params=None, json_data=None, retries=2):
    """Faz request com retry e tratamento de rate limit."""
    url = f'{ADVBOX_BASE_URL}{endpoint}'
    for tentativa in range(retries + 1):
        try:
            resp = requests.request(
                method, url, headers=_headers(),
                params=params, json=json_data, timeout=30
            )
            if resp.status_code == 429:
                wait = int(resp.headers.get('Retry-After', 10))
                print(f'  Rate limit atingido. Aguardando {wait}s...')
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json() if resp.text else {}
        except requests.exceptions.HTTPError as e:
            print(f'  ADVBOX API erro ({resp.status_code}): {resp.text}')
            if tentativa < retries and resp.status_code >= 500:
                time.sleep(3)
                continue
            raise
        except requests.exceptions.RequestException as e:
            print(f'  ADVBOX conexao falhou: {e}')
            if tentativa < retries:
                time.sleep(3)
                continue
            raise
    return None


# ============================================================
# SETTINGS - Dados de referência (chamar 1x e cachear)
# ============================================================

def _normalizar_settings(data):
    """
    Normaliza o schema do /settings do ADVBOX para o formato que o modulo espera.

    A API agrupa banks/categories/cost_centers/departments dentro de 'financial'
    e usa 'lawsuit_types' (nao 'type_lawsuits'). Aqui achatamos para o topo e
    criamos o alias, para que todos os helpers funcionem sem alteracao.
    """
    if not isinstance(data, dict):
        return data
    financial = data.get('financial')
    if isinstance(financial, dict):
        for chave in ('banks', 'categories', 'cost_centers', 'departments'):
            if chave in financial and chave not in data:
                data[chave] = financial[chave]
    # Alias: o modulo usa 'type_lawsuits', a API retorna 'lawsuit_types'
    if 'lawsuit_types' in data and 'type_lawsuits' not in data:
        data['type_lawsuits'] = data['lawsuit_types']
    return data


def carregar_settings(force=False):
    """Carrega e cacheia settings do ADVBOX (users, origins, stages, types, banks, categories, cost_centers)."""
    global _settings_cache, _settings_timestamp
    if not force and _settings_cache and (time.time() - _settings_timestamp) < CACHE_TTL:
        return _settings_cache
    print('  Carregando settings ADVBOX...')
    data = _request('GET', '/settings')
    data = _normalizar_settings(data)
    _settings_cache = data
    _settings_timestamp = time.time()
    return data


def email_usuario(user_id):
    """E-mail do usuario ADVBOX (settings['users']), em minusculas; None se nao achar.

    Usado para liberar edicao da peca ao advogado responsavel no Drive
    (google_integration.liberar_edicao). O e-mail vem do cadastro do ADVBOX,
    nunca de mapa proprio: pessoa entra e sai da equipe e o ADVBOX e' a fonte.
    """
    for u in carregar_settings().get('users', []) or []:
        if str(u.get('id')) == str(user_id):
            email = (u.get('email') or '').strip().lower()
            return email or None
    return None


def buscar_id_por_nome(tipo, nome_parcial):
    """Busca ID em settings por nome parcial. tipo: 'users', 'origins', 'stages', 'categories', etc."""
    settings = carregar_settings()
    items = settings.get(tipo, [])
    nome_upper = nome_parcial.upper()
    # Mapear campo de nome conforme o tipo
    campo = {
        'users': 'name', 'origins': 'origin', 'stages': 'stage',
        'type_lawsuits': 'type', 'lawsuit_types': 'type',
        'banks': 'name', 'categories': 'category',
        'cost_centers': 'cost_center', 'departments': 'department'
    }.get(tipo, 'name')
    for item in items:
        if nome_upper in str(item.get(campo, '')).upper():
            return item['id']
    return None


def listar_settings_tipo(tipo):
    """Lista todos os itens de um tipo de settings para debug."""
    settings = carregar_settings()
    return settings.get(tipo, [])


# ============================================================
# CLIENTES
# ============================================================

def buscar_cliente(cpf=None, nome=None):
    """Busca cliente no ADVBOX por CPF ou nome."""
    params = {}
    if cpf:
        params['identification'] = cpf
    if nome:
        params['name'] = nome
    data = _request('GET', '/customers', params=params)
    clientes = data.get('data', [])
    return clientes


def obter_cliente(cliente_id):
    """Obtém dados completos de um cliente pelo ID."""
    return _request('GET', f'/customers/{cliente_id}')


def cadastrar_cliente(dados_cliente, user_id=None, origin_id=None):
    """
    Cadastra novo cliente no ADVBOX.

    dados_cliente: dict com campos do cliente (nome, cpf, email, telefone, etc.)
    user_id: ID do usuário responsável (se None, busca nas settings)
    origin_id: ID da origem (se None, busca 'INDICACAO')

    Retorna: {'success': True, 'customers_id': 12345678} ou None
    """
    settings = carregar_settings()

    if not user_id:
        users = settings.get('users', [])
        user_id = users[0]['id'] if users else None

    if not origin_id:
        origin_id = buscar_id_por_nome('origins', 'INDICA')
        if not origin_id:
            origins = settings.get('origins', [])
            origin_id = origins[0]['id'] if origins else None

    nome = dados_cliente.get('nome', '').strip()
    if not nome:
        print('ERRO: Nome do cliente e obrigatorio')
        return None

    # Verificar duplicidade por CPF
    cpf = dados_cliente.get('cpf', '')
    if cpf:
        existentes = buscar_cliente(cpf=cpf)
        if existentes:
            print(f'  Cliente ja existe no ADVBOX (ID: {existentes[0]["id"]}): {existentes[0]["name"]}')
            return {'success': True, 'customers_id': existentes[0]['id'], 'ja_existia': True}

    payload = {
        'users_id': user_id,
        'customers_origins_id': origin_id,
        'name': nome,
    }

    # Campos opcionais
    # Telefones: a API separa fixo (phone, 10 digitos) de celular (cellphone, 11).
    # O campo de destino e' decidido pela quantidade de digitos, nao pelo nome
    # do campo local - planilhas do escritorio misturam os dois.
    for campo_local in ('telefone', 'celular', 'telefone_fixo', 'whatsapp'):
        bruto = dados_cliente.get(campo_local, '')
        if not bruto:
            continue
        numero, campo_api = formatar_telefone(bruto)
        if not numero:
            print('  AVISO: telefone "%s" ignorado (precisa de DDD, sem o +55)' % bruto)
            continue
        payload.setdefault(campo_api, numero)

    mapa = {
        'cpf': 'identification',
        'email': 'email',
        'rg': 'document',
        'data_nascimento': 'birthdate',
        'sexo': 'gender',
        'profissao': 'occupation',
        'rua': 'street',
        'bairro': 'region',
        'cidade': 'city',
        'estado': 'state',
        'cep': 'postalcode',
        'estado_civil': 'civil_status',
        'ctps': 'number_ctps',
        'pis': 'number_pis',
    }

    for campo_local, campo_api in mapa.items():
        valor = dados_cliente.get(campo_local, '')
        if valor:
            # Ajustes de formato
            if campo_api == 'birthdate' and '/' in str(valor):
                # DD/MM/YYYY -> YYYY-MM-DD
                partes = str(valor).split('/')
                if len(partes) == 3:
                    valor = f'{partes[2]}-{partes[1]}-{partes[0]}'
            if campo_api == 'state' and len(str(valor)) > 2:
                # Truncar para 2 letras (UF)
                valor = str(valor)[:2].upper()
            if campo_api == 'gender':
                valor = 'M' if str(valor).upper().startswith('M') else 'F'
            # CEP deve ter hífen (99999-999)
            if campo_api == 'postalcode':
                valor = str(valor).replace('-', '').replace('.', '').strip()
                if len(valor) == 8:
                    valor = f'{valor[:5]}-{valor[5:]}'
            payload[campo_api] = valor

    # Endereco completo -> separar se veio como campo unico
    endereco = dados_cliente.get('endereco', '')
    if endereco and 'street' not in payload:
        payload['street'] = endereco

    print(f'  Cadastrando cliente no ADVBOX: {nome}...')
    resultado = _request('POST', '/customers', json_data=payload)
    if resultado and resultado.get('success'):
        print(f'  Cliente cadastrado! ID: {resultado["customers_id"]}')
    return resultado


# ============================================================
# PROCESSOS (LAWSUITS)
# ============================================================

def buscar_processo(cliente_id=None, numero_processo=None, nome=None):
    """Busca processos no ADVBOX."""
    params = {}
    if cliente_id:
        params['customer_id'] = cliente_id
    if numero_processo:
        params['process_number'] = numero_processo
    if nome:
        params['name'] = nome
    data = _request('GET', '/lawsuits', params=params)
    return data.get('data', [])


def obter_processo(lawsuit_id):
    """
    Obtem os dados completos de um processo pelo ID (GET /lawsuits/{id}).

    Traz mais campos que a listagem: honorarios (fees_expec/fees_money),
    contingencia, grupo, etapa (step) e o array de clientes com CPF/CNPJ.
    Retorna None se o processo nao existir (a API responde 404).
    """
    try:
        return _request('GET', f'/lawsuits/{lawsuit_id}')
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise


def listar_processos(filtros=None, limit=1000):
    """
    Lista processos do escritorio com paginacao completa (GET /lawsuits).

    Diferente de buscar_processo(), que devolve so a primeira pagina, aqui
    percorremos ate o totalCount - necessario para o comando `processos`,
    que precisa da carteira inteira.

    limit=1000 (o default da API) e' proposital: a carteira tem ~3.000
    processos, entao com limit=100 seriam 30 requests - exatamente o teto de
    30 GET/min, batendo em 429 junto com qualquer outra chamada do mesmo
    minuto. Com 1000 sao 3 requests.
    """
    params = dict(filtros or {})
    todos = []
    params['offset'] = 0
    params['limit'] = limit
    while True:
        data = _request('GET', '/lawsuits', params=params)
        registros = data.get('data', [])
        todos.extend(registros)
        total = data.get('totalCount', 0)
        if len(todos) >= total or not registros:
            break
        params['offset'] += limit
    return todos


def cadastrar_processo(cliente_id, dados_processo, user_id=None):
    """
    Cadastra novo processo no ADVBOX.

    dados_processo: dict com campos (tipo, empresa_reclamada, etc.)
    Retorna: {'success': True, 'lawsuits_id': 12345} ou None
    """
    settings = carregar_settings()

    if not user_id:
        users = settings.get('users', [])
        user_id = users[0]['id'] if users else None

    # Tipo do processo: override explicito > busca por nome > TRABALHISTA > primeiro
    tipo_id = dados_processo.get('type_lawsuits_id')
    if not tipo_id and dados_processo.get('tipo'):
        tipo_id = buscar_id_por_nome('type_lawsuits', dados_processo['tipo'])
    if not tipo_id:
        tipo_id = buscar_id_por_nome('type_lawsuits', 'TRABALHISTA')
    if not tipo_id:
        tipos = settings.get('type_lawsuits', [])
        tipo_id = tipos[0]['id'] if tipos else None

    # Fase/stage: override explicito > busca por nome > NEGOCIACAO > primeiro
    stage_id = dados_processo.get('stages_id')
    if not stage_id and dados_processo.get('fase'):
        stage_id = buscar_id_por_nome('stages', dados_processo['fase'])
    if not stage_id:
        stage_id = buscar_id_por_nome('stages', 'NEGOC')
    if not stage_id:
        stages = settings.get('stages', [])
        stage_id = stages[0]['id'] if stages else None

    payload = {
        'users_id': user_id,
        'customers_id': [cliente_id],
        'stages_id': stage_id,
        'type_lawsuits_id': tipo_id,
    }

    if dados_processo.get('numero_processo'):
        payload['process_number'] = dados_processo['numero_processo']
    if dados_processo.get('pasta'):
        payload['folder'] = dados_processo['pasta'][:30]
    if dados_processo.get('notas'):
        payload['notes'] = dados_processo['notas']
    if dados_processo.get('honorarios_esperados'):
        payload['fees_expec'] = dados_processo['honorarios_esperados']

    print(f'  Cadastrando processo no ADVBOX...')
    resultado = _request('POST', '/lawsuits', json_data=payload)
    if resultado and resultado.get('success'):
        print(f'  Processo cadastrado! ID: {resultado["lawsuits_id"]}')
    return resultado


# ============================================================
# TRANSACOES FINANCEIRAS
# ============================================================

def listar_transacoes(filtros=None):
    """
    Lista transacoes financeiras do ADVBOX.

    filtros: dict com campos opcionais:
        - lawsuit_id, category, responsible, customer_name
        - description, process_number, customer_identification (CPF)
        - created_start/end, date_due_start/end, date_payment_start/end (YYYY-MM-DD)
        - competence_start/end (MM/YYYY)
    """
    params = filtros or {}
    todas = []
    offset = 0
    limit = 1000

    while True:
        params['limit'] = limit
        params['offset'] = offset
        data = _request('GET', '/transactions', params=params)
        registros = data.get('data', [])
        todas.extend(registros)
        total = data.get('totalCount', 0)
        print(f'  Transacoes ADVBOX: {len(todas)}/{total}')
        if len(todas) >= total or not registros:
            break
        offset += limit

    return todas


def obter_transacao(transacao_id):
    """Obtém detalhes de uma transação pelo ID."""
    return _request('GET', f'/transactions/{transacao_id}')


def criar_transacao(tipo, valor, data_vencimento, categoria_id, banco_id,
                    centro_custo_id, user_id=None, cliente_id=None,
                    processo_id=None, descricao=None, data_pagamento=None):
    """
    Cria transação financeira no ADVBOX.

    tipo: 'income' (receita/honorario) ou 'expense' (despesa)
    valor: float > 0
    data_vencimento: 'YYYY-MM-DD'
    categoria_id: ID da categoria (CREDITO para income, DEBITO para expense)
    banco_id: ID da conta bancaria (debit_account)
    centro_custo_id: ID do centro de custo
    """
    settings = carregar_settings()

    if not user_id:
        users = settings.get('users', [])
        user_id = users[0]['id'] if users else None

    # amount: a API descarta o ponto decimal (15.00 vira 1500). Sempre string
    # com virgula. E amount == 0 derruba a API com 500 - barrar antes.
    if float(valor) <= 0:
        print('ERRO: valor da transacao deve ser maior que zero')
        return None

    payload = {
        'users_id': user_id,
        'entry_type': tipo,
        'debit_account': banco_id,
        'categories_id': categoria_id,
        'cost_centers_id': centro_custo_id,
        'amount': formatar_amount(valor),
        'date_due': data_vencimento,
    }

    if cliente_id:
        payload['customers_id'] = cliente_id
    if processo_id:
        if not cliente_id:
            print('AVISO: processo_id requer cliente_id no ADVBOX')
        payload['lawsuits_id'] = processo_id
    if descricao:
        payload['description'] = descricao
    if data_pagamento:
        payload['date_payment'] = data_pagamento

    resultado = _request('POST', '/transactions', json_data=payload)
    if resultado and resultado.get('success'):
        print(f'  Transacao criada! ID: {resultado["transactions_id"]} ({tipo}: R$ {valor:,.2f})')
    return resultado


def atualizar_transacao(transacao_id, campos):
    """
    Atualiza transação existente.

    campos: dict com campos a atualizar:
        - amount, date_due, date_payment (ou None para desmarcar)
        - description, competence (MM/YYYY)
        - entry_type + categories_id (devem ser enviados juntos)
    """
    campos = dict(campos or {})
    if 'amount' in campos:
        campos['amount'] = formatar_amount(campos['amount'])
    return _request('PUT', f'/transactions/{transacao_id}', json_data=campos)


# ============================================================
# HELPERS FINANCEIROS
# ============================================================

def buscar_categoria(nome_parcial, tipo_entry='income'):
    """
    Busca categoria financeira por nome.
    tipo_entry: 'income' -> categorias CREDITO, 'expense' -> categorias DEBITO
    """
    settings = carregar_settings()
    # A doc do ADVBOX e' inconsistente: /settings mostra type "income"/"expense",
    # o texto de POST /transactions fala em "CREDITO"/"DEBITO". Aceitamos os dois.
    aceitos = {'income', 'CREDITO'} if tipo_entry == 'income' else {'expense', 'DEBITO'}
    categorias = settings.get('categories', [])
    nome_upper = nome_parcial.upper()

    def _casa(cat):
        t = cat.get('type')
        return t in aceitos or _sem_acento(t) in aceitos

    for cat in categorias:
        if nome_upper in str(cat.get('category', '')).upper() and _casa(cat):
            return cat['id']
    # Fallback: primeira categoria do tipo
    for cat in categorias:
        if _casa(cat):
            return cat['id']
    return None


def buscar_banco(nome_parcial=None):
    """Busca conta bancária nas settings. Se None, retorna a primeira."""
    settings = carregar_settings()
    bancos = settings.get('banks', [])
    if not bancos:
        return None
    if nome_parcial:
        nome_upper = nome_parcial.upper()
        for b in bancos:
            if nome_upper in str(b.get('name', '')).upper():
                return b['id']
    return bancos[0]['id']


def buscar_centro_custo(nome_parcial=None):
    """Busca centro de custo nas settings. Se None, retorna o primeiro."""
    settings = carregar_settings()
    centros = settings.get('cost_centers', [])
    if not centros:
        return None
    if nome_parcial:
        nome_upper = nome_parcial.upper()
        for c in centros:
            if nome_upper in str(c.get('cost_center', '')).upper():
                return c['id']
    return centros[0]['id']


def resumo_financeiro(competencia=None, data_inicio=None, data_fim=None):
    """
    Retorna resumo financeiro do ADVBOX para o periodo.

    competencia: 'MM/YYYY' (ex: '03/2026')
    OU data_inicio/data_fim: 'YYYY-MM-DD'

    Retorna dict com totais e listas separadas.
    """
    filtros = {}
    if competencia:
        filtros['competence_start'] = competencia
        filtros['competence_end'] = competencia
    if data_inicio:
        filtros['date_due_start'] = data_inicio
    if data_fim:
        filtros['date_due_end'] = data_fim

    transacoes = listar_transacoes(filtros)

    receitas = [t for t in transacoes if t.get('entry_type') == 'income']
    despesas = [t for t in transacoes if t.get('entry_type') == 'expense']

    return {
        'total_receitas': sum(t.get('amount', 0) for t in receitas),
        'total_despesas': sum(t.get('amount', 0) for t in despesas),
        'qtd_receitas': len(receitas),
        'qtd_despesas': len(despesas),
        'receitas': receitas,
        'despesas': despesas,
        'todas': transacoes
    }


# ============================================================
# PUBLICACOES (POSTS) - Tarefas e registros
# ============================================================

def criar_publicacao(lawsuit_id, task_id, guest_ids, comments='',
                     from_id=None, date_deadline=None, urgent=False,
                     start_date=None):
    """
    Cria publicação/tarefa no ADVBOX vinculada a um processo.

    lawsuit_id: ID do processo
    task_id: ID do tipo de tarefa (ver settings['tasks'])
    guest_ids: lista de IDs dos destinatarios
    comments: texto da publicação
    from_id: remetente (ID ADVBOX de quem lanca) - DEVE ser string. Sem default:
        em tarefa vinculada a processo, e' a controller do advogado responsavel
        (OPERACIONAL/roteamento_controller.resolver() -> from_id); sem processo,
        config.equipe.USUARIOS_ADVBOX[USUARIO_PADRAO_TAREFAS].
    date_deadline: prazo fatal (YYYY-MM-DD) - opcional
    start_date: DATA DA TAREFA (YYYY-MM-DD): o dia em que a pessoa deve agir e em
        que a tarefa aparece na agenda dela. Se None, usa hoje.

        ATENCAO (apontamento da Dra. Juliana, 23/09/2026): tarefa criada hoje
        para ser feita amanha tem de nascer com start_date do DIA DA ACAO. Com a
        data de hoje e prazo amanha, ela aparece na agenda de HOJE e, ao virar o
        dia, conta como ATRASO do advogado mesmo estando dentro do prazo. As
        rotinas D-5/D-3 do POP seguem nascendo com a data de hoje de proposito,
        porque ali a tarefa deve aparecer antes do prazo; tarefa pontual e' que
        precisa informar o dia.
    """
    if not from_id:
        raise ValueError("from_id obrigatorio - passe o ID ADVBOX do responsavel (config/equipe.py)")
    hoje = time.strftime('%Y-%m-%d')
    if start_date and start_date < hoje:
        print('  AVISO: start_date %s esta no passado; gravando com %s.' % (start_date, hoje))
        start_date = hoje
    if not start_date and date_deadline and date_deadline > hoje:
        print('  AVISO: prazo %s sem start_date. Se a acao e do dia do prazo, passe '
              'start_date=%s para a tarefa nao nascer como atraso na agenda.'
              % (date_deadline, date_deadline))
    payload = {
        'lawsuits_id': str(lawsuit_id),
        'start_date': start_date or hoje,
        'from': str(from_id),
        'guests': guest_ids if isinstance(guest_ids, list) else [guest_ids],
        'tasks_id': str(task_id),
        'comments': comments,
    }
    if date_deadline:
        payload['date_deadline'] = date_deadline
    if urgent:
        payload['urgent'] = True
        payload['important'] = True

    return _request('POST', '/posts', json_data=payload)


def buscar_tipo_tarefa(nome_parcial):
    """Busca ID de tipo de tarefa por nome parcial nas settings."""
    settings = carregar_settings()
    tasks = settings.get('tasks', [])
    nome_upper = nome_parcial.upper()
    for t in tasks:
        if nome_upper in t.get('task', '').upper():
            return t['id']
    return None


# ============================================================
# PROCESSOS - ATUALIZAR (PUT)
# ============================================================

def atualizar_processo(lawsuit_id, campos):
    """
    Atualiza processo existente no ADVBOX.

    campos: dict com campos a atualizar (enviar só o que mudar):
        - stages_id, type_lawsuits_id, users_id (string)
        - process_number, protocol_number, folder (max 30 chars)
        - date, status_closure, exit_production, exit_execution (YYYY-MM-DD ou "" para limpar)
        - notes, fees_expec, fees_money, contingency
    """
    if not campos:
        print('ERRO: Nenhum campo para atualizar')
        return None
    resultado = _request('PUT', f'/lawsuits/{lawsuit_id}', json_data=campos)
    if resultado and resultado.get('success'):
        print(f'  Processo {lawsuit_id} atualizado!')
    return resultado


# ============================================================
# MOVIMENTACOES PROCESSUAIS
# ============================================================

def listar_ultimas_movimentacoes(lawsuit_id=None, process_number=None,
                                 date_start=None, date_end=None):
    """Lista últimas movimentações de todos os processos ou filtrado."""
    params = {}
    if lawsuit_id:
        params['lawsuit_id'] = lawsuit_id
    if process_number:
        params['process_number'] = process_number
    if date_start and date_end:
        params['date_start'] = date_start
        params['date_end'] = date_end
    todas = []
    offset = 0
    while True:
        params['limit'] = 100
        params['offset'] = offset
        data = _request('GET', '/last_movements', params=params)
        registros = data.get('data', [])
        todas.extend(registros)
        total = data.get('totalCount', 0)
        if len(todas) >= total or not registros:
            break
        offset += 100
    return todas


def listar_movimentacoes_processo(lawsuit_id, origin=None):
    """Lista movimentações de um processo específico. origin: 'TRIBUNAL' ou 'MANUAL'."""
    params = {}
    if origin:
        params['origin'] = origin
    data = _request('GET', f'/movements/{lawsuit_id}', params=params)
    return data.get('data', []) if data else []


def criar_movimentacao(lawsuit_id, data_mov, descricao):
    """
    Cria movimentação manual em um processo.

    data_mov: DD/MM/YYYY (formato diferente dos outros endpoints!)
    descricao: mínimo 10 caracteres
    """
    if len(descricao) < 10:
        print('ERRO: Descrição deve ter no mínimo 10 caracteres')
        return None
    payload = {
        'lawsuit_id': int(lawsuit_id),
        'date': data_mov,
        'description': descricao,
    }
    resultado = _request('POST', '/lawsuits/movement', json_data=payload)
    if resultado and resultado.get('success'):
        print(f'  Movimentação criada no processo {lawsuit_id}')
    return resultado


# ============================================================
# PUBLICACOES (GET)
# ============================================================

def listar_publicacoes(lawsuit_id):
    """
    Lista publicacoes de um processo especifico.

    Processo sem publicacao devolve 404 (nao a lista vazia que a doc mostra) -
    medido em 31 de 129 processos numa varredura real. Por isso o 404 e'
    tratado como "nenhuma publicacao", senao a varredura morre no meio.
    """
    try:
        data = _request('GET', f'/publications/{lawsuit_id}', retries=0)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return []
        raise
    return data.get('data', []) if data else []


# ============================================================
# TAREFAS - LISTAR (GET /posts)
# ============================================================

def listar_tarefas(user_name=None, user_id=None, lawsuit_id=None,
                   task_id=None, date_start=None, date_end=None,
                   deadline_start=None, deadline_end=None,
                   completed_start=None, completed_end=None, limit=100):
    """
    Lista tarefas do escritório com filtros.

    ATENÇÃO: pares de data devem ser completos (start + end).
    Filtrar por user retorna APENAS pendentes daquele usuário.
    """
    params = {'limit': limit, 'offset': 0}
    if user_name:
        params['user_name'] = user_name
    if user_id:
        params['user_id'] = str(user_id)
    if lawsuit_id:
        params['lawsuit_id'] = str(lawsuit_id)
    if task_id:
        params['task_id'] = str(task_id)
    if date_start and date_end:
        params['date_start'] = date_start
        params['date_end'] = date_end
    if deadline_start and deadline_end:
        params['deadline_start'] = deadline_start
        params['deadline_end'] = deadline_end
    if completed_start and completed_end:
        params['completed_start'] = completed_start
        params['completed_end'] = completed_end

    todas = []
    while True:
        # _request devolve None quando a API esgota os retries (429/timeout):
        # sem este guarda a rodada inteira morre com AttributeError e a planilha
        # fica sem os dados do dia (aconteceu na revisao de 24/09/2026).
        data = _request('GET', '/posts', params=params) or {}
        registros = data.get('data') or []
        todas.extend(registros)
        total = data.get('totalCount', 0)
        if len(todas) >= total or not registros:
            break
        params['offset'] += limit
    return todas


# ============================================================
# HISTORICO DE TAREFAS DE PROCESSO
# ============================================================

def listar_historico(lawsuit_id, status=None):
    """
    Lista histórico de tarefas de um processo.

    status: 'pending', 'completed' ou None (todas)
    ATENÇÃO: não suporta paginação — retorna tudo de uma vez.
    """
    params = {}
    if status:
        params['status'] = status
    data = _request('GET', f'/history/{lawsuit_id}', params=params)
    return data.get('data', []) if data else []


# ============================================================
# ANIVERSARIANTES
# ============================================================

def listar_aniversariantes():
    """Lista aniversariantes do mês atual."""
    data = _request('GET', '/customers/birthdays')
    return data.get('data', []) if data else []


# ============================================================
# DOCUMENTOS (doc v1.24.0)
# ============================================================

def listar_documentos(nome=None, cliente_id=None, transacao_id=None,
                      post_id=None, limit=1000):
    """
    Lista arquivos anexados na conta (GET /documents).

    PELO MENOS UM filtro e' obrigatorio - sem filtro a API retorna 422:
        nome          - busca parcial no nome do arquivo (min. 3 caracteres,
                        case-insensitive, inclui a extensao)
        cliente_id    - anexos de um cliente
        transacao_id  - anexos de um lancamento financeiro
        post_id       - anexos de uma tarefa

    Filtros multiplos sao combinados com AND. Um id inexistente devolve
    lista vazia (totalCount 0), nao erro.

    Cada item traz links.download - use-o em url_download_documento().
    """
    params = {}
    if nome:
        if len(nome) < 3:
            print('ERRO: filtro de nome precisa de no minimo 3 caracteres')
            return []
        params['name'] = nome
    if cliente_id:
        params['customer_id'] = int(cliente_id)
    if transacao_id:
        params['transaction_id'] = int(transacao_id)
    if post_id:
        params['post_id'] = int(post_id)

    if not params:
        print('ERRO: informe ao menos um filtro (nome, cliente_id, '
              'transacao_id ou post_id) - a API rejeita busca sem filtro')
        return []

    todos = []
    params['offset'] = 0
    params['limit'] = limit
    while True:
        data = _request('GET', '/documents', params=params)
        registros = data.get('data', [])
        todos.extend(registros)
        total = data.get('totalCount', 0)
        if len(todos) >= total or not registros:
            break
        params['offset'] += limit
    return todos


def url_download_documento(documento):
    """
    Gera a URL temporaria (S3) para baixar um documento.

    documento: o id (int) ou o proprio dict devolvido por listar_documentos()
               - nesse caso usamos links.download, que e' o caminho recomendado
               pela ADVBOX (nao quebra se a rota mudar).

    A URL expira em 300 segundos (5 min) - baixe na hora, nao guarde.
    Retorna None se o documento nao existir: a API responde 500 (nao 404)
    para id inexistente, por isso tratamos o 500 como "nao encontrado".
    """
    if isinstance(documento, dict):
        caminho = (documento.get('links') or {}).get('download')
        # links.download vem como '/api/v1/documents/123/download'; o
        # _request ja concatena a base, entao tiramos o prefixo duplicado.
        if caminho:
            endpoint = caminho.replace('/api/v1', '', 1)
        else:
            endpoint = f'/documents/{documento.get("id")}/download'
    else:
        endpoint = f'/documents/{documento}/download'

    try:
        data = _request('GET', endpoint, retries=0)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (404, 500):
            print(f'  Documento nao encontrado ({endpoint})')
            return None
        raise
    return (data or {}).get('data')


# ============================================================
# TESTE DE CONEXAO
# ============================================================

def testar_conexao():
    """Testa conexao com ADVBOX e mostra dados disponíveis."""
    print('Testando conexao com ADVBOX...')
    try:
        settings = carregar_settings(force=True)
        users = settings.get('users', [])
        origins = settings.get('origins', [])
        categories = settings.get('categories', [])
        banks = settings.get('banks', [])
        cost_centers = settings.get('cost_centers', [])
        stages = settings.get('stages', [])
        types = settings.get('type_lawsuits', [])

        print(f'  Conexao OK!')
        print(f'  Usuarios: {len(users)}')
        for u in users:
            print(f'    - {u["name"]} (ID: {u["id"]})')
        print(f'  Origens: {len(origins)}')
        for o in origins:
            print(f'    - {o["origin"]} (ID: {o["id"]})')
        print(f'  Categorias financeiras: {len(categories)}')
        for c in categories:
            print(f'    - [{c.get("type", "?")}] {c["category"]} (ID: {c["id"]})')
        print(f'  Bancos/Contas: {len(banks)}')
        for b in banks:
            print(f'    - {b["name"]} (ID: {b["id"]})')
        print(f'  Centros de custo: {len(cost_centers)}')
        for cc in cost_centers:
            print(f'    - {cc["cost_center"]} (ID: {cc["id"]})')
        print(f'  Fases (stages): {len(stages)}')
        print(f'  Tipos processo: {len(types)}')
        return True
    except Exception as e:
        print(f'  ERRO: {e}')
        return False


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    testar_conexao()
