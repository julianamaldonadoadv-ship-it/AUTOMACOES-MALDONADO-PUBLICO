# Guia de Instalação — Agentes Maldonado no Claude.ai

Este guia mostra como instalar os agentes do Dr. **Renan Gomes Maldonado de Jesus** (Maldonado Advogados, Porto Velho/RO) como **Projects** no Claude.ai (https://claude.ai).

## Agentes disponíveis em `.claude/agents/`

### Custom Instructions (3 Projects do Claude.ai — as 3 frentes do contrato)

| Arquivo (em `.claude/agents/`) | Para que serve | Quando usar |
|---|---|---|
| `maldonado-divida-rural.md` | **Produção de peças** — prorrogação/alongamento, descaracterização de mora (Tema 28/STJ) e ação revisional de contrato bancário rural. | Sempre que o caso for da carteira principal do escritório: produtor rural endividado junto a instituição financeira. |
| `maldonado-jurimetria.md` | **Jurimetria / "cérebro" do escritório** — estima probabilidade de êxito por tese/tribunal, mapeia perfil de magistrados do TJRO, estrutura o banco de teses (vault Obsidian). | Antes de aceitar um caso novo, ou para definir a linha recursal de um caso em andamento. |
| `maldonado-controladoria.md` | **Triagem de intimações/publicações e novas ações** — identifica a providência cabível, a peça necessária e prepara a delegação. | Toda vez que chegar uma intimação/publicação, ou um caso novo que precisa ser classificado antes de virar peça. |

> Os 3 juntos cobrem as 3 frentes do contrato fechado em 12/08/2026 (palavras do Dr. Renan): produção de peças, jurimetria via Obsidian e automação/métricas da controladoria. A automação **de verdade** da controladoria (captura automática de intimações + criação de tarefa no ADVBOX, sem colar texto manualmente) depende de credenciais (token ADVBOX + OABs a monitorar via DJEN) — ver a seção "Automação real" dentro de `maldonado-controladoria.md`.

### Skill empacotada (Claude.ai)

Skills ficam disponíveis na conta inteira (não só em um Project) — o Claude as invoca automaticamente conforme o pedido. Para empacotar, abra um chat **novo** no Claude.ai (Chrome ou app) e **cole o prompt abaixo**. O Claude responde com um pacote pronto para instalação.

| Arquivo (prompt) | Nome da skill que será criada | Quando o Claude vai invocar sozinho |
|---|---|---|
| `prompt-criar-skill-timbrado.md` | `timbrado-maldonado` | Toda vez que precisar gerar um DOCX no papel timbrado oficial do escritório. |

> **Instale a skill `timbrado-maldonado` antes de usar o Project para gerar DOCX final.** Antes de instalar, suba no Drive um arquivo `TIMBRADO_MALDONADO.docx` com o cabeçalho/rodapé oficiais (o header/footer da Procuração ou do Contrato de Honorários que a Dra. Juliana já mandou servem de referência visual exata).

**Por que ter os dois formatos?**
- **Custom Instructions** dá controle máximo dentro de um Project (permite subir base de conhecimento dedicada: as 3 peças-modelo, o timbrado, o contrato de honorários).
- **Skill** funciona em qualquer conversa da conta, e é invocada automaticamente quando alguém pede algo que se encaixe na descrição.

## Pré-requisitos

- Conta Claude.ai do Dr. Renan / Dra. Juliana / equipe jurídica
- **Plano Claude Pro ou Max** (Projects não estão disponíveis no plano Free)

## Passo a passo

### 1. Criar os 3 Projects

Para **cada agente**, repita:

1. Abra https://claude.ai
2. No menu lateral esquerdo, clique em **"Projects"**
3. Clique em **"+ Create Project"** (canto superior direito)
4. Preencha conforme a tabela:

| Arquivo `.md` | Nome do Project | Descrição |
|---|---|---|
| `maldonado-divida-rural.md` | **Maldonado — Dívida Rural** | Especialista em prorrogação de crédito rural, descaracterização de mora (Tema 28/STJ) e ação revisional bancária, no padrão do escritório Maldonado Advogados. |
| `maldonado-jurimetria.md` | **Maldonado — Jurimetria** | Estima probabilidade de êxito por tese/tribunal, mapeia perfil de magistrados do TJRO e estrutura o banco de teses. |
| `maldonado-controladoria.md` | **Maldonado — Controladoria** | Triagem de intimações/publicações e novas ações — identifica a providência cabível e a peça necessária. |

5. Clique em **"Create"**

> **Boas práticas:** um Project separado para cada agente — cada um tem foco diferente e responde melhor isolado.

### 2. Configurar as instruções (Custom Instructions)

Para cada Project:

1. Dentro do Project, clique em **"⚙️ Set Instructions"** (ou "Custom Instructions" — o nome muda conforme a versão)
2. Abra o arquivo `.md` correspondente em `.claude/agents/`
3. **Pule as primeiras linhas** entre `---` (o bloco frontmatter, com `name:` / `description:` / `model:`)
4. Cole **todo o resto do arquivo** — começando pelo primeiro `# Título`
5. Clique em **"Save"**

### 3. Subir base de conhecimento (essencial)

**Para o Project "Dívida Rural" (prioridade alta):**
- As **3 peças-modelo reais** já enviadas pela Dra. Juliana (ação de prorrogação, ação declaratória de descaracterização de mora, ação revisional) — estão em `DOCS_MODELOS/` (raiz do repositório).
- O **timbrado** (Procuração ou Contrato de Honorários servem de referência de identidade visual — também em `DOCS_MODELOS/`).
- Qualquer **contrato bancário real de cliente** (com dados sensíveis anonimizados, se for testar fora do ambiente do escritório).

**Para o Project "Jurimetria":**
- As mesmas 3 peças-modelo (para conhecer as teses).
- Decisões/sentenças já obtidas pelo escritório em casos de dívida rural (quando disponíveis) — vira a base inicial do banco de teses.
- Material dos "casos do Dr. Rogério Augusto" quando o Dr. Renan compartilhar.

**Para o Project "Controladoria":**
- As 3 peças-modelo (para saber apontar a peça certa).
- Exemplos reais de intimação/publicação do DJE que a equipe já recebeu (para calibrar o formato de leitura).

> Essencial mínimo no Project de Dívida Rural: **as 3 peças-modelo** + **o timbrado**. Sem isso o agente não reproduz o padrão técnico do escritório (distinção juros compostos x capitalização, estrutura em tópicos numerados da revisional etc.).

### 4. Testar

**Dívida Rural:**
> "Cliente produtor rural, CPR nº [X], Banco do Brasil, valor R$ 400.000, vencimento 15/03/2026, taxa de juros 18% a.a., sem cláusula expressa de capitalização no contrato. Cliente já está negativado e tem uma ação de execução em curso. Ele quer suspender a cobrança e discutir os juros. Qual ação cabe e monta a peça."

Esperado: o agente primeiro confirma qual das 3 teses cabe (aqui, provavelmente descaracterização de mora — juros acima de 12% a.a. — combinada com pedido de tutela, ou revisional se o cliente quiser recálculo), pergunta o que falta antes de redigir, e ao redigir aplica a estrutura correta (endereçamento Porto Velho/RO, distinção técnica juros compostos x capitalização, súmulas 539/541/298/286-STJ, Tema 28), terminando com "Peça pronta para revisão. Não protocolei."

**Jurimetria:**
> "Caso novo: produtor rural com CCB no [Banco], taxa 22% a.a., sem cláusula expressa de capitalização, ainda não distribuído. Vara Cível de Porto Velho, juiz ainda não sorteado. Vale a pena aceitar? Qual tese tem melhor prognóstico?"

Esperado: aplica a metodologia de 8 passos, é transparente sobre a falta de dado de magistrado (ainda não sorteado), recomenda a tese com base nos precedentes do TJRO que encontrar (ou diz que não achou), entrega relatório + nota pronta para o vault Obsidian.

**Controladoria:**
> "Cola aqui uma intimação: [texto de uma publicação do DJE informando decisão que rejeitou tutela de urgência em ação revisional, com prazo de 15 dias para agravo]."

Esperado: devolve o bloco de triagem padrão (processo, tipo de ato, providência cabível = agravo de instrumento, prazo calculado como preliminar, prioridade alta), sem protocolar nem mover nada.

## Variação para Claude Code (avançado — já pronto neste repositório)

Os 3 agentes já estão em `.claude/agents/` na raiz deste repositório — o Claude Code reconhece
automaticamente (frontmatter `---` mantido). Isso permite usá-los junto com os comandos reais
(`OPERACIONAL/main.py triagem`, etc.), lendo/gerando arquivos direto no repositório, além de usá-los
como Custom Instructions no Claude.ai.

---

## Roadmap (fases combinadas com o Dr. Renan/Dra. Juliana)

1. **Fase 1 — Produção de peças** (este pacote): agente + skill de timbrado para as 3 ações de dívida rural.
2. **Fase 2 — Jurimetria via Obsidian**: "cérebro" do escritório com estudo estratégico de juízes/decisões do TJRO, espelhando os casos do Dr. Rogério Augusto (referência citada pelo Dr. Renan).
3. **Fase 3 — Controladoria automatizada**: triagem de intimações (processos em andamento) + novas ações iniciais, eliminando a necessidade de 2 controllers dedicadas.

## Manutenção

- **Atualizar o agente:** edite `maldonado-divida-rural.md` e cole novamente nas Custom Instructions.
- **Adicionar nova peça modelo:** suba na knowledge base do Project — o agente passa a usar imediatamente.
- **Bug ou ajuste fino:** abra um chamado com a equipe de implantação.
