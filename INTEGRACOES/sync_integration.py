# -*- coding: utf-8 -*-
"""
Integracao com o SYNC (Atende Direito) - Maldonado Advogados
============================================================
O Sync e a plataforma de MONITORAMENTO PROCESSUAL do Atende Direito. Nao
confundir com `atende_direito_integration.py`, que e o CRM/intake (lead
qualificado -> cliente no ADVBOX). Sao dois produtos da mesma casa, com
credenciais e base URL diferentes:

    atende_direito_integration.py  -> CRM  (lead, pipeline comercial)
    sync_integration.py (este)     -> autos, intimacoes, prazos, jurimetria

O que o Sync cobre e que hoje sai do `comunica_djen.py`:
  - captura de intimacoes na fonte oficial (PDPJ/jus.br + DJEN), ja
    deduplicada por ATO (o DJEN publica uma copia por advogado destinatario;
    o Sync funde as copias numa obrigacao so);
  - prazo calculado (data fatal) com estado `aberta|ciente|vencida|decorrida`;
  - autos digitais completos, com teor dos documentos em markdown (OCR);
  - webhook assinado (HMAC-SHA256) em vez de polling.

Doc oficial (Swagger publico, sem login):
    https://api.sync.atendedireito.app/openapi.json
    https://sync.atendedireito.app/  (painel / aba API para gerar a chave)

Auth: uma chave so, em toda requisicao -> `Authorization: Bearer sk_live_...`
Gerar/rotacionar em POST /v1/conta/chaves (ou na aba API do painel).
Validar com GET /v1/conta.

--------------------------------------------------------------------------
GUARD-RAILS DO ESCRITORIO (nao desfazer)
--------------------------------------------------------------------------
1. SOMENTE LEITURA por padrao. Toda rota de escrita (dar ciencia em prazo,
   marcar intimacao como tratada, registrar webhook) exige `confirmado=True`
   E a trava `SYNC_PERMITIR_ESCRITA=1` no .env. Vale a regra de ouro do
   repositorio: a IA nunca protocola e nunca marca nada sem confirmacao.

2. O PRAZO DO SYNC NAO DECIDE O RECURSO. O Sync calcula a data fatal pelo
   CPC, mas o POP-CJ-003-A (regra da Dra. Juliana, 08/09/2026) exige cotejo
   INICIAL x DECISAO para saber se cabe ED (5 dias uteis) antes do agravo /
   apelacao (15 dias uteis). Quem fecha o recurso continua sendo
   `triagem_divida_rural.avaliar_recurso_cabivel()`, com as DUAS datas. O
   `data_fatal` do Sync entra como insumo e como conferencia, nunca como
   conclusao - anotar prazo de agravo sem checar o ED perde o ED em silencio.

3. O POLO NAO SE ADIVINHA. A apuracao de KPI depende de saber de que lado o
   escritorio esta: "recurso nao provido" e inexito se o recurso e nosso e
   exito se e do banco. No DJEN isso vem estruturado em
   `destinatarios[].polo` ("A"/"P"). Se o Sync nao devolver o polo, o
   adaptador deixa `partes_polo` VAZIO e marca `polo_indisponivel=True` -
   nunca chuta. Polo errado inverte o exito do mes inteiro.

4. Os schemas de RESPOSTA nao estao tipados no Swagger (a API publica os
   parametros, mas devolve `{}` como schema de retorno). Por isso a leitura
   do payload aqui e TOLERANTE a aliases, no mesmo padrao do modulo do
   Atende Direito, e existe `inspecionar()` para calibrar contra o JSON real
   assim que a chave do escritorio estiver ativa.
"""
import hashlib
import hmac
import json
import os
import sys
import time
import unicodedata

import requests


# ============================================================
# CONFIG
# ============================================================

BASE_URL_PADRAO = 'https://api.sync.atendedireito.app'
TIMEOUT_PADRAO = 60

# Endpoints (a API do Sync e versionada e documentada; ao contrario do CRM,
# aqui as rotas sao estaveis e podem ficar no codigo).
EP_CONTA = '/v1/conta'
EP_DASHBOARD = '/v1/dashboard'
EP_INTIMACOES = '/v1/intimacoes'
EP_INTIMACAO = '/v1/intimacoes/{id}'
EP_INTIMACAO_TRATAR = '/v1/intimacoes/{id}/tratar'
EP_PRAZOS = '/v1/prazos'
EP_PRAZOS_CIENCIA = '/v1/prazos/ciencia'
EP_PROCESSOS = '/v1/processos'
EP_PROCESSO = '/v1/processos/{numero}'
EP_PROCESSO_AUTOS = '/v1/processos/{numero}/autos'
EP_PROCESSO_AUTOS_MD = '/v1/processos/{numero}/autos.md'
EP_DOCUMENTO_MD = '/v1/documentos/{id}/markdown'
EP_MONITORES = '/v1/monitores'
EP_WEBHOOKS = '/v1/webhooks'
EP_BUSCA = '/v1/busca'
EP_JURIMETRIA = '/v1/jurimetria'


