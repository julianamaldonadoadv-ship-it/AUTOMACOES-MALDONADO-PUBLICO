"""
=============================================================================
  APONTAMENTOS DA GERENCIA JURIDICA - Maldonado Advogados
=============================================================================

  A Dra. Juliana recebe, na tag CONFERIR/REVISAR PETICAO do ADVBOX, as pecas
  que os advogados submetem antes do protocolo, e devolve cada uma com os
  apontamentos de melhoria. Sao ~200 devolutivas por mes. Este modulo levanta
  esses apontamentos e os transforma em base de dados: o que a Gerencia
  Juridica mais corrige, por familia de erro, por mes e por advogado.

  O que sai daqui alimenta tres coisas (decisao da Dra. Juliana, 10/09/2026):
    1. o CHECKLIST DE AUTORREVISAO que o advogado roda ANTES de mandar a peca;
    2. as regras que o agente de divida rural ja aplica ao produzir a minuta;
    3. o relatorio por advogado, para feedback dirigido.

  ---------------------------------------------------------------------------
  COMO A AUTORIA E DESCOBERTA (e por que nao ha caminho mais curto)
  ---------------------------------------------------------------------------
  GET /posts devolve o texto da tarefa (campo 'notes') mas NAO devolve quem a
  escreveu - so os convidados. Numa tarefa CONFERIR/REVISAR PETICAO o texto e'
  do ADVOGADO submetendo a peca ("Submeto a analise da Gerencia Juridica..."),
  nunca da Dra. Juliana: das 238 tarefas dessa tag cuja autoria foi possivel
  conferir, ZERO foram escritas por ela.

  O unico endpoint que devolve o campo 'author' e' GET /history/{lawsuit_id}.
  E' por ele que se descobre o que a Gerencia Juridica escreveu - e a devolutiva
  aparece em varias tags (COMENTARIO, AGENDAMENTO, PECA ENVIADA PARA AJUSTES,
  PECA APROVADA PARA PROTOCOLO, ANALISE - NIVEL 01, PRESTAR ESCLARECIMENTOS),
  porque ela devolve tanto como comentario quanto como tarefa nova.

  LIMITE CONHECIDO DA API: /history devolve no maximo ~20 itens por processo e
  NAO pagina (limit, offset, page, skip, start, per_page, date_start - todos
  ignorados, conferido em 10/09/2026). Em processo muito movimentado, os itens
  mais antigos ficam fora do alcance. Por isso o relatorio sempre imprime a
  cobertura por mes: e' subcontagem, nunca "nao houve apontamento".

  Regra de ouro do projeto: SOMENTE LEITURA. Nenhum POST, nenhuma tarefa criada.
=============================================================================
"""
import os
import re
import csv
import sys
import time
import unicodedata
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))

from INTEGRACOES import advbox_integration as advbox

try:
    from equipe import USUARIOS_ADVBOX, CONTROLLERS
except ImportError:  # pragma: no cover - config sempre existe em producao
    USUARIOS_ADVBOX, CONTROLLERS = {}, {}


# ID da tag que o escritorio usa para submeter peca a Gerencia Juridica.
TAG_REVISAO = '2596525'          # CONFERIR/REVISAR PETICAO
TAG_AJUSTES = '8690258'          # PECA ENVIADA PARA AJUSTES
TAG_APROVADA = '8720914'         # PECA APROVADA PARA PROTOCOLO

# Tags em que a devolutiva da Gerencia Juridica aparece de fato (levantado no
# historico real de jun-ago/2026). Nao restringir a "PECA ENVIADA PARA AJUSTES":
# so 20 devolutivas em 3 meses usaram essa tag - a maioria sai como COMENTARIO.
TAGS_DEVOLUTIVA = (
    'COMENTÁRIO', 'AGENDAMENTO', 'PEÇA ENVIADA PARA AJUSTES',
    'PEÇA APROVADA PARA PROTOCOLO', 'ANÁLISE - NÍVEL 01',
    'PRESTAR ESCLARECIMENTOS', 'EMISSÃO DE PARECER', 'AGENDAR DESPACHO',
    'PARECER JURÍDICO', 'MANIFESTAÇÃO',
)

# Abaixo disso o texto e' recado operacional ("Ciente.", "Segue o devido."),
# nao apontamento tecnico.
MIN_CARACTERES = 150


def _sem_acento(texto):
    nfd = unicodedata.normalize('NFD', str(texto or ''))
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').upper()


# ============================================================
# TAXONOMIA DOS APONTAMENTOS
# ============================================================
# Derivada da LEITURA das 125 devolutivas reais de jun-ago/2026 - nao e' uma
# lista teorica de erros de peticao. Cada gatilho saiu de um texto que a
# Gerencia Juridica escreveu de fato.
#
# A classificacao e' HEURISTICA DE PALAVRA-CHAVE: palpite, nao laudo. O que nao
# casa com nada sobe como "revisar manualmente" - e' ai que costuma estar o
# apontamento com redacao nova, que merece virar categoria.

