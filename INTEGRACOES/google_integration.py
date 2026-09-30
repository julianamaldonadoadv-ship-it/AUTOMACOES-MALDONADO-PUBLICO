"""
Integração com Google Drive/Docs/Calendar - Maldonado Advogados

Modulo enxuto (auth + helpers genericos). NAO inclui geracao de documento por
template fixo (Ficha/Contrato/Procuracao) porque o Squad Comercial/Intake nao
faz parte do escopo contratado por este cliente nesta fase - ver
docs/_WHITE_LABEL_SPEC.md secao 5. Quando o cliente definir o formato de peca
final (DOCX gerado pelo Claude, ou template Google Docs com placeholders
{{CHAVE}}), usar preencher_documento() abaixo.
"""
import os
import sys
import io
import unicodedata
import requests
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar'
]

MIME_PASTA = 'application/vnd.google-apps.folder'

# Caminho da estrutura propria do escritorio (nao impor outra convencao):
# ZEUS > 03. CLIENTES > 01 CLIENTES > [LETRA] > [NOME DO CLIENTE] > 4 subpastas
CAMINHO_CLIENTES = ('ZEUS', '03. CLIENTES', '01 CLIENTES')

# Levantado no Drive real do escritorio (amostra de 60 clientes, 02/09/2026), NAO do
# _WHITE_LABEL_SPEC.md §7 — o spec dizia 'CONTRATO BANCÁRIO' e 'REUNIÕES - VIA MEET', que
# quase nao aparecem na pratica. Nenhum conjunto e universal (o mais comum esta em 42% dos
# clientes), entao isto e so o ponto de partida: sobrescreva com DRIVE_SUBPASTAS_CLIENTE.
SUBPASTAS_CLIENTE = (
    'DOC ADMINISTRATIVO',   # 42% dos clientes
    'DOC PESSOAL',          # 30%
    'DOC BANCARIO',         # 27%
    'DOC RURAL',            # 22%
)

# Saida da automacao de peca. Convencao definida pela Dra. Juliana (08/09/2026):
# ZEUS > PEÇAS AUTOMAÇÃO > [NOME DO CLIENTE] - [Nº DO PROCESSO] > peca.docx
# Fica na RAIZ da ZEUS (nao dentro da pasta do cliente) de proposito: o escritorio precisa
# conseguir auditar num lugar so tudo que a automacao produziu, sem varrer 60+ pastas de cliente.
PASTA_PECAS_AUTOMACAO = 'PEÇAS AUTOMAÇÃO'

# Peca de acao inicial ainda nao distribuida: rotulo explicito, para nao confundir com
# pasta em que alguem esqueceu de por o numero. Renomear quando sair a distribuicao.
SEM_PROCESSO = 'SEM PROCESSO'

# Todas as chamadas passam esses flags: a ZEUS pode estar num Drive compartilhado,
# e sem isso a API simplesmente nao devolve nada (falso-vazio, sem erro).
_DRIVE_COMPARTILHADO = {'supportsAllDrives': True, 'includeItemsFromAllDrives': True}

_CAMPOS_PADRAO = 'id, name, mimeType, modifiedTime, webViewLink, size'


def _escapar(valor: str) -> str:
    """Escapa aspas simples/barras para uso dentro de query da API do Drive.

    Sem isso, cliente com apostrofo no nome (ex.: D'ALMEIDA) quebra a consulta.
    """
    return str(valor).replace('\\', '\\\\').replace("'", "\\'")


def _sem_acento(texto: str) -> str:
    """Normaliza para comparar nome de pasta (Drive nao e' consistente com acento/caixa)."""
    nfd = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').strip().upper()


def _listar(drive_service, query: str, limite: int = 100, campos: str = _CAMPOS_PADRAO):
    """Executa files().list paginando, ja com suporte a Drive compartilhado."""
    itens, token = [], None
    while True:
        resposta = drive_service.files().list(
            q=query, corpora='allDrives', pageSize=min(limite - len(itens), 100),
            fields=f'nextPageToken, files({campos})', pageToken=token,
            **_DRIVE_COMPARTILHADO,
        ).execute()
        itens.extend(resposta.get('files', []))
        token = resposta.get('nextPageToken')
        if not token or len(itens) >= limite:
            return itens[:limite]



