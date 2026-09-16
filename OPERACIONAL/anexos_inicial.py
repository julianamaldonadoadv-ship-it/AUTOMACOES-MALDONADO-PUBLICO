"""
=============================================================================
  ANEXOS DA PETICAO INICIAL - Squad Divida Rural / Maldonado Advogados
=============================================================================

  Toda inicial do escritorio e' instruida por documentos que ficam na pasta do
  cliente na ZEUS, e os modelos de inicial trazem placeholders literais onde o
  recorte desse documento tem que entrar no corpo da peca
  (ex.: "INSERIR UMA IMAGEM.", "IMAGEM DO REQUERIMENTO QUE FOI ENVIADO AO BANCO",
  "INSERIR GRAFICO" - ver BASE_CONHECIMENTO/05 - FORMATACAO/).

  Este modulo faz as 4 pontas desse trabalho, sem decidir nada sozinho:

    1. INVENTARIO  - varre a pasta do cliente no Drive e classifica cada arquivo
                     por tipo de documento (heuristica de nome + subpasta).
    2. CONFERENCIA - cruza o inventario com o rol exigido pela tese escolhida e
                     diz o que tem, o que falta e o que nao deu pra classificar.
    3. RECORTE     - renderiza a pagina (ou so a regiao ao redor de um termo) do
                     PDF em PNG, para entrar como imagem no corpo da peca.
    4. MONTAGEM    - substitui o placeholder do modelo pela imagem + legenda, ou,
                     se o documento nao existir, marca a pendencia em amarelo.

  Regra de ouro do projeto: nada aqui protocola, nada aqui grava no Drive.
  Documento que nao foi encontrado vira PENDENCIA destacada - nunca suposicao.
=============================================================================
"""
import os
import re

from docx.oxml.ns import qn
import shutil
import unicodedata
from copy import deepcopy

# ============================================================
# CATALOGO DE TIPOS DE DOCUMENTO
# ============================================================
# 'termos'    - o que procurar no nome do arquivo (sem acento, minusculo).
#               Termo com ate 4 caracteres so casa como palavra inteira, senao
#               'car' casaria com 'carta' e 'cpr' com qualquer coisa.
# 'subpastas' - onde o documento costuma estar na pasta do cliente. So pontua
#               (nao filtra): o Drive real tem 43 variantes de nome de subpasta.
# 'recorte'   - se o documento pode virar imagem no CORPO da peca. Documento
#               pessoal (RG, CPF, comprovante de residencia) entra no rol de
#               anexos, nunca recortado no corpo - dado sensivel exposto na peca.
# 'busca'     - termos que localizam a pagina/regiao relevante dentro do PDF.

