# Onboarding — Maldonado Advogados

Checklist para colocar o sistema rodando. A prioridade é o **Squad Controladoria**
(comando `triagem`) — é o que resolve o gargalo das 2 controllers mais rápido.

## 1. Instalar dependências

Escritório com máquinas Windows e Mac — use o instalador do seu sistema (repositório:
`https://github.com/<organizacao>/<repositorio>`):

**Windows** (duplo clique ou terminal):
```bat
deploy\instalar_windows.bat
```

**Mac:**
```bash
chmod +x deploy/instalar_mac.sh
./deploy/instalar_mac.sh
```

Isso já cria o ambiente virtual, instala as dependências e copia `config/.env.example` para
`config/.env`. Se preferir fazer manualmente, ver o passo a passo em `README.md`.

## 2. Configurar `config/.env`

O instalador (passo 1) já criou o arquivo a partir do modelo. Preencher, nesta ordem de prioridade:

| Variável | Onde conseguir | Prioridade |
|---|---|---|
| `ADVBOX_API_TOKEN` | Painel ADVBOX do escritório → Configurações → API | **Crítica** — sem isso nada funciona (nem `tarefas`, nem `triagem`, nem `processos`) |
| `DJEN_OAB_LISTA` | OABs dos advogados do escritório, formato `NUMERO-UF` separado por vírgula (ex.: `5769-RO,13021-RO`) | **Crítica para o Squad Controladoria** — sem isso o comando `triagem` não busca nada |
| `GOOGLE_CONTA_ESCRITORIO` / `GOOGLE_OAUTH_CREDENTIALS` | Conta Google do escritório + credencial OAuth criada no Google Cloud Console — **passo a passo na seção 5 abaixo** | Necessária para o Google Drive (estrutura ZEUS), eventos de prazo na Agenda e o vault do Squad Jurimetria |
| `ANTHROPIC_API_KEY` | console.anthropic.com (conta do escritório) | Necessária se quiser rodar os agentes via API em vez de só Claude.ai/Claude Code |

## 3. Configurar `config/equipe.py`

Preencher `USUARIOS_ADVBOX` com os IDs reais (painel ADVBOX → Usuários → clicar no usuário → ID
aparece na URL) e `OABS_MONITORADAS` com as OABs a acompanhar no DJEN.

Conferir também o bloco **CONTROLLERS** — o mapa controller → advogados que define quem lança
(`from`) e quem recebe (`guests`) cada tarefa de intimação, mais `CONTROLLER_DA_DIRECAO` (quem
assume os processos da direção/gerência) e `CONTROLLER_FALLBACK` (quem assume responsável fora do
mapa). Tratamento de intimação é sempre de uma controller — a gerência jurídica não entra nessa
fila. `python OPERACIONAL/main.py advbox` confere controller por controller e advogado por
advogado contra a conta real; o `"id"` pode ficar `None` (o código resolve pelo nome), mas
preencher é mais seguro.

## 4. Testar a conexão com o ADVBOX

```
python -c "import sys; sys.path.insert(0,'INTEGRACOES'); from dotenv import load_dotenv; load_dotenv('config/.env'); import advbox_integration as a; print(a.testar_conexao())"
```

## 4.1 Conectar o Google Drive do escritório (credencial OAuth própria)

> A credencial tem que ser criada **na conta Google do escritório Maldonado**. Não reaproveite
> credencial de nenhuma outra conta (implantação, consultoria, conta pessoal): o token dá acesso
> de leitura **e escrita** ao Drive inteiro, e o sistema grava documento de cliente lá dentro.

**Passo 1 — criar o projeto e a credencial** (feito uma vez, logado na conta do escritório):

> Antes de clicar em qualquer link: confira, no canto superior direito do Console, que a conta
> logada é a **do escritório**. O Google abre o Console na última conta usada no navegador.

1. **Criar o projeto** — <https://console.cloud.google.com/projectcreate>
   Nome: `Maldonado Automacoes`. Depois de criar, confirme que ele está selecionado no seletor de
   projeto (barra superior) antes de seguir.

2. **Ativar as 4 APIs** — abra um link, clique em **Ativar**, volte e repita:
   - Drive — <https://console.cloud.google.com/apis/library/drive.googleapis.com>
   - Docs — <https://console.cloud.google.com/apis/library/docs.googleapis.com>
   - Sheets — <https://console.cloud.google.com/apis/library/sheets.googleapis.com>
   - Calendar — <https://console.cloud.google.com/apis/library/calendar-json.googleapis.com>

