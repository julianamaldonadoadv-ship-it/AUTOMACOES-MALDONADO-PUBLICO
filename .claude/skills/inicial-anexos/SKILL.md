---
name: inicial-anexos
description: Documentos que instruem a petição inicial — localiza na pasta do cliente na ZEUS os documentos cabíveis à tese, confere o rol contra o que a ação exige, recorta a cláusula/página relevante e cola no placeholder do modelo de inicial. Use SEMPRE que for produzir, montar ou revisar uma petição inicial do escritório (alongamento, descaracterização de mora, mora c/c falha na assistência técnica, revisional) — junto com a skill `timbrado`, que cuida do papel e da formatação.
---

# Anexos da petição inicial — Maldonado Advogados

## Regra

Nenhuma inicial do escritório sai sem os documentos que a instruem, e os modelos de
inicial trazem **placeholders literais** onde o recorte do documento tem que entrar no
corpo da peça (`INSERIR UMA IMAGEM.`, `IMAGEM DO REQUERIMENTO QUE FOI ENVIADO AO BANCO`,
`INSERIR GRÁFICO`). Preencher isso na mão é o que consome a controladoria e é onde a
peça chega errada na revisão da Dra. Juliana.

Esta skill fecha esse ciclo: **pasta do cliente na ZEUS → rol da tese → recorte → placeholder**.

Ela **não** escolhe a tese, **não** inventa documento e **não** protocola. O que não
existir na pasta do cliente sai da peça como **pendência destacada em amarelo** — nunca
como suposição, nunca como frase genérica de "documento anexo".

Módulo: `OPERACIONAL/anexos_inicial.py` · CLI: `python OPERACIONAL/main.py anexos ...`

---

## Fluxo (6 passos)

### 1. Confirme a tese antes de qualquer coisa

O rol de documentos muda conforme a ação. As quatro do escritório:

| chave | ação |
|---|---|
| `alongamento` | Prorrogação/alongamento compulsório (MCR 2.6.4 + Súmula 298/STJ) |
| `mora` | Declaratória de descaracterização de mora (Tema 28/STJ) |
| `mora-assistencia` | Mora c/c falha na assistência técnica (Justiça Federal, réu CEF/BB) |
| `revisional` | Revisional de contrato bancário rural |

Se a tese estiver ambígua, **pare e pergunte** — é o erro que a Dra. Juliana relatou
como o mais recorrente nas 200 correções/mês. Ver `.claude/agents/maldonado-divida-rural.md`.

### 2. Inventarie a pasta do cliente

```bash
python OPERACIONAL/main.py anexos inventario --cliente "NOME DO CLIENTE"
```

Varre `ZEUS > 03. CLIENTES > 01 CLIENTES > [LETRA] > [CLIENTE]` e subpastas, e classifica
cada arquivo por tipo. A classificação é **heurística de nome de arquivo** — palpite, não
laudo. Sempre leia a lista de "não classificados": é onde costuma estar o documento com
nome ruim (`IMG_2043.pdf`, `digitalizado 3.pdf`) que era justamente o que faltava.

### 3. Confira o rol contra o que a tese exige

```bash
python OPERACIONAL/main.py anexos conferir --cliente "NOME" --acao-peca mora
```

Sai o que tem, o que falta (obrigatórios e recomendados) e quais recortes a tese pede no
corpo. **Faltando documento obrigatório, avise antes de redigir** — não adianta produzir
a peça inteira para descobrir na revisão que a ficha gráfica nunca chegou.

### 4. Baixe o que vai usar

```bash
python OPERACIONAL/main.py anexos baixar --cliente "NOME" --acao-peca mora
python OPERACIONAL/main.py anexos baixar --cliente "NOME" --tipo cedula --tipo ficha-grafica
```

Vai para `_trabalho/anexos/[CLIENTE]/` (local, não versionado).

### 5. Recorte

Primeiro **ache a página** — nunca recorte às cegas:

```bash
python OPERACIONAL/main.py anexos localizar cedula.pdf --tipo cedula
python OPERACIONAL/main.py anexos localizar cedula.pdf --buscar "capitalização diária"
```

Depois recorte a região do termo (com 1 cm de folga) ou a página inteira:

```bash
python OPERACIONAL/main.py anexos recorte cedula.pdf --tipo cedula --saida rec-clausula.png
python OPERACIONAL/main.py anexos recorte ficha.pdf --pagina 3 --pagina-inteira --saida rec-ficha.png
```

**Abra e olhe o PNG antes de colar.** Se `localizar` não achar nada, o PDF é digitalização
sem OCR: escolha a página na mão com `--pagina N --pagina-inteira`.

### 6. Monte na peça

```bash
python OPERACIONAL/main.py anexos placeholders inicial.docx
python OPERACIONAL/main.py anexos inserir inicial.docx \
    -m "INSERIR UMA IMAGEM." -i rec-clausula.png \
    -l "Imagem 03. Cédula Rural Pignoratícia nº 000000000, fl. 2 (grifo nosso)"
python OPERACIONAL/main.py anexos pendencia inicial.docx -m "IMAGEM DO REQUERIMENTO"
```

