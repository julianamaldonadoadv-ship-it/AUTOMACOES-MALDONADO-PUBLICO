---
name: prescricao-intercorrente
description: >
  Use esta skill SEMPRE que precisar analisar autos de processo judicial para verificar o cabimento da prescrição trienal intercorrente em execuções de título extrajudicial. Ative esta skill quando o usuário mencionar: prescrição intercorrente, prescrição trienal, execução parada, processo inativo, diligências infrutíferas, mandado negativo, bens não encontrados, executado não localizado, art. 921 CPC, art. 924 V CPC, extinção de execução, CCB prescrição, cédula de crédito bancário prescrição, cédula rural prescrição, nota de crédito rural, LUG art. 70, Lei 10.931/2004, Lei 14.195/2021, inércia do credor, exceção de pré-executividade prescrição, análise de processo executivo, ou qualquer combinação de execução + tempo + inatividade. Esta skill fornece a metodologia completa de análise jurídica, checklist de verificação, cálculo de prazos e estrutura de peça processual. Metodologia exclusiva do escritório Maldonado Advogados.
---

# Skill: Análise de Prescrição Trienal Intercorrente

## O que esta skill faz

Guia a análise completa dos autos de um processo de execução para verificar se houve prescrição intercorrente trienal, com foco em execuções fundadas em Cédula de Crédito Bancário (CCB), Cédula de Crédito Rural Pignoratícia (CRP), Nota de Crédito Rural (NCR) e demais títulos cambiais sujeitos à Lei nº 10.931/2004 c/c Lei Uniforme de Genebra (LUG).

---

## Passo 1 — Identificação do Título e do Prazo Prescricional

Antes de verificar a prescrição intercorrente, confirme qual prazo prescricional se aplica ao título executivo do caso.

### Tabela de prazos por tipo de título

| Tipo de Título | Base Legal | Prazo |
|---|---|---|
| CCB (Cédula de Crédito Bancário) | Lei 10.931/2004, art. 44 + LUG, art. 70 | **3 anos** |
| CRP (Cédula de Crédito Rural Pignoratícia) | Lei 10.931/2004, art. 44 + Decreto 57.663/1966, art. 70 | **3 anos** |
| NCR (Nota de Crédito Rural) | Lei 10.931/2004, art. 44 + LUG, art. 70 | **3 anos** |
| Duplicata / Letra de Câmbio | LUG, art. 70 | **3 anos** |
| Nota Promissória | LUG, art. 70 | **3 anos** |
| Contrato bancário simples (sem natureza cambial) | CC, art. 206, §5º, I | **5 anos** |
| Cheque (ação de execução) | Lei 7.357/85, art. 59 | **6 meses** |

> **Fundamento consolidado para CCB/CRP/NCR:** O STJ pacificou que o art. 44 da Lei nº 10.931/2004 submete esses títulos à legislação cambial, fazendo incidir o art. 70 da LUG (prazo de 3 anos), afastando o prazo quinquenal do art. 206, §5º, I, do CC. O mesmo raciocínio se aplica à CRP e NCR via Decreto 57.663/1966.

**Ação:** Identifique o tipo de título e registre o prazo prescricional aplicável.

---

## Passo 2 — Identificação do Marco Inicial da Prescrição Intercorrente

A prescrição intercorrente **não começa** com o ajuizamento da ação. Ela tem marco inicial específico, definido pelo art. 921, §4º do CPC (com redação dada pela Lei nº 14.195/2021):

> *"O termo inicial da prescrição no curso do processo será a ciência da **primeira tentativa infrutífera de localização do devedor ou de bens penhoráveis**."*

### Como identificar o marco inicial nos autos

Nos documentos do processo, procure por:

1. **Mandado de citação/penhora retornado negativo** — o oficial de justiça certifica que não encontrou o executado ou bens penhoráveis (certidão "baixado parcial", "baixado negativo", "deixei de citar")
2. **Certidão de diligência negativa** — documento cartorário atestando insucesso
3. **Resultado de pesquisas sistêmicas negativas** (SISBAJUD, RENAJUD, INFOJUD) — com ausência de bens
4. **Data de juntada** do documento negativo aos autos — esta é a data-chave (não a data em que o oficial realizou a diligência)

> **Atenção:** O marco inicial é a **ciência** (data de juntada/intimação ao credor), não a data em que o oficial realizou a diligência em campo.