CATEGORIAS = (
    # ---------------------------------------------------- tese e enquadramento
    ('TESE E ENQUADRAMENTO', 'Contradicao interna: moldura da acao x pedido',
     ('NAO E REVISIONAL', 'NAO SE PEDE RECALCULO', 'CONTRADICAO SOBRE A NATUREZA',
      'CONTRADICAO ENTRE A MOLDURA', 'CONTRADICAO INTERNA', 'CONTRADIZ', 'INCONSISTENCIA ENTRE')),
    ('TESE E ENQUADRAMENTO', 'Via/natureza da acao trocada ou confundida',
     ('EMBARGOS A EXECUCAO, NAO', 'ACAO DECLARATORIA AUTONOMA', 'CONFUSAO ENTRE CEDULA',
      'NATUREZA RURAL DA CEDULA', 'CONFUSAO ENTRE O OBJETO DA ACAO',
      'VOCABULARIO E REQUISITOS DE ALONGAMENTO', 'NOMEN JURIS')),
    ('TESE E ENQUADRAMENTO', 'Tese principal mal hierarquizada (evidencia x urgencia, principal x subsidiario)',
     ('TUTELA DE EVIDENCIA COMO TESE PRINCIPAL', 'TESE PRINCIPAL', 'PEDIDO PRINCIPAL E AUTONOMO',
      'COMO PEDIDO PRINCIPAL', 'SUBSIDIARIAMENTE', 'PEDIDO SUBSIDIARIO', 'HIERARQUIZAR',
      'ORDEM DE PRIORIDADE', 'TUTELA DE EVIDENCIA', 'DISPENSA PERICULUM',
      'DISPENSAR A COMPROVACAO DO PERIGO')),
    ('TESE E ENQUADRAMENTO', 'Tese nao resiste a premissa contraria (nao lidera pelo argumento mais forte)',
     ('MESMO QUE A CAMARA ACEITE', 'AINDA QUE SE COMPROVE', 'NAO FUNCIONA SE', 'PRECISA LIDERAR',
      'ARGUMENTO MAIS FORTE DISPONIVEL', 'DESNECESSARIAMENTE DEFENSIVO', 'O EFEITO E O OPOSTO')),
    ('TESE E ENQUADRAMENTO', 'Tese/argumento adicional cabivel nao explorado',
     ('NAO USA ESSE FATO', 'A PECA NAO USA', 'MUNICAO DIRETA', 'PONTO DE ADICAO', 'PARA ADICAO',
      'SUGIRO UM PARAGRAFO', 'ADICIONAR:', 'EXPLORAR', 'APROFUNDAR', 'REFORCAR O ARGUMENTO',
      'LINHA DE ATUACAO', 'CERCEAMENTO DE DEFESA', 'POLITICA JUDICIARIA', 'REFORCAR A SECAO',
      'CLASSIFICAR O RECURSO', 'TETO DE 12', 'REFUTACAO DA TESE', 'DECISAO-SURPRESA',
      'TEORIA DA IMPREVISAO', 'SILENCIO QUALIFICADO', 'NEGATIVA TACITA', 'PROVA TESTEMUNHAL',
      'OITIVA', 'EXIBICAO DE DOCUMENTOS', 'PROPAGANDA ENGANOSA', 'MENOR ONEROSIDADE')),

    # ---------------------------------------------------------- fundamentacao
    ('FUNDAMENTACAO', 'Dispositivo legal-chave ausente',
     ('ART. 341', 'ART. 373', 'ART. 370', 'ART. 356', 'ART. 805', 'ART. 830', 'ART. 317',
      'ART. 478', 'ART. 1.426', 'ART. 919', 'ART. 803', 'ART. 99', 'ART. 311', 'ART. 489',
      'ART. 927', 'ART. 190', 'ART. 272', 'ART. 357', 'ART. 783', 'ART. 784', 'ART. 313',
      'NUNCA ANCORA', 'NAO MENCIONA O ART', 'SEM ESSA BASE POSITIVADA',
      'FUNDAMENTAR EXPRESSAMENTE O PEDIDO')),
    ('FUNDAMENTACAO', 'Precedente generico em vez do paradigma',
     ('REFERENCIA GENERICA AO', 'PRECEDENTE PARADIGMA', 'SUBSTITUA A REFERENCIA',
      'TEMA REPETITIVO 28" PELA TESE', 'PRECISAR A CITACAO')),
    ('FUNDAMENTACAO', 'Precedente local/interno do escritorio nao citado',
     ('PRECEDENTE LOCAL', 'INSERIR PRECEDENTES DO TJ', 'JURISPRUDENCIA DO PROPRIO TJ',
      'PRECEDENTES DO TJRO', 'PRECEDENTES DO TRF', 'JULGADOS DO TJ', 'INCLUIR JURISPRUDENCIA',
      'BANCO DE TESES', 'PRECEDENTES INTERNOS', 'NAO CITA, EM NENHUM PONTO, A SENTENCA',
      'PRECEDENTE MAIS FORTE DISPONIVEL', 'ADICIONAR JURISPRUDENCIA', 'CITAR MAIS PRECEDENTES',
      'PESQUISAR PRECEDENTES', 'DIVERGENCIA ENTRE CAMARAS')),
    ('FUNDAMENTACAO', 'Precedente citado joga contra a propria tese',
     ('CONTRADIZ, NO MESMO TOPICO', 'SINAL DE FRAGILIDADE ARGUMENTATIVA',
      'REPOSICIONAR ESSA CITACAO', 'HOJE JOGAM CONTRA', 'SUMULA 121',
      'EXIGEM PEDIDO ANTERIOR AO VENCIMENTO', 'RETIRA-LA')),
    ('FUNDAMENTACAO', 'Falta distinguishing/alcance de precedente vinculante',
     ('DISTINGUISHING', 'DISTINCAO/SUPERACAO', 'NUNCA INDICOU QUAL PECULIARIDADE',
      'PRECISAR O ALCANCE', 'SEM ESSA DISTINCAO', 'RATIO DECIDENDI', 'SUMULA 7', 'OBICE')),
    ('FUNDAMENTACAO', 'Placeholder de jurisprudencia nao preenchido',
     ('INSERIR JUS', '(INSERIR', 'PLACEHOLDER', 'PREENCHER OS DEMAIS',
      'SEM NENHUM PRECEDENTE E SEM CONCLUSAO')),
    ('FUNDAMENTACAO', 'Peca fatica demais, fundamentacao juridica subdesenvolvida',
     ('POUCO DESENVOLVIDA NA FUNDAMENTACAO', 'FUNDAMENTACAO JURIDICA QUE DARIA SUPORTE',
      'MUITO FOCADA NOS FATOS', 'PERSUASIVO-RETORICO DO QUE DOGMATICO', 'FUNDAMENTAR NA EMENDA',
      'FUNDAMENTACAO ESPECIFICA', 'SEM FUNDAMENTACAO', 'ANALISE JURIDICA DEVIDAMENTE FUNDAMENTADA')),

    # ------------------------------------------------------ prova e documentos
    ('PROVA E DOCUMENTOS', 'Documento essencial ausente ou nao solicitado',
     ('DOCUMENTOS ESSENCIAIS', 'ACIONAR O SETOR DE DOCUMENTOS', 'SETOR DE PROVAS', 'NAO FOI JUNTAD',
      'FALTA DE PROVA DO REQUERIMENTO', 'COMPROVANTES DE PREPARO', 'JUNTAR OS COMPROVANTES',
      'DOCUMENTOS PARA ANEXAR', 'SUGESTAO DE DOCUMENTOS COMPLEMENTARES',
      'COMPROVACAO DE PROTOCOLO DO REQUERIMENTO', 'AUSENCIA DE LAUDO', 'COLETAR EXTRATO',
      'ENVIAR A CEDULA E A FICHA GRAFICA', 'INSUFICIENCIA DA PROVA DE EXPLORACAO FAMILIAR')),
    ('PROVA E DOCUMENTOS', 'Pede pericia onde a materia e documental (fecha a porta da tutela de evidencia)',
     ('NAO PEDIR PERICIA', 'SEM PERICIA', 'CONFRONTO DOCUMENTAL', 'NUNCA FUNDAMENTAMOS EM LAUDO PERICIAL',
      'FECHA A PORTA PARA TUTELA', 'COMPROVAVEL APENAS DOCUMENTALMENTE', 'SEGREGAR',
      'A PERICIA SERVE PARA QUANTIFICAR', 'ENQUADRAMENTO E INSUFICIENTE',
      'INDEPENDENTEMENTE DE QUALQUER PERICIA', 'RECONHECIMENTO DOCUMENTAL IMEDIATO',
      'JULGAMENTO IMEDIATO')),
    ('PROVA E DOCUMENTOS', 'Quesito de pericia mal direcionado',
     ('REDIRECIONAR O QUESITO', 'QUESITO DA PERICIA', 'NAO PERGUNTAR SE A CAPITALIZACAO E LEGAL EM TESE',
      'QUESITOS CONTABEIS', 'DELIMITAR O OBJETO DA PERICIA')),
    ('PROVA E DOCUMENTOS', 'Laudo/prova tecnica nao explorada ou nao blindada',
     ('HOMOLOGACAO JUDICIAL DO LAUDO', 'LAUDO TECNICO UNILATERAL', 'RATIFICACAO DO LAUDO',
      'TESTEMUNHA TECNICA', 'BILATERALIZAR', 'CONTRALAUDO', 'NAO IMPUGNOU TECNICAMENTE',
      'VALIDADE DO LAUDO', 'LAUDO APOCRIFO', 'LAUDO NAO IMPUGNADO', 'BLINDA-LA')),
    ('PROVA E DOCUMENTOS', 'Fatos incontroversos / onus da prova nao trabalhados',
     ('FATOS INCONTROVERSOS', 'INCONTROVERS', 'ONUS DA PROVA', 'COLUNA DE ONUS', 'COLUNA "ONUS',
      'IMPUGNACAO ESPECIFICA', 'PRESUNCAO DE VERACIDADE', 'DISTRIBUICAO DINAMICA', 'ART. 341, CPC')),
    ('PROVA E DOCUMENTOS', 'Provas sem hierarquia/segregacao no requerimento',
     ('HIERARQUIZAR AS PROVAS', 'ESSENCIAIS; TESTEMUNHAL', 'RISCO DE INDEFERIMENTO PARCIAL',
      'DELIMITE OS MEIOS DE PROVA')),

    # ---------------------------------------------------- fatos e dados do caso
    ('FATOS E DADOS DO CASO', 'Erro factual: ID, numero, data ou valor errado',
     ('ERRO FACTUAL', 'MAS, NOS AUTOS DO AGRAVO', 'DATA DE PUBLICACAO DA', 'LOGICAMENTE IMPOSSIVEL',
      'DIVERGENCIA DE NUMERACAO', 'DIVERGENCIA DE DATAS', 'TEMPESTIVIDADE', 'MARCO TEMPORAL CORRETO',
      'PROCESSO INEXISTE', 'MENCAO A TERCEIRO', 'CLIENTE DIVERSO', 'ERRO NO ENDERECO',
      'QUALIFICACAO DA PARTE ADVERSA')),
    ('FATOS E DADOS DO CASO', 'Erro formal: numeracao de secoes, numero do processo, remissao interna',
     ('NUMERACAO DE SECOES', 'FORA DE ORDEM', 'INCONSISTENCIA FORMAL NO NUMERO', 'SEM O ZERO INICIAL',
      'NUMERACAO QUEBRADA', 'REMISSAO', 'NAO HA ITENS "2.2')),
    ('FATOS E DADOS DO CASO', 'Fato superveniente ou conexo ignorado',
     ('FATO SUPERVENIENTE', 'ACHADO CRITICO', 'LIMINAR SEGUE VIGENTE', 'NAO MENCIONA EM NENHUM MOME',
      'ORDEM DE SUSPENSAO', 'ACAO REVISIONAL EM APARTADO', 'RENEGOCIACAO', 'MOVIMENTACOES RECENTES')),
    ('FATOS E DADOS DO CASO', 'Sintese do caso sem os dados da operacao',
     ('SINTESE DO CASO SEM OS DADOS', 'IDENTIFICACAO DAS OPERACOES', 'TABELA POR CONTRATO',
      'SINTESE FATICA', 'NAO APENAS VALOR CONSOLIDADO', 'DADOS DA OPERACAO',
      'IDENTIFICAR COM CLAREZA QUAL', 'NARRATIVA FATICA ESPECIFICA')),

    # ------------------------------------------------------------------ pedidos
    ('PEDIDOS', 'Pedido condicionado a ato futuro e incerto',
     ('ATO FUTURO E INCERTO', 'CONDICAO INCERTA', 'UMA VEZ GARANTIDA A EXECUCAO',
      'PRE-REQUISITO DO PROPRIO PEDIDO', 'NAO PODE FICAR CONDICIONADO')),
    ('PEDIDOS', 'Pedido generico - falta individualizar ao caso concreto',
     ('ESTA GENERICA', 'INDIVIDUALIZAR O PERIGO', 'DE FORMA GENERICA', 'LISTA GENERICA',
      'APENAS DE FORMA GENERICA', 'TRATADA APENAS DE FORMA GENERICA', 'MENCAO GENERICA EM PROSA',
      'DECISAO GENERICA')),
    ('PEDIDOS', 'Pedido da inicial nao enfrentado no recurso / topico faltante',
     ('NAO SAO ENFRENTADOS NO RECURSO', 'PEDIDOS DA INICIAL QUE NAO', 'TOPICO ESPECIFICO',
      'SECAO AUTONOMA', 'SUBITEM PROPRIO', 'TOPICO PROPRIO', 'CAPITULO PROPRIO', 'INSERIR TOPICO',
      'INCLUIR UM ITEM ESPECIFICO', 'AUSENTE, PRECISA', 'HOJE AUSENTE', 'FICOU FORA DO RECURSO')),
    ('PEDIDOS', 'Pedido final nao cobre a tese desenvolvida na peca',
     ('CORRIGIR O PEDIDO FINAL', 'SO REMETE', 'NUNCA PEDIU EXPRESSAMENTE', 'PEDIDO FINAL')),
    ('PEDIDOS', 'Calculo/valor devido nao demonstrado (excesso alegado sem memoria de calculo)',
     ('MEMORIA DE CALCULO', 'PLANILHA DE CALCULO', 'VALOR QUE ENTENDE CORRETO',
      'DEMONSTRACAO DISCRIMINADA', 'NAO APRESENTA O CALCULO', 'DEMONSTRATIVO DISCRIMINADO')),
    ('PEDIDOS', 'Pedido dirigido ao orgao/autoridade errada',
     ('DIRIGIDO AO DESEMBARGADOR', 'VICE-PRESIDENTE', 'AJUSTAR A DIRECAO DO PEDIDO',
      'COMPETENTE PARA A ADMISSIBILIDADE')),

    # ------------------------------------------------------- forma e estrategia
    ('FORMA E ESTRATEGIA', 'Extensao inadequada a especie recursal',
     ('EXCESSIVAMENTE EXTENSA', '12 LAUDAS', 'NAO DEVERIA ULTRAPASSAR', 'CONCISAO',
      'OBJETIVIDADE EXIGIDA')),
    ('FORMA E ESTRATEGIA', 'Redundancia: reargumenta o merito onde bastava apontar o vicio',
     ('REARGUMENTA O MERITO', 'RECONSTITUI QUASE INTEGRALMENTE', 'REDUNDANTE',
      'REDISCUSSAO DE MERITO', 'E REDUNDANTE E TRAZ RISCO')),
    ('FORMA E ESTRATEGIA', 'Revela calculo/estrategia que enfraquece a tese',
     ('TAXA REVERSA', 'ANALISE REVERSA', 'O EFEITO E O OPOSTO DO PRETENDIDO', 'REVELA O NUMERO',
      'A INTENCAO E BOA')),
    ('FORMA E ESTRATEGIA', 'Falta impacto visual da prova documental (recorte/tabela)',
     ('IMPACTO VISUAL', 'RECORTE VISUAL', 'EM TABELA', 'PRINTS DE TRECHOS', 'INSERIR GRAFICO',
      'EXIBIR A CLAUSULA', 'CONFRONTO LITERAL ENTRE AS DUAS CLAUSULAS', 'TABELA COMPARATIVA',
      'JUNTAR PRINTS', 'ANEXAR COMO DOCUMENTO ESPECIFICO', 'RECORTE')),

    # ----------------------------------------------------------- entrega/projeto
    ('ENTREGA/PROJETO', 'Estrutura do projeto/relatorio ao cliente incompleta',
     ('MATRIZ DE RISCOS', 'CRONOGRAMA SEMANAL', 'SWOT', 'DILIGENCIAS', 'TABELA INDEPENDENTE',
      'TABELA CENTRALIZADA', 'PROXIMOS PASSOS E PRAZOS', 'ENTREGA DE PROJETO')),
)