TIPOS_DOCUMENTO = (
    {'slug': 'procuracao', 'rotulo': 'Procuração ad judicia',
     'termos': ('procuracao', 'proc ad judicia', 'substabelecimento'),
     'subpastas': ('DOC PESSOAL', 'PROCURACAO'), 'recorte': False, 'busca': ()},

    {'slug': 'doc-pessoal', 'rotulo': 'Documento pessoal (RG/CNH/CPF)',
     'termos': ('rg', 'cnh', 'cpf', 'identidade', 'doc pessoal', 'documento pessoal',
                'carteira de identidade', 'habilitacao'),
     'subpastas': ('DOC PESSOAL',), 'recorte': False, 'busca': ()},

    {'slug': 'comprovante-residencia', 'rotulo': 'Comprovante de residência',
     'termos': ('comprovante de residencia', 'residencia', 'energisa', 'ceron',
                'conta de luz', 'conta de agua', 'caerd'),
     'subpastas': ('DOC PESSOAL',), 'recorte': False, 'busca': ()},

    {'slug': 'estado-civil', 'rotulo': 'Certidão de casamento/nascimento',
     'termos': ('certidao de casamento', 'certidao de nascimento', 'casamento',
                'uniao estavel', 'averbacao'),
     'subpastas': ('DOC PESSOAL',), 'recorte': False, 'busca': ()},

    {'slug': 'hipossuficiencia', 'rotulo': 'Comprovação de hipossuficiência (IRPF/declaração)',
     'termos': ('hipossuficiencia', 'declaracao de pobreza', 'irpf', 'imposto de renda',
                'dirpf', 'gratuidade', 'declaracao de rendimentos'),
     'subpastas': ('DOC PESSOAL', 'IRPF'), 'recorte': False, 'busca': ()},

    {'slug': 'contrato-social', 'rotulo': 'Contrato social / CNPJ (autor pessoa jurídica)',
     'termos': ('contrato social', 'cnpj', 'cartao cnpj', 'estatuto', 'alteracao contratual'),
     'subpastas': ('DOC ADMINISTRATIVO', 'DOC PESSOAL'), 'recorte': False, 'busca': ()},

    {'slug': 'cedula', 'rotulo': 'Cédula / contrato bancário rural (CCB, CPR, CRP, CPRF)',
     'termos': ('cedula', 'ccb', 'cpr', 'crp', 'cprf', 'contrato bancario', 'pignoraticia',
                'hipotecaria', 'contrato de financiamento', 'financiamento', 'credito rural',
                'instrumento particular'),
     'subpastas': ('DOC BANCARIO', 'CEDULA', 'CONTRATO BANCARIO'), 'recorte': True,
     'busca': ('capitaliza', 'taxa efetiva', 'juros remunerat', 'taxa de juros', 'encargos')},

    {'slug': 'aditivo', 'rotulo': 'Aditivo / renegociação / repactuação',
     'termos': ('aditivo', 'renegociacao', 'repactuacao', 'composicao de divida',
                'confissao de divida', 'termo aditivo'),
     'subpastas': ('DOC BANCARIO',), 'recorte': True,
     'busca': ('capitaliza', 'taxa', 'saldo devedor')},

    {'slug': 'ficha-grafica', 'rotulo': 'Ficha gráfica / evolução do débito / demonstrativo',
     'termos': ('ficha grafica', 'ficha', 'evolucao', 'demonstrativo', 'planilha',
                'saldo devedor', 'memoria de calculo', 'calculo', 'extrato de divida'),
     'subpastas': ('DOC BANCARIO',), 'recorte': True,
     'busca': ('saldo devedor', 'juros', 'encargos', 'vencimento')},

    {'slug': 'banco-movimentacao', 'rotulo': 'Extrato bancário / movimentação financeira',
     'termos': ('extrato', 'movimentacao', 'comprovante de pagamento', 'ted', 'deposito',
                'conta corrente'),
     'subpastas': ('DOC BANCARIO',), 'recorte': True, 'busca': ('saldo', 'lancamento')},

    {'slug': 'negativacao', 'rotulo': 'Negativação SPC/Serasa/CCF ou protesto',
     'termos': ('serasa', 'spc', 'ccf', 'negativacao', 'protesto', 'restricao',
                'cadastro de inadimplentes', 'consulta de credito'),
     'subpastas': ('DOC ADMINISTRATIVO', 'DOC BANCARIO'), 'recorte': True,
     'busca': ('pendencia', 'anotacao', 'valor', 'inclusao')},

    {'slug': 'requerimento-banco', 'rotulo': 'Requerimento administrativo ao banco + protocolo',
     'termos': ('requerimento', 'prorrogacao', 'notificacao extrajudicial', 'notificacao',
                'protocolo', 'aviso de recebimento', 'pedido administrativo', 'email',
                'e-mail'),
     'subpastas': ('DOC ADMINISTRATIVO', 'DOC BANCARIO'), 'recorte': True,
     'busca': ('requer', 'prorroga', 'protocolo', 'assunto')},

    {'slug': 'negativa-banco', 'rotulo': 'Negativa / resposta do banco',
     'termos': ('negativa', 'resposta do banco', 'indeferimento', 'carta do banco',
                'recusa', 'improcedente'),
     'subpastas': ('DOC ADMINISTRATIVO', 'DOC BANCARIO'), 'recorte': True,
     'busca': ('indefer', 'nao e possivel', 'resposta')},

    {'slug': 'decreto-emergencia', 'rotulo': 'Decreto de emergência / calamidade',
     'termos': ('decreto', 'emergencia', 'calamidade', 'portaria', 'situacao de emergencia'),
     'subpastas': ('DOC ADMINISTRATIVO', 'DOC RURAL'), 'recorte': True,
     'busca': ('decreta', 'emergencia', 'calamidade', 'art. 1')},

    {'slug': 'laudo-agronomico', 'rotulo': 'Laudo/projeto técnico e assistência técnica (ATER)',
     'termos': ('laudo', 'relatorio tecnico', 'parecer tecnico', 'agronomo', 'agronomico',
                'ater', 'assistencia tecnica', 'projeto tecnico', 'vistoria', 'veterinario'),
     'subpastas': ('DOC RURAL', 'DOC ADMINISTRATIVO'), 'recorte': True,
     'busca': ('conclusao', 'vistoria', 'perda', 'produtividade')},

    {'slug': 'clima', 'rotulo': 'Boletim climático / dados de chuva (INMET, Embrapa, SIPAM)',
     'termos': ('inmet', 'boletim', 'climatico', 'clima', 'chuva', 'estiagem', 'seca',
                'precipitacao', 'embrapa', 'sipam', 'meteorolog'),
     'subpastas': ('DOC RURAL',), 'recorte': True,
     'busca': ('precipitacao', 'mm', 'media', 'periodo')},

    {'slug': 'cotacao', 'rotulo': 'Cotação de commodity / arroba do boi',
     'termos': ('cotacao', 'arroba', 'indicador', 'cepea', 'preco do boi', 'mercado',
                'scot', 'boi gordo'),
     'subpastas': ('DOC RURAL',), 'recorte': True,
     'busca': ('arroba', 'indicador', 'r$')},

    {'slug': 'imovel-rural', 'rotulo': 'Matrícula / CAR / ITR / CCIR / arrendamento',
     'termos': ('matricula', 'car', 'cadastro ambiental', 'itr', 'ccir', 'incra',
                'arrendamento', 'escritura', 'imovel rural', 'georreferenciamento',
                'certidao de imovel'),
     'subpastas': ('DOC RURAL',), 'recorte': True,
     'busca': ('matricula', 'area', 'imovel')},

    {'slug': 'producao', 'rotulo': 'Notas fiscais / GTA / comprovantes de produção',
     'termos': ('nota fiscal', 'notas fiscais', 'nfe', 'gta', 'guia de transito',
                'produtor rural', 'talao', 'romaneio', 'venda de gado', 'rebanho'),
     'subpastas': ('DOC RURAL',), 'recorte': True, 'busca': ('valor', 'quantidade')},

    {'slug': 'dap-caf', 'rotulo': 'DAP / CAF (enquadramento Pronaf)',
     'termos': ('dap', 'caf', 'declaracao de aptidao', 'pronaf'),
     'subpastas': ('DOC RURAL',), 'recorte': False, 'busca': ()},

    {'slug': 'processo', 'rotulo': 'Execução / busca e apreensão em curso',
     'termos': ('execucao', 'busca e apreensao', 'citacao', 'mandado', 'penhora',
                'leilao', 'monitoria', 'autos'),
     'subpastas': ('DOC ADMINISTRATIVO',), 'recorte': True,
     'busca': ('vistos', 'decido', 'cite-se', 'valor da causa')},
)

