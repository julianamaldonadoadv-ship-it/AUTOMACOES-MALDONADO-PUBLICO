# -*- coding: utf-8 -*-
"""
Corretor de acentuação — rede de segurança para texto vindo de LLM
==================================================================

Modelo de linguagem às vezes devolve palavra sem acento ("peticao", "mora
descaracterizada" vira "descaracterizacao"). Numa peça que vai ao PJe isso é
erro de português com o nome do Dr. Renan embaixo. Este módulo é a última
conferência antes de o texto entrar no .docx.

    from acentuacao import corrigir_acentuacao
    texto = corrigir_acentuacao(texto)

    python OPERACIONAL/acentuacao.py minuta.txt        # corrige e imprime
    python OPERACIONAL/acentuacao.py --autoteste       # confere as regras

Origem: adaptado de `OPERACIONAL/agente_operacional/acentuacao.py` do
repositório irmão pabadvogados-hub/alves-carneiro-advogados (mesmo produto
white-label, outro escritório), com duas correções e o vocabulário de dívida
rural somado.

**As duas correções, que importam mais que a lista de palavras:**

1. **Palavra ambígua não entra.** O mapa de origem trazia `esta -> está` e
   `pais -> país` aplicados sem contexto nenhum. O comentário no arquivo dizia
   "cuidado: ver fallback", mas não havia fallback no código: toda ocorrência
   era trocada. Em peça jurídica "esta" é pronome o tempo todo ("esta ação",
   "esta Egrégia Corte") e viraria "está ação". Aqui essas palavras ficam de
   fora — `AMBIGUAS` documenta quais e por quê. Uma correção que erra é pior
   que nenhuma, porque ninguém revisa o que o corretor "já arrumou".

2. **Mapeamento identidade não entra.** O original tinha ~15 entradas do tipo
   `'processo': 'processo'`, que só engordavam a expressão regular sem efeito
   nenhum. `_conferir_mapa()` recusa esse tipo de entrada.

O que este módulo **não** faz: não conjuga, não concorda, não corrige crase.
É troca palavra-a-palavra de forma sem acento por forma acentuada, quando
existe uma só leitura possível.
"""
import re
import sys


# ============================================================
#  Palavras que NÃO entram — a leitura depende do contexto
# ============================================================
#  Cada uma aqui foi considerada e recusada. Mantenha o motivo: é o que impede
#  alguém de "completar a lista" no futuro e reintroduzir o defeito.
AMBIGUAS = {
    'esta':   'pronome ("esta ação") x verbo ("está provado") — em peça, quase sempre pronome',
    'pais':   'plural de pai x país',
    'e':      'conjunção x verbo "é"',
    'so':     'advérbio "só" x substantivo "so" (raro, mas "sol"/"soa" colidem no boundary)',
    'as':     'artigo x crase "às"',
    'a':      'artigo x preposição "à"',
    'para':   'preposição x verbo "pára" (grafia antiga)',
    'pela':   'preposição x "pelá"',
    'secretaria': 'a secretária (pessoa) x a secretaria (setor) — ambos ocorrem no fórum',
    'duvida': 'substantivo "dúvida" x verbo "duvida" — os dois aparecem em peça',
    'critica': 'substantivo "crítica" x verbo "critica"',
    'ha':     'verbo "há" x HECTARE — num escritório de dívida rural, "120 ha" '
              'aparece em cédula, matrícula e laudo o tempo todo',
    'publica': 'adjetivo "pública" x verbo "publica" (o DJEN publica)',
    'juizo':  'NAO e ambigua, fica no mapa — exemplo de entrada que passou',
}
AMBIGUAS.pop('juizo')