def conta_esperada():
    """E-mail da conta Google do escritorio (config/.env -> GOOGLE_CONTA_ESCRITORIO)."""
    return (os.getenv('GOOGLE_CONTA_ESCRITORIO') or '').strip().lower()


def conta_autenticada(drive_service):
    """E-mail da conta a que o token atual pertence (None se nao der pra descobrir)."""
    try:
        sobre = drive_service.about().get(fields='user(emailAddress, displayName)').execute()
        return (sobre.get('user') or {}).get('emailAddress')
    except Exception:
        return None


def _conferir_conta(drive_service):
    """Aborta se o token for de outra conta que nao a do escritorio.

    Sem isso, um token esquecido de outro Google (outro escritorio, conta pessoal, conta de
    implantacao) faria o sistema ler e GRAVAR documento de cliente no Drive errado. Se
    GOOGLE_CONTA_ESCRITORIO estiver vazio, so informa qual conta esta conectada.
    """
    atual = conta_autenticada(drive_service)
    esperada = conta_esperada()

    if not esperada:
        if atual:
            print(f'  Conta Google conectada: {atual}')
            print('  (defina GOOGLE_CONTA_ESCRITORIO em config/.env para travar nesta conta)')
        return atual

    if atual and atual.strip().lower() != esperada:
        raise RuntimeError(
            f'CONTA GOOGLE ERRADA: o token em config/token.json e da conta "{atual}", '
            f'mas o esperado e "{esperada}" (GOOGLE_CONTA_ESCRITORIO).\n'
            f'  Rode:  python OPERACIONAL/main.py drive sair\n'
            f'  e depois:  python OPERACIONAL/main.py drive autenticar')

    print(f'  Conta Google conferida: {(atual or esperada).strip()}')
    return atual


# ------------------------------------------------------------
# Gmail - SOMENTE LEITURA, com token proprio
# ------------------------------------------------------------
# Escopo e token separados de proposito: somar o Gmail ao SCOPES geral
# invalidaria o config/token.json que o Drive (e a rotina da VPS) ja usam e
# forcaria novo login em tudo. Aqui o token e' config/token_gmail.json
# (coberto pelo config/token*.json do .gitignore e do enviar.sh).
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def autenticar_gmail():
    """Autentica o Gmail (leitura) com a conta do escritorio.

    Devolve (service, email_da_conta). Aplica a mesma trava de conta do Drive
    (GOOGLE_CONTA_ESCRITORIO). Service Account nao le caixa de e-mail, entao
    so funciona com config/oauth_credentials.json.
    """
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    oauth_creds_path = os.getenv("GOOGLE_OAUTH_CREDENTIALS",
                                 os.path.join(config_dir, "oauth_credentials.json"))
    token_path = os.path.join(config_dir, "token_gmail.json")

    if not os.path.exists(oauth_creds_path):
        raise RuntimeError('Gmail exige config/oauth_credentials.json (login da conta do '
                           'escritorio). Service Account nao le caixa de e-mail.')

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print(f"Token do Gmail expirado ou revogado ({e}). Pedindo autorizacao de novo...")
                creds = None
        if not creds or not creds.valid:
            esperada = conta_esperada()
            print("Abrindo navegador para autorizar a LEITURA do Gmail...")
            if esperada:
                print(f"ATENCAO: faca login com {esperada} - nenhuma outra conta.")
            flow = InstalledAppFlow.from_client_secrets_file(oauth_creds_path, GMAIL_SCOPES)
            extras = {'login_hint': esperada} if esperada else {}
            creds = flow.run_local_server(port=0, **extras)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    gmail = build('gmail', 'v1', credentials=creds)
    atual = gmail.users().getProfile(userId='me').execute().get('emailAddress')
    esperada = conta_esperada()
    if esperada and atual and atual.strip().lower() != esperada:
        raise RuntimeError(
            f'CONTA GOOGLE ERRADA NO GMAIL: o token e da conta "{atual}", mas o esperado e '
            f'"{esperada}". Apague config/token_gmail.json e rode: '
            f'python OPERACIONAL/main.py gmail autenticar')
    return gmail, atual


def _cabecalho(msg, nome):
    for h in msg.get('payload', {}).get('headers', []):
        if h.get('name', '').lower() == nome.lower():
            return h.get('value', '')
    return ''


def _partes(payload):
    """Percorre as partes MIME (multipart aninhado) de uma mensagem."""
    pilha = [payload]
    while pilha:
        parte = pilha.pop()
        yield parte
        pilha.extend(parte.get('parts', []) or [])


