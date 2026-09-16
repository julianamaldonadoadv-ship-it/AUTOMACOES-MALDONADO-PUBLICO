---
name: analise-pontos-controvertidos
description: >
  Use esta skill SEMPRE que precisar analisar autos de processo judicial (petição inicial, contestação, réplica) para mapear pontos controvertidos, fatos incontroversos, fatos novos e a distribuição do ônus da prova, com o objetivo de atuar de forma mais estratégica no processo. Ative quando o usuário mencionar: pontos controvertidos, fatos incontroversos, ônus da prova, ônus de impugnação especificada, saneamento do processo, delimitação das questões de fato, art. 341/342/356/357/373/374 CPC, matriz de fatos, mapa probatório, plano de provas, quesitos periciais, rol de testemunhas estratégico, réplica à contestação, julgamento antecipado parcial do mérito, ou análise que cruze fatos da inicial com fatos impugnados/admitidos na contestação. Fornece metodologia passo a passo, matriz de trabalho fato a fato e fundamentos do CPC. Metodologia do escritório Maldonado Advogados.
---

# Skill: Análise de Pontos Controvertidos, Incontroversos e Produção de Provas

## O que esta skill faz

Guia a leitura cruzada da **petição inicial**, da **contestação** e, quando houver, da **réplica**, para produzir uma **matriz fato a fato** que classifica cada fato do processo (controvertido, incontroverso ou fato novo), define se ele precisa de prova, de quem é o ônus de prová-lo e qual é a prova idônea para tanto. O resultado é uma peça de trabalho interna (e, quando útil, um trecho de petição) que orienta:

- o que impugnar e o que **não vale a pena** discutir (fato incontroverso/notório/presumido);
- que provas efetivamente requerer (evitando pedidos de prova sobre fatos que já dispensam prova);
- como se posicionar no **saneamento do processo** (art. 357, CPC) para fixar a seu favor a delimitação dos pontos controvertidos e a distribuição do ônus da prova;
- onde há **fato incontroverso apto a julgamento antecipado parcial** (art. 356, CPC), acelerando parte da causa.

Use esta skill em qualquer área (não é exclusiva de crédito rural) — ela se aplica a qualquer processo em que exista petição inicial e contestação/resposta.

---

## Visão geral do fluxo

```
PETIÇÃO INICIAL (fatos alegados pelo autor)
        ↓
CONTESTAÇÃO (o réu impugna? confirma? cala-se? traz fato novo?)
        ↓
CLASSIFICAÇÃO FATO A FATO
   → CONTROVERTIDO (impugnado especificamente)
   → INCONTROVERSO (não impugnado — art. 341, CPC)
   → FATO NOVO (matéria de defesa ou fato superveniente — art. 342, CPC)
        ↓
RÉPLICA DO AUTOR sobre fatos novos e preliminares
        ↓
PARA CADA FATO CONTROVERTIDO:
   → precisa de prova? (art. 374, CPC — notório, confessado, incontroverso, presunção legal dispensam)
   → de quem é o ônus? (art. 373, CPC — regra geral e possibilidade de distribuição diversa)
   → qual prova produzir e quem a produz? (documental, testemunhal, pericial, depoimento pessoal)
   → há contraprova a antecipar?
        ↓
MATRIZ CONSOLIDADA → subsidia SANEAMENTO (art. 357), RÉPLICA, RAZÕES FINAIS e RECURSOS
```

---

## Passo 1 — Levantar os fatos da Petição Inicial

Leia a petição inicial e liste, **um a um e numerado**, cada fato relevante alegado pelo autor como causa de pedir. Para cada fato, registre a referência exata nos autos (folha, ID do documento ou número do evento).

**Boas práticas:**
- Separe fatos de teses jurídicas — a matriz trabalha com **fatos**, não com o direito aplicável a eles.
- Quebre fatos compostos em fatos simples sempre que isso ajudar a isolar o que efetivamente será controvertido (ex.: "o réu causou o acidente porque avançou o sinal vermelho" pode ser decomposto em "houve o acidente" + "o réu avançou o sinal vermelho").
- Não pule fatos secundários — mesmo fatos que parecem óbvios podem se tornar controvertidos.