# ============================================================
#  Mapa: forma sem acento -> forma acentuada (sempre minúsculo)
# ============================================================
PALAVRAS = {
    # --- processual geral ---
    'acao': 'ação', 'acoes': 'ações',
    'peticao': 'petição', 'peticoes': 'petições',
    'peca': 'peça', 'pecas': 'peças',
    'replica': 'réplica', 'replicas': 'réplicas',
    'treplica': 'tréplica',
    'analise': 'análise', 'analises': 'análises',
    'reanalise': 'reanálise', 'reanalises': 'reanálises',
    'contestacao': 'contestação', 'contestacoes': 'contestações',
    'manifestacao': 'manifestação', 'manifestacoes': 'manifestações',
    'contrarrazoes': 'contrarrazões', 'razoes': 'razões', 'razao': 'razão',
    'decisao': 'decisão', 'decisoes': 'decisões',
    'sentenca': 'sentença', 'sentencas': 'sentenças',
    'acordao': 'acórdão', 'acordaos': 'acórdãos',
    'execucao': 'execução', 'execucoes': 'execuções',
    'extincao': 'extinção',
    'citacao': 'citação', 'intimacao': 'intimação', 'intimacoes': 'intimações',
    'notificacao': 'notificação', 'comunicacao': 'comunicação',
    'excecao': 'exceção', 'excecoes': 'exceções',
    'pretensao': 'pretensão', 'pretensoes': 'pretensões',
    'prescricao': 'prescrição', 'decadencia': 'decadência',
    'preliminar': 'preliminar',
    'juizo': 'juízo', 'juizos': 'juízos',
    'audiencia': 'audiência', 'audiencias': 'audiências',
    'competencia': 'competência', 'incompetencia': 'incompetência',
    'ciencia': 'ciência',
    'jurisprudencia': 'jurisprudência', 'jurisprudencias': 'jurisprudências',
    'paragrafo': 'parágrafo', 'paragrafos': 'parágrafos',
    'codigo': 'código', 'codigos': 'códigos',
    'sumula': 'súmula', 'sumulas': 'súmulas',
    'liminar': 'liminar',
    'tutela': 'tutela',
    'agravo': 'agravo',
    'apelacao': 'apelação',
    'embargos': 'embargos',
    'recurso': 'recurso',
    'oficio': 'ofício', 'oficios': 'ofícios',
    'certidao': 'certidão', 'certidoes': 'certidões',
    'peticionamento': 'peticionamento',
    'saneamento': 'saneamento',
    'instrucao': 'instrução',
    'pericia': 'perícia', 'pericias': 'perícias',
    'pericial': 'pericial',
    'quesito': 'quesito', 'quesitos': 'quesitos',
    'preclusao': 'preclusão',
    'sucumbencia': 'sucumbência',
    'honorarios': 'honorários',
    'custas': 'custas',
    'hipossuficiencia': 'hipossuficiência',

    # --- dívida rural bancária (as 4 teses do escritório) ---
    'divida': 'dívida', 'dividas': 'dívidas',
    'credito': 'crédito', 'creditos': 'créditos',
    'debito': 'débito', 'debitos': 'débitos',
    'cedula': 'cédula', 'cedulas': 'cédulas',
    'prorrogacao': 'prorrogação', 'prorrogacoes': 'prorrogações',
    'alongamento': 'alongamento',
    'descaracterizacao': 'descaracterização',
    'caracterizacao': 'caracterização',
    'capitalizacao': 'capitalização',
    'juros': 'juros',
    'encargos': 'encargos',
    'inadimplencia': 'inadimplência',
    'adimplencia': 'adimplência',
    'mora': 'mora',
    'garantia': 'garantia', 'garantias': 'garantias',
    'hipoteca': 'hipoteca',
    'penhor': 'penhor',
    'alienacao': 'alienação',
    'fiduciaria': 'fiduciária', 'fiduciario': 'fiduciário',
    'renegociacao': 'renegociação',
    'financiamento': 'financiamento',
    'safra': 'safra', 'safras': 'safras',
    'produtor': 'produtor',
    'assistencia': 'assistência',
    'tecnica': 'técnica', 'tecnicas': 'técnicas',
    'tecnico': 'técnico', 'tecnicos': 'técnicos',
    'revisional': 'revisional',
    'abusividade': 'abusividade',
    'nulidade': 'nulidade',
    'exigibilidade': 'exigibilidade',
    'inexigibilidade': 'inexigibilidade',
    'restituicao': 'restituição',
    'repeticao': 'repetição',
    'indebito': 'indébito',

    # --- adjetivos e formas em -vel / -rio / -ico ---
    'cabivel': 'cabível', 'cabiveis': 'cabíveis',
    'aplicavel': 'aplicável', 'aplicaveis': 'aplicáveis',
    'inaplicavel': 'inaplicável', 'inaplicaveis': 'inaplicáveis',
    'admissivel': 'admissível', 'inadmissivel': 'inadmissível',
    'possivel': 'possível', 'possiveis': 'possíveis',
    'impossivel': 'impossível', 'impossiveis': 'impossíveis',
    'disponivel': 'disponível', 'disponiveis': 'disponíveis',
    'indisponivel': 'indisponível', 'indisponiveis': 'indisponíveis',
    'responsavel': 'responsável', 'responsaveis': 'responsáveis',
    'provavel': 'provável', 'improvavel': 'improvável',
    'visivel': 'visível', 'irrecorrivel': 'irrecorrível',
    'necessario': 'necessário', 'necessarios': 'necessários',
    'necessaria': 'necessária', 'necessarias': 'necessárias',
    'pecuniario': 'pecuniário', 'pecuniaria': 'pecuniária',
    'proprio': 'próprio', 'propria': 'própria',
    'proprios': 'próprios', 'proprias': 'próprias',
    'generico': 'genérico', 'generica': 'genérica',
    'genericos': 'genéricos', 'genericas': 'genéricas',
    'especifico': 'específico', 'especifica': 'específica',
    'especificos': 'específicos', 'especificas': 'específicas',
    'juridico': 'jurídico', 'juridica': 'jurídica',
    'juridicos': 'jurídicos', 'juridicas': 'jurídicas',
    'fisico': 'físico', 'fisica': 'física',
    'fisicos': 'físicos', 'fisicas': 'físicas',
    'historico': 'histórico', 'historica': 'histórica',
    'historicos': 'históricos', 'historicas': 'históricas',
    'contrario': 'contrário', 'contraria': 'contrária',
    'contrarios': 'contrários', 'contrarias': 'contrárias',

    # --- substantivos frequentes ---
    'exito': 'êxito', 'onus': 'ônus',
    'prejuizo': 'prejuízo', 'prejuizos': 'prejuízos',
    'vinculo': 'vínculo', 'vinculos': 'vínculos',
    'obrigacao': 'obrigação', 'obrigacoes': 'obrigações',
    'condicao': 'condição', 'condicoes': 'condições',
    'relacao': 'relação', 'relacoes': 'relações',
    'aplicacao': 'aplicação', 'aplicacoes': 'aplicações',
    'producao': 'produção', 'producoes': 'produções',
    'apresentacao': 'apresentação',
    'descricao': 'descrição', 'descricoes': 'descrições',
    'observacao': 'observação', 'observacoes': 'observações',
    'violacao': 'violação', 'violacoes': 'violações',
    'resolucao': 'resolução', 'solucao': 'solução',
    'protecao': 'proteção', 'atencao': 'atenção',
    'opcao': 'opção', 'opcoes': 'opções',
    'regiao': 'região', 'regioes': 'regiões',
    'familia': 'família', 'familias': 'famílias',
    'memoria': 'memória', 'historia': 'história',
    'saude': 'saúde', 'industria': 'indústria',
    'comercio': 'comércio', 'socio': 'sócio', 'socios': 'sócios',
    'versao': 'versão', 'versoes': 'versões',

    # --- palavras de ligação sem ambiguidade ---
    'ate': 'até', 'ja': 'já', 'tambem': 'também',
    'nao': 'não', 'sao': 'são', 'entao': 'então',
    'estao': 'estão', 'sera': 'será', 'serao': 'serão',
    'tera': 'terá', 'terao': 'terão', 'havera': 'haverá',
    'alem': 'além', 'apos': 'após', 'atraves': 'através',
    'porem': 'porém', 'ninguem': 'ninguém', 'alguem': 'alguém',
}