def _base_url():
    return (os.getenv('SYNC_BASE_URL') or BASE_URL_PADRAO).rstrip('/')


def _token(obrigatorio=True):
    token = os.getenv('SYNC_API_TOKEN') or ''
    if not token and obrigatorio:
        print('ERRO: SYNC_API_TOKEN nao encontrado em config/.env')
        print('      Gere a chave no painel (https://sync.atendedireito.app -> aba API)')
        print('      ou em POST /v1/conta/chaves. O formato e sk_live_...')
        sys.exit(1)
    return token


def _headers():
    return {
        'Authorization': f'Bearer {_token()}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Maldonado-Advogados/1.0',
    }


def escrita_liberada():
    """Trava dupla de escrita: so grava no Sync com SYNC_PERMITIR_ESCRITA=1."""
    return (os.getenv('SYNC_PERMITIR_ESCRITA') or '').strip() in ('1', 'true', 'True', 'sim')


def _sem_acento(texto):
    nfd = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').upper()


def _so_digitos(valor):
    return ''.join(filter(str.isdigit, str(valor or '')))


# ============================================================
# HTTP
# ============================================================

class SyncError(RuntimeError):
    """Falha de comunicacao ou de credencial no Sync."""


def _request(method, endpoint, params=None, json_data=None, retries=2, aceita_texto=False):
    """
    Request com retry/backoff e leitura dos erros que a API do Sync usa.

    Diferencas para o DJEN: o Sync e uma API de verdade (nao tem o falso-vazio
    do Comunica), entao vazio aqui significa vazio mesmo - nao ha retry cego.
    Os codigos que importam:
      401 - chave invalida/revogada
      402 - conta suspensa por cobranca (a API cobra na porta, fora de /v1/conta)
      404 - id inexistente OU documento sem versao markdown
      429 - rate limit, respeita Retry-After
    """
    url = f'{_base_url()}{endpoint}'
    resp = None
    for tentativa in range(retries + 1):
        try:
            resp = requests.request(
                method, url, headers=_headers(),
                params=params, json=json_data, timeout=_timeout(),
            )
            if resp.status_code == 429:
                espera = int(resp.headers.get('Retry-After', 10))
                print(f'  Sync: rate limit atingido, aguardando {espera}s...')
                time.sleep(espera)
                continue
            if resp.status_code == 401:
                raise SyncError(
                    'Sync recusou a chave (401). Confira SYNC_API_TOKEN no config/.env '
                    'ou gere outra no painel (aba API).'
                )
            if resp.status_code == 402:
                raise SyncError(
                    'Sync respondeu 402: a conta do escritorio esta suspensa por cobranca. '
                    'Regularize no painel - a API fica bloqueada ate la.'
                )
            resp.raise_for_status()
            if aceita_texto:
                return resp.text
            return resp.json() if resp.text else {}
        except SyncError:
            raise
        except ValueError:
            trecho = (resp.text or '')[:300] if resp is not None else ''
            raise SyncError(f'Sync devolveu resposta nao-JSON em {endpoint}: {trecho}')
        except requests.exceptions.HTTPError:
            codigo = resp.status_code if resp is not None else '?'
            corpo = (resp.text or '')[:300] if resp is not None else ''
            rid = resp.headers.get('X-Request-Id', '-') if resp is not None else '-'
            if codigo == 404:
                raise SyncError(f'Sync 404 em {endpoint} (X-Request-Id {rid}): {corpo}')
            if tentativa < retries and isinstance(codigo, int) and codigo >= 500:
                time.sleep(3)
                continue
            raise SyncError(f'Sync erro {codigo} em {endpoint} (X-Request-Id {rid}): {corpo}')
        except requests.exceptions.RequestException as e:
            if tentativa < retries:
                time.sleep(3)
                continue
            raise SyncError(f'Sync: falha de conexao em {endpoint}: {e}')
    raise SyncError(f'Sync: esgotou as tentativas em {endpoint}')


def _timeout():
    try:
        return int(os.getenv('SYNC_TIMEOUT') or TIMEOUT_PADRAO)
    except ValueError:
        return TIMEOUT_PADRAO


# ============================================================
# LEITURA TOLERANTE DE PAYLOAD
# ============================================================

_CHAVES_LISTA = ('itens', 'items', 'data', 'resultados', 'results',
                 'intimacoes', 'prazos', 'processos', 'registros', 'rows',
                 # envelopes reais conferidos em 21/09/2026 (GET /v1/monitores
                 # devolve {"monitores": [...]}; sem isto o diagnostico dizia
                 # "0 monitores" com a OAB RO5769 ativa):
                 'monitores', 'credenciais', 'webhooks', 'entregas', 'publicacoes')