_POR_SLUG = {t['slug']: t for t in TIPOS_DOCUMENTO}


# ============================================================
# ROL DE DOCUMENTOS POR TESE
# ============================================================
# Default do escritorio, a confirmar caso a caso com a Dra. Juliana - o modulo
# nunca escolhe a tese sozinho (e' o erro mais recorrente segundo o POP).

ACOES = {
    'alongamento': {
        'rotulo': 'Prorrogação/alongamento compulsório de crédito rural (MCR 2.6.4 + Súmula 298/STJ)',
        'obrigatorios': ('procuracao', 'doc-pessoal', 'comprovante-residencia', 'cedula',
                         'requerimento-banco', 'decreto-emergencia'),
        'recomendados': ('imovel-rural', 'producao', 'laudo-agronomico', 'clima', 'cotacao',
                         'ficha-grafica', 'negativa-banco', 'negativacao', 'hipossuficiencia',
                         'processo'),
        'recortes': ('requerimento-banco', 'negativa-banco', 'decreto-emergencia', 'cotacao',
                     'clima', 'laudo-agronomico'),
    },
    'mora': {
        'rotulo': 'Declaratória de descaracterização de mora (Tema 28/STJ)',
        'obrigatorios': ('procuracao', 'doc-pessoal', 'cedula', 'ficha-grafica'),
        'recomendados': ('comprovante-residencia', 'aditivo', 'negativacao', 'processo',
                         'hipossuficiencia'),
        'recortes': ('cedula', 'ficha-grafica', 'negativacao'),
    },
    'mora-assistencia': {
        'rotulo': 'Descaracterização de mora c/c falha na assistência técnica (Justiça Federal)',
        'obrigatorios': ('procuracao', 'doc-pessoal', 'cedula', 'ficha-grafica',
                         'laudo-agronomico'),
        'recomendados': ('dap-caf', 'decreto-emergencia', 'producao', 'imovel-rural',
                         'negativacao', 'processo', 'hipossuficiencia',
                         'comprovante-residencia'),
        'recortes': ('cedula', 'ficha-grafica', 'laudo-agronomico', 'decreto-emergencia'),
    },
    'revisional': {
        'rotulo': 'Revisional de contrato bancário rural c/c tutela de urgência',
        'obrigatorios': ('procuracao', 'doc-pessoal', 'cedula', 'ficha-grafica',
                         'hipossuficiencia'),
        'recomendados': ('aditivo', 'banco-movimentacao', 'imovel-rural', 'producao',
                         'negativacao', 'processo', 'comprovante-residencia'),
        'recortes': ('cedula', 'ficha-grafica', 'banco-movimentacao'),
    },
}


# ============================================================
# PLACEHOLDERS DO MODELO DE INICIAL
# ============================================================
# Marcadores literais que os modelos reais do escritorio trazem. Ver
# BASE_CONHECIMENTO/05 - FORMATACAO/Modelo-Mandamental-Prorrogacao.md e
# Modelo-Revisional.md.

