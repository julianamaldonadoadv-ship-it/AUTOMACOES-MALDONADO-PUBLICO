#!/bin/bash
# =============================================================================
#  SUBIR A AUTOMACAO PARA A VPS - Maldonado Advogados  (primeira instalacao)
# =============================================================================
#
#  UM comando, rodado NO MAC, da raiz do projeto:
#
#      bash deploy/vps/subir.sh --conferir   # confere o Mac. NAO precisa da VPS.
#      bash deploy/vps/subir.sh              # instala tudo na VPS
#
#  Faz, em ordem: confere o Mac -> prova a conexao -> provisiona a VPS ->
#  envia o codigo -> copia as credenciais (pergunta antes) -> instala os timers
#  -> roda a checagem de saude.
#
#  E' IDEMPOTENTE: rodar de novo nao estraga nada (reaproveita usuario, venv e
#  pastas; so reinstala o que mudou). Se parar no meio, rode de novo.
#
#  Depois da primeira vez, o comando do dia a dia e'  deploy/vps/enviar.sh.
#
#  O QUE ELE NAO FAZ: nao cria a VPS (isso e' no painel da Hostinger, passo 1 do
#  README) e nao libera a gravacao no ADVBOX (a rotina sobe em simulacao).
# =============================================================================
set -uo pipefail

PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJETO" || exit 1

CONFERIR=""
[ "${1:-}" = "--conferir" ] && CONFERIR="1"

PROBLEMAS=0
ok()     { echo "  [ok] $1"; }
alerta() { echo "  [!]  $1"; }
falha()  { echo "  [X]  $1"; PROBLEMAS=$((PROBLEMAS+1)); }
titulo() { echo; echo "-- $1"; }

echo "==============================================================="
echo "  Subir automacao para a VPS${CONFERIR:+  [SO CONFERENCIA - nada sera enviado]}"
echo "  $(date '+%d/%m/%Y %H:%M')"
echo "==============================================================="

# ============================================================
#  ETAPA 1 - o que da' para conferir sem a VPS existir
# ============================================================
titulo "1. Chave SSH do Mac"
CHAVE=""
for c in ~/.ssh/id_ed25519.pub ~/.ssh/id_rsa.pub; do
  [ -f "$c" ] && { CHAVE="$c"; break; }
done
if [ -n "$CHAVE" ]; then
  ok "$CHAVE"
  echo "       cole ESTA linha no campo 'SSH Key' da Hostinger:"
  echo
  sed 's/^/       /' "$CHAVE"
  echo
else
  falha "nenhuma chave SSH no Mac. Crie antes de criar a VPS:"
  echo "       ssh-keygen -t ed25519 -C 'maldonado-automacao'"
  echo "       (aperte Enter nas tres perguntas)"
fi

titulo "2. Credenciais que a VPS vai precisar"
if [ -f config/.env ]; then
  ok "config/.env existe"
  if grep -qE "^ADVBOX_API_TOKEN=.+" config/.env; then ok "ADVBOX_API_TOKEN preenchido"
  else falha "ADVBOX_API_TOKEN vazio - a rotina nao roda sem ele"; fi
  # As OABs do DJEN saem de config/equipe.py (OABS_MONITORADAS); DJEN_OAB_LISTA
  # no .env e' so o fallback de quem nao tem equipe.py (ver main._oabs_monitoradas).
  # Por isso a conferencia pergunta ao codigo qual e' o resultado efetivo: olhar so
  # o .env acusava "vazio" num escritorio que tem as OABs no equipe.py.
  # Importa `equipe` direto, e nao `main`, porque equipe.py nao depende de nada
  # externo - com `main` a conferencia falharia so por falta de python-dotenv.
  N_OABS="$(python3 - <<'PYOAB' 2>/dev/null
import os, sys
sys.path.insert(0, 'config')
n = 0
try:
    import equipe
    n = len(equipe.OABS_MONITORADAS or [])
except Exception:
    pass
if not n:
    try:
        for linha in open('config/.env', encoding='utf-8'):
            if linha.startswith('DJEN_OAB_LISTA='):
                n = len([x for x in linha.split('=', 1)[1].split(',') if '-' in x])
    except Exception:
        pass