def buscar_emails(gmail, consulta, limite=20):
    """Busca mensagens com a sintaxe do Gmail (ex.: 'reuniao estrategica Agenor has:attachment').

    Devolve lista de dicts: id, data, de, assunto, trecho, anexos (nomes).
    """
    resp = gmail.users().messages().list(userId='me', q=consulta, maxResults=limite).execute()
    saida = []
    for m in resp.get('messages', []):
        msg = gmail.users().messages().get(userId='me', id=m['id'], format='full').execute()
        anexos = [p['filename'] for p in _partes(msg.get('payload', {}))
                  if p.get('filename') and p.get('body', {}).get('attachmentId')]
        saida.append({
            'id': m['id'],
            'data': _cabecalho(msg, 'Date'),
            'de': _cabecalho(msg, 'From'),
            'assunto': _cabecalho(msg, 'Subject'),
            'trecho': msg.get('snippet', ''),
            'anexos': anexos,
        })
    return saida


def baixar_email(gmail, msg_id, destino):
    """Salva o corpo em texto (corpo.txt) e todos os anexos da mensagem em `destino`.

    Somente leitura no Gmail. Devolve a lista de caminhos gravados localmente.
    """
    import base64
    os.makedirs(destino, exist_ok=True)
    msg = gmail.users().messages().get(userId='me', id=msg_id, format='full').execute()
    gravados = []

    texto = []
    for p in _partes(msg.get('payload', {})):
        dados = p.get('body', {}).get('data')
        if p.get('mimeType') == 'text/plain' and dados and not p.get('filename'):
            texto.append(base64.urlsafe_b64decode(dados).decode('utf-8', errors='replace'))
    corpo = os.path.join(destino, 'corpo.txt')
    with open(corpo, 'w', encoding='utf-8') as f:
        f.write(f"Assunto: {_cabecalho(msg, 'Subject')}\nDe: {_cabecalho(msg, 'From')}\n"
                f"Data: {_cabecalho(msg, 'Date')}\n\n" + '\n'.join(texto))
    gravados.append(corpo)

    for p in _partes(msg.get('payload', {})):
        att_id = p.get('body', {}).get('attachmentId')
        if not (p.get('filename') and att_id):
            continue
        att = gmail.users().messages().attachments().get(
            userId='me', messageId=msg_id, id=att_id).execute()
        caminho = os.path.join(destino, os.path.basename(p['filename']))
        with open(caminho, 'wb') as f:
            f.write(base64.urlsafe_b64decode(att['data']))
        gravados.append(caminho)
    return gravados


def esquecer_credencial(revogar=True):
    """Desconecta a conta Google: revoga o token no Google e apaga config/token.json.

    Usar quando o sistema foi autenticado com a conta errada.
    """
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    token_path = os.path.join(config_dir, 'token.json')

    if not os.path.exists(token_path):
        return False, 'Nenhum token local para remover (config/token.json nao existe).'

    revogado = 'token local apagado'
    if revogar:
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            alvo = creds.refresh_token or creds.token
            resposta = requests.post('https://oauth2.googleapis.com/revoke',
                                     params={'token': alvo},
                                     headers={'content-type': 'application/x-www-form-urlencoded'},
                                     timeout=15)
            revogado = ('acesso revogado no Google + token local apagado'
                        if resposta.status_code == 200
                        else f'token local apagado (revogacao remota falhou: HTTP {resposta.status_code})')
        except Exception as e:
            revogado = f'token local apagado (nao deu pra revogar no Google: {e})'

    os.remove(token_path)
    return True, revogado


