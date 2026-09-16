# -*- coding: utf-8 -*-
"""Gera a PETIÇÃO PERFEITA de ALONGAMENTO / PRORROGAÇÃO DE DÍVIDA RURAL.

    ./.venv/bin/python OPERACIONAL/gerar_modelo_alongamento.py

O .docx é artefato; **este script é a fonte versionada** (mesma lógica do
`gerar_modelo_declaratoria.py`). Para alterar o modelo, altere aqui e regenere.

De onde vem cada coisa (13/09/2026):

* **Devolutiva da Gerência Jurídica (Dra. Juliana, 08/08/2026)** — os três ajustes
  pendentes do modelo antigo: (1) tópico de ATER com a análise técnica do pedido
  e o requerimento de exibição do parecer ou declaração de inexistência; (2)
  orientação para provar o pedido administrativo por qualquer meio; (3) objeto
  delimitado sem conteúdo revisional.
* **Dr. Rogério Augusto da Silva (livros de congresso, OCR conferido por página)**
  — peça com sumário e argumentos numerados; objetivo inicial é a SUSPENSÃO DA
  EXIGIBILIDADE, não a prorrogação imediata; tutela cautelar; pedido expresso de
  SCR/SICOR; prorrogação ≠ renegociação; requisitos do MCR não cumulativos.
* **Conferência normativa do dia** — MCR nº 758 no vault (2-6-4 com a redação da
  Res. CMN 5.314; 2-6-11/12; 10-1-25/27; 11-1-4; 1-1-1; 1-3-1 a 1-3-5; 2-7-1),
  CPC no vault, e leis federais no Planalto: Lei 4.829/65 arts. 4º, 10 e 14;
  Lei 8.171/91 art. 50; **DL 167/67 art. 62** (prorrogação "ainda que efetuada
  após o vencimento original"); CC arts. 187, 396 e 422.

Guard-rails que o script materializa (não desfazer):

* **Nenhuma lei federal cria sozinha o direito à prorrogação.** A âncora é a
  delegação ao CMN (Lei 4.829, arts. 4º e 14) que dá força ao MCR 2-6-4, somada
  à Súmula 298/STJ. Não citar CC 317/478, Lei 8.171 art. 104 nem DL 167 art. 13
  como fonte de direito do devedor: os textos não dizem isso.
* **Tutela da evidência do art. 311, II, NÃO cabe aqui:** exige tese de casos
  repetitivos ou súmula vinculante, e a Súmula 298/STJ não é nenhuma das duas.
  A via é a cautelar (arts. 300 e 301), com o pedido principal formulado
  conjuntamente (art. 308, § 1º).
* **Tempestividade depende da linha de crédito e da data do fato** — ver
  `BASE_CONHECIMENTO/00 - TEMAS/Tempestividade-Pedido-Prorrogacao.md`. A peça traz
  os dois caminhos (houve pedido antes do vencimento × não houve) e o advogado
  apaga um.
* **Precedente só entra com identificação conferida** no acervo (bloco
  PRECEDENTES abaixo). O que não foi conferido sai em amarelo como [[CONFERIR]].
"""

import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from OPERACIONAL import visual_law as vl  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMBRADO = os.path.join(RAIZ, "DOCS_MODELOS", "timbrado_modelo.docx")
SAIDA = os.path.join(RAIZ, "DOCS_MODELOS", "MODELO_ALONGAMENTO_DIVIDA_RURAL.docx")

# Fases da linha do tempo desta ação: o que importa é a posição de cada evento em
# relação ao VENCIMENTO, porque é isso que decide qual dos dois caminhos do
# tópico III.2 se aplica.
FASE_ANTES = ("ANTES DO VENCIMENTO", vl.VERDE)
FASE_DEPOIS = ("APÓS O VENCIMENTO", vl.SALMAO)

MCR_NORMA = ("MANUAL DE CRÉDITO RURAL · NORMA DO CONSELHO MONETÁRIO NACIONAL", vl.AZUL, vl.AZUL_CLARO)
LEI_FEDERAL = ("LEI FEDERAL", vl.AZUL, vl.AZUL_CLARO)
# vl.TRIBUNAL diz "TRIBUNAL DE ORIGEM" e só serve para julgado do tribunal que vai
# julgar a causa. Julgado de outro TJ/TRF é persuasivo e precisa dizer isso: tarja
# errada é o tipo de imprecisão que o banco explora e o juízo nota.
PERSUASIVO = ("OUTRO TRIBUNAL · JURISPRUDÊNCIA PERSUASIVA", vl.LARANJA_ESCURO, vl.SALMAO)
# Julgado do TJRO: "tribunal de origem" só quando a ação corre na Justiça Estadual de RO.
# Em ação contra a CEF (Justiça Federal/TRF1) a tarja tem de ser trocada por PERSUASIVO.
TJRO_LOCAL = ("TJRO · TRIBUNAL DE ORIGEM", vl.LARANJA_ESCURO, vl.SALMAO)