### Atenção — Processos com suspensão judicial anterior

Quando o juízo já decretou suspensão formal pelo art. 921, III do CPC **antes** da Lei 14.195/2021, o marco mais seguro para fins de cálculo é o **despacho de suspensão**. Após 1 ano da suspensão, o prazo prescricional trienal começa a fluir. Esse foi o entendimento aplicado ao processo 0000013-00.0000.8.22.0021 (número fictício; Buritis/RO), em que o próprio juízo decretou suspensão em 18/05/2021, sendo a prescrição consumada em 18/05/2025.

**Registre:** Data e ID/fl. do primeiro documento negativo, e se há despacho formal de suspensão anterior ou posterior.

---

## Passo 3 — Verificação do Período de Suspensão Obrigatório

Após a primeira diligência negativa, o CPC exige **suspensão da execução por 1 (um) ano** antes de começar a correr o prazo prescricional (art. 921, III e §1º, CPC).

### Como contar:

```
MARCO INICIAL (1ª diligência negativa ou despacho de suspensão)
       ↓
+ 1 ANO DE SUSPENSÃO LEGAL (art. 921, §1º, CPC)
       ↓
INÍCIO DO PRAZO PRESCRICIONAL TRIENAL
       ↓
+ 3 ANOS SEM ATO EFICAZ
       ↓
PRESCRIÇÃO INTERCORRENTE CONSUMADA
```

**Verificação importante:** O período de suspensão de 1 ano suspende também a prescrição — só após ele encerrar é que o prazo prescricional começa a fluir.

> Conforme o STJ (Tema 566) e o §4º-A do art. 921 do CPC: durante o período de suspensão e após ele, **somente citação válida ou efetiva constrição patrimonial** interrompem o prazo. Petições genéricas, requerimentos de pesquisas e diligências frustradas **não** interrompem nem suspendem.

---

## Passo 4 — Levantamento de Atos com Potencial de Interrupção/Suspensão

Analise os autos buscando atos que possam ter interrompido ou suspenso o prazo prescricional após o início da contagem. Classifique cada ato encontrado:

### Atos que INTERROMPEM o prazo (recomeçam do zero)
- ✅ **Citação válida** do executado (por oficial, com entrega de contrafé — ainda que dispensada a assinatura por ato conjunto da CGJ)
- ✅ **Penhora efetivada** sobre bem real (imóvel, veículo, dinheiro com bloqueio efetivo e não devolvido)
- ✅ **Bloqueio SISBAJUD com constrição positiva** — valores efetivamente bloqueados e mantidos

### Atos que SUSPENDEM o prazo
- ⏸️ Decisão judicial que determine prazo para o credor diligenciar
- ⏸️ Causa legal de suspensão (art. 921, III — novo prazo de 1 ano)

### Atos que NÃO interrompem nem suspendem (apenas formais/inócuos)
- ❌ Petições requerendo penhora ou citação sem resultado
- ❌ Resultados negativos de SISBAJUD, RENAJUD, INFOJUD
- ❌ Mandados de citação/penhora retornados negativos ("deixei de citar", "baixado negativo")
- ❌ "Baixado positivo ou parcial" de **citação** (sem constrição patrimonial) — apenas citação do devedor não interrompe o prazo intercorrente por si só se não houver penhora
- ❌ Requerimentos de nova pesquisa ou ofício a telefônicas/bancos
- ❌ Meros despachos de andamento
- ❌ Bloqueio SISBAJUD com posterior desbloqueio imediato (sem constrição efetiva)
- ❌ Petições de suspensão da execução pelo credor
- ❌ Pedidos de baixa de anotações (SERASA, SPC)
- ❌ Juntada de documentos pessoais dos executados

> **Fundamento (STJ):** *"Os requerimentos para realização de diligências que se mostraram infrutíferas em localizar o devedor ou seus bens não têm o condão de suspender ou interromper a prescrição intercorrente."* (AgRg no Ag 1.372.530/RS)

### Atenção — Citação válida durante o período de suspensão