_PADROES_IMAGEM = (
    re.compile(r'INSERIR\s+(UMA?\s+)?(IMAGEM|FOTO|PRINT|RECORTE|GR[ÁA]FICO|TABELA)', re.I),
    # 'INCLUA AQUI A PRINT' e' o marcador do modelo de declaratoria de mora.
    re.compile(r'INCLU(A|IR)\s+(AQUI\s+)?(UMA?\s+|[AO]\s+)?'
               r'(IMAGEM|FOTO|PRINT|RECORTE|GR[ÁA]FICO|TABELA)', re.I),
    re.compile(r'\b(IMAGEM|PRINT|RECORTE|FOTO|GR[ÁA]FICO)\s+D[OEA]\b', re.I),
    re.compile(r'\b(ANEXAR|COLAR|COLOCAR)\s+(A\s+|O\s+)?(IMAGEM|PRINT|RECORTE|DOCUMENTO)', re.I),
    re.compile(r'\[\s*(INSERIR|IMAGEM|PRINT|RECORTE|DOC)\b[^\]]*\]', re.I),
    re.compile(r'\{\{[^}]+\}\}'),
    re.compile(r'<<[^>]+>>'),
)

# Campo de texto a preencher (qualificacao, numero de contrato): nao e' imagem,
# mas tambem nao pode ir pro protocolo em branco - por isso entra no relatorio.
_PADRAO_TEXTO = re.compile(r'_{4,}')

# Palavra no texto do placeholder -> tipo de documento que provavelmente o preenche.
_PISTAS_PLACEHOLDER = (
    ('requerimento', 'requerimento-banco'), ('protocolo', 'requerimento-banco'),
    ('negativa', 'negativa-banco'), ('resposta do banco', 'negativa-banco'),
    ('arroba', 'cotacao'), ('boi', 'cotacao'), ('cotacao', 'cotacao'), ('preco', 'cotacao'),
    ('chuva', 'clima'), ('clima', 'clima'), ('estiagem', 'clima'), ('seca', 'clima'),
    ('decreto', 'decreto-emergencia'), ('emergencia', 'decreto-emergencia'),
    ('calamidade', 'decreto-emergencia'),
    ('ficha', 'ficha-grafica'), ('evolucao', 'ficha-grafica'), ('saldo', 'ficha-grafica'),
    ('demonstrativo', 'ficha-grafica'), ('planilha', 'ficha-grafica'),
    ('clausula', 'cedula'), ('capitalizacao', 'cedula'), ('juros', 'cedula'),
    ('cedula', 'cedula'), ('contrato', 'cedula'), ('taxa', 'cedula'),
    ('laudo', 'laudo-agronomico'), ('tecnic', 'laudo-agronomico'),
    ('serasa', 'negativacao'), ('spc', 'negativacao'), ('negativacao', 'negativacao'),
    ('matricula', 'imovel-rural'), ('car', 'imovel-rural'),
    ('nota fiscal', 'producao'), ('gta', 'producao'),
    ('extrato', 'banco-movimentacao'), ('movimenta', 'banco-movimentacao'),
)


# ============================================================
# NORMALIZACAO E CLASSIFICACAO
# ============================================================

def _normalizar(texto: str) -> str:
    """Minusculo, sem acento, com separadores virando espaco."""
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', texto).strip()


def _casa(termo: str, alvo_normalizado: str) -> bool:
    """Termo curto (<=4) so casa como palavra inteira: 'car' nao pode casar 'carta'."""
    termo = _normalizar(termo)
    if not termo:
        return False
    if len(termo) <= 4:
        return re.search(r'\b' + re.escape(termo) + r'\b', alvo_normalizado) is not None
    return termo in alvo_normalizado


def classificar_arquivo(nome: str, subpasta: str = ''):
    """Devolve [(slug, pontuacao)] ordenado, do mais provavel pro menos.

    Heuristica pura de nome de arquivo + subpasta: e' um palpite, nao um laudo.
    Arquivo que nao casa com nada volta [] e sobe no relatorio como
    'nao classificado', pra conferencia humana.
    """
    alvo = _normalizar(nome)
    sub = _normalizar(subpasta)
    achados = []
    for tipo in TIPOS_DOCUMENTO:
        pontos = sum(2 for t in tipo['termos'] if _casa(t, alvo))
        if not pontos:
            continue
        if any(_normalizar(s) in sub for s in tipo['subpastas']):
            pontos += 1
        achados.append((tipo['slug'], pontos))
    return sorted(achados, key=lambda x: -x[1])


def rotulo(slug: str) -> str:
    tipo = _POR_SLUG.get(slug)
    return tipo['rotulo'] if tipo else slug


def eh_recortavel(slug: str) -> bool:
    tipo = _POR_SLUG.get(slug)
    return bool(tipo and tipo['recorte'])


def termos_de_busca(slug: str):
    tipo = _POR_SLUG.get(slug)
    return tuple(tipo['busca']) if tipo else ()


# ============================================================
# 1. INVENTARIO DA PASTA DO CLIENTE (Drive)
# ============================================================

