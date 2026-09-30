"""
Config central da equipe - Maldonado Advogados

Preencher no onboarding. Nao hardcodar IDs em nenhum outro modulo -
todo codigo deve importar deste arquivo.
"""

# IDs de usuario no ADVBOX (Configuracoes > Usuarios, no painel ADVBOX do escritorio)
USUARIOS_ADVBOX = {
    "RESPONSAVEL": 93208,     # Renan Gomes Maldonado de Jesus (OAB/RO 5769)
    "OUTRO_ADVOGADO": 101621,  # Bruno Vinicius de Souza Faustino (OAB/RO 13021)
    # A Dra. Juliana e' GERENTE JURIDICA, nao controller: ela NAO trata
    # intimacao. Nao usar este ID como destino de tarefa de intimacao - quem faz
    # o tratamento e' a Controladoria (CONTROLLERS, abaixo). Regra dela mesma,
    # 10/09/2026.
    "GERENCIA_JURIDICA": 120163,  # Juliana Ferreira Gusmao de Lara
}

# ============================================================
# CONTROLLERS x ADVOGADOS  (regra da Dra. Juliana, 10/09/2026)
# ============================================================
# Quem LANCA a tarefa de intimacao no ADVBOX (campo 'from') nao e' mais o
# Dr. Renan: e' a CONTROLLER do advogado responsavel pelo processo. O
# destinatario (guests) e' o proprio advogado responsavel.
#
# IDs conferidos contra a conta real do escritorio em 10/09/2026 (46 usuarios).
# O ID e' o que manda: e' exato e sobrevive a mudanca de grafia do nome. O "nome"
# fica ao lado so para o relatorio e para casar o responsavel que o /lawsuits
# devolve como texto (match por tokens, sem acento e sem caixa).
# `python OPERACIONAL/main.py advbox` reconfere o mapa inteiro contra a conta.
#
# Advogado que casar com DUAS controllers e' tratado como ambiguo - a automacao
# para e pergunta, nunca chuta.
CONTROLLERS = {
    "NATALY": {
        "id": 252009,          # NATALY DAMASCENA DE CARVALHO
        "nome": "NATALY DAMASCENA DE CARVALHO",
        "advogados": [
            {"nome": "ARILSON CRUZ LOPES", "id": 130926},
            {"nome": "MAILSON SANTOS MONTEIRO", "id": 93693},
            {"nome": "JOSUE KALEBE OLIVEIRA DE ANDRADE", "id": 100903},
            {"nome": "HELOISA GARCIA ANTUNES", "id": 288554},
            {"nome": "AGENOR RUFINO DE MELO NETO", "id": 262240},
        ],
    },
    "MANUELLE": {
        "id": 189532,          # MANUELLE ABREU
        "nome": "MANUELLE ABREU",
        "advogados": [
            # A conta tem dois Brunos: o BRUNO FERNANDO FERREIRA (271032) e'
            # ENGENHEIRO AGRONOMO, nao advogado - nunca recebe intimacao.
            # O advogado e' o Dr. Bruno Vinicius, OAB/RO 13021 (confirmado pela
            # Dra. Juliana em 10/09/2026).
            {"nome": "BRUNO VINICIUS DE SOUZA FAUSTINO", "id": 101621},
            # No ADVBOX esta cadastrado como NARCISO (nao "Narcisio")
            {"nome": "FELIPE DA CONCEICAO SOUZA NARCISO", "id": 253330},
            {"nome": "MATHEUS RAMOS", "id": 182170},
            {"nome": "TAYNARA SCATOLIN", "id": 288544},
            {"nome": "ANA SHEILA DA SILVA GARCEZ", "id": 295888},
        ],
    },
}

# Processo cujo responsavel e' a DIRECAO (Dr. Renan) ou a GERENCIA JURIDICA
# (Dra. Juliana): nenhum dos dois trata intimacao, entao quem assume e' a
# controller abaixo - ela lanca e ela recebe. Regra da Dra. Juliana, 10/09/2026.
# Na carteira de 10/09/2026 sao 143 + 68 processos, dos quais so 22 + 6 estao
# ativos - o resto ja' esta' arquivado.
RESPONSAVEIS_DIRECAO = [
    93208,   # RENAN GOMES MALDONADO DE JESUS
    120163,  # JULIANA FERREIRA GUSMAO DE LARA
]
CONTROLLER_DA_DIRECAO = "NATALY"

