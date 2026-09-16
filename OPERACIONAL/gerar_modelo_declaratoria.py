# -*- coding: utf-8 -*-
"""Gera o modelo mestre da AÇÃO DECLARATÓRIA DE DESCARACTERIZAÇÃO DA MORA.

    ./.venv/bin/python OPERACIONAL/gerar_modelo_declaratoria.py

O .docx é artefato; **este script é a fonte versionada** (mesma lógica dos .md
de `docs/`, que são versionados enquanto os .pdf não). Para alterar o modelo,
altere aqui e regenere — nunca edite o .docx à mão, ou a próxima regeneração
apaga a alteração.

O texto-base é a peça real de um caso do escritório x Banco do Brasil
(Cédula Rural Pignoratícia, 4ª Vara Cível de Porto Velho), generalizada em
campos `[[ASSIM]]` e reestruturada segundo a skill `descaracterizacao-mora`
v4.15. Os componentes visuais saem de `OPERACIONAL/visual_law.py`; o porquê de
cada um está em `.claude/skills/descaracterizacao-mora/MODELO_INICIAL.md`.

Enxugamento de 10/09/2026 (Dra. Juliana): peça do padrão Dr. Marcello é curta e
certeira, não longa. A primeira versão do modelo saiu com 28 tabelas para 3.700
palavras — corrigiu o excesso da peça original (99 parágrafos, zero tabelas) e
passou do ponto para o outro lado. Foram removidos os componentes que apenas
repetiam em quadro o que o parágrafo ao lado já dizia: a caixa DELIMITAÇÃO DA
CONTROVÉRSIA (repetia o quadro EM SÍNTESE), a cadeia dos dois elos, o quadro do
ônus argumentativo do distinguishing, a conclusão do tópico III.1, o quadro dos
requisitos do art. 311, a Súmula 541 transcrita (já está na linha ERRO FATAL do
quadro comparativo) e um dos três badges de precedente do STJ sobre a MESMA tese
— os julgados repetidos passaram a citação em linha. **Não reintroduzir**: o que
ficou são os quadros que fazem trabalho argumentativo (declara × omite, linha do
tempo com a fase contratual, execução conexa, badge do vinculante), e acumular
precedente sobre tese única dilui, não reforça (seção 12 da skill).
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
SAIDA = os.path.join(RAIZ, "DOCS_MODELOS",
                     "MODELO_DECLARATORIA_DESCARACTERIZACAO_MORA.docx")


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


def construir():
    doc = Document(TIMBRADO)

    # ------------------------------------------------------------------
    # Bloco de instruções — o único elemento que NÃO faz parte da peça
    # ------------------------------------------------------------------
    vl.caixa(
        doc,
        "MODELO — APAGUE ESTE QUADRO ANTES DE ENTREGAR A PEÇA PARA REVISÃO",
        "Antes de entregar: (1) confirme no PJe, por CPF e por número de contrato, se já existe "
        "execução sobre este mesmo título — havendo execução, a via provavelmente é embargos, e a "
        "escolha é do advogado responsável (Restrição Absoluta nº 20) — havendo, o número da "
        "execução tem de aparecer na linha de distribuição por dependência do endereçamento e na "
        "seção II; não havendo, registre no histórico do caso a data da pesquisa; (2) rode a "
        "varredura léxica "
        "de vocabulário de embargos — nenhuma ocorrência de \"embargos\", \"embargante\", \"efeito "
        "suspensivo\", \"art. 919, § 1º\" ou \"garantia do juízo\" pode sobrar numa declaratória "
        "(Restrição Absoluta nº 19: OPERACIONAL/visual_law.py, varrer_lexico_embargos); "
        "(3) confira que nenhum pedido de prova pericial contábil entrou no rol, nem em caráter "
        "subsidiário (Restrição Absoluta nº 18); (4) confira que nenhum quadro traz taxa calculada "
        "pelo escritório onde o título é omisso — a célula diz \"não consta\" (Restrição Absoluta "
        "nº 15); (5) confira que todo print entrou EM PAR — o recorte e a transcrição do que ele "
        "mostra ([[INSERIR PRINT nn]] + [[TEXTO DO PRINT nn]]), porque imagem no PJe não é "
        "pesquisável nem copiável (OPERACIONAL/visual_law.py, varrer_marcadores_print); "
        "(6) resolva ou mantenha sinalizadas, em amarelo, todas as pendências documentais.",
        vl.VERMELHO)

    # ------------------------------------------------------------------
    # Endereçamento
    # ------------------------------------------------------------------
    vl.paragrafo(
        doc,
        "EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DE DIREITO DA [[Nº]]ª VARA CÍVEL DA "
        "COMARCA DE [[COMARCA]], ESTADO DE [[ESTADO]]",
        negrito=True)

    vl.pendencia(
        doc,
        "Distribuição por dependência: incluir a linha abaixo SOMENTE se houver execução ou busca "
        "e apreensão em curso sobre o mesmo título e a opção consciente do advogado responsável "
        "tiver sido pela declaratória autônoma (ver seção 13bis da skill). Caso contrário, apagar. "
        "Texto: \"Distribuição por dependência aos autos da Execução de Título Extrajudicial nº "
        "[[Nº DA EXECUÇÃO]], em curso perante este Juízo (art. 286, I, do CPC).\"")

    vl._espaco(doc, 12)

    # ------------------------------------------------------------------
    # Qualificação
    # ------------------------------------------------------------------
    vl.paragrafo(
        doc,
        "[[NOME DO CLIENTE]], [[nacionalidade]], [[estado civil]], [[profissão]], portador da "
        "Cédula de Identidade nº [[RG]] [[órgão]], inscrito no CPF sob o nº [[CPF]], residente e "
        "domiciliado em [[ENDEREÇO COMPLETO]], vem, por seus advogados que esta subscrevem, com "
        "fundamento no art. 19, I, do Código de Processo Civil, propor")

    _centro(doc, "AÇÃO DECLARATÓRIA DE DESCARACTERIZAÇÃO DA MORA", negrito=True, espaco=0)
    _centro(doc, "com pedido de tutela da evidência (art. 311, II, do CPC)", espaco=10)

    vl.paragrafo(
        doc,
        "em face de [[NOME DO BANCO]], [[natureza jurídica]], inscrito no CNPJ sob o nº [[CNPJ]], "
        "com sede em [[ENDEREÇO DA SEDE]], pelos fundamentos de fato e de direito a seguir "
        "expostos.")

    # ------------------------------------------------------------------
    # Síntese
    # ------------------------------------------------------------------
    vl.sintese_da_controversia(
        doc,
        o_que_se_pede=(
            "A declaração de que a mora do autor está descaracterizada quanto à "
            "[[ESPÉCIE E Nº DO TÍTULO]] e, por consequência, de que o título não é exigível."),
        por_que=(
            "O réu exigiu, no período de normalidade contratual e antes de qualquer "
            "inadimplemento, capitalização de juros sem que o instrumento indicasse a taxa "
            "correspondente à periodicidade em que ela se opera. Verificada a abusividade em "
            "encargo da normalidade, a descaracterização da mora é consequência automática da "
            "Orientação 2 do Tema 28/STJ, precedente de observância obrigatória."),
        o_que_nao_se_pede=(
            "Não se pede revisão de cláusulas, recálculo de prestações, repetição de indébito "
            "nem apuração de saldo devedor. Não há, portanto, valor incontroverso a depositar, "
            "nem matéria que dependa de perícia: a prova é o próprio instrumento contratual."))

    # ------------------------------------------------------------------
    # I — Natureza da ação
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "I", "Da natureza da ação e da audiência de conciliação")

    vl.paragrafo(
        doc,
        "Trata-se de ação estritamente declaratória (art. 19, I, do CPC), de pedido único: a "
        "declaração de descaracterização da mora. Não se postula recálculo, revisão de cláusulas, "
        "repetição de indébito nem apuração de saldo devedor, e a causa de pedir esgota-se em "
        "uma verificação objetiva: houve, ou não, exigência de encargo abusivo no período de "
        "normalidade contratual. Exigir depósito do incontroverso, caução ou perícia seria impor "
        "requisito estranho ao pedido (art. 492 do CPC): tais condicionantes constam da "
        "Orientação 4 do REsp 1.061.530/RS, que rege hipótese diversa (a vedação de inscrição em "
        "cadastro de inadimplentes antes da sentença), ao passo que a Orientação 2, aqui "
        "invocada, é autoaplicável.")

    vl.paragrafo(
        doc,
        "O autor manifesta interesse na realização da audiência de conciliação prevista no art. "
        "334 do CPC, nos termos do art. 3º, §§ 2º e 3º, do CPC.")

    # ------------------------------------------------------------------
    # II — Síntese do caso
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "II", "Da síntese do caso")

    vl.paragrafo(
        doc,
        "Em [[DATA DE EMISSÃO]], o autor emitiu, em favor do réu, a [[ESPÉCIE E Nº DO TÍTULO]], "
        "no valor de R$ [[VALOR]] ([[VALOR POR EXTENSO]]), destinada a [[FINALIDADE DECLARADA NO "
        "TÍTULO]] (Doc. [[Nº]]).")

    vl.paragrafo(
        doc,
        "O pagamento foi ajustado em [[Nº]] prestações [[periodicidade]] e sucessivas, vencendo-se "
        "a primeira em [[DATA]] e a última em [[DATA]].")

    vl.linha_do_tempo(doc, [
        ("[[DATA]]", "Emissão do título e liberação do crédito", vl.FASE_NORMALIDADE, "Doc. [[Nº]]"),
        ("[[DATA]]", "Incidência do encargo impugnado: [[descrever o lançamento]]",
         vl.FASE_NORMALIDADE, "Doc. [[Nº]]"),
        ("[[DATA]]", "Vencimento da primeira prestação", vl.FASE_NORMALIDADE, "Doc. [[Nº]]"),
        ("[[DATA]]", "Primeiro inadimplemento", vl.FASE_INADIMPLEMENTO, "Doc. [[Nº]]"),
        ("[[DATA]]", "[[Ajuizamento da execução / notificação / protesto, se houver]]",
         vl.FASE_INADIMPLEMENTO, "Doc. [[Nº]]"),
    ])

    vl.pendencia(
        doc,
        "A linha do tempo só entra na peça com as datas efetivamente extraídas do título e do "
        "demonstrativo. Data que não puder ser conferida no documento sai da tabela. Linha do "
        "tempo com data suposta é prova contra a própria peça. Se o demonstrativo não permitir "
        "identificar a data do primeiro inadimplemento, registre a pendência em vez de estimá-la.")

    vl.paragrafo(
        doc,
        "Em [[DATA]], o réu [[ajuizou execução de título extrajudicial fundada nessa mesma "
        "cédula, autuada sob o nº (…) / promoveu (…)]].")

    vl.paragrafo(
        doc,
        "Embora tenha havido inadimplemento que, a princípio, configuraria mora, esta deve ser "
        "declarada descaracterizada. O réu exigiu, no período de normalidade contratual e antes "
        "de qualquer atraso, encargo abusivo e, nos termos do Tema 28/STJ, a abusividade "
        "verificada na normalidade retira da mora a validade jurídica.")

    # ------------------------------------------------------------------
    # III — Do direito
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "III", "Do direito")

    _subtitulo(doc, "III.1. Da aplicação do Código de Defesa do Consumidor")

    vl.paragrafo(
        doc,
        "Aplica-se à relação que deu origem ao título o Código de Defesa do Consumidor. De um "
        "lado está a instituição financeira ré, que atua no mercado com finalidade de lucro, "
        "ofertando serviços financeiros de forma contínua e profissional; de outro, o autor, que "
        "os contrata sem deter o mesmo nível de conhecimento técnico, jurídico ou econômico. Os "
        "serviços bancários enquadram-se no conceito legal de serviço do art. 3º, § 2º, do CDC, e "
        "a constitucionalidade dessa incidência foi assentada pelo Supremo Tribunal Federal no "
        "julgamento da ADI 2.591/DF, consolidando-se na Súmula 297 do Superior Tribunal de "
        "Justiça: \"O Código de Defesa do Consumidor é aplicável às instituições financeiras\".")

    vl.paragrafo(
        doc,
        "O fato de o crédito ter sido tomado para viabilizar atividade produtiva não afasta essa "
        "incidência. Embora a literalidade do art. 2º do CDC sugira a teoria finalista estrita, o "
        "Superior Tribunal de Justiça consolidou, por interpretação teleológica e com apoio no "
        "conceito de consumidor por equiparação do art. 29, a teoria finalista mitigada, também "
        "dita finalismo aprofundado, pela qual as normas consumeristas incidem sempre que "
        "demonstrada a vulnerabilidade de uma das partes frente à outra, em qualquer de suas "
        "modalidades: técnica, jurídica, fática ou informacional. A vulnerabilidade é o "
        "princípio-motor da política nacional das relações de consumo (art. 4º, I, do CDC). Em "
        "cédula de crédito rural a questão está decidida: presume-se a vulnerabilidade do "
        "produtor, equiparado a consumidor ainda quando o financiamento se destina à sua própria "
        "atividade, dando-se prevalência à destinação fática (REsp 1.166.054/RN, Rel. Min. Luis "
        "Felipe Salomão, 4ª Turma, DJe 18/06/2015).")

    vl.paragrafo(
        doc,
        "No caso concreto, a vulnerabilidade do autor não é presunção invocada de passagem: é "
        "técnica e informacional, e mede-se exatamente pela impossibilidade de apurar, sozinho, o "
        "encargo que lhe seria cobrado. O autor é [[produtor rural / pecuarista / agricultor]], "
        "pessoa natural, que não redigiu uma linha do instrumento: a cédula é formulário padrão "
        "do réu, de cláusulas impressas e sem possibilidade real de negociação, isto é, contrato "
        "de adesão (art. 54 do CDC), cujo § 4º ainda exige que a cláusula limitativa de direito "
        "seja redigida com destaque e permita compreensão imediata e fácil.")

    vl.paragrafo(
        doc,
        "Reconhecida a relação de consumo, as normas consumeristas incidem inclusive para efeito "
        "de interpretação das cláusulas contratuais, de inversão do ônus da prova e de controle "
        "judicial da legalidade dos encargos exigidos. Três delas regem diretamente a cláusula "
        "impugnada: o art. 6º, III, que assegura a informação adequada e clara sobre o preço e os "
        "acréscimos; o art. 52, II, que impõe ao fornecedor informar prévia e adequadamente a "
        "taxa de juros no financiamento; e, sobretudo, o art. 46, segundo o qual o contrato "
        "redigido de modo a dificultar a compreensão de seu sentido e alcance NÃO OBRIGA o "
        "consumidor. São exatamente os três dispositivos que o Superior Tribunal de Justiça "
        "invocou ao inaugurar a tese da capitalização sem taxa expressa (REsp 1.568.290/RS, voto "
        "do Rel. Min. Paulo de Tarso Sanseverino).")

    vl.paragrafo(
        doc,
        "Registre-se, por fim, que a tese não depende exclusivamente do Código. Ainda que se "
        "afastasse sua incidência, a exigência de pactuação expressa da capitalização em "
        "periodicidade inferior à anual é autônoma, por força das Súmulas 539 e 93 do STJ, e a boa-fé "
        "objetiva (art. 422 do Código Civil) impõe ao credor o dever anexo de informar o conteúdo "
        "do encargo que cobra. Por qualquer das vias, a omissão do número não se sana.")

    _subtitulo(doc, "III.2. Da distinção entre juros compostos e capitalização")

    vl.paragrafo(
        doc,
        "O Superior Tribunal de Justiça fixou, no REsp 973.827/RS (Tema 247, Rel. p/ acórdão "
        "Min. Maria Isabel Gallotti, 2ª Seção, DJe 24/09/2012), origem das Súmulas 539 e 541, a "
        "distinção que delimita esta demanda:")

    vl.quadro_comparativo(
        doc,
        "JUROS COMPOSTOS × CAPITALIZAÇÃO (Tema 247/STJ, REsp 973.827/RS)",
        "Regime de juros compostos", "Capitalização (sentido jurídico)",
        [
            ("Natureza", "Categoria matemática: método de formação da taxa",
             "Instituto jurídico: incorporação de juros vencidos ao principal"),
            ("Pressupõe mora?", "Não. Opera com o contrato em dia",
             "Sim. Pressupõe juros vencidos e não pagos"),
            ("O que o autor discute", "Nada. Não se impugna o regime composto",
             "A ausência da taxa correspondente à periodicidade pactuada"),
        ],
        linha_erro=(
            "ERRO FATAL",
            "Tratar o teste do duodécuplo (Súmula 541/STJ) como prova de pactuação",
            "A Súmula 541 afere taxa; não supre a pactuação expressa que a Súmula 539 exige"))

    vl.paragrafo(
        doc,
        "Não se impugna, pois, o regime composto, nem a licitude da capitalização em "
        "periodicidade inferior à anual. Impugna-se a exigência do encargo sem que o título "
        "informe a taxa da periodicidade em que ele se opera.")

    _subtitulo(doc, "III.3. Da abusividade da capitalização: o título declara o evento e omite a taxa")

    vl.paragrafo(
        doc,
        "A cláusula [[NOME DA CLÁUSULA]] da [[ESPÉCIE E Nº DO TÍTULO]] tem a seguinte redação, no "
        "que interessa:")

    vl.precedente(
        doc,
        "[[TEXTO DO PRINT 01: transcrição literal da cláusula, copiada do título, sem corte que "
        "descaracterize o sentido]]",
        "[[ESPÉCIE E Nº DO TÍTULO]], cláusula [[NOME]]", vl.TITULO_CONTRATUAL,
        realce=["CAPITALIZADOS", "CAPITALIZAÇÃO", "TAXA EQUIVALENTE DIÁRIA",
                "TAXA EQUIVALENTE MENSAL", "DIAS CORRIDOS", "PRIMEIRO DIA DE CADA MES",
                "PRIMEIRO DIA DE CADA MÊS"])

    vl.marcador_print(
        doc, 1,
        "recorte da cláusula de encargos financeiros: faixa de largura total da página (nunca "
        "recorte estreito, que corta a linha no meio), com os termos da capitalização grifados "
        "em amarelo e a legenda citando a folha E a expressão \"grifo nosso\"",
        transcrever=False)

    vl.caixa_prova(
        doc,
        "Nos trechos grifados o réu declara QUANDO capitaliza: por dias corridos, com base em "
        "taxa equivalente diária, no primeiro dia de cada mês. Em nenhum ponto declara A QUE "
        "TAXA. O único percentual do instrumento é o de 4% ao ano, de outra periodicidade: para "
        "aquela em que a capitalização efetivamente se opera, o título é omisso.")

    vl.paragrafo(
        doc,
        "A leitura da cláusula revela dois planos que não se confundem e que precisam ser "
        "verificados separadamente.")

    vl.quadro_declara_omite(
        doc,
        declara=[
            ("O evento da capitalização",
             "O título diz quando a capitalização ocorre: [[transcrever o trecho, ex.: "
             "\"debitados e capitalizados no primeiro dia de cada mês\"]]."),
            ("A licitude desse evento",
             "Nada há de ilícito na periodicidade em si, desde que pactuada, na forma da Súmula 539/STJ e, "
             "em cédula rural, Súmula 93/STJ. O autor não a impugna."),
        ],
        omite=[
            ("A taxa da periodicidade pactuada",
             "Para a periodicidade [[diária/mensal]] em que a capitalização efetivamente se "
             "opera, o instrumento NÃO CONSTA taxa alguma."),
            ("O único percentual declarado",
             "O título informa apenas a taxa [[anual/efetiva]] de [[X]]%, que é de outra "
             "periodicidade e não supre a omissão."),
        ])

    vl.paragrafo(
        doc,
        "A clareza quanto ao evento não supre a omissão quanto à taxa: são exigências autônomas. "
        "A Súmula 539/STJ exige pactuação expressa da capitalização inferior à anual, e pactuar "
        "expressamente um encargo financeiro compreende o percentual que o quantifica. Dizer "
        "quando os juros são capitalizados, sem dizer a que taxa, é pactuar a metade do encargo e "
        "cobrar o todo. É a violação ao dever de informação demonstrada no item III.1 (arts. 6º, "
        "III, 46 e 52, II, do CDC), agora aplicada ao encargo concreto deste título.")

    vl.precedente(
        doc,
        "Necessidade de fornecimento, pela instituição financeira, de informações claras ao "
        "consumidor acerca da periodicidade da capitalização dos juros adotada no contrato, e da "
        "taxa de juros correspondente a essa periodicidade, sendo insuficiente a informação "
        "apenas das taxas efetivas mensal e anual.",
        "STJ, REsp 1.826.463/SC, Rel. Min. Paulo de Tarso Sanseverino, 2ª Seção, DJe 29/10/2020",
        vl.STJ)

    vl.paragrafo(
        doc,
        "A orientação é firme: REsp 1.568.290/RS (3ª Turma, DJe 02/02/2016), precedente inaugural "
        "da tese; AgInt no REsp 2.024.575/RS (3ª Turma, DJe 19/04/2023); REsp 2.254.100/RS (3ª "
        "Turma, DJEN 16/04/2026); e AgInt nos EDcl no REsp 2.230.328/SC (4ª Turma, DJEN "
        "22/04/2026). A observância do limite anual pactuado não supre a ausência da taxa "
        "correspondente à periodicidade em que a capitalização se opera.")

    vl.pendencia(
        doc,
        "Substituir o parágrafo e o precedente acima pelo julgado do tribunal a que a peça se "
        "dirige, quando houver. Precedente do próprio tribunal de origem pesa mais do que "
        "acúmulo de julgados de outras cortes. Ver seção 16 da skill e o ACERVO.md.")

    vl.precedente(
        doc,
        "[[TRANSCREVER A EMENTA DO TRIBUNAL DE ORIGEM]]",
        "[[TRIBUNAL, classe e nº, Câmara, Rel. Des. (…), j. (…)]]", vl.TRIBUNAL)

    vl.paragrafo(
        doc,
        "Em crédito rural a exigência é ainda mais estrita: o Superior Tribunal de Justiça já "
        "corrigiu, precisamente, o uso da Súmula 541, que afere o regime matemático dos juros, "
        "para suprir a ausência de cláusula expressa quanto à taxa da periodicidade adotada "
        "(REsp 2.214.495/MG, Rel. Min. Raul Araújo, DJEN 26/03/2026).")

    vl.paragrafo(
        doc,
        "Por fim, e para que não reste dúvida quanto ao alcance do pedido, a incidência do "
        "encargo impugnado se deu no período de normalidade contratual, conforme a linha do tempo "
        "acima e a segregação que o próprio demonstrativo do réu apresenta entre a coluna do "
        "período de normalidade e a do período de inadimplemento.")

    vl.marcador_print(
        doc, 2,
        "recorte do demonstrativo de débito / ficha gráfica mostrando a segregação entre a coluna "
        "do período de normalidade e a do período de inadimplemento; o recorte TEM de mostrar a "
        "normalidade; recorte só da coluna de inadimplência contradiz o Elo 1",
        transcrever="transcrever os lançamentos do período de normalidade que o recorte mostra: "
                    "data, histórico e valor, linha a linha, sem calcular nada a partir deles "
                    "(Restrição Absoluta nº 15)")

    vl.pendencia(
        doc,
        "Documento indispensável. Sem ele, não afirmar \"conforme documento anexo\". A pendência "
        "fica em amarelo na peça até o demonstrativo ser localizado na pasta do cliente.")

    vl.caixa_conclusao(
        doc,
        "Está configurado o Elo 1 do Tema 28/STJ: encargo abusivo exigido no período de "
        "normalidade contratual, demonstrado pela simples leitura do título, sem necessidade de "
        "qualquer dilação probatória.")

    _subtitulo(doc, "III.4. Dos juros remuneratórios: verificação e conclusão")

    vl.paragrafo(
        doc,
        "O Tema 28/STJ admite dois fundamentos independentes para a abusividade dos encargos da "
        "normalidade: a capitalização e os juros remuneratórios. Por dever de precisão, e para "
        "que a delimitação da causa de pedir fique inequívoca, registra-se o resultado da "
        "verificação do segundo.")

    vl.pendencia(
        doc,
        "Escolher UMA das duas redações abaixo e apagar a outra. A verificação dos dois encargos "
        "é obrigatória mesmo quando um deles dá negativo (Restrição Absoluta nº 12); o que se "
        "escolhe é a redação, nunca deixar de verificar.\n"
        "(A) NÃO HÁ ABUSIVIDADE: \"A cédula pactua juros à taxa efetiva de [[X]]% ao ano, "
        "percentual inferior ao teto de 12% ao ano que o Decreto 22.626/33 impõe às operações de "
        "crédito rural na ausência de fixação pelo Conselho Monetário Nacional quanto a recursos "
        "não controlados. Não há, portanto, abusividade dos juros remuneratórios nesta operação, "
        "e nada se pede a esse título. O Elo 1 do Tema 28/STJ apoia-se, nesta demanda, "
        "exclusivamente na capitalização.\"\n"
        "(B) HÁ ABUSIVIDADE: desenvolver como fundamento autônomo do Elo 1, pela via do teto "
        "legal do crédito rural (seção 9.1 da skill) ou, em contrato NÃO rural, pela superação de "
        "1,5 vez a taxa média de mercado do BACEN (seção 3.4), registrando o número da série "
        "temporal e a data da extração.")

    _subtitulo(doc, "III.5. Da inexigibilidade do título: Tema 28/STJ e nulidade da execução")

    vl.paragrafo(
        doc,
        "A abusividade demonstrada no item III.3, exigida integralmente no período de normalidade "
        "contratual, atrai a tese vinculante fixada pelo Superior Tribunal de Justiça no "
        "julgamento do recurso representativo da controvérsia:")

    vl.precedente(
        doc,
        "O reconhecimento da abusividade nos encargos exigidos no período da normalidade "
        "contratual (juros remuneratórios e capitalização) descaracteriza a mora.",
        "STJ, Tema 28, REsp 1.061.530/RS, Rel. Min. Nancy Andrighi, 2ª Seção, DJe 10/03/2009, "
        "Orientação 2", vl.VINCULANTE)

    vl.paragrafo(
        doc,
        "O verbo é indicativo, não permissivo: não se autoriza o julgador a descaracterizar a "
        "mora, determina-se que a abusividade a descaracteriza. Sem mora válida não há vencimento "
        "antecipado; sem vencimento antecipado, o título carece de exigibilidade (art. 783 do "
        "CPC) e a execução é nula (art. 803, I, do CPC). Tampouco cabe remeter a matéria à "
        "liquidação: a descaracterização é efeito jurídico substantivo sobre a exigibilidade, e "
        "não questão de cálculo (STJ, AREsp 3.030.541/MG, Rel. Min. Raul Araújo, DJEN "
        "04/12/2025).")

    vl.paragrafo(
        doc,
        "Há, ainda, uma consequência lógica que o réu não contorna. Foi ele quem, ao incorporar "
        "ao saldo encargo cuja taxa não pactuou expressamente, tornou impossível o cumprimento da "
        "obrigação nos termos ajustados. O inadimplemento que hoje invoca como causa da execução "
        "foi provocado por sua própria conduta no período de normalidade, e ninguém pode alegar "
        "em favor próprio a mora que criou.")

    vl.paragrafo(
        doc,
        "Tampouco se sustenta a alegação de que a matéria ainda não estaria pacificada. O "
        "Superior Tribunal de Justiça indeferiu o Incidente de Assunção de Competência sobre o "
        "tema precisamente por já existir tese firmada em recurso repetitivo, faltando ao "
        "incidente o requisito da relevante questão de direito ainda não pacificada (art. 947 do "
        "CPC), conforme REsp 2.214.495/MG, Rel. Min. Raul Araújo, DJEN 26/03/2026.")

    vl.quadro_distinguishing(doc, [
        "Identificar, no caso concreto, elemento fático que o distinga do REsp 1.061.530/RS, "
        "não bastando afirmação genérica de que o contrato foi livremente pactuado.",
        "Enfrentar especificamente por que a capitalização exigida sem indicação da taxa da "
        "periodicidade não configuraria abusividade em encargo da normalidade.",
        "Decisão que rejeite precedente de observância obrigatória sem esse enfrentamento é "
        "decisão não fundamentada (art. 489, § 1º, VI, do CPC) e desafia, além do recurso "
        "cabível, a reclamação prevista no art. 988, IV, do CPC.",
    ])

    # ------------------------------------------------------------------
    # IV — Tutela da evidência
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "IV", "Da tutela da evidência (art. 311, II, do CPC)")

    vl.paragrafo(
        doc,
        "O pedido liminar deve ser apreciado como tutela da evidência, que dispensa a "
        "demonstração de perigo de dano ou de risco ao resultado útil do processo. Os dois "
        "requisitos do art. 311, II, do CPC estão integralmente preenchidos:")

    vl.paragrafo(
        doc,
        "Prova documental das alegações de fato: é o próprio título juntado com a inicial, pois a "
        "abusividade se afere pela leitura da cláusula, sem dilação probatória e sem perícia. "
        "Tese firmada em julgamento de casos repetitivos: Tema 28/STJ, REsp 1.061.530/RS, "
        "Orientação 2, de observância obrigatória (art. 927, III, do CPC).")

    _subtitulo(doc, "IV.1. Subsidiariamente, da tutela de urgência (art. 300 do CPC)")

    vl.paragrafo(
        doc,
        "Caso não se reconheçam preenchidos os requisitos da tutela da evidência, o que se admite "
        "apenas por argumentação, requer-se a tutela de urgência do art. 300 do CPC, cujos dois "
        "requisitos se verificam concretamente nestes autos.")

    vl.paragrafo(
        doc,
        "Da probabilidade do direito. Ela não decorre de alegação, mas de dois documentos e de um "
        "precedente: a cláusula [[NOME DA CLÁUSULA]] do título, que declara a capitalização e "
        "omite a taxa da periodicidade em que ela se opera; o demonstrativo elaborado pelo "
        "próprio réu, que lança esse encargo dentro do período de normalidade; e a Orientação 2 "
        "do Tema 28/STJ, de observância obrigatória. Não há fato controvertido a instruir, e sim "
        "subsunção de fato documentado a tese vinculante.")

    vl.paragrafo(
        doc,
        "Do perigo de dano. Ele não é, aqui, a perda patrimonial considerada em abstrato: é a "
        "interrupção do ciclo produtivo de que o autor vive. O autor explora [[ATIVIDADE: "
        "pecuária de corte / pecuária leiteira / lavoura de (…)]] em [[ÁREA E LOCALIZAÇÃO DO "
        "IMÓVEL]], atividade que depende de crédito renovado a cada ciclo para custear "
        "[[INSUMOS DO CICLO: sal mineral, silagem, ração, vacinas, sêmen / sementes, "
        "fertilizantes, defensivos]]. A mora indevidamente caracterizada produz, em cadeia: "
        "(i) restrição cadastral, que fecha o acesso ao crédito de custeio, inclusive às linhas "
        "oficiais de crédito rural, cuja concessão exige regularidade do tomador; (ii) sem "
        "custeio, o autor deixa de adquirir [[INSUMO CRÍTICO]] na janela de [[PERÍODO, SAFRA OU "
        "ESTAÇÃO]], que não se repete dentro do mesmo ciclo; (iii) sem esse insumo na janela "
        "própria, sobrevém [[CONSEQUÊNCIA FÍSICA: perda de peso e de escore do rebanho, queda de "
        "produtividade, descarte de matrizes, perda da safra]], com redução da receita "
        "exatamente no período em que ela seria necessária para pagar. O dano se realimenta: a "
        "mora indevida gera a incapacidade de pagamento que o réu depois invoca como prova da "
        "própria mora.")

    vl.paragrafo(
        doc,
        "Acrescente-se que a constrição recai sobre [[BENS CONSTRITOS OU AMEAÇADOS: os "
        "semoventes dados em penhor cedular / o maquinário / a área de produção]], que não "
        "constituem patrimônio de reserva, e sim o próprio instrumento da produção. Apreendê-los "
        "não antecipa a satisfação do crédito: suprime a fonte de onde ele poderia sair, com "
        "afronta ao princípio da menor onerosidade (art. 805 do CPC) e à função social da "
        "propriedade rural (art. 186, II e III, da Constituição).")

    vl.paragrafo(
        doc,
        "A medida requerida é integralmente reversível (art. 300, § 3º, do CPC): ela suspende os "
        "efeitos de uma mora cuja própria validade é o objeto desta ação e, julgada improcedente "
        "a demanda, o réu retoma a cobrança sem prejuízo algum. A irreversibilidade está do outro "
        "lado: [[O QUE NÃO SE RECOMPÕE: rebanho vendido em leilão, safra perdida, matrizes "
        "descartadas]] não se restitui por sentença.")

    vl.pendencia(
        doc,
        "Este é o tópico que a Gerência Jurídica mais devolve: \"a tutela de urgência está "
        "genérica, individualizar o perigo de dano e a probabilidade do direito ao caso "
        "concreto\" (5º apontamento mais frequente, jun-ago/2026). Substituir TODOS os campos "
        "acima por fatos do cliente: qual atividade, qual insumo, qual janela do ciclo, qual "
        "consequência física, quais bens. Tutela genérica é indeferida.")

    # ------------------------------------------------------------------
    # V — Gratuidade
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "V", "Da gratuidade de justiça")

    vl.paragrafo(
        doc,
        "O autor é [[produtor rural / pessoa natural]] e não possui condições de arcar com as "
        "custas processuais e com os honorários sem prejuízo do próprio sustento e do de sua "
        "família, razão por que requer os benefícios da gratuidade de justiça (art. 98 do CPC), "
        "cuja declaração goza de presunção de veracidade (art. 99, § 3º, do CPC).")

    vl.pendencia(
        doc,
        "Declaração de hipossuficiência assinada, documento indispensável ao pedido. Conferir "
        "também se há registro de gratuidade indeferida em processo conexo e, havendo, enfrentar "
        "o ponto em vez de repetir o pedido. Para pessoa jurídica, o pedido exige prova da "
        "impossibilidade (Súmula 481/STJ), e a via usual é o diferimento.")

    # ------------------------------------------------------------------
    # VI — Pedidos
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "VI", "Dos pedidos")

    vl.paragrafo(doc, "Diante do exposto, requer-se:")

    vl.rol_de_pedidos(doc, [
        ("a", "a concessão dos benefícios da gratuidade de justiça;"),
        ("b", "a concessão liminar da tutela da evidência (art. 311, II, do CPC), "
              "independentemente de demonstração de urgência, para afastar desde já todos os "
              "efeitos jurídicos da mora quanto à [[ESPÉCIE E Nº DO TÍTULO]], [[determinando-se a "
              "suspensão dos atos de constrição / abstenção de inscrição em cadastro restritivo / "
              "abstenção de apreensão do bem]];"),
        ("c", "subsidiariamente, a concessão de tutela de urgência (art. 300 do CPC) para os "
              "mesmos fins;"),
        ("d", "a citação do réu para, querendo, contestar a presente ação no prazo legal, sob "
              "pena de revelia;"),
        ("e", "no mérito, o reconhecimento da abusividade da capitalização de juros exigida no "
              "período de normalidade contratual, por ausência de indicação, no título, da taxa "
              "correspondente à periodicidade em que se opera;"),
        ("f", "a consequente declaração de descaracterização da mora do autor em relação à "
              "[[ESPÉCIE E Nº DO TÍTULO]], nos termos do Tema 28/STJ (Orientação 2, REsp "
              "1.061.530/RS), com eficácia de coisa julgada material;"),
        ("g", "a declaração de inexigibilidade do título executivo [[e a extinção da Execução nº "
              "(…), nos termos do art. 803, I, do CPC. Manter apenas se houver execução em "
              "curso]];"),
        ("h", "o julgamento antecipado do mérito (art. 355, I, do CPC), por ser a questão "
              "exclusivamente de direito e estar a matéria de fato integralmente comprovada pelos "
              "documentos que instruem esta inicial;"),
        ("i", "a condenação do réu ao pagamento das custas processuais e dos honorários "
              "advocatícios sucumbenciais, fixados nos termos do art. 85, § 2º, do CPC."),
    ])

    vl.paragrafo(doc, "Protesta provar o alegado pela prova documental já acostada.")

    vl.pendencia(
        doc,
        "Não incluir, aqui nem em qualquer outro ponto da peça, requerimento de prova pericial "
        "contábil, nem mesmo em caráter subsidiário. Restrição Absoluta nº 18: pedido "
        "subsidiário de perícia foi o fundamento textualmente citado para indeferir a tutela de "
        "evidência nos autos 0000000-00.0000.0.00.0000.")

    # ------------------------------------------------------------------
    # VII — Valor da causa
    # ------------------------------------------------------------------
    vl.titulo_secao(doc, "VII", "Do valor da causa")

    vl.paragrafo(
        doc,
        "Dá-se à causa o valor de R$ 1.000,00 (mil reais), por se tratar de pedido declaratório "
        "sem conteúdo econômico imediatamente aferível, não se postulando recálculo, restituição "
        "ou proveito patrimonial direto.")

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


def main():
    doc = construir()
    doc.save(SAIDA)

    achados = vl.varrer_lexico_embargos(doc)
    print("Modelo gerado: %s" % SAIDA)
    print("Parágrafos: %d | Tabelas: %d" % (len(doc.paragraphs), len(doc.tables)))

    orfaos = vl.varrer_marcadores_print(doc)
    if orfaos:
        print("\nMARCADORES DE PRINT ÓRFÃOS — %d:" % len(orfaos))
        for numero, falta in orfaos:
            print("  · print %s: %s" % (numero, falta))
    else:
        print("Marcadores de print: todos em par (imagem + texto).")
    if achados:
        print("\nVARREDURA LÉXICA (Restrição Absoluta nº 19) — %d ocorrência(s):" % len(achados))
        for _, termo, trecho in achados:
            print("  · %-22s %s" % (termo, trecho[:110]))
        print("\nConferir cada uma: em declaratória, só é aceitável a menção que descreva a "
              "execução do réu\n(\"execução de título extrajudicial\"), nunca pedido em nome próprio.")
    else:
        print("Varredura léxica: limpo — nenhum termo de embargos.")


if __name__ == "__main__":
    main()
