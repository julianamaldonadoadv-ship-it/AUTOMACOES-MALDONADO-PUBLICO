# Integração com o SYNC (Atende Direito)

> Levantado em 11/09/2026 contra o Swagger público da API.
>
> **Status: o Sync NÃO foi contratado pelo escritório.** Esta integração está escrita, testada
> e **inerte** — não há conta, não há chave, nenhuma chamada sai. Foi deixada pronta de
> propósito: se a direção decidir contratar, a ativação é colar uma chave no `.env`, não
> esperar desenvolvimento. Enquanto `SYNC_API_TOKEN` estiver vazio, o sistema se comporta
> exatamente como antes — a triagem captura pelo DJEN e a rodada das 08:00 nem passa por
> este código.
>
> Nenhuma dependência nova foi adicionada (`requests` e `python-dotenv` já estavam no
> `requirements.txt`).
>
> **O que este documento serve agora:** subsídio para a decisão de contratar — a seção
> "Por que interessa ao escritório" lista o que o Sync resolveria das dores atuais, e
> "Diferenças de cobertura" e "Webhook" listam o que ele *não* resolve sozinho.

## O que o Sync é — e o que ele não é

O **Sync** é o produto de **monitoramento processual** do Atende Direito: importa a carteira
pela OAB na fonte oficial (PDPJ/jus.br + DJEN) e mantém vigilância contínua.

**Não confundir com o "Atende Direito" que já está integrado neste repositório.** São dois
produtos da mesma casa, com chave, base URL e finalidade diferentes:

| | Produto | Módulo | Serve para |
|---|---|---|---|
| Já integrado | Atende Direito (CRM) | `INTEGRACOES/atende_direito_integration.py` | Lead qualificado → cliente + processo no ADVBOX (Squad Comercial/Intake) |
| **Agora** | **Sync** | **`INTEGRACOES/sync_integration.py`** | **Intimação, prazo, autos, jurimetria (Squad Controladoria + KPI)** |

O Sync encosta no `comunica_djen.py`, não no intake.

## Por que interessa ao escritório

O que o Sync entrega e que hoje o repositório faz por conta própria — ou não faz:

| Dor atual | O que o Sync traz |
|---|---|
| A API do DJEN é instável (alterna "sistema ocupado" e falso-vazio; `comunica_djen.py` tem 10 tentativas com backoff só para contornar) | Captura na fonte oficial já consolidada, com PDPJ **além** do DJEN |
| O DJEN publica **uma cópia por advogado destinatário** — o mesmo ato chega N vezes | Prazo é **obrigação deduplicada por ato**: as N cópias viram uma linha, com todos os `intimacao_ids`; ciência em qualquer uma fecha todas |
| A triagem roda por **polling** às 08:00 (POP-CJ-003) e só vê as publicações de ontem | **Webhook assinado (HMAC-SHA256)** por evento — intimação chega em tempo real |
| Ler o teor da decisão exige abrir o PJe na mão; o `BASE_CONHECIMENTO` precisou de OCR do Vision | `GET /v1/processos/{n}/autos.md` devolve **os autos inteiros em Markdown**, com teor dos documentos |
| Processo parado é descoberto na conferência manual | `parado_min` na listagem de processos + alerta nativo de 90+ dias |

## Guard-rails — as três regras que o módulo protege

Estas não são detalhe de implementação; são decisões do escritório que a integração podia
atropelar em silêncio. Estão no topo de `sync_integration.py` e nos testes.

### 1. Somente leitura, com trava dupla

Toda rota de escrita do Sync (dar ciência em prazo, marcar intimação como tratada, criar
monitor, registrar webhook) exige **as duas coisas**: `SYNC_PERMITIR_ESCRITA=1` no `.env`
**e** `confirmado=True` na chamada. Sem isso levanta `SyncError` antes de tocar a rede.

O comando `sync` da CLI **não expõe nenhuma escrita** de propósito: dar ciência é ato da
controller, depois de lançar a tarefa no ADVBOX. Ciência carimbada pela automação esconde a
pendência — o prazo desaparece do painel sem ninguém ter tratado o ato.

### 2. O prazo do Sync não decide o recurso (POP-CJ-003-A)

O Sync calcula a data fatal pelo CPC. Isso **não substitui** o cotejo INICIAL × DECISÃO que a
regra da Dra. Juliana (08/09/2026) exige para saber se cabe **ED em 5 dias úteis** antes do
agravo/apelação em 15.

Quem fecha o recurso continua sendo `triagem_divida_rural.avaliar_recurso_cabivel()`, que
devolve **as duas datas**. O `data_fatal` do Sync entra como insumo e como conferência — nunca
como conclusão. Anotar só o prazo do agravo perde o ED em silêncio, e sem ED a omissão não
fica prequestionada.

O comando `sync prazos` imprime esse lembrete junto da lista, para o número não ser lido como
veredito.

### 3. O polo não se adivinha

A apuração de KPI depende de saber de que lado o escritório está: *"recurso não provido"* é
inêxito se o recurso é nosso e êxito se é do banco. No DJEN isso vem estruturado em
`destinatarios[].polo` (`"A"`/`"P"`).