`placeholders` mostra o marcador, **a frase que o antecede** (é ela que diz qual documento
entra ali — "INSERIR UMA IMAGEM." sozinho não diz nada) e um palpite de tipo. A imagem
entra centralizada, limitada à mancha da página do timbrado, com legenda em 10 pt itálico
**acima** da imagem (Dr. Mailson, 14/09/2026: quem lê sabe o que vai ver antes de ver).

---

## O que recortar em cada tese

| Tese | Recortes que a peça pede no corpo | O que o recorte precisa mostrar |
|---|---|---|
| `mora` | cláusula de juros e de capitalização da cédula; ficha gráfica | **o período de normalidade** — ver abaixo |
| `mora-assistencia` | idem + laudo/projeto técnico; decreto de emergência | a conclusão do laudo, não a capa |
| `alongamento` | requerimento enviado ao banco + protocolo/AR; negativa do banco; decreto de emergência; cotação da arroba; boletim climático | a data e o protocolo, senão não prova o requerimento prévio |
| `revisional` | cláusula de juros/capitalização; ficha gráfica; extrato de movimentação | a cláusula inteira, com o nº da cédula identificado |

**Ficha gráfica — o ponto que mais erra:** o recorte tem que mostrar o **período de
normalidade contratual** (antes do inadimplemento). Recorte da coluna de inadimplência não
sustenta o Elo 1 do Tema 28 — pelo contrário, contradiz a tese, porque a Orientação 2 só
alcança encargo cobrado na normalidade. Ver a skill `descaracterizacao-mora`.

**Cédula:** o recorte da cláusula precisa deixar visível **qual contrato é**. Se o número da
cédula está no quadro da página 1 e a cláusula na página 5, faça **dois recortes** e cite
as duas folhas na legenda. Cláusula solta, sem identificação do título, não prova nada.

---

## Regras do recorte (é prova, não ilustração)

1. **Nunca cortar de modo que mude o sentido.** O recorte sai com folga ao redor do termo
   justamente para não decapitar a cláusula. Na dúvida, página inteira.
2. **Nunca editar, limpar ou remontar** o recorte. Ele reproduz o documento como está —
   inclusive torto e mal digitalizado. **Grifar, sim — desde que declarado.**

   > **Grifo na imagem, com "grifo nosso" na legenda** (decisão da Dra. Juliana, 10/09/2026).
   > O peso do destaque dentro do print é maior do que na transcrição, e a praxe forense já
   > resolveu o problema há muito: grifo declarado não é prova adulterada, é destaque
   > assumido — a mesma lógica de "grifamos" / "sem grifos no original" que se usa ao
   > transcrever jurisprudência. O que seria adulteração é o grifo **não** declarado, que
   > passa por parte do documento original.
   >
   > `anexos recorte --realcar "TRECHO"` (repetível) grifa em amarelo na própria imagem, via
   > anotação de realce do PDF — o texto continua legível por baixo, e **o PDF de origem não
   > é alterado**: o grifo vive só no render em memória. A legenda **tem** de terminar em
   > "— grifo nosso"; sem isso, não cole.
   >
   > O realce na **transcrição** continua valendo, e os dois se somam:
   > `visual_law.realcar_em(doc, trechos, comeca_com=...)`. Abaixo da imagem,
   > `visual_law.caixa_prova()` diz em uma frase o que aquele documento prova.

   **Duas regras de enquadramento**, aprendidas numa peça real de cliente:
   - **`--largura-total`**: recorte estreito corta a linha no meio ("juros à taxa efet…").
     A faixa mantém a largura da página e corta só na vertical.
   - **`_contornar()`** põe um fio cinza de 0,75 pt em toda imagem inserida: sem moldura, o
     documento do banco se confunde com o corpo da peça.
3. **Sempre citar o documento e a folha/página** na legenda (`fl. 2`).
4. **Documento pessoal não vai recortado no corpo** — RG, CPF, CNH, comprovante de
   residência, procuração, IRPF entram no **rol de anexos**, não como imagem no meio da
   peça. Expor dado pessoal no corpo de peça pública não tem ganho argumentativo e tem
   custo de LGPD.
5. **Imagem numerada em sequência, não "Doc. [[nº]]".** Regra da Dra. Juliana (15/09/2026):
   cada imagem da peça sai como `Imagem 01`, `Imagem 02`..., na ordem em que aparece, e o
   texto e o índice de provas citam esse número. O número do anexo no PJe só existe depois do
   upload; com `Doc. [[nº]]` o advogado tinha de substituir cada referência à mão, e um número
   trocado manda o juiz para o documento errado. Quem localiza a prova é a legenda: documento e
   folha. `anexos_inicial.legenda_padrao()` já monta nesse formato.
