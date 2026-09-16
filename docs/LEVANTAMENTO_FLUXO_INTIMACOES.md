# Levantamento — rotina automática de intimações (08:00 diário)

> Pedido da Dra. Juliana em 10/09/2026: estabelecer o fluxo completo de controle de intimações
> para rodar sozinho todos os dias às 08:00 — capturar, analisar, distribuir ao advogado
> responsável, abrir os prazos (protocolo e coleta de provas) e, quando for manifestação, já
> entregar a minuta pronta para o advogado só revisar.
>
> Este documento é o levantamento **antes** de escrever qualquer código. Primeiro o que já está
> confirmado (para não perguntar duas vezes), depois o que falta.

---

## PARTE 0 — Decisões da Dra. Juliana em 10/09/2026 (já valem)

**1. A linha do tempo — D-5 é o marco dos dois.**

```
INTIMAÇÃO (dia 0)
   |
   +-- tarefa: advogado confecciona a peça .......... vence D-5
   +-- tarefa: setor de provas monta a pasta no Zeus  vence D-5
   |
  D-5   peça pronta E pasta pronta
   |
  D-3   CONTROLADORIA PROTOCOLA  (responsabilidade exclusiva dela)
   |
  PRAZO FATAL
```

Ou seja: em D-5 a Controladoria tem tudo na mão — peça e documentos — e usa D-5→D-3 como
folga para protocolar. Bate com o POP-CJ-003 (D-5 = 48h antes de D-3) e acrescenta o setor de
provas no mesmo marco.

**2. Autonomia da rotina das 08:00 — distribui e abre prazos sozinha.**
Cria automaticamente: a tarefa de distribuição ao advogado responsável, o D-5, o D-3 e a tarefa
do setor de provas; minuta a peça e anexa o link. **Protocolo continua sendo sempre humano**
(POP-CJ-PROT-001) — a automação nunca protocola.

**3. Escopo das minutas — todos os atos.**
A automação minuta qualquer ato, não só manifestação simples. Regra que continua valendo em
todos eles: a peça sai **pronta para revisão**, no timbrado, com **placeholder destacado em
amarelo** em tudo que dependa de documento não lido ou de precedente não conferido — nunca
preenchido por suposição. Quanto mais complexo o ato (contestação, recurso a tribunal superior),
mais a peça é um rascunho estruturado do que uma peça final: ela poupa a montagem, não substitui
a leitura dos autos pelo advogado.

**4. Onde roda — servidor/nuvem do escritório.**
A rotina não depende de nenhuma máquina pessoal ligada. Detalhes de infraestrutura ainda a
definir (ver G1b).

**5. Captura — fica só nas OABs que já olhamos.**
Decisão da Dra. Juliana: manter `OABS_MONITORADAS` como está (Renan 5769/RO e Bruno Vinícius
13021/RO). A rotina, portanto, enxerga o que sai nessas duas OABs.

**6. Setor de Provas — César, Ana Clara e Hanna.**
IDs conferidos: César Augusto Oliveira Petkowski (261858), Ana Clara Botelho Leal Gomes (296105),
Hanna Luisa Furtado Pereira (296635). Tarefa: `PROTOCOLO - ORGANIZAR DOCUMENTOS` (9970888),
vencendo no D-5. A automação **monta a lista sugerida** de documentos a partir do ato e da tese,
declarada como palpite; o setor confere e completa.

**7. Contagem — dias úteis de trás para frente a partir do fatal.**
D-3 = 3 dias úteis antes do fatal; D-5 = 5 dias úteis antes. Em prazo curto (embargos de
declaração e afins), **a elaboração fica para o mesmo dia, sem prejuízo de D-5 e D-3** — os
marcos são trazidos para hoje em vez de nascerem vencidos, e o item é marcado `PRAZO CURTO`.

**8. Minuta — todas as áreas, e o advogado recebe para revisar.**
A tarefa do advogado é `CONFERIR/REVISAR PETIÇÃO` (2596525). Concluída a revisão, **ele devolve
à Controladoria com a tag `PEÇA APROVADA PARA PROTOCOLO`** (8720914) — e a Controladoria
protocola em D-3.