---

## Passo 2 — Confrontar com a Contestação

Para cada fato listado no Passo 1, verifique na contestação:

| Situação na contestação | Classificação | Base legal |
|---|---|---|
| O réu nega o fato ou apresenta versão diferente, especificamente | **CONTROVERTIDO** | — |
| O réu não se manifesta sobre o fato, e não se enquadra nas exceções do art. 341 | **INCONTROVERSO** (presume-se verdadeiro) | Art. 341, *caput*, CPC |
| O réu apenas nega "por negativa geral" ou de forma genérica, sem impugnação específica | Trate como **INCONTROVERSO**, salvo se o réu for Defensoria, advogado dativo ou curador especial | Art. 341, *caput* e parágrafo único, CPC |
| O réu confessa o fato expressamente | **INCONTROVERSO** (fato confessado) | Art. 374, II, CPC |
| O réu traz fato **diferente do alegado na inicial**, como matéria de defesa (fato impeditivo, modificativo ou extintivo) | **FATO NOVO** trazido pelo réu | Art. 373, II, CPC |

> **Atenção às exceções do art. 341:** a presunção de veracidade pelo silêncio do réu **não se aplica** quando (i) não for admissível confissão sobre aquele fato, (ii) a inicial não vier acompanhada de documento que a lei considera da substância do ato, ou (iii) a alegação estiver em contradição com a defesa considerada em seu conjunto. Verifique sempre essas três hipóteses antes de classificar um fato como incontroverso apenas pelo silêncio do réu.

**Ação:** preencha as colunas "Fatos controvertidos na contestação" e destaque separadamente qualquer fato novo trazido pelo réu (matéria de defesa) — ele exige tratamento próprio no passo seguinte.

---

## Passo 3 — Tratar os Fatos Novos trazidos pela Contestação

Fatos novos alegados pelo réu (matéria de defesa ou fato impeditivo/modificativo/extintivo) precisam de manifestação do autor em réplica:

1. Verifique se o fato novo é, de fato, um fato **não coberto** pela causa de pedir original.
2. Elabore a manifestação do autor sobre cada fato novo: impugna especificamente (vira controvertido) ou não impugna (vira incontroverso, mesma lógica do art. 341 aplicada agora ao autor).
3. Depois da contestação, novas alegações do réu só são lícitas se (i) forem de direito ou fato superveniente, (ii) forem matéria cognoscível de ofício pelo juiz, ou (iii) houver autorização legal expressa para alegação a qualquer tempo — use isso para **impugnar preliminarmente** fatos novos extemporâneos trazidos fora da contestação (tréplicas, memoriais etc.).

**Base legal:** Art. 342, CPC.

**Ação:** preencha as colunas "Fatos novos alegados na contestação" e "Manifestação do autor sobre os fatos novos".

---

## Passo 4 — Verificar a necessidade de prova de cada fato controvertido

Para cada fato classificado como **CONTROVERTIDO**, verifique se ele se enquadra em alguma das hipóteses do art. 374 do CPC, que **dispensam prova**:

- **I — Fato notório** (de conhecimento geral, não depende de prova mesmo sendo tecnicamente "controvertido" pela parte contrária);
- **II — Fato afirmado por uma parte e confessado pela parte contrária;**
- **III — Fato admitido no processo como incontroverso** (ex.: tornou-se incontroverso em manifestação posterior, mesmo que inicialmente impugnado);
- **IV — Fato em cujo favor milita presunção legal** de existência ou de veracidade (a parte contrária é que tem o ônus de provar o contrário).

**Regra prática:** só entram na coluna "este fato deve ser provado" os fatos genuinamente controvertidos que **não** se enquadram em nenhum dos quatro incisos do art. 374. Isso evita pedir prova (e gastar tempo de audiência, quesitos periciais, rol de testemunhas) sobre algo que juridicamente já está resolvido.

---

## Passo 5 — Distribuir o ônus da prova

Para cada fato que efetivamente precisa de prova (Passo 4), identifique **de quem é o ônus**, aplicando a regra geral do art. 373, CPC:

- **Autor**: ônus de provar o **fato constitutivo** do seu direito (o fato-base da causa de pedir) — art. 373, I.
- **Réu**: ônus de provar **fato impeditivo, modificativo ou extintivo** do direito do autor — art. 373, II (é aqui que entram os "fatos novos" tratados no Passo 3, quando não impugnados pelo autor mas ainda carentes de prova, ou quando o autor os impugna e o réu segue com o ônus de prová-los).

**Distribuição diversa do ônus (dinâmica ou negocial) — avalie sempre como estratégia:**
- O juiz pode atribuir o ônus de modo diverso, por decisão fundamentada, quando houver **impossibilidade ou excessiva dificuldade** de a parte cumprir o encargo, ou **maior facilidade de obtenção da prova do fato contrário** pela parte adversa (art. 373, §1º). A parte deve ter oportunidade de se desincumbir do novo ônus atribuído.
- Essa inversão **não pode** tornar o encargo impossível ou excessivamente difícil para quem o recebe (art. 373, §2º).
- As partes também podem **convencionar** distribuição diversa do ônus da prova, antes ou durante o processo, salvo se recair sobre direito indisponível ou tornar excessivamente difícil o exercício do direito por uma delas (art. 373, §3º e §4º).

**Ação:** se identificar hipótese de desequilíbrio informacional ou técnico entre as partes (ex.: prova depende de documentos/sistemas que só a parte contrária controla), avalie requerer a inversão do ônus da prova de forma fundamentada — não é automática, exige decisão motivada do juízo.

---

## Passo 6 — Definir a prova idônea e quem a produzirá

Para cada fato controvertido que precisa de prova e já tem o ônus atribuído, defina:

1. **Quem deve produzir** a prova (a parte onerada pelo art. 373, ou o terceiro/parte contrária, se houver inversão);
2. **Qual é a prova adequada** para aquele fato específico — pense em todos os meios possíveis:
   - Prova documental (contratos, boletins de ocorrência, laudos, prints, extratos, prontuários);
   - Prova testemunhal (identifique nominalmente as testemunhas, se já souber quem são, e o que cada uma pode confirmar);
   - Prova pericial (defina desde já possíveis quesitos, se o fato for técnico);
   - Depoimento pessoal da parte contrária (útil para obter confissão real ou ficta);
   - Prova emprestada de outro processo (art. 372, CPC), se existir;
   - Inspeção judicial, quando cabível.
3. **Contraprovas**: liste desde já qualquer prova que a parte contrária (ou você) já tenha nos autos e que contradiga a versão do fato — isso é fundamental para antecipar o resultado da instrução e ajustar a estratégia (inclusive para eventual acordo).

> Lembre-se do art. 370: cabe ao juiz, de ofício ou a requerimento, determinar as provas necessárias, mas ele também pode **indeferir, fundamentadamente, provas inúteis ou protelatórias**. Não peça prova sobre fato que já está dispensado pelo art. 374 — isso enfraquece a credibilidade do pedido probatório como um todo.

---

## Passo 7 — Montar a Matriz de Fatos e Provas

Consolide tudo em uma tabela única, fato a fato. Esse é o formato de trabalho padrão do escritório (adaptado do template usado em casos de responsabilidade civil, mas aplicável a qualquer matéria):

| Coluna | Conteúdo |
|---|---|
| **Fatos alegados na Petição Inicial** | Fato numerado + referência (f./ID) |
| **Fatos controvertidos na Contestação** | Trecho/resumo da impugnação + referência (f./ID) |
| **Fatos novos alegados na Contestação** | Matéria de defesa nova + referência |
| **Manifestação do autor sobre os fatos novos** | Impugna ou não impugna, com referência à réplica |
| **Este fato precisa de prova?** | SIM (controvertido e fora do art. 374) / NÃO (incontroverso, notório, confessado ou presumido) |
| **Quem deve produzir a prova deste fato** | Autor / Réu / ambos (conforme art. 373 e eventual inversão) |
| **Qual é a prova deste fato** | Testemunha (nome), documento, perícia (quesito), depoimento pessoal etc. |
| **Contraprovas** | Provas já existentes nos autos que contradizem a versão da parte onerada |