# Processo ARQUIVADO no ADVBOX, em regra, nao tem agendamento - mas quando chega
# intimacao nele (desarquivamento, execucao de honorarios, baixa) o destino NAO
# muda: continua sendo a controller do advogado responsavel. O que muda e' o
# relatorio, que marca "PROCESSO ARQUIVADO" para a controller conferir se cabe
# algo antes de agendar. Regra da Dra. Juliana, 10/09/2026.

# Responsavel fora do mapa acima (advogado que saiu, estagiario, engenheiro,
# equipe de atendimento, cadastro antigo) ou processo sem responsavel: a
# CONTROLLER DE FALLBACK assume - ela lanca e ela recebe, nao o responsavel do
# processo. Decisao da Dra. Juliana, 10/09/2026: sao ~92 processos ativos de 23
# pessoas que "em geral nao tem movimentacao", e varias delas nem sao advogados
# (Karla e' atendimento, Bruno Fernando e' engenheiro agronomo) - intimacao
# nenhuma pode cair na fila de quem nao cumpre prazo.
#
# CONTROLLER_FALLBACK = None volta ao comportamento anterior: nao cria a tarefa
# e sobe o item como "CONTROLLER A DEFINIR" no relatorio.
CONTROLLER_FALLBACK = "MANUELLE"

# ============================================================
# SETOR DE PROVAS / DOCUMENTOS  (rotina diaria de intimacoes)
# ============================================================
# Quem monta a pasta no Zeus ate o D-5, para a Controladoria protocolar em D-3.
# Regra da Dra. Juliana, 10/09/2026 - IDs conferidos na conta.
SETOR_PROVAS = {
    "CESAR": 261858,      # CESAR AUGUSTO OLIVEIRA PETKOWSKI
    "ANA_CLARA": 296105,  # ANA CLARA BOTELHO LEAL GOMES
    "HANNA": 296635,      # HANNA LUISA FURTADO PEREIRA
}

# Tipos de tarefa do ADVBOX usados pela rotina diaria (IDs da conta do
# escritorio - `python OPERACIONAL/main.py advbox` reconfere).
TIPOS_TAREFA = {
    # advogado, 1o dia util apos a intimacao: analisa a MEDIDA CABIVEL
    # (regra da Dra. Juliana, 10/09/2026 - vale para todo ato com providencia,
    # nao so para ato decisorio)
    "ANALISE_MEDIDA": 2987285,      # ANALISE - NIVEL 01
    # advogado: recebe a minuta pronta e revisa (nao confecciona do zero)
    "REVISAO_PECA": 2596525,        # CONFERIR/REVISAR PETICAO
    # setor de provas, 1o dia util apos a intimacao: junta o que falta
    "ORGANIZAR_DOCUMENTOS": 9970888,  # PROTOCOLO - ORGANIZAR DOCUMENTOS
    # setor de provas, em D-5: pasta fechada no Zeus para a Controladoria protocolar
    "CONFERIR_PASTA": 10347758,       # CONFERIR PASTA DE DOCUMENTOS
    # controladoria: protocola em D-3 (nunca a automacao)
    "PROTOCOLO_D3": 8941168,        # PROTOCOLO D-3
    # o advogado devolve a peca aprovada para a controladoria protocolar
    "PECA_APROVADA": 8720914,       # PECA APROVADA PARA PROTOCOLO
    # audiencia designada -> aviso ao cliente (POP-CJ-003-C)
    "AVISAR_AUDIENCIA": 2596497,    # AVISAR CLIENTE DA AUDIENCIA
    # item que a rotina nao conseguiu decidir sozinha
    "CONFERIR_CONTROLLER": 4651503,  # ACOMPANHAMENTO
    # controller agenda despacho com relator/vogais (recurso distribuido no 2o
    # grau, inclusao em pauta - regra da Dra. Juliana, 21/09/2026)
    "AGENDAR_DESPACHO": 9222516,    # AGENDAR DESPACHO
    # relatorio diario da rodada das 08:00
    "RELATORIO": 6018821,           # RELATORIO
}