# ---------------------------------------------------------------------------
# PROVAS — a peça é contada pelas provas (pedido da Dra. Juliana, 13/09/2026)
#
# "O que o juiz quer ver quando abre o processo são as provas." Cada item vira um
# `visual_law.bloco_prova` (moldura, recorte grifado, transcrição, o que prova),
# uma linha do índice de provas e uma entrada na ficha
# DOCS_MODELOS/MODELO_ALONGAMENTO_DIVIDA_RURAL.provas.json, que diz à automação de
# anexos (`anexos_inicial.recortar` + `inserir_recorte`) qual documento procurar
# (`tipo_documento` = slug do módulo), onde recortar (`buscar`) e o que grifar
# (`grifar`). Os termos de busca e de grifo são PONTO DE PARTIDA: o formulário de
# cada banco muda e o advogado confere contra o documento real.
#
# Calibragem: cada grupo responde a um motivo real de derrota do diagnóstico
# (laudo unilateral 31/61, pedido pós-vencimento 16/61, capacidade de pagamento
# 12/61, natureza rural 17/61, perigo genérico 6/61).
# ---------------------------------------------------------------------------
PROVAS = [
    # --- A operação ---------------------------------------------------------
    dict(numero=1, secao="operacao", tipo_documento="cedula",
         titulo="A cédula: programa, fonte de recursos e finalidade",
         documento="Cédula rural · Doc. [[nº]], fl. [[…]]",
         requisito="Enquadramento da linha · III.1-A e III.2",
         demonstra="Linha de crédito, fonte de recursos e finalidade rural da operação",
         recortar="faixa de largura total com os quadros de composição do crédito e de destinação (programa, "
                  "fonte de recursos, finalidade, atividade)",
         buscar=["Programa", "Fonte de Recurso", "Finalidade"],
         grifar=["PRONAMP", "PRONAF", "Custeio", "Investimento", "OBRIGATÓRIOS"],
         largura_total=True,
         o_que_prova="A operação é crédito rural pela literalidade do título: programa [[…]], recursos [[…]], "
                     "finalidade [[…]]. É esse enquadramento que define o regime de prorrogação aplicável "
                     "(tópico III.2) e afasta a tese de crédito comum."),
    dict(numero=2, secao="operacao", tipo_documento="cedula",
         titulo="O vencimento e o cronograma de reembolso",
         documento="Cédula rural · Doc. [[nº]], fl. [[…]]",
         requisito="Data do vencimento · linha do tempo · III.2",
         demonstra="Data de vencimento contratada, que define se o pedido foi antes ou depois",
         recortar="quadro do cronograma de reembolso e campo de vencimento",
         buscar=["CRONOGRAMA DE REEMBOLSO", "VENCIMENTO"],
         grifar=["VENCIMENTO"],
         largura_total=True,
         o_que_prova="O vencimento contratado é [[dd/mm/aaaa]]. É a data de referência da linha do tempo: o "
                     "pedido de prorrogação (Provas 16 e 17) foi feito [[antes / depois]] dela."),
    dict(numero=3, secao="operacao", tipo_documento="cedula",
         titulo="As garantias que continuam protegendo o banco",
         documento="Cédula rural · Doc. [[nº]], fl. [[…]]",
         requisito="Reversibilidade e caução · IV",
         demonstra="Garantias reais que permanecem íntegras durante a suspensão",
         recortar="quadro de garantias com espécie, bem e valor",
         buscar=["GARANTIA"],
         grifar=["Penhor", "Hipoteca", "TOTAL GARANTIDO"],
         largura_total=True,
         o_que_prova="O crédito do réu está garantido por [[penhor de (…) e hipoteca de (…)]], no total de R$ "
                     "[[…]]. A suspensão da exigibilidade não atinge essas garantias: a medida é reversível e "
                     "dispensa caução (art. 300, § 1º, do CPC)."),
    dict(numero=4, secao="operacao", tipo_documento="cedula",
         titulo="A assistência técnica pactuada",
         documento="Cédula rural · Doc. [[nº]], fl. [[…]]",
         requisito="Análise técnica e exibição · III.4 e V",
         demonstra="Qual assistência técnica o próprio título previu",
         recortar="campo de assistência técnica (plano simples, projeto técnico, nível de imóvel, empresa)",
         buscar=["ASSISTÊNCIA TÉCNICA"],
         grifar=["Plano Simples", "Projeto Técnico", "Nível de Imóvel"],
         largura_total=True,
         o_que_prova="O título prevê [[plano simples / projeto técnico / assistência em nível de imóvel]] a "
                     "cargo de [[empresa]]. É esse o documento técnico que o réu tem de exibir, ou declarar "
                     "inexistente (tópico V)."),
    dict(numero=5, secao="operacao", tipo_documento="aditivo", condicional="houve prorrogação ou renegociação "
         "administrativa anterior (aditivo, boleto de entrada, novo vencimento)",
         titulo="A prorrogação anterior concedida pelo próprio banco",
         documento="Aditivo / boleto de entrada · Doc. [[nº]]",
         requisito="Tempestividade pelo vencimento renegociado · III.2",
         demonstra="O banco já reconheceu a dificuldade e fixou novo vencimento",
         recortar="campo do novo vencimento e data do pagamento ou da assinatura",
         buscar=["vencimento", "prorroga"],
         grifar=["vencimento", "prorrogação"],
         o_que_prova="Em [[data]], o próprio réu prorrogou a operação para [[novo vencimento]], [[inclusive "
                     "depois do vencimento original]]. A dificuldade foi reconhecida pelo credor, e a "
                     "tempestividade se mede pelo vencimento renegociado."),
    # --- O evento adverso --------------------------------------------------
    dict(numero=6, secao="evento", tipo_documento="decreto-emergencia",
         titulo="O decreto que reconheceu a situação de emergência",
         documento="Decreto nº [[…]] · Doc. [[nº]]",
         requisito="Evento adverso oficial · MCR 2-6-4, \"b\" ou \"c\"",
         demonstra="Evento adverso reconhecido pelo Poder Público, com período e área",
         recortar="ementa e artigo que declara a emergência, com data e municípios abrangidos",
         buscar=["situação de emergência", "Art. 1"],
         grifar=["situação de emergência", "estiagem"],
         o_que_prova="O Poder Público declarou situação de emergência por [[evento]] em [[área]], de [[…]] a "
                     "[[…]]. Fato notório (art. 374, I, do CPC), com teor e vigência comprovados (art. 376)."),
    dict(numero=7, secao="evento", tipo_documento="clima",
         titulo="A medição oficial do evento",
         documento="INMET / índice de vegetação (NDVI) · Doc. [[nº]]",
         requisito="Intensidade do evento · III.3",
         demonstra="Chuva, temperatura ou vigor da vegetação fora da média no período",
         recortar="gráfico ou tabela da estação mais próxima (ou mapa NDVI) com o período e a média histórica",
         buscar=["precipitação", "mm"],
         grifar=["precipitação", "média"],
         o_que_prova="A precipitação em [[período]] foi de [[… mm]], contra média de [[… mm]]. É prova que não vem "
                     "do autor e corrobora o laudo — o reforço que faltou nas decisões que chamaram o laudo "
                     "de unilateral."),
    dict(numero=8, secao="evento", tipo_documento="cotacao",
         titulo="A queda do preço do produto",
         documento="Cotação oficial (CEPEA/CONAB) · Doc. [[nº]]",
         requisito="Dificuldade de comercialização · MCR 2-6-4, \"a\"",
         demonstra="Queda do preço de venda entre a contratação e a comercialização",
         recortar="série de preços com o valor na contratação e no período de venda",
         buscar=["arroba", "saca"],
         grifar=["R$"],
         o_que_prova="O preço de [[produto]] caiu de R$ [[…]] em [[data]] para R$ [[…]] em [[data]], queda de "
                     "[[…%]]: dificuldade de comercialização, hipótese da alínea \"a\" do MCR 2-6-4."),
    dict(numero=9, secao="evento", tipo_documento=None, foto=True,
         titulo="O evento na propriedade do autor",
         documento="Fotografias com data e localização · Doc. [[nº]]",
         requisito="Efeito concreto do evento · III.3",
         demonstra="Pastagem, lavoura ou rebanho atingidos, na própria propriedade",
         recortar="uma a três fotos com data e coordenadas visíveis (metadado ou carimbo), sem edição",
         buscar=[], grifar=[],
         transcrever="data, local/coordenadas e o que a foto mostra, sem adjetivo",
         o_que_prova="As fotos de [[data]], na propriedade [[…]], mostram [[pasto seco / lavoura perdida / "
                     "rebanho magro]]: o evento oficial atingiu a atividade do autor."),
    # --- O laudo de perda --------------------------------------------------
    dict(numero=10, secao="laudo", tipo_documento="laudo-agronomico",
         titulo="Quem assina o laudo: habilitação, ART e visita",
         documento="Laudo de perda · Doc. [[nº]], fl. [[…]]",
         requisito="Idoneidade da prova técnica · arg. 7",
         demonstra="Engenheiro agrônomo habilitado, com ART e visita à propriedade",
         recortar="identificação do responsável técnico, número de registro, ART e data da vistoria",
         buscar=["ART", "CREA", "vistoria"],
         grifar=["ART", "CREA", "vistoria"],
         o_que_prova="O laudo é de [[nome]], engenheiro agrônomo, CREA [[…]], ART [[…]], com visita à "
                     "propriedade em [[data]]: prova técnica idônea para a cognição sumária."),
    dict(numero=11, secao="laudo", tipo_documento="laudo-agronomico",
         titulo="Produção esperada × obtida, por safra e por operação",
         documento="Laudo de perda · Doc. [[nº]], fl. [[…]]",
         requisito="Frustração quantificada · MCR 2-6-4, \"b\"",
         demonstra="A perda medida na propriedade, safra a safra e operação a operação",
         recortar="quadro comparativo de produção ou receita esperada e obtida",
         buscar=["esperada", "obtida"],
         grifar=["esperada", "obtida", "perda"],
         largura_total=True,
         o_que_prova="A produção esperada era [[…]] e a obtida foi [[…]], perda de [[…%]] em [[safra/operação]]. "
                     "Individualizado por operação, é o dado que as decisões desfavoráveis disseram faltar."),
    dict(numero=12, secao="laudo", tipo_documento="laudo-agronomico",
         titulo="Redução de renda e nexo com o evento",
         documento="Laudo de perda · Doc. [[nº]], fl. [[…]]",
         requisito="Intensidade e % de redução · MCR 2-6-12 \"d\" / 10-1-27 \"d\"",
         demonstra="Percentual de redução de renda causado pelo evento adverso",
         recortar="conclusão do laudo com o percentual de redução de renda e a causa",
         buscar=["conclusão", "redução"],
         grifar=["redução", "renda"],
         o_que_prova="O laudo conclui por redução de [[…%]] da renda esperada, causada por [[evento]], com "
                     "recuperação estimada em [[…]]: exatamente as informações técnicas que o MCR manda "
                     "apresentar ao banco."),
    # --- A capacidade de pagamento ------------------------------------------
    dict(numero=13, secao="capacidade", tipo_documento="laudo-agronomico",
         titulo="O fluxo de caixa projetado",
         documento="Laudo de capacidade de pagamento · Doc. [[nº]], fl. [[…]]",
         requisito="Dificuldade TEMPORÁRIA · MCR 2-6-4",
         demonstra="A renda da atividade volta a cobrir a dívida no cronograma pedido",
         recortar="tabela de receitas, custos e saldo disponível por ano",
         buscar=["receita", "custo"],
         grifar=["saldo", "disponível"],
         largura_total=True,
         o_que_prova="A projeção mostra saldo disponível de R$ [[…]] a partir de [[ano]]: a dificuldade é "
                     "temporária, e não insolvência estrutural."),
    dict(numero=14, secao="capacidade", tipo_documento="laudo-agronomico",
         titulo="O cronograma proposto: carência e parcelas",
         documento="Laudo de capacidade de pagamento · Doc. [[nº]], fl. [[…]]",
         requisito="Pedido principal \"h\" · teto da linha",
         demonstra="Carência, número e valor das parcelas que o autor consegue pagar",
         recortar="quadro do cronograma de amortização",
         buscar=["carência", "parcela"],
         grifar=["carência", "parcela"],
         largura_total=True,
         o_que_prova="O laudo propõe carência de [[…]] e [[…]] parcelas de R$ [[…]], dentro do limite do MCR "
                     "para a linha [[…]]. É o cronograma do pedido \"h\"."),
    dict(numero=15, secao="capacidade", tipo_documento="laudo-agronomico",
         titulo="O endividamento total declarado e a conclusão de viabilidade",
         documento="Laudo de capacidade de pagamento · Doc. [[nº]], fl. [[…]]",
         requisito="Transparência do passivo · III.3",
         demonstra="Todas as dívidas do autor consideradas, e a conclusão de viabilidade",
         recortar="quadro do endividamento total e parágrafo de conclusão",
         buscar=["endividamento", "conclusão"],
         grifar=["endividamento", "capacidade de pagamento"],
         o_que_prova="O laudo considera todo o passivo do autor, R$ [[…]] em [[…]] credores, e ainda assim "
                     "conclui pela viabilidade do cronograma. Endividamento escondido derrubou tutelas; declarado, "
                     "reforça a credibilidade."),
    # --- O pedido ao banco -------------------------------------------------
    dict(numero=16, secao="pedido", tipo_documento="requerimento-banco",
         titulo="O pedido escrito de prorrogação, com os laudos anexos",
         documento="Requerimento ao banco · Doc. [[nº]]",
         requisito="Solicitação do mutuário · MCR 2-6-4 · III.2",
         demonstra="O pedido, sua data e os laudos que o acompanharam",
         recortar="cabeçalho com data e destinatário, o parágrafo do pedido e a lista de anexos",
         buscar=["prorrogação", "anexo"],
         grifar=["prorrogação", "laudo", "anexo"],
         o_que_prova="Em [[data]], o autor pediu por escrito a prorrogação das operações [[nº]], anexando os "
                     "laudos de perda e de capacidade de pagamento. O banco teve diante de si tudo o que o MCR "
                     "exige para decidir."),
    dict(numero=17, secao="pedido", tipo_documento="requerimento-banco",
         titulo="A prova de que o banco recebeu",
         documento="AR / confirmação de leitura / protocolo · Doc. [[nº]]",
         requisito="Tempestividade · linha do tempo",
         demonstra="Data do recebimento pelo banco, antes do vencimento",
         recortar="data e assinatura do AR, confirmação de leitura do e-mail ou carimbo de protocolo",
         buscar=["recebido", "protocolo"],
         grifar=["recebido", "data"],
         o_que_prova="O réu recebeu o pedido em [[data]], [[… dias]] antes do vencimento de [[data]]. Pedido "
                     "sem prova de recebimento foi desconsiderado nas decisões lidas."),
    dict(numero=18, secao="pedido", tipo_documento="negativa-banco",
         titulo="A resposta do banco, ou o silêncio",
         documento="Resposta do banco / declaração de ausência de resposta · Doc. [[nº]]",
         requisito="Negativa sem análise técnica · III.4",
         demonstra="Negativa sem parecer técnico, proposta fora do MCR ou silêncio",
         recortar="a resposta inteira com data e assinante; se houve silêncio, o registro de reiteração sem "
                  "resposta",
         buscar=["prorrogação", "não"],
         grifar=["indeferido", "entrada", "política"],
         o_que_prova="[[Em (…), o réu negou por manifestação de (…), sem parecer técnico / exigiu entrada de "
                     "(…)%, o que não é prorrogação / não respondeu até hoje, apesar da reiteração de (…)]]. "
                     "Não houve a análise que o MCR 2-6-4 impõe ao banco."),
    dict(numero=19, secao="pedido", tipo_documento="requerimento-banco", condicional="houver conversa com "
         "o gerente ou assessor agro (WhatsApp, e-mail, áudio transcrito)",
         titulo="A conversa com o gerente (reforço)",
         documento="Mensagens / e-mail · Doc. [[nº]]",
         requisito="Confissão extrajudicial · CPC 389 e 422, § 3º",
         demonstra="O banco sabia da dificuldade e do pedido",
         recortar="a conversa com número/identificação do gerente, datas e horas visíveis",
         buscar=["prorroga"],
         grifar=["prorrogação", "sistema", "não"],
         o_que_prova="Em [[data]], o gerente [[nome]] [[reconheceu o pedido / informou que (…)]]. É reforço do "
                     "pedido escrito, não substituto dele."),
    # --- Aplicação e produção ----------------------------------------------
    dict(numero=20, secao="aplicacao", tipo_documento="producao",
         titulo="A aplicação do crédito na atividade",
         documento="Notas fiscais / GTA · Doc. [[nº]]",
         requisito="Destinação rural · Lei 4.829, art. 2º · III.1-A",
         demonstra="O dinheiro foi aplicado em insumos, animais ou serviços da atividade",
         recortar="as notas fiscais principais, com data, emitente, produto e valor",
         buscar=["NOTA FISCAL"],
         grifar=["Valor", "Descrição"],
         o_que_prova="O crédito foi aplicado em [[insumos/animais]] no valor de R$ [[…]], em [[datas]]: "
                     "destinação rural comprovada, que responde à tese de crédito comum ou de recursos próprios."),
    dict(numero=21, secao="aplicacao", tipo_documento="producao",
         titulo="A produção e sua evolução",
         documento="Ficha IDARON/ADERR / declaração de produção / DIRPF · Doc. [[nº]]",
         requisito="Atividade e queda da produção · III.3",
         demonstra="Rebanho ou produção antes e depois do evento",
         recortar="saldo de rebanho ou produção declarada em dois períodos",
         buscar=["saldo", "rebanho"],
         grifar=["saldo", "total"],
         o_que_prova="O rebanho/produção passou de [[…]] em [[data]] para [[…]] em [[data]]: documento de "
                     "órgão público que confirma o laudo."),
    # --- A ameaça concreta -------------------------------------------------
    dict(numero=22, secao="ameaca", tipo_documento="negativacao",
         titulo="A restrição cadastral já lançada ou anunciada",
         documento="SERASA / SPC / SCR (Registrato) · Doc. [[nº]]",
         requisito="Perigo de dano concreto · IV",
         demonstra="Negativação datada, inclusive no SCR do Banco Central",
         recortar="a anotação com credor, valor e data",
         buscar=["inclusão", "pendência"],
         grifar=["data", "valor"],
         o_que_prova="Em [[data]], o réu [[incluiu / anunciou a inclusão de]] o nome do autor em [[cadastro]], "
                     "o que fecha o crédito do próximo ciclo."),
    dict(numero=23, secao="ameaca", tipo_documento="processo",
         titulo="A cobrança, a execução ou o leilão",
         documento="Notificação de vencimento antecipado / execução / edital · Doc. [[nº]]",
         requisito="Perigo datado sobre o patrimônio produtivo · IV",
         demonstra="Ato de cobrança com data e bem ameaçado",
         recortar="o ato com número, data e bens atingidos",
         buscar=["execução", "leilão", "vencimento antecipado"],
         grifar=["data", "penhora", "leilão"],
         o_que_prova="[[Em (…), o réu ajuizou a execução nº (…) / designou leilão para (…) / notificou o "
                     "vencimento antecipado]], atingindo [[bem]], que é o próprio instrumento da produção."),
]


# Imagem numerada em sequência na peça (Imagem 01, 02...), não "Doc. [[nº]]": o número do anexo
# no PJe só existe depois do upload, e o advogado tinha de substituir cada referência à mão
# (Dra. Juliana, 15/09/2026). Cada prova do modelo tem um slot de imagem, então Imagem NN = Prova NN;
# em peça com mais de uma imagem por prova, numerar em sequência na ordem de exibição.
for _p in PROVAS:
    _p["documento"] = _p["documento"].replace("Doc. [[nº]]", "Imagem %02d" % _p["numero"])


def _provas(doc, secao):
    """Emite os blocos de prova de uma seção dos fatos."""
    for p in PROVAS:
        if p["secao"] != secao:
            continue
        if p.get("condicional"):
            vl.pendencia(doc, "PROVA %02d só entra se %s. Não havendo, apague o bloco e a linha do índice de "
                              "provas." % (p["numero"], p["condicional"]))
        vl.bloco_prova(doc, p["numero"], p["titulo"], p["documento"], p["requisito"], p["recortar"],
                       grifar=p.get("grifar"), transcrever=p.get("transcrever"),
                       o_que_prova=p["o_que_prova"], foto=p.get("foto", False))


SAIDA_PROVAS = os.path.join(RAIZ, "DOCS_MODELOS", "MODELO_ALONGAMENTO_DIVIDA_RURAL.provas.json")


