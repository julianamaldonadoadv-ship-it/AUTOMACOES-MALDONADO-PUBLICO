# Prompt para o Claude CRIAR a skill "Timbrado"

> Cole exatamente isso no Claude (Claude.ai — Chrome ou app) e ele empacota a skill pra você instalar.

---

Use seu skill creator (ou sua capacidade de criar skills) para empacotar uma skill chamada **"timbrado-maldonado"**, instalável no meu Claude.ai.

**Função:** aplicar o **papel timbrado oficial** do escritório **MALDONADO ADVOGADOS** (Dr. **RENAN GOMES MALDONADO DE JESUS** — **OAB/RO 5769**, Porto Velho/RO) em qualquer peça ou documento que eu gerar — para nunca produzirmos peça em folha branca.

**Description da skill (pro modelo invocar certo):** "Aplica o papel timbrado oficial do escritório Maldonado Advogados em qualquer peça DOCX (petição inicial, contestação, recurso, embargos, contrato, procuração, parecer). Use sempre que precisar formatar uma peça com a identidade visual do escritório do Dr. Renan Gomes Maldonado de Jesus — OAB/RO 5769."

**Quando invocada (geralmente por outra skill, como `divida-rural-maldonado`, ou diretamente por mim):**

1. **Buscar o timbrado-base** no meu Drive — arquivo `TIMBRADO_MALDONADO.docx` (ou nome equivalente que eu indicar; já tenho o modelo real da Procuração e do Contrato de Honorários com o cabeçalho/rodapé oficiais — use-os como referência de identidade visual se o timbrado-base ainda não estiver isolado). Use-o como template: copie o **header (logo "M" dourado/preto + "MALDONADO ADVOGADOS" + faixa dourada lateral) e o footer (endereço, e-mail, WhatsApp em faixa preta/dourada)** dele, mantendo intactos. Caso eu ainda não tenha esse arquivo isolado, **peça antes de gerar** — não invente identidade visual.

2. **Receber o conteúdo da peça** (texto da ação de prorrogação, da declaratória de mora, da revisional, contestação etc.) e **injetá-lo no corpo** do documento, sem mexer no header/footer.

3. **Aplicar o padrão de formatação do escritório** (calibrado pelos modelos reais: ação de prorrogação, ação declaratória Tema 28, ação revisional, procuração e contrato de honorários):
   - Corpo **justificado**.
   - **Cabeçalhos principais em MAIÚSCULO e negrito**: `AO JUIZ DE DIREITO DA ____ VARA CÍVEL DA COMARCA DE [...]`, `DA DELIMITAÇÃO DA CONTROVÉRSIA`, `DOS FATOS`, `DO DIREITO`, `DOS REQUERIMENTOS`.
   - **Subtítulos numerados** (ex.: `1.1 DA CARACTERIZAÇÃO DA CÉDULA BANCÁRIA...`, `1.2 DA NATUREZA DA CÉDULA...`) — negrito, numeração sequencial mantida.
   - Na ação revisional, **sempre inclua o sumário no início** (Tópico I a IV) — é o padrão do escritório.
   - **Tabelas comparativas** quando o texto contrapuser institutos (ex.: "juros compostos" x "capitalização") — bordas finas, cabeçalho em negrito, células centralizadas.
   - **Citações de súmula/precedente** em destaque (a peça-modelo usa blocos com fonte identificada: "STJ", número da súmula/REsp, enunciado, data).
   - **Assinatura final padronizada:**
     ```
     Porto Velho - RO, [DIA] de [MÊS] de [ANO].
     (assinado digitalmente)
     RENAN GOMES MALDONADO DE JESUS
     OAB/RO 5769
     ```
     (ou o advogado responsável indicado — ex.: Bruno Vinícius de Souza Faustino, OAB/RO 13021 — se apontado por mim).

4. **Rodapé/assinatura da peça** com nome e OAB do(a) advogado(a) responsável. **Default fixo:** Dr. **RENAN GOMES MALDONADO DE JESUS — OAB/RO 5769**. Se outro advogado do escritório for indicado, usar os dados dele(a).

5. **Gerar o DOCX final** e salvar onde for solicitado (geralmente na pasta do cliente no Drive — estrutura padrão do escritório: `01 CLIENTES > [LETRA] > [NOME DO CLIENTE] > CONTRATO BANCÁRIO / DOC ADMINISTRATIVO / DOC PESSOAL / REUNIÕES - VIA MEET`). Nome do arquivo conforme a skill chamadora (`[NOME DO CLIENTE] - [AÇÃO] - PRONTA PARA REVISÃO.docx`).

**Implementação sugerida:**
- Inclua no pacote da skill um **script Python (python-docx)** que:
  1. Abre `TIMBRADO_MALDONADO.docx` como base.
  2. **Limpa o body** mantendo header e footer intactos.
  3. **Injeta o conteúdo formatado** conforme as regras acima.
  4. Gera o DOCX final e devolve o caminho.
- Inclua um exemplo mínimo de uso (entrada: texto da peça + nome do cliente + tipo da ação; saída: caminho do DOCX gerado).
- Se não der pra rodar Python na sessão, deixe as **regras de formatação descritas no `SKILL.md`** pra eu seguir manualmente ao gerar peças.

**Guard-rails:**
- **NUNCA gere peça do escritório em folha branca.** Toda peça do Maldonado Advogados sai no timbrado dele.
- **Nunca invente logo, cabeçalho, endereço ou OAB.** Use só o que estiver no arquivo `TIMBRADO_MALDONADO.docx` (ou nos modelos reais de referência: Procuração e Contrato de Honorários). Se ele não existir, peça antes de gerar.
- **Não altere o conteúdo da peça** ao aplicar o timbrado — só formate.
- **Default de advogado responsável:** Dr. Renan Gomes Maldonado de Jesus — OAB/RO 5769.

**Identidade institucional fixa (caso falte info no template):**
- Escritório: **MALDONADO ADVOGADOS** (razão social judicial: RENAN MALDONADO SOCIEDADE INDIVIDUAL DE ADVOCACIA, CNPJ 20.920.644/0001-05; razão social consultoria: MALDONADO CONSULTORIA EMPRESARIAL LTDA, CNPJ 56.082.220/0001-66)
- Advogado titular: **Dr. RENAN GOMES MALDONADO DE JESUS — OAB/RO 5769**
- Outro advogado do quadro: Dr. Bruno Vinícius de Souza Faustino — OAB/RO 13021
- Gerente Jurídico: Dra. Juliana Ferreira Gusmão de Lara
- E-mail: maldonadoadvogadopvh@gmail.com
- WhatsApp: 69 3223-5881 / 69 9846-2865 (escritório) · 69 9369-5030 (consultoria)
- Endereço: Rua Rafael Vaz e Silva, n. 1040, Bairro Nossa Senhora das Graças, CEP 76.804-162, Porto Velho/RO
- Comarca/foro principal: Porto Velho/RO — TJRO

Empacote como skill instalável e me devolva o pacote pronto pra eu instalar no meu Claude.ai.

---

> **Nota pré-instalação:** antes de instalar a skill, suba no seu Drive um arquivo chamado `TIMBRADO_MALDONADO.docx` com o cabeçalho e rodapé oficiais do escritório (logo, endereço completo, telefones, OAB) — o header/footer da Procuração ou do Contrato de Honorários que você já tem servem de referência exata do design. Sem esse arquivo isolado, a skill `divida-rural-maldonado` vai pedir o template antes de gerar.