def autenticar_google():
    """
    Autentica com OAuth2 (conta do escritorio) se oauth_credentials.json existir.
    Caso contrario, usa Service Account como fallback.
    """
    project_root = os.path.join(os.path.dirname(__file__), '..')
    config_dir = os.path.join(project_root, 'config')
    oauth_creds_path = os.getenv("GOOGLE_OAUTH_CREDENTIALS", os.path.join(config_dir, "oauth_credentials.json"))
    token_path = os.path.join(config_dir, "token.json")
    sa_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.join(config_dir, "credentials.json"))

    creds = None

    if os.path.exists(oauth_creds_path):
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            renovou = False
            if creds and creds.expired and creds.refresh_token:
                print("Renovando token de acesso...")
                try:
                    creds.refresh(Request())
                    renovou = True
                except RefreshError as e:
                    # Token revogado/expirado de vez (o Google invalida o refresh
                    # token depois de um tempo sem uso, ou quando a senha muda).
                    # Antes isso derrubava o comando com stack trace; o certo e'
                    # descartar o token e pedir o consentimento de novo.
                    print(f"Token expirado ou revogado ({e}). Pedindo autorizacao de novo...")
                    creds = None
                    try:
                        os.remove(token_path)
                    except OSError:
                        pass
            if not renovou:
                esperada = conta_esperada()
                print("Abrindo navegador para login com a conta Google do escritorio...")
                if esperada:
                    print(f"ATENCAO: faca login com {esperada} - nenhuma outra conta.")
                print("(isso so precisa ser feito uma vez)")
                flow = InstalledAppFlow.from_client_secrets_file(oauth_creds_path, SCOPES)
                extras = {'login_hint': esperada} if esperada else {}
                creds = flow.run_local_server(port=0, **extras)

            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        print("Autenticado com a conta Google do escritorio!")

    elif os.path.exists(sa_creds_path):
        print("AVISO: Usando Service Account (cota limitada).")
        print("Para usar a conta do escritorio, configure oauth_credentials.json")
        creds = service_account.Credentials.from_service_account_file(
            sa_creds_path, scopes=SCOPES)
    else:
        print("ERRO: Nenhum arquivo de credenciais encontrado.")
        print("Coloque 'oauth_credentials.json' ou 'credentials.json' na pasta config/.")
        sys.exit(1)

    try:
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
    except Exception as e:
        print(f"ERRO DE AUTENTICACAO: {str(e)}")
        sys.exit(1)

    # Trava: nunca operar no Drive de outra conta que nao a do escritorio.
    try:
        _conferir_conta(drive_service)
    except RuntimeError as e:
        print(f"\n{e}\n")
        sys.exit(1)

    return drive_service, docs_service


def buscar_pasta_por_nome(drive_service, nome: str, pasta_pai_id: str = None):
    """Busca uma pasta pelo nome (opcionalmente dentro de um pai). Retorna o ID ou None.

    Uso tipico no escritorio: navegar a estrutura dele (ZEUS > 03. CLIENTES > 01 CLIENTES
    > [LETRA] > [NOME DO CLIENTE]) sem hardcodar IDs de pasta.
    """
    query = f"name = '{_escapar(nome)}' and mimeType = '{MIME_PASTA}' and trashed = false"
    if pasta_pai_id:
        query += f" and '{pasta_pai_id}' in parents"
    arquivos = _listar(drive_service, query, limite=10)
    return arquivos[0]['id'] if arquivos else None


def preencher_documento(docs_service, document_id: str, dados: dict):
    """
    Edita um documento Google via BatchUpdate substituindo placeholders {{CHAVE}}
    pelos valores do dicionario. Uso: gerar peca a partir de um template com marcadores.
    """
    print("Preenchendo documento...")

    requests = []
    for chave, valor in dados.items():
        if not isinstance(valor, str):
            valor = str(valor)
        requests.append({
            'replaceAllText': {
                'containsText': {'text': f"{{{{{chave}}}}}", 'matchCase': True},
                'replaceText': valor
            }
        })

    try:
        docs_service.documents().batchUpdate(
            documentId=document_id, body={'requests': requests}).execute()
        print("Documento finalizado com sucesso.")
    except HttpError as error:
        print("ERRO DE API DOCS: falha ao formatar o texto do arquivo.")
        print(f"Detalhes: {error}")
        sys.exit(1)


# ============================================================
# GOOGLE DRIVE — estrutura ZEUS do escritorio (Squad Controladoria / Divida Rural)
# ============================================================

def listar_pasta(drive_service, pasta_id: str, apenas_pastas: bool = False, limite: int = 200):
    """Lista o conteudo de uma pasta (id, name, mimeType, webViewLink)."""
    query = f"'{_escapar(pasta_id)}' in parents and trashed = false"
    if apenas_pastas:
        query += f" and mimeType = '{MIME_PASTA}'"
    itens = _listar(drive_service, query, limite=limite)
    return sorted(itens, key=lambda f: (f.get('mimeType') != MIME_PASTA, _sem_acento(f.get('name', ''))))