def gravar_ficha_provas():
    """Ficha que a automação de anexos consome para trazer os prints prontos."""
    import json
    ficha = {
        "modelo": os.path.basename(SAIDA),
        "gerado_por": "OPERACIONAL/gerar_modelo_alongamento.py",
        "como_usar": [
            "Para cada prova: localizar na pasta do cliente o arquivo do tipo_documento "
            "(anexos_inicial.classificar_arquivo).",
            "Recortar com anexos_inicial.recortar(caminho, saida, buscar=buscar, realcar=grifar, "
            "largura_total=largura_total).",
            "Inserir com anexos_inicial.inserir_recorte(docx, marcador_imagem, png, legenda=legenda_modelo): "
            "a imagem entra na moldura da prova, com borda fina.",
            "Transcrever o trecho grifado no marcador_texto, lendo o documento — nunca de memória.",
            "Documento inexistente: anexos_inicial.marcar_pendencia ou apagar o bloco e a linha do índice.",
            "Grifo só com a legenda declarando (grifo nosso). Documento original nunca é alterado.",
        ],
        "provas": [],
    }
    for p in PROVAS:
        n = "%02d" % p["numero"]
        ficha["provas"].append({
            "numero": p["numero"], "secao": p["secao"], "titulo": p["titulo"],
            "tipo_documento": p["tipo_documento"], "documento": p["documento"],
            "requisito": p["requisito"], "recortar": p["recortar"],
            "buscar": p.get("buscar") or [], "grifar": p.get("grifar") or [],
            "largura_total": bool(p.get("largura_total")), "foto": bool(p.get("foto")),
            "condicional": p.get("condicional"),
            "marcador_imagem": "[[INSERIR PRINT %s" % n,
            "marcador_texto": "[[TEXTO DO PRINT %s" % n,
            "legenda_modelo": "Imagem %02d. %s, fl. X%s" % (
                p["numero"], p["titulo"], "" if p.get("foto") or not p.get("grifar") else " (grifo nosso)"),
            "legenda_posicao": "acima da imagem",
        })
    with open(SAIDA_PROVAS, "w", encoding="utf-8") as f:
        json.dump(ficha, f, ensure_ascii=False, indent=2)
    return SAIDA_PROVAS


# ---------------------------------------------------------------------------
# PRECEDENTES — único lugar do script com jurisprudência.
# Preenchido com o que o acervo do escritório confirma (identificação completa).
# O que não estiver aqui não entra na peça.
# ---------------------------------------------------------------------------
#
# Critério (13/09/2026): só entra precedente classificado [ALTA] no levantamento
# do acervo — ementa literal na coletânea `jurisprudencia-rural` com número
# completo. Mesmo assim, TODO precedente sai com a marca de conferência do
# inteiro teor antes do protocolo (a coletânea é acervo interno, não o DJ).
# NENHUM precedente do TJRO entra aqui: o acervo só tem síntese, sem íntegra.
# O advogado substitui ou soma o julgado do tribunal que vai julgar a causa.
_CONFERIR = " [[conferir inteiro teor e data de publicação antes do protocolo]]"

PRECEDENTES = {
    "Súmula 298 aplicada pelo tribunal que vai julgar": (
        "Considerando que o alongamento do prazo independe da vontade da instituição financeira, sendo "
        "necessário apenas o atendimento das condições previstas no Manual de Crédito Rural, tendo "
        "restado demonstrado pelo devedor o atendimento aos requisitos previstos no MCR e não havendo "
        "prova dos motivos alegados pela instituição financeira para a negativa do pedido de "
        "alongamento, deve ser reconhecido o direito do devedor à análise da renegociação requerida.",
        "TRF-4, AC 5002286-98.2021.4.04.7106/RS, Rel. Des. Federal Vânia Hack de Almeida, 3ª Turma, "
        "j. 07/03/2023" + _CONFERIR,
        PERSUASIVO),
    "Desnecessidade de requerimento administrativo prévio (STJ)": (
        "2) A comprovação pelo autor de que houve prévio requerimento administrativo para alongamento da "
        "dívida, bem como de sua situação de adimplência junto à instituição demandada, não constitui, a "
        "princípio, condição de procedibilidade para o ajuizamento de ação pela qual se busca o "
        "alongamento de dívida rural (...) 4) A observância ou não das condições estabelecidas pelo Banco "
        "Central do Brasil - BACEN (...) constitui questão a ser resolvida na seara meritória (...).",
        "TJES, AI 0000102-51.2020.8.08.0057, Rel. Des.ª Eliana Junqueira Munhos Ferreira, 3ª Câmara "
        "Cível, j. 02/02/2021, publ. 12/02/2021, que aplica o REsp 1.531.676/MG (STJ, 3ª Turma, Rel. "
        "Min.ª Nancy Andrighi)" + _CONFERIR,
        PERSUASIVO),
    "Desnecessidade de requerimento prévio ou pedido após o vencimento (tribunal local)": (
        "INDEFERIMENTO DA PETIÇÃO INICIAL. IMPOSSIBILIDADE. INTERESSE DE AGIR VERIFICADO. SENTENÇA "
        "CASSADA. (...) NOTIFICAÇÃO EXTRAJUDICIAL, LAUDOS PERICIAIS E PROCURAÇÃO ENVIADOS POR E-MAIL E "
        "CARTA COM AR. (...) NEGATIVA IMPLÍCITA. COMPARECIMENTO PESSOAL DESNECESSÁRIO.",
        "TJPR, Apelação Cível 0006568-19.2024.8.16.0083, Rel. Des. Carlos Mansur Arida, 5ª Câmara Cível, "
        "j. 21/05/2025, publ. 26/05/2025" + _CONFERIR,
        PERSUASIVO),
    "Tempestividade pela obrigação renegociada": (
        "2. Tempestivo o requerimento de prorrogação aferido pelo vencimento da obrigação renegociada, e "
        "não da originária; laudo técnico habilitado basta em cognição sumária.",
        "TJMT, AI 1010134-81.2026.8.11.0000, Rel. Des. Luiz Octávio Oliveira Saboia Ribeiro, 5ª Câmara de "
        "Direito Privado, j. 02/06/2026" + _CONFERIR,
        PERSUASIVO),
    "Pedido por WhatsApp e silêncio do banco": (
        "3. O requerimento administrativo prévio, formalizado por WhatsApp, e-mail, notificação "
        "extrajudicial e protocolo dos formulários do banco antes do vencimento, seguido do silêncio da "
        "instituição, reforça a probabilidade do direito (Súmula 298/STJ e MCR 2.6.4).",
        "TJMT, AI 1024124-42.2026.8.11.0000, Rel. Des. Hélio Nishiyama, 2ª Câmara de Direito Privado, "
        "j. 04/06/2026" + _CONFERIR,
        PERSUASIVO),
    "Laudo técnico particular suficiente em cognição sumária": (
        "ainda que a referida prova tenha sido produzida de forma unilateral e seja passível de "
        "desconstituição no curso da ação, em análise perfunctória, é de reputar preenchido ao menos um "
        "dos requisitos materiais fixados na norma de regência",
        "TJPR, AI 0024107-19.2025.8.16.0000, 16ª Câmara Cível, Rel. Des. José Laurindo de Souza Netto "
        "(Rel. convocada Des.ª Subst. Vania Maria da Silva Kramer), j. 16/07/2025, publ. 18/07/2025, "
        "trecho do voto" + _CONFERIR,
        PERSUASIVO),
    "Tutela cautelar em ação de prorrogação: suspensão da exigibilidade e baixa de restrições": (
        "1.- Suspensa a exigibilidade do crédito por norma legal que faculta o alongamento da dívida "
        "rural, não subsiste a mora. 2. Por conseguinte, ausente a mora do devedor, inviável a inscrição "
        "ou a manutenção de seu nome nos cadastros de inadimplentes.",
        "STJ, AgInt no REsp 1.590.413/SE, Rel. Min.ª Maria Isabel Gallotti, 4ª Turma, j. 14/02/2017, "
        "DJe 21/02/2017" + _CONFERIR,
        vl.STJ),
    "Pendência do litígio sobre alongamento impede negativação (STJ)": (
        "2.- Esta Corte já decidiu que encontrando-se pendente de julgamento o litígio instaurado entre as "
        "partes acerca do alongamento do débito, não se justifica o registro do nome do devedor no CADIN "
        "ou qualquer outro órgão cadastral de proteção ao crédito (REsp 217.629/MG (...)).",
        "STJ, AgRg no REsp 1.228.968/PI, Rel. Min. Sidnei Beneti, 3ª Turma, j. 28/05/2013, DJe "
        "17/06/2013" + _CONFERIR,
        vl.STJ),
    "Cognição sumária: exigir prova exauriente é erro de premissa": (
        "1. Incorre em erro de premissa a decisão que, para deferir tutela de urgência, exige demonstração "
        "robusta e aprofundamento probatório típicos de cognição exauriente, quando o art. 300 do CPC "
        "reclama apenas probabilidade do direito e perigo de dano, não certeza. 2. Laudo pericial, "
        "declarações fiscais e requerimento administrativo previamente formulado e negado constituem "
        "conjunto suficiente para a cognição sumária.",
        "TJDFT, AI 0724412-74.2026.8.07.0000, Rel. Des. Rômulo de Araújo Mendes, Turma Cível, "
        "j. 09/06/2026" + _CONFERIR,
        PERSUASIVO),
    "Natureza rural pela destinação dos recursos": (
        "3. A formalização do contrato por meio de Cédula de Crédito Bancário não descaracteriza, por si "
        "só, a natureza rural da operação, desde que comprovada a destinação dos recursos a atividades "
        "agropecuárias, nos termos do art. 2º da Lei nº 4.829/1965 e do Manual de Crédito Rural.",
        "TJMT, AI 1027855-80.2025.8.11.0000, Rel. Des.ª Anglizey Solivan de Oliveira, 4ª Câmara de "
        "Direito Privado, j. 09/10/2025" + _CONFERIR,
        PERSUASIVO),
    # --- TJRO: texto integral lido e conferido em 13/09/2026 ---------------
    # (acórdãos do PJe 2º grau / DJEN; números omitidos nesta cópia pública)
    "TJRO: direito subjetivo, sem discricionariedade bancária": (
        "Na presença dos requisitos legais, o alongamento da dívida rural é direito subjetivo do devedor, "
        "independentemente de anuência do agente financeiro ou de discricionariedade bancária, devendo o "
        "termo inicial do novo vencimento ser fixado conforme a data de vencimento original do contrato, "
        "observando a Súmula 298/STJ e o Manual de Crédito Rural.",
        "TJRO, Apelação Cível [nº omitido], Rel. Desa. Inês Moreira da Costa, sessão de "
        "29/04/2026, tese de julgamento [[conferir câmara e publicação]]",
        TJRO_LOCAL),
    "TJRO: laudos específicos contra alegação genérica do banco": (
        "Os laudos técnicos juntados Laudo de Frustração de Safra e Laudo de Capacidade de Pagamento são "
        "específicos, individualizados e elaborados por profissional habilitado, demonstrando queda drástica "
        "do preço da arroba, aumento de custos, quebra produtiva e comprometimento severo da receita. A "
        "alegação genérica do Banco não afasta os dados técnicos apresentados, o que afasta o cerceamento de "
        "defesa.",
        "TJRO, Apelação Cível [nº omitido], Rel. Juiz Jorge Gurgel de Amaral, sessão eletrônica "
        "de 09 a 12/12/2025, unânime [[conferir câmara: não consta do texto publicado]]",
        TJRO_LOCAL),
    "TJRO: tutela em cognição sumária com laudo e Súmula 298": (
        "A documentação anexada ao recurso, notadamente o laudo técnico, indica frustração relevante da "
        "atividade pecuária por fatores externos e imprevisíveis, especialmente a desvalorização expressiva do "
        "preço da arroba bovina, o que compromete a capacidade financeira do agravante. A Súmula 298 do STJ "
        "reconhece o direito ao alongamento da dívida rural quando presentes os requisitos legais, sendo "
        "indevida a negativa unilateral da instituição financeira. Embora a verificação definitiva do direito "
        "postulado dependa de instrução probatória, a análise em sede de cognição sumária permite concluir "
        "pela existência de probabilidade do direito e de risco de dano irreparável (...).",
        "TJRO, Agravo de Instrumento [nº omitido], Rel. Des. Isaias Fonseca Moraes, j. "
        "10/10/2025, recurso parcialmente provido [[conferir câmara: 2ª no acórdão, 3ª na autuação do PJe]]",
        TJRO_LOCAL),
}


