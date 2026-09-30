# Maldonado Advogados - Central de Automações

> Escritório: **Maldonado Advogados** | Responsável: **Dr. Renan Gomes Maldonado de Jesus (OAB/RO 5769)** | Gerente Jurídico: **Dra. Juliana Ferreira Gusmão de Lara** | Foro: **Porto Velho - RO (TJRO)**
> Área: **Dívida rural bancária** (prorrogação/alongamento, descaracterização de mora — Tema 28/STJ, revisional bancária).
> **Prioridade do projeto: Squad Controladoria primeiro** (eliminar o gargalo das 2 controllers e das 200 correções de peça/mês) — Squads Dívida Rural e Jurimetria seguem em paralelo/sequência.

## Estrutura

```
MALDONADO_ADVOGADOS/
├── INTEGRACOES/          # Modulos compartilhados (todos os squads usam)
│   ├── google_integration.py   # Google Drive/Docs/Sheets
│   ├── advbox_integration.py   # API ADVBOX (clientes, processos, tarefas)
│   ├── comunica_djen.py        # API DJEN/Comunica (CNJ) - captura de intimacoes por OAB
│   ├── atende_direito_integration.py  # API Atende Direito (CRM/atendimento) - leads qualificados
│   └── sync_integration.py     # API SYNC (Atende Direito) - monitoramento processual:
│                               # intimacao, prazo deduplicado por ato, autos em Markdown.
│                               # Outro produto, outra chave - nao confundir com o CRM acima.
│
├── OPERACIONAL/           # Squad Controladoria (PRIORIDADE) + Divida Rural + Intake
│   ├── main.py                     # Comandos: tarefas / processos / prazos / triagem / intake / criar-tarefa / drive / anexos / kpi / vault
│   ├── triagem_divida_rural.py     # Classificador: intimacao -> tese -> peca necessaria -> prioridade
│   ├── intake_atende_direito.py    # Lead qualificado (Atende Direito) -> cliente + processo ADVBOX + pasta Drive
│   ├── custas_protocolo.py         # Trava de custas antes do protocolo: inicial ->
│   │                                #  gratuidade x guia x documentos (POP-CJ-006)
│   ├── vault_obsidian.py           # Banco de teses: apuracao de KPI -> nota de caso e de orgao
│   │                                #  julgador no vault Obsidian (BASE_CONHECIMENTO/)
│   └── anexos_inicial.py           # Documentos da inicial: inventario da pasta do cliente -> rol da tese
│                                    # -> recorte do PDF -> placeholder do modelo (skill `inicial-anexos`)
│                                    # (o texto da minuta continua saindo do agente Claude; este modulo
│                                    #  cuida so dos documentos que instruem a peca)
│
├── docs/pop_controladoria/         # POP real da Controladoria (Dra. Juliana, 20/08/2026)
│   └── MAPA_MESTRE_CONTROLADORIA_JULIANA.png  # Mapa mestre: 3 estagios, POP-CJ-001 a 020
│
├── .claude/agents/        # Agentes Claude Code / Claude.ai (mesmo conteudo do Custom Instructions)
│   ├── maldonado-controladoria.md  # Squad Controladoria (triagem)
│   ├── maldonado-divida-rural.md   # Squad Divida Rural (producao de pecas)
│   └── maldonado-jurimetria.md     # Squad Jurimetria (banco de teses / prognostico)
│
├── .claude/skills/        # Skills (carregadas sob demanda ao produzir peca)
│   ├── timbrado/                   # Papel timbrado + formatacao do escritorio
│   ├── descaracterizacao-mora/     # Metodologia Tema 28 (2 elos, restricoes absolutas)
│   ├── inicial-anexos/             # Documentos que instruem a inicial (recorte -> placeholder)
│   ├── alongamento-divida-rural/   # Nucleo Sigma: prorrogacao/MCR 2.6.4/Sumula 298 + precedentes
│   ├── jurisprudencia-rural/       # Coletanea Leopoldo Castilho (315 ementas prontas p/ citar)
│   ├── analise-pontos-controvertidos/ # Matriz fato a fato (saneamento, art. 357) — inicial x contestacao
│   └── prescricao-intercorrente/   # Prescricao trienal em execucao (art. 921) + calculadora de prazo
│
├── DOCS_MODELOS/          # Timbrado + pecas-modelo do escritorio
├── BASE_CONHECIMENTO/     # Banco de teses (vault Obsidian) - ver Squad Jurimetria
├── CADASTROS/             # Fichas e dados de cliente
│
├── config/                # Configuracoes centralizadas
│   ├── .env               # (criar a partir de .env.example - NAO versionar)
│   ├── .env.example       # Template de variaveis
│   ├── equipe.py           # IDs de usuario ADVBOX por papel + OABs monitoradas no DJEN
│   └── credentials.json   # (credenciais Google - NAO versionar)
│
├── docs/                  # Documentacao (onboarding, white-label spec)
├── CLAUDE.md              # Este arquivo
└── requirements.txt
```

> **Fora do escopo nesta fase:** ZapSign (assinatura) e Squad Financeiro (fechamento/Asaas) não
> foram contratados por este cliente — o escritório já opera esse fluxo por conta própria.
> Ver `docs/_WHITE_LABEL_SPEC.md` §5. O **Atende Direito entrou no escopo** (Squad Comercial/Intake
> — ver seção abaixo).
>
> **SYNC — ativo desde 21/09/2026, somente leitura:** o Sync (monitoramento processual do
> Atende Direito, outro produto que não o CRM) foi contratado e a chave está no `config/.env`.
> A triagem **continua no DJEN por padrão**; o Sync entra com `--fonte sync` ou `--fonte ambas`.
> Ver `docs/INTEGRACAO_SYNC.md` e a seção "SYNC API" abaixo.

## Squad Controladoria (OPERACIONAL) — PRIORIDADE 1

Objetivo: eliminar a triagem manual das 2 controllers, que hoje só distribuem intimações
sem tratamento estratégico. Duas frentes, conforme o Dr. Renan definiu no fechamento:
(1) processos em andamento (intimações/publicações) e (2) novas ações iniciais.

**POP real do escritório:** a Dra. Juliana enviou o mapa mestre completo da Controladoria
(3 estágios — Entrada / Ciclo Operacional Contínuo / Encerramento — com ~20 POPs numerados
POP-CJ-001 a POP-CJ-020, cobrindo KPI, prazos D-5/D-3, saneamento, protocolo, PMP, encerramento
etc.). A imagem está em `docs/pop_controladoria/MAPA_MESTRE_CONTROLADORIA_JULIANA.png` e o
detalhamento textual completo está em `.claude/agents/maldonado-controladoria.md` — esse agente
é a fonte da verdade operacional, não o resumo abaixo (que cobre só a fatia já automatizada,
POP-CJ-003).

Comando:
```
python OPERACIONAL/main.py triagem --dias 7
python OPERACIONAL/main.py triagem --dias 7 --criar-tarefa   # cria a tarefa no ADVBOX (pede confirmacao)
```

Fluxo:
1. Busca as intimações/publicações dos últimos N dias via **DJEN/Comunica (CNJ)**, filtrando pelas
   OABs do escritório (`config/equipe.py` → `OABS_MONITORADAS`).
2. Para cada intimação, `triagem_divida_rural.py` classifica: tipo de ato, providência cabível,
   qual das 4 teses de dívida rural está envolvida (se for o caso), peça necessária e prioridade.
3. Cruza com o **ADVBOX** (`/lawsuits`) pelo número do processo, para trazer cliente e responsável.
4. Imprime o relatório de triagem (ou, com `--criar-tarefa`, cria a tarefa em `/posts` — sempre com
   confirmação manual antes de gravar).
5. Nunca protocola, nunca decide sozinho qual das 4 teses cabe quando for ambíguo — sinaliza e para.

Regras:
- Tarefas ADVBOX usam endpoint `/posts` (não `/tasks`).
- Campo `from` é a **controller do advogado responsável pelo processo** (`config/equipe.py` →
  `CONTROLLERS`) — ver "Quem lança a intimação" abaixo. Não é mais o Dr. Renan.
- Campo de mensagem é `"comments"` (não `"notes"`).
- **Nunca criar tarefa sem confirmação explícita** (`--criar-tarefa` ainda pede "s/N" no terminal).
- A API DJEN é instável (alterna respostas de "sistema ocupado" e falso-vazio para a mesma
  consulta) — o módulo já trata isso com retry/backoff; se mesmo assim vier vazio, o script avisa
  em vez de reportar silenciosamente "nenhuma intimação".

### O que a rotina agenda — calibrado pela conferência das controllers (21/09/2026)

`OPERACIONAL/providencia.py` decide o que a intimação pede **de nós** antes de abrir tarefa. Nasceu das
572 linhas conferidas pelas controllers na planilha de conferência (rodadas 10–17/09): contra essa
conferência, a rotina antiga acertava **54%** das tarefas de 15–17/09 e a atual acerta **90%** (325 → 188
tarefas). Regras (não desfazer):
- **Decisão sem prazo no texto → marcos dos embargos de declaração (5 dias úteis)**, não do recurso
  principal (15). Sem vício, o advogado avisa e a controller reagenda. ED em agravo não gera tarefa do
  setor de provas.
- **Ato burocrático** (remessa dos autos, migração de sistema) → nenhuma tarefa. **Ordem só à parte
  contrária** (pelo `destinatarios[].polo` do DJEN) ou **andamento sem ordem para nós** (Sisbajud deferido,
  "à CPE para que prossiga") → só a análise do advogado, sem peça nem protocolo. Sinal de decisão
  desfavorável, sentença ou ordem às partes/ao advogado mantêm o fluxo completo.
