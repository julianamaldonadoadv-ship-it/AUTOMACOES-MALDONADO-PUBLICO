# VPS Hostinger — onde as rotinas diárias rodam

> Responde ao item **G1b** do `docs/LEVANTAMENTO_FLUXO_INTIMACOES.md` ("qual servidor,
> concretamente?"). O escritório contratou uma VPS na Hostinger; este diretório é a
> camada de deploy dela.

**Por que sair do Mac.** Hoje a apuração do KPI roda no Mac da Dra. Juliana via `launchd`
(`deploy/com.maldonado.kpi.plist`). Isso tem três problemas que a VPS resolve:

| No Mac | Na VPS |
|---|---|
| Mac desligado às 08:00 = **rodada perdida e não reposta** (`StartCalendarInterval` não replica) | `Persistent=true` no timer: a rodada roda assim que a máquina volta |
| A automação depende de uma pessoa deixar o notebook ligado | Servidor ligado 24/7 |
| Não dá para receber webhook do Sync (sem IP público) | IP público — abre caminho para o receptor de intimação em tempo real |

O Mac continua sendo a **fonte da verdade do código** e o lugar de trabalhar peça. A VPS
só roda as rotinas agendadas.

---

## O que roda na VPS

| Rotina | Horário | Unit | Grava? |
|---|---|---|---|
| **Intimações** (POP-CJ-003) — triagem, roteamento por controller, D-5/D-3, plano de tarefas | seg–sex **08:00** | `maldonado-intimacoes.timer` | **Não** (simulação é o padrão) |
| **KPI de êxito** — apuração da competência inteira + relatórios | seg–sex **08:20** | `maldonado-kpi.timer` | Nunca (somente leitura) |
| **Saúde** — "está de pé e rodou hoje?" | sob demanda | `saude.sh` | Nunca |

A rotina de intimações nasce em **simulação**: monta tudo e não grava nada no ADVBOX nem
no Zeus. É a semana de simulação combinada com a Dra. Juliana — primeiro a automação prova
que acerta contra o que as controllers fariam à mão, depois ganha autonomia (passo 7).
**Protocolo continua sendo nunca**, em qualquer modo (POP-CJ-PROT-001).

---

## Instalação

### Antes de criar a VPS — conferir o Mac

```bash
bash deploy/vps/subir.sh --conferir
```

Não precisa de VPS nenhuma. Diz o que falta no Mac e **imprime a chave pública** para você
colar no painel da Hostinger no passo 1. Resolva os `[X]` antes de criar a máquina.

### Depois que a VPS existir — um comando

```bash
bash deploy/vps/subir.sh
```

Faz tudo: prova a conexão → provisiona → envia o código → copia as credenciais (pergunta
antes) → instala os timers → roda a checagem de saúde. É **idempotente**: parou no meio,
rode de novo. Depois da primeira vez, o comando do dia a dia é `enviar.sh`.

Os passos abaixo detalham o que ele faz — leia se algo falhar, ou se preferir ir a pé.

---

### 1. Criar a VPS na Hostinger
Painel hPanel → **VPS** → criar. Escolhas que importam:
- **SO: Ubuntu 24.04 LTS** (limpo, sem painel). Os scripts assumem `apt` + `systemd`.
- **Plano:** o menor já resolve — a rotina é I/O de API, não CPU. 1 vCPU / 4 GB sobra.
- **Localização:** Brasil, se houver; senão EUA. Não muda nada funcional.
- **Chave SSH:** cadastre a chave pública do Mac **na criação** (evita senha depois).
  No Mac, se ainda não existir: `ssh-keygen -t ed25519` e cole o conteúdo de
  `~/.ssh/id_ed25519.pub`.

Anote o **IP** que a Hostinger mostrar — é a única coisa que falta para subir.

> **Se ainda não houver chave SSH no Mac**, crie ANTES de criar a VPS (assim ela já nasce
> com a chave e você nunca digita senha):
> ```bash
> ssh-keygen -t ed25519 -C 'maldonado-automacao'   # Enter nas três perguntas
> cat ~/.ssh/id_ed25519.pub                        # cole isto na Hostinger
> ```
>
> **Não** habilite painel (CyberPanel, hPanel add-ons) nem Docker no assistente: eles trazem
> serviço web ouvindo na internet, e esta VPS não serve página nenhuma — ela só *chama* API.
> Quanto menos porta aberta, melhor, num servidor que guarda token do ADVBOX e do Google.

### 2. Provisionar (o `subir.sh` já faz; à mão seria assim)
```bash
ssh root@SEU_IP 'bash -s' < deploy/vps/provisionar.sh
```
Faz: fuso **America/Porto_Velho**, usuário de serviço `maldonado` (a automação **não**
roda como root), Python + venv, Chromium (motor de PDF), pastas em
`/opt/maldonado/automacoes`.

> **O fuso é o detalhe que mais quebra.** VPS nasce em UTC; sem o `timedatectl`, o
> timer das "08:00" dispara às **04:00** no horário de Porto Velho, antes de o DJEN
> publicar o dia.

### 3. Apontar o Mac para a VPS
Em `config/.env` (no Mac), preencha o bloco `VPS_*`:
```
VPS_HOST=123.45.67.89
VPS_USUARIO=maldonado
VPS_CAMINHO=/opt/maldonado/automacoes
VPS_PORTA_SSH=22
```

### 4. Copiar as credenciais — **à mão, uma vez só**
As credenciais **nunca** viajam no deploy (o `enviar.sh` exclui todas). Copie você mesma:
```bash
scp config/.env            maldonado@SEU_IP:/opt/maldonado/automacoes/config/
scp config/token.json      maldonado@SEU_IP:/opt/maldonado/automacoes/config/
scp config/oauth_credentials.json maldonado@SEU_IP:/opt/maldonado/automacoes/config/
ssh maldonado@SEU_IP 'chmod 600 /opt/maldonado/automacoes/config/*'
```

> **O `token.json` tem que ser gerado no Mac e copiado.** O login do Google abre
> navegador (`run_local_server`), e a VPS não tem tela. O token copiado se renova
> sozinho — **desde que** o app OAuth do escritório esteja **publicado** no Google
> Cloud, e não em "Testing": em modo de teste o Google invalida o refresh token a
> cada **7 dias** e a rotina para de arquivar no Zeus toda semana.
>
> Enquanto o Drive não estiver resolvido na VPS, a rotina roda igual — só não arquiva
> o relatório no Zeus (o `saude.sh` avisa).

### 5. Enviar o código (o `subir.sh` já faz; depois é este o comando do dia a dia)
```bash
bash deploy/vps/enviar.sh --simular   # mostra o que iria
bash deploy/vps/enviar.sh             # envia, instala deps e liga os timers
```

### 6. Conferir
```bash
ssh maldonado@SEU_IP 'bash /opt/maldonado/automacoes/deploy/vps/saude.sh'
ssh maldonado@SEU_IP 'systemctl list-timers maldonado-* --no-pager'
# forçar uma rodada agora, sem esperar as 08:00:
ssh SEU_IP 'sudo systemctl start maldonado-intimacoes.service'
ssh maldonado@SEU_IP 'tail -60 /opt/maldonado/automacoes/_trabalho/logs/rotina_intimacoes.log'
```

### 7. Liberar a gravação — só depois da semana de simulação
No `.env` **da VPS** (não no do Mac):
```bash
ssh maldonado@SEU_IP
nano /opt/maldonado/automacoes/config/.env    # VPS_ROTINA_GRAVAR=1
```
A decisão fica escrita no servidor, com data — não no histórico de quem rodou o comando.

---

## Rotina de conferência diária

```bash
bash deploy/vps/saude.sh
```
Sai com status **0** se estiver tudo certo e **1** se houver `[X]`, e confere: fuso,
credenciais e permissão, bibliotecas, Chromium, timers habilitados, idade do último log,
`[FALHA]` na última rodada, conexão com o ADVBOX e em que modo a rotina está.

Log das rodadas, nos dois lugares:
```bash
tail -40 _trabalho/logs/rotina_intimacoes.log
journalctl -u maldonado-intimacoes.service --since today
```

---

## Armadilhas (não desfazer)

- **Fuso.** `America/Porto_Velho` (UTC-4). Ver passo 2.
- **`enviar.sh` é `rsync --delete`:** o que sumir do Mac some da VPS. É de propósito — o
  Mac manda no código. As exclusões (`config/` secreto, `_trabalho/`, `BASE_CONHECIMENTO/`)
  existem para que um envio errado nunca apague o token bom nem os relatórios da VPS.
- **`BASE_CONHECIMENTO/` e `_trabalho/` não vão para a VPS** — são nome de cliente e
  processo reais. A VPS tem o `_trabalho/` dela, que ela mesma gera.
- **As duas rotinas não disparam juntas** (08:00 e 08:20): o DJEN alterna "sistema ocupado"
  e falso-vazio, e bater nele duas vezes no mesmo segundo piora. O `RandomizedDelaySec=300`
  espalha mais um pouco.
- **Falha de rodada não derruba o agendamento** — `Restart=on-failure` tenta 3x com 10 min
  de intervalo, e o resto fica no log. Falso-vazio do DJEN é rotina, não incidente.
- **`ProtectSystem=strict` nos units:** a automação só escreve em `_trabalho/` e `docs/`.
  Se um comando novo precisar escrever em outro lugar, é preciso somar o caminho em
  `ReadWritePaths` — senão falha com "read-only file system".
- **O `.plist` do Mac continua lá.** Rodando as duas máquinas, o KPI é apurado duas vezes
  (é somente leitura, então não estraga nada — mas polui). Com a VPS estável, descarregue
  o do Mac: `launchctl unload ~/Library/LaunchAgents/com.maldonado.kpi.plist`.

---

## O que a VPS destrava depois

**Receptor de webhook do Sync.** `INTEGRACOES/sync_integration.py` já valida a assinatura
HMAC (`X-Webhook-Signature`), mas não há servidor HTTP para receber o POST — porque no Mac
não havia URL pública. Com a VPS existe. Falta decidir domínio e TLS (Caddy resolve em
duas linhas) antes de construir; a API do Sync recusa IP privado como destino.

Isso mudaria a intimação de **rodada das 08:00** para **tempo real**. Fica para depois de a
rotina agendada estar provada.