Ao montar a matriz, uma linha por fato — inclusive linhas específicas para os fatos novos que não têm correspondente na petição inicial (eles nascem na contestação).

**Dica de uso:** construa a matriz em planilha (Excel/Google Sheets) quando o processo tiver muitos fatos, para facilitar reordenação, destaque por cor (ex.: vermelho = controvertido/precisa prova; verde = incontroverso/não precisa prova; azul = fato novo) e compartilhamento com a equipe. Veja `references/exemplo-matriz.md` para um exemplo preenchido a partir de um caso de acidente de trânsito.

---

## Passo 8 — Usar a matriz no Saneamento do Processo

A matriz pronta é a base para atuar no **saneamento e organização do processo** (art. 357, CPC), momento em que o juiz deve:

- resolver questões processuais pendentes (inciso I);
- **delimitar as questões de fato** sobre as quais recairá a prova, especificando os meios admitidos (inciso II);
- **definir a distribuição do ônus da prova**, observado o art. 373 (inciso III);
- delimitar as questões de direito relevantes (inciso IV);
- designar, se necessário, audiência de instrução (inciso V).

**Estratégias a partir da matriz:**
1. **Antecipe-se**: peticione antes (ou durante) o saneamento levando sua própria matriz de pontos controvertidos/incontroversos e a distribuição de ônus que entende correta — isso influencia a decisão do juiz.
2. **Delimitação consensual**: se a parte contrária concordar com sua classificação fato a fato, considere apresentar ao juiz, para homologação, delimitação consensual das questões de fato e de direito (art. 357, §2º) — uma vez homologada, **vincula as partes e o juiz**, dando segurança sobre o que será discutido na instrução.
3. **Peça esclarecimentos/ajustes** no prazo comum de 5 dias após a decisão de saneamento, se ela deixar de considerar algum fato da sua matriz como controvertido (ou o contrário) — depois desse prazo a decisão se torna estável (art. 357, §1º).
4. **Rol de testemunhas e quesitos periciais**: baseie o rol de testemunhas e os quesitos periciais exclusivamente nos fatos que, pela matriz, (i) são controvertidos e (ii) não se enquadram no art. 374 — não desperdice o limite de testemunhas (máx. 10, sendo até 3 por fato, art. 357, §6º) com fatos incontroversos.

---

## Passo 9 — Explorar fatos incontroversos para julgamento antecipado parcial

Se, ao final da matriz, um ou mais **pedidos inteiros** (não apenas fatos isolados) estiverem amparados só em fatos incontroversos ou já provados, avalie requerer o **julgamento antecipado parcial do mérito** (art. 356, I, CPC) para esse(s) pedido(s) — isso permite, inclusive, liquidar/executar desde logo a parte incontroversa, independentemente de caução, ainda que haja recurso quanto ao restante (art. 356, §§2º e 3º).

---

## Passo 8.1 — Estrutura sugerida da manifestação em resposta à decisão de saneamento

Quando a matriz for usada para elaborar a própria petição de resposta a uma decisão que determine especificação de provas e delimitação de questões (art. 357, CPC — cenário do Passo 8), monte a peça seguindo esta estrutura, que espelha exatamente os itens que esse tipo de decisão costuma exigir:

1. **Da tempestividade** (breve, se aplicável).
2. **Dos pontos incontroversos** — liste, um a um, todos os fatos classificados como incontroversos na matriz (Passo 2/4), e não apenas os "formais" (existência da ação, do título, valores). Inclua explicitamente:
   - fatos não impugnados especificamente pela parte contrária (art. 341, CPC), mesmo que pareçam periféricos (parcelamento, datas, inadimplemento, tempestividade, garantias);
   - quando houver um fato central da tese (ex.: natureza/finalidade de uma operação, uma qualificação jurídica de base) que não foi impugnado especificamente, **peça a declaração de incontrovérsia como pedido principal** — e mantenha as provas relacionadas a esse fato apenas como pedido **subsidiário**, para o caso de o Juízo entender de forma diversa. Não trate como puramente controvertido, por cautela, um fato que a matriz já classificou como incontroverso — isso desperdiça a incontrovérsia obtida de graça pelo silêncio da parte contrária.
