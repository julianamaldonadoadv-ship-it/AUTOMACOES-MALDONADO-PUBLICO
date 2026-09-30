# -*- coding: utf-8 -*-
"""
Atualização do cliente sobre o processo — em português, não em juridiquês
=========================================================================

Fluxo pedido pela Dra. Juliana (30/09/2026), na rodada das 08:00:

    publicação (Sync) -> tratamento simples -> texto que o cliente entende
    -> contato do cliente -> LOTE PARA A GJ APROVAR -> envio do que foi liberado

**A GJ aprova no lote.** A rotina não fala com cliente por conta própria: ela
escreve o texto, acha o contato e põe tudo numa planilha com a coluna
`Liberar? (S/N)`. A Dra. Juliana corta o que não deve sair e libera o resto;
só então a linha liberada vira envio. Mensagem sobre processo vai para fora do
escritório e não tem como voltar atrás — é o mesmo motivo pelo qual a
automação não protocola.

Duas travas, e as duas são verificáveis:

1. **Nem toda publicação vira mensagem.** Das 112 intimações de 01–10/09/2026,
   só 21 eram decisão; o resto é despacho, remessa, expediente. Cliente avisado
   de "juntada de petição" para de ler as mensagens do escritório — e aí não lê
   a que importa. `EVENTOS` é a lista do que ele quer saber; o que não está lá
   **não gera mensagem** (sobe como `sem_mensagem`, com o motivo).

2. **Juridiquês não passa.** `varrer_juridiques()` varre o texto contra
   `TERMOS_PROIBIDOS`. Texto com termo proibido **não é publicado** no lote:
   sobe como `texto_reprovado`. Lista vazia é o único resultado aceitável — o
   mesmo padrão de `visual_law.varrer_marcadores_print()`.

O que o módulo **nunca** faz: não promete resultado, não dá prazo ao cliente
("em 30 dias o senhor recebe"), não explica estratégia, não manda documento, e
não escreve texto para evento que não reconhece — nesse caso a linha sobe para
a GJ escrever à mão. Palpite sobre o processo do cliente é pior que silêncio.

    python OPERACIONAL/main.py cliente-atualizacao --dias 1
    python OPERACIONAL/main.py cliente-atualizacao --dias 1 --planilha
    python OPERACIONAL/main.py cliente-atualizacao --enviar-liberados
    python OPERACIONAL/atualizacao_cliente.py --autoteste
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'INTEGRACOES'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config'))


# ============================================================
#  1. O QUE O CLIENTE QUER SABER
# ============================================================
#  Cada entrada: marca no ato -> (assunto, o que aconteceu, o que fazemos,
#                                 o que o cliente faz)
#  A 4a parte é quase sempre "nada" — e dizer isso explicitamente evita a
#  ligação de volta perguntando "preciso fazer algo?".
EVENTOS = {
    'sentenca_favoravel': dict(
        assunto='decisão do juiz',
        aconteceu='o juiz decidiu o processo a seu favor',
        fazemos='estamos conferindo o prazo do banco para recorrer e acompanhamos',
        cliente='nada por agora'),
    'sentenca_desfavoravel': dict(
        assunto='decisão do juiz',
        aconteceu='o juiz não acolheu o nosso pedido nesta etapa',
        fazemos='estamos analisando a decisão para apresentar recurso',
        cliente='nada por agora — entramos em contato se precisarmos de algum documento'),
    'liminar_deferida': dict(
        assunto='pedido urgente aceito',
        aconteceu='o juiz aceitou o nosso pedido urgente',
        fazemos='vamos comunicar o banco e acompanhar o cumprimento',
        cliente='nada por agora'),
    'liminar_indeferida': dict(
        assunto='pedido urgente',
        aconteceu='o juiz não aceitou o pedido urgente por agora — o processo continua normalmente',
        fazemos='estamos vendo a melhor forma de refazer o pedido com mais documentos',
        cliente='nada por agora'),
    'audiencia_designada': dict(
        assunto='audiência marcada',
        aconteceu='foi marcada uma audiência no seu processo',
        fazemos='vamos passar data, hora e como participar, com preparação antes',
        cliente='aguardar o nosso contato com os detalhes'),
    'banco_citado': dict(
        assunto='banco avisado',
        aconteceu='o banco foi oficialmente avisado do processo e agora tem prazo para responder',
        fazemos='acompanhamos a resposta dele e avisamos',
        cliente='nada por agora'),
    'acao_distribuida': dict(
        assunto='processo aberto',
        aconteceu='a sua ação foi registrada na justiça e já tem juiz responsável',
        fazemos='acompanhamos os próximos passos',
        cliente='nada por agora'),
    'recurso_distribuido': dict(
        assunto='recurso no tribunal',
        aconteceu='o recurso chegou ao tribunal e já foi sorteado o desembargador que vai analisar',
        fazemos='vamos despachar com o gabinete e acompanhar',
        cliente='nada por agora'),
    'recurso_julgado_favoravel': dict(
        assunto='decisão do tribunal',
        aconteceu='o tribunal decidiu a seu favor',
        fazemos='estamos conferindo os próximos passos e os prazos',
        cliente='nada por agora'),
    'recurso_julgado_desfavoravel': dict(
        assunto='decisão do tribunal',
        aconteceu='o tribunal não acolheu o nosso recurso',
        fazemos='estamos analisando a decisão para ver o que ainda cabe',
        cliente='nada por agora — entramos em contato para conversar'),
    'pericia_designada': dict(
        assunto='perícia marcada',
        aconteceu='o juiz mandou fazer uma perícia no seu caso',
        fazemos='vamos indicar o nosso assistente e as perguntas técnicas',
        cliente='aguardar o nosso contato — podemos pedir documentos da propriedade'),
    'acordo_homologado': dict(
        assunto='acordo confirmado',
        aconteceu='o juiz confirmou o acordo do seu processo',
        fazemos='acompanhamos o cumprimento do que foi combinado',
        cliente='nada por agora'),
}

#  Motivo pelo qual um ato NÃO gera mensagem. Sai no relatório, para a GJ ver
#  que a rotina não esqueceu — ela decidiu não incomodar o cliente.
SEM_MENSAGEM = {
    'expediente': 'ato interno do processo (juntada, remessa, migração de sistema) — cliente não precisa saber',
    'so_prazo_nosso': 'ato que pede providência só nossa (manifestação, documentos) — vira tarefa do advogado, não mensagem',
    'parte_contraria': 'ordem dirigida só à parte contrária',
    'embargos_declaracao': 'pedido de esclarecimento da decisão — o cliente é avisado quando sair o resultado',
    'processo_arquivado': 'processo arquivado — a controller confere antes de qualquer contato',
    'evento_nao_reconhecido': 'a rotina não reconheceu o tipo de ato — GJ escreve o texto à mão',
}


# ============================================================
#  2. JURIDIQUÊS NÃO PASSA
# ============================================================
#  Termo que o cliente produtor rural não usa. Alguns são sinônimos do que já
#  está em EVENTOS ("defiro" -> "aceitou"); outros são a armadilha de copiar o
#  ato judicial para dentro da mensagem.
TERMOS_PROIBIDOS = (
    'deferimento', 'deferido', 'defiro', 'indeferimento', 'indeferido', 'indefiro',
    'tutela', 'liminar', 'antecipatoria', 'cautelar', 'mandamental',
    'exordial', 'peticao inicial', 'exequente', 'executado', 'embargante',
    'embargado', 'agravante', 'agravado', 'apelante', 'apelado',
    'autos', 'egregia', 'excelencia', 'meritissimo', 'douto', 'colenda',
    'sumula', 'tema 28', 'repetitivo', 'jurisprudencia', 'acordao',
    'improcedente', 'procedente', 'transito em julgado', 'preclusao',
    'saneamento', 'despacho', 'dispositivo', 'sucumbencia', 'honorarios',
    'capitalizacao', 'anatocismo', 'mora', 'descaracterizacao', 'alongamento',
    'prorrogacao compulsoria', 'mcr', 'cedula de credito',
    'intimacao', 'citacao', 'compulsoria', 'requerimento',
    'nos termos do', 'art.', 'artigo', 'cpc', 'inciso',
    'oportunamente', 'destarte', 'outrossim', 'ex positis', 'data venia',
)


def _sem_acento(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto or '')
                   if unicodedata.category(c) != 'Mn').lower()


def varrer_juridiques(texto):
    """Devolve a lista de termos proibidos achados. Lista vazia e' o unico
    resultado aceitavel — texto com termo nao vai ao lote."""
    plano = _sem_acento(texto)
    achados = []
    for termo in TERMOS_PROIBIDOS:
        alvo = _sem_acento(termo)
        # Fronteira de palavra quando o termo e' uma palavra so; "art." e os
        # termos com ponto/espaco entram como trecho literal.
        padrao = (r'\b' + re.escape(alvo) + r'\b') if alvo.isalpha() else re.escape(alvo)
        if re.search(padrao, plano):
            achados.append(termo)
    return achados


# ============================================================
#  3. O TEXTO
# ============================================================

def tratamento(nome_cliente):
    """`Sr.`/`Sra.` nao se adivinha por nome. Usa o primeiro nome sem titulo —
    e' o que a Karla faz no atendimento.

    **Nem o corpo da mensagem trata o cliente por genero** (nao ha "o senhor"
    em EVENTOS, e o autoteste cobra isso): metade da carteira e' de mulheres, e
    nome nao diz genero. "O que precisa da sua parte" serve para os dois e
    ainda casa melhor com o "avisamos/entramos em contato" do resto do texto.
    """
    primeiro = (nome_cliente or '').strip().split()
    return primeiro[0].title() if primeiro else 'Olá'


def texto_para_cliente(evento, nome_cliente, numero_processo=None):
    """Monta a mensagem. Devolve (texto, problemas).

    `problemas` nao vazio = o texto NAO vai ao lote (a GJ escreve a mao).
    """
    if evento not in EVENTOS:
        return None, [f'evento nao reconhecido: {evento}']
    e = EVENTOS[evento]
    saudacao = tratamento(nome_cliente)
    partes = [
        f'{saudacao}, tudo bem? Aqui é do escritório Maldonado Advogados.',
        f'Temos novidade no seu processo: {e["aconteceu"]}.',
        f'O que estamos fazendo: {e["fazemos"]}.',
        f'O que precisa da sua parte: {e["cliente"]}.',
        'Qualquer dúvida, é só responder esta mensagem.',
    ]
    texto = '\n\n'.join(partes)
    return texto, varrer_juridiques(texto)


# ============================================================
#  4. CONTATO DO CLIENTE
# ============================================================
#  O Atende Direito (CRM) e' a fonte que a Dra. Juliana indicou, mas em
#  30/09/2026 ATENDE_DIREITO_BASE_URL e o token estao VAZIOS no config/.env e o
#  modulo nao tem funcao de envio. O telefone ja esta' no cadastro do ADVBOX,
#  entao a rotina usa o ADVBOX e registra a origem — quando as credenciais do
#  Atende Direito chegarem, ele entra na frente, sem mudar o resto do fluxo.

def contato_do_cliente(cliente_id, advbox=None):
    """Devolve (numero, origem, aviso). `numero` None quando nao ha contato."""
    if advbox is None:
        import advbox_integration as advbox
    try:
        cad = advbox.obter_cliente(cliente_id) or {}
    except Exception as erro:
        return None, None, f'nao consegui ler o cadastro no ADVBOX ({erro})'
    for campo in ('cellphone', 'phone'):
        valor = (cad.get(campo) or '').strip()
        digitos = re.sub(r'\D', '', valor)
        if len(digitos) >= 10:
            return valor, f'ADVBOX/{campo}', None
    return None, None, 'cliente sem telefone no cadastro do ADVBOX — CS atualiza o cadastro'


def contato_atende_direito_disponivel():
    """O CRM esta' configurado? Sem isso a origem do contato e' o ADVBOX."""
    return bool(os.getenv('ATENDE_DIREITO_BASE_URL') and os.getenv('ATENDE_DIREITO_API_TOKEN'))


# ============================================================
#  5. AUTOTESTE
# ============================================================

def _autoteste():
    falhas = []

    # 5.1 - todo texto de EVENTOS tem de passar limpo pela varredura. E' o
    # teste que impede alguem de escrever "tutela deferida" num evento novo.
    for evento in EVENTOS:
        texto, problemas = texto_para_cliente(evento, 'JOAO DA SILVA PEREIRA')
        if problemas:
            falhas.append(f'  {evento}: juridiques no texto -> {problemas}')
        if texto and len(texto) > 700:
            falhas.append(f'  {evento}: texto longo demais ({len(texto)} caracteres)')

    # 5.1b - nenhum texto pode tratar o cliente por genero (nome nao diz genero)
    GENERADAS = ('o senhor', 'a senhora', 'ao senhor', 'a sra', 'o sr',
                 'prezado', 'prezada', 'caro cliente', 'cara cliente')
    for evento in EVENTOS:
        texto, _ = texto_para_cliente(evento, 'FULANA DE TAL')
        plano = _sem_acento(texto or '')
        for g in GENERADAS:
            if _sem_acento(g) in plano:
                falhas.append(f'  {evento}: trata o cliente por genero ({g!r})')

    # 5.2 - a varredura tem de PEGAR juridiques de verdade
    casos_pegar = [
        ('O juiz deferiu a tutela de urgencia.', ['tutela']),
        ('Nos termos do art. 300 do CPC, a liminar foi concedida.', ['liminar']),
        ('A acao foi julgada procedente.', ['procedente']),
        ('Houve descaracterizacao da mora.', ['mora']),
    ]
    for texto, esperado_em in casos_pegar:
        achados = varrer_juridiques(texto)
        if not achados:
            falhas.append(f'  varredura nao pegou nada em: {texto!r}')
        for termo in esperado_em:
            if termo not in achados:
                falhas.append(f'  varredura nao pegou {termo!r} em {texto!r} (achou {achados})')

    # 5.3 - falso positivo: frase limpa nao pode acusar nada
    limpas = [
        'O juiz decidiu a favor do senhor no processo.',
        'Foi marcada uma audiencia no seu processo.',
        'O banco foi avisado e agora tem prazo para responder.',
    ]
    for texto in limpas:
        achados = varrer_juridiques(texto)
        if achados:
            falhas.append(f'  falso positivo em {texto!r}: {achados}')

    # 5.4 - evento desconhecido nao inventa texto
    texto, problemas = texto_para_cliente('evento_que_nao_existe', 'MARIA')
    if texto is not None or not problemas:
        falhas.append('  evento desconhecido deveria devolver (None, [problema])')

    # 5.5 - tratamento nao inventa genero
    if tratamento('MARIA DAS DORES') != 'Maria':
        falhas.append('  tratamento deveria usar o primeiro nome, sem titulo')

    print(f'  eventos: {len(EVENTOS)} | termos proibidos: {len(TERMOS_PROIBIDOS)} | '
          f'motivos de nao-envio: {len(SEM_MENSAGEM)}')
    print(f'  Atende Direito configurado: {contato_atende_direito_disponivel()} '
          f'(sem ele, contato sai do ADVBOX)')
    if falhas:
        print('  FALHAS:')
        for f in falhas:
            print(f)
        return 1
    print('  todos os casos passaram.')
    return 0


if __name__ == '__main__':
    if '--autoteste' in sys.argv:
        sys.exit(_autoteste())
    print(__doc__)