def buscar_por_caminho(drive_service, caminho, raiz_id: str = None):
    """Resolve um caminho de pastas ('ZEUS', '03. CLIENTES', ...) e retorna o ID da ultima.

    Retorna None se qualquer nivel faltar — quem chama decide se isso e' erro ou se cria.
    """
    atual = raiz_id
    for nivel in caminho:
        atual = buscar_pasta_por_nome(drive_service, nivel, atual)
        if not atual:
            return None
    return atual


def pasta_clientes(drive_service):
    """ID da pasta '01 CLIENTES'.

    Usa DRIVE_PASTA_CLIENTES_ID do .env se estiver preenchido (caminho rapido e a prova de
    renomeacao); senao navega ZEUS > 03. CLIENTES > 01 CLIENTES a partir de
    DRIVE_PASTA_ZEUS_ID (ou da raiz, se nem isso estiver configurado).
    """
    direto = (os.getenv('DRIVE_PASTA_CLIENTES_ID') or '').strip()
    if direto:
        return direto

    zeus_id = (os.getenv('DRIVE_PASTA_ZEUS_ID') or '').strip()
    if zeus_id:
        return buscar_por_caminho(drive_service, CAMINHO_CLIENTES[1:], zeus_id)
    return buscar_por_caminho(drive_service, CAMINHO_CLIENTES)


def _letra_inicial(nome_cliente: str) -> str:
    """Letra da pasta-indice do cliente (A..Z), pela 1a letra do nome sem acento."""
    for c in _sem_acento(nome_cliente):
        if c.isalpha():
            return c
    return '#'


def _pasta_da_letra(drive_service, clientes_id: str, letra: str):
    """Acha a pasta-indice da letra dentro de '01 CLIENTES'.

    Tolerante a variacao de nomenclatura ('A', '[A]', '01 A'): compara so os alfanumericos.
    """
    for pasta in listar_pasta(drive_service, clientes_id, apenas_pastas=True):
        limpo = ''.join(c for c in _sem_acento(pasta['name']) if c.isalnum())
        if limpo == letra:
            return pasta['id']
    return None


def pasta_do_cliente(drive_service, nome_cliente: str):
    """Localiza a pasta de um cliente na estrutura ZEUS. Retorna o dict do arquivo ou None.

    Procura sob a letra esperada (match exato primeiro, depois parcial); se nao achar,
    cai para uma busca global por nome — cliente cadastrado fora da letra e' comum.
    Nao cria nada — ver criar_estrutura_cliente().
    """
    clientes_id = pasta_clientes(drive_service)
    if not clientes_id:
        return None

    alvo = _sem_acento(nome_cliente)
    pasta_letra_id = _pasta_da_letra(drive_service, clientes_id, _letra_inicial(nome_cliente))

    parcial = None
    if pasta_letra_id:
        for pasta in listar_pasta(drive_service, pasta_letra_id, apenas_pastas=True):
            if _sem_acento(pasta['name']) == alvo:
                return pasta
            if parcial is None and alvo in _sem_acento(pasta['name']):
                parcial = pasta
    if parcial:
        return parcial

    query = (f"name contains '{_escapar(nome_cliente)}' and mimeType = '{MIME_PASTA}' "
             f"and trashed = false")
    candidatos = _listar(drive_service, query, limite=20)
    return candidatos[0] if candidatos else None


def buscar_subpasta(drive_service, pasta_pai_id: str, nome: str):
    """Acha uma subpasta tolerando as variacoes reais do Drive do escritorio.

    As pastas do escritorio tem espaco sobrando no fim ('DOC PESSOAL '), acento inconsistente
    e caixa variada — busca exata por nome falha nesses casos. Compara normalizado; se nao
    houver igual, aceita quem contem o termo (ex.: 'BANCARIO' -> 'DOC BANCARIO ').
    Retorna o dict da pasta ou None.
    """
    alvo = _sem_acento(nome)
    parcial = None
    for pasta in listar_pasta(drive_service, pasta_pai_id, apenas_pastas=True):
        atual = _sem_acento(pasta['name'])
        if atual == alvo:
            return pasta
        if parcial is None and (alvo in atual or atual in alvo):
            parcial = pasta
    return parcial