Se houver **citação válida ocorrida DURANTE o período de suspensão de 1 ano** (antes do início do prazo prescricional), essa citação não reinicia nem antecipa a contagem — o prazo começa após a suspensão normalmente. Exemplo real (número fictício): no processo 0000012-00.0000.8.22.0001, a Executada C foi citada em 04/12/2023, dentro do período de suspensão (02/03/2023 a 02/03/2024), sem efeito interruptivo sobre o prazo que só começou a fluir em 02/03/2024.

**Construa uma linha do tempo** com todos os eventos relevantes e classifique cada um.

---

## Passo 5 — Análise Individualizada por Executado

Quando há **pluralidade de executados**, analise separadamente cada um:

- Verificar se cada um foi ou não citado validamente
- A citação de um executado **não aproveita** aos demais para fins de interrupção da prescrição intercorrente
- Executado **nunca citado** tem argumento mais forte: não há nenhum ato interruptivo em seu favor desde o início
- Avalista não citado: o prazo corre desde a primeira diligência negativa relativa a ele

**Exemplo real (número fictício):** Processo 0000013-00.0000.8.22.0021 — o devedor (Executado E) foi citado em 04/07/2020, mas o avalista (Executado F) jamais foi citado. Ambos têm o mesmo resultado final (prescrição consumada) porque o prazo trienal correu sem interrupção após o fim da suspensão em 18/05/2022.

---

## Passo 6 — Cálculo do Prazo e Verificação do Consumo

Com os dados levantados, calcule:

```
DATA DO MARCO INICIAL: ___/___/______
+ 1 ano de suspensão: ___/___/______  (início do prazo prescricional)
+ 3 anos do prazo trienal: ___/___/______ (data da consumação, se sem ato interruptivo)

HOUVE ATO INTERRUPTIVO EFICAZ APÓS O INÍCIO DO PRAZO?
  SE SIM → refaça o cálculo a partir do último ato interruptivo válido
  SE NÃO → verifique se a data atual supera a data de consumação
```

**Prescrição consumada se:** a data atual (ou a data do protocolo da exceção/embargos) é posterior à data de consumação calculada, **sem** qualquer ato interruptivo eficaz no intervalo.

---

## Passo 7 — Checklist Final de Cabimento

Confirme cada item antes de concluir pelo cabimento:

- [ ] O título é de natureza cambial e sujeito ao prazo trienal?
- [ ] Foi identificada a primeira diligência negativa (marco inicial)?
- [ ] Há certidão/documento nos autos comprovando a diligência negativa?
- [ ] Decorreu 1 ano de suspensão sem ato interruptivo?
- [ ] Decorreu mais 3 anos sem citação válida ou constrição patrimonial efetiva?
- [ ] Não há causa legal de interrupção ou suspensão no período?
- [ ] A execução ainda está em curso (sem pagamento integral ou outra forma de extinção)?
- [ ] Para cada executado: foi citado? Houve penhora de bens?

**Se todos os itens estiverem marcados:** a prescrição intercorrente está caracterizada e é cabível a exceção de pré-executividade (ou tópico nos embargos à execução).

---

## Passo 8 — Estrutura da Peça Processual

Ao redigir a exceção de pré-executividade ou o tópico dos embargos, siga esta estrutura:

```
1. DA ADMISSIBILIDADE DA EXCEÇÃO DE PRÉ-EXECUTIVIDADE
   - Matéria de ordem pública, conhecível de ofício
   - Prova pré-constituída (certidões do oficial e documentos dos autos)
   - Dispensabilidade de garantia do juízo
   - STJ: REsp 1110925/SP (requisitos da exceção de pré-executividade)

2. DA NATUREZA DO TÍTULO E DO PRAZO PRESCRICIONAL APLICÁVEL
   - Identificação do título (CCB, CRP, NCR etc.)
   - Fundamentação: Lei 10.931/2004, art. 44 + LUG, art. 70
   - Prazo: 3 anos
   - Precedentes do STJ (AgInt nos EDcl no AREsp 1890875; AgInt no AREsp 1992331)

3. DA PRESCRIÇÃO INTERCORRENTE — REGIME JURÍDICO
   - Art. 921, III, §1º, §4º e §4º-A, CPC (redação Lei 14.195/2021)
   - Art. 206-A do CC
   - Art. 487, II e art. 924, V, CPC
   - STJ Tema 566 — o que interrompe e o que não interrompe
   - STF, Súmula 150

4. DA OCORRÊNCIA DA PRESCRIÇÃO NO CASO CONCRETO
   - Identificação do marco inicial (data + ID/fl.)
   - Linha do tempo dos eventos processuais
   - Análise de cada ato: eficaz ou inócuo
   - Ausência de ato eficaz de interrupção
   - Cálculo da consumação do prazo
   - Análise individualizada por executado (se houver pluralidade)

5. DOS PEDIDOS
   - Extinção com resolução de mérito (art. 924, V c/c art. 487, II, CPC)
   - Baixa de todos os apontamentos e restrições
   - Liberação de eventuais constrições ainda vigentes
   - Vedação de novos atos expropriatórios fundados neste processo
   - (Opcional) Suspensão imediata de atos constritivos até julgamento (art. 805, CPC)
```