# ---------------------------------------------------------------------------
# Primitivas locais
# ---------------------------------------------------------------------------
def _centro(doc, texto, negrito=False, tamanho=vl.PT_CORPO, espaco=6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(espaco)
    vl._runs(p, texto, tamanho=tamanho, negrito=negrito)
    return p


def _subtitulo(doc, texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    vl._runs(p, texto, tamanho=vl.PT_CORPO, negrito=True)
    return p


def _argumento(doc, numero, titulo, texto):
    """Argumento numerado, no padrão que o Dr. Rogério descreve como adotado
    pelo relator item a item ([C] p. 89): número e tese em negrito, e a
    explicação em seguida, no mesmo parágrafo."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(6)
    vl._runs(p, "%s. %s " % (numero, titulo), tamanho=vl.PT_CORPO, negrito=True)
    vl._runs(p, texto, tamanho=vl.PT_CORPO)
    return p


def _sumario(doc, itens):
    t = vl._tabela(doc, len(itens) + 1, 2, larguras=[0.10, 0.90])
    c = t.cell(0, 0).merge(t.cell(0, 1))
    vl._escrever(c, "SUMÁRIO", negrito=True, fundo=vl.LARANJA,
                 alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (romano, titulo) in enumerate(itens, start=1):
        vl._escrever(t.cell(i, 0), romano, negrito=True, fundo=vl.CINZA,
                     alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
        vl._escrever(t.cell(i, 1), titulo)
    vl._espaco(doc)
    return t


def _quadro_operacoes(doc):
    cab = ["Título e nº", "Programa e fonte", "Valor", "Vencimento", "Garantias", "Situação"]
    linhas = [
        ["[[Cédula Rural (…) nº (…)]]", "[[PRONAF / PRONAMP / sem programa]]\n[[fonte: obrigatórios, "
         "BNDES, FNO, livres…]]", "R$ [[valor]]", "[[dd/mm/aaaa]]", "[[penhor / hipoteca / aval]]",
         "[[em dia / vencida em …]]"],
        ["[[repetir uma linha por operação]]", "", "", "", "", ""],
    ]
    t = vl._tabela(doc, len(linhas) + 2, 6, larguras=[0.19, 0.21, 0.13, 0.13, 0.17, 0.17])
    c = t.cell(0, 0)
    for j in range(1, 6):
        c = c.merge(t.cell(0, j))
    vl._escrever(c, "AS OPERAÇÕES CUJA PRORROGAÇÃO SE PEDE", negrito=True, fundo=vl.LARANJA,
                 alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for j, txt in enumerate(cab):
        vl._escrever(t.cell(1, j), txt, negrito=True, fundo=vl.CINZA,
                     alinhamento=WD_ALIGN_PARAGRAPH.CENTER, tamanho=vl.PT_ROTULO)
    for i, linha in enumerate(linhas, start=2):
        for j, txt in enumerate(linha):
            vl._escrever(t.cell(i, j), txt, tamanho=vl.PT_ROTULO)
    vl._espaco(doc)
    return t


def _quadro_requisitos(doc):
    """Requisito do MCR 2-6-4 × prova nos autos. É o componente que faz o
    trabalho argumentativo da probabilidade do direito: cada exigência do texno
    normativo ao lado do documento que a satisfaz."""
    linhas = [
        ("Dificuldade TEMPORÁRIA para reembolso", "[[Laudo de capacidade de pagamento: renda projetada que "
         "volta a cobrir a dívida em (…) safras]]", "Provas 13 a 15"),
        ("Ao menos UMA das situações das alíneas \"a\" a \"d\"",
         "[[alínea (…): frustração de safra / dificuldade de comercialização / ocorrência prejudicial / "
         "fluxo de caixa com perdas acumuladas]]", "Provas 08 e 11"),
        ("Evento adverso e sua intensidade", "[[Decreto de emergência nº (…), medição oficial e fotos da "
         "propriedade]]", "Provas 06, 07 e 09"),
        ("Percentual de redução de renda e tempo de recuperação", "[[Laudo: redução de (…)% e recuperação "
         "estimada em (…)]]", "Prova 12"),
        ("Solicitação do mutuário", "[[Pedido escrito de (…), recebido pelo banco em (…); ou tópico III.2, "
         "caminho B]]", "Provas 16 e 17"),
    ]
    t = vl._tabela(doc, len(linhas) + 2, 3, larguras=[0.33, 0.52, 0.15])
    c = t.cell(0, 0).merge(t.cell(0, 1)).merge(t.cell(0, 2))
    vl._escrever(c, "O QUE O MCR 2-6-4 EXIGE DO MUTUÁRIO E ONDE ESTÁ A PROVA", negrito=True,
                 fundo=vl.LARANJA, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for j, txt in enumerate(["Exigência", "Prova nos autos", "Documento"]):
        vl._escrever(t.cell(1, j), txt, negrito=True, fundo=vl.CINZA,
                     alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (req, prova, doc_) in enumerate(linhas, start=2):
        vl._escrever(t.cell(i, 0), req, negrito=True, fundo=vl.AZUL_CLARO)
        vl._escrever(t.cell(i, 1), prova)
        vl._escrever(t.cell(i, 2), doc_, alinhamento=WD_ALIGN_PARAGRAPH.CENTER)
    vl._espaco(doc)
    return t


def _precedente(doc, chave):
    """Insere o precedente do bloco PRECEDENTES ou, se não houver, a pendência."""
    item = PRECEDENTES.get(chave)
    if not item:
        vl.pendencia(doc, "[[CONFERIR]] Precedente para \"%s\": inserir somente julgado com número, "
                          "órgão, relator e data conferidos no acervo (03 - PRECEDENTES) ou no inteiro "
                          "teor. Não completar de memória." % chave)
        return None
    texto, fonte, forca = item
    return vl.precedente(doc, texto, fonte, forca)


# ---------------------------------------------------------------------------
def construir():
    doc = Document(TIMBRADO)

    # ------------------------------------------------------------------
    # Instruções — sai da peça antes da entrega
    # ------------------------------------------------------------------
    vl.caixa(
        doc,
        "MODELO — APAGUE ESTE QUADRO ANTES DE ENTREGAR A PEÇA PARA REVISÃO",
        "Antes de redigir: (1) LEIA A CÉDULA e preencha o quadro de identificação com programa "
        "(Pronaf, Pronamp ou sem programa), fonte de recursos e vencimento de cada operação; a "
        "tempestividade depende disso (MCR 10-1-27 \"f\" só vale para Pronaf; 2-6-12 \"e\" para custeio "
        "Pronamp e demais; 11-1-4 \"h\" para investimento subvencionado); (2) o pedido que vence nas decisões é ESCRITO, ANTES do vencimento (FAEP: 15 dias), com os DOIS laudos anexos e prova de recebimento; descubra QUANDO e COMO o "
        "cliente pediu a prorrogação: WhatsApp ou áudio ao gerente, e-mail, protocolo na agência, AR, "
        "ata notarial, testemunha de comparecimento. Todo registro com data vai para a linha do tempo "
        "e vira print em par (imagem + transcrição); (3) escolha UM dos dois caminhos do tópico III.2 "
        "e apague o outro; (4) confira a redação do MCR 2-6-4 VIGENTE NA DATA DO PEDIDO: a expressão "
        "\"por sua conveniência e decisão, mediante solicitação do mutuário\" entrou com a Res. CMN "
        "5.314 (MCR nº 757, 17/07/2026); (5) leia na cédula qual assistência técnica foi pactuada "
        "(plano simples, projeto técnico, assistência em nível de imóvel) e ajuste o tópico III.4; "
        "(6) pesquise no PJe, por CPF e por número da cédula, execução, monitória ou busca e apreensão "
        "sobre as mesmas operações; (7) foro: CEF, Justiça Federal (art. 109, I, CF); Banco do Brasil "
        "segue na Justiça Estadual até decisão da GJ; (8) não cumule revisão de encargos: se houver "
        "abusividade, avalie peça própria (descaracterização da mora ou revisional); (9) LAUDO é o "
        "primeiro motivo de derrota (31 de 61 decisões desfavoráveis, diagnóstico de 13/09/2026): exija "
        "engenheiro agrônomo com ART, visita à propriedade, números da propriedade, e laudo de capacidade "
        "de pagamento com carência, número de parcelas e forma de amortização; (10) junte o que os juízes "
        "mais disseram faltar: notas fiscais e declaração de produção, requerimento administrativo datado, "
        "certidão de órgão público (ADERR, EMATER, IDARON, Defesa Civil); (11) o cronograma pedido tem de "
        "caber no teto normativo da LINHA (ex.: MCR 11-1-4 \"d\", 10-1-25, 2-6-11 \"c\"): carência acima do "
        "teto é cortada; (12) se o título for CCB, CPR ou houver recursos livres, mantenha o tópico III.1-A "
        "(natureza rural); se for cédula rural com recursos controlados, apague-o; (13) CADA PROVA TEM BLOCO PRÓPRIO (PROVA nn): recorte com moldura, grifo amarelo declarado "
        "(legenda com \"grifo nosso\"), transcrição e \"o que prova\"; a ficha MODELO_ALONGAMENTO_DIVIDA_RURAL"
        ".provas.json diz à automação que documento procurar, onde recortar e o que grifar; prova que não "
        "existe na pasta: apague o bloco E a linha do índice, nunca \"conforme documento\" sem documento; "
        "(14) JURISPRUDÊNCIA: todo julgado deste modelo foi selecionado por automação e TEM DE SER "
        "CONFERIDO pelo advogado no inteiro teor (número, órgão, relator, data e se o trecho citado está "
        "mesmo lá) antes do protocolo — na montagem deste modelo, a própria conferência corrigiu um relator "
        "atribuído errado; ALIMENTE com jurisprudência LOCAL do tribunal que vai julgar (TJRO ou TRF1), de "
        "preferência do gabinete ou câmara sorteada, e confira no vault (01 - MAGISTRADOS) o perfil recente "
        "do gabinete; (15) rode "
        "varrer_marcadores_print e confira que não sobrou [[campo]] amarelo.",
        vl.VERMELHO)

    # ------------------------------------------------------------------
    # Endereçamento e qualificação
    # ------------------------------------------------------------------
    vl.paragrafo(
        doc,
        "[[EXCELENTÍSSIMO(A) SENHOR(A) JUIZ(A) DE DIREITO DA (…) VARA CÍVEL DA COMARCA DE (…) / "
        "JUIZ(A) FEDERAL DA (…) VARA FEDERAL DA SUBSEÇÃO JUDICIÁRIA DE (…)]]",
        negrito=True)

    vl._espaco(doc, 12)

    vl.paragrafo(
        doc,
        "[[NOME DO CLIENTE]], [[nacionalidade]], [[estado civil]], produtor rural, portador da Cédula "
        "de Identidade nº [[RG]], inscrito no CPF sob o nº [[CPF]], residente e domiciliado em "
        "[[ENDEREÇO COMPLETO]], endereço eletrônico [[e-mail]], vem, por seus advogados que esta "
        "subscrevem, propor")

    _centro(doc, "AÇÃO MANDAMENTAL DE PRORROGAÇÃO DE CRÉDITO RURAL", negrito=True, espaco=0)
    _centro(doc, "(obrigação de fazer: arts. 497 e 501 do CPC)", espaco=0)
    _centro(doc, "com pedido de TUTELA DE URGÊNCIA DE NATUREZA CAUTELAR formulado conjuntamente com o "
                 "pedido principal (arts. 300, 301 e 308, § 1º, do CPC)", espaco=10)

    vl.paragrafo(
        doc,
        "em face de [[NOME DA INSTITUIÇÃO FINANCEIRA]], [[natureza jurídica]], inscrita no CNPJ sob o "
        "nº [[CNPJ]], com sede em [[ENDEREÇO]], e agência operadora [[AGÊNCIA E ENDEREÇO]], pelos "
        "fundamentos de fato e de direito a seguir expostos.")

    # ------------------------------------------------------------------
    # Identificação e síntese
    # ------------------------------------------------------------------
    vl.quadro_identificacao(doc, [
        ("Operação(ões)", "[[espécie e nº de cada cédula]]"),
        ("Programa e fonte de recursos", "[[Pronaf / Pronamp / sem programa · recursos obrigatórios / "
                                         "BNDES / FNO / livres]] (conforme Quadro da cédula)"),
        ("Vencimento(s)", "[[original e, se houver, prorrogado]]"),
        ("Pedido de prorrogação ao banco", "[[data · meio (WhatsApp, e-mail, protocolo, AR) · se levou "
                                           "laudo]] ou [[não houve pedido antes do vencimento]]"),
        ("Resposta do banco", "[[silêncio desde (…) / negativa sem fundamentação técnica em (…) / "
                              "proposta fora do MCR em (…)]]"),
        ("Assistência técnica pactuada", "[[plano simples / projeto técnico / assistência em nível de "
                                         "imóvel · empresa (…)]]"),
        ("Evento adverso e ato oficial", "[[estiagem / queda de preço / praga · Decreto nº (…)]]"),
        ("Cobrança judicial conexa", "[[Execução/Monitória nº (…), Juízo (…)]] ou [[não há, pesquisa "
                                     "no PJe por CPF e por cédula em (…)]]"),
    ])

    vl.sintese_da_controversia(
        doc,
        o_que_se_pede=(
            "Agora: a suspensão da exigibilidade das operações e dos efeitos da mora, com abstenção de "
            "negativação (inclusive SCR/SICOR) e de atos constritivos. Ao final: a condenação do réu a "
            "prorrogar as operações, aos mesmos encargos pactuados, no cronograma que o laudo de "
            "capacidade de pagamento demonstra."),
        por_que=(
            "O autor comprovou dificuldade temporária de reembolso causada por [[evento adverso]], "
            "hipótese do MCR 2-6-4, norma editada pelo Conselho Monetário Nacional por delegação da "
            "Lei 4.829/65 (arts. 4º e 14). O alongamento de dívida originada de crédito rural não "
            "constitui faculdade da instituição financeira, mas direito do devedor (Súmula 298/STJ)."),
        o_que_nao_se_pede=(
            "Não se pede revisão de juros ou de outros encargos, recálculo de saldo, repetição de "
            "indébito, perdão ou redução da dívida. A prorrogação do MCR 2-6-4 se faz \"aos mesmos "
            "encargos financeiros pactuados no instrumento de crédito\": muda o prazo, não o preço."))

    _sumario(doc, [
        ("I", "Da delimitação do objeto"),
        ("II", "Dos fatos"),
        ("III", "Do direito à prorrogação"),
        ("IV", "Da tutela de urgência de natureza cautelar"),
        ("V", "Da distribuição do ônus da prova e da exibição de documentos"),
        ("VI", "Da gratuidade da justiça"),
        ("VII", "Dos pedidos"),
        ("VIII", "Do valor da causa"),
    ])

    # ------------------------------------------------------------------
    # I — Delimitação do objeto
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "I", "Da delimitação do objeto")

    vl.paragrafo(
        doc,
        "A demanda tem dois pedidos, de naturezas distintas e complementares, deduzidos conjuntamente "
        "como autoriza o art. 308, § 1º, do CPC:")

    _argumento(
        doc, "a", "Pedido cautelar.",
        "Suspender a exigibilidade das operações e os efeitos da mora enquanto se discute o direito à "
        "prorrogação, impedindo negativação, cobrança e constrição das garantias. É pedido de meio: "
        "preserva o resultado útil do processo, sem antecipar o mérito.")

    _argumento(
        doc, "b", "Pedido principal.",
        "Condenar o réu a prorrogar as operações de crédito rural descritas no tópico II, aos mesmos "
        "encargos financeiros pactuados, com os vencimentos readequados à capacidade de pagamento "
        "demonstrada em laudo técnico (MCR 2-6-1 e 2-6-4).")

    vl.paragrafo(
        doc,
        "A ação não é revisional. Não se discute a taxa de juros, a capitalização ou qualquer outro "
        "encargo, não se pede recálculo de saldo e não se pede redução da dívida: o próprio item do "
        "Manual de Crédito Rural que fundamenta o pedido determina que a prorrogação se faça \"aos "
        "mesmos encargos financeiros pactuados no instrumento de crédito\". O que se altera é o "
        "cronograma de reembolso. Por isso não há valor incontroverso a depositar, nem perícia "
        "contábil a produzir sobre encargos.")

    vl.quadro_comparativo(
        doc,
        "PRORROGAÇÃO (MCR 2-6-4) × RENEGOCIAÇÃO",
        "Prorrogação (o que se pede)", "Renegociação (o que não se pede)",
        [
            ("Objeto", "O prazo de reembolso da mesma operação", "Novo acordo sobre a dívida"),
            ("Encargos", "Os mesmos pactuados no instrumento (MCR 2-6-4)",
             "Livremente redefinidos pelas partes"),
            ("Fundamento", "MCR 2-6-4 e Súmula 298/STJ", "Autonomia da vontade"),
            ("Formalização", "Anotação pelo credor no título, ainda que após o vencimento original "
                             "(DL 167/67, art. 62)", "Novo instrumento ou aditivo"),
        ],
        linha_erro=(
            "CONFUSÃO A EVITAR",
            "Ler o pedido de prorrogação como pedido de revisão de encargos",
            "A prorrogação mantém os encargos por força do próprio MCR 2-6-4"))

    # ------------------------------------------------------------------
    # II — Fatos, contados pelas provas
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "II", "Dos fatos e das provas")

    vl.paragrafo(
        doc,
        "Os fatos desta ação estão nos documentos, e por isso são apresentados pelas próprias provas: cada "
        "uma traz o recorte do documento, a transcrição do trecho relevante e o que ela demonstra. O índice "
        "abaixo resume o que está nos autos e para que serve cada documento.")

    vl.indice_de_provas(doc, [(p["numero"], p["documento"], p["demonstra"], p["requisito"]) for p in PROVAS])

    _subtitulo(doc, "II.1. O autor e as operações")

    vl.paragrafo(
        doc,
        "O autor é produtor rural e explora [[atividade: pecuária de corte / leite / soja / café …]] no "
        "imóvel [[denominação, matrícula e município]], [[em regime familiar / com (…) empregados]], "
        "sendo essa atividade [[sua única fonte de renda]]. As operações cuja prorrogação se pede são estas, "
        "com os dados extraídos dos próprios títulos:")

    _quadro_operacoes(doc)

    vl.pendencia(
        doc,
        "Preencher programa, fonte de recursos e vencimento LENDO O QUADRO DA CÉDULA. Nunca estimar. "
        "Se a operação já foi prorrogada administrativamente antes (pagamento de entrada, aditivo), "
        "registrar o vencimento original E o prorrogado e trazer o documento: a prorrogação anterior "
        "mostra que o próprio banco reconheceu a dificuldade, e, se foi feita depois do vencimento, "
        "que ele mesmo prorrogou fora do prazo.")

    _provas(doc, "operacao")

    _subtitulo(doc, "II.2. O evento adverso")

    vl.paragrafo(
        doc,
        "Em [[período]], a atividade foi atingida por [[evento: estiagem severa / queda do preço da arroba / "
        "praga (…)]]. O evento é oficial, medido por fonte pública e visível na propriedade do autor:")

    _provas(doc, "evento")

    _subtitulo(doc, "II.3. O laudo de perda")

    vl.paragrafo(
        doc,
        "A perda na propriedade foi apurada por profissional habilitado, com visita ao local e números da "
        "própria atividade, operação por operação:")

    _provas(doc, "laudo")

    _subtitulo(doc, "II.4. A capacidade de pagamento")

    vl.paragrafo(
        doc,
        "A dificuldade é temporária. O laudo de capacidade de pagamento demonstra em que cronograma a dívida "
        "volta a ser paga, considerado todo o endividamento do autor:")

    _provas(doc, "capacidade")

    _subtitulo(doc, "II.5. O pedido de prorrogação ao banco e a resposta")

    vl.paragrafo(
        doc,
        "Em [[data]], [[antes do vencimento de (…)]], o autor pediu ao réu, por escrito, a prorrogação das "
        "operações, com os dois laudos anexos. [[O réu não respondeu / negou sem análise técnica / ofereceu "
        "(…), proposta que não observa o MCR]]:")

    _provas(doc, "pedido")

    vl.paragrafo(
        doc,
        "Mensagem eletrônica impressa é meio de prova (art. 422, § 3º, do CPC), e as partes podem empregar "
        "todos os meios legais e moralmente legítimos para provar os fatos (art. 369 do CPC).")

    _precedente(doc, "Pedido por WhatsApp e silêncio do banco")

    vl.pendencia(
        doc,
        "PROVA DO PEDIDO POR QUALQUER MEIO (devolutiva da GJ de 08/08/2026). Antes de escrever este "
        "tópico, verifique com o cliente e com o setor de documentos: mensagens e áudios de WhatsApp com "
        "gerente ou assessor agro; e-mails; protocolos e senhas de atendimento na agência; AR de "
        "notificação; registro de comparecimento; testemunha que acompanhou o cliente; ata notarial das "
        "conversas. Adapte a narrativa ao que existe e junte TODOS os registros com data. Mensagem do "
        "gerente que admite o fato contra o banco é confissão extrajudicial (art. 389 do CPC). Se não "
        "houver registro nenhum, NÃO afirme que houve pedido: use o caminho B do tópico III.2. ATENÇÃO "
        "(diagnóstico de 13/09/2026): nas decisões lidas, o pedido que sustentou a tutela foi o ESCRITO, "
        "com os laudos anexos e prova de recebimento (AR, confirmação de leitura, protocolo); pedido verbal, "
        "só por WhatsApp ou sem laudo anexo foi rejeitado no TJRO. Registro informal entra como reforço, "
        "não como o pedido. Laudo datado DEPOIS do pedido também derrubou tutela.")

    _subtitulo(doc, "II.6. A aplicação do crédito e a produção")

    vl.paragrafo(
        doc,
        "O crédito foi aplicado na atividade rural, e a queda da produção está registrada em documento de "
        "órgão público:")

    _provas(doc, "aplicacao")

    _subtitulo(doc, "II.7. A ameaça concreta")

    vl.paragrafo(
        doc,
        "O dano não é hipotético: o réu já adotou, ou anunciou com data, as medidas abaixo:")

    _provas(doc, "ameaca")

    vl.linha_do_tempo(doc, [
        ("[[dd/mm/aaaa]]", "Emissão da cédula [[nº]]", FASE_ANTES, "Prova 01"),
        ("[[dd/mm/aaaa]]", "Evento adverso: [[descrever]] · decreto de emergência [[nº]]", FASE_ANTES,
         "Provas 06 e 07"),
        ("[[dd/mm/aaaa]]", "Laudos de perda e de capacidade de pagamento", FASE_ANTES, "Provas 10 e 13"),
        ("[[dd/mm/aaaa]]", "Pedido escrito de prorrogação, com os laudos anexos", FASE_ANTES, "Prova 16"),
        ("[[dd/mm/aaaa]]", "Recebimento do pedido pelo banco", FASE_ANTES, "Prova 17"),
        ("[[dd/mm/aaaa]]", "Vencimento da operação [[original / prorrogado]]", FASE_DEPOIS, "Provas 02 e 05"),
        ("[[dd/mm/aaaa]]", "[[Silêncio / negativa / negativação / execução]]", FASE_DEPOIS,
         "Provas 18, 22 e 23"),
    ], titulo="LINHA DO TEMPO: O PEDIDO E O VENCIMENTO")

    vl.pendencia(
        doc,
        "Coloque cada evento na coluna certa: a fase é definida pela data do VENCIMENTO. Data que não "
        "puder ser conferida em documento sai da tabela. Nunca escreva \"pedido tempestivo\" ou \"antes "
        "do vencimento\" sem as duas datas nesta tabela.")

    # ------------------------------------------------------------------
    # III — Do direito
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "III", "Do direito à prorrogação")

    _subtitulo(doc, "III.1. A fonte normativa do direito")

    _argumento(
        doc, "1", "A lei delegou ao Conselho Monetário Nacional as condições do crédito rural.",
        "A Lei 4.829/65 atribuiu ao Conselho Monetário Nacional a disciplina do crédito rural e a edição, "
        "com exclusividade, de suas normas operativas (art. 4º), e determinou que \"os têrmos, prazos, "
        "juros e demais condições das operações de crédito rural, sob quaisquer de suas modalidades, serão "
        "estabelecidos pelo Conselho Monetário Nacional\" (art. 14). O Manual de Crédito Rural consolida "
        "essas normas. Quando o MCR disciplina o prazo e a prorrogação da operação, portanto, não expede "
        "recomendação ao mercado: exerce competência normativa conferida por lei federal.")

    _argumento(
        doc, "2", "O MCR prevê a prorrogação quando há dificuldade temporária de reembolso.",
        "O item 2-6-4 do Manual dispõe:")

    vl.precedente(
        doc,
        "[[TRANSCREVER A REDAÇÃO DO MCR 2-6-4 VIGENTE NA DATA DO PEDIDO. Redação atual (MCR nº 758): "
        "\"Fica a instituição financeira autorizada, por sua conveniência e decisão, mediante solicitação "
        "do mutuário, a prorrogar a dívida referente à operação de crédito rural, aos mesmos encargos "
        "financeiros pactuados no instrumento de crédito, desde que o mutuário comprove a dificuldade "
        "temporária para reembolso do crédito em razão de uma ou mais entre as situações abaixo e que a "
        "instituição financeira ateste a necessidade de prorrogação e demonstre a capacidade de pagamento "
        "do mutuário: a) dificuldade de comercialização dos produtos; b) frustração de safras, por fatores "
        "adversos; c) eventuais ocorrências prejudiciais ao desenvolvimento das explorações; d) "
        "dificuldades no fluxo de caixa do mutuário, devido ao impacto acumulado de perdas de safra "
        "decorrentes de eventos climáticos adversos em safras anteriores, que gerem aumento do "
        "endividamento no Sistema Nacional de Crédito Rural - SNCR e impossibilitem o reembolso integral "
        "das operações de crédito rural.\" Para pedido anterior a 17/07/2026, buscar a atualização da "
        "época no site do Banco Central.]]",
        "MCR 2-6-4 ([[atualização nº (…), vigente em (…)]])", MCR_NORMA)

    vl.paragrafo(
        doc,
        "Três leituras do texto decidem a causa. Primeira: os requisitos das alíneas são alternativos, "
        "porque basta \"uma ou mais entre as situações abaixo\". Segunda: ao mutuário cabe comprovar a "
        "dificuldade temporária e a situação que a causou; atestar a necessidade e demonstrar a capacidade "
        "de pagamento é tarefa que o texto atribui à instituição financeira, e não ao produtor. Terceira: "
        "a prorrogação se faz aos mesmos encargos, o que confirma que o objeto é o prazo.")

    _argumento(
        doc, "3", "Não é faculdade do banco: é direito do devedor.",
        "O Superior Tribunal de Justiça consolidou o entendimento:")

    vl.precedente(
        doc,
        "O alongamento de dívida originada de crédito rural não constitui faculdade da instituição "
        "financeira, mas, direito do devedor nos termos da lei.",
        "STJ, Súmula 298", vl.SUMULA)

    vl.pendencia(
        doc,
        "SE O PEDIDO FOR POSTERIOR A 17/07/2026 (redação com \"por sua conveniência e decisão\"), manter o "
        "parágrafo abaixo. SE FOR ANTERIOR, apagá-lo e registrar que a redação vigente na data do fato não "
        "continha a expressão.")

    vl.paragrafo(
        doc,
        "A expressão \"por sua conveniência e decisão\", introduzida na redação atual do item, não "
        "converte o direito em liberalidade. A decisão do banco continua vinculada aos requisitos que o "
        "mesmo item enumera: se o mutuário comprova a dificuldade temporária e a situação adversa, a "
        "instituição só pode negar demonstrando, com análise técnica, que a prorrogação não é necessária "
        "ou que falta capacidade de pagamento, porque é ela quem deve atestar uma e demonstrar a outra. "
        "Decisão que nega sem essa análise excede manifestamente o fim econômico e social do direito que "
        "a norma confere ao credor, o que configura ato ilícito (art. 187 do Código Civil), e viola o dever "
        "de probidade e boa-fé na execução do contrato (art. 422 do Código Civil).")

    # Em linha, e não em quadro: a Súmula já tem tarja própria logo acima, e dois
    # quadros seguidos para a mesma tese diluem em vez de reforçar (economia fixada
    # pela Dra. Juliana no modelo da declaratória, 10/09/2026).
    vl.paragrafo(
        doc,
        "Aplicando a súmula, os tribunais têm afirmado que \"o alongamento do prazo independe da vontade da "
        "instituição financeira, sendo necessário apenas o atendimento das condições previstas no Manual de "
        "Crédito Rural\" (TRF-4, AC 5002286-98.2021.4.04.7106/RS, Rel. Des. Federal Vânia Hack de Almeida, "
        "3ª Turma, j. 07/03/2023) [[conferir inteiro teor]].")

    vl.pendencia(
        doc,
        "ALERTA AO ADVOGADO — JURISPRUDÊNCIA. (1) Os julgados deste modelo foram selecionados por "
        "automação: CONFIRA cada um no inteiro teor (número, câmara, relator, data e o trecho citado) antes "
        "do protocolo — na montagem, a conferência corrigiu um relator atribuído errado e achou câmara "
        "divergente entre acórdão e autuação. (2) ALIMENTE com jurisprudência LOCAL: julgado do TJRO (ou do "
        "TRF1, se a ré for a CEF), de preferência da câmara ou do gabinete sorteado, e troque a tarja "
        "\"TJRO · tribunal de origem\" por \"persuasiva\" se a ação correr na Justiça Federal. (3) Confira no "
        "vault (01 - MAGISTRADOS) o perfil recente do gabinete: o 2º grau do TJRO foi o terreno mais difícil "
        "do diagnóstico de 13/09/2026.")

    _precedente(doc, "TJRO: direito subjetivo, sem discricionariedade bancária")

    _subtitulo(doc, "III.1-A. A natureza rural da operação (só se o título for CCB, CPR ou houver recursos livres)")

    vl.pendencia(
        doc,
        "CCB comercial e \"recursos próprios / não controlados\" somaram 17 das 61 derrotas do diagnóstico. "
        "Se o título for Cédula de Crédito Rural com recursos controlados e programa indicado no Quadro, "
        "APAGUE este subtópico: a natureza rural consta da própria literalidade do título. Se ficar, junte a "
        "prova da destinação: notas fiscais de insumos e animais, extratos com a aplicação, declaração de "
        "produção.")

    _argumento(
        doc, "3-A", "A natureza rural decorre da destinação do crédito, e não do nome do título.",
        "A lei define crédito rural pela aplicação: é \"o suprimento de recursos financeiros por entidades "
        "públicas e estabelecimentos de crédito particulares a produtores rurais ou a suas cooperativas para "
        "aplicação exclusiva em atividades que se enquadrem nos objetivos indicados na legislação em vigor\" "
        "(Lei 4.829/65, art. 2º). Os recursos foram integralmente aplicados em [[finalidade: aquisição de "
        "bovinos / custeio da lavoura de (…)]], como provam as notas fiscais e o registro da produção "
        "(Provas 20 e 21).")

    _argumento(
        doc, "3-B", "Recursos próprios do banco também são fonte de crédito rural.",
        "O próprio Manual classifica como fonte do crédito rural os recursos \"livres\", definidos como os "
        "\"provenientes das captações não sujeitas ao direcionamento, ou próprios da instituição financeira "
        "aplicados em crédito rural\" (MCR 6-1-1, \"a\", II), e dispõe que, \"seja qual for a origem dos "
        "recursos, sua aplicação só é considerada crédito rural quando observadas a legislação aplicável ao "
        "crédito rural e as normas estabelecidas neste manual\" (MCR 6-1-10). A origem do dinheiro não "
        "retira a operação do regime do crédito rural: o que a define é a aplicação na atividade rural, "
        "observadas as normas do Manual, entre elas o item 2-6-4.")

    _precedente(doc, "Natureza rural pela destinação dos recursos")

    _subtitulo(doc, "III.2. O pedido ao banco e o vencimento")

    vl.pendencia(
        doc,
        "ESCOLHA UM CAMINHO E APAGUE O OUTRO. Caminho A: houve pedido ao banco ANTES do vencimento, com "
        "prova datada. Caminho B: o pedido veio depois do vencimento ou não houve pedido. Na dúvida sobre a "
        "data, use o B: ele não depende da data e é o que se sustenta até o STJ.")

    _subtitulo(doc, "Caminho A: o pedido foi feito antes do vencimento")

    _argumento(
        doc, "4-A", "A solicitação do mutuário existiu e foi tempestiva.",
        "Em [[data]], antes do vencimento de [[data]], o autor pediu a prorrogação por [[meio]] "
        "(tópico II.3), acompanhada de [[laudos]], contendo as informações técnicas que a norma manda "
        "apresentar: a situação que gerou a dificuldade, sua intensidade, o percentual de redução de renda "
        "e o tempo estimado de recuperação ([[MCR 2-6-12, \"d\" / MCR 10-1-27, \"d\" / MCR 11-1-4, "
        "\"i\"]]). O banco teve diante de si, antes do vencimento, tudo o que o MCR exige para decidir.")

    _argumento(
        doc, "5-A", "O silêncio do banco não é neutro.",
        "Recebido o pedido instruído, o réu [[não respondeu / respondeu sem análise técnica]]. Deixou de "
        "atestar a desnecessidade ou de demonstrar a falta de capacidade de pagamento, que eram ônus seus "
        "pelo texto do MCR 2-6-4, e com isso deixou de exercer, na via administrativa, o contraditório sobre "
        "o laudo que lhe foi apresentado. Não pode agora qualificar como unilateral a prova técnica que "
        "recebeu e não impugnou.")

    _subtitulo(doc, "Caminho B: o pedido foi feito após o vencimento, ou não houve pedido")

    _argumento(
        doc, "4-B", "A exigência de pedido antes do vencimento não é regra geral do crédito rural.",
        "O MCR só a escreve para linhas determinadas e com vigência datada: custeio do Pronamp e dos demais "
        "produtores (MCR 2-6-12, \"e\", incluído pela Res. CMN 5.220/2025) e investimento com recursos "
        "subvencionados pelo Tesouro (MCR 11-1-4, \"h\"). No Pronaf, o próprio Manual admite o pedido em "
        "até 30, 60 ou 120 dias após o vencimento da prestação, conforme a fonte (MCR 10-1-27, \"f\", "
        "Res. CMN 5.122/2024). E o item 2-6-4, regime geral, não fixa prazo algum para a solicitação. "
        "[[A operação do autor é (…), com recursos (…): indicar o regime aplicável.]]")

    _argumento(
        doc, "5-B", "A lei federal admite a prorrogação depois do vencimento original.",
        "O Decreto-Lei 167/67, com a redação da Lei 14.421/2022, dispõe:")

    vl.precedente(
        doc,
        "Art. 62. Nas prorrogações de que trata o art. 13 deste Decreto-Lei, ainda que efetuadas após o "
        "vencimento original da operação, ficam dispensadas a lavratura de termo aditivo e a assinatura do "
        "emitente, bastando, para todos os efeitos, a anotação pelo credor no instrumento de crédito, salvo "
        "nas hipóteses estabelecidas pelo poder público.",
        "Decreto-Lei 167/1967, art. 62 (redação dada pela Lei 14.421/2022)", LEI_FEDERAL)

    vl.paragrafo(
        doc,
        "Se a lei regula a forma da prorrogação efetuada após o vencimento original, a afirmação de que "
        "\"não se prorroga dívida vencida\" não encontra apoio no ordenamento. O vencimento sem pedido "
        "anterior pode, quando muito, deslocar o regime da renegociação dentro do próprio Manual (MCR "
        "2-6-12, \"g\", que remete ao MCR 2-6-7 a 2-6-9, e MCR 10-1-27, \"j\" e \"k\"); não extingue o "
        "direito, e em nenhum desses itens a norma autoriza o banco a recusar a prorrogação apenas porque "
        "o pedido veio depois.")

    _subtitulo(doc, "Em qualquer dos caminhos")

    _argumento(
        doc, "6", "O interesse de agir não depende de requerimento administrativo prévio.",
        "Para postular em juízo basta ter interesse e legitimidade (art. 17 do CPC). O interesse do autor "
        "está demonstrado pela resistência concreta do réu: [[a cobrança das parcelas nos vencimentos "
        "originais / a negativação em (…) / o ajuizamento da execução nº (…) / a ausência de resposta ao "
        "pedido]]. Condicionar o acesso ao Judiciário a um pedido que nenhuma lei impõe como pressuposto "
        "da ação seria criar requisito que o legislador não criou.")

    _precedente(doc, "Desnecessidade de requerimento administrativo prévio (STJ)")
    vl.paragrafo(
        doc,
        "No mesmo sentido, reconhecendo o interesse de agir e a negativa implícita do banco diante de "
        "notificação e laudos enviados por e-mail e carta com AR: TJPR, Apelação Cível "
        "0006568-19.2024.8.16.0083, Rel. Des. Carlos Mansur Arida, 5ª Câmara Cível, j. 21/05/2025 "
        "[[conferir inteiro teor]].")

    vl.paragrafo(
        doc,
        "[[Se a operação já foi prorrogada antes, administrativamente, manter:]] a tempestividade se mede "
        "pelo vencimento da obrigação prorrogada, e não pelo da original (TJMT, AI 1010134-81.2026.8.11.0000, "
        "Rel. Des. Luiz Octávio Oliveira Saboia Ribeiro, 5ª Câmara de Direito Privado, j. 02/06/2026: "
        "\"Tempestivo o requerimento de prorrogação aferido pelo vencimento da obrigação renegociada, e não "
        "da originária\") [[conferir inteiro teor]].")

    _subtitulo(doc, "III.3. Os requisitos materiais estão provados")

    vl.paragrafo(
        doc,
        "O quadro abaixo confronta cada exigência do MCR 2-6-4 com a prova que a satisfaz:")

    _quadro_requisitos(doc)

    vl.paragrafo(
        doc,
        "A estiagem de [[período]] é fato notório, que não depende de prova (art. 374, I, do CPC), e foi "
        "declarada oficialmente pelo [[Decreto nº (…)]], cujo teor e vigência se comprovam pelo documento "
        "juntado (art. 376 do CPC). O laudo técnico abrange [[as operações vencidas e as vincendas]] e "
        "projeta a capacidade de pagamento no cronograma pedido.")

    _argumento(
        doc, "7", "O laudo não é \"unilateral\" no sentido que o afastaria.",
        "O laudo foi elaborado por [[engenheiro agrônomo, CREA nº (…), ART nº (…)]], com visita à propriedade "
        "em [[data]], e quantifica, com dados da própria atividade do autor, a perda de [[(…)%]], a renda "
        "projetada e o cronograma de [[carência de (…) e (…) parcelas]] em que a dívida volta a ser paga. "
        "[[Foi enviado ao réu em (…), junto com o pedido de prorrogação, e não recebeu impugnação técnica: o "
        "contraditório foi oferecido na via administrativa e não exercido.]] É corroborado por prova que não "
        "vem do autor: [[decreto de emergência nº (…); certidão/laudo da ADERR, EMATER ou IDARON; cotação "
        "oficial da arroba em (…)]]. Em cognição sumária, basta a probabilidade do direito (art. 300 do "
        "CPC); a certeza é tarefa da instrução.")

    _argumento(
        doc, "8", "Não se trata de risco ordinário do negócio.",
        "O próprio MCR 2-6-4 elege a frustração de safra \"por fatores adversos\", a dificuldade de "
        "comercialização e as \"ocorrências prejudiciais ao desenvolvimento das explorações\" como causas de "
        "prorrogação: a norma do crédito rural já decidiu que esses eventos não são risco que o produtor "
        "suporta sozinho. A intensidade do evento no caso concreto está oficialmente reconhecida pelo "
        "[[Decreto nº (…)]] e quantificada no laudo.")

    vl.pendencia(
        doc,
        "Laudo unilateral ou insuficiente foi o motivo de 31 das 61 derrotas do diagnóstico. Não protocole "
        "sem: ART; visita à propriedade; números DA PROPRIEDADE (não só da região); capacidade de pagamento "
        "com carência, número de parcelas e forma de amortização (laudo \"sem prazo, parcelas e forma de "
        "amortização\" foi rejeitado); ao menos uma prova pública que o corrobore. E, pelo que as "
        "decisões das referências do agro mostram: laudo de perda POR OPERAÇÃO E POR SAFRA (esperado × "
        "obtido); números COERENTES entre o laudo de perda e o de capacidade (divergência de receita entre "
        "os dois derrubou tutela); corroboração externa (INMET/CEMADEN, NDVI, DIRPF, notas fiscais, "
        "balanços); endividamento global DECLARADO, não escondido; se houve operação nova contratada já na "
        "crise, enfrente o ponto antes do banco.")

    vl.quadro_distinguishing(doc, [
        "Demonstrar, com análise técnica, que a dificuldade de reembolso do autor não é temporária ou "
        "que nenhuma das situações das alíneas do MCR 2-6-4 ocorreu.",
        "Demonstrar que o autor não terá capacidade de pagamento no cronograma prorrogado: é a "
        "instituição que deve demonstrá-la, nos termos do próprio item.",
        "Afirmar genericamente que a prorrogação é \"faculdade\" ou que \"a política interna não "
        "permite\" não enfrenta a Súmula 298/STJ nem os requisitos do MCR, e decisão que acolha esse "
        "argumento sem distinção fundamentada deixa de seguir enunciado de súmula invocado pela parte "
        "(art. 489, § 1º, VI, do CPC).",
    ], titulo="O QUE CABE AO RÉU DEMONSTRAR PARA NEGAR A PRORROGAÇÃO")

    _precedente(doc, "TJRO: laudos específicos contra alegação genérica do banco")

    vl.paragrafo(
        doc,
        "No mesmo sentido, admitindo o laudo particular em cognição sumária \"ainda que a referida prova tenha "
        "sido produzida de forma unilateral\": TJPR, AI 0024107-19.2025.8.16.0000, 16ª Câmara Cível, j. "
        "16/07/2025 [[conferir inteiro teor]].")

    _subtitulo(doc, "III.4. A análise técnica que o banco devia fazer: assistência técnica e fiscalização")

    _argumento(
        doc, "9", "O banco é obrigado a manter análise técnica do crédito rural.",
        "Para atuar em crédito rural, a instituição financeira deve \"manter serviços de assessoramento "
        "técnico em nível de carteira, à sua conta exclusiva, visando à adequada administração do crédito "
        "rural, bem como assegurar a prestação de assistência técnica em nível de imóvel ou empresa, "
        "quando devida\" (MCR 1-1-1, \"c\"). É também \"responsável pelo monitoramento e pela "
        "fiscalização das operações de crédito rural\", com \"o necessário registro das verificações "
        "realizadas\" (MCR 2-7-1, \"a\" e \"d\"). A fiscalização pelo financiador é exigência essencial "
        "da operação desde a lei (Lei 4.829/65, art. 10, III; Lei 8.171/91, art. 50, II).")

    _argumento(
        doc, "10", "A assistência técnica registra justamente os eventos que fundamentam a prorrogação.",
        "Quando há assistência técnica, o prestador \"deve manter permanente acompanhamento do "
        "empreendimento, fornecendo laudos à instituição financeira, em até 15 (quinze) dias da visita\", "
        "com registro, entre outros, de \"eventos prejudiciais à produção\" (MCR 1-3-5, \"e\"). No caso, a "
        "cédula prevê [[plano simples / projeto técnico / assistência técnica em nível de imóvel]] a cargo "
        "de [[empresa]] (Prova 04).")

    _argumento(
        doc, "11", "A negativa sem análise técnica não é decisão fundamentada.",
        "O MCR condiciona a negativa à demonstração, pela instituição, de que a prorrogação é desnecessária "
        "ou de que falta capacidade de pagamento. Essa demonstração é técnica e depende dos registros de "
        "acompanhamento e fiscalização que o banco é obrigado a manter. Se [[o réu não respondeu / negou "
        "por manifestação de gerente ou setor administrativo, sem parecer técnico]], não houve a análise "
        "que a norma exige. Ou os registros existem, e devem vir aos autos; ou não existem, e o banco "
        "descumpriu o dever de fiscalização e não tem base técnica para contrariar o laudo do autor.")

    vl.paragrafo(
        doc,
        "Daí o requerimento, que se formula de forma específica (tópico V e pedido \"f\"): que o réu exiba "
        "o parecer ou a análise técnica que embasou a resposta ao pedido de prorrogação, os laudos de "
        "assistência técnica e os registros de fiscalização da operação, ou declare expressamente, no mesmo "
        "prazo, que tais documentos não existem.")

    vl.pendencia(
        doc,
        "Ajustar ao que a cédula diz sobre assistência técnica. Plano simples: pedir o plano e o Orçamento "
        "de Aplicação da proposta de crédito. Projeto técnico: pedir o projeto e os laudos do MCR 1-3-5. "
        "Assistência em nível de imóvel: pedir os laudos de visita. Sem assistência: manter só a "
        "fiscalização (MCR 2-7-1) e o assessoramento de carteira (MCR 1-1-1, \"c\"). Não afirmar falha de "
        "assistência técnica como causa autônoma: essa é outra ação.")

    _subtitulo(doc, "III.5. A mora")

    vl.paragrafo(
        doc,
        "\"Não havendo fato ou omissão imputável ao devedor, não incorre este em mora\" (art. 396 do "
        "Código Civil). O atraso decorre de [[evento adverso]], hipótese que a norma do crédito rural "
        "considera causa de prorrogação, e não de conduta do autor, que [[pediu a prorrogação em (…) / "
        "buscou o banco em (…)]]. Reconhecido o direito à prorrogação, as parcelas não eram exigíveis nos "
        "vencimentos originais, e não há mora a sustentar encargos moratórios, negativação ou constrição.")

    # ------------------------------------------------------------------
    # IV — Tutela cautelar
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "IV", "Da tutela de urgência de natureza cautelar")

    vl.paragrafo(
        doc,
        "A tutela de urgência será concedida quando houver elementos que evidenciem a probabilidade do "
        "direito e o perigo de dano ou o risco ao resultado útil do processo (art. 300 do CPC), e a de "
        "natureza cautelar pode ser efetivada por \"qualquer outra medida idônea para asseguração do "
        "direito\" (art. 301 do CPC). O que se pede agora não é a prorrogação, e sim a preservação das "
        "condições para que ela seja útil ao final.")

    _argumento(
        doc, "12", "Probabilidade do direito.",
        "Está documentada: laudos (Provas 10 a 15), decreto e medição oficial (Provas 06 e 07), pedido "
        "escrito recebido pelo banco (Provas 16 e 17) "
        "e o quadro do tópico III.3, que confronta cada requisito do MCR 2-6-4 com a prova. O direito "
        "invocado tem enunciado de súmula do STJ (Súmula 298). A tutela de urgência exige probabilidade, "
        "não certeza: remeter o pedido à instrução porque a prova \"depende de contraditório\" é exigir, na "
        "liminar, a cognição exauriente que só a sentença faz.")

    _precedente(doc, "Cognição sumária: exigir prova exauriente é erro de premissa")

    _argumento(
        doc, "13", "Perigo de dano concreto e individualizado.",
        "O autor explora [[atividade]] e depende de crédito a cada ciclo para [[insumos do ciclo: sal "
        "mineral, vacinas, ração / sementes, fertilizantes]] na janela de [[período]], que não se repete "
        "dentro do mesmo ciclo. A negativação, inclusive no Sistema de Informações de Crédito do Banco "
        "Central (SCR), fecha esse crédito; sem ele, [[consequência física: perda de peso e venda "
        "antecipada do rebanho / perda da safra]], exatamente no período em que a receita seria necessária "
        "para pagar. [[Há ainda a ameaça concreta de (…): execução nº (…), leilão marcado para (…), "
        "consolidação da propriedade]]. As garantias da operação são [[penhor de (…) e hipoteca de (…)]], "
        "que não são reserva patrimonial: são o próprio instrumento da produção.")

    vl.pendencia(
        doc,
        "Tutela genérica é indeferida (checklist da GJ, Bloco 5). Substituir TODOS os campos por fatos "
        "deste cliente: qual atividade, qual insumo, qual janela, qual consequência física, quais bens, "
        "qual ameaça datada.")

    _argumento(
        doc, "14", "Reversibilidade.",
        "A medida apenas suspende a exigibilidade e os efeitos da mora enquanto se discute o direito; as "
        "garantias permanecem íntegras e, se o pedido for julgado improcedente, o réu retoma a cobrança. "
        "Irreversível é o dano do outro lado: [[rebanho vendido, safra perdida, imóvel arrematado]].")

    _argumento(
        doc, "15", "Caução.",
        "O juiz pode dispensar a caução \"se a parte economicamente hipossuficiente não puder oferecê-la\" "
        "(art. 300, § 1º, do CPC). É o caso do autor, cuja incapacidade temporária de pagamento é o próprio "
        "objeto da ação. De todo modo, o crédito do réu continua garantido por [[penhor e hipoteca "
        "cedulares]], que a medida não atinge.")

    _argumento(
        doc, "16", "Justificação prévia, se houver dúvida.",
        "A tutela de urgência pode ser concedida liminarmente ou após justificação prévia (art. 300, § 2º, "
        "do CPC). Se Vossa Excelência não tiver elementos suficientes para decidir de plano, requer-se que "
        "designe a audiência de justificação antes de decidir, com a oitiva do responsável técnico pelo "
        "laudo e do preposto do réu.")

    _argumento(
        doc, "17", "Cobrança judicial conexa.",
        "[[Se houver execução ou monitória sobre as mesmas operações: a sentença daquela ação depende da "
        "declaração sobre a exigibilidade que é objeto desta, o que impõe a suspensão (art. 313, V, \"a\", "
        "do CPC), pelo prazo máximo de um ano (art. 313, § 4º). Se não houver, apagar este item.]]")

    _precedente(doc, "TJRO: tutela em cognição sumária com laudo e Súmula 298")
    _precedente(doc, "Tutela cautelar em ação de prorrogação: suspensão da exigibilidade e baixa de restrições")
    vl.paragrafo(
        doc,
        "No mesmo sentido: \"encontrando-se pendente de julgamento o litígio instaurado entre as partes acerca "
        "do alongamento do débito, não se justifica o registro do nome do devedor no CADIN ou qualquer outro "
        "órgão cadastral de proteção ao crédito\" (STJ, AgRg no REsp 1.228.968/PI, Rel. Min. Sidnei Beneti, "
        "3ª Turma, DJe 17/06/2013) [[conferir inteiro teor]].")

    vl.pendencia(
        doc,
        "Há decisão (TJMT, AI 1010134-81.2026.8.11.0000) que limita a liminar de prorrogação a 180 dias, "
        "prorrogáveis. Se o juízo seguir essa linha, pedir expressamente a prorrogação da medida antes do "
        "termo final, com a demonstração de que a causa persiste.")

    _subtitulo(doc, "IV.1. Variante: tutela antecipada, só quando a evidência for plena")

    vl.pendencia(
        doc,
        "REGRA DO MODELO: a tutela CAUTELAR é a principal, porque o produtor precisa continuar produzindo e "
        "ela pede só os meios (suspender exigibilidade, mora, negativação e constrição), sem antecipar o "
        "mérito. Use a variante abaixo SOMENTE quando probabilidade do direito E perigo de dano estiverem "
        "evidentes nos documentos (pedido datado antes do vencimento, laudo com ART, decreto oficial, "
        "silêncio ou negativa sem análise técnica, ameaça datada). Nesse caso, mantenha a cautelar e "
        "acrescente este pedido; caso contrário, apague este subtópico.")

    _argumento(
        doc, "18", "Antecipação dos efeitos da prorrogação.",
        "Presentes, de forma evidente, a probabilidade do direito e o perigo de dano, requer-se ainda a "
        "antecipação dos efeitos da tutela final, para que as parcelas das operações [[nº]] passem a vencer, "
        "provisoriamente, no cronograma do laudo de capacidade de pagamento, até o julgamento. A medida não "
        "é irreversível (art. 300, § 3º, do CPC): apenas desloca vencimentos, mantidos os encargos e as "
        "garantias, e, revogada, restabelece-se o cronograma original.")

    # ------------------------------------------------------------------
    # V — Ônus da prova e exibição
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "V", "Da distribuição do ônus da prova e da exibição de documentos")

    vl.paragrafo(
        doc,
        "Os documentos que decidem pontos centrais da causa estão em poder exclusivo do réu: o parecer "
        "técnico da análise do pedido, os registros de fiscalização (MCR 2-7-1, \"d\"), os laudos de "
        "assistência técnica (MCR 1-3-5), os aditivos e a evolução da dívida. Diante da maior facilidade "
        "de obtenção da prova do fato contrário, o juiz pode atribuir o ônus de modo diverso, por decisão "
        "fundamentada (art. 373, § 1º, do CPC). Requer-se essa distribuição e, cumulativamente, a exibição "
        "(art. 396 do CPC), com a descrição, a finalidade e as circunstâncias exigidas pelo art. 397:")

    vl.rol_de_pedidos(doc, [
        ("i", "as cédulas e todos os aditivos, e a ficha gráfica com a evolução do débito, para demonstrar "
              "os vencimentos, as prorrogações anteriores e a situação de cada operação;"),
        ("ii", "o parecer, a análise técnica ou a manifestação interna que embasou a resposta, ou a falta "
               "de resposta, ao pedido de prorrogação de [[data]], para demonstrar que não houve a análise "
               "exigida pelo MCR 2-6-4;"),
        ("iii", "o [[plano simples / projeto técnico]], o Orçamento de Aplicação, os laudos de assistência "
                "técnica (MCR 1-3-5) e os registros de fiscalização da operação (MCR 2-7-1), para "
                "demonstrar o que o banco sabia sobre os eventos prejudiciais à produção;"),
        ("iv", "ou, no mesmo prazo, a declaração expressa de que os documentos dos itens ii e iii não "
               "existem."),
    ])

    vl.paragrafo(
        doc,
        "Os documentos são comuns às partes, porque se referem à relação contratual entre elas, o que "
        "impede a recusa (art. 399, III, do CPC). Não exibidos nem declarados inexistentes no prazo, os "
        "fatos que por meio deles se pretendia provar devem ser admitidos como verdadeiros (art. 400, I, do "
        "CPC). O Código de Defesa do Consumidor (art. 6º, VIII) reforça a mesma conclusão, mas o pedido não "
        "depende dele: basta a regra processual.")

    # ------------------------------------------------------------------
    # VI — Gratuidade
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "VI", "Da gratuidade da justiça")

    vl.paragrafo(
        doc,
        "O autor é pessoa natural e não pode arcar com custas e honorários sem prejuízo do próprio "
        "sustento, situação que decorre do mesmo evento que fundamenta a prorrogação. A alegação de "
        "insuficiência deduzida por pessoa natural presume-se verdadeira (art. 99, § 3º, do CPC), e o "
        "pedido só pode ser indeferido após intimação para comprovar os pressupostos (art. 99, § 2º). "
        "Instruem o pedido [[declaração de hipossuficiência, extratos, IRPF ou declaração de isenção, "
        "comprovantes de despesas]] (Doc. [[nº]]).")

    vl.pendencia(
        doc,
        "Operação de valor alto com garantia real costuma levar o juízo a pedir documentos (art. 99, § 2º). "
        "Juntar desde já extratos dos últimos meses, despesas da atividade e da família e a situação do "
        "IRPF. Não reproduzir aqui jurisprudência genérica de outros temas.")

    # ------------------------------------------------------------------
    # VII — Pedidos
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "VII", "Dos pedidos")

    vl.paragrafo(doc, "Diante do exposto, requer-se, nesta ordem:")

    vl.rol_de_pedidos(doc, [
        ("a", "a concessão da gratuidade da justiça;"),
        ("b", "a concessão, em caráter liminar, da tutela de urgência de natureza cautelar para, quanto às "
              "operações [[nº das cédulas]], até o julgamento final: (b.1) suspender a exigibilidade das "
              "operações; (b.2) suspender os efeitos da mora, vedada a cobrança de encargos moratórios; "
              "(b.3) determinar que o réu se abstenha de inscrever, ou exclua em 5 (cinco) dias, o nome do "
              "autor e dos garantidores em SERASA, SPC, cartórios de protesto[[, CADIN]] e no Sistema de "
              "Informações de Crédito do Banco Central (SCR), expedindo-se ofício ao Banco Central do "
              "Brasil; (b.4) determinar que o réu se abstenha de qualquer ato constritivo, expropriatório "
              "ou de consolidação sobre as garantias, mantidas as garantias pactuadas; (b.5) fixar multa "
              "diária para o descumprimento (art. 537 do CPC); (b.6) determinar que o réu se abstenha de "
              "declarar o vencimento antecipado das operações e de debitar ou compensar em conta valores a elas "
              "relativos; apreciando-se cada item separadamente;"),
        ("c", "subsidiariamente ao pedido \"b\", a designação de audiência de justificação prévia antes da "
              "decisão sobre a tutela (art. 300, § 2º, do CPC);"),
        ("d", "a dispensa de caução (art. 300, § 1º, do CPC);"),
        ("e", "[[a suspensão da Execução/Monitória nº (…), em curso perante (…), nos termos do art. 313, V, "
              "\"a\", do CPC, oficiando-se aquele juízo. Apagar se não houver.]]"),
        ("f", "a distribuição do ônus da prova ao réu (art. 373, § 1º, do CPC) e a exibição dos documentos "
              "relacionados no tópico V, em 15 (quinze) dias, ou a declaração expressa de sua inexistência, "
              "sob a consequência do art. 400 do CPC;"),
        ("g", "a citação do réu para, querendo, contestar;"),
        ("h", "no mérito, a condenação do réu na obrigação de prorrogar as operações [[nº]], aos mesmos "
              "encargos financeiros pactuados, com [[carência de (…) meses e reembolso em (…) parcelas "
              "anuais, vencendo-se a primeira em (…)]], conforme o laudo de capacidade de pagamento, "
              "formalizando a prorrogação no prazo de 15 (quinze) dias do trânsito em julgado, sob multa "
              "diária (arts. 497 e 537 do CPC), e, não o fazendo, que a sentença produza os efeitos da "
              "declaração não emitida (art. 501 do CPC);"),
        ("i", "subsidiariamente ao pedido \"h\", a prorrogação no cronograma que Vossa Excelência entender "
              "compatível com a capacidade de pagamento demonstrada (art. 326 do CPC);"),
        ("j", "a declaração de que as parcelas não eram exigíveis nos vencimentos originais e de que não há "
              "mora imputável ao autor, afastados os encargos moratórios desde [[data do pedido / do "
              "vencimento]], confirmando-se em definitivo a tutela concedida;"),
        ("k", "a produção de prova documental, já juntada, e da exibição requerida; a homologação dos fatos "
              "técnicos constantes dos laudos, com a oitiva do responsável técnico; e, se o réu impugnar a "
              "metodologia dos laudos, ou subsidiariamente, perícia "
              "agronômica e de capacidade de pagamento, e prova testemunhal sobre o pedido feito ao banco;"),
        ("l", "[[a realização da audiência de conciliação, preferencialmente por meio eletrônico (art. 334, "
              "§ 7º, do CPC) / o desinteresse na audiência de conciliação (art. 334, § 5º)]];"),
        ("m", "que as intimações sejam feitas em nome dos advogados [[nomes e OAB]], sob pena de nulidade "
              "(art. 272, § 5º, do CPC);"),
        ("n", "a condenação do réu nas custas e nos honorários advocatícios."),
    ])

    # ------------------------------------------------------------------
    # VIII — Valor da causa
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "VIII", "Do valor da causa")

    vl.paragrafo(
        doc,
        "Dá-se à causa o valor de R$ [[valor]] ([[por extenso]]), correspondente [[ao saldo das operações "
        "cuja prorrogação se pede]], por ser a ação relativa ao cumprimento e à modificação do ato "
        "jurídico (art. 292, II, do CPC).")

    vl.pendencia(
        doc,
        "Não usar valor simbólico: o juiz corrige de ofício quando o valor não corresponde ao conteúdo "
        "patrimonial em discussão (art. 292, § 3º, do CPC).")

    # ------------------------------------------------------------------
    # Fecho
    # ------------------------------------------------------------------
    vl._espaco(doc, 12)
    _centro(doc, "Nestes termos,", espaco=0)
    _centro(doc, "Pede deferimento.", espaco=10)
    _centro(doc, "[[CIDADE]]/[[UF]], [[DATA]].", espaco=24)

    _centro(doc, "RENAN GOMES MALDONADO DE JESUS", negrito=True, espaco=0)
    _centro(doc, "OAB/RO 5769", espaco=18)
    _centro(doc, "[[NOME DO SEGUNDO SUBSCRITOR]]", negrito=True, espaco=0)
    _centro(doc, "[[OAB/UF Nº]]", espaco=0)

    return doc


# Termos de revisional que não podem aparecer como pedido ou tese nesta ação
# (ajuste 3 da devolutiva da GJ de 08/08/2026). A menção NEGATIVA ("não se pede
# revisão") é legítima e esperada; a varredura lista para conferência humana.
TERMOS_REVISIONAIS = [
    "revisar os encargos", "revisão dos encargos", "revisão de cláusulas", "abusividade",
    "capitalização mensal", "limite de 12%", "lei da usura", "repetição de indébito",
    "diminuição do saldo devedor", "recálculo",
]


def varrer_lexico_revisional(doc):
    textos = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        if "APAGUE ESTE QUADRO" in t.cell(0, 0).text.upper():
            continue
        for linha in t.rows:
            for cel in linha.cells:
                textos.append(cel.text)
    achados = []
    for texto in textos:
        baixo = texto.lower()
        for termo in TERMOS_REVISIONAIS:
            if termo in baixo:
                pos = baixo.index(termo)
                achados.append((termo, texto[max(0, pos - 70):pos + 70].strip()))
    return achados


def main():
    doc = construir()
    doc.save(SAIDA)
    print("Modelo gerado: %s" % SAIDA)
    print("Ficha das provas (automação): %s · %d provas" % (gravar_ficha_provas(), len(PROVAS)))
    print("Parágrafos: %d | Tabelas: %d" % (len(doc.paragraphs), len(doc.tables)))

    orfaos = vl.varrer_marcadores_print(doc)
    print("Marcadores de print: %s" % ("todos em par" if not orfaos else orfaos))

    emb = vl.varrer_lexico_embargos(doc)
    print("Vocabulário de embargos: %s" % ("limpo" if not emb else [a[1] for a in emb]))

    rev = varrer_lexico_revisional(doc)
    if rev:
        print("\nVocabulário revisional — conferir se é menção NEGATIVA (\"não se pede\"):")
        for termo, trecho in rev:
            print("  · %-28s %s" % (termo, trecho))
    else:
        print("Vocabulário revisional: limpo")

    faltam = [k for k in (
        "Súmula 298 aplicada pelo tribunal que vai julgar",
        "Desnecessidade de requerimento administrativo prévio (STJ)",
        "Desnecessidade de requerimento prévio ou pedido após o vencimento (tribunal local)",
        "Laudo técnico particular suficiente em cognição sumária",
        "Tutela cautelar em ação de prorrogação: suspensão da exigibilidade e baixa de restrições",
    ) if k not in PRECEDENTES]
    if faltam:
        print("\nPrecedentes ainda como [[CONFERIR]]: %d" % len(faltam))
        for k in faltam:
            print("  · %s" % k)


if __name__ == "__main__":
    main()