# Apontamento que nao e' sobre a peca: cobranca de fluxo, KPI, prazo, gestao.
# Fica na base, marcado, porque e' volume real da Gerencia Juridica - mas nao
# entra no ranking de erro de peca nem no checklist do advogado.
CATEGORIAS_FLUXO = (
    ('FLUXO/CONTROLADORIA', 'Despacho com magistrado nao agendado apos protocolo',
     ('NAO HOUVE REALIZACAO DE DESPACHO', 'AGENDAR DESPACHO', 'NAO LOCALIZEI AGENDAMENTO')),
    ('FLUXO/CONTROLADORIA', 'Tag/KPI lancada errada ou nao lancada',
     ('KPI', 'TAG DE LIMINAR', 'NAO FOI LANCADA', 'PARA FINS DE METRICAS')),
    ('FLUXO/CONTROLADORIA', 'Prazo D-3 / perda de prazo',
     ('D-3', 'PERDA DE PRAZO', 'PRAZO FATAL', 'DESCUMPRIMENTO DO PRAZO')),
    ('FLUXO/CONTROLADORIA', 'Habilitacao/procuracao/contrato nao juntado',
     ('HABILITACAO', 'PROCURACAO', 'CONTRATO DE HONORARIOS NAO FOI', 'NAO HOUVE MANIFESTACAO NOS AUTOS')),
    ('FLUXO/CONTROLADORIA', 'Gestao: financeiro, sucesso do cliente, contrato, premiacao',
     ('SETOR DE SUCESSO', 'SETOR FINANCEIRO', 'O FINANCEIRO', 'NEGOCIACAO', 'RESCISAO', 'PREMIACAO',
      'CAMPANHA DE EXITO', 'ADITIVO', 'SATISFACAO', 'COBRANCA DOS HONORARIOS', 'G.A.',
      'GERENCIA ADMINISTRATIVA', 'CUSTAS', 'RENUNCIA', 'ABRIR AGENDAMENTO', 'DISTRIBUIR CADASTRO',
      'APURACAO', 'ESCLARECIMENTOS', 'PARECER DA CONTROLADORIA')),
    ('FLUXO/CONTROLADORIA', 'Orientacao de conduta ao advogado (sustentacao oral, postura, POP)',
     ('SUSTENTACAO ORAL', 'POSTURA ATIVA', 'REITERO A ORIENTACAO', 'INCLUIR NO POP',
      'ORIENTACAO QUE JA LHE FOI TRANSMITIDA')),
)