def _conferir_mapa():
    """Recusa entrada identidade e palavra que esta' na lista de ambiguas.

    Roda no import: mapa mal formado tem que falhar aqui, e nao no meio de uma
    peca. Custa microssegundos.
    """
    problemas = []
    for sem, com in PALAVRAS.items():
        if sem == com:
            problemas.append(f'identidade inutil no mapa: {sem!r}')
        if sem in AMBIGUAS:
            problemas.append(f'{sem!r} e ambigua ({AMBIGUAS[sem]}) e nao pode estar no mapa')
        if sem != sem.lower():
            problemas.append(f'chave tem que ser minuscula: {sem!r}')
    if problemas:
        raise ValueError('acentuacao.PALAVRAS invalido:\n  - ' + '\n  - '.join(problemas))


# Identidades são úteis para documentar "já conferi, não tem acento", mas não
# no mapa de substituição. Quem quiser registrar isso, use este conjunto:
SEM_ACENTO_CONFERIDAS = {
    'processo', 'processual', 'processuais', 'advogado', 'advocacia',
    'tribunal', 'magistrado', 'sociedade', 'empresa', 'assinatura',
    'conhecimento', 'doutrina', 'responsabilidade', 'terceiros', 'dever',
}
PALAVRAS = {k: v for k, v in PALAVRAS.items() if k != v}
_conferir_mapa()