def criar_pasta(drive_service, nome: str, pasta_pai_id: str):
    """Cria uma pasta (ou devolve a existente, se ja houver equivalente no pai).

    Usa comparacao normalizada: sem isso, criar 'DOC PESSOAL' num cliente que ja tem
    'DOC PESSOAL ' (com espaco) geraria duas pastas irmas quase identicas.
    """
    existente = buscar_subpasta(drive_service, pasta_pai_id, nome)
    if existente:
        return existente['id']
    corpo = {'name': nome, 'mimeType': MIME_PASTA, 'parents': [pasta_pai_id]}
    pasta = drive_service.files().create(
        body=corpo, fields='id, name, webViewLink', supportsAllDrives=True).execute()
    return pasta['id']


def criar_estrutura_cliente(drive_service, nome_cliente: str):
    """Cria [LETRA] > [NOME DO CLIENTE] > 4 subpastas, seguindo a convencao do escritorio.

    Idempotente: o que ja existe e' reaproveitado. NUNCA chamar sem confirmacao explicita
    do usuario (regra de ouro do projeto) — o CLI pergunta antes.
    Retorna (pasta_cliente_id, {nome_subpasta: id}).
    """
    clientes_id = pasta_clientes(drive_service)
    if not clientes_id:
        raise RuntimeError(
            "Pasta '01 CLIENTES' nao encontrada. Preencha DRIVE_PASTA_CLIENTES_ID (ou "
            "DRIVE_PASTA_ZEUS_ID) em config/.env, ou confira se a conta autenticada tem "
            "acesso a ZEUS.")

    letra = _letra_inicial(nome_cliente)
    pasta_letra_id = _pasta_da_letra(drive_service, clientes_id, letra) or \
        criar_pasta(drive_service, letra, clientes_id)

    cliente_id = criar_pasta(drive_service, nome_cliente.strip(), pasta_letra_id)

    subpastas = {}
    for nome_sub in _subpastas_configuradas():
        subpastas[nome_sub] = criar_pasta(drive_service, nome_sub, cliente_id)

    return cliente_id, subpastas


def _subpastas_configuradas():
    """Subpastas do cliente — SUBPASTAS_CLIENTE, sobrescrevivel por DRIVE_SUBPASTAS_CLIENTE."""
    bruto = (os.getenv('DRIVE_SUBPASTAS_CLIENTE') or '').strip()
    if bruto:
        return [s.strip() for s in bruto.split(',') if s.strip()]
    return list(SUBPASTAS_CLIENTE)


def _zeus_id(drive_service):
    """ID da pasta ZEUS — do .env se configurado, senao busca pelo nome."""
    direto = (os.getenv('DRIVE_PASTA_ZEUS_ID') or '').strip()
    return direto or buscar_pasta_por_nome(drive_service, 'ZEUS')


def pasta_pecas_automacao(drive_service, criar: bool = False):
    """ID da pasta 'PEÇAS AUTOMAÇÃO' na raiz da ZEUS.

    DRIVE_PASTA_PECAS_AUTOMACAO_ID no .env e' o caminho rapido (a prova de renomeacao).
    Sem ele, localiza pelo nome dentro da ZEUS. Retorna None se nao existir e criar=False —
    criar a pasta-mae e' decisao do escritorio, nao efeito colateral de gerar peca.
    """
    direto = (os.getenv('DRIVE_PASTA_PECAS_AUTOMACAO_ID') or '').strip()
    if direto:
        return direto

    zeus_id = _zeus_id(drive_service)
    if not zeus_id:
        raise RuntimeError(
            "Pasta ZEUS nao encontrada. Preencha DRIVE_PASTA_ZEUS_ID em config/.env ou "
            "confira se a conta autenticada tem acesso a ela.")

    existente = buscar_subpasta(drive_service, zeus_id, PASTA_PECAS_AUTOMACAO)
    if existente:
        return existente['id']
    return criar_pasta(drive_service, PASTA_PECAS_AUTOMACAO, zeus_id) if criar else None


def nome_pasta_peca(nome_cliente: str, numero_processo: str = None) -> str:
    """Monta '[NOME DO CLIENTE] - [Nº DO PROCESSO]' (ou '- SEM PROCESSO')."""
    cliente = ' '.join(str(nome_cliente or '').split()).strip()
    if not cliente:
        raise ValueError('nome_cliente e obrigatorio para criar a pasta da peca.')
    processo = ' '.join(str(numero_processo or '').split()).strip() or SEM_PROCESSO
    # '/' quebraria o nome da pasta no Drive; numero CNJ nao usa barra, mas entrada humana usa.
    return f"{cliente} - {processo}".replace('/', '-')