def inventariar_cliente(g, drive_service, nome_cliente: str, profundidade: int = 3):
    """Varre a pasta do cliente na ZEUS e classifica tudo que encontrar.

    `g` e' o modulo INTEGRACOES/google_integration (injetado pra manter a regra do
    projeto: acesso ao Drive so por aquele modulo, e import tardio no CLI).
    Retorna (pasta_do_cliente, [arquivos]). Somente leitura.
    """
    pasta = g.pasta_do_cliente(drive_service, nome_cliente)
    if not pasta:
        return None, []

    arquivos = []

    def _varrer(pasta_id, caminho, nivel):
        for item in g.listar_pasta(drive_service, pasta_id):
            if item['mimeType'] == g.MIME_PASTA:
                if nivel < profundidade:
                    _varrer(item['id'], caminho + [item['name']], nivel + 1)
                continue
            subpasta = ' / '.join(caminho)
            tipos = classificar_arquivo(item['name'], subpasta)
            arquivos.append({
                'id': item['id'],
                'nome': item['name'],
                'mime': item['mimeType'],
                'subpasta': subpasta,
                'modificado': item.get('modifiedTime', ''),
                'link': item.get('webViewLink', ''),
                'tipos': [slug for slug, _ in tipos],
                'tipo': tipos[0][0] if tipos else None,
            })

    _varrer(pasta['id'], [], 1)
    arquivos.sort(key=lambda a: (a['tipo'] or 'zzz', _normalizar(a['nome'])))
    return pasta, arquivos


def conferir_rol(arquivos, acao: str):
    """Cruza o inventario com o rol da tese. Retorna dict com o que tem e o que falta."""
    if acao not in ACOES:
        raise ValueError(f"Acao desconhecida: {acao}. Use uma de: {', '.join(sorted(ACOES))}")

    perfil = ACOES[acao]
    por_tipo = {}
    for arq in arquivos:
        for slug in arq['tipos']:
            por_tipo.setdefault(slug, []).append(arq)

    return {
        'acao': acao,
        'rotulo': perfil['rotulo'],
        'obrigatorios': [(s, por_tipo.get(s, [])) for s in perfil['obrigatorios']],
        'recomendados': [(s, por_tipo.get(s, [])) for s in perfil['recomendados']],
        'recortes': [(s, por_tipo.get(s, [])) for s in perfil['recortes']],
        'faltando': [s for s in perfil['obrigatorios'] if not por_tipo.get(s)],
        'faltando_recomendados': [s for s in perfil['recomendados'] if not por_tipo.get(s)],
        'nao_classificados': [a for a in arquivos if not a['tipos']],
        'por_tipo': por_tipo,
    }


def baixar_documentos(g, drive_service, arquivos, destino: str):
    """Baixa os arquivos escolhidos pro diretorio de trabalho local. Somente leitura no Drive."""
    os.makedirs(destino, exist_ok=True)
    baixados = []
    for arq in arquivos:
        try:
            caminho = g.baixar_arquivo(drive_service, arq['id'], destino)
            baixados.append(dict(arq, caminho=caminho))
        except Exception as erro:                      # noqa: BLE001 - o relatorio segue
            baixados.append(dict(arq, caminho=None, erro=str(erro)))
    return baixados


# ============================================================
# 2. RECORTE (PDF/imagem -> PNG)
# ============================================================

_MSG_PYMUPDF = ('PyMuPDF nao instalado - sem ele nao da pra recortar PDF.\n'
                '  Instale com:  pip install pymupdf   (ja consta em requirements.txt)')


def _fitz():
    try:
        import fitz
    except ImportError:
        raise RuntimeError(_MSG_PYMUPDF)
    return fitz


def paginas_com(caminho_pdf: str, termos, limite: int = 20):
    """Onde, no PDF, aparece cada termo. Retorna [(pagina_1based, termo, n_ocorrencias)].

    E' o que evita recortar a pagina errada: antes de renderizar, confira aqui em
    que pagina esta a clausula de capitalizacao / a linha da ficha grafica.
    """
    fitz = _fitz()
    achados = []
    with fitz.open(caminho_pdf) as pdf:
        for n, pagina in enumerate(pdf, start=1):
            for termo in termos:
                ocorrencias = pagina.search_for(termo)
                if ocorrencias:
                    achados.append((n, termo, len(ocorrencias)))
            if len(achados) >= limite:
                break
    return achados