# Marcadores de RESULTADO — alimentam o KPI da Controladoria (POP-CJ-002).
# So sao lancados quando o resultado esta claro no texto; em caso ambiguo a
# rotina nao chuta, sinaliza no relatorio (regra da Dra. Juliana, 10/09/2026).
TIPOS_RESULTADO = {
    "LIMINAR_DEFERIDA": 6523484,
    "LIMINAR_PARCIAL": 6523333,
    "LIMINAR_INDEFERIDA": 6364203,
    "SENTENCA_PROCEDENTE": 6523487,
    "SENTENCA_PARCIAL": 6523490,
    "SENTENCA_IMPROCEDENTE": 6523491,
    "SENTENCA_EXTINCAO": 10016576,
    "ACORDAO_PROCEDENTE": 6523183,
    "ACORDAO_PARCIAL": 6523180,
    "ACORDAO_IMPROCEDENTE": 6364204,
    "ACORDO_CELEBRADO": 6523485,
}

# Destinatarios do relatorio diario das 08:00 (tarefa no ADVBOX + e-mail).
# Decisao da Dra. Juliana, 10/09/2026: as duas controllers + gerencia juridica.
RELATORIO_DIARIO_IDS = [252009, 189532, 120163]
RELATORIO_DIARIO_EMAILS = [
    "contato@exemplo.com.br",
    "contato@exemplo.com.br",
    "contato@exemplo.com.br",
]

# Onde o relatorio diario e' arquivado no Drive (a partir da raiz da ZEUS).
RELATORIO_DIARIO_PASTA_ZEUS = ["CONTROLADORIA", "RELATORIOS DIARIOS"]

# Feriados/suspensoes de expediente que o calculo de prazo nao tem como
# adivinhar (portaria do TJRO, ponto facultativo local). Formato "AAAA-MM-DD".
# Ver OPERACIONAL/prazos.py.
FERIADOS_EXTRA = []


# Dupla responsavel por avisar o cliente (WhatsApp) quando a intimacao designa audiencia.
# Regra da Dra. Juliana, 08/09/2026 - ver POP-CJ-003-C no agente de controladoria.
COMUNICACAO_CLIENTE = {
    "KARLA": 252439,       # Karla Beatriz dos Santos
    "ANNA_LYDIA": 185089,  # Anna Lydia Rabelo
}

# E-mails da mesma dupla (convite de agenda, quando for o caso)
EMAILS_COMUNICACAO_CLIENTE = [
    "contato@exemplo.com.br",
    "contato@exemplo.com.br",
]

# Campo 'from' das tarefas criadas via /posts quando NAO ha processo (e portanto
# nao ha advogado responsavel de quem derivar a controller). Tarefa vinculada a
# processo usa sempre a controller - ver CONTROLLERS acima.
USUARIO_PADRAO_TAREFAS = "GERENCIA_JURIDICA"

# OABs monitoradas na captura de intimacoes via DJEN/Comunica (CNJ)
# Formato: (numero, UF)
OABS_MONITORADAS = [
    ("5769", "RO"),   # Renan Gomes Maldonado de Jesus
    ("13021", "RO"),  # Bruno Vinicius de Souza Faustino
]

# E-mails da equipe para convite de eventos de prazo no Google Agenda
EMAILS_EQUIPE_AGENDA = [
    # "juliana@...",
    # "renan@...",
]