# ============================================================
# QUEBRA DO TEXTO EM APONTAMENTOS INDIVIDUAIS
# ============================================================
# A Dra. escreve em lista numerada ("1) ... 2) ..." / "1. ... 2. ..." /
# "## 1. ..."), entao cada item vira uma linha da base. O problema e' que ela
# tambem COLA EMENTA de acordao no meio do texto, e a ementa tambem e' numerada
# - sem tratamento, cada topico da ementa viraria um "apontamento" fantasma.

RE_ITEM = re.compile(r'(?:^|\s)(?:\*\*)?(?:\d{1,2}[\).]|##\s*\d{1,2}\.|[a-h]\))\s+')

RE_JURIS = re.compile(
    r'(RELATOR|REL\.|DJE|D J E|RESP:|AGINT|AREsp|ACORDAO|EMENTA|SUMULA \d|TURMA|CAMARA CIVEL'
    r'|DATA DE JULGAMENTO|PUBLICADO EM|TJ-|STJ -|STF -|RECURSO ESPECIAL CONHECIDO'
    r'|NEGO PROVIMENTO|UNANIME)', re.I)

# Verbo de comando/diagnostico. A Dra. tambem escreve apontamento em forma
# nominal ("Impacto Visual da Prova Documental"), entao a ausencia de verbo
# sozinha NAO basta para descartar - so conta junto com sinal de jurisprudencia.
VERBOS_APONTAMENTO = (
    'INCLUIR', 'INSERIR', 'INSIRA', 'ARGUMENTE', 'CORRIGIR', 'AJUSTAR', 'REVISAR', 'ACRESCENTAR',
    'RETIRAR', 'SUBSTITUIR', 'REFORCAR', 'EXPLORAR', 'FUNDAMENTAR', 'REQUERER', 'SUGIRO', 'SUGERE',
    'RECOMENDO', 'PRECISA', 'DEVE ', 'FALTA', 'AUSENTE', 'NAO MENCIONA', 'EVITAR', 'ATENTAR',
    'VERIFICAR', 'RESOLVER', 'FORMULAR', 'REDESENHAR', 'RECLASSIFICAR', 'SEGREGAR', 'DESTACAR',
    'HIERARQUIZAR', 'JUNTAR', 'ANEXAR', 'MELHORIA', 'AJUSTE', 'PEDIR', 'PEDIDO', 'SOLICITO',
    'APROFUNDAR', 'ADICIONAR', 'CONSTRUIR', 'MANTER', 'ELIMINAR', 'REPOSICIONAR', 'REESCREVER',
    'TROCAR', 'PREENCHER', 'CITAR', 'ACIONAR', 'PROVIDENCIAR', 'ANALISAR', 'NAO USA',
    'NAO APRESENTA', 'NAO CITA', 'NAO ENFRENTA', 'ENTENDO', 'VEJO QUE', 'IDENTIFIQUEI',
    'QUESTIONO', 'ORIENTA',
)