def recortar(caminho, saida, pagina: int = None, buscar=None, dpi: int = 200,
             margem_cm: float = 1.0, pagina_inteira: bool = False,
             realcar=None, largura_total: bool = False):
    """Gera o PNG que vai entrar na peca. Retorna (caminho_saida, descricao).

    - `buscar`: recorta so a regiao ao redor do termo (com margem), que e' o
      'recorte' de clausula que o escritorio usa. Sem termo (ou com
      --pagina-inteira), renderiza a pagina toda.
    - `realcar`: grifa em amarelo, na propria imagem, os termos indicados. Grifo
      em prova so' e' legitimo quando DECLARADO - a legenda tem que trazer
      "grifo nosso", que e' a praxe forense. Sem essa declaracao, o grifo passa
      por parte do documento original e ai' vira adulteracao. O PDF de origem
      NAO e' alterado: o grifo vive so' no render em memoria.
    - `largura_total`: mantem a largura da pagina e recorta so' na vertical.
      Recorte que corta a margem direita mutila o texto no meio da linha - foi
      o que aconteceu na primeira montagem de uma peca real.
    - Arquivo que ja e' imagem (JPG/PNG) e' copiado como esta: recorte de foto
      teria que ser feito a olho, e cortar sem ver o conteudo altera prova.
    """
    ext = os.path.splitext(caminho)[1].lower()
    os.makedirs(os.path.dirname(os.path.abspath(saida)) or '.', exist_ok=True)

    if ext in ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp'):
        shutil.copyfile(caminho, saida)
        return saida, 'imagem copiada sem recorte (origem ja e imagem)'

    if ext != '.pdf':
        raise RuntimeError(
            f'Nao sei recortar "{ext}". Converta para PDF antes '
            '(no Drive: abrir > imprimir > salvar como PDF).')

    fitz = _fitz()
    with fitz.open(caminho) as pdf:
        if pagina is None and buscar:
            pagina = _primeira_pagina_com(pdf, buscar)
        if pagina is None:
            pagina = 1
        if not 1 <= pagina <= pdf.page_count:
            raise RuntimeError(f'O PDF tem {pdf.page_count} pagina(s); pedida a {pagina}.')

        alvo = pdf[pagina - 1]
        recorte = None
        if buscar and not pagina_inteira:
            recorte = _regiao_dos_termos(alvo, buscar, margem_cm,
                                         largura_total=largura_total)

        grifados = _grifar(alvo, realcar) if realcar else 0

        pix = alvo.get_pixmap(dpi=dpi, clip=recorte)
        pix.save(saida)

    if recorte:
        desc = f'pagina {pagina}, regiao do termo (recorte {int(recorte.width)}x{int(recorte.height)} pt)'
    else:
        desc = f'pagina {pagina} inteira'
    if realcar:
        desc += f'; {grifados} trecho(s) grifado(s) — a legenda TEM de dizer "grifo nosso"'
    return saida, desc


def _grifar(pagina, termos):
    """Grifa em amarelo os termos na pagina renderizada. Devolve quantos grifou.

    Usa a anotacao de realce do proprio PDF, que e' o mesmo grifo do leitor de
    PDF - o texto continua legivel por baixo, ao contrario de tarja. O arquivo
    de origem nao e' salvo em momento algum: o grifo existe so' no objeto em
    memoria que gera o PNG.
    """
    total = 0
    for termo in termos:
        for caixa in pagina.search_for(termo):
            anotacao = pagina.add_highlight_annot(caixa)
            anotacao.set_colors(stroke=(1, 0.92, 0.23))
            anotacao.update()
            total += 1
    return total


def _primeira_pagina_com(pdf, termos):
    for n, pagina in enumerate(pdf, start=1):
        for termo in termos:
            if pagina.search_for(termo):
                return n
    return None


def _regiao_dos_termos(pagina, termos, margem_cm: float, largura_total: bool = False):
    """Retangulo que cobre todas as ocorrencias dos termos na pagina, com folga.

    A folga existe pra clausula nao sair decapitada: um recorte colado na linha
    tira o contexto e enfraquece a prova.
    """
    fitz = _fitz()
    caixas = []
    for termo in termos:
        caixas.extend(pagina.search_for(termo))
    if not caixas:
        return None

    margem = margem_cm * 28.35                          # cm -> pontos
    x0 = min(c.x0 for c in caixas) - margem
    y0 = min(c.y0 for c in caixas) - margem
    x1 = max(c.x1 for c in caixas) + margem
    y1 = max(c.y1 for c in caixas) + margem
    limite = pagina.rect
    if largura_total:
        x0, x1 = limite.x0, limite.x1
    return fitz.Rect(max(x0, limite.x0), max(y0, limite.y0),
                     min(x1, limite.x1), min(y1, limite.y1))


# ============================================================
# 3. PLACEHOLDERS DA PECA (.docx)
# ============================================================

def _paragrafos(doc):
    """Todos os paragrafos da peca, inclusive os de dentro de tabela.

    O modelo de revisional tem 3 tabelas e o de alongamento 21 - marcador dentro
    de celula e' comum (a tabela 'Descricao | Valor | Documento Comprobatorio').
    """
    itens = [(i, p, None) for i, p in enumerate(doc.paragraphs)]
    for t, tabela in enumerate(doc.tables):
        for l, linha in enumerate(tabela.rows):
            for c, celula in enumerate(linha.cells):
                for p in celula.paragraphs:
                    itens.append((None, p, f'tabela {t + 1} [{l + 1},{c + 1}]'))
    return itens