def pasta_da_peca(drive_service, nome_cliente: str, numero_processo: str = None,
                  criar: bool = True):
    """ID da subpasta do cliente dentro de 'PEÇAS AUTOMAÇÃO'.

    Idempotente: reaproveita a pasta existente (comparacao normalizada, como no resto do
    modulo) em vez de criar uma irma quase identica.
    """
    raiz = pasta_pecas_automacao(drive_service, criar=criar)
    if not raiz:
        raise RuntimeError(
            f"Pasta '{PASTA_PECAS_AUTOMACAO}' nao existe na ZEUS. Crie-a uma vez (ou preencha "
            "DRIVE_PASTA_PECAS_AUTOMACAO_ID em config/.env) antes de arquivar peca.")

    nome = nome_pasta_peca(nome_cliente, numero_processo)
    existente = buscar_subpasta(drive_service, raiz, nome)
    if existente:
        return existente['id']
    if not criar:
        return None
    return criar_pasta(drive_service, nome, raiz)


def liberar_edicao(drive_service, file_id: str, emails, notificar: bool = False):
    """Da permissao de EDICAO (writer) no arquivo a cada e-mail. Idempotente.

    Regra da Dra. Juliana (18/09/2026): peca que a automacao devolve ao advogado
    ja sai com edicao liberada para o advogado responsavel. Sem isso, cada
    devolutiva gerava um pedido de acesso e a peca parava ate a GJ aprovar.
    Quem ja tem acesso de edicao (ou e' dono) e' pulado; quem tem so leitura sobe
    para edicao. notificar=False porque o link vai no AGENDAMENTO do ADVBOX.
    Retorna a lista de e-mails efetivamente liberados.
    """
    alvos = [e.strip().lower() for e in ([emails] if isinstance(emails, str) else emails or [])
             if e and e.strip()]
    if not alvos:
        return []
    atuais = drive_service.permissions().list(
        fileId=file_id, fields='permissions(id,emailAddress,role)',
        supportsAllDrives=True).execute().get('permissions', [])
    por_email = {(p.get('emailAddress') or '').lower(): p for p in atuais}

    liberados = []
    for email in dict.fromkeys(alvos):
        atual = por_email.get(email)
        if atual and atual.get('role') in ('owner', 'organizer', 'fileOrganizer', 'writer'):
            continue
        if atual:
            drive_service.permissions().update(
                fileId=file_id, permissionId=atual['id'], body={'role': 'writer'},
                supportsAllDrives=True).execute()
        else:
            drive_service.permissions().create(
                fileId=file_id, body={'type': 'user', 'role': 'writer', 'emailAddress': email},
                sendNotificationEmail=notificar, supportsAllDrives=True).execute()
        liberados.append(email)
    return liberados


def arquivar_peca(drive_service, caminho_local: str, nome_cliente: str,
                  numero_processo: str = None, nome_arquivo: str = None,
                  converter_google_docs: bool = False, editores=None):
    """Guarda a peca produzida em ZEUS > PEÇAS AUTOMAÇÃO > [CLIENTE] - [PROCESSO].

    editores: e-mail(s) que recebem edicao no arquivo (o advogado responsavel —
    ver advbox_integration.email_usuario()). Regra da GJ: peca devolvida ao
    advogado sai com edicao liberada.

    NUNCA chamar sem confirmacao explicita (regra de ouro do projeto) — o CLI pergunta antes.
    Retorna (arquivo, pasta_id).
    """
    pasta_id = pasta_da_peca(drive_service, nome_cliente, numero_processo, criar=True)
    arquivo = enviar_arquivo(drive_service, caminho_local, pasta_id, nome=nome_arquivo,
                             converter_google_docs=converter_google_docs)
    if editores:
        liberar_edicao(drive_service, arquivo['id'], editores)
    return arquivo, pasta_id