**9. Relatório das 08:00 — três canais.**
Tarefa no ADVBOX + e-mail + arquivo no Zeus, para as duas controllers e a Gerência Jurídica
(Nataly, Manuelle, Dra. Juliana). Arquivo em `ZEUS > CONTROLADORIA > RELATÓRIOS DIÁRIOS`.
O que a rotina não consegue decidir sozinha **vira tarefa para a controller conferir**.

---

## PARTE 4 — Estado da implementação (10/09/2026)

### Já construído e testado

| Peça | Onde | Estado |
|---|---|---|
| Motor de prazos D-5/D-3/fatal, dias úteis, feriados RO + Porto Velho + recesso (art. 220) | `OPERACIONAL/prazos.py` | pronto |
| Regra do prazo curto (ED no mesmo dia, sem prejuízo de D-5/D-3) | `prazos.marcos()` | pronto |
| Plano de ação por intimação (as 4 tarefas + audiência + conferência) | `OPERACIONAL/rotina_diaria.py` | pronto |
| Roteamento controller ← advogado | `OPERACIONAL/roteamento_controller.py` | pronto |
| Relatório da rodada | `rotina_diaria.relatorio_texto()` | pronto |
| Comando | `python OPERACIONAL/main.py rotina --dias 1` | pronto (simulação) |

Modo simulação é o padrão: a rodada monta tudo e **não grava nada** no ADVBOX. `--gravar` é o que
autoriza a escrita — é com essa flag que a rotina agendada vai rodar, depois da semana de teste.

### Ainda falta

1. **Onde a rotina roda** — a senhora não soube informar se existe servidor. Enquanto não houver,
   ela roda sob demanda, na mão. Ver G1b.
2. **E-mail do relatório** — o OAuth atual do Google só tem escopo de Drive/Docs/Sheets. Mandar
   e-mail exige acrescentar o escopo do Gmail e reautenticar a conta do escritório (`drive sair`
   + `drive autenticar`). Enquanto isso, o relatório sai no ADVBOX e no Zeus.
3. **Tarefa de relatório no ADVBOX** — o endpoint `/posts` exige `lawsuits_id`, e o relatório
   diário não é de nenhum processo. Preciso testar se a conta aceita tarefa sem processo; se não
   aceitar, o relatório vai por e-mail e Zeus, e no ADVBOX entra só como tarefa de conferência
   dos itens que precisam de decisão humana.
4. **A minuta automática.** Este é o ponto mais importante e o mais delicado: a rotina em Python
   captura, classifica, calcula prazo, decide de quem é e abre as tarefas — mas **quem escreve a
   peça é o agente Claude**, com a skill `timbrado`, e isso não roda dentro do script. Enquanto
   não estiver ligado, a tarefa do advogado diz **"PEÇA A CONFECCIONAR"**, e não "minuta pronta
   para revisão" — a automação não pode prometer o que não entregou. Ligar isso significa rodar o
   agente pela API da Anthropic no mesmo servidor, com a chave do escritório.

---

## PARTE 1 — O que já está confirmado (não precisa responder)

Levantado do POP real, do mapa mestre e da própria conta ADVBOX do escritório.

### Jornada, conforme o POP-CJ-003 + POP-CJ-PROT-001

1. Intimação chega (hoje via DJE; na automação, via API DJEN/Comunica do CNJ, por OAB).
2. Tem conteúdo decisório (liminar, sentença, acórdão)? **Sim** → abre prazo de análise no mesmo dia.
3. Lança **D-5** (confecção pela advocacia) e **D-3** (protocolo pela Controladoria) — D-5 = 48h antes de D-3.
4. Ato decisório nunca sai com recurso fechado: cotejo INICIAL x DECISÃO (contradição / obscuridade /
   omissão) antes de decidir entre ED (5 dias úteis) e agravo/apelação (15) — POP-CJ-003-A.
5. Controle às 17h: D-5 cumprido? Não → sinaliza, registra e escala à Assessoria da GJ.
6. Peça aprovada pela GJ volta com a tag **PEÇA APROVADA PARA PROTOCOLO**; o protocolo em D-3 é
   **responsabilidade exclusiva da Controladoria**, nunca do advogado (POP-CJ-PROT-001).
7. Peça não chegou até D-3 → avoca e escala à GJ no mesmo dia.
8. Protocolado: comprovante salvo no ADVBOX **e** no Zeus, na mesma hora.
9. Audiência designada → segunda tarefa, para Karla e Anna Lydia, com o texto de WhatsApp pronto
   (POP-CJ-003-C).