- O comando só conta com **verbo de ordem** ("intime-se a parte exequente", "fica a parte requerente
  intimada"): o cabeçalho do ato ("ADVOGADO DO EMBARGADO:") não é ordem.
- **Processo sem cadastro no ADVBOX não gera tarefa nem marcador**, só pendência.
- **2º grau (Dra. Juliana, 21/09/2026):** recurso distribuído → controller agenda **despacho com o
  relator** (D+1); na **apelação**, o advogado decide em D+1, **justificando**, se a sustentação oral será
  presencial (cotação de viagem). **Inclusão em pauta** → despacho com os **vogais** + **memoriais**
  (avaliar novo despacho com o relator), com prazo pela data da sessão lida no texto.
- Rodada das 08:00 no Mac: `deploy/controladoria_diaria.sh` (intimações em simulação + despachos +
  custas), via `com.maldonado.controladoria.plist`, até a VPS assumir.
- **Rodada perdida se repõe sozinha** (22/09/2026): `OPERACIONAL/rotina_recuperar.py` guarda a última
  rodada publicada em `_trabalho/logs/ultima_rodada_intimacoes.txt` e refaz **cada dia útil que faltou**,
  um por vez, com a data daquele dia (o D-5/D-3 conta da publicação, então varrer tudo numa rodada só
  falsearia os marcos). Teto de 7 dias por chamada, e dia com falha do DJEN **não** é marcado como feito.
  Os despachos usam janela de 7 dias, que o upsert por id de tarefa torna idempotente.
- **Armadilha do macOS (TCC):** o projeto está em `~/Documents`, pasta protegida. O agente do launchd
  roda como `/bin/bash`, que **não tem Acesso Total ao Disco**, e a rodada morre com
  `Operation not permitted` — foi o que aconteceu em 22/09/2026 (a planilha de despachos ficou parada
  em 18/09). Conferir sempre `_trabalho/logs/controladoria_launchd.err`. Sai disso de dois jeitos:
  dar Acesso Total ao Disco a `/bin/bash` (Ajustes → Privacidade e Segurança) ou mover o projeto para
  fora de `~/Documents`. Na VPS o problema não existe.

### Quem lança a intimação — controller por advogado (POP-CJ-003-D)

Regra da Dra. Juliana (10/09/2026): o Dr. Renan **sai** do controle de intimações. Quem lança a
tarefa no ADVBOX (campo `from`) é a **controller do advogado responsável pelo processo**; quem
recebe (`guests`) é o **próprio advogado responsável**.

| Controller | Advogados |
|---|---|
| **Nataly Damascena de Carvalho** (252009) | Arilson Cruz Lopes (130926) · Mailson Santos Monteiro (93693) · Josué Kalebe Oliveira de Andrade (100903) · Heloisa Garcia Antunes (288554) · Agenor Rufino de Melo Neto (262240) |
| **Manuelle Abreu** (189532) | Bruno Vinícius de Souza Faustino (101621) · Felipe da Conceição Souza **Narciso** (253330) · Matheus Ramos (182170) · Taynara Scatolin (288544) · Ana Sheila da Silva Garcez (295888) |

- Mapa em `config/equipe.py` → `CONTROLLERS`; resolução em
  `OPERACIONAL/roteamento_controller.py`. Nenhum módulo mapeia pessoa por conta própria.
- **IDs conferidos contra a conta real em 10/09/2026** (`python OPERACIONAL/main.py advbox`
  reconfere os 12 de uma vez). O match vai pelo **ID** do responsável do processo; o nome só entra
  como reserva, porque a grafia do ADVBOX não é a do dia a dia: o Dr. Felipe está cadastrado como
  **NARCISO** (não "Narcísio"), e há **dois Brunos** na conta — o do mapa é o Bruno Vinícius
  (OAB/RO 13021), não o Bruno Fernando Ferreira (271032).
**As regras, na ordem em que o roteamento aplica** (contagem sobre a carteira real de
10/09/2026 — 3.004 processos, dos quais 1.163 ativos):

| # | Responsável pelo processo no ADVBOX | Quem lança | Quem recebe | Ativos (total) |
|---|---|---|---|---|
| 1 | **A própria controller** | ela mesma | ela mesma | 130 (266) |
| 2 | **Dr. Renan ou Dra. Juliana** | Nataly | Nataly | 28 (211) |
| 3 | **Um dos 10 advogados** do mapa | a controller dele | o advogado | 913 (1.351) |
| 4 | **Qualquer outro** (advogado que saiu, estagiário, engenheiro, atendimento) | Manuelle | Manuelle | 92 (1.176) |

**O tratamento de intimação é sempre de uma controller.** A Dra. Juliana é gerente jurídica, não
controller: o ID dela (`USUARIOS_ADVBOX["GERENCIA_JURIDICA"]`) não é destino de tarefa de
intimação em nenhuma das quatro rotas — conferido contra a carteira inteira, aparece em zero
processos. Por isso as regras 2 e 4 mandam para uma controller, que lança **e** recebe: nem o
Dr. Renan, nem a Dra. Juliana, nem quem não é advogado (Karla é atendimento ao cliente; Bruno
Fernando Ferreira, o outro Bruno da conta, é engenheiro agrônomo) pode ter intimação na fila.

**Processo arquivado não muda o destino** — segue com a controller do dono. O que muda é o
relatório, que marca `PROCESSO ARQUIVADO` e conta esses itens à parte: em regra não há
agendamento, e a controller confere se cabe algo (desarquivamento, execução de honorários, baixa)
antes de agendar. Detectar isso não é trivial: o ADVBOX marca em dois campos que nem sempre
concordam (`step` = ARQUIVAMENTO e `stage` = ARQUIVADO...), com 55 processos em que só um marca —
48 deles "CRIADO EQUIVOCADAMENTE" —, então o código considera arquivado se **qualquer um** marcar.
`status_closure` (data de encerramento) não serve sozinho: 648 processos têm data e seguem ativos.

Responsável que não é mais advogado ativo do escritório não entra no mapa, por decisão da
Dra. Juliana, mesmo quando concentra grande volume de processos (em regra já arquivados): cai na regra 4.

**Carga resultante nos 1.163 processos ativos:** Manuelle 733 (585 dos advogados dela + 92 da
regra 4 + 56 em que ela é a responsável), Nataly 430 (328 + 74 + 28 da direção). Nenhum processo
da carteira fica sem destino, e nenhum cai na gerência jurídica.

- `CONTROLLER_FALLBACK = "MANUELLE"` é o que garante que nada fique órfão. Pondo `None`, a
  automação volta a **não criar** tarefa para responsável fora do mapa: o item sobe como
  `CONTROLLER A DEFINIR — <motivo>` e entra no resumo final.
- Vale para toda tarefa da automação (triagem, intake e `criar-tarefa`) — inclusive a tarefa de
  conferência de cadastro do intake, que também é trabalho de controller.

## Squad Comercial/Intake (OPERACIONAL) — Atende Direito → ADVBOX

Objetivo: o lead que o **Atende Direito** já qualificou (WhatsApp/Instagram/site, pipeline
kanban) entra no ADVBOX como cliente + processo, com a pasta na estrutura ZEUS do Drive, sem
redigitação manual.

Comandos:
```
python OPERACIONAL/main.py intake --inspecionar          # JSON cru do lead (calibrar mapa de campos)
python OPERACIONAL/main.py intake --dias 7               # so relatorio, nao grava nada
python OPERACIONAL/main.py intake --dias 7 --integrar --com-drive
```

Fluxo:
1. Busca no Atende Direito os leads do período na etapa qualificada
   (`ATENDE_DIREITO_ETAPA_QUALIFICADO`).
2. `normalizar_lead()` converte o payload no formato que `advbox_integration.cadastrar_cliente()`
   espera (nome, CPF, telefone, endereço, resumo do atendimento).
3. Classifica cada lead em **novo** / **já cadastrado no ADVBOX** (dedup por CPF, depois por nome
   exato) / **pendente** (falta CPF, nome ou contato) e imprime o relatório.
4. Com `--integrar`: para cada lead novo, **pede confirmação individual** e então cadastra
   cliente → processo (`ADVBOX_TIPO_PROCESSO_PADRAO`) → pasta no Drive (`--com-drive`) → tarefa
   de conferência para a Controladoria.
5. Marca o lead como integrado no Atende Direito **apenas se** `ATENDE_DIREITO_ENDPOINT_MARCAR`
   estiver configurado; sem isso, a dedup fica por conta do CPF no ADVBOX.

Regras:
- **A API do Atende Direito não tem documentação pública.** Nenhuma rota é hardcodada: base URL,
  endpoints, nomes de parâmetro e mapa de campos vêm do `.env` (bloco `ATENDE_DIREITO_*`).
  Se um campo vier vazio, rode `--inspecionar` e ajuste `ATENDE_DIREITO_MAPA_CAMPOS`.
- Lead **pendente nunca é cadastrado** — sobe no relatório para tratamento humano.
- Sem `--integrar` o comando é somente leitura.
- Nada é gravado em lote: cada lead pede "s/N" no terminal.

## Squad Dívida Rural (OPERACIONAL) — Produção de peças

As 4 ações centrais do escritório (ver `.claude/agents/maldonado-divida-rural.md` para o
detalhamento jurídico completo):
1. **Prorrogação/alongamento compulsório de crédito rural** (item 2.6.4 MCR + Súmula 298/STJ).
2. **Ação declaratória de descaracterização de mora** (Tema 28/STJ — distinção juros compostos x
   capitalização, Súmulas 539/541).
3. **Descaracterização de mora c/c falha na assistência técnica** (Justiça Federal, réu CEF/BB).
4. **Ação revisional de contrato bancário rural** (estrutura em tópicos I-IV).

A minuta é produzida pelo agente Claude (`.claude/agents/maldonado-divida-rural.md`), calibrado
pelas 3 peças-modelo reais em `DOCS_MODELOS/`. Toda peça sai **pronta para revisão** — nunca
protocolada automaticamente.

### Skills de conteúdo jurídico (instaladas em 11/09/2026)

Quatro skills do escritório entraram em `.claude/skills/`, cobrindo a parte **argumentativa** que
as três anteriores (`timbrado`, `descaracterizacao-mora`, `inicial-anexos`) não cobriam — elas
cuidam de papel, metodologia da mora e documentos; estas trazem tese, precedente e prazo:

| Skill | Cobre | Quando aciona |
|---|---|---|
| `alongamento-divida-rural` | Ação 1 (prorrogação/alongamento) — Núcleo Sigma: MCR 2.6.4, Súmula 298/STJ, frustração de safra, desnecessidade de protocolo prévio, checklist probatório, estratégia recursal | Decisão, peça mandamental/cautelar ou recurso de alongamento |
| `jurisprudencia-rural` | Coletânea Leopoldo Castilho — 315 ementas prontas para citar, por tese, com "Notas de uso" do escritório | "jurisprudência sobre X", "precedente para Y", "ementa pronta" |
| `analise-pontos-controvertidos` | Matriz fato a fato (controvertido / incontroverso / fato novo), ônus da prova, plano de provas, quesitos — arts. 341/357/373 CPC | Réplica, saneamento, leitura cruzada inicial x contestação |
| `prescricao-intercorrente` | Prescrição trienal em execução de CCB/CRP/NCR (art. 921 CPC, LUG art. 70, Lei 10.931/2004), + `scripts/calcular_prescricao.py` | Execução parada, diligências infrutíferas, exceção de pré-executividade |

- `alongamento-divida-rural` delimita o próprio escopo: **não** usar para revisional de juros ou
  capitalização pura (Núcleo Delta), nem para falha de assistência técnica como causa autônoma
  (Núcleo Gama) — nessas, valem o agente de dívida rural e a skill `descaracterizacao-mora`.
- Elas **não substituem** a `timbrado` nem a `inicial-anexos`: a peça continua saindo no timbrado
  e instruída pelos documentos da pasta do cliente. Entram junto, não no lugar.
- `prescricao-intercorrente/scripts/calcular_prescricao.py` usa `python-dateutil` (já em
  `requirements.txt`); o script tenta `pip install` sozinho se faltar.

### Documentos que instruem a inicial — skill `inicial-anexos`

Toda inicial é instruída por documentos que estão na pasta do cliente na ZEUS, e os modelos
de inicial trazem **placeholders literais** onde o recorte do documento entra no corpo da peça
(`INSERIR UMA IMAGEM.` p. 20 · `IMAGEM DO REQUERIMENTO QUE FOI ENVIADO AO BANCO` p. 17 ·
`INSERIR GRÁFICO` — levantados nos modelos reais, ver `BASE_CONHECIMENTO/05 - FORMATACAO/`).

`OPERACIONAL/anexos_inicial.py` fecha esse ciclo: **pasta do cliente → rol da tese → recorte
→ placeholder**. A skill `.claude/skills/inicial-anexos/SKILL.md` é a fonte da verdade
operacional (o que recortar em cada tese, e por quê).

```
python OPERACIONAL/main.py anexos inventario --cliente "NOME"                 # classifica a pasta do cliente
python OPERACIONAL/main.py anexos conferir  --cliente "NOME" --acao-peca mora # o que tem / o que falta
python OPERACIONAL/main.py anexos baixar    --cliente "NOME" --acao-peca mora # -> _trabalho/anexos/[CLIENTE]/
python OPERACIONAL/main.py anexos placeholders inicial.docx                   # marcadores + contexto + palpite
python OPERACIONAL/main.py anexos localizar cedula.pdf --tipo cedula          # em que pagina esta a clausula
python OPERACIONAL/main.py anexos recorte  cedula.pdf --tipo cedula --saida rec.png
python OPERACIONAL/main.py anexos inserir  inicial.docx -m "INSERIR UMA IMAGEM." -i rec.png -l "Imagem 03. Cédula ..., fl. 2 (grifo nosso)"
python OPERACIONAL/main.py anexos pendencia inicial.docx -m "IMAGEM DO REQUERIMENTO"
```

Regras:
- As 4 teses têm rol próprio (`ACOES` no módulo): `alongamento`, `mora`, `mora-assistencia`,
  `revisional`. O módulo **nunca escolhe a tese** — se estiver ambígua, para e pergunta.
- A classificação dos arquivos é **heurística de nome + subpasta** (palpite, não laudo).
  Arquivo que não casou com nada sobe como "não classificado" para conferência humana — é aí
  que costuma estar o documento com nome ruim (`IMG_2043.pdf`).
- **Todo print entra em par** (regra da Dra. Juliana, 10/09/2026): `[[INSERIR PRINT nn]]` para a
  imagem e `[[TEXTO DO PRINT nn]]` para a transcrição literal do que ela mostra. Imagem no PJe não
  é pesquisável nem copiável — sem o texto ao lado, o juiz não leva a cláusula para o dispositivo
  e o argumento morre se o recorte sair ilegível. `visual_law.varrer_marcadores_print()` acusa o
  marcador órfão; lista vazia é o único resultado aceitável.
- **Recorte é prova:** sai com folga ao redor do termo (não decapita a cláusula), nunca é
  editado/realçado, e a legenda cita a folha. Recorte da **ficha gráfica tem que mostrar o
  período de normalidade** — a coluna de inadimplência contradiz o Elo 1 do Tema 28.
- **Documento pessoal não vai recortado no corpo** (RG, CPF, comprovante de residência,
  procuração, IRPF): entra no rol de anexos. Sem ganho argumentativo e com custo de LGPD.
- Documento que não existe na pasta vira **pendência em amarelo** na peça — nunca "conforme
  documento anexo" sem documento (mesmo guard-rail da skill `timbrado`).
- Somente leitura no Drive. Nada é gravado lá por este comando; o arquivamento continua em
  `drive peca` (que pede confirmação). Os arquivos baixados ficam em `_trabalho/` (gitignored,
  são documentos reais de cliente).
- Depende de **PyMuPDF** (`pip install pymupdf`, já em `requirements.txt`) para renderizar PDF.
  PDF digitalizado sem OCR não tem texto pesquisável: nesse caso a página é escolhida na mão.

## Acervo de skills jurídicas — o que cada uma cobre

Além de `timbrado` e `inicial-anexos` (que cuidam do papel e dos documentos), o acervo tem uma
skill por metodologia. **Carregue a skill antes de trabalhar o tema — nunca improvise a
metodologia**, que é o mesmo guard-rail já valendo para `descaracterizacao-mora`.

| Skill | Cobre | Origem |
|---|---|---|
| `descaracterizacao-mora` | Tese 2 e 3 — Tema 28, 2 elos, 20 restrições absolutas | Dr. Marcello Serpa Braz (OAB/MG 188.066) |
| `alongamento-divida-rural` | Tese 1 — prorrogação/MCR 2.6.4/Súmula 298, análise de decisão **e** redação da peça | Núcleo Sigma — Dr. Mailson |
| `jurisprudencia-rural` | Ementa pronta para citar — 315 precedentes indexados por tese | Coletânea Leopoldo Castilho |
| `analise-pontos-controvertidos` | Matriz fato a fato: inicial x contestação, ônus da prova, saneamento (art. 357) | Metodologia do escritório |
| `prescricao-intercorrente` | Prescrição trienal em execução (art. 921 CPC, LUG art. 70) + calculadora de prazo | Metodologia do escritório |
| `jurimetria-estrategica` | Briefing antes de redigir: o que a vara e o tribunal decidiram na tese, o que derruba a tese ali (vira prova), acórdãos favoráveis/contrários e óbices do STJ para prequestionar desde a inicial | Base de julgados do DJEN (17/09/2026) |
| `rogerio-augusto` | **Referência externa** — as 4 teses do Dr. Rogério Augusto com precedente numerado, o padrão de atuação real dele e as frentes onde o escritório tem lacuna | Levantamento público (DJEN/CNJ + perfil), 11/09/2026 |

Incorporadas em 11/09/2026. Notas de uso:

- **As duas últimas não são de dívida rural** — `analise-pontos-controvertidos` e
  `prescricao-intercorrente` valem para qualquer processo com inicial e contestação, ou para
  qualquer execução parada. São as primeiras skills do acervo fora das 4 teses.
- `jurisprudencia-rural` **não deve ser lida inteira**: `references/jurisprudencias.md` tem
  ~3.800 linhas. A própria skill manda usar grep pelo Índice por Tese ou pelo número (`**NNN.**`).
- `alongamento-divida-rural` vem com o **vocabulário de outro escritório** ("Maldonado
  Advogadas", Núcleos Sigma/Delta/Gama). A metodologia vale; a nomenclatura não é a daqui —
  as 4 teses deste repositório estão em `.claude/agents/maldonado-divida-rural.md`. Ao produzir
  peça, quem manda na assinatura e na formatação é a skill `timbrado`.
- `alongamento-divida-rural` manda **não citar item do MCR que não esteja transcrito na skill** —
  o item tem que ser conferido no documento original antes de entrar na peça. Mesmo espírito da
  regra de nunca escrever "conforme documento anexo" sem o documento.
- `prescricao-intercorrente` traz `scripts/calcular_prescricao.py` — a única skill do acervo com
  código. O cálculo é do prazo; a conclusão sobre a inércia continua sendo humana.

- `rogerio-augusto` **não é metodologia de tese** — é dossiê de referência externa. Responde *"o
  que a referência nacional faz e com que lastro"*, e entra **junto** com a skill da tese
  (`descaracterizacao-mora`, `alongamento-divida-rural`), nunca no lugar dela. O banco de teses
  fica em `BASE_CONHECIMENTO/04 - REFERENCIAS EXTERNAS/Rogerio-Augusto-Silva-Advogados.md`,
  **fora do git** (dossiê de terceiro nomeado); só a skill é versionada.
- O que ele traz de **novo** para o escritório não é tese — as 4 batem com as daqui. É **frente
  processual**: o volume dele é reativo (agravo, embargos à execução), e ele tem duas frentes que
  o repositório não estrutura — **recuperação judicial do produtor rural** e **impugnação de
  crédito**.

**Material de congresso do Dr. Rogério Augusto da Silva** (a mesma fonte do Manual de Insights)
está em `BASE_CONHECIMENTO/04 - REFERENCIAS EXTERNAS/Rogerio Augusto Silva/` — 3 PDFs, 480
páginas, sobre prorrogação, defesas executivas e revisional. Ficam fora do git junto com o resto
do `BASE_CONHECIMENTO/`.

Chegaram como **imagem pura** (0 de 480 páginas com texto) e **passaram por OCR em 11/09/2026** —
hoje são pesquisáveis por grep e pelos scripts do repositório (~606 mil caracteres; as 6 páginas
sem texto são folhas em branco). O OCR é do **Vision do macOS em pt-BR**, camada de texto
invisível sobre a imagem original, que não foi recomprimida. **O texto é OCR, não é o original do
editor**: serve para localizar a passagem, mas **citação em peça se confere contra a página** —
mesmo guard-rail de nunca escrever "conforme documento anexo" sem abrir o documento.

## Trava de custas antes do protocolo (OPERACIONAL) — POP-CJ-006 x POP-CJ-PROT-001

Nasceu de um caso real: a declaratória da Sra. Cliente G (**0000021-76.2026.8.22.0001**) foi
protocolada em 22/09/2026 às 10:49 **sem o recolhimento das custas**. As tarefas de custas
nasceram depois do protocolo — RECOLHER CUSTAS às 10:53 e SOLICITAR DOCUMENTAÇÃO ("documentos
para emenda: comprovante de residência e juntada de custas") às 10:57. A peça ainda **anunciava
a guia no rol de documentos** ("... e guia de recolhimento das custas iniciais") sem que a guia
existisse.

```
python OPERACIONAL/main.py custas fila --dias 5              # o que vai a protocolo (roda sozinho as 08:00)
python OPERACIONAL/main.py custas conferir peca.docx --cliente "NOME" --processo 7001234-56.2026.8.22.0001
python OPERACIONAL/main.py custas conferir peca.docx --cliente "NOME" --acao-peca mora --criar-tarefa
python OPERACIONAL/main.py custas conferir peca.docx --apesar-de "prazo fatal hoje - Dra. Juliana autorizou"
python OPERACIONAL/main.py custas auditar --dias 7            # so relatorio
python OPERACIONAL/main.py custas auditar --dias 7 --criar-tarefa
python OPERACIONAL/custas_protocolo.py --autoteste
```

**Três camadas, de propósito — só a do meio depende de alguém rodar.**

| Camada | Comando | Quando | O que enxerga |
|---|---|---|---|
| **Fila** | `custas fila` | **automática**, 08:00 | As tarefas `PEÇA APROVADA PARA PROTOCOLO` e `PROTOCOLO D-3/D-2/D-1` dos próximos dias: o que vai a protocolo sem guia/pagamento registrado. **Não lê a peça** |
| **Peça** | `custas conferir` | a controller roda no arquivo | Leitura completa: gratuidade, marcadores, rol de documentos, valor da causa. **Sai com status 1** quando bloqueia |
| **Auditoria** | `custas auditar` | **automática**, 08:00 | O que já foi protocolado sem custas nos últimos dias — rede de segurança |

**Por que a fila não lê a peça:** conferido em 22/09/2026, as tarefas de protocolo do ADVBOX
**não trazem a peça anexada** (`GET /documents?post_id=` volta vazio nas 66 tarefas PROTOCOLO D-3
abertas). Então a rodada automática confere pela fila (rótulo da tarefa + histórico de custas do
processo) e a leitura do texto fica com o `conferir`, rodado no arquivo.

A pergunta que a trava responde, nesta ordem: **é inicial ou recurso? → inicial: tem tópico de
gratuidade? tem os documentos que o sustentam? senão, guia emitida + comprovante juntado + CS
acionado → recurso: preparo comprovado?**

### Recurso é preparo, não custa inicial — e não tem emenda

Dispositivos conferidos no CPC do vault (`06 - LEGISLACAO/CPC/`), não citados de memória:

- **art. 1.007, caput** — preparo comprovado **no ato da interposição**, sob pena de deserção.
- **art. 1.007, § 4º** — não comprovado, intima-se para recolher **em dobro**; **§ 5º** veda a
  complementação nesse recolhimento. É a diferença que importa: na inicial há 15 dias de emenda
  (art. 321); no recurso, **não há segunda chance**.
- **art. 1.007, § 3º** — porte de remessa e retorno dispensado em autos eletrônicos: no PJe
  cobra-se só o preparo.
- **art. 1.017, § 1º** — o agravo vai acompanhado do comprovante do pagamento (as cópias do
  inciso I são dispensadas em autos eletrônicos, § 5º — o comprovante não).
- **art. 1.023** — embargos de declaração **não se sujeitam a preparo**. Agravo interno e
  contrarrazões também ficam fora (`STATUS NAO SE APLICA`).
- **art. 98, § 1º, I** — a gratuidade compreende taxas e custas. Gratuidade **deferida** dispensa
  o preparo; gratuidade apenas **pedida** no recurso não dispensa por si — a trava manda conferir
  a decisão antes de protocolar.

Regras e armadilhas (não desfazer):
- **A peça anunciar a guia no rol NÃO é prova de recolhimento** — é promessa a conferir
  (`GUIA_ANUNCIADA_NAO_JUNTADA`). Ler aquilo como prova liberaria justamente o protocolo que deu
  errado. O juízo lê o rol, não encontra o anexo e intima para emenda.
- **`[PENDENTE]` / `[[INSERIR ...]]` vivo na minuta bloqueia.** Mesmo guard-rail da skill
  `timbrado`: nunca "conforme documento anexo" sem documento. O modelo da declaratória já sai com
  `[PENDENTE] declaração de hipossuficiência assinada` no tópico de gratuidade — é esse marcador
  que a trava cobra.
- **Gratuidade sem declaração na pasta bloqueia; sem prova de renda, é ressalva.** Art. 99, § 2º:
  havendo nos autos elementos que contrariem a alegação, o juízo indefere — produtor rural com
  área e maquinário cai nessa hipótese com frequência.
- **A natureza da peça sai do verbo, não do nome do recurso.** Só conta "vem ... interpor/opor/
  apresentar o presente X". Sem isso, as contrarrazões do Cliente R viravam agravo (o endereçamento
  é "EXCELENTÍSSIMO RELATOR DO AGRAVO DE INSTRUMENTO 0000029-00...") e a inicial da Sra. Cliente G
  virava recurso especial (citava o REsp 1.061.530/RS do Tema 28). Nome citado **sem** o verbo vira
  aviso, nunca conclusão.
- **Rótulo da fila com fronteira de palavra:** `\bacao\b`. Sem ela, "Protocolar manifestação.
  (document**ação** pendente)" entrava como inicial — apareceu na fila real de 22/09/2026.
- **Na auditoria do que já foi protocolado, o filtro é o número CNJ:** origem `0000` é processo
  originário do tribunal e processo de ano anterior cadastrado agora é cadastro tardio, não
  distribuição nova. Sem esse filtro a auditoria de 10 dias trazia 9 falsos — e alarme falso é o
  que faz a controller parar de ler.
- **O valor da causa sai de "dá-se à causa"**, não de "valor de R$ ..." solto: na peça da Cliente G o
  genérico pegava R$ 787.500,00 (o contrato) contra a causa de R$ 1.000,00.
- **O processo que vem dentro da tarefa (`/posts`) não traz `responsible_id`** — só id, número
  e cliente. Sem ele o `roteamento_controller` cai no fallback e manda **tudo para a mesma
  controller** (primeira rodada da fila: 37 tarefas para a Manuelle). A fila carrega a carteira
  inteira uma vez (`listar_processos()`, 3 GET) e resolve o responsável pelo id.
- **Peça intermediária fica fora da trava.** Manifestação, réplica, alegações finais: não pagam
  custa de distribuição nem preparo. Elas caíam no ramo das custas e saíam como "SEM REGISTRO —
  custas iniciais" — 14 dos 32 alarmes da primeira rodada eram isso.
- **A fila custa 1 GET de `/history` por item de inicial/recurso**, e o teto do ADVBOX é 30
  GET/min: a passada das 08:00 leva alguns minutos e imprime "Rate limit atingido. Aguardando".
  Por isso a fila só consulta o histórico do que é inicial ou recurso com preparo — manifestação,
  contrarrazões e ED não geram chamada.
- **Pasta errada não bloqueia.** `google_integration.pasta_do_cliente()` cai numa busca global
  quando o cliente não está sob a letra em `03. CLIENTES`, e devolve a pasta de **PEÇAS
  AUTOMAÇÃO** (`FULANO - SEM PROCESSO`), que não tem documento nenhum — foi o que aconteceu com a
  Sra. Cliente G. `pasta_confere()` detecta isso e o que depende da pasta vira **ressalva**; o que
  vem do ADVBOX continua bloqueando. Trava que bloqueia por engano é desligada na primeira semana.
- **`/history` devolve ~20 itens e não pagina**: "não encontrei" nunca vira "não existe", vira
  pendência a conferir. E o que está no `/history` e não está no `/posts` foi concluído — é
  inferência, e sai rotulada como tal.
- **Há saída de exceção, com nome e motivo.** `--apesar-de "motivo"` libera e registra por escrito
  na tarefa: prazo fatal no mesmo dia acontece. O que a trava impede é o protocolo sem custas
  **silencioso**.
- Somente leitura. Tarefa só com `--criar-tarefa` e "s/N"; quem lança é a controller do advogado
  responsável (`roteamento_controller`), e o CS (Anna Lydia/Karla) recebe o CONTATO COM CLIENTE.
- `drive peca` **avisa** quando a peça arquivada tem pendência de custas — avisa, não bloqueia:
  quem bloqueia é o `custas conferir`, rodado antes do protocolo.

## Base de apontamentos da Gerência Jurídica (OPERACIONAL) — causa raiz das correções

Objetivo: parar de corrigir a mesma coisa 200 vezes por mês. A Dra. Juliana recebe as peças na
tag **CONFERIR/REVISAR PETIÇÃO** e devolve com os apontamentos; este comando levanta essas
devolutivas, classifica e vira checklist.

```
python OPERACIONAL/main.py apontamentos --de 2026-06-01 --ate 2026-08-31 --csv base.csv
python OPERACIONAL/main.py apontamentos --dias 30          # so relatorio
```

Entregas do levantamento de jun–ago/2026 em `docs/base_apontamentos_gj/`:
planilha por apontamento, planilha das devolutivas integrais, `RELATORIO_PADROES.md` e
`CHECKLIST_AUTORREVISAO.md`.

O material de treinamento da equipe é o **Manual de Técnica e Estratégia**
(`docs/manual_insights/MANUAL_INSIGHTS_AUTORREVISAO.md`), que junta os insights dos
congressos/mentorias (Dr. Rogério Augusto, Dr. Paulo Abatti, saneamento art. 357) com o que a
revisão da GJ mais refina, organizados **por fase do processo**. É ele que o agente de dívida
rural consulta.

O complemento de **condução do processo** é o **Processo Civil Estratégico do Produtor Rural**
(`docs/manual_insights/MANUAL_PROCESSO_CIVIL_ESTRATEGICO.md`, 12/09/2026): 29 insights tirados do
CPC vigente lido por fase, cada um mirando um motivo real de indeferimento do levantamento da GJ
(justificação prévia como condição do indeferimento, produção antecipada de prova, julgamento
antecipado **parcial** + saneamento compartilhado, penhora sobre o bem da garantia pelo art. 835,
§ 3º), cruzados com a Trilogia do Agro do Dr. Rogério Augusto. **O §8 lista decisões da GJ que
mexem em regra escrita das skills** (Restrição 18 e seção 13ter da `descaracterizacao-mora`,
indeferimento tácito × ED primeiro): nenhuma foi aplicada nas skills, que seguem valendo até a
deliberação. Mesmo tom preventivo do Manual.

A **Parte II** (`docs/manual_insights/PROCESSO_CIVIL_POR_PRODUTO.md`, 13/09/2026) veio da leitura
**integral** do CPC (1º a 1.072), em cinco blocos, com todo trecho citado conferido por programa contra
o vault. Organizada por produto, com roteiro cronológico da defesa do patrimônio e prazos novos para a
Controladoria. Dois achados que mexem além da peça:
- **Competência do Banco do Brasil.** Este arquivo, o agente e a nota da tese 3 dizem "réu CEF/BB →
  Justiça Federal". O art. 45 alcança empresa pública (CEF), não sociedade de economia mista (BB), e os
  22 processos do escritório contra o BB correm na Justiça Estadual. **Decisão da GJ pendente** (Parte II,
  §12, item 8); a regra não foi reescrita, só sinalizada no agente.
- **A leitura achou defeito no próprio vault:** texto revogado que escapava do filtro de riscado (o
  Planalto desenha o risco de uma linha em vários segmentos). Corrigido em `legislacao_vault.py`
  (cobertura somada dos segmentos + anotação de revogação órfã). Afetava os arts. 1.029, 1.037, 1.041
  (§ 2º tinha sumido) e 1.043, entre outros.

**Tom do manual — decisão da Dra. Juliana (10/09/2026): preventivo, nunca corretivo.** O objetivo
é a peça sair certa na primeira vez, sem retrabalho — não apontar culpa. Por isso: "refinamentos"
e "onde costuma escapar", não "erros"; nenhuma contagem por advogado; a citação da devolutiva
entra pelo trecho **propositivo** (o que fazer), não pela parte diagnóstica. O indicador que o
manual persegue é positivo: a proporção de peças aprovadas direto (148 aprovações para 125
devolutivas com refinamento, jun–ago/2026). Manter esse tom em qualquer atualização.

PDF para circular no escritório: `python OPERACIONAL/md_para_pdf.py docs/**/*.md`
(motor: Chrome headless; os `.md` são a fonte versionada, os `.pdf` não).

Regras e armadilhas (não desfazer):
- **`GET /posts` não devolve o autor da tarefa** — só os convidados. Dentro da tag
  CONFERIR/REVISAR PETIÇÃO o texto é sempre do **advogado submetendo**, nunca da GJ (0 de 238
  conferidas). A autoria só existe em `GET /history/{lawsuit_id}` (campo `author`).
- **`/history` devolve ~20 itens por processo e NÃO pagina** (`limit`, `offset`, `page`, `skip`,
  `start`, `per_page`, `date_start` — todos ignorados, conferido em 10/09/2026). O relatório
  imprime a cobertura por mês porque o número é **piso, não total**.
- A devolutiva sai em 6 tags diferentes (AGENDAMENTO, COMENTÁRIO, PEÇA ENVIADA PARA AJUSTES,
  ANÁLISE - NÍVEL 01, PRESTAR ESCLARECIMENTOS, PEÇA APROVADA PARA PROTOCOLO). Olhar só
  "PEÇA ENVIADA PARA AJUSTES" mostra **16%** do trabalho da GJ.
- A classificação é **heurística de palavra-chave** — palpite, não laudo. O que não casa sobe
  como `revisar manualmente` (≈20%): é aí que está o apontamento com redação nova.
- Somente leitura. Nenhum POST, nenhuma tarefa criada.

## KPI de êxito (OPERACIONAL) — taxa de êxito a partir das intimações

Objetivo: parar de garimpar as decisões do mês a mão. Das 112 intimações de 01–10/09/2026, só
**21 eram decisão classificável** — as outras 91 são despacho, expediente ou questão acessória.

```
python OPERACIONAL/main.py kpi --dias 1                       # rodada do dia (so relatorio em tela)
python OPERACIONAL/main.py kpi --de 2026-09-01 --ate 2026-09-30 --csv kpi_set.csv
python OPERACIONAL/main.py kpi --de 2026-09-01 --ate 2026-09-30 --pdf \
       --ressalvas docs/kpi_exito/RESSALVAS_2026-09.md        # fechamento da competencia
```

`--pdf` gera **quatro documentos** (`.md` versionado + `.pdf` para circular), via
`OPERACIONAL/kpi_relatorio.py` e o mesmo motor Chrome do `md_para_pdf.py`:

| Documento | Para quem | O que traz |
|---|---|---|
| `RELATORIO_KPI_*` | Direção / GJ | Funil do período, quadro por carteira e por advogado, gráfico de barras com a meta, composição por KPI, recálculo só com confiança alta |
| `DECISOES_KPI_*` | Quem quer ver as decisões | **O diário do período**: dia a dia, cada decisão com o dispositivo e o **link da publicação no DJEN**. Dia sem decisão aparece como tal |
| `ANEXO_KPI_*` | Auditoria | Processo a processo, com o **dispositivo lido** em cada linha, as decisões a conferir e os atos fora de escopo agrupados por motivo |
| `FICHAS_KPI_*` | Conversa individual | Uma ficha por advogado, com composição por KPI e aviso de base insuficiente |

### Planilha de acompanhamento da competência — `kpi --planilha` (15/09/2026)

Pedido da Dra. Juliana: **uma única planilha por mês, aberta por semana, no formato que a GJ já usava**
(`Acompanhamento_Casos_Maldonado_<Mês>`, com diagnóstico de cada decisão). `OPERACIONAL/kpi_acompanhamento.py`
grava `Acompanhamento_Casos_Maldonado_Setembro_2026` na pasta de `config/equipe.py` → `KPI_PLANILHA_PASTA_ID`:

- **Uma aba por semana útil** (`Semana 01.09-04.09`), uma linha por decisão, com as colunas da GJ (Processo,
  Cliente, Advogado Responsável, Categoria, Parte Adversa/Órgão, Situação e Fundamentos, Diagnóstico, Despacho,
  Estratégia, Probabilidade) **mais** Carteira/KPI/Classificação/Peso/Contribuição. Linha só de rastreabilidade
  (já computada no mês anterior, pendente da GJ) sai em rosa, como no modelo.
- **`Taxa Êxito Rural <Mês>` e `Carteira Diversa <Mês>`** no layout da aba de agosto: blocos por KPI, subtotais,
  não contabilizados, taxa geral, **taxa por semana**, taxa por advogado e notas. Pontos de bonificação ficam
  "a lançar (GJ)": a automação não pontua.
- **O diagnóstico não sai de regex**: é escrito lendo o ato inteiro e fica em `_trabalho/kpi_diagnosticos_AAAA-MM.json`
  (dado de cliente, gitignored — a VPS não tem esse arquivo). Decisão nova sem diagnóstico sai "A elaborar".
  Os números (KPI, resultado, peso, carteira) vêm da apuração + `DECISOES_GJ`, nunca do arquivo de diagnóstico.
- **Atribuição por advogado** = quem conduziu o ato (`advogado_kpi`), não o responsável atual do ADVBOX; vazio
  sobe como "A confirmar (X)". O `/history` do ADVBOX só traz ~20 eventos: é indício, não prova completa.
- Decisão **já computada na planilha do mês anterior** não pontua de novo, mesmo republicada no DJEN.
- **Categoria PMP (Start/Plus/Gold/Platinum)** vem do campo **Pasta** do processo no ADVBOX (`folder` na
  API), em regra no **PROC. MÃE** do cliente — agravo e incidente costumam ter a Pasta vazia, então o
  gerador olha os outros processos do mesmo cliente (cache em `_trabalho/kpi_pmp_cache.json`). Sem Pasta, a
  fonte é o contrato de honorários (orientação da GJ, 15/09/2026). `/customers` e `/lawsuits/{id}` não
  trazem campo personalizado; não procurar lá.
- Cada rodada reescreve as abas; a rodada diária já passa `--planilha`. Falha no Drive não derruba a apuração.
- Refazer a partir de um CSV: `python OPERACIONAL/kpi_acompanhamento.py kpi.csv 2026-09-01 2026-09-15 <spreadsheet_id>`.
  (`kpi_planilha.py`, o formato anterior com fórmulas, fica só como biblioteca de leitura de CSV.)

`--ressalvas ARQUIVO.md` anexa ao executivo as ressalvas da competência (o que é decisão da GJ,
não da automação). São elas que impedem o relatório de virar avaliação de desempenho.

### Dia e semana

A GJ acompanha por **dia** e por **semana** ("Semana 01"). A semana é de **segunda a domingo**,
numerada a partir da que contém o primeiro dia da competência — **não** é a semana ISO do ano,
que daria "Semana 36" e não diz nada a quem fecha setembro. A primeira semana pode começar no
meio, porque a competência começa no dia 1º e não numa segunda.

`kpi_exito.numerar_semanas()` é a fonte da numeração (executivo, diário e CSV usam a mesma), e
`apurar()` devolve `por_dia` e `por_semana`, cada um aberto por carteira. No diário, a semana do
dia vem do **calendário**, não das linhas: sábado e domingo não têm publicação e sairiam sem
semana no índice, embora pertençam à semana como qualquer dia.

Em 01–10/09/2026 a leitura semanal mostra o que a média esconde: **Semana 01 = 9,7%** (0,90/9,30)
e **Semana 02 = 71,4%** (2,00/2,80) na carteira rural.

### Verificação diária (agendada)

```
bash deploy/kpi_diario.sh                       # roda a competência corrente (dia 1º até hoje)
cp deploy/com.maldonado.kpi.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.maldonado.kpi.plist   # seg-sex, 08:00
tail -40 _trabalho/logs/kpi_diario.log          # conferir a última rodada
```

- Roda a **competência inteira**, não só o dia: a taxa do mês só faz sentido acumulada, e o
  diário já separa por dia e por semana.
- **08:00, de segunda a sexta**, junto com a rotina de intimações da Controladoria (POP-CJ-003).
  Nesse horário a rodada reflete até as publicações do **dia anterior** — as de hoje entram na
  rodada de amanhã.
- Pega `docs/kpi_exito/RESSALVAS_AAAA-MM.md` se existir; sem o arquivo, roda sem ele em vez de
  falhar (as ressalvas da competência são escritas a mão pela GJ).
- Falha de rodada fica no log e **não** derruba o agendamento — a API do DJEN dá falso-vazio.
- **Rodada perdida não é reposta:** com `StartCalendarInterval` o launchd não replica a execução
  se o Mac estiver desligado às 08:00. Basta rodar `bash deploy/kpi_diario.sh` na mão — a
  apuração é da competência inteira e se recompõe sozinha.
- O `.plist` traz o caminho absoluto do Mac da Dra. Juliana: em outra máquina, ajustar os dois
  caminhos antes de carregar.

**Fonte da régua: o "7 - MANUAL DO ÊXITO JURÍDICO KPI"** (v1.0, mai/2026, Google Doc
`<ID_DO_DOC_NO_DRIVE>` no Drive) — CEO Dr. Renan + GJ Dra. Juliana. É
ele que define os 4 KPIs, os pesos e o que fica de fora. O relatório *Taxa de Êxito por Advogado
— Jun-Jul-Ago 2026* é **aplicação** da régua a uma competência, não a régua: onde divergirem,
vale o manual (foi o caso da meta — **20%** no manual, 30% no relatório de jun-jul).

`Taxa = Σ(peso × favorável) ÷ Σ(peso)`, favorável 1,0 / 0,5 / 0,0 para Êxito / Parcial / Inêxito.
Pesos: KPI 1 (mérito) 1,0 · KPI 2 (tutela 1º grau) 0,4 · KPI 3 (tutela recursal) 0,5 ·
KPI 4 (êxito negocial) 0,5 a 2,0. Só a **carteira rural** compõe o indicador da Presidência.

**A taxa é sempre ponderada individualmente por carteira** (Dra. Juliana, 14/09/2026): rural de
um lado, diversa do outro, cada uma com o total e a quebra por KPI. **Não existe "taxa do
escritório"** somando as duas — nem no total, nem por KPI (`apurar()` devolve `por_kpi[carteira][kpi]`).
Contagem de decisões pode somar; taxa não.

Entregas de 01–10/09/2026 em `docs/kpi_exito/`: os três PDFs + o CSV linha a linha + as ressalvas
da competência. Resultado: carteira rural **3,65/13,60 = 26,8%**, diversa 1,50/3,50 = 42,9%.

### Procedência se mede pela tese, não pelo rótulo (regra da Dra. Juliana, 10/09/2026)

Em sentença **"parcialmente procedente"**, o que decide entre Êxito e Parcial é se a **tese
central** foi acolhida — não o rótulo do dispositivo. Sentença que declara descaracterizada a
mora, reconhece o direito ao alongamento ou anula a cláusula discutida entregou ao cliente o que
ele veio buscar, ainda que o juízo rejeite um pedido acessório e chame tudo de "parcialmente
procedente". `kpi_exito.avaliar_procedencia()` implementa isso (`_TESES_CENTRAIS`), e reforça com
os sinais que o próprio juízo dá — art. 86, § único, "decaimento mínimo", "procedência
substancial".

Quando a sentença fixa **sucumbência recíproca** e mesmo assim acolhe a tese, a linha entra como
Êxito **marcada `confirmar_resultado`**: é o único ponto em que o texto e a régua divergem, e a
GJ decide. Sai destacada no relatório e no CSV.

**Nem toda liminar deferida diz "tutela" no dispositivo.** A decisão que suspendeu a execução da
Sra. Cliente H (0000025-78.2025.8.22.0024) abre com *"defiro o pedido formulado pela parte autora"* —
por isso o padrão genérico existe, sempre com o guarda-negativo `_DEFERIMENTO_PROCESSUAL`
(dilação de prazo, gratuidade, juntada, produção de prova...). Sem esse guarda, o
*"defiro a dilação de prazo"* da **mesma cliente na mesma semana** viraria êxito de KPI 2.

Regras e armadilhas (não desfazer):
- **Somente leitura.** Nenhum POST, nenhuma tarefa, nada gravado no Drive.
- **Objeto acessório não entra em KPI nenhum** — gratuidade da justiça, custas, honorários
  sucumbenciais. O manual mede mérito, tutela de 1º grau, tutela recursal e êxito negocial;
  **a forma do ato não salva o objeto** (agravo cujo único objeto é a revogação da gratuidade
  fica fora mesmo tendo efeito suspensivo deferido — 0000026-04.2026.8.22.0000). O teste roda só
  no cabeçalho, no "trata-se de" e na ementa (`objeto_acessorio()`): varrer o texto inteiro
  excluiu por engano duas sentenças de mérito que citavam gratuidade na fundamentação.
- **Objeto misto não é objeto acessório** (14/09/2026): se a região do objeto lista o pedido
  acessório **ao lado** de um pedido principal (`_OBJETO_PRINCIPAL`: efeito suspensivo aos
  embargos, tutela de urgência, suspensão da execução), o ato fica no KPI. Os embargos do Cliente I
  (0000030-00) saíam como "custas" por pedirem parcelamento de custas junto do efeito suspensivo
  indeferido. Regressão: 0000026-04 e 0000031-00 continuam fora.
- **Decisões da GJ por competência** (`docs/kpi_exito/DECISOES_GJ_AAAA-MM.json`): o `kpi` aplica o
  arquivo **depois** da classificação automática (`aplicar_decisoes_gj()`), senão cada rodada
  diária desfaz o fechamento da GJ. `carteira` vale para o processo; `fora_do_kpi`/`incluir` só
  para a publicação da `data`. Toda linha ajustada sai na coluna `decisao_gj` do CSV, e decisão que
  não casar com publicação do período é impressa como `NAO APLICADA`. As semanas são renumeradas
  **depois** de aplicar (16/09/2026): o lançamento manual de ato fora do DJEN (Cliente M,
  0000032-00) entrava no total sem semana, e a quebra semanal não somava o total.
- **Decisão parcialmente procedente nunca é classificada sozinha** (item 1.4 do manual): exige
  análise da Controladoria + GJ. A automação entrega a proposta fundamentada com
  `confirmar_resultado=True`, nunca a classificação final. **Isso vale só para o KPI 1.**
- **KPI 2 e KPI 3 são binários** (itens 2.3 e 3.3): só *deferida → Êxito* e *indeferida →
  Inêxito*. **Não existe Parcial em tutela** — tutela deferida com alcance menor que o pedido
  continua sendo tutela deferida, e vale o peso cheio (regra da GJ, 10/09/2026, sobre
  0000027-76.2026.8.08.0000, que saía como 0,25 quando vale 0,50).
- **Indeferimento "por ora" CONTA no KPI** (Dra. Juliana, 29/09/2026 — reverte a regra de
  17/09/2026): tutela indeferida "por ora", aguardando contestação, garantia do juízo ou elementos
  novos, entra como **inêxito** de KPI 2 ou 3 conforme o grau. "Inclua tudo, inclusive os
  indeferimentos de tutela por ora." O bloco que excluía está **comentado** em `kpi_exito.py`, com
  instrução de como voltar atrás; `indeferimento_provisorio()` continua marcando
  `monitorar_renovacao`, agora só como lembrete de renovar o pedido depois da contestação, não mais
  como motivo de exclusão. Em setembro/2026 a reversão trouxe 5 decisões de volta (Cliente N ×2, Cliente O,
  Cliente P, Cliente Q) e **baixou** a carteira rural de 26,8% para 23,7%.
- **Sentença terminativa NÃO pontua** (Dra. Juliana, 28/09/2026): extinção sem resolução de mérito
  (art. 485) não é inêxito de KPI 1 — só a improcedência (art. 487, I). O caso vai para
  monitoramento e quem entra é a decisão do recurso (caso Cliente L, 0000033-00, extinto
  pelo art. 485, VI por eficácia preclusiva da coisa julgada).
- **Processo conduzido pelo um advogado externo não entra no KPI** (Dra. Juliana,
  29/09/2026): o KPI mede a carteira dos advogados do mapa. Mesma lógica que deixa fora do mapa quem não é advogado ativo
  do mapa de controllers. Vale também para ato em que a parte é o próprio Dr. Renan (RHC 247328/RO).
- **Dispositivo sem "ante o exposto"** (17/09/2026): seção intitulada só "DISPOSITIVO" é marcador
  (`_TITULO_DISPOSITIVO`, 0000034-00), e em ato de **1º grau** o comando de tutela na 1ª pessoa no
  meio do texto é lido como reserva (`_TUTELA_OPERATIVA_1G`, 0000035-00) — antes o fecho "designe
  audiência / cumpra-se" fazia a decisão parecer despacho. Não vale para 2º grau, onde o relator
  transcreve a decisão agravada na 1ª pessoa.
- **Acórdão não é mérito só por ser colegiado** (29/09/2026, regras da GJ de 15, 22 e 23/09 levadas
  ao código): em `classificar_kpi()`, **agravo interno que nega provimento** (só mantém a decisão
  anterior) fica fora; **agravo de instrumento cujo objeto é tutela** vai para o KPI 3; acórdão sobre
  **incidente da execução** (penhora, Sisbajud, impugnação ao cumprimento, exceção) fica no KPI 1 com
  `confirmar_resultado` — a GJ decide. Antes, 0000036-00 (Cliente J) e 0000037-00 (Cliente K) entravam
  como mérito inêxito e derrubavam a taxa rural de set/2026 de 30,7% para 26,8%.
- **Os pesos de tutela são diferentes:** KPI 2 (1º grau) = **0,4**, KPI 3 (recursal) = **0,5**.
  O que decide é o grau em que o ato foi proferido, não o objeto.
- O polo do escritório vem do campo **`destinatarios[].polo`** ("A"/"P") do DJEN, não do texto —
  é o único lugar em que a informação vem estruturada, e sem ela "recurso não provido" não tem
  sinal (é inêxito se o recurso é nosso, êxito se é do banco). O texto é só reserva.
- O banco entra como `customer` do processo no ADVBOX ao lado do cliente: `clientes_do_escritorio()`
  separa os dois. Sem isso o polo sai invertido e o êxito vira inêxito.
- O resultado é lido **só do dispositivo**, nunca do texto inteiro: o corpo da decisão transcreve
  a decisão recorrida e a ementa da jurisprudência citada, ambas cheias de "recurso provido".
  Sem marcador (`ante o exposto`, `decisão:`, ementa), lê-se só o **fecho** do ato.
- Em ato de 2º grau vale o **último** enunciado de caráter recursal (o relator transcreve antes
  de decidir); em 1º grau, o **primeiro** (o dispositivo abre com o verbo operativo).
- `group` do ADVBOX **não é taxonomia de tese** — traz "AÇÃO CÍVEL" e "AGRAVO DE INSTRUMENTO",
  que são classe processual. A carteira rural sai do grupo só quando ele nomeia a tese; senão,
  do texto. "Diversa" por ausência de marca sobe como **a confirmar**, não como conclusão.
- **Embargos de declaração NÃO contam** — regra da Dra. Juliana, 10/09/2026, nem em 1º grau nem
  em acórdão. O item 1.2 do manual cita "acórdão em apelação, embargos, RESP, RE", e "embargos"
  ali **não** alcança os de declaração: o mérito já foi pontuado na decisão embargada, e contá-lo
  de novo pontuaria o mesmo ato duas vezes. Ficam fora e aparecem no Anexo com o motivo.
- **Trânsito em julgado (peso 2,0) e acordo (KPI 4) continuam lançamento manual da GJ** — não
  passam pelo DJEN, e a diferença entre 0,5 e 2,0 no acordo muda o resultado do mês inteiro.
- A captura cobre as **2 OABs** de `OABS_MONITORADAS`, não as 12 da equipe.

## Melhorias trazidas do repositório irmão (11/09/2026)

`pabadvogados-hub/alves-carneiro-advogados` é **outro escritório** no mesmo produto white-label
(mesmo fornecedor, bootstrap de 03/09/2026). O que veio de lá foi **copiado e adaptado**, nunca
sobreposto — e a maior parte do repositório dele **não** se aplica aqui:

| Trazido | O que mudou aqui |
|---|---|
| `.gitattributes` (**já existia** — foi ampliado, as 2 regras originais seguem intactas e com o mesmo efeito, conferido com `git check-attr`) | Normalização de fim de linha. O escritório é híbrido (há `instalar_windows.bat` e `instalar_mac.sh`) e a VPS é Linux: `.sh` salvo no Windows chega com CRLF e morre em `bad interpreter: /bin/bash^M`. **Adaptado:** `*.csv` fica em CRLF, porque o módulo `csv` do Python grava `\r\n` e quem abre é o Excel da equipe |
| OCR e libs no provisionamento | `tesseract-ocr` + `tesseract-ocr-por` (no Mac o OCR saiu do Vision da Apple, que não existe no Linux; sem o `-por` o tesseract lê em inglês) e `libgl1`/`libglib2.0-0`, que o PyMuPDF pede para renderizar PDF |
| `ufw` | Instalado sempre, **ligado só com `MALDONADO_UFW=1`** — `ufw enable` sem liberar o SSH antes tranca você para fora da VPS |
| `pip install --upgrade pip wheel` | Sem `wheel`, dependência sem wheel pronta tenta compilar na VPS |
| `OPERACIONAL/acentuacao.py` | Rede de segurança de acentuação para texto de LLM — ver abaixo |

**Armadilha do `.gitattributes` (não reordenar):** vale a **última** regra que casa com o
arquivo. Por isso `* text=auto eol=lf` está **antes** das específicas — invertido, ele anula o
`*.bat ... eol=crlf` e o `instalar_windows.bat` passa a ser gravado com LF, quebrando no
`cmd.exe`. Foi exatamente o que aconteceu na primeira versão desta mudança.

**Não trazido, de propósito:** `FINANCEIRO/` (Asaas) e ZapSign estão **fora do escopo deste
cliente** (`docs/_WHITE_LABEL_SPEC.md` §5); o `INTAKE/` deles é de trabalhista/previdenciário e
aqui o intake é o do Atende Direito; e as `.claude/rules/` e skills de lá carregam o padrão
**do outro escritório** (Montserrat 11 pt, recuo 7 cm, POP trabalhista) — copiá-las
sobrescreveria a skill `timbrado` daqui (Arial Narrow 12, faixa 2026, margens da Dra. Juliana).

### `OPERACIONAL/acentuacao.py` — o corretor, com dois consertos

```
python OPERACIONAL/acentuacao.py minuta.txt --listar    # o que ele mudaria (confira antes)
python OPERACIONAL/acentuacao.py minuta.txt             # corrige e imprime
python OPERACIONAL/acentuacao.py --autoteste            # 16 casos
```

É proposta, não aplicação automática: `--listar` primeiro. Três coisas que a versão de origem
não fazia e **não devem ser desfeitas**:

- **Palavra ambígua fica fora.** O mapa de lá trazia `esta → está` e `pais → país` sem contexto
  nenhum (o comentário dizia "ver fallback"; não havia fallback). Em peça, "esta ação" viraria
  "está ação". `AMBIGUAS` lista as 13 recusadas **com o motivo** — inclusive **`ha`, que num
  escritório de dívida rural é hectare** ("120 ha" em cédula, matrícula e laudo).
- **Código não é prosa.** Na primeira rodada real sobre o repositório, o corretor propôs
  `maldonado-divida-rural` → "dívida" (identificador de agente) e `main.py drive peca` → "peça"
  (comando do CLI) — os dois quebram o sistema. `_TRECHOS_PROTEGIDOS` mascara bloco de código,
  código inline, URL, caminho, `snake_case`, `kebab-com-3-partes` e nome de arquivo com extensão.
  Na mesma rodada ele achou "exito negocial" no relatório de KPI, que é **erro de verdade** — por
  isso a saída não é desligar o corretor nesses arquivos, é separar prosa de código.
- **Mapeamento identidade não entra.** O original tinha ~15 entradas `'processo': 'processo'`,
  que só engordavam a regex. `_conferir_mapa()` recusa no import.

## Onde as rotinas rodam — VPS Hostinger (`deploy/vps/`)

Resposta ao item **G1b** do `docs/LEVANTAMENTO_FLUXO_INTIMACOES.md`: o escritório contratou uma
**VPS na Hostinger**. As rotinas agendadas saem do Mac da Dra. Juliana e passam a rodar lá; o Mac
continua sendo a **fonte da verdade do código** e o lugar de trabalhar peça.

| Rotina | Horário | Unit systemd | Grava? |
|---|---|---|---|
| **Rodada da Controladoria** — intimações (POP-CJ-003) + despachos (POP-CJ-DESP-001) + custas (POP-CJ-006) | seg–sex 08:00 | `maldonado-intimacoes.timer` → `deploy/controladoria_diaria.sh` | Intimações em **simulação**; despachos gravam a planilha; custas só relatório |
| KPI de êxito (competência inteira) | seg–sex 08:20 | `maldonado-kpi.timer` → `deploy/kpi_diario.sh` | Nunca (somente leitura) |
| Saúde (`saude.sh`) | sob demanda | — | Nunca |

**Corrigido em 30/09/2026:** o unit apontava para `deploy/vps/rotina_intimacoes.sh` (escrito em
11/09, só intimações). A rodada do escritório passou a ser `deploy/controladoria_diaria.sh` em
21/09, com despachos e custas — subir sem esse conserto faria a VPS rodar versão atrasada e
deixar as duas planilhas de fora. O `rotina_intimacoes.sh` **não foi apagado**: fica como caminho
de emergência para rodar só as intimações. O `saude.sh` confere o log do script certo.

**Plugin da Hostinger instalado em 30/09/2026** (`hostinger@claude-plugins-official`, v1.2.0,
escopo de usuário) mais os servidores MCP por serviço (`hostinger-vps`, `hostinger-dns`, ...).
Com eles a VPS pode ser **criada daqui**, sem passar pelo hPanel, e o IP entra no `.env` sem
digitação. Servidor MCP adicionado no meio de uma sessão **não** aparece nela: reiniciar o Claude
Code para as ferramentas carregarem.

```
bash deploy/vps/subir.sh --conferir     # no Mac: confere o que falta. NAO precisa da VPS existir
bash deploy/vps/subir.sh                # no Mac: primeira instalacao (um comando, idempotente)
bash deploy/vps/enviar.sh               # no Mac: atualizacao do dia a dia (--simular mostra antes)
bash deploy/vps/saude.sh                # na VPS: "esta de pe e rodou hoje?" (status 1 se houver [X])
```

`subir.sh` e' o caminho da primeira vez: confere o Mac -> prova a conexao -> provisiona ->
envia -> copia credenciais (pergunta antes) -> instala os timers -> roda o `saude.sh`. E'
idempotente; parou no meio, roda de novo. Depois disso o comando do dia a dia e' `enviar.sh`.
`--conferir` roda **antes de a VPS existir** e diz o que falta no Mac (inclusive imprime a chave
publica para colar no painel da Hostinger).

Passo a passo completo em `deploy/vps/README.md`. Regras e armadilhas:

- **Dois usuarios, de proposito:** `maldonado` (servico, sem sudo) roda a automacao; `root`
  (`VPS_USUARIO_ADMIN`) so provisiona e instala unit. Quem le processo de cliente nao precisa
  de privilegio.
- **Fuso `America/Porto_Velho` (UTC-4)** — VPS nasce em UTC, e sem isso o timer das "08:00"
  dispara às 04:00 locais, antes de o DJEN publicar o dia. `provisionar.sh` resolve; `saude.sh`
  reconfere a cada checagem.
- **A rotina de intimações roda em SIMULAÇÃO por padrão.** Quem libera a gravação é
  `VPS_ROTINA_GRAVAR=1` no `.env` **da VPS** — não é flag de linha de comando de propósito:
  a decisão fica escrita no servidor, com data. **Protocolo continua sendo nunca.**
- **Credencial não trafega em deploy.** `enviar.sh` exclui `config/.env`, `credentials.json`,
  `oauth_credentials.json` e `token*.json`; são copiados uma vez, à mão, com `chmod 600`. Assim
  um envio errado nunca sobrescreve o token bom da VPS.
- **`enviar.sh` é `rsync --delete`** — o que sumir do Mac some da VPS. `_trabalho/` e
  `BASE_CONHECIMENTO/` ficam fora (documento real de cliente; a VPS tem o `_trabalho/` dela).
- **`token.json` tem que nascer no Mac.** O login do Google abre navegador (`run_local_server`)
  e a VPS não tem tela. O token copiado se renova sozinho **só se** o app OAuth estiver
  *publicado* no Google Cloud — em "Testing" o Google invalida o refresh token a cada 7 dias.
  Sem Drive a rotina roda igual, só não arquiva o relatório no Zeus.
- **`Persistent=true` nos timers** repõe a rodada perdida — é justamente o que o `launchd` do
  Mac não fazia. Com a VPS estável, descarregar o `com.maldonado.kpi.plist` do Mac para o KPI
  não ser apurado duas vezes.
- **`ProtectSystem=strict`:** os units só escrevem em `_trabalho/` e `docs/`. Comando novo que
  precise de outro caminho tem que somá-lo em `ReadWritePaths`, senão falha com read-only.
- **Os scripts do lado do Mac tem que rodar em bash 3.2** (e' o que o macOS traz). Nada de
  `${VAR,,}` nem outro bashismo de 4+; e apostrofo dentro de `${VAR:+...}` quebra o parser do
  3.2 (`e' enviado` virou erro de sintaxe uma vez). Conferir com `bash -n` antes de entregar.
- `md_para_pdf.py` agora conhece os caminhos de Chromium do Linux — sem isso `kpi --pdf` gerava
  o `.md` e falhava no `.pdf` no servidor.
- **O que a VPS destrava depois:** o receptor de webhook do Sync (`sync_integration.py` já valida
  o HMAC, faltava URL pública). Levaria a intimação de rodada das 08:00 para tempo real — só
  depois de a rotina agendada estar provada, e exige decidir domínio e TLS.

## Jurisprudência no DJEN — busca por tema, todos os tribunais (17/09/2026)

Pedido da Dra. Juliana: jurisprudência na hora para a peça, **sem login no JusBrasil e sem
navegador aberto** (roda na VPS). O DJEN publica o teor integral de decisão, sentença e acórdão
de todos os tribunais que o usam, **inclusive o STJ**, e a API aceita `texto`. As APIs próprias dos
tribunais (levantamento do Manus, pasta no Drive) não servem: são de transparência, estatística ou
MNI com convênio; a do TJRO é de atermação; o Datajud não traz ementa.

```
python OPERACIONAL/main.py jurisprudencia "Súmula 298"                                  # todos, 3 meses
python OPERACIONAL/main.py jurisprudencia "Súmula 298" --tribunal TJRO --meses 12 --md   # _trabalho/jurisprudencia/
python OPERACIONAL/main.py jurisprudencia "Súmula 298" --tambem "frustração de safra" --tipo acordao --so-ementa
python OPERACIONAL/jurisprudencia.py --autoteste
```

Tipos (`--tipo`), na régua do KPI mas com sentença e acórdão separados: `liminar` (tutela de 1º
grau, inclusive efeito suspensivo a embargos à execução), `tutela-recursal`, `sentenca`, `acordao`,
`monocratica` (relator que resolve o recurso: nego provimento/seguimento, não admito). Embargos
de declaração ficam fora. Primeira carga, TJRO "Súmula 298" em 12 meses: 1.449 publicações →
1.023 julgados (170 liminares, 76 tutelas recursais, 308 sentenças, 250 acórdãos, 217 monocráticas).

Regras e armadilhas (não desfazer):
- **A API casa palavras soltas, não a frase**, e não faz E entre frases ("Súmula 298 frustração
  de safra" dá 0). A frase e o `--tambem` são conferidos no texto; para a API vai só a frase que
  o DJEN conta menos vezes (`termo_mais_seletivo`).
- **Uma consulta por mês.** A API devolve do mais recente para o mais antigo; com um limite só,
  o começo do período sumia sem aviso (a 1ª versão cobriu fev–set achando que era o ano). Mês que
  bate no limite sai como **período incompleto** na tela e no relatório.
- **Três origens de ementa, e só a própria vira citação.** Acórdão (TJRO: `DECISÃO: ... Ementa:`)
  → própria. Decisão do STJ que transcreve o "acórdão assim ementado" → é do TJ de origem, **nunca
  citar como STJ**. Ementa no corpo com referência entre parênteses → precedente citado, pista.
- **Resultado só do dispositivo** (`kpi_exito.extrair_dispositivo`); quando o extrator devolve
  uma "ementa" que não é do ato, lê-se o fecho (a ementa era de precedente citado na liminar).
- **Grau pela classe**, não por "desembargador" no início (sentença que cita precedente virava 2º
  grau); e o DJEN às vezes publica acórdão com a classe de origem.
- **"Favorável ao produtor" é leitura automática**: verbo do dispositivo × quem pediu (banco ou
  não). Na execução quem pede é o **executado** — sem isso, exceção rejeitada saía favorável.
- Magistrado pelo `vault_obsidian` (gabinete no DJEN → relator no cabeçalho → assinatura **no fim**
  do ato; nunca o corpo, onde estão os relatores dos precedentes citados).
- TRT/TST/TRE ficam fora por padrão ("Súmula 298" do TST é outra coisa). CPF/CNPJ mascarados.
- Somente leitura; saída em `_trabalho/jurisprudencia/` (gitignored, tem nome de parte). Citação
  continua exigindo conferência do inteiro teor no tribunal, mesmo guard-rail da `jurisprudencia-rural`.

### Base de julgados e perfil por órgão — `base` (17/09/2026)

A busca acima vira **base local**, **perfil decisório** e **ementário** no vault. Decisões da Dra.
Juliana: TJRO primeiro, depois o tribunal com mais processos no ADVBOX (**TRF1**: 148, 99 ativos,
contra TJMT 78 e TJPR 65); **2º grau por gabinete** e **1º grau por vara, informando os juízes**.

**Jurimetria não se mistura com as métricas do escritório** (17/09/2026). Fica em pasta própria,
`BASE_CONHECIMENTO/07 - JURIMETRIA/` (`ORGAOS/<TRIB>/`, `EMENTARIO/<TRIB>/`, `_PAINEL-<TRIB>`,
`_EMENTARIO-<TRIB>`), **nunca** em `01 - MAGISTRADOS` (que tem o bloco do KPI dos nossos casos), e
**não roda junto com o KPI** nem na VPS. Cada nota abre com esse aviso.

```
python OPERACIONAL/main.py base coletar             # TJRO desde 09/2024; incremental (mês fechado não recoleta)
python OPERACIONAL/main.py base status
python OPERACIONAL/main.py base perfil              # simula
python OPERACIONAL/main.py base perfil --gravar     # grava no vault (pede s/N)
python OPERACIONAL/main.py base coletar --tribunal TRF1 && python OPERACIONAL/main.py base perfil --tribunal TRF1
python OPERACIONAL/base_julgados.py --autoteste
```

- Base em `_trabalho/jurisprudencia/base_julgados.sqlite` (gitignored). Termos: crédito rural, cédula
  rural, alongamento, Súmula 298, descaracterização da mora. **"prorrogação" fica fora** (1.329/mês
  no TJRO, quase tudo prazo). O ato só entra no perfil com marca real do tema no texto.
- **Começa em set/2024** porque antes disso o DJEN quase não tem o TJRO ("Súmula 298": 2 em
  set/2023, 26 em set/2024, 134 em ago/2026). Perfil de período antigo é amostra do DJEN, não do tribunal.
- **Análise versionada** (`VERSAO_ANALISE`): mudou regra do `jurisprudencia.py`, sobe a versão e a
  base é relida sem coletar de novo.
- A automação só é dona do bloco `<!-- inicio:jurimetria -->` de cada nota; "Leitura humana do perfil"
  e "Nota de uso" ficam fora dele e nunca são tocadas. O bloco é **reconstruído** da base a cada rodada.
- **Ementário:** uma nota por acórdão com ementa própria (TJRO: 839), nome `TRIB AAAA-MM-DD SIGLA
  processo`, com sufixo `(2)` quando o mesmo processo tem dois acórdãos no mesmo dia (sem isso um
  sobrescrevia o outro). Frontmatter com tese, órgão, relator e resultado para consulta no Obsidian.
- **TRF1 abrange 13 estados:** 2º grau entra inteiro (gabinete no formato `Gab. 15 - DESEMBARGADOR
  FEDERAL ...`), 1º grau só varas de Rondônia (`FILTRO_1O_GRAU`) — no ADVBOX são 105 processos na SJRO,
  15 nas subseções de RO, 21 no TRF1 e só 5 de outros estados.
- Taxa favorável ao produtor = (favorável + 0,5 × parcial) ÷ atos com lado lido; **abaixo de 10 atos
  sai "amostra insuficiente"**. "Termos presentes nas desfavoráveis" sai sempre ao lado da frequência
  nas favoráveis: é indício, não motivo lido.
- Acórdão publicado **sem gabinete** no `nomeOrgao` não é atribuído por nome lido no texto: entra na
  contagem "sem órgão atribuível" do painel `_PAINEL-JURIMETRIA-TJRO`.
- **Conferido por amostra antes de ir ao vault** (3 sorteios de 30 atos, 17/09/2026): resultado e
  lado corretos em ~88% na 2ª e ~95% na 3ª. Cada erro virou regra: fronteira de palavra na marca de
  banco ("s.advogado" casava "s.a"); tema tem de estar no **objeto** do ato, não citado de passagem
  (INSS e promessa de compra e venda com "cédula rural" como prova); admissibilidade de REsp da
  Vice-Presidência fora do perfil de gabinete; gratuidade/custas fora (objeto acessório); parte só com
  **iniciais** vira "a conferir"; na busca e apreensão o autor é o credor; dispositivo que atravessa
  precedente citado é lido depois da referência; mesmo juiz com grafias diferentes é agrupado.
  Mudou regra? Nova amostra antes de gravar de novo.

### Uso estratégico na peça — `jurimetria` (17/09/2026)

Pedido da Dra. Juliana: a base não é só consulta, é **insumo da peça**. Mandamental em Ariquemes traz
o que a vara de Ariquemes já decidiu, precedente do TJRO na tese e a inicial já pensada para o STJ.

```
python OPERACIONAL/main.py jurimetria --tese alongamento --comarca Ariquemes --md
python OPERACIONAL/main.py jurimetria --tese mora --processo 7001234-56.2026.8.22.0002   # comarca pelo código de origem do CNJ
python OPERACIONAL/jurimetria_estrategia.py --autoteste
```

- Skill `jurimetria-estrategica` diz como cada seção entra na peça; os agentes `maldonado-divida-rural`
  (pergunta 16 do Bloco 4) e `maldonado-jurimetria` (passos 3 e 4) rodam o briefing antes de redigir/estimar.
- **Sinal de derrota vira prova, não argumento**, e é ordenado pela diferença entre a frequência nas
  derrotas e nas vitórias (termo que aparece igual nas duas não diz nada).
- **Óbices do STJ contados no texto integral** (Súmula 7 vem na fundamentação, não no dispositivo).
- **Perfil de juiz nunca entra na peça**; não escolhe juiz; precedente só com inteiro teor conferido.
- **Foco: alongamento e descaracterização da mora** (Dra. Juliana). Ato que trata das duas conta nas duas
  (`teses`, lista); antes ficava "tese não identificada" e sumia das duas.
- **STJ separado por quem recorreu.** A maioria dos REsp é do banco: taxa única media o banco perdendo, não
  a chance do produtor (alongamento: produtor recorrente 10%, banco recorrente 82%). Óbices e "REsp do
  produtor que deram certo" saem só do produtor recorrente. Óbices contados no texto integral: Súmula 7
  aparece em 84% das derrotas do produtor em alongamento.
- Armadilhas da carga de TRF1/STJ (17/09/2026, não desfazer): o STJ rotula decisão monocrática como
  "DESPACHO / DECISÃO" (7.895 saíam como despacho); monocrática do STJ transcreve "por unanimidade" do
  acórdão recorrido (não é acórdão); "descaracterização da mora" sozinha trazia financiamento de veículo
  (só conta com marca de crédito rural); TRF1 escreve "POLO ATIVO:"; IBAMA/União/INSS são parte não
  produtora; ação previdenciária com "aptidão ao Pronaf" como prova fica fora.
- A tese é marcada pelo texto (ementa, dispositivo ou objeto): ato que só menciona MCR/Súmula 298 também
  conta. O briefing avisa; a lista de favoráveis tem de ser aberta antes de usar.
- **Ementa do STJ só de "EMENTA / ACÓRDÃO"** (18/09/2026). A decisão monocrática do STJ transcreve a ementa do
  TJ de origem ("contra acórdão do TJSP cuja ementa guarda os seguintes termos"): 537 ementas de TJ entraram no
  ementário como se fossem do STJ e foram retiradas para `.trash/07 - JURIMETRIA (limpeza 18-09-2026)/`. O STJ
  entra no briefing (resultado, quem recorreu, óbices), não no ementário. Notas que saem da base vão para a
  lixeira do vault, e só se a parte humana estiver intacta.
- **Cobertura em 18/09/2026:** TJRO (86 órgãos, 708 ementas), TRF1 (48 órgãos: gabinetes + varas de RO, 30
  ementas, quase todas de execução fiscal de crédito rural: o acórdão de alongamento/mora do TRF1 chega ao DJEN
  sem ementa no texto), STJ (1.638 atos, só no briefing). Ementa de ED não entra (acórdão embargado transcrito,
  "cuja ementa segue abaixo transcrita"). `base perfil --gravar` move para a lixeira do vault a nota que saiu
  da base, se a parte humana estiver intacta. Rodar com `.venv/bin/python`: o `python3` do sistema não tem as dependências.

## Squad Jurimetria (BASE_CONHECIMENTO) — "Cérebro" do escritório

Ver `.claude/agents/maldonado-jurimetria.md` para a metodologia completa (8 passos): íntegra →
magistrado → perfil decisório → precedentes TJRO → probabilidade por pedido → veredito. Alimenta
um **vault Obsidian** em `BASE_CONHECIMENTO/` com notas por tema/magistrado/caso, interligadas.

### O vault se alimenta da automação (`vault_obsidian.py`) — 11/09/2026

As pastas `01 - MAGISTRADOS/` e `02 - CASOS/` estavam vazias desde a criação do vault: a
matéria-prima delas já existia, mas só como CSV de KPI. `OPERACIONAL/vault_obsidian.py` fecha
esse ciclo — **apuração de KPI → nota de caso e de órgão julgador**, com `[[links]]` para as
notas de tese que já existiam em `00 - TEMAS/`.

```
python OPERACIONAL/main.py vault --de 2026-09-01 --ate 2026-09-11      # simula (padrao)
python OPERACIONAL/main.py vault --de 2026-09-01 --ate 2026-09-11 --gravar
python OPERACIONAL/main.py vault --csv                    # le o CSV mais recente, sem API
python OPERACIONAL/main.py vault --dias 7 --incluir-fora-escopo   # tambem despacho/expediente
```

Primeira carga (01–11/09/2026): **28 notas de caso + 20 de órgão julgador + 2 painéis**
(`_PAINEL-CASOS`, `_PAINEL-ORGAOS`).

**A automação é dona de um bloco, não da nota.** Cada nota tem um trecho entre
`<!-- inicio:automacao -->` e `<!-- fim:automacao -->`; o resto — fatos, contrato, prognóstico,
perfil decisório — é humano e **nunca** é sobrescrito. Nota que não tenha o marcador não é
tocada de jeito nenhum (sobe como `ignorada` no relatório).

**A nota é o banco de dados dela mesma.** A tabela de atos é lida de volta e fundida antes de
ser reescrita, por (data, KPI, dispositivo) — rodar a competência de outubro não apaga os atos
de setembro, e o bloco é montado **depois** da fusão, para o resumo do órgão contar a nota
inteira e não só a rodada.

Regras e armadilhas (não desfazer):
- **Nunca inventa magistrado.** O DJEN entrega `nomeOrgao`, não o nome do juiz. O nome sai de
  duas fontes reais: o **órgão que se nomeia** (`Gabinete Des. Kiyochi Mori` — campo
  estruturado, vence tudo) e a **assinatura do ato** (`... Rinaldo Forti da Silva Juiz de
  Direito` — regex conservadora, com lista de bloqueio para não capturar "Vara"/"Tribunal").
  Sem os dois, fica vazio: nome errado numa nota de perfil faz a nota inteira descrever o juiz
  errado. Por isso as notas de `01 - MAGISTRADOS/` são **por órgão**, não por pessoa.
- **Nunca inventa tese.** O KPI classifica `rural`/`diversa`, que não é tese. O link para
  `00 - TEMAS/` sai do grupo do ADVBOX (alta) ou do texto do ato (média); batendo em **duas**
  teses ou em nenhuma, sobe como `TESE A CONFIRMAR` — não escolhe "a mais provável".
- **Nota nunca é rebaixada por fonte mais pobre.** `--csv` não carrega o texto do ato; sem a
  regra de acumular, rodar pelo CSV depois de uma rodada ao vivo apagaria tese, órgão e
  magistrado que a nota já tinha. Vale o valor **e a origem** já registrados.
- **Nome de órgão leva o tribunal na frente** (`TJPR - 14ª Câmara Cível`). "14ª Câmara Cível"
  existe no TJPR e no TJRJ; "Primeira Câmara de Direito Privado", no TJMA e no TJMT — sem o
  prefixo, dois tribunais diferentes cairiam na mesma nota de perfil decisório. O TJRO já traz
  a comarca no próprio nome (`Porto Velho - 4ª Vara Cível`).
- **Três foros, não dois.** Além de `TJRO/` e `JUSTICA_FEDERAL/` existe `OUTROS_TRIBUNAIS/`: a
  carteira real tem processo em TJPR, TJMT, TJRJ, TJMA, TJES e TRT14.
- **Só ato decidido vira nota** (padrão). Das 130 comunicações de 01–11/09, 102 eram despacho
  ou expediente — virariam 100 notas sem resultado nenhum. `--incluir-fora-escopo` traz tudo.
- `atualizado_em` só anda quando o conteúdo anda, senão a rodada diária marcaria as 50 notas
  como alteradas todo dia só pela troca da data.
- **Nada é gravado sem `--gravar` e sem "s/N"** no terminal. Somente leitura em ADVBOX, DJEN e
  Drive — a única escrita é `.md` dentro de `BASE_CONHECIMENTO/` (que é gitignored: tem nome de
  cliente e número de processo reais).
- O CSV do KPI ganhou a coluna **`orgao`** para isto (`kpi_exito.avaliar()`). CSV gerado antes
  de 11/09/2026 não a tem: as notas de caso saem, as de órgão não — regere com `kpi --csv`.
- A captura ao vivo é a mesma do KPI (`_capturar_djen_advbox()` em `main.py`, extraída de
  `cmd_kpi` para os dois usarem). Ela respeita o rate limit de 30 GET/min do ADVBOX, então a
  competência inteira leva alguns minutos.

### O vault aberto no Obsidian — configurado em 11/09/2026

`BASE_CONHECIMENTO/` virou um vault de verdade: `.obsidian/` com configuração, `_TEMPLATES/`
com as notas-modelo, e o vault registrado no app (Obsidian → `BASE_CONHECIMENTO`). O cofre
antigo `~/Documents/Obsidian Vault` era só o exemplo de fábrica e continua lá, vazio.

- **Sync e Publish ficam desligados de propósito.** O vault tem nome de cliente e número de
  processo reais — os mesmos dados que fazem `BASE_CONHECIMENTO/` ser gitignored. Nada sai
  desta máquina sem decisão do escritório.
- **Lixeira local** (`.trash` dentro do vault): nota apagada por engano se recupera ali.
- `_TEMPLATES/` guarda `_TEMPLATE-CASO` (o que a automação replica) e `_TEMPLATE-MAGISTRADO`
  — este último é **nota humana por pessoa**, para consolidar quem atua em mais de um órgão;
  a automação escreve notas de **órgão**, não de pessoa.
- **Bookmarks** já apontam para o índice e os dois painéis; o **grafo** tem cor por pasta
  (tema, órgão, caso, precedente, referência, formatação), senão vira nuvem sem significado.
- `.obsidian/` **não é versionado** (está dentro da pasta ignorada), e o `workspace.json` que o
  Obsidian grava ali carrega nome de arquivo aberto — ou seja, nome de cliente. Versionar a
  configuração exigiria excluir esse arquivo, e é decisão do escritório, não do código.
- Para registrar o vault noutra máquina: abrir o Obsidian → *Open folder as vault* →
  apontar para `BASE_CONHECIMENTO/`. O esquema `obsidian://open?path=...` **não** serve para
  isso — só abre vault já conhecido (dá "vault not found").

### Legislação na íntegra — CPC e MCR (`legislacao_vault.py`) — 12/09/2026

`BASE_CONHECIMENTO/06 - LEGISLACAO/` tem o **CPC** (Lei 13.105/2015, texto compilado do
Planalto de 12/09/2026 — 1.073 artigos em 10 notas por Livro) e o **MCR** (atualização nº 758, de
28/08/2026 — 99 seções e 1.010 itens em 12 notas por Capítulo), com o PDF oficial em `_original/`.
Cada artigo é título `###### Art. N` e cada item é `#### MCR c-s-i`, então a citação vira link
(`[[MCR-02-Condicoes-Basicas#MCR 2-6-4]]`) ou texto embutido (`![[...]]`).

```
python OPERACIONAL/legislacao_vault.py cpc ~/Downloads/L13105.pdf
python OPERACIONAL/legislacao_vault.py mcr ~/Downloads/ManualCompleto.pdf
```

- **As notas numeradas são artefato** — regerar com o PDF novo, nunca editar à mão. Comentário do
  escritório vai em `CPC-Guia-do-Escritorio` e `MCR-Guia-do-Escritorio`, que o script não toca.
- **O compilado do Planalto traz a redação revogada riscada ao lado da vigente**, e o risco é um
  retângulo desenhado por cima, não atributo de fonte. `_riscado()` descarta o que tem traço no
  **meio** da linha (o sublinhado de link fica na base). Sem isso o art. 921 sai com dois § 4º. O
  art. 945 não aparece porque foi revogado por inteiro.
- **O PDF do Bacen tem cabeçalho de seção errado** (pág. 83 e 274–275): seção que "volta" dentro
  do capítulo é tratada como continuação da anterior, e o script imprime a anomalia.
- As tabelas do Cap. 7 numeram linha como item ("1 - "): só vira título o número que avança.
- **Achado de 12/09/2026:** o **MCR 2-6-4 vigente** diz que a IF está autorizada a prorrogar
  *"por sua conveniência e decisão, mediante solicitação do mutuário"* (marca (*) na atualização de
  17/07/2026, Res. CMN 5.314). Isso atinge a tese da Súmula 298 como direito subjetivo e a subtese
  da desnecessidade do pedido prévio. Está sinalizado em `00 - TEMAS/MCR-2.6.4-Alongamento`, no
  guia do MCR e na skill `alongamento-divida-rural`. A resposta argumentativa é do Dr. Renan.
- **Norma do tempo do fato:** a pasta é a versão de hoje. Contrato ou pedido anterior pode ter sido
  regido por outra redação — buscar a atualização da época no site do Bacen.
- Fica dentro de `BASE_CONHECIMENTO/` (gitignored) por coerência com o vault. Só o script é versionado.

## Google Drive — estrutura ZEUS

O escritorio ja tem a convencao dele; o codigo **segue** ela, nao impoe outra:

```
ZEUS > 03. CLIENTES > 01 CLIENTES > [LETRA] > [NOME DO CLIENTE] > [subpastas]
```

**As subpastas variam por cliente** — levantamento no Drive real (amostra de 60 clientes,
02/09/2026): `DOC ADMINISTRATIVO` (42%), `DOC PESSOAL` (30%), `DOC BANCARIO` (27%),
`DOC RURAL` (22%), depois uma cauda longa (FOTOS E VIDEOS, REUNIAO, PROCURACAO, IRPF, CEDULA...).
Esses 4 primeiros sao o default de `SUBPASTAS_CLIENTE`; `DRIVE_SUBPASTAS_CLIENTE` no `.env`
sobrescreve. O `_WHITE_LABEL_SPEC.md` §7 diz `CONTRATO BANCÁRIO` e `REUNIÕES - VIA MEET`, que
na pratica quase nao existem — o codigo segue o Drive real, nao o spec.

Nomes de pasta no Drive do escritorio tem espaco sobrando (`DOC PESSOAL `), acento inconsistente
e ate erro de digitacao (`DOC ADIMINISTRATIVO`) — 43 variantes so na amostra. Por isso toda busca
de pasta usa `buscar_subpasta()` (comparacao normalizada), nunca match exato, e `criar_pasta()`
reaproveita a variante existente em vez de criar uma pasta irma quase identica.

### Saída da automação — `PEÇAS AUTOMAÇÃO`

Convenção definida pela Dra. Juliana (08/09/2026). Toda peça que a automação produz é
arquivada em:

```
ZEUS > PEÇAS AUTOMAÇÃO > [NOME DO CLIENTE] - [Nº DO PROCESSO] > peça.docx
```

- Fica na **raiz da ZEUS**, ao lado de `03. CLIENTES` — não dentro da pasta do cliente. O
  escritório precisa auditar num lugar só tudo que a automação gerou, sem varrer 60+ pastas.
- Peça de ação inicial ainda não distribuída: a pasta vai como `[CLIENTE] - SEM PROCESSO`,
  para renomear quando sair a distribuição.
- `DRIVE_PASTA_PECAS_AUTOMACAO_ID` no `.env` é o caminho rápido; sem ele o módulo localiza
  a pasta pelo nome dentro da ZEUS.
- Idempotente e com a mesma comparação normalizada do resto do módulo (caixa/acento/espaço),
  para não criar pasta irmã quase idêntica. **Pede confirmação antes de gravar.**

Comandos:
```
python OPERACIONAL/main.py drive peca peca.docx --cliente "NOME" --processo "7001234-56.2026.8.22.0001"
python OPERACIONAL/main.py drive peca peca.docx --cliente "NOME"     # sem processo -> SEM PROCESSO
python OPERACIONAL/main.py drive autenticar                   # conecta/confere a conta do escritorio
python OPERACIONAL/main.py drive sair                         # revoga o acesso e apaga o token
python OPERACIONAL/main.py drive testar                       # confere acesso e lista as letras
python OPERACIONAL/main.py drive cliente "NOME DO CLIENTE"    # localiza a pasta e lista conteudo
python OPERACIONAL/main.py drive cliente "NOME" --criar       # cria [LETRA]>[CLIENTE]>4 subpastas
python OPERACIONAL/main.py drive enviar peca.docx --cliente "NOME" --subpasta "DOC PESSOAL"
```

Regras:
- Auth: OAuth da conta do escritorio (`config/oauth_credentials.json` -> `config/token.json`);
  Service Account so como fallback. Nenhum dos dois e' versionado.
- **Trava de conta:** `GOOGLE_CONTA_ESCRITORIO` no `.env` fixa qual conta Google pode operar.
  Se o `token.json` for de outra conta, `autenticar_google()` aborta com o e-mail encontrado em
  vez de ler/gravar no Drive errado. Trocar de conta: `drive sair` (revoga + apaga o token) e
  depois `drive autenticar`.
- `DRIVE_PASTA_CLIENTES_ID` no `.env` e' o caminho rapido; sem ele o modulo navega ZEUS a partir
  de `DRIVE_PASTA_ZEUS_ID` — e sem nenhum dos dois, varre a raiz (mais lento e sujeito a homonimo).
- Toda chamada usa `supportsAllDrives`/`includeItemsFromAllDrives`: se a ZEUS estiver num Drive
  compartilhado, sem esses flags a API devolve **vazio sem erro** (falso-vazio silencioso).
- `criar_estrutura_cliente()` e' idempotente (reaproveita o que ja existe), mas **nunca roda sem
  confirmacao** — o `--criar` mostra o que sera criado e pergunta "s/N". Enviar arquivo tambem
  pede confirmacao.
- Nome de cliente e' comparado sem acento/caixa; apostrofo no nome (D'ALMEIDA) e' escapado antes
  de ir pra query.

## ADVBOX API
- Base: https://app.advbox.com.br/api/v1 | Doc oficial: https://api.softwareadvbox.com.br/docs
- Auth: Bearer token + User-Agent obrigatório. Token fornecido pela ADVBOX a parceiros/integradores
  aprovados — vive só em `config/.env` (`ADVBOX_API_TOKEN`), nunca no código nem em chat de IA.
- Rate limit: GET 30/min | POST 500/dia por rota | PUT 500/dia → `429`
- Diagnóstico: `python OPERACIONAL/main.py advbox` (confere token, conexão e se os IDs de
  `config/equipe.py` existem mesmo na conta — erro de ID só apareceria como 422 na hora de gravar).
- **Todo acesso passa por `INTEGRACOES/advbox_integration.py`.** Nenhum módulo deve montar
  `requests` + header de Bearer por conta própria: só o `_request` do módulo trata 429/retry
  e paginação.

Armadilhas da API já tratadas no módulo (não desfazer):
- `amount` (POST/PUT /transactions): a API **descarta o ponto decimal** — enviar `1500.50` grava
  `150050` (erro de 100x). Sempre string com vírgula (`"1.500,50"`) via `formatar_amount()`.
  `amount: 0` derruba a API com 500.
- `entry_type` deve casar com o tipo da categoria (`income`→CRÉDITO, `expense`→DÉBITO).
  `type` e `competence` são derivados de `entry_type`/`date_due` — não enviar.
- `lawsuits_id` em transação **exige `customers_id` junto**, senão 422.
- `phone`/`cellphone` (POST /customers): número local com DDD, **sem `+55`** — com código do país
  o contato é criado mas o telefone vira `ERROR`. `formatar_telefone()` normaliza e escolhe o
  campo certo (10 dígitos → `phone`, 11 → `cellphone`).
- `postalcode` exige o hífen (`99999-999`).
- `/settings` agrupa banks/categories/cost_centers/departments dentro de `financial` e usa
  `lawsuit_types` — `_normalizar_settings()` achata e cria o alias `type_lawsuits`.
- Tarefas usam `/posts`; campo de mensagem é `comments` (não `notes`); `from` é string.
- `GET /documents` **exige ao menos um filtro** (name ≥3 chars, customer_id, transaction_id ou
  post_id), senão 422. A URL de download expira em **300s** — baixar na hora.
- `GET /documents/{id}/download` responde **500 (não 404)** para id inexistente.

## DJEN/Comunica API (CNJ)
- Base: https://comunicaapi.pje.jus.br/api/v1/comunicacao
- Filtro principal: `numeroOab` + `ufOab` (não usar `nomeParte`, gera ruído).
- Instável: mesma consulta pode retornar "sistema ocupado" ou falso-vazio (`count:0`) mesmo
  havendo dados — o módulo trata isso com retry/backoff.

## Atende Direito API (CRM/Intake)
- Base URL e token em `config/.env` (`ATENDE_DIREITO_BASE_URL` / `ATENDE_DIREITO_API_TOKEN`).
- Auth: Bearer token + User-Agent.
- **Sem documentação pública** — endpoints e nomes de campo são configuráveis no `.env`;
  `intake --inspecionar` mostra o payload real para calibrar.
- Escrita de volta no Atende Direito é opt-in (`ATENDE_DIREITO_ENDPOINT_MARCAR` vazio = não escreve).

## SYNC API (Atende Direito) — monitoramento processual

**Não é o mesmo produto da seção acima.** O Atende Direito tem dois sistemas, e este
repositório integra os dois separadamente: o **CRM** (lead → cliente, Squad Intake) e o
**Sync** (intimação, prazo, autos — Squad Controladoria + KPI). Chave, base URL e módulo
diferentes. O Sync encosta no `comunica_djen.py`, não no intake.

- Base: https://api.sync.atendedireito.app | Swagger **público**: `/openapi.json`
- Painel (gerar a chave, aba API): https://sync.atendedireito.app
- Auth: `Authorization: Bearer sk_live_...` — uma chave só, em `config/.env` (`SYNC_API_TOKEN`).
- Módulo: `INTEGRACOES/sync_integration.py` · Comando: `python OPERACIONAL/main.py sync`
- Detalhamento completo: **`docs/INTEGRACAO_SYNC.md`** (ativação, cobertura, webhook, armadilhas).

Fonte da triagem passou a ser escolhível — **o default não mudou**:
```
python OPERACIONAL/main.py triagem --dias 7                 # DJEN (padrao, inalterado)
python OPERACIONAL/main.py triagem --dias 7 --fonte sync    # Sync
python OPERACIONAL/main.py triagem --dias 7 --fonte ambas   # as duas, com dedupe conservador
python OPERACIONAL/main.py sync                             # diagnostico (chave, conta, monitores, OABs)
python OPERACIONAL/main.py sync inspecionar --recurso intimacoes -n 2
```

O que o Sync resolve: captura em PDPJ **além** do DJEN (sem o falso-vazio), prazo como
**obrigação deduplicada por ato** (o DJEN publica uma cópia por advogado; ciência em qualquer
uma fecha todas), autos inteiros em Markdown com teor dos documentos, e webhook assinado em vez
de polling.

Guard-rails (não desfazer):
- **Somente leitura, trava dupla.** Toda escrita exige `SYNC_PERMITIR_ESCRITA=1` no `.env` **e**
  `confirmado=True`. O comando `sync` não expõe escrita nenhuma: dar ciência é ato da
  controller, depois de lançar a tarefa no ADVBOX — ciência carimbada pela automação esconde a
  pendência.
- **O prazo do Sync não decide o recurso.** Ele calcula a data fatal pelo CPC, mas o
  POP-CJ-003-A exige cotejo INICIAL x DECISÃO: quem fecha é
  `triagem_divida_rural.avaliar_recurso_cabivel()`, com as **duas** datas (ED e principal). O
  `data_fatal` entra como insumo e conferência, nunca como conclusão.
- **O polo não se adivinha.** Se o Sync não devolver o polo da parte, `resumir_intimacao()`
  deixa `partes_polo` vazio e marca `polo_indisponivel=True`. Polo invertido transforma êxito em
  inêxito e falseia o mês inteiro do KPI.
- **`GET /v1/intimacoes` corta o `texto` em 600 caracteres** — serve para triar o tipo do ato,
  **não** para ler dispositivo (KPI). `intimacoes_para_triagem()` abre cada item para o teor
  integral e marca `texto_truncado=True` no que não deu.
- **`GET /v1/prazos` não tem janela de data padrão** — sem `de`/`ate` devolve a carteira inteira.
- `resumir_intimacao()` devolve **o mesmo dict que `comunica_djen.resumir()`**, para
  `triagem_lote()` e o KPI consumirem sem alteração. Os extras do Sync vêm prefixados `sync_*`.
- O Swagger documenta os parâmetros mas **não tipa as respostas** (`schema: {}`): a leitura é
  tolerante a aliases e `sync inspecionar` existe para calibrar contra o payload real.
- **Cobertura é outra lista.** O DJEN usa `OABS_MONITORADAS` (2 OABs); o Sync usa os monitores
  cadastrados **na conta dele**. `sync diagnostico` cruza as duas e acusa a diferença — carteira
  menor lá não dá erro, dá intimação que não chegou. Criar monitor de OAB consome **cota do
  plano**, por isso é escrita travada.
- `autos.md` é **o espelho do Sync, não certidão dos autos** — mesmo guard-rail do OCR do
  `BASE_CONHECIMENTO`: serve para localizar a passagem; citação em peça se confere contra os autos.

**Status em 21/09/2026: Sync ATIVO, somente leitura.** Conta "Renan Maldonado" (tenant 165),
chave no `config/.env` do Mac (a VPS ainda não tem: copiar à mão, como toda credencial).
`SYNC_PERMITIR_ESCRITA` segue vazio. O que a conta tem hoje (`main.py sync`):

- **1 monitor, OAB RO5769.** A **OAB 13021/RO** (Dr. Bruno Vinícius), que o DJEN monitora, **não
  tem monitor** no Sync. Criar monitor consome cota do plano: decisão do escritório.
- **Ativação em 21/09/2026 (`main.py sync ativar --todos`, a pedido da Dra. Juliana):** os 2.688
  descobertos pela OAB foram enviados — 1.945 ativados nas vagas do plano Escritório (teto 2.000,
  com os 528 ativos no ADVBOX na frente) e **743 aguardando pagamento** da fatura avulsa nº 187
  (R$ 111,45, vence 28/09/2026). Processo não ativado não gera intimação pelo Sync.
- **Importação dos ativos do ADVBOX (`main.py sync importar-advbox`, 21/09/2026):** 363 processos
  ativos no ADVBOX que a OAB RO5769 não enxergava foram importados (monitor 331, tipo
  `importacao`); 116 ativados nas vagas e **245 aguardando a fatura nº 188** (R$ 36,75, vence
  28/09/2026). A importação é assíncrona: o comando espera o lote concluir antes de ativar.
  Ficam de fora os ativos do ADVBOX **sem número CNJ válido** no cadastro (~211). Monitor da OAB
  13021/RO (Dr. Bruno Vinícius): **não criar** — decisão da Dra. Juliana, 21/09/2026.
- Antes da ativação eram 55 acompanhados.
- **O Sync desliga sozinho o processo baixado no tribunal** (`monitorado: false` no detalhe; some de
  `GET /v1/processos`). Na leitura inicial a carteira caiu de 1.960 para 1.281 com metade lida:
  a carteira em andamento tende a ~1.000, dentro do teto de 2.000, sem excedente a partir do
  ciclo de 16/10. Regra da Dra. Juliana (21/09/2026): **no Sync, só processo em andamento**. Por
  isso a fatura 187 (743, quase todos arquivados no ADVBOX) não é para pagar; a 188 (ativos), sim.
  `main.py sync desligar-arquivados` (simula; `--executar` grava) tira o que está arquivado no
  ADVBOX e ainda ficou ligado; ativo no ADVBOX × baixado no tribunal sobe como divergência.
- **Fechamento de 21/09/2026:** faturas 187 e 188 **canceladas** pela Dra. Juliana. Os 230 ativos do
  ADVBOX que estavam presos na 188 foram ativados dentro das vagas (`sync ativar --monitor 331
  --so-ativos`, sem custo) e os 6 arquivados no ADVBOX foram desligados. Carteira no Sync: ~1.290
  processos em andamento, sem excedente. Mesmo assim, em 20–21/09 o Sync trouxe 16 dos 17
  processos com publicação no DJEN (o que faltou, 0000028-96.2026.8.22.0024, está na carteira
  como `baixado`). Por isso o default da triagem não mudou.
- **Credencial do Dr. Renan** (certificado A1, válido até 20/08/2027, com 2FA) cadastrada e
  com saúde "ok": é ela que destrava documento de processo que o DJEN não publica.

Calibragem contra o payload real (21/09/2026, não desfazer):
- `GET /v1/monitores` devolve `{"monitores": [...]}` (e `/credenciais`, `{"credenciais": [...]}`):
  sem essas chaves em `_CHAVES_LISTA`, o diagnóstico dizia "0 monitores" com a OAB ativa.
- **A intimação do Sync não traz parte nem polo** (nem na lista, nem no detalhe) — só o cadastro
  do processo tem `polo_ativo`/`polo_passivo`, em texto. `polo_indisponivel` agora sobe sempre
  que não houver polo lido (antes só subia se viessem partes sem polo, e ficava `False`).
- O detalhe da intimação traz a **"costura"**: todas as hipóteses de prazo do ato (ex.: ED 5 dias
  + recurso principal), com base legal. Continua sendo insumo: quem fecha o recurso é o cotejo.
- O webhook ainda pede URL pública HTTPS (a VPS destrava) e `SYNC_WEBHOOK_SECRET`.

## Padrões de peça
- Toda peça sai no timbrado do escritório via **skill `timbrado`**
  (`.claude/skills/timbrado/SKILL.md`), que carrega `DOCS_MODELOS/timbrado_modelo.docx` — faixa
  2026 (extraída de peça protocolada em 08/09/2026), margens esq 2,54 / dir 2,44 / sup 7,37 (5,33 até 15/09/2026) /
  inf 2,5 cm, Arial Narrow 12 pt, justificado, entrelinha 1,5. **Nunca** montar peça a partir de
  arquivo "timbrado" solto do Drive: há 44 deles e quase todos estão obsoletos (o de 2024 ainda
  lista advogado que saiu do escritório).
- **O quadro de advogados da faixa é dado, não imagem** (`config/equipe.py` →
  `ADVOGADOS_TIMBRADO`): 11 nomes desde 16/09/2026, com a entrada da Dra. Taynara, da Dra.
  Heloísa, do Dr. Agenor (**OAB/PE 62.751** — é de Pernambuco, não de Rondônia) e da Dra. Ana
  Sheila (OAB/RO 16.126). Incluir ou
  tirar advogado é editar a lista e rodar `python OPERACIONAL/gerar_timbrado.py`, seguido dos
  dois geradores de modelo (`gerar_modelo_declaratoria.py`, `gerar_modelo_alongamento.py`), que
  embutem o timbrado. O `.docx` é artefato: não editar à mão. Quadro em uma coluna, Dr. Renan primeiro
  e demais em ordem alfabética, Arial 9 pt preto; o cabeçalho cresceu (margem superior 7,37 cm),
  reservada para 12 nomes; `gerar_timbrado.py` falha com erro em vez de estourar em silêncio, porque o estouro
  empurraria o corpo de toda peça para baixo e só apareceria no protocolo.
- Assinatura padrão: Dr. Renan Gomes Maldonado de Jesus - OAB/RO 5769 - Porto Velho/RO.
- **Títulos em negrito**, caixa alta, na margem esquerda, numerados em romano.
- **Jurisprudência com recuo à direita e em itálico** (bloco deslocado ~4 cm além da margem);
  a identificação da fonte ("STJ - Súmula 297") centralizada, em negrito + itálico.
  Regras confirmadas pela Dra. Juliana em 08/09/2026 — ver
  `BASE_CONHECIMENTO/05 - FORMATACAO/Modelo-Mandamental-Prorrogacao.md`.
- Documentos que instruem a peça (e os recortes que vão nos placeholders) saem da skill
  **`inicial-anexos`** — ver a seção do Squad Dívida Rural.
- **Declaratória de descaracterização da mora não se redige do zero:** o modelo mestre é
  `DOCS_MODELOS/MODELO_DECLARATORIA_DESCARACTERIZACAO_MORA.docx`, gerado por
  `OPERACIONAL/gerar_modelo_declaratoria.py` (a fonte versionada — o `.docx` é artefato, não
  editar à mão). Os componentes de visual law estão em `OPERACIONAL/visual_law.py` e a
  justificativa de cada um em `.claude/skills/descaracterizacao-mora/MODELO_INICIAL.md`.
  Antes de entregar, rodar `visual_law.varrer_lexico_embargos(doc)`: vocabulário de embargos
  numa declaratória já custou a reconversão da classe de ofício (Restrição Absoluta nº 19).
- **Alongamento / prorrogação também não se redige do zero (13/09/2026):** a "Petição Perfeita" é
  `DOCS_MODELOS/MODELO_ALONGAMENTO_DIVIDA_RURAL.docx`, gerada por
  `OPERACIONAL/gerar_modelo_alongamento.py` (fonte versionada; o `.docx` é artefato). Substitui o
  modelo do Google Docs do Núcleo Sigma, que não tinha os 3 ajustes da devolutiva da GJ de 08/08/2026.
  Regras que o gerador materializa (não desfazer):
  - **Tutela cautelar é a via principal** (arts. 300, 301 e 308, § 1º) — pede os meios (exigibilidade,
    mora, negativação com SCR/SICOR, constrição); a antecipada é variante só com evidência plena. **Tutela
    da evidência (art. 311, II) não cabe**: Súmula 298 não é repetitivo nem súmula vinculante.
  - **Âncora legal:** Lei 4.829/65 arts. 4º e 14 (delegação ao CMN) → MCR 2-6-4 + Súmula 298; **DL 167/67
    art. 62** para prorrogação após o vencimento. Nunca CC 317/478 nem Lei 8.171 art. 104 (os textos não
    dizem isso — conferido no Planalto, `06 - LEGISLACAO/LEIS-FEDERAIS/`).
  - **Dois caminhos no tópico III.2** (pedido antes do vencimento × não houve), porque a tempestividade
    depende da linha de crédito e da redação do MCR na data do fato.
  - **Calibrado pelos motivos reais de derrota** (`00 - TEMAS/Diagnostico-Vitorias-Derrotas-Alongamento`,
    104 decisões): blindagem do laudo (1º motivo, 31 de 61), cognição sumária × dilação, natureza rural para
    CCB/recursos próprios (MCR 6-1-1 "a" II e 6-1-10), cronograma dentro do teto da linha.
  - **Precedente só com ementa literal conferida no acervo**, com tarja correta (STJ / "outro tribunal ·
    persuasiva"); nenhum do TJRO até haver íntegra. Tudo marcado "conferir inteiro teor".
  - Antes de entregar: `varrer_marcadores_print` e a varredura de vocabulário revisional do próprio script
    (menção negativa "não se pede" é legítima).
  - **A peça é contada pelas provas** (Dra. Juliana, 13/09/2026: "o que o juiz quer ver são as provas"):
    índice das provas + **23 blocos** `visual_law.bloco_prova` (moldura, recorte grifado com "grifo nosso",
    transcrição, "o que prova"). A ficha `MODELO_ALONGAMENTO_DIVIDA_RURAL.provas.json` diz à automação de
    anexos o tipo de documento, onde recortar e o que grifar; `anexos_inicial.inserir_recorte` limita a
    imagem à largura da célula quando o marcador está dentro do quadro (não desfazer — sem isso a imagem
    estoura a moldura). Mais quadros aqui é decisão consciente: a economia vale para a argumentação, não
    para a prova.
- Peça pronta vai para `ZEUS > PEÇAS AUTOMAÇÃO > [CLIENTE] - [Nº PROCESSO]` (ver seção do Drive).
- Formatação calibrada pelos 3 modelos reais: justificado, citações/tabelas comparativas em
  destaque (ex.: "juros compostos" x "capitalização"), sumário em tópicos I-IV na revisional.

## Credenciais (config/.env)
Todas as credenciais ficam em `config/.env` (copiar de `config/.env.example`).
NUNCA versionar o `.env`. Ver `docs/ONBOARDING.md` para o passo a passo de configuração.

## Regra recursal — ED antes de agravo/apelação (POP-CJ-003-A)

Regra da Dra. Juliana (08/09/2026), obrigatória para **todo ato decisório de todo
processo**, não só dívida rural: antes de concluir que cabe agravo ou apelação, é
preciso **cotejar a petição inicial (ou a última manifestação da parte) com a decisão**
e verificar **contradição, obscuridade ou omissão** (inclui fundamentação genérica,
art. 489 §1º III e IV). Havendo qualquer um → **embargos de declaração, 5 dias úteis**
(art. 1.023), que **interrompem** o prazo do recurso principal (art. 1.026). Não havendo
nenhum → agravo de instrumento (art. 1.015, I) ou apelação, 15 dias úteis.

Por que é obrigatória e não opcional: a janela do ED fecha 3x mais cedo que a do agravo,
então quem anota só o prazo do agravo perde o ED em silêncio; e sem ED a omissão não fica
prequestionada, ou seja, o tribunal não conhece o argumento depois.

Implementação: `triagem_divida_rural.avaliar_recurso_cabivel()` marca todo ato decisório
como `RECURSO CABÍVEL: A DEFINIR — exige cotejo INICIAL x DECISÃO`, força **prioridade
alta**, devolve as **duas datas** (ED e recurso principal) e levanta indícios textuais de
vício. **Indício não é conclusão** — o classificador não lê a inicial e nunca fecha o
recurso sozinho. Detalhamento em `.claude/agents/maldonado-controladoria.md`.

## Regra de ouro
A IA **nunca protocola** e **nunca cria/move tarefa sem confirmação explícita**. Toda peça e toda
triagem terminam prontas para revisão da Dra. Juliana / do Dr. Renan.