print(n)
PYOAB
)"
  if [ "${N_OABS:-0}" -gt 0 ] 2>/dev/null; then
    ok "$N_OABS OAB(s) monitorada(s) no DJEN"
  else
    falha "nenhuma OAB monitorada (config/equipe.py OABS_MONITORADAS ou DJEN_OAB_LISTA)"
  fi
  for chave in SYNC_API_TOKEN ATENDE_DIREITO_API_TOKEN; do
    grep -qE "^${chave}=.+" config/.env && ok "$chave preenchido (vai junto)" \
      || alerta "$chave vazio - a integracao correspondente fica inativa na VPS"
  done
else
  falha "config/.env nao existe (copie de config/.env.example e preencha)"
fi
if [ -f config/token.json ]; then
  ok "config/token.json existe (Google Drive)"
else
  alerta "config/token.json ausente - rode 'python OPERACIONAL/main.py drive autenticar'"
  alerta "  no MAC antes de subir: a VPS nao tem tela para abrir o login do Google"
fi

titulo "3. Destino (bloco VPS_* do config/.env)"
if [ -f config/.env ]; then
  set -a; . <(grep -E '^VPS_[A-Z_]+=' config/.env || true); set +a
fi
HOST="${VPS_HOST:-}"
USUARIO="${VPS_USUARIO:-maldonado}"
DESTINO="${VPS_CAMINHO:-/opt/maldonado/automacoes}"
PORTA="${VPS_PORTA_SSH:-22}"
ADMIN="${VPS_USUARIO_ADMIN:-root}"
if [ -n "$HOST" ]; then
  ok "VPS_HOST=$HOST  usuario=$USUARIO  admin=$ADMIN  porta=$PORTA"
  ok "destino: $DESTINO"
else
  if [ -n "$CONFERIR" ]; then
    alerta "VPS_HOST ainda vazio - normal, a VPS nao foi criada. Preencha depois."
  else
    falha "VPS_HOST vazio em config/.env - sem isso nao ha para onde subir"
  fi
fi

titulo "4. Arquivos da camada de deploy"
for f in deploy/vps/provisionar.sh deploy/vps/enviar.sh deploy/vps/saude.sh \
         deploy/vps/rotina_intimacoes.sh deploy/kpi_diario.sh \
         deploy/vps/systemd/maldonado-intimacoes.service \
         deploy/vps/systemd/maldonado-intimacoes.timer \
         deploy/vps/systemd/maldonado-kpi.service \
         deploy/vps/systemd/maldonado-kpi.timer; do
  [ -f "$f" ] && ok "$(basename "$f")" || falha "falta $f"