3. **Da delimitação das questões de fato controvertidas e do ônus da prova** — reproduza a matriz em forma de tabela, com uma coluna explícita de **ônus** por fato (Autor/Réu/ambos, conforme art. 373 e eventual distribuição diversa), pois decisões de saneamento costumas exigir isso *fato a fato*, e não apenas uma explicação genérica no corpo do texto.
4. **Das provas que pretende produzir e sua pertinência** — para cada meio de prova requerido, amarre-o a um fato específico da matriz (não pedir prova "em geral"). Hierarquize: identifique quais provas são **essenciais** (documentais e periciais, em regra) e quais são **complementares** (testemunhal, depoimento pessoal), para que um eventual deferimento parcial pelo Juízo preserve o núcleo da tese.
5. **Das questões de direito relevantes para o mérito** (com referência ao art. 489, §1º, IV, CPC) — indicar teses e precedentes que se queira ver enfrentados, preferindo, quando possível, fundamentar a tese central em terreno que **independa** de controvérsias jurídicas paralelas mais frágeis (ex.: se a tese central pode se sustentar sem depender da aplicação do CDC, não a torne dependente disso).
6. **Da possibilidade de saneamento consensual / audiência de conciliação** — manifestar-se objetivamente, condicionando eventual composição à prévia disponibilização de informações/documentos necessários para que a negociação não ocorra em assimetria informacional.
7. **Dos pedidos** — retomar, em lista numerada, a homologação dos fatos incontroversos, a fixação do ônus da prova por fato, o deferimento das provas (na ordem de prioridade definida no item 4), e a manifestação sobre conciliação/saneamento consensual. Peça que eventual indeferimento de prova seja fundamentado especificamente em relação a cada fato, preservando o contraditório.

**Checklist de revisão específico desta estrutura**, a aplicar antes de protocolar:
- [ ] Todo fato incontroverso da matriz (não só os "formais") está listado no item 2?
- [ ] Fatos centrais da tese que não foram especificamente impugnados pela parte contrária foram pedidos como incontroversos em caráter **principal**, com prova apenas subsidiária?
- [ ] A tabela de questões de fato controvertidas tem coluna própria de **ônus** por fato?
- [ ] Cada prova requerida está amarrada a um fato específico, e não pedida de forma genérica?
- [ ] As provas essenciais foram distinguidas das complementares, para resistir a deferimento parcial?
- [ ] Contradições factuais da parte contrária (ex.: negar genericamente algo que a própria parte já demonstrou documentalmente nos autos) foram exploradas expressamente no corpo da peça?

---

## Checklist final antes de usar a matriz numa peça

- [ ] Todos os fatos da petição inicial foram numerados e localizados nos autos (f./ID)?
- [ ] Cada fato foi confrontado com a contestação e classificado (controvertido / incontroverso / fato novo)?
- [ ] Foram verificadas as três exceções do art. 341 antes de presumir um fato como incontroverso pelo silêncio do réu?
- [ ] Fatos novos da contestação foram objeto de manifestação específica na réplica?
- [ ] Cada fato controvertido foi checado contra as quatro hipóteses do art. 374 (dispensa de prova)?
- [ ] O ônus da prova de cada fato remanescente foi atribuído conforme o art. 373 (e avaliada eventual inversão)?
- [ ] Para cada fato com ônus definido, há prova idônea identificada (testemunha, documento, perícia, depoimento pessoal)?
- [ ] Foram identificadas contraprovas já existentes nos autos?
- [ ] A matriz foi usada para orientar o requerimento no saneamento (art. 357) e o rol de testemunhas/quesitos?
- [ ] Foi avaliada a existência de pedido inteiramente incontroverso apto a julgamento antecipado parcial (art. 356)?

---

## Fundamentos legais de referência

Leia `references/fundamentos-legais.md` para o texto integral dos artigos do CPC citados nesta skill (arts. 341, 342, 356, 357 e 369 a 380), prontos para citar em petições.

## Exemplo de matriz preenchida

Leia `references/exemplo-matriz.md` para um exemplo completo, baseado em um caso de acidente de trânsito, mostrando a matriz totalmente preenchida linha a linha.