10. Agendamento de despacho em até 1 dia útil após o protocolo (POP-CJ-DESP-001).

### Quem lança e quem recebe (POP-CJ-003-D, definido em 10/09/2026)

| Responsável pelo processo | Lança | Recebe |
|---|---|---|
| A própria controller | ela mesma | ela mesma |
| Dr. Renan ou Dra. Juliana | Nataly | Nataly |
| Um dos 10 advogados do mapa | a controller dele | o advogado |
| Qualquer outro | Manuelle | Manuelle |

Controller Nataly: Arilson · Mailson · Josué Kalebe · Heloísa · Agenor
Controller Manuelle: Bruno Vinícius · Felipe Narciso · Matheus · Taynara · Ana Sheila

### Tipos de tarefa que já existem na conta (IDs conferidos)

| Etapa | Tipo de tarefa no ADVBOX | ID |
|---|---|---|
| Protocolo em D-3 | `PROTOCOLO D-3` | 8941168 |
| Protocolo D-2 / D-1 / fatal | `PROTOCOLO D-2` · `PROTOCOLO D-1` · `PROTOCOLO - PRAZO FATAL` | 10177444 · 10177445 · 10177446 |
| Documentos do protocolo | `PROTOCOLO - ORGANIZAR DOCUMENTOS` | 9970888 |
| Coleta de provas | `COLETA DE PROVAS` | 2596485 |
| Pedir documento ao cliente | `SOLICITAR DOCUMENTAÇÃO` | 9970898 |
| Conferência da pasta | `CONFERIR PASTA DE DOCUMENTOS` | 10347758 |
| Peça pronta / com ajuste | `PEÇA APROVADA PARA PROTOCOLO` · `PEÇA ENVIADA PARA AJUSTES` | 8720914 · 8690258 |
| Revisão pelo advogado | `CONFERIR/REVISAR PETIÇÃO` | 2596525 |
| Peças | `MANIFESTAÇÃO` · `EMBARGOS DE DECLARAÇÃO` · `AGRAVO DE INSTRUMENTO` · `RECURSO DE APELAÇÃO/INOMINADO` · `RÉPLICA/IMPUGNAÇÃO À CONTESTAÇÃO` · `CONTESTAÇÃO` · `ELABORAR CONTRARRAZÕES` | 4654962 · 4654939 · 2596522 · 4654965 · 2596496 · 9304697 · 4654896 |
| Perda de prazo | `PERDA DE PRAZO (D-3)` · `PERDA DE PRAZO (D-2)` | 4666068 · 4666069 |
| Audiência | `AVISAR CLIENTE DA AUDIÊNCIA` | 2596497 |
| Despacho | `AGENDAR DESPACHO` · `DESPACHO REALIZADO` | 9222516 · 10349941 |

### O que a automação já faz hoje

- Captura DJEN por OAB, cruza com o ADVBOX pelo número do processo, classifica o ato, calcula
  prazo preliminar, aplica a regra ED-antes-de-agravo e decide a controller — tudo isso rodando.
- Produz peça no timbrado 2026 e arquiva em `ZEUS > PEÇAS AUTOMAÇÃO > [CLIENTE] - [Nº PROCESSO]`.
- Cria tarefa no ADVBOX (`/posts`) — hoje **só com confirmação manual item a item**.

---

## PARTE 2 — O que preciso que a senhora responda

Marquei com 🔴 o que **trava** a automação (sem isso não consigo escrever a rotina) e com 🟡 o que
dá para começar sem, ajustando depois.

### Bloco A — A linha do tempo do prazo (o coração da rotina)

✅ **A1. RESPONDIDA** — D-5 é o marco dos dois (peça + pasta). Ver Parte 0.

🔴 **A2.** D-5 e D-3 são contados em **dias úteis a partir do prazo fatal**? Ou seja, prazo fatal
dia 30 (útil) → D-3 = 3 dias úteis antes, D-5 = 5 dias úteis antes?

🔴 **A3.** Quando o prazo é curto — intimação com 5 dias úteis, por exemplo — D-5 e D-3 não cabem
antes do fatal. O que a Controladoria faz nesses casos hoje?