def enviar_arquivo(drive_service, caminho_local: str, pasta_id: str, nome: str = None,
                   converter_google_docs: bool = False):
    """Envia um arquivo local para uma pasta do Drive. Retorna o dict do arquivo criado.

    converter_google_docs=True transforma .docx em Google Docs (util para revisao a varias
    maos da peca antes do protocolo); False mantem o .docx original.
    """
    if not os.path.exists(caminho_local):
        raise FileNotFoundError(f'Arquivo nao encontrado: {caminho_local}')

    nome_final = nome or os.path.basename(caminho_local)
    midia = MediaFileUpload(caminho_local, resumable=True)

    # Peca revisada SUBSTITUI a anterior no MESMO fileId (POP-CJ-003-B, etapa 9):
    # o link ja esta na tarefa do ADVBOX e nos convites de agenda, e nao pode
    # quebrar. Sem isso, cada revisao criava um arquivo novo com o mesmo nome e
    # a pasta acumulava duplicatas - foi o que aconteceu na peca do Cliente AG
    # (10/09/2026).
    existente = _listar(
        drive_service,
        f"'{pasta_id}' in parents and name = '{_escapar(nome_final)}' and trashed = false",
        limite=1)
    if existente:
        return drive_service.files().update(
            fileId=existente[0]['id'], media_body=midia,
            fields=_CAMPOS_PADRAO, supportsAllDrives=True).execute()

    corpo = {'name': nome_final, 'parents': [pasta_id]}
    if converter_google_docs:
        corpo['mimeType'] = 'application/vnd.google-apps.document'
    return drive_service.files().create(
        body=corpo, media_body=midia, fields=_CAMPOS_PADRAO, supportsAllDrives=True).execute()


def baixar_arquivo(drive_service, file_id: str, destino: str):
    """Baixa um arquivo do Drive para `destino`. Exporta Google Docs/Sheets como .docx/.xlsx."""
    meta = drive_service.files().get(
        fileId=file_id, fields='id, name, mimeType', supportsAllDrives=True).execute()
    mime = meta.get('mimeType', '')

    exportacoes = {
        'application/vnd.google-apps.document':
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.google-apps.spreadsheet':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.google-apps.presentation':
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    }

    if mime in exportacoes:
        pedido = drive_service.files().export_media(fileId=file_id, mimeType=exportacoes[mime])
    elif mime.startswith('application/vnd.google-apps'):
        raise RuntimeError(f'Tipo do Google sem exportacao suportada: {mime}')
    else:
        pedido = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)

    if os.path.isdir(destino):
        destino = os.path.join(destino, meta['name'])

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, pedido)
    concluido = False
    while not concluido:
        _, concluido = downloader.next_chunk()

    with open(destino, 'wb') as f:
        f.write(buffer.getvalue())
    return destino


def link_pasta(pasta_id: str) -> str:
    return f'https://drive.google.com/drive/folders/{pasta_id}'


# ============================================================
# GOOGLE CALENDAR — convites de prazo (Squad Controladoria)
# ============================================================

def _calendar_service():
    """Servico do Calendar reusando o token OAuth (mesma conta do Drive)."""
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    token_path = os.path.join(config_dir, 'token.json')
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    return build('calendar', 'v3', credentials=creds)


def criar_evento_prazo(titulo, data_ymd, descricao='', convidados=None, hora_inicio='09:00', duracao_min=60):
    """Cria um evento no Google Agenda para um prazo fatal e envia convite pros e-mails da equipe.

    data_ymd: 'YYYY-MM-DD'
    convidados: lista de e-mails (recebem convite; sendUpdates=all)
    Retorna o link do evento, ou None se falhar.
    """
    try:
        cal = _calendar_service()
        h, m = (hora_inicio.split(':') + ['00'])[:2]
        fim_min = int(h) * 60 + int(m) + duracao_min
        fim_h, fim_m = divmod(fim_min, 60)
        body = {
            'summary': titulo,
            'description': descricao,
            'start': {'dateTime': f'{data_ymd}T{int(h):02d}:{int(m):02d}:00', 'timeZone': 'America/Porto_Velho'},
            'end': {'dateTime': f'{data_ymd}T{fim_h:02d}:{fim_m:02d}:00', 'timeZone': 'America/Porto_Velho'},
            'attendees': [{'email': e} for e in (convidados or [])],
            'reminders': {'useDefault': False, 'overrides': [
                {'method': 'popup', 'minutes': 60}, {'method': 'email', 'minutes': 1440}]},
        }
        ev = cal.events().insert(calendarId='primary', body=body, sendUpdates='all').execute()
        print(f'   Evento na agenda criado: {titulo} ({data_ymd}) -> {ev.get("htmlLink")}')
        return ev.get('htmlLink')
    except Exception as e:
        print(f'   Aviso: falha ao criar evento na agenda: {e}')
        return None