3. **Tela de permissão OAuth** — <https://console.cloud.google.com/auth/overview>
   (se o Console ainda mostrar o layout antigo: <https://console.cloud.google.com/apis/credentials/consent>)
   - Nome do app: `Maldonado Automacoes` | e-mail de suporte: o do escritório.
   - Tipo **Interno** se o escritório usa Google Workspace (domínio próprio) — mais simples, sem
     tela de aviso.
   - Tipo **Externo** se for Gmail comum: em **Público / Usuários de teste**, adicione os e-mails
     da equipe que vão usar o sistema. Sem isso o login é recusado.

4. **Criar o ID do cliente OAuth** — <https://console.cloud.google.com/auth/clients>
   (layout antigo: <https://console.cloud.google.com/apis/credentials/oauthclient>)
   - **Criar cliente** → Tipo de aplicativo: **App para computador** (Desktop app).
   - Nome: `Maldonado CLI`.

5. **Baixar o JSON** e salvar como `config/oauth_credentials.json` na pasta do projeto.
   O `.gitignore` já ignora esse arquivo — ele **nunca** vai para o GitHub.

**Passo 2 — apontar a conta no `.env`:**

```
GOOGLE_CONTA_ESCRITORIO=<e-mail da conta Google do escritório>
```

Isso é a trava de segurança: se o sistema for autenticado com qualquer outra conta, ele **aborta**
mostrando o e-mail encontrado, em vez de ler/gravar no Drive errado.

**Passo 3 — conectar:**

```
python OPERACIONAL/main.py drive autenticar
```

Abre o navegador uma única vez, você faz login **com a conta do escritório**, e o token fica em
`config/token.json` (também fora do Git).

**Passo 4 — conferir o acesso à ZEUS:**

```
python OPERACIONAL/main.py drive testar
```

Deve listar as pastas-índice (A, B, C...) dentro de `01 CLIENTES`. Se não achar, preencha
`DRIVE_PASTA_CLIENTES_ID` no `.env` com o ID da pasta `01 CLIENTES` (é o trecho final da URL
quando você abre a pasta no Drive).

**Trocar de conta / remover uma credencial errada:**

```
python OPERACIONAL/main.py drive sair
```

Revoga o acesso no Google e apaga o `config/token.json`. Depois é só rodar `drive autenticar` de
novo com a conta certa.

## 5. Rodar a primeira triagem (modo leitura, sem criar nada)

```
python OPERACIONAL/main.py triagem --dias 7
```

Isso já mostra o relatório de triagem das intimações da última semana, cruzadas com o ADVBOX —
**sem criar nem alterar nada**. Só depois de conferir que o relatório faz sentido, usar
`--criar-tarefa` (que ainda pede confirmação item a item).

## 6. Timbrado isolado

Subir em `DOCS_MODELOS/timbrado_modelo.docx` um arquivo com **apenas o cabeçalho e rodapé**
oficiais (logo, endereço, telefones, OAB) — sem conteúdo de peça. Hoje o timbrado real só existe
embutido na Procuração e no Contrato de Honorários que a Dra. Juliana já enviou; falta isolar.

## 7. Banco de teses (Squad Jurimetria)

Criar a pasta `BASE_CONHECIMENTO/` como vault Obsidian (ver estrutura sugerida em
`.claude/agents/maldonado-jurimetria.md`). Pode ser local (sincronizada por Drive/OneDrive) ou
direto numa pasta do Drive do escritório.

## 8. Instalar os agentes no Claude.ai (opcional, complementar ao Claude Code)

Ver `.claude/agents/` — os 3 arquivos (`maldonado-controladoria.md`, `maldonado-divida-rural.md`,
`maldonado-jurimetria.md`) também funcionam como Custom Instructions de Projects no Claude.ai.
Passo a passo completo em `docs/GUIA_INSTALACAO_CLAUDE_AI.md`.

## Pendências conhecidas (não bloqueiam o começo, mas faltam para o sistema completo)

- [ ] `DOCS_MODELOS/timbrado_modelo.docx` isolado.
- [ ] Credenciais reais: `ADVBOX_API_TOKEN`, `DJEN_OAB_LISTA`, Google (seção 4.1).
- [ ] `GOOGLE_CONTA_ESCRITORIO` preenchido — sem ele a trava de conta fica desligada.
- [ ] IDs em `config/equipe.py`.
- [ ] Definir onde fica o vault Obsidian (local vs. Drive).
- [ ] Confirmar com o escritório se querem geração de peça DOCX automática (via
      `google_integration.preencher_documento`, precisa de template com placeholders `{{CHAVE}}`)
      ou se preferem que a peça saia direto do chat do Claude (copiar/colar) por enquanto.