6. **Documento que não existe vira pendência amarela**, com o tipo faltante escrito. Nunca
   "conforme documento anexo" sem documento.
7. **Todo print entra EM PAR: a imagem e a transcrição do que ela mostra.** Regra da Dra.
   Juliana (10/09/2026). Dois marcadores numerados, sempre os dois:

   ```
   [[INSERIR PRINT 01 — recorte da cláusula de encargos financeiros, fl. (…)]]
   [[TEXTO DO PRINT 01 — transcrever literalmente o trecho que o recorte mostra]]
   ```

   O motivo é prático, não estético. **Imagem, no PJe, não é pesquisável nem copiável:** o
   juiz que quiser levar a cláusula para o dispositivo não consegue selecioná-la, a busca
   textual dos autos não a encontra e o leitor de tela não a lê. Se o recorte sair ilegível
   na conversão para PDF ou na impressão em preto e branco, o argumento morre junto com
   ele. Transcrito ao lado, o conteúdo sobrevive a tudo isso — e o recorte passa a fazer o
   que só ele faz, que é **provar que aquilo está mesmo no documento**.

   > A transcrição é **literal e do documento lido** — nunca de memória, nunca "conforme se
   > vê". E nunca calcula nada a partir do que o print mostra: em ficha gráfica, transcreve
   > os lançamentos, não a taxa que eles deixariam deduzir (Restrição Absoluta nº 15 da
   > skill `descaracterizacao-mora`).

   `vl.marcador_print(doc, n, o_que, transcrever=...)` emite o par; `vl.varrer_marcadores_print(doc)`
   acusa qualquer um dos dois que tenha ficado órfão. **Lista vazia é o único resultado
   aceitável antes de entregar.**

---

## Placeholders conhecidos dos modelos

Levantados nos modelos reais (`BASE_CONHECIMENTO/05 - FORMATACAO/`):

| Marcador | Modelo | Documento que o preenche |
|---|---|---|
| `[[INSERIR PRINT nn — …]]` | **padrão novo** (10/09/2026), modelo da declaratória | o que o próprio marcador descreve — e exige o par `[[TEXTO DO PRINT nn]]` |
| `[[TEXTO DO PRINT nn — …]]` | **padrão novo**, par obrigatório do anterior | **texto**, não imagem — a transcrição do que o recorte mostra |
| `INSERIR UMA IMAGEM.` | Mandamental de prorrogação, p. 20 | depende do contexto — leia a frase anterior |
| `IMAGEM DO REQUERIMENTO QUE FOI ENVIADO AO BANCO` | Mandamental, p. 17 | requerimento administrativo + protocolo/AR |
| `INSERIR GRÁFICO` | Revisional, item 1.2.1 | cotação da arroba, ou extrato de movimentação |
| gráficos de arroba do boi | Mandamental, p. 10–11 | cotação CEPEA/Scot |
| `____________` | qualificação, em todos | **texto**, não imagem — dado do cliente (ADVBOX) |

Marcador em formato novo que a peça trouxer e o comando não reconhecer: avise, para
incluir o padrão em `_PADROES_IMAGEM` (`OPERACIONAL/anexos_inicial.py`).

---

## Tipos de documento catalogados

`procuracao` · `doc-pessoal` · `comprovante-residencia` · `estado-civil` ·
`hipossuficiencia` · `contrato-social` · `cedula` · `aditivo` · `ficha-grafica` ·
`banco-movimentacao` · `negativacao` · `requerimento-banco` · `negativa-banco` ·
`decreto-emergencia` · `laudo-agronomico` · `clima` · `cotacao` · `imovel-rural` ·
`producao` · `dap-caf` · `processo`

O rol por tese (obrigatórios/recomendados/recortes) está em `ACOES`, no módulo. É o
**default do escritório, a confirmar caso a caso** — caso concreto pode dispensar ou exigir
documento fora da lista.

---

## Fechamento

1. Rode `anexos placeholders` de novo na peça pronta: **não pode sobrar marcador não
   tratado** — ou tem recorte, ou tem pendência amarela.
2. Liste o rol numerado no final da peça, na mesma ordem do upload.
3. A peça vai para o Drive por `drive peca` (pede confirmação):
   ```bash
   python OPERACIONAL/main.py drive peca inicial.docx --cliente "NOME"
   ```
   Inicial ainda não distribuída vai para `[CLIENTE] - SEM PROCESSO`.

## Guard-rail

Peça sai **pronta para revisão da Dra. Juliana / do Dr. Renan**, nunca protocolada. Este
comando não grava nada no Drive: só lê a pasta do cliente e escreve no `.docx` local.

## Skills e agentes ligados

`timbrado` (papel e formatação — sempre junto) · `descaracterizacao-mora` (o que o recorte
da cédula e da ficha gráfica precisa provar) · `.claude/agents/maldonado-divida-rural.md`
(qual tese, qual estrutura) · `.claude/agents/maldonado-controladoria.md` (POP e prazos).