Se o Sync não devolver o polo, `resumir_intimacao()` deixa `partes_polo` **vazio** e marca
`polo_indisponivel=True` — nunca chuta. A captura avisa quantos itens vieram assim. Polo
invertido transforma êxito em inêxito e falseia o mês inteiro.

## Como ativar (3 passos) — quando e se for contratado

```bash
# 1. Gerar a chave: https://sync.atendedireito.app -> aba API  (formato sk_live_...)
#    e colar em config/.env:
#       SYNC_API_TOKEN=sk_live_...

# 2. Conferir chave, conta, monitores e cobertura das OABs:
python OPERACIONAL/main.py sync

# 3. Calibrar o adaptador contra o JSON real da conta:
python OPERACIONAL/main.py sync inspecionar --recurso intimacoes -n 2
```

O passo 3 não é opcional. O Swagger do Sync documenta todos os **parâmetros**, mas devolve
`schema: {}` nas **respostas** — os nomes de campo do retorno não estão publicados. Por isso a
leitura é tolerante a aliases (mesmo padrão do módulo do CRM) e `inspecionar` mostra o payload
cru ao lado do que o adaptador extraiu dele. Campo que sair vazio no "ADAPTADO PARA A TRIAGEM"
é alias a acrescentar em `resumir_intimacao()`.

Enquanto `SYNC_API_TOKEN` estiver vazio, **nada muda**: a triagem segue capturando pelo DJEN.

## Comandos

```
python OPERACIONAL/main.py sync                       # diagnostico (chave, conta, monitores, OABs)
python OPERACIONAL/main.py sync painel                # painel do dia numa chamada
python OPERACIONAL/main.py sync intimacoes --dias 1   # intimacoes acionaveis, teor integral
python OPERACIONAL/main.py sync prazos --estado acionaveis
python OPERACIONAL/main.py sync prazos --de 2026-09-01 --ate 2026-09-30
python OPERACIONAL/main.py sync autos 7001234-56.2026.8.22.0001 -o autos.md
python OPERACIONAL/main.py sync webhooks              # o que esta registrado
python OPERACIONAL/main.py sync inspecionar --recurso prazos -n 2
```

E a triagem da Controladoria passa a escolher a fonte:

```
python OPERACIONAL/main.py triagem --dias 7                    # DJEN (padrao, inalterado)
python OPERACIONAL/main.py triagem --dias 7 --fonte sync       # so Sync
python OPERACIONAL/main.py triagem --dias 7 --fonte ambas      # as duas, com dedupe
```

**O default continua `djen`** — nada muda na rotina das 08:00 sem alguém pedir. `--fonte ambas`
é o modo de transição: roda as duas e unifica o ato repetido, para comparar cobertura antes de
trocar de fonte.

### Como o dedupe de `--fonte ambas` se comporta

Agrupa por (processo, dia) e só funde quando **a abertura do texto coincide** (60 primeiros
caracteres, ignorando espaço). É conservador de propósito, porque o mesmo processo pode ter
dois atos diferentes no mesmo dia — foi o caso de uma cliente, com *"defiro o pedido formulado
pela parte autora"* e *"defiro a dilação de prazo"*. Na dúvida **mantém os dois** e avisa:
duplicata repetida é incômodo visível; intimação fundida por engano é prazo perdido em
silêncio.

Ganhando o par, fica a versão **com polo**; empatado, a do **Sync** (teor integral). O texto
mais longo dos dois é sempre preservado, e `_fontes` registra por onde o ato chegou.

## Diferenças de cobertura — o que conferir antes de trocar de fonte

A captura do DJEN usa `OABS_MONITORADAS` (2 OABs: Dr. Renan 5769/RO e Dr. Bruno Vinícius
13021/RO). A captura do Sync usa **os monitores cadastrados na conta do Sync** — que são outra
lista, mantida no painel deles.

`sync diagnostico` cruza as duas e acusa OAB monitorada aqui que não tem monitor lá. Carteira
diferente = triagem com cobertura diferente, e isso não aparece como erro: aparece como
intimação que simplesmente não chegou.

Atenção também ao **plano**: criar monitor de OAB traz a carteira inteira daquele advogado e
consome cota de processos monitorados. Por isso `criar_monitor()` é escrita travada — não é
decisão da automação.

## Webhook — o que falta decidir

O Sync entrega os eventos por **POST assinado com HMAC-SHA256** (header
`X-Webhook-Signature`), com retry e backoff. Isso substituiria o polling das 08:00 por
tratamento em tempo real.

O módulo já traz `registrar_webhook()` e `verificar_assinatura_webhook()` (comparação em tempo
constante, aceita o formato cru e o prefixado `sha256=`). **O que não existe ainda é o
receptor**, e ele depende de uma decisão de infraestrutura que não é da automação:

- a API do Sync **recusa IP interno/privado** — o receptor precisa de URL pública HTTPS;
- hoje o escritório roda por `launchd` no Mac da Dra. Juliana (`deploy/com.maldonado.kpi.plist`),
  que não tem endereço público;