🟡 **A4.** Qual calendário de feriados devo usar no cálculo (nacional + estadual RO + municipal
Porto Velho + suspensões do TJRO)? Existe alguma lista que o escritório já segue, ou puxo do
calendário do TJRO?

### Bloco B — Setor de Provas

🔴 **B1.** Quem são as pessoas do Setor de Provas / Documentos? (nome como está no ADVBOX, para eu
pegar os IDs — como fiz com as controllers)

🔴 **B2.** Qual tipo de tarefa usar para eles: `COLETA DE PROVAS`, `PROTOCOLO - ORGANIZAR
DOCUMENTOS`, `SOLICITAR DOCUMENTAÇÃO` ou `CONFERIR PASTA DE DOCUMENTOS`? (existem os quatro)

🔴 **B3.** O que a tarefa precisa dizer para eles? A automação sabe qual é a tese e qual é o ato —
consigo montar o **rol de documentos** esperado (é o que a skill `inicial-anexos` já faz para as
4 teses de dívida rural). Mas para os demais tipos de ato, quem define o que coletar: o advogado
na análise, ou a Controladoria já manda a lista?

🟡 **B4.** "Pasta pronta no Zeus" significa exatamente o quê — os documentos dentro da pasta do
cliente, ou uma subpasta específica do protocolo (algo como `PROTOCOLOS > [processo] > [data]`)?
Quem confere que ficou pronta: a controller, na véspera?

### Bloco C — A peça que a automação minuta

✅ **C1. RESPONDIDA** — todos os atos, sempre prontos para revisão. Ver Parte 0.

🔴 **C2.** Vale para toda a carteira ou só para dívida rural? (a carteira tem regularização
fundiária, agrário, precatório, dano ambiental, criminal — as skills e os modelos hoje são de
dívida rural)

🔴 **C3.** A minuta pronta gera qual tarefa para o advogado — `CONFERIR/REVISAR PETIÇÃO` (revisar o
que já está pronto) ou continua sendo `MANIFESTAÇÃO` (confeccionar)? Isso muda o que ele vê na
agenda dele.

🟡 **C4.** Depois que o advogado revisa, a peça passa pela GJ (tag `PEÇA APROVADA PARA PROTOCOLO`)
antes do protocolo, ou o advogado aprova direto para a Controladoria protocolar?

### Bloco D — Autonomia da rotina das 08:00

✅ **D1. RESPONDIDA** — distribui, abre D-5/D-3 e a tarefa de provas, e minuta, tudo automático.
Protocolo nunca. Ver Parte 0.

🔴 **D2.** O que a rotina faz com o que ela **não** consegue decidir sozinha (ato ambíguo, processo
sem cadastro no ADVBOX, tese não identificada)? Abre tarefa para a controller conferir, ou só
entra no relatório do dia?

🔴 **D3.** Para onde vai o relatório da rodada das 08:00 — tarefa no ADVBOX para as duas
controllers, e-mail, WhatsApp, arquivo no Zeus? (posso fazer mais de um)

🟡 **D4.** Rodo também a **checagem das 17h** do POP-CJ-003 (D-5 não cumprido → sinaliza e escala à
Assessoria da GJ)? É a mesma máquina, outro horário.

🟡 **D5.** A rodada deve alimentar a **planilha de apuração diária de KPI** (POP-CJ-002)? Se sim,
preciso do link da planilha e de quais colunas.

### Bloco E — Cobertura da captura

🔴 **E1.** **As OABs dos dez advogados.** Hoje só monitoro Renan (5769/RO) e Bruno (13021/RO) —
tudo que sai no nome do Matheus, Josué, Arilson etc. **não está sendo capturado**. Preciso de
número e UF de cada um.

🟡 **E2.** Fora o DJEN, de onde mais chega intimação hoje (push do PJe por e-mail, DJE estadual,
sistemas de outros estados — POP-CJ-016)? Se chega por e-mail, em qual caixa?

🟡 **E3.** Segunda-feira a rodada deve varrer sexta/sábado/domingo, certo? E depois de feriado, o
período inteiro?

### Bloco F — Exceções

🟡 **F1.** Processo da intimação **não existe** no ADVBOX: abre tarefa de cadastro para quem?
(existe o tipo `CADASTRAR PROCESSOS`)

🟡 **F2.** Mais de um cadastro para o mesmo número de processo — qual a regra de desempate?