def e_transcricao(trecho):
    """Trecho de ementa/acordao colado na devolutiva - nao e' apontamento."""
    hits = len(RE_JURIS.findall(trecho))
    tem_verbo = any(v in _sem_acento(trecho) for v in VERBOS_APONTAMENTO)
    caixa_alta = sum(1 for c in trecho if c.isupper())
    return (hits >= 2
            or (hits >= 1 and not tem_verbo)
            or (caixa_alta > len(trecho) * 0.5 and not tem_verbo))


def quebrar_em_apontamentos(texto):
    """Divide a devolutiva em itens. Texto sem lista numerada volta inteiro."""
    marcas = [m.start() for m in RE_ITEM.finditer(texto) if m.start() > 20]
    if len(marcas) < 2:
        return [texto]
    marcas.append(len(texto))
    partes = [texto[marcas[i]:marcas[i + 1]].strip() for i in range(len(marcas) - 1)]
    return [p for p in partes if len(p) > 40] or [texto]


def classificar(trecho):
    """Devolve [(familia, categoria)]. Pode cair em mais de uma - o apontamento
    da Dra. costuma misturar (ex.: 'incluir o art. 341 e listar os fatos
    incontroversos' e' fundamentacao E prova)."""
    if e_transcricao(trecho):
        return [('TRANSCRICAO DE JURISPRUDENCIA', 'ementa colada na devolutiva (nao e apontamento)')]
    normalizado = _sem_acento(trecho)
    achados = [(fam, cat) for fam, cat, gatilhos in CATEGORIAS
               if any(g in normalizado for g in gatilhos)]
    if achados:
        return achados
    achados = [(fam, cat) for fam, cat, gatilhos in CATEGORIAS_FLUXO
               if any(g in normalizado for g in gatilhos)]
    return achados or [('NAO CLASSIFICADO', 'revisar manualmente')]