def _extrair_lista(payload):
    """Acha a lista de registros dentro do envelope, seja qual for a chave."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for chave in _CHAVES_LISTA:
        valor = payload.get(chave)
        if isinstance(valor, list):
            return valor
        if isinstance(valor, dict):
            interno = _extrair_lista(valor)
            if interno:
                return interno
    return []


def _total(payload, fallback):
    if isinstance(payload, dict):
        for chave in ('total', 'total_itens', 'totalCount', 'count'):
            valor = payload.get(chave)
            if isinstance(valor, int):
                return valor
    return fallback


def _achatar(dicionario, prefixo='', destino=None):
    """Achata dicts aninhados mantendo tambem o alias sem prefixo."""
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
            if prefixo and chave not in destino:
                destino[chave] = valor
    return destino


# Quando o campo vem como OBJETO aninhado (`orgao: {nome: "1a Vara"}`), o valor
# util esta num destes subcampos. Sem isso o alias "orgao" nao acha nada, porque
# o achatamento guardou a chave como "orgao.nome".
_SUBCAMPOS = ('', 'nome', 'sigla', 'descricao', 'titulo', 'valor', 'numero', 'label')


def _primeiro(achatado, *aliases):
    """Devolve o primeiro alias preenchido, comparando sem acento/caixa/_/.

    Para cada alias tenta tambem o subcampo obvio do objeto aninhado, na ordem
    de `_SUBCAMPOS` - o Swagger do Sync nao tipa as respostas, entao o mesmo
    dado pode chegar como string ou como objeto.
    """
    normalizado = {_sem_acento(k).replace('_', '').replace('.', ''): v
                   for k, v in achatado.items()}
    for alias in aliases:
        base = _sem_acento(alias).replace('_', '').replace('.', '')
        for sub in _SUBCAMPOS:
            chave = base + _sem_acento(sub)
            valor = normalizado.get(chave)
            if valor not in (None, '', [], {}):
                return valor
    return ''


def _paginar(endpoint, params=None, itens_por_pagina=100, max_paginas=50, rotulo='registros'):
    """Paginacao padrao do Sync: `pagina` (a partir de 1) + `itens`."""
    params = dict(params or {})
    params['itens'] = itens_por_pagina
    coletados = []
    pagina = 1
    while pagina <= max_paginas:
        params['pagina'] = pagina
        payload = _request('GET', endpoint, params=params)
        lote = _extrair_lista(payload)
        if not lote:
            break
        coletados.extend(lote)
        total = _total(payload, len(coletados))
        print(f'  Sync: {len(coletados)}/{total} {rotulo}')
        if len(coletados) >= total or len(lote) < itens_por_pagina:
            break
        pagina += 1
    return coletados


# ============================================================
# CONTA / DIAGNOSTICO
# ============================================================

def conta():
    """Whoami: valida a chave e devolve os dados da conta e o nivel de acesso."""
    return _request('GET', EP_CONTA)


def dashboard():
    """Painel do dia em uma chamada (prazos abertos, intimacoes pendentes,
    audiencias proximas, saude do monitoramento)."""
    return _request('GET', EP_DASHBOARD)


# ============================================================
# INTIMACOES
# ============================================================

def listar_intimacoes(status='pendentes', dias=30, com_prazo=False, sem_prazo=False,
                      tribunal=None, processo=None, acionaveis=False,
                      itens_por_pagina=100, max_paginas=50):
    """
    Inbox de intimacoes dos processos da carteira (mais recente primeiro).

    status:     pendentes | tratadas | todas
    dias:       janela; 0 = sem limite
    acionaveis: True esconde o que ja teve ciencia (inclusive por copia irma
                do DJEN) ou ja decorreu - e' o que a Controladoria quer ver.

    ATENCAO: o campo `texto` vem CORTADO em 600 caracteres nesta rota. Para
    triagem e KPI, que leem o dispositivo, use `obter_intimacao(id)` (teor
    integral) - ler dispositivo em texto truncado da conclusao errada.
    """
    if com_prazo and sem_prazo:
        raise ValueError('com_prazo e sem_prazo nao se combinam.')
    params = {'status': status, 'dias': dias}
    if com_prazo:
        params['com_prazo'] = 'true'
    if sem_prazo:
        params['sem_prazo'] = 'true'
    if acionaveis:
        params['acionaveis'] = 'true'
    if tribunal:
        params['tribunal'] = tribunal
    if processo:
        params['processo'] = processo
    return _paginar(EP_INTIMACOES, params, itens_por_pagina, max_paginas, 'intimacao(oes)')


def obter_intimacao(intimacao_id):
    """Detalhe da intimacao com o teor INTEGRAL, sem corte."""
    return _request('GET', EP_INTIMACAO.replace('{id}', str(intimacao_id)))


def tratar_intimacao(intimacao_id, confirmado=False):
    """
    ESCRITA. Marca a intimacao como tratada no Sync (sai da lista de pendentes).

    Exige `confirmado=True` e SYNC_PERMITIR_ESCRITA=1. Quem da ciencia e a
    controller, depois de lancar a tarefa no ADVBOX - nunca a automacao por
    conta propria: ciencia carimbada sem tratamento esconde a pendencia.
    """
    _exigir_escrita(confirmado, f'marcar a intimacao {intimacao_id} como tratada')
    return _request('POST', EP_INTIMACAO_TRATAR.replace('{id}', str(intimacao_id)))


# ============================================================
# PRAZOS
# ============================================================

def listar_prazos(estado='acionaveis', de=None, ate=None, leitura=False, dias=0,
                  itens_por_pagina=100, max_paginas=50):
    """
    Prazos como OBRIGACAO, ja deduplicados por ato (as N copias que o DJEN
    publica por advogado viram uma linha so, com todos os `intimacao_ids`).

    estado: acionaveis (padrao) | abertas | vencidas | leitura
    de/ate: janela sobre a DATA FATAL (AAAA-MM-DD). Sem os dois nao ha janela
            padrao - a API devolve a lista inteira de proposito.

    LEMBRETE (POP-CJ-003-A): a data fatal que o Sync calcula e o prazo do
    recurso principal. Ela NAO substitui o cotejo INICIAL x DECISAO que define
    se cabe ED antes - quem fecha isso e' a triagem, com as duas datas.
    """
    params = {'estado': estado}
    if leitura:
        params['leitura'] = 'true'
        if dias:
            params['dias'] = dias
    if de:
        params['de'] = de
    if ate:
        params['ate'] = ate
    return _paginar(EP_PRAZOS, params, itens_por_pagina, max_paginas, 'prazo(s)')


def dar_ciencia_prazos(prazo_ids=None, vencidos=False, confirmado=False):
    """
    ESCRITA. Registra ciencia do ATO - fecha a obrigacao inteira de uma vez
    (todas as copias do DJEN e o prazo gemeo detectado nos autos).

    Exige `confirmado=True` e SYNC_PERMITIR_ESCRITA=1.
    """
    alvo = 'os prazos vencidos (faxina)' if vencidos else f'os prazos {prazo_ids}'
    _exigir_escrita(confirmado, f'registrar ciencia em {alvo}')
    corpo = {}
    if prazo_ids:
        corpo['ids'] = list(prazo_ids)
    if vencidos:
        corpo['vencidos'] = True
    return _request('POST', EP_PRAZOS_CIENCIA, json_data=corpo)


# ============================================================
# PROCESSOS E AUTOS
# ============================================================

def listar_processos(busca=None, tribunal=None, parado_min=None, pasta=None,
                     ordenar='atualizacao', ordem='desc',
                     itens_por_pagina=100, max_paginas=50):
    """Lista paginada dos processos da carteira no Sync.

    parado_min: so processos parados ha N dias ou mais (alerta de processo
    parado - insumo do POP de processo sem movimentacao)."""
    params = {'ordenar': ordenar, 'ordem': ordem}
    if busca:
        params['busca'] = busca
    if tribunal:
        params['tribunal'] = tribunal
    if parado_min:
        params['parado_min'] = parado_min
    if pasta:
        params['pasta'] = pasta
    return _paginar(EP_PROCESSOS, params, itens_por_pagina, max_paginas, 'processo(s)')


def obter_processo(numero):
    """Ficha do processo sincronizado: partes, movimentos, audiencias,
    intimacoes e documentos."""
    return _request('GET', EP_PROCESSO.replace('{numero}', str(numero)))


def sincronizar_processo(numero, confirmado=False):
    """POST /v1/processos/{n}/sincronizar: enfileira a importacao do processo a
    partir do PDPJ e o vincula a conta. Escrita travada (SYNC_PERMITIR_ESCRITA +
    confirmado): processo fora da conta consome vaga do plano."""
    _exigir_escrita(confirmado, f'sincronizar {numero}')
    return _request('POST', f'/v1/processos/{numero}/sincronizar')


def ressincronizar_processo(numero, confirmado=False):
    """POST /v1/processos/{n}/ressincronizar: releitura completa na fonte (re-lista
    os documentos, re-tenta downloads que falharam). Escrita travada."""
    _exigir_escrita(confirmado, f'ressincronizar {numero}')
    return _request('POST', f'/v1/processos/{numero}/ressincronizar')


def autos(numero, pagina=1, itens=100, ordem='desc'):
    """
    Autos digitais: movimentos, documentos, intimacoes e audiencias fundidos
    numa cronologia so. Cada item traz `tipo`, `data` e os campos da fonte.
    A resposta inclui o bloco `capa` (classe, assunto, partes, valor da causa).
    """
    return _request('GET', EP_PROCESSO_AUTOS.replace('{numero}', str(numero)),
                    params={'pagina': pagina, 'itens': itens, 'ordem': ordem})


def autos_markdown(numero):
    """
    Os autos inteiros num unico .md - capa, partes, sumario de completude e a
    linha do tempo com o teor integral dos documentos.

    E' o insumo natural do Squad Jurimetria e da leitura de decisao. O proprio
    Sync avisa: o arquivo retrata o espelho DELE no momento da geracao, nao e
    certidao dos autos oficiais. Vale o mesmo guard-rail do OCR do
    BASE_CONHECIMENTO - serve para localizar a passagem; citacao em peca se
    confere contra os autos.
    """
    return _request('GET', EP_PROCESSO_AUTOS_MD.replace('{numero}', str(numero)),
                    aceita_texto=True)


def documento_markdown(documento_id):
    """Texto extraido do documento (OCR) em markdown puro. 404 = sem versao markdown."""
    return _request('GET', EP_DOCUMENTO_MD.replace('{id}', str(documento_id)),
                    aceita_texto=True)


def documento_arquivo(documento_id):
    """URL ASSINADA do arquivo ORIGINAL do documento (o PDF que esta nos autos), valida por 1 hora.

    Serve para o que o markdown nao resolve: entregar ao perito ou ao juizo a cedula e o
    demonstrativo como o banco os juntou, e nao a transcricao de OCR. Por isso o arquivo tem de ser
    baixado na hora e guardado no Drive, onde o link e' permanente.

    404 aqui NAO significa que o documento nao existe: significa que o Sync tem o texto mas nao
    guardou o binario (acontece em tribunal que serve o PDF so com a credencial do advogado, e foi
    o que ocorreu no TRF5 e no TJSC em 24/09/2026). Nesse caso o arquivo vem do PJe, a mao.
    """
    return _request('GET', '/v1/documentos/%s/arquivo' % documento_id)


def buscar(tipo, valor):
    """
    Busca processual em tempo real no PDPJ/DJEN. NAO persiste nada.
    tipo: oab | cpf | cnpj | nome | numero (conforme a API)
    """
    return _request('POST', EP_BUSCA, json_data={'tipo': tipo, 'valor': valor})


def jurimetria(**filtros):
    """Panorama jurimetrico da carteira (insumo do Squad Jurimetria)."""
    return _request('GET', EP_JURIMETRIA, params=filtros or None)


# ============================================================
# MONITORES E WEBHOOKS
# ============================================================

def listar_monitores():
    """Alvos que o Sync acompanha sozinho (OAB, CPF, CNPJ, nome, processo)."""
    return _extrair_lista(_request('GET', EP_MONITORES))


def criar_monitor(tipo, valor, confirmado=False):
    """
    ESCRITA. Liga o acompanhamento continuo de um alvo (e dispara na hora a
    descoberta dos processos existentes).

    ATENCAO: criar monitor de OAB traz a carteira inteira daquele advogado e
    costuma ter efeito no PLANO CONTRATADO (cota de processos monitorados).
    Por isso exige confirmacao explicita - nao e' decisao da automacao.
    """
    _exigir_escrita(confirmado, f'criar monitor {tipo}={valor} (afeta a cota do plano)')
    return _request('POST', EP_MONITORES, json_data={'tipo': tipo, 'valor': valor})


def descobertos(monitor_id):
    """Processos que o monitor achou mas NAO estao ativados (sem coleta, sem
    intimacao). Traz tambem o bloco `cobranca` (vagas no plano, preco do excedente)."""
    return _request('GET', f'{EP_MONITORES}/{monitor_id}/descobertos')


def confirmar_selecao(monitor_id, numeros=None, todos=False, confirmado=False):
    """
    ESCRITA. Ativa o monitoramento dos processos descobertos.

    ATENCAO - CUSTO: o que couber nas vagas do plano ativa na hora; o que passar
    do teto NAO ativa e vira fatura avulsa PRE-PAGA (a resposta traz o link), e
    a coleta desses so comeca na baixa. Processo ativado conta no plano da
    competencia: desligar no mesmo mes nao estorna.
    """
    if not todos and not numeros:
        raise ValueError('informe numeros ou todos=True')
    _exigir_escrita(confirmado, 'ativar processos descobertos (afeta o plano/fatura)')
    corpo = {'todos': True} if todos else {'numeros': list(numeros)}
    return _request('POST', f'{EP_MONITORES}/{monitor_id}/confirmar', json_data=corpo)


def importar_processos(numeros, lote_id=None, confirmado=False):
    """
    ESCRITA. Importa processos por numero CNJ (ate 5.000 por lote) e poe em
    monitoramento continuo. Acima do teto do plano o lote entra como
    "aguardando selecao" num monitor tipo `importacao`: ativar com
    `confirmar_selecao()` nesse monitor (gera fatura avulsa pre-paga).
    `lote_id` torna o envio idempotente (reenviar nao enfileira de novo).
    """
    _exigir_escrita(confirmado, f'importar {len(numeros)} processo(s) (afeta o plano/fatura)')
    corpo = {'numeros': list(numeros), 'monitorar': True}
    if lote_id:
        corpo['lote_id'] = lote_id
    return _request('POST', '/v1/processos/importar', json_data=corpo)


def desligar_monitoramento(numero, confirmado=False):
    """ESCRITA. Para de acompanhar o processo (os dados ja lidos continuam
    acessiveis; sincronizar o numero de novo religa). Nao e' o DELETE do
    processo, que esconde da carteira e bloqueia o discovery."""
    _exigir_escrita(confirmado, f'desligar monitoramento de {numero}')
    return _request('DELETE', f'/v1/processos/{numero}/monitoramento')


def bloquear_processo(numero, confirmado=False):
    """ESCRITA. Bloqueia o processo: ele sai do monitoramento e a API passa a
    recusar leitura dele (403 "Processo bloqueado"). Libera a vaga do plano."""
    _exigir_escrita(confirmado, f'bloquear o processo {numero}')
    return _request('POST', f'/v1/processos/{numero}/bloquear')


def desbloquear_processo(numero, confirmado=False):
    """
    ESCRITA. Tira o processo do bloqueio e o devolve ao monitoramento.

    ATENCAO - CUSTO: desbloquear OCUPA UMA VAGA do plano. Dentro do teto nao
    gera cobranca; acima dele o Sync cobra por processo excedente. Conferir o
    total monitorado (`GET /v1/processos` -> `total`) contra o limite do plano
    (`GET /v1/conta/planos`) ANTES de desbloquear em lote.

    Processo bloqueado recusa `sincronizar_processo()` com 409: desbloquear
    vem primeiro, e so depois a sincronizacao traz os autos.
    """
    _exigir_escrita(confirmado, f'desbloquear o processo {numero} (ocupa vaga do plano)')
    return _request('DELETE', f'/v1/processos/{numero}/bloquear')


def listar_webhooks():
    return _extrair_lista(_request('GET', EP_WEBHOOKS))


def registrar_webhook(nome, url, eventos=None, secret='', confirmado=False):
    """
    ESCRITA. Inscreve uma URL publica HTTPS para receber os eventos do Sync.

    eventos: lista de nomes (ex.: 'intimacao.criada', 'prazo.vencendo').
             Vazio = todos. O Swagger cita esses dois como exemplo e nao
             publica o enum completo - confira a lista real na aba API do
             painel antes de filtrar, porque evento nao assinado nao chega.
    secret:  segredo do HMAC-SHA256 (header X-Webhook-Signature). Sempre use.

    IPs internos/privados sao recusados pela API: o receptor precisa estar
    publicamente acessivel por HTTPS.
    """
    _exigir_escrita(confirmado, f'registrar o webhook "{nome}" apontando para {url}')
    if not secret:
        print('  AVISO: registrando webhook SEM secret - qualquer um que descobrir a '
              'URL consegue injetar intimacao falsa na Controladoria. Use um segredo.')
    corpo = {'nome': nome, 'url': url, 'eventos': list(eventos or []), 'secret': secret}
    return _request('POST', EP_WEBHOOKS, json_data=corpo)


def verificar_assinatura_webhook(corpo_bruto, assinatura_recebida, segredo=None):
    """
    Confere o header X-Webhook-Signature de um POST recebido do Sync.

    corpo_bruto: bytes do corpo EXATAMENTE como chegou (nao re-serializar o
                 JSON: qualquer diferenca de espaco ou ordem quebra o HMAC).
    Devolve True/False. Comparacao em tempo constante.

    Sem isso, o receptor aceita qualquer POST forjado - e uma intimacao falsa
    entra na fila da controller como se fosse do tribunal.
    """
    segredo = segredo if segredo is not None else (os.getenv('SYNC_WEBHOOK_SECRET') or '')
    if not segredo or not assinatura_recebida:
        return False
    if isinstance(corpo_bruto, str):
        corpo_bruto = corpo_bruto.encode('utf-8')
    esperado = hmac.new(segredo.encode('utf-8'), corpo_bruto, hashlib.sha256).hexdigest()
    recebida = str(assinatura_recebida).strip()
    # Alguns emissores prefixam o algoritmo ("sha256=..."); aceita as duas formas.
    if '=' in recebida and recebida.lower().startswith('sha256='):
        recebida = recebida.split('=', 1)[1]
    return hmac.compare_digest(esperado, recebida)


def _exigir_escrita(confirmado, acao):
    if not escrita_liberada():
        raise SyncError(
            f'Escrita bloqueada: tentativa de {acao}. O modulo do Sync e somente '
            'leitura ate que SYNC_PERMITIR_ESCRITA=1 esteja no config/.env.'
        )
    if not confirmado:
        raise SyncError(
            f'Escrita bloqueada: {acao} exige confirmado=True. '
            '(Regra de ouro: nada e gravado sem confirmacao explicita.)'
        )


# ============================================================
# ADAPTADOR -> formato do comunica_djen.resumir()
# ============================================================

# Tipos de ato que o Sync pode nomear de formas diferentes; a triagem le o
# campo `tipo`, entao o adaptador entrega o rotulo mais informativo que achar.
def resumir_intimacao(item, teor_integral=None):
    """
    Converte uma intimacao do Sync no MESMO dict que `comunica_djen.resumir()`
    devolve, para que `triagem_lote()` e o KPI consumam sem alteracao.

    teor_integral: texto completo (de `obter_intimacao`), quando ja carregado.
                   Sem ele, o texto vem cortado em 600 caracteres pela rota de
                   listagem - suficiente para triar o TIPO do ato, insuficiente
                   para ler DISPOSITIVO (KPI).

    Campos extras, so do Sync, prefixados para nao colidir com os do DJEN:
      sync_id, sync_obrigacao_estado, sync_data_fatal, sync_prazo_dias,
      sync_tratada, polo_indisponivel
    """
    achatado = _achatar(item or {})

    processo = _primeiro(achatado, 'processo', 'numero_processo', 'numeroProcesso',
                         'processo.numero', 'numero')
    texto = teor_integral if teor_integral else _primeiro(
        achatado, 'texto', 'teor', 'texto_previa', 'conteudo', 'resumo')

    # --- Polo: nunca chutar (ver guard-rail 3 no topo do modulo) -------------
    partes_polo = []
    partes = []
    for bloco in (item.get('destinatarios') or item.get('partes') or []):
        if not isinstance(bloco, dict):
            if bloco:
                partes.append(str(bloco))
            continue
        nome = bloco.get('nome') or bloco.get('name') or ''
        polo = bloco.get('polo') or bloco.get('polo_sigla') or bloco.get('tipo_polo')
        partes.append(nome)
        if polo:
            partes_polo.append({'nome': nome, 'polo': _normalizar_polo(polo)})
    # A intimacao do Sync (lista E detalhe, conferido em 21/09/2026) nao traz
    # parte nem polo: isso so existe no cadastro do processo. Sem polo lido,
    # a marca sobe sempre - inclusive quando nao veio parte nenhuma.
    polo_indisponivel = not partes_polo

    advogados = []
    for a in (item.get('advogados') or item.get('destinatarioadvogados') or []):
        if isinstance(a, dict):
            adv = a.get('advogado') if isinstance(a.get('advogado'), dict) else a
            nome = adv.get('nome') or adv.get('name') or ''
            oab = f"{adv.get('numero_oab') or adv.get('oab') or ''}/" \
                  f"{adv.get('uf_oab') or adv.get('uf') or ''}".strip('/')
            advogados.append(f'{nome} (OAB {oab})'.strip())
        elif a:
            advogados.append(str(a))

    return {
        # --- contrato do comunica_djen.resumir() ---
        'id': _primeiro(achatado, 'id', 'intimacao_id', 'uuid'),
        'data': _primeiro(achatado, 'data_disponibilizacao', 'data_publicacao',
                          'data', 'publicado_em', 'criado_em'),
        'tribunal': _primeiro(achatado, 'tribunal', 'siglaTribunal', 'sigla_tribunal'),
        'orgao': _primeiro(achatado, 'orgao', 'nomeOrgao', 'orgao_julgador', 'vara'),
        'tipo': _primeiro(achatado, 'tipo_ato', 'tipoComunicacao', 'tipo', 'especie'),
        'classe': _primeiro(achatado, 'classe', 'nomeClasse', 'classe_processual'),
        'processo': processo,
        'partes': [p for p in partes if p],
        'partes_polo': partes_polo,
        'advogados': advogados,
        'link': _primeiro(achatado, 'link', 'url', 'link_publicacao'),
        'texto': (texto or '').strip(),
        # --- extras do Sync ---
        '_fonte': 'sync',
        'sync_id': _primeiro(achatado, 'id', 'intimacao_id'),
        'sync_obrigacao_estado': _primeiro(achatado, 'obrigacao_estado', 'estado'),
        'sync_data_fatal': _primeiro(achatado, 'data_fatal', 'prazo_data_fatal', 'vencimento'),
        'sync_prazo_dias': _primeiro(achatado, 'prazo_dias', 'dias_prazo'),
        'sync_resumo_ia': _primeiro(achatado, 'resumo', 'resumo_ia'),
        'sync_tratada': bool(_primeiro(achatado, 'tratada', 'tratado')),
        'texto_truncado': teor_integral is None,
        'polo_indisponivel': polo_indisponivel,
        '_bruto': item,
    }


def _normalizar_polo(valor):
    """Converte o polo do Sync para a convencao do DJEN ("A" ativo / "P" passivo)."""
    bruto = _sem_acento(valor).strip()
    if bruto.startswith('A'):   # A, ATIVO, AUTOR
        return 'A'
    if bruto.startswith('P'):   # P, PASSIVO
        return 'P'
    if bruto.startswith('R'):   # REU / REQUERIDO
        return 'P'
    return None


def intimacoes_para_triagem(dias=1, acionaveis=True, teor_integral=True,
                            max_teor_integral=200):
    """
    Atalho para a Controladoria: devolve as intimacoes do periodo ja no formato
    que `triagem_lote()` consome.

    teor_integral=True busca o teor completo item a item (1 GET por intimacao),
    porque a listagem corta em 600 caracteres. `max_teor_integral` evita
    estourar rate limit numa janela grande - acima disso o item sobe truncado
    e marcado com `texto_truncado=True`.
    """
    brutos = listar_intimacoes(status='pendentes', dias=dias, acionaveis=acionaveis)
    resumos = []
    buscados = 0
    for bruto in brutos:
        teor = None
        ident = bruto.get('id') if isinstance(bruto, dict) else None
        if teor_integral and ident and buscados < max_teor_integral:
            try:
                detalhe = obter_intimacao(ident)
                teor = _primeiro(_achatar(detalhe), 'texto', 'teor', 'conteudo')
                buscados += 1
            except SyncError as e:
                print(f'    Aviso: nao foi possivel abrir a intimacao {ident}: {e}')
        resumos.append(resumir_intimacao(bruto, teor_integral=teor or None))
    if teor_integral and len(brutos) > max_teor_integral:
        print(f'  AVISO: {len(brutos) - max_teor_integral} intimacao(oes) ficaram com o '
              f'texto CORTADO em 600 caracteres (limite max_teor_integral). '
              f'Nao use essas linhas para ler dispositivo/KPI.')
    return resumos


# ============================================================
# DIAGNOSTICO
# ============================================================

def inspecionar(recurso='intimacoes', quantidade=1):
    """
    Imprime o JSON cru do Sync para calibrar o adaptador.

    O Swagger do Sync documenta os parametros mas NAO tipa as respostas
    (`schema: {}`), entao os nomes de campo so se confirmam contra a conta
    real. Rode isto assim que a chave do escritorio estiver ativa.
    """
    fontes = {
        'intimacoes': lambda: listar_intimacoes(status='todas', dias=30,
                                                itens_por_pagina=max(quantidade, 1),
                                                max_paginas=1),
        'prazos': lambda: listar_prazos(itens_por_pagina=max(quantidade, 1), max_paginas=1),
        'processos': lambda: listar_processos(itens_por_pagina=max(quantidade, 1), max_paginas=1),
        'monitores': listar_monitores,
        'webhooks': listar_webhooks,
    }
    if recurso not in fontes:
        print(f'  Recurso desconhecido: {recurso}. Use: {", ".join(fontes)}')
        return []
    brutos = fontes[recurso]()
    if not brutos:
        print(f'  Nenhum registro em {recurso}.')
        return []
    for i, bruto in enumerate(brutos[:quantidade], 1):
        print(f'\n  ----- {recurso.upper()} CRU #{i} -----')
        print(json.dumps(bruto, indent=2, ensure_ascii=False)[:4000])
        if recurso == 'intimacoes':
            print(f'\n  ----- ADAPTADO PARA A TRIAGEM #{i} -----')
            adaptado = {k: v for k, v in resumir_intimacao(bruto).items() if k != '_bruto'}
            print(json.dumps(adaptado, indent=2, ensure_ascii=False))
    return brutos


def testar_conexao():
    """Diagnostico da integracao: chave, conta, carteira e travas."""
    print('Testando conexao com o Sync (Atende Direito)...')
    print(f'  Base URL: {_base_url()}')
    if not _token(obrigatorio=False):
        print('  SYNC_API_TOKEN nao configurado em config/.env - integracao inativa.')
        return False
    try:
        dados = conta()
    except SyncError as e:
        print(f'  ERRO: {e}')
        return False

    achatado = _achatar(dados)
    nome = _primeiro(achatado, 'conta', 'nome', 'escritorio', 'razao_social', 'tenant_nome')
    plano = _primeiro(achatado, 'plano', 'plano_nome', 'assinatura.plano')
    print(f'  Conexao OK. Conta: {nome or "(sem nome)"} | Plano: {plano or "-"}')

    for rotulo, fn in (('monitores', listar_monitores), ('webhooks', listar_webhooks)):
        try:
            print(f'  {rotulo.capitalize()}: {len(fn())}')
        except SyncError as e:
            print(f'  {rotulo.capitalize()}: falha ({e})')

    print(f'  Escrita no Sync: {"LIBERADA" if escrita_liberada() else "BLOQUEADA (somente leitura)"}')
    print(f'  Webhook secret: {"configurado" if os.getenv("SYNC_WEBHOOK_SECRET") else "AUSENTE"}')
    return True


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    testar_conexao()
