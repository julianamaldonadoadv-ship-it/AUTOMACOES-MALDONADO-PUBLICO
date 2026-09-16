"""
Integracao com API do ATENDE DIREITO - Maldonado Advogados
Squad Comercial/Intake: lead qualificado no Atende Direito -> cliente + processo no ADVBOX.

A API do Atende Direito nao tem documentacao publica. Por isso este modulo NAO
hardcoda rotas: base URL, caminhos de endpoint e nomes de campo saem do
config/.env (ver bloco ATENDE_DIREITO_*). Os defaults sao um palpite razoavel -
rode `python OPERACIONAL/main.py intake --inspecionar` para ver o JSON cru que a
conta do escritorio devolve e ajustar o .env conforme o payload real.

Auth: Bearer token (ATENDE_DIREITO_API_TOKEN)
"""
import os
import sys
import time
import json
import unicodedata
import requests


# ============================================================
# CONFIG (tudo vem do .env - nada hardcodado)
# ============================================================

DEFAULT_ENDPOINT_LEADS = '/leads'
DEFAULT_ENDPOINT_LEAD = '/leads/{id}'


def _base_url():
    base = (os.getenv('ATENDE_DIREITO_BASE_URL') or '').rstrip('/')
    if not base:
        print('ERRO: ATENDE_DIREITO_BASE_URL nao encontrado no config/.env')
        sys.exit(1)
    return base


def _get_token():
    token = os.getenv('ATENDE_DIREITO_API_TOKEN')
    if not token:
        print('ERRO: ATENDE_DIREITO_API_TOKEN nao encontrado no config/.env')
        sys.exit(1)
    return token


def _headers():
    return {
        'Authorization': f'Bearer {_get_token()}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Maldonado-Advogados/1.0',
    }


def _endpoint(nome_env, default):
    return os.getenv(nome_env) or default


def _sem_acento(texto):
    """Remove acentos e coloca em maiusculo para comparacoes robustas."""
    nfd = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').upper()


# ============================================================
# HTTP
# ============================================================

def _request(method, endpoint, params=None, json_data=None, retries=2):
    """Request com retry, backoff e tratamento de rate limit (mesmo padrao do ADVBOX)."""
    url = f'{_base_url()}{endpoint}'
    resp = None
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
        except ValueError:
            print(f'  Atende Direito devolveu resposta nao-JSON em {endpoint}:')
            print(f'    {(resp.text or "")[:300]}')
            raise
        except requests.exceptions.HTTPError:
            print(f'  Atende Direito API erro ({resp.status_code}) em {endpoint}: {resp.text[:300]}')
            if resp.status_code == 404:
                print(f'    Endpoint pode estar errado - ajuste no config/.env '
                      f'(ATENDE_DIREITO_ENDPOINT_*) e rode --inspecionar.')
            if tentativa < retries and resp.status_code >= 500:
                time.sleep(3)
                continue
            raise
        except requests.exceptions.RequestException as e:
            print(f'  Atende Direito conexao falhou: {e}')
            if tentativa < retries:
                time.sleep(3)
                continue
            raise
    return None


# ============================================================
# LEITURA TOLERANTE DE PAYLOAD
# ============================================================

_CHAVES_LISTA = ('data', 'items', 'results', 'leads', 'atendimentos', 'records', 'rows')