# ============================================================
# COLETA
# ============================================================

def _dt(valor):
    try:
        return datetime.strptime(str(valor)[:19], '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return None


def processos_com_revisao(data_inicio, data_fim, verbose=True):
    """Processos que tiveram peca submetida a Gerencia Juridica no periodo.

    Fonte: GET /posts filtrado pela tag CONFERIR/REVISAR PETICAO (cobertura
    total, com paginacao). As tags de retorno entram junto porque a devolutiva
    as vezes e' o unico registro que sobrou no historico.
    """
    lawsuits, submissoes = set(), []
    for tag in (TAG_REVISAO, TAG_AJUSTES, TAG_APROVADA):
        params = {'limit': 100, 'offset': 0, 'task_id': tag,
                  'completed_start': data_inicio, 'completed_end': data_fim}
        while True:
            resposta = advbox._request('GET', '/posts', params=params) or {}
            registros = resposta.get('data', [])
            for r in registros:
                if r.get('lawsuits_id'):
                    lawsuits.add(r['lawsuits_id'])
                if tag == TAG_REVISAO:
                    submissoes.append(r)
            total = resposta.get('totalCount', 0)
            params['offset'] += 100
            if params['offset'] >= total or not registros:
                break
        if verbose:
            print(f'  tag {tag}: {len(lawsuits)} processos acumulados')
    return sorted(lawsuits), submissoes


def devolutivas_da_gerencia(lawsuit_ids, data_inicio, data_fim,
                            autor='JULIANA FERREIRA', pausa=2.1, verbose=True):
    """Le o historico de cada processo e separa o que a Gerencia Juridica escreveu.

    ATENCAO: /history nao pagina e devolve ~20 itens. Em processo movimentado os
    itens antigos ficam fora - o resultado e' piso, nao total.
    """
    encontradas, sem_historico = [], 0
    for i, lawsuit_id in enumerate(lawsuit_ids, 1):
        try:
            resposta = advbox._request('GET', f'/history/{lawsuit_id}',
                                       params={'limit': 100}, retries=1) or {}
        except Exception:
            resposta = {}
        itens = resposta.get('data', [])
        if not itens:
            sem_historico += 1
        for item in itens:
            if autor not in str(item.get('author') or ''):
                continue
            if item.get('task') not in TAGS_DEVOLUTIVA:
                continue
            texto = ' '.join((item.get('comments') or '').split())
            if len(texto) < MIN_CARACTERES:
                continue
            quando = str(item.get('created_at') or '')[:10]
            if not (data_inicio <= quando <= data_fim):
                continue
            encontradas.append({
                'quando': item.get('created_at'),
                'tag': item.get('task'),
                'processo': item.get('process_number') or item.get('protocol_number') or '',
                'cliente': item.get('customers') or '',
                'destinatario': item.get('responsible') or '',
                'texto': texto,
            })
        if verbose and i % 25 == 0:
            print(f'  historico {i}/{len(lawsuit_ids)} ({len(encontradas)} devolutivas)')
        time.sleep(pausa)   # GET 30/min: manter folga
    if verbose and sem_historico:
        print(f'  {sem_historico} processos sem historico acessivel')
    encontradas.sort(key=lambda x: x['quando'])
    return encontradas


def montar_base(devolutivas):
    """Uma linha por (apontamento x categoria)."""
    linhas = []
    for d in devolutivas:
        for n, trecho in enumerate(quebrar_em_apontamentos(d['texto']), 1):
            for familia, categoria in classificar(trecho):
                linhas.append({**d, 'ap_n': n, 'familia': familia,
                               'categoria': categoria, 'apontamento': trecho})
    return linhas


def gravar_csv(linhas, caminho):
    campos = ['quando', 'tag', 'processo', 'cliente', 'destinatario',
              'ap_n', 'familia', 'categoria', 'apontamento', 'texto']
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        escritor = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        escritor.writeheader()
        escritor.writerows(linhas)
    return caminho


# ============================================================
# RELATORIO
# ============================================================

FORA_DO_RANKING = ('FLUXO/CONTROLADORIA', 'TRANSCRICAO DE JURISPRUDENCIA')


def _advogados_conhecidos():
    nomes = []
    for bloco in CONTROLLERS.values():
        nomes += [_sem_acento(a['nome']) for a in bloco.get('advogados', [])]
    # advogados que aparecem nas devolutivas mas nao estao no mapa de controllers
    nomes += ['BRUNA CLAUDIA VICENTE', 'RENAN GOMES MALDONADO DE JESUS']
    return sorted(set(nomes))


def relatorio(linhas, devolutivas):
    from collections import Counter, defaultdict

    peca = [l for l in linhas if l['familia'] not in FORA_DO_RANKING]
    print()
    print('=' * 74)
    print('  APONTAMENTOS DA GERENCIA JURIDICA')
    print('=' * 74)
    print(f'  devolutivas da GJ .............. {len(devolutivas)}')
    print(f'  apontamentos sobre a peca ..... {len(peca)}')
    print(f'  cobranca de fluxo/KPI/prazo ... '
          f'{sum(1 for l in linhas if l["familia"] == "FLUXO/CONTROLADORIA")}')
    print(f'  ementa colada (descartada) .... '
          f'{sum(1 for l in linhas if l["familia"] == "TRANSCRICAO DE JURISPRUDENCIA")}')

    print()
    print('  POR MES (subcontagem: /history so devolve ~20 itens por processo)')
    for mes, n in sorted(Counter(l['quando'][:7] for l in peca).items()):
        print(f'    {mes}  {n:4d} apontamentos')

    print()
    print('  RANKING POR FAMILIA')
    for familia, n in Counter(l['familia'] for l in peca).most_common():
        print(f'    {n:4d}  {familia}')

    print()
    print('  RANKING POR CATEGORIA')
    for (familia, categoria), n in Counter(
            (l['familia'], l['categoria']) for l in peca
            if l['familia'] != 'NAO CLASSIFICADO').most_common():
        print(f'    {n:4d}  [{familia[:20]:20s}] {categoria}')

    print()
    print('  POR ADVOGADO DESTINATARIO')
    print('  (a devolutiva costuma marcar advogado + controller; so o advogado conta)')
    conhecidos = _advogados_conhecidos()
    por_adv, devol_adv, vistos = defaultdict(Counter), Counter(), set()
    for l in peca:
        destino = _sem_acento(l['destinatario'])
        for nome in conhecidos:
            if nome in destino:
                por_adv[nome][l['categoria']] += 1
                chave = (nome, l['quando'], l['texto'][:50])
                if chave not in vistos:
                    vistos.add(chave)
                    devol_adv[nome] += 1
    for nome, n in devol_adv.most_common():
        top = [f'{c} ({q})' for c, q in por_adv[nome].most_common(2)
               if c != 'revisar manualmente']
        print(f'    {n:3d} devolutivas | {nome.title():38s} | {"; ".join(top)[:90]}')
    print()


# ============================================================
# CLI
# ============================================================

def executar(dias=None, de=None, ate=None, csv_saida=None, pausa=2.1):
    if de and ate:
        data_inicio, data_fim = de, ate
    else:
        fim = datetime.now()
        inicio = fim - timedelta(days=dias or 90)
        data_inicio, data_fim = inicio.strftime('%Y-%m-%d'), fim.strftime('%Y-%m-%d')

    print(f'Periodo: {data_inicio} a {data_fim}')
    print('1/3 Localizando processos com peca submetida a Gerencia Juridica...')
    lawsuit_ids, submissoes = processos_com_revisao(data_inicio, data_fim)
    print(f'    {len(lawsuit_ids)} processos | {len(submissoes)} submissoes na tag CONFERIR/REVISAR')

    minutos = len(lawsuit_ids) * pausa / 60
    print(f'2/3 Lendo o historico de cada um (autor so existe la) ~{minutos:.0f} min...')
    devolutivas = devolutivas_da_gerencia(lawsuit_ids, data_inicio, data_fim, pausa=pausa)
    print(f'    {len(devolutivas)} devolutivas da Gerencia Juridica')

    print('3/3 Classificando...')
    linhas = montar_base(devolutivas)
    if csv_saida:
        gravar_csv(linhas, csv_saida)
        print(f'    base gravada em {csv_saida}')
    relatorio(linhas, devolutivas)
    return linhas