def _pista_de_tipo(texto: str):
    alvo = _normalizar(texto)
    for pista, slug in _PISTAS_PLACEHOLDER:
        if _normalizar(pista) in alvo:
            return slug
    return None


def localizar_placeholders(caminho_docx: str):
    """Lista os marcadores a preencher na peca/modelo.

    Retorna [{'n', 'tipo', 'texto', 'contexto', 'onde', 'sugestao'}] - 'tipo' e'
    'imagem' (entra recorte) ou 'texto' (campo de qualificacao em branco).

    'contexto' e' a frase imediatamente anterior, e nao e' enfeite: marcador como
    'INSERIR UMA IMAGEM.' nao diz nada sozinho - quem diz qual documento entra ali
    e' a frase que o antecede ('conforme a clausula de capitalizacao da cedula:').
    A sugestao de tipo sai do marcador e, se ele for mudo, do contexto.

    O quadro de instrucoes do modelo (o que comeca com "APAGUE ESTE QUADRO") e'
    ignorado: ele cita os marcadores justamente para explicar a regra, e sai da
    peca antes da entrega. Mesma excecao que `visual_law.varrer_lexico_embargos`.
    """
    from docx import Document

    doc = Document(caminho_docx)
    itens = _paragrafos(doc)
    achados = []
    anterior = ''
    for posicao, (indice, paragrafo, onde) in enumerate(itens):
        texto = (paragrafo.text or '').strip()
        if not texto:
            continue
        local = onde or f'paragrafo {indice + 1}'
        # O rotulo esta na 1a celula do quadro e o texto das instrucoes na 2a,
        # entao a frase pode estar no proprio paragrafo ou no anterior.
        if 'APAGUE ESTE QUADRO' in (texto + ' ' + anterior).upper():
            anterior = texto
            continue
        if any(p.search(texto) for p in _PADROES_IMAGEM):
            achados.append({'n': len(achados) + 1, 'tipo': 'imagem', 'texto': texto,
                            'contexto': anterior, 'onde': local,
                            'sugestao': _pista_de_tipo(texto) or _pista_de_tipo(anterior)})
        elif _PADRAO_TEXTO.search(texto):
            achados.append({'n': len(achados) + 1, 'tipo': 'texto', 'texto': texto,
                            'contexto': anterior, 'onde': local, 'sugestao': None})
        anterior = texto
    return achados


def _achar_paragrafo(doc, marcador: str):
    """Localiza o paragrafo do marcador (comparacao normalizada, como no resto do projeto).

    Erra alto de proposito: marcador ambiguo levanta excecao em vez de escolher
    um dos dois e colar a imagem no lugar errado.
    """
    alvo = _normalizar(marcador)
    if not alvo:
        raise ValueError('Marcador vazio.')

    candidatos = [p for _, p, _ in _paragrafos(doc) if alvo in _normalizar(p.text or '')]
    if not candidatos:
        raise LookupError(f'Marcador nao encontrado na peca: "{marcador}"')
    if len(candidatos) > 1:
        exatos = [p for p in candidatos if _normalizar(p.text or '') == alvo]
        if len(exatos) != 1:
            raise LookupError(
                f'Marcador "{marcador}" aparece {len(candidatos)} vezes na peca. '
                'Use um trecho maior, que identifique so um deles.')
        candidatos = exatos
    return candidatos[0]


def _limpar(paragrafo):
    for run in list(paragrafo.runs):
        run._element.getparent().remove(run._element)
    return paragrafo


def _paragrafo_depois(paragrafo):
    """Cria um paragrafo vazio logo apos, herdando a formatacao (pPr) do modelo."""
    from docx.text.paragraph import Paragraph

    novo = deepcopy(paragrafo._p)
    paragrafo._p.addnext(novo)
    return _limpar(Paragraph(novo, paragrafo._parent))


def _largura_util(doc):
    from docx.shared import Cm

    secao = doc.sections[0]
    if secao.page_width and secao.left_margin is not None:
        return secao.page_width - secao.left_margin - secao.right_margin
    return Cm(16.0)


def _altura_util(doc):
    from docx.shared import Cm, Emu

    secao = doc.sections[0]
    if secao.page_height and secao.top_margin is not None:
        # 0.75 da mancha: recorte que ocupa a pagina inteira empurra o texto e
        # quebra a leitura da peca.
        return Emu(int((secao.page_height - secao.top_margin - secao.bottom_margin) * 0.75))
    return Cm(15.0)