done
for f in deploy/vps/*.sh deploy/kpi_diario.sh; do
  bash -n "$f" 2>/dev/null || falha "erro de sintaxe em $f"
done

if [ -n "$CONFERIR" ]; then
  echo
  echo "==============================================================="
  if [ "$PROBLEMAS" -eq 0 ]; then
    echo "  O Mac esta pronto. Assim que a VPS existir:"
    echo "    1. preencha VPS_HOST em config/.env"
    echo "    2. bash deploy/vps/subir.sh"
  else
    echo "  $PROBLEMAS item(ns) com [X] - resolver antes de subir."
  fi
  echo "==============================================================="
  exit $(( PROBLEMAS > 0 ? 1 : 0 ))
fi

if [ "$PROBLEMAS" -gt 0 ]; then
  echo
  echo "  $PROBLEMAS item(ns) com [X]. Corrija e rode de novo."
  exit 1
fi

# ============================================================
#  ETAPA 2 - daqui para baixo, precisa da VPS no ar
# ============================================================
SSH_ADMIN="ssh -p $PORTA -o ConnectTimeout=15"
SSH_SVC="ssh -p $PORTA -o ConnectTimeout=15"

titulo "5. Conexao com a VPS"
if $SSH_ADMIN "$ADMIN@$HOST" 'echo conectado' >/dev/null 2>&1; then
  ok "$ADMIN@$HOST responde"
else
  echo "  [X] nao consegui entrar como $ADMIN@$HOST."
  echo "      - a VPS ja terminou de subir no painel da Hostinger?"
  echo "      - a chave publica do Mac foi cadastrada nela?"
  echo "      - o IP em VPS_HOST esta certo?"
  exit 1
fi

titulo "6. Provisionamento (fuso, usuario, Python, Chromium)"
$SSH_ADMIN "$ADMIN@$HOST" "MALDONADO_USER='$USUARIO' MALDONADO_BASE='$DESTINO' bash -s" \
  < deploy/vps/provisionar.sh || { echo "  [X] provisionamento falhou"; exit 1; }

titulo "7. Envio do codigo"
rsync -az --delete -e "$SSH_SVC" \
  --exclude '.git/' --exclude '__pycache__/' --exclude '*.pyc' \
  --exclude '.venv/' --exclude 'venv/' \
  --exclude '_trabalho/' --exclude 'BASE_CONHECIMENTO/' \
  --exclude 'config/.env' --exclude 'config/credentials.json' \
  --exclude 'config/oauth_credentials.json' --exclude 'config/token*.json' \
  --exclude '.DS_Store' \
  ./ "$USUARIO@$HOST:$DESTINO/" || { echo "  [X] rsync falhou"; exit 1; }
ok "codigo enviado"

titulo "8. Credenciais"
echo "  Vao para $HOST:$DESTINO/config/ com permissao 600:"
for f in config/.env config/token.json config/oauth_credentials.json config/credentials.json; do
  [ -f "$f" ] && echo "      $f"
done
echo
read -r -p "  Copiar as credenciais para a VPS? [s/N] " RESP
# ${RESP,,} seria mais curto, mas e' bash 4+ e o Mac do escritorio roda bash 3.2.
case "$RESP" in
  s|S|sim|SIM|Sim)
  for f in config/.env config/token.json config/oauth_credentials.json config/credentials.json; do
    [ -f "$f" ] && scp -P "$PORTA" -q "$f" "$USUARIO@$HOST:$DESTINO/config/" && ok "$(basename "$f")"
  done
  $SSH_SVC "$USUARIO@$HOST" "chmod 600 $DESTINO/config/* 2>/dev/null; chmod 700 $DESTINO/config"
    ok "permissoes ajustadas (600)"
    ;;
  *)
    alerta "pulado - a rotina NAO roda sem config/.env na VPS. Copie depois:"
    echo "       scp config/.env $USUARIO@$HOST:$DESTINO/config/"
    ;;
esac

titulo "9. Dependencias Python"
$SSH_SVC "$USUARIO@$HOST" "cd '$DESTINO' && (test -d .venv || python3 -m venv .venv) && \
  ./.venv/bin/pip install -q --upgrade pip wheel && ./.venv/bin/pip install -q -r requirements.txt" \
  && ok "venv pronto" || falha "instalacao das dependencias falhou"

titulo "10. Timers"
$SSH_ADMIN "$ADMIN@$HOST" "install -m 644 $DESTINO/deploy/vps/systemd/*.service $DESTINO/deploy/vps/systemd/*.timer /etc/systemd/system/ && \
  systemctl daemon-reload && \
  systemctl enable --now maldonado-intimacoes.timer maldonado-kpi.timer && \
  systemctl list-timers 'maldonado-*' --no-pager" \
  && ok "timers ativos" || falha "instalacao dos timers falhou"

titulo "11. Checagem de saude"
$SSH_SVC "$USUARIO@$HOST" "bash $DESTINO/deploy/vps/saude.sh"

echo
echo "==============================================================="
echo "  SUBIDA CONCLUIDA."
echo
echo "  A rotina de intimacoes esta em SIMULACAO: as 08:00 ela monta"
echo "  triagem, D-5/D-3 e o plano de tarefas, e NAO grava no ADVBOX."
echo
echo "  Rodar agora, sem esperar as 08:00:"
echo "    ssh $ADMIN@$HOST 'systemctl start maldonado-intimacoes.service'"
echo "    ssh $USUARIO@$HOST 'tail -60 $DESTINO/_trabalho/logs/rotina_intimacoes.log'"
echo
echo "  Atualizar o codigo depois:  bash deploy/vps/enviar.sh"
echo "==============================================================="