# Ordena por tamanho decrescente: sem isso, 'acao' casaria dentro de
# 'prorrogacao' e a palavra sairia pela metade.
_CHAVES = sorted(PALAVRAS, key=len, reverse=True)
_PADRAO = re.compile(r'\b(' + '|'.join(re.escape(k) for k in _CHAVES) + r')\b',
                     flags=re.IGNORECASE)


# ============================================================
#  Proteção de código: o que NÃO é prosa não pode ser acentuado
# ============================================================
#  Levantado na primeira rodada real sobre os documentos do repositório: o
#  corretor propôs `maldonado-divida-rural` -> "dívida" (identificador YAML de
#  agente) e `main.py drive peca` -> "peça" (comando do CLI). Acentuar
#  qualquer um dos dois quebra o sistema — o agente deixa de carregar, o
#  comando deixa de existir. A versão de origem não tinha essa proteção.
#
#  O mesmo texto, na mesma rodada, apontou "exito negocial" no relatório de
#  KPI — esse é erro de verdade. Ou seja: não dá para desligar o corretor nesses
#  arquivos; é preciso separar prosa de código.
_TRECHOS_PROTEGIDOS = (
    re.compile(r'```.*?```', re.DOTALL),          # bloco de código cercado
    re.compile(r'`[^`\n]+`'),                     # código inline
    re.compile(r'https?://\S+'),                  # URL
    re.compile(r'\b[\w.-]+\.(?:py|sh|md|docx|pdf|json|csv|txt|bat|plist|yml|yaml)\b'),
    re.compile(r'\b\w+(?:_\w+)+\b'),               # snake_case
    re.compile(r'\b\w+(?:/\w+)+\b'),               # caminho/de/pasta
    re.compile(r'\b\w+(?:-\w+){2,}\b'),            # kebab-com-tres-ou-mais (nome de agente/skill)
)


def _mascarar(texto):
    """Troca trecho de codigo por marcador antes de corrigir. Devolve (texto, mapa)."""
    guardados = []

    def guardar(m):
        guardados.append(m.group(0))
        # Marcador sem letra acentuavel e sem \b interno, para o corretor ignorar.
        return f'\x00{len(guardados) - 1}\x00'

    for padrao in _TRECHOS_PROTEGIDOS:
        texto = padrao.sub(guardar, texto)
    return texto, guardados


def _restaurar(texto, guardados):
    for i, original in enumerate(guardados):
        texto = texto.replace(f'\x00{i}\x00', original)
    return texto


def _ajustar_caso(original, nova):
    """Preserva MAIUSCULA / Capitalizada / minuscula do original."""
    if original.isupper():
        return nova.upper()
    if original[0].isupper():
        return nova[0].upper() + nova[1:]
    return nova