def _contornar(inline_shape, cor: str = '7f7f7f', largura_pt: float = 0.75):
    """Poe borda fina no recorte inserido.

    Regra da Dra. Juliana (10/09/2026). Documento colado sem moldura se confunde
    com o corpo da peca: o juiz nao distingue, de relance, o que e' transcricao
    nossa do que e' reproducao do documento do banco. A borda e' o unico
    tratamento que o recorte admite - ela emoldura a prova sem tocar nela, ao
    contrario de realce ou grifo, que a editam (ver skill `inicial-anexos`).
    """
    from docx.oxml import OxmlElement

    spPr = inline_shape._inline.graphic.graphicData.pic.spPr
    for antigo in spPr.findall(qn('a:ln')):
        spPr.remove(antigo)
    ln = OxmlElement('a:ln')
    ln.set('w', str(int(largura_pt * 12700)))   # EMU por ponto
    preenchimento = OxmlElement('a:solidFill')
    rgb = OxmlElement('a:srgbClr')
    rgb.set('val', cor.upper())
    preenchimento.append(rgb)
    ln.append(preenchimento)
    spPr.append(ln)
    return inline_shape


def inserir_recorte(caminho_docx: str, marcador: str, imagem: str, legenda: str = None,
                    saida: str = None, largura_cm: float = None):
    """Troca o placeholder pelo recorte + legenda. Retorna o caminho salvo.

    A imagem entra centralizada, limitada a mancha da pagina (nunca estourando a
    margem do timbrado), e a legenda vai ACIMA dela, em 10 pt italico, presa a
    imagem (keep_with_next) - pedido do Dr. Mailson (14/09/2026): o leitor sabe o
    que vai ver antes de ver, e a referencia nao fica orfã no pe da pagina.
    """
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Emu, Pt

    if not os.path.exists(imagem):
        raise FileNotFoundError(f'Recorte nao encontrado: {imagem}')

    doc = Document(caminho_docx)
    paragrafo = _achar_paragrafo(doc, marcador)
    original = (paragrafo.text or '').strip()

    legenda_par = paragrafo.insert_paragraph_before() if legenda else None

    _limpar(paragrafo)
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    largura = Cm(largura_cm) if largura_cm else _largura_util(doc)
    # Marcador dentro de quadro (visual_law.bloco_prova): a imagem cabe na
    # célula, com folga para a margem interna — com a largura da página ela
    # estouraria a moldura da prova.
    from docx.table import _Cell
    if not largura_cm and isinstance(paragrafo._parent, _Cell) and paragrafo._parent.width:
        largura = Emu(min(int(largura), int(paragrafo._parent.width) - int(Cm(0.5))))
    paragrafo.add_run().add_picture(imagem, width=largura)

    forma = doc.inline_shapes[-1]
    maxima = _altura_util(doc)
    if forma.height > maxima:
        proporcao = maxima / forma.height
        forma.height = Emu(int(forma.height * proporcao))
        forma.width = Emu(int(forma.width * proporcao))

    _contornar(forma)

    if legenda_par is not None:
        legenda_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        legenda_par.paragraph_format.keep_with_next = True
        run = legenda_par.add_run(legenda)
        run.italic = True
        run.font.size = Pt(10)

    saida = saida or caminho_docx
    doc.save(saida)
    return saida, original


def marcar_pendencia(caminho_docx: str, marcador: str, texto: str = None, saida: str = None):
    """Documento que nao existe na pasta do cliente: pendencia em amarelo, nunca suposicao.

    Mesmo guard-rail da skill `timbrado` - o que depende de documento nao lido
    sai destacado, para a Dra. Juliana resolver antes do protocolo.
    """
    from docx import Document
    from docx.enum.text import WD_COLOR_INDEX

    doc = Document(caminho_docx)
    paragrafo = _achar_paragrafo(doc, marcador)
    original = (paragrafo.text or '').strip()

    aviso = texto or f'[PENDENTE] {original} — documento não localizado na pasta do cliente'
    _limpar(paragrafo)
    run = paragrafo.add_run(aviso)
    run.bold = True
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW

    saida = saida or caminho_docx
    doc.save(saida)
    return saida, original


def rol_de_documentos(itens):
    """Numera os anexos no padrao da peca: [(1, 'Doc. 01 - rotulo (arquivo)'), ...].

    `itens` = [(slug, nome_do_arquivo)] na ordem em que devem aparecer.
    A numeracao e' a mesma que a legenda do recorte cita no corpo, senao o juiz
    procura o 'doc. 03' e acha outra coisa.
    """
    linhas = []
    for n, (slug, nome) in enumerate(itens, start=1):
        linhas.append((n, f'Doc. {n:02d} — {rotulo(slug)} ({nome})'))
    return linhas


def legenda_padrao(numero: int, slug: str, descricao: str = None, pagina: int = None):
    """Legenda do recorte: "Imagem NN. documento, fl. X".

    A imagem e' numerada em sequencia na peca (Imagem 01, 02...), e nao pelo numero
    do anexo no PJe, que so existe depois do upload: com "Doc. [[nº]]" o advogado
    tinha de substituir cada referencia a mao (Dra. Juliana, 15/09/2026). O
    documento e a folha continuam na legenda, e sao eles que localizam a prova.
    """
    partes = [f'Imagem {numero:02d}. {descricao or rotulo(slug)}']
    if pagina:
        partes.append(f'fl. {pagina}')
    return ', '.join(partes)