# ============================================================
# QUADRO DE ADVOGADOS DO TIMBRADO  (faixa 2026)
# ============================================================
# Ate 11/09/2026 esta lista existia apenas como PIXEL, rasterizada dentro de
# `.claude/skills/timbrado/assets/timbrado-maldonado-2026.jpeg`. Incluir um
# advogado exigia editar a imagem, e por isso CINCO advogados ativos do mapa
# CONTROLLERS nunca chegaram ao papel timbrado. Agora a arte foi separada em
# duas pecas (friso e logo) e o quadro virou TEXTO, gerado a partir daqui por
# `OPERACIONAL/gerar_timbrado.py`. Incluir alguem passou a ser uma linha.
#
# A ORDEM IMPORTA: e' a ordem de exibicao na faixa, comecando pelo Dr. Renan.
# Nomes novos entram no fim, para nao remexer a hierarquia ja' impressa.
#
# NUNCA preencher OAB por suposicao: advogado sem numero confirmado fica FORA
# da lista e e' registrado em ADVOGADOS_SEM_OAB, abaixo.
ADVOGADOS_TIMBRADO = [
    ("Renan Maldonado",    "OAB/RO 5.769"),
    ("Eliane Miranda",     "OAB/RO 7.904"),
    ("Arilson Cruz Lopes", "OAB/RO 9.982"),
    ("Bruno Vinícius",     "OAB/RO 13.021"),
    ("Felipe Souza",       "OAB/RJ 244.309"),
    ("Mailson Monteiro",   "OAB/RO 14.501"),
    ("Matheus Ramos",      "OAB/RJ 262.255"),
    ("Taynara Scatolin",   "OAB/MT 30.109"),   # incluida em 11/09/2026
    ("Heloisa Antunes",    "OAB/DF 76.621"),   # incluida em 11/09/2026
    ("Agenor Rufino",      "OAB/PE 62.751"),   # incluida em 15/09/2026
    ("Ana Sheila Garcez",  "OAB/RO 16.126"),   # incluida em 16/09/2026 (OAB informada pela GJ)
]

# Advogados do escritorio que NAO entram no timbrado ate que a OAB seja
# confirmada pela Gerencia Juridica (decisao da Dra. Juliana, 11/09/2026:
# "os demais por ora nao coloque, quando eu tiver os dados te informo").
ADVOGADOS_SEM_OAB = [
    ("Josué Kalebe Oliveira de Andrade", 100903),
]
# Levantamento no DJEN em 16/09/2026 (so' indicio, a GJ confirma antes de entrar):
#   - Josue Kalebe: JOSUE KALEBE OLIVEIRA DE ANDRADE, OAB/RO 15.351, em 78
#     publicacoes (campo estruturado do DJEN). Entrando, e' o 12o nome: o quadro
#     nao cabe mais em uma coluna (ver gerar_timbrado.ALTURA_MAXIMA_QUADRO).
# Saiu desta lista em 16/09/2026: ANA SHEILA DA SILVA GARCEZ, OAB/RO 16.126,
# informada pela Dra. Juliana. Nao ha' publicacao dela no DJEN ate' essa data
# (inscricao recente), entao o numero veio da GJ, nao do Diario.
# Saiu desta lista em 15/09/2026: AGENOR RUFINO DE MELO NETO, que entrou no
# quadro. A OAB dele e' de PERNAMBUCO (OAB/PE 62.751), nao de Rondonia -
# conferida em 19 publicacoes do DJEN. Quem supuser "OAB/RO" pelo escritorio
# ser de Porto Velho poe numero de outro advogado no papel.

# Saiu da faixa em 11/09/2026 por decisao da Dra. Juliana: BRUNA VICENTE
# (OAB/TO 9.013). Atencao: ela subscreveu iniciais em 2026 (p. ex. a do
# Sr. Cliente V, 0000072-93.2026.8.11.0098, em 10/06/2026) e segue
# como advogada constituida nesses autos - sair do timbrado nao a tira do
# processo.
#
# Pendente de confirmacao da GJ: Angela Rosa (OAB/RO 11.689), que consta do
# timbrado antigo de 2024 e nao do de 2026; e Carlos Gabriel (OAB/RO 7.486),
# que a skill `timbrado` ja' registra como fora do escritorio.


# Planilha do KPI de exito (uma por competencia, aberta por semana) - pasta do
# Drive indicada pela Dra. Juliana em 15/09/2026. Usada por OPERACIONAL/kpi_planilha.py
# (comando: main.py kpi --planilha).
KPI_PLANILHA_PASTA_ID = None  # ID da pasta do Drive onde a planilha de acompanhamento e gravada