def corrigir_acentuacao(texto, proteger_codigo=True):
    """Troca a forma sem acento pela acentuada, palavra inteira, preservando o caso.

    Só troca o que tem leitura única (ver AMBIGUAS) e, por padrão, só em prosa:
    código, caminho, URL e identificador ficam intocados (ver
    _TRECHOS_PROTEGIDOS). Devolve o texto como veio se ele for vazio ou None.

    `proteger_codigo=False` só para texto que você sabe ser 100% prosa.
    """
    if not texto:
        return texto
    guardados = []
    if proteger_codigo:
        texto, guardados = _mascarar(texto)
    texto = _PADRAO.sub(lambda m: _ajustar_caso(m.group(0), PALAVRAS[m.group(0).lower()]),
                        texto)
    return _restaurar(texto, guardados) if guardados else texto


def diferencas(texto, proteger_codigo=True):
    """Lista o que `corrigir_acentuacao` mudaria: [(original, corrigida), ...].

    Serve para conferir antes de aplicar — numa peça pronta, ver a lista vale
    mais que ver o texto corrigido.
    """
    vistas = []
    if proteger_codigo:
        texto, _ = _mascarar(texto or '')
    for m in _PADRAO.finditer(texto or ''):
        orig = m.group(0)
        nova = _ajustar_caso(orig, PALAVRAS[orig.lower()])
        if orig != nova:
            vistas.append((orig, nova))
    return vistas


def _autoteste():
    casos = [
        ('A peticao inicial sera protocolada.', 'A petição inicial será protocolada.'),
        ('PETICAO INICIAL', 'PETIÇÃO INICIAL'),
        ('Peticao', 'Petição'),
        ('prorrogacao da divida rural', 'prorrogação da dívida rural'),
        ('descaracterizacao da mora', 'descaracterização da mora'),
        ('a cedula de credito rural', 'a cédula de crédito rural'),
        ('acao revisional', 'ação revisional'),
        # "ha" fica intocado de proposito: em divida rural e' hectare (ver AMBIGUAS)
        ('nao ha juros sobre 120 ha', 'não ha juros sobre 120 ha'),
        ('', ''),
        # Codigo e identificador ficam intocados (a razao de _TRECHOS_PROTEGIDOS):
        ('rode `main.py drive peca` para a peca', 'rode `main.py drive peca` para a peça'),
        ('o agente maldonado-divida-rural trata da divida',
         'o agente maldonado-divida-rural trata da dívida'),
        ('veja OPERACIONAL/triagem_divida_rural.py sobre a divida',
         'veja OPERACIONAL/triagem_divida_rural.py sobre a dívida'),
        ('arquivo peticao.docx e a peticao', 'arquivo peticao.docx e a petição'),
    ]
    # O que NAO pode mudar: as ambiguas e o que ja' esta' certo.
    intocaveis = [
        'esta acao',            # 'esta' fica; 'acao' vira 'ação'
        'os pais do autor',
        'a peticao ja esta correta',
    ]
    falhas = []
    for entrada, esperado in casos:
        saida = corrigir_acentuacao(entrada)
        if saida != esperado:
            falhas.append(f'  {entrada!r}\n    esperado: {esperado!r}\n    obtido:   {saida!r}')
    for t in intocaveis:
        saida = corrigir_acentuacao(t)
        for palavra in AMBIGUAS:
            if re.search(r'\b' + palavra + r'\b', t, re.IGNORECASE):
                if palavra not in saida.lower():
                    falhas.append(f'  palavra ambigua {palavra!r} foi alterada em {t!r} -> {saida!r}')
    print(f'  mapa: {len(PALAVRAS)} palavras | ambiguas recusadas: {len(AMBIGUAS)}')
    if falhas:
        print('  FALHAS:'); [print(f) for f in falhas]
        return 1
    print(f'  {len(casos) + len(intocaveis)} casos passaram.')
    return 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)
    if args[0] == '--autoteste':
        sys.exit(_autoteste())
    with open(args[0], encoding='utf-8') as fh:
        texto = fh.read()
    mudancas = diferencas(texto)
    if '--listar' in args:
        for a, b in mudancas:
            print(f'{a}  ->  {b}')
        print(f'\n  {len(mudancas)} correcao(oes).')
    else:
        sys.stdout.write(corrigir_acentuacao(texto))