def _extrair_lista(payload):
    """Acha a lista de registros dentro do envelope, seja qual for o nome da chave."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for chave in _CHAVES_LISTA:
        valor = payload.get(chave)
        if isinstance(valor, list):
            return valor
        # Envelope aninhado: {"data": {"items": [...]}}
        if isinstance(valor, dict):
            interno = _extrair_lista(valor)
            if interno:
                return interno
    return []


def _total_registros(payload, fallback):
    if isinstance(payload, dict):
        for chave in ('totalCount', 'total', 'count', 'total_items'):
            valor = payload.get(chave)
            if isinstance(valor, int):
                return valor
    return fallback


def _achatar(dicionario, prefixo='', destino=None):
    """Achata dicts aninhados: {'contato': {'nome': 'X'}} -> {'contato.nome': 'X', 'nome': 'X'}."""
    if destino is None:
        destino = {}
    if not isinstance(dicionario, dict):
        return destino
    for chave, valor in dicionario.items():
        caminho = f'{prefixo}{chave}'
        if isinstance(valor, dict):
            _achatar(valor, f'{caminho}.', destino)
        else:
            destino[caminho] = valor
            # Alias sem prefixo, se ainda nao houver um valor melhor no topo
            if prefixo and chave not in destino:
                destino[chave] = valor
    return destino


def _primeiro(bruto_achatado, *aliases):
    """Devolve o primeiro alias preenchido, comparando sem acento/caixa."""
    normalizado = {_sem_acento(k).replace('_', '').replace('.', ''): v
                   for k, v in bruto_achatado.items()}
    for alias in aliases:
        chave = _sem_acento(alias).replace('_', '').replace('.', '')
        valor = normalizado.get(chave)
        if valor not in (None, '', [], {}):
            return valor
    return ''


def _so_digitos(valor):
    return ''.join(filter(str.isdigit, str(valor or '')))


# ============================================================
# LEADS / ATENDIMENTOS
# ============================================================

def listar_leads(etapa=None, desde=None, ate=None, limite=100, max_paginas=20, filtros_extra=None):
    """
    Lista leads/atendimentos do Atende Direito.

    etapa: nome da etapa/coluna do pipeline (ex.: 'QUALIFICADO'). Se None, usa
           ATENDE_DIREITO_ETAPA_QUALIFICADO do .env; se tambem vazio, nao filtra.
    desde/ate: 'YYYY-MM-DD'
    Retorna: lista de dicts crus (sem normalizacao).
    """
    endpoint = _endpoint('ATENDE_DIREITO_ENDPOINT_LEADS', DEFAULT_ENDPOINT_LEADS)

    etapa = etapa if etapa is not None else os.getenv('ATENDE_DIREITO_ETAPA_QUALIFICADO', '')
    campo_etapa = os.getenv('ATENDE_DIREITO_PARAM_ETAPA', 'stage')
    campo_desde = os.getenv('ATENDE_DIREITO_PARAM_DATA_INICIO', 'start_date')
    campo_ate = os.getenv('ATENDE_DIREITO_PARAM_DATA_FIM', 'end_date')
    campo_limite = os.getenv('ATENDE_DIREITO_PARAM_LIMITE', 'limit')
    campo_pagina = os.getenv('ATENDE_DIREITO_PARAM_PAGINA', 'page')

    params = dict(filtros_extra or {})
    if etapa:
        params[campo_etapa] = etapa
    if desde:
        params[campo_desde] = desde
    if ate:
        params[campo_ate] = ate
    params[campo_limite] = limite

    todos = []
    pagina = 1
    while pagina <= max_paginas:
        params[campo_pagina] = pagina
        payload = _request('GET', endpoint, params=params)
        registros = _extrair_lista(payload)
        if not registros:
            break
        todos.extend(registros)
        total = _total_registros(payload, len(todos))
        print(f'  Leads Atende Direito: {len(todos)}/{total}')
        if len(todos) >= total or len(registros) < limite:
            break
        pagina += 1
    return todos


def obter_lead(lead_id):
    """Detalhe de um lead pelo ID."""
    endpoint = _endpoint('ATENDE_DIREITO_ENDPOINT_LEAD', DEFAULT_ENDPOINT_LEAD)
    return _request('GET', endpoint.replace('{id}', str(lead_id)))


def marcar_lead_integrado(lead_id, observacao=''):
    """
    Marca no Atende Direito que o lead ja virou cliente no ADVBOX, para nao ser
    reprocessado. So roda se ATENDE_DIREITO_ENDPOINT_MARCAR estiver configurado -
    sem isso, o modulo apenas avisa e segue (nunca inventa rota de escrita).
    """
    endpoint = os.getenv('ATENDE_DIREITO_ENDPOINT_MARCAR')
    if not endpoint:
        print('  (ATENDE_DIREITO_ENDPOINT_MARCAR nao configurado - lead nao foi marcado '
              'como integrado no Atende Direito; controle a duplicidade pelo CPF no ADVBOX.)')
        return None
    campo = os.getenv('ATENDE_DIREITO_CAMPO_MARCAR', 'stage')
    valor = os.getenv('ATENDE_DIREITO_VALOR_MARCAR', 'INTEGRADO ADVBOX')
    metodo = os.getenv('ATENDE_DIREITO_METODO_MARCAR', 'PATCH').upper()
    payload = {campo: valor}
    if observacao:
        payload[os.getenv('ATENDE_DIREITO_CAMPO_OBSERVACAO', 'notes')] = observacao
    return _request(metodo, endpoint.replace('{id}', str(lead_id)), json_data=payload)


# ============================================================
# NORMALIZACAO -> formato aceito por advbox_integration
# ============================================================

def normalizar_lead(bruto):
    """
    Converte o lead cru do Atende Direito no dict que
    advbox_integration.cadastrar_cliente() espera.

    Os aliases cobrem as grafias mais provaveis (pt-BR e en). Se o payload real
    usar outro nome, adicione o mapeamento em ATENDE_DIREITO_MAPA_CAMPOS no .env
    (JSON: {"cpf": "documento_cliente", "nome": "razao_social"}).
    """
    achatado = _achatar(bruto or {})

    mapa_extra = {}
    bruto_mapa = os.getenv('ATENDE_DIREITO_MAPA_CAMPOS', '')
    if bruto_mapa:
        try:
            mapa_extra = json.loads(bruto_mapa)
        except ValueError:
            print('  AVISO: ATENDE_DIREITO_MAPA_CAMPOS nao e um JSON valido - ignorado.')

    def campo(destino, *aliases):
        if destino in mapa_extra:
            aliases = (mapa_extra[destino],) + aliases
        return _primeiro(achatado, *aliases)

    cpf = _so_digitos(campo('cpf', 'cpf', 'documento', 'document', 'identification',
                            'cpf_cnpj', 'cpfCnpj', 'contato.cpf'))
    telefone = _so_digitos(campo('telefone', 'telefone', 'celular', 'phone', 'cellphone',
                                 'whatsapp', 'numero', 'contato.telefone'))

    lead = {
        'lead_id': campo('lead_id', 'id', 'lead_id', 'uuid', 'ticket_id', 'protocolo'),
        'nome': str(campo('nome', 'nome', 'name', 'nome_completo', 'full_name',
                          'cliente', 'contato.nome')).strip(),
        'cpf': cpf,
        'email': campo('email', 'email', 'e_mail', 'mail', 'contato.email'),
        'telefone': telefone,
        'cidade': campo('cidade', 'cidade', 'city', 'municipio'),
        'estado': campo('estado', 'estado', 'state', 'uf'),
        'rua': campo('rua', 'endereco', 'rua', 'street', 'logradouro', 'address'),
        'bairro': campo('bairro', 'bairro', 'region', 'neighborhood'),
        'cep': campo('cep', 'cep', 'postalcode', 'postal_code', 'zip'),
        'data_nascimento': campo('data_nascimento', 'data_nascimento', 'nascimento',
                                 'birthdate', 'birth_date'),
        'profissao': campo('profissao', 'profissao', 'occupation'),
        'etapa': campo('etapa', 'etapa', 'stage', 'status', 'pipeline_stage', 'coluna'),
        'origem': campo('origem', 'origem', 'origin', 'source', 'canal', 'channel'),
        'resumo': campo('resumo', 'resumo', 'summary', 'descricao', 'description',
                        'observacao', 'notes', 'ultima_mensagem'),
        'criado_em': campo('criado_em', 'created_at', 'criado_em', 'data_criacao', 'date'),
        'responsavel': campo('responsavel', 'responsavel', 'owner', 'atendente', 'agent'),
        '_bruto': bruto,
    }
    return lead


def validar_lead(lead):
    """
    Devolve lista de pendencias que impedem o cadastro automatico.
    Vazio = pronto para cadastrar (ainda assim com confirmacao humana).
    """
    pendencias = []
    if not lead.get('nome'):
        pendencias.append('sem nome')
    if not lead.get('cpf'):
        pendencias.append('sem CPF (obrigatorio para dedup no ADVBOX)')
    elif len(lead['cpf']) not in (11, 14):
        pendencias.append(f"CPF/CNPJ com {len(lead['cpf'])} digitos")
    if not lead.get('telefone') and not lead.get('email'):
        pendencias.append('sem telefone e sem e-mail')
    return pendencias


# ============================================================
# DIAGNOSTICO
# ============================================================

def inspecionar(quantidade=1):
    """
    Imprime o JSON cru dos primeiros leads, para calibrar o mapa de campos.
    Use quando o normalizar_lead() vier com campos vazios.
    """
    print(f'  GET {_base_url()}{_endpoint("ATENDE_DIREITO_ENDPOINT_LEADS", DEFAULT_ENDPOINT_LEADS)}')
    brutos = listar_leads(limite=max(quantidade, 1), max_paginas=1)
    if not brutos:
        print('  Nenhum lead retornado. Confira o endpoint e a etapa filtrada no .env.')
        return []
    for i, bruto in enumerate(brutos[:quantidade], 1):
        print(f'\n  ----- LEAD CRU #{i} -----')
        print(json.dumps(bruto, indent=2, ensure_ascii=False)[:4000])
        print(f'\n  ----- NORMALIZADO #{i} -----')
        normalizado = {k: v for k, v in normalizar_lead(bruto).items() if k != '_bruto'}
        print(json.dumps(normalizado, indent=2, ensure_ascii=False))
    return brutos


def testar_conexao():
    """Testa credencial e endpoint de leads do Atende Direito."""
    print('Testando conexao com Atende Direito...')
    try:
        brutos = listar_leads(limite=5, max_paginas=1)
        print(f'  Conexao OK! {len(brutos)} lead(s) na primeira pagina.')
        for bruto in brutos[:5]:
            lead = normalizar_lead(bruto)
            print(f"    - [{lead['etapa'] or 's/etapa'}] {lead['nome'] or '(sem nome)'} "
                  f"| CPF {lead['cpf'] or '-'} | {lead['telefone'] or '-'}")
        return True
    except Exception as e:
        print(f'  ERRO: {e}')
        return False


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    testar_conexao()