🟡 **F3.** Intimação em processo arquivado: hoje decidimos que segue com a controller do dono, com
marca de "PROCESSO ARQUIVADO". Confirma?

🟡 **F4.** Os níveis `ANÁLISE - NÍVEL 01` a `05` — o que significam? Servem para graduar a
complexidade da análise que a automação distribui?

### Bloco G — Onde a rotina roda

✅ **G1a. RESPONDIDA** — servidor/nuvem do escritório.

🔴 **G1b.** Qual servidor, concretamente? O escritório já tem alguma máquina/VPS/servidor
próprio rodando outra coisa, ou preciso propor uma contratação (uma VPS pequena resolve, custa
pouco)? Isso muda quem cuida das credenciais e de onde elas ficam guardadas.

---

## PARTE 3 — Sugestão de teste

Assim que os itens 🔴 estiverem respondidos, proponho rodar **em modo simulação por uma semana**:
a rotina roda às 08:00, monta tudo (tarefas, prazos, minutas, relatório) e **não grava nada no
ADVBOX** — entrega o relatório para a senhora e as controllers conferirem contra o que elas
fariam à mão. Onde divergir, a gente corrige a regra. Só depois libera a gravação automática.

É o mesmo princípio que já usamos aqui: primeiro a automação prova que acerta, depois ela ganha
autonomia.


---

## PARTE 5 — O teste com a intimação de hoje (10/09/2026)

Rodada real sobre as publicações do dia: **21 intimações**, 89 agendamentos planejados,
roteadas para 8 advogados. Um processo foi levado até o fim (0000000-00.0000.0.00.0000,
Cliente A × banco — emenda à inicial determinada pela 6ª Vara Cível).

### Correções que o teste obrigou (todas já aplicadas)

| # | Defeito | Correção |
|---|---|---|
| 1 | Todas as tarefas nasciam com a data de hoje | cada tarefa nasce na data do seu marco (D-5, D-3, D+1); o campo de prazo leva o fatal |
| 2 | Uma única tarefa para o setor de provas, no D-5 | duas: `PROTOCOLO - ORGANIZAR DOCUMENTOS` no 1º dia útil após a intimação e `CONFERIR PASTA DE DOCUMENTOS` em D-5 |
| 3 | Protocolo D-3 só para a controller | advogado **e** controller |
| 4 | A tarefa dizia "minuta pronta" sem peça anexada | texto condicional: só diz "pronta para revisão" quando há link |
| 5 | `drive autenticar` estourava com token revogado | apaga o token e refaz o consentimento |
| 6 | `arquivar_peca` duplicava o arquivo a cada revisão | substitui no mesmo `fileId` (POP-CJ-003-B, etapa 9) |
| 7 | Assinatura sem os sublinhados de MALDONADO/sobrenome | corrigido na geração da peça |
| 8 | Controller aparecia duas vezes no protocolo quando era a própria responsável | destinatários deduplicados |

### Limites da API do ADVBOX descobertos no teste

- **`/posts/{id}` só aceita GET.** Não há como editar nem apagar tarefa pela API (405 no PUT) —
  tarefa criada errada só se resolve à mão no painel. É a razão de a semana de conferência
  rodar em simulação antes de ligar a gravação.
- **Não há upload de documento.** A peça vai para o Zeus e o link entra no comentário da tarefa;
  anexar o arquivo dentro do ADVBOX teria que ser manual.

### Calibragem pendente (decisão da Dra. Juliana)

O classificador leu o **despacho de emenda à inicial** como ato decisório e queria abrir a tarefa
de cotejo INICIAL × DECISÃO (janela dos ED). Não cabe: determinação de emenda é para cumprir, não
para embargar. Falta ensinar o classificador a distinguir os dois casos.

### A planilha de conferência

`ZEUS > CONTROLADORIA > RELATORIOS DIARIOS > CONFERENCIA DA ROTINA DE INTIMACOES`

Duas abas acumulativas — **AGENDAMENTOS** (uma linha por tarefa, com as colunas "Confere?" e
"Observação da controller" em branco) e **INTIMACOES** (uma linha por publicação, com ato,
D-5/D-3/fatal, controller, advogado, regra aplicada e pendências).

Comando da semana de teste (não grava nada no ADVBOX):

```
python OPERACIONAL/main.py rotina --dias 1 --planilha
```