---

## Fundamentos Legais de Referência

Leia o arquivo `references/fundamentos-legais.md` para os textos normativos completos e os julgados paradigmáticos a citar nas peças.

---

## Casos Paradigmáticos Analisados pelo Escritório

> Números de processo e nomes das partes substituídos por identificadores fictícios; datas e lógica preservadas.

### Caso 1 — Processo 0000011-00.0000.8.22.0001 (Porto Velho/RO, 4ª Vara Cível)
- **Título:** CRP (Cédula de Crédito Rural Pignoratícia)
- **Executados:** Executada A e Executada B
- **Marco inicial:** 1ª diligência negativa
- **Resultado:** Prescrição intercorrente reconhecida pelo juízo. Exceção de pré-executividade acolhida. Execução extinta com resolução de mérito (sentença de 15/05/2026).

### Caso 2 — Processo 0000012-00.0000.8.22.0001 (Porto Velho/RO, 8ª Vara Cível)
- **Título:** CRP (Cédula Rural Pignoratícia; número omitido)
- **Executados:** Executada C (emitente) e Executado D
- **Nuance:** a Executada C foi citada em 04/12/2023 *durante* o período de suspensão — citação não interrompe prazo que ainda não começou a fluir
- **Marco de início do prazo:** 02/03/2024 (fim da suspensão)
- **Data de consumação:** 02/03/2027
- **Status:** Prazo em curso — monitorar até 02/03/2027

### Caso 3 — Processo 0000013-00.0000.8.22.0021 (Buritis/RO, 1ª Vara Genérica)
- **Títulos:** CRP + NCR (números omitidos)
- **Executados:** Executado E (devedor, citado em 04/07/2020) e Executado F (avalista, jamais citado)
- **Suspensão judicial formal:** Despacho de 18/05/2021 (art. 921, III, CPC)
- **Fim da suspensão:** 18/05/2022
- **Data de consumação:** 18/05/2025
- **Status:** 🔴 **PRESCRIÇÃO CONSUMADA HÁ MAIS DE 13 MESES** — exceção de pré-executividade cabível imediatamente

---

## Notas de Atenção

- **Lei 14.195/2021:** Alterou o art. 921 do CPC e criou critérios objetivos para a prescrição intercorrente. Para processos ajuizados antes de sua vigência (26/08/2021), os tribunais têm aplicado a lei nova aos processos em curso sem ofensa ao direito intertemporal.
- **Penhora parcial:** Penhora efetivada sobre parte dos bens não extingue o processo quanto ao saldo remanescente, mas pode interromper a prescrição quanto ao valor constrito. Analisar se a penhora foi suficiente para satisfazer o crédito integral.
- **Citação por edital:** A citação por edital só produz efeitos quando decorrido o prazo editalício e efetivada a citação ficta. Se a consumação da prescrição ocorrer antes do término desse prazo, a exceção é cabível mesmo com edital em curso.
- **TJRO consolidado:** O Tribunal de Justiça de Rondônia aplica o prazo trienal intercorrente às CCB, CRP e NCR com reconhecimento inclusive de ofício (AC 7005370-48.2016.8.22.0014, j. 06/07/2023; AI 0800430-90.2024.8.22.0000, j. 28/05/2024; AC 7001147-07.2020.8.22.0016, j. 22/05/2025).
- **Ação pedida pelo próprio banco (suspensão):** Quando o banco pede a suspensão nos termos do art. 921 e o juízo defere, o despacho constitui marco inequívoco. Após 1 ano da suspensão sem retomada pelo credor, a prescrição intercorrente flui e se consuma 3 anos depois.