- sem `SYNC_WEBHOOK_SECRET` conferido a cada POST, qualquer um que descubra a URL injeta
  intimação falsa na fila da controller.

Enquanto essa decisão não vier, o polling (`--fonte sync`) resolve com atraso de uma rodada —
igual ao DJEN hoje.

## Referência da API

- Base: `https://api.sync.atendedireito.app`
- Swagger público (sem login): `https://api.sync.atendedireito.app/openapi.json`
- Painel: `https://sync.atendedireito.app`
- Auth: `Authorization: Bearer sk_live_...` (uma chave só, em toda requisição)
- MCP remoto: `https://api.sync.atendedireito.app/mcp` (OAuth 2.1; 21 ferramentas) — permite
  operar o Sync em linguagem natural pelo próprio Claude Code. Fora do escopo deste módulo,
  mas é o caminho mais curto para consulta exploratória.
- Toda resposta traz `X-Request-Id` — o módulo inclui esse id nas mensagens de erro, para
  abrir chamado com o suporte deles.

Códigos que o módulo trata: **401** chave inválida · **402** conta suspensa por cobrança (a
API cobra na porta, fora de `/v1/conta`) · **404** id inexistente ou documento sem markdown ·
**429** rate limit, respeitando `Retry-After`.

Ao contrário do DJEN, **vazio aqui é vazio de verdade** — não há falso-vazio, então não há
retry cego.

### Endpoints usados pelo módulo

| Endpoint | Função no módulo | Onde serve |
|---|---|---|
| `GET /v1/conta` | `conta()` | diagnóstico / whoami |
| `GET /v1/dashboard` | `dashboard()` | `sync painel` |
| `GET /v1/intimacoes` | `listar_intimacoes()` | triagem (POP-CJ-003) |
| `GET /v1/intimacoes/{id}` | `obter_intimacao()` | teor integral (a listagem corta em 600 caracteres) |
| `GET /v1/prazos` | `listar_prazos()` | prazos D-5/D-3, já deduplicados por ato |
| `GET /v1/processos` | `listar_processos()` | carteira, processo parado (`parado_min`) |
| `GET /v1/processos/{n}/autos` | `autos()` | linha do tempo unificada |
| `GET /v1/processos/{n}/autos.md` | `autos_markdown()` | leitura de decisão, Squad Jurimetria |
| `GET /v1/documentos/{id}/markdown` | `documento_markdown()` | teor OCR de um documento |
| `POST /v1/busca` | `buscar()` | busca em tempo real, não persiste |
| `GET /v1/jurimetria` | `jurimetria()` | Squad Jurimetria |
| `GET /v1/monitores` | `listar_monitores()` | conferir cobertura x `OABS_MONITORADAS` |
| `GET /v1/webhooks` | `listar_webhooks()` | `sync webhooks` |

Escritas implementadas mas **travadas**: `POST /v1/intimacoes/{id}/tratar`,
`POST /v1/prazos/ciencia`, `POST /v1/monitores`, `POST /v1/webhooks`.

### Armadilhas da API já tratadas (não desfazer)

- **`GET /v1/intimacoes` corta o campo `texto` em 600 caracteres.** Para triagem serve (dá o
  tipo do ato); para **ler dispositivo** (KPI de êxito) não serve. `intimacoes_para_triagem()`
  abre cada item para pegar o teor integral e marca `texto_truncado=True` no que não deu.
  Ler dispositivo em texto cortado dá a conclusão errada — e o KPI já tem a regra de ler
  **só o dispositivo**, nunca o corpo, porque o corpo transcreve a decisão recorrida.
- **`GET /v1/prazos` não tem janela de data padrão** — sem `de`/`ate` devolve a lista inteira,
  de propósito (é o que a tela deles consome). Numa carteira de 3.004 processos isso é muita
  linha: passe `de`/`ate` ao apurar competência.
- **`com_prazo` e `sem_prazo` não se combinam** — `listar_intimacoes()` levanta `ValueError`
  antes de gastar a chamada.
- **`autos.md` é o espelho do Sync, não certidão dos autos.** O próprio sumário do arquivo diz
  o que ficou de fora (teor em processamento, indisponível na origem, arquivo binário). Vale o
  mesmo guard-rail do OCR do `BASE_CONHECIMENTO`: serve para localizar a passagem; **citação em
  peça se confere contra os autos**.
- **O enum de eventos do webhook não está no Swagger** — só os exemplos `intimacao.criada` e
  `prazo.vencendo`. Confirme a lista na aba API do painel antes de filtrar: evento não assinado
  **não chega**, e o silêncio é indistinguível de "não aconteceu nada". Lista vazia = todos.
- Campo que chega como **objeto aninhado** (`orgao: {nome: ...}`, `tribunal: {sigla: ...}`) é
  resolvido por `_SUBCAMPOS` no `_primeiro()`. Sem isso o alias `orgao` não achava nada, porque
  o achatamento guardou a chave como `orgao.nome`.
