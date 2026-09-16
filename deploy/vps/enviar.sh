#!/bin/bash
# =============================================================================
#  ENVIO DO PROJETO PARA A VPS - Maldonado Advogados
# =============================================================================
#
#  Roda NO MAC, da raiz do projeto:
#
#      bash deploy/vps/enviar.sh              # envia e reinstala os timers
#      bash deploy/vps/enviar.sh --simular    # mostra o que enviaria, nao envia
#
#  Le o destino de config/.env (bloco VPS_*):
#      VPS_HOST=123.45.67.89
#      VPS_USUARIO=maldonado
#      VPS_CAMINHO=/opt/maldonado/automacoes
#      VPS_PORTA_SSH=22
#
#  O QUE NUNCA VAI NO ENVIO (e por que):
#    config/.env, credentials.json, token.json  -> credencial nao trafega em
#        deploy; e' copiada uma vez, a mao, com permissao 600 (README passo 4).
#        Assim um envio errado nunca sobrescreve o token bom da VPS.
#    _trabalho/          -> documento real de cliente e log; a VPS tem o dela.
#    BASE_CONHECIMENTO/  -> vault com nome de cliente e processo reais.
#    .git/, __pycache__, .venv/
#
#  E' rsync --delete: o que sumir do Mac some da VPS (menos o que esta excluido
#  acima). E' de proposito - o Mac e' a fonte da verdade do codigo.
# =============================================================================
set -euo pipefail

PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJETO"

SIMULAR=""
[ "${1:-}" = "--simular" ] && SIMULAR="--dry-run"

# ---- destino ---------------------------------------------------------------
if [ -f config/.env ]; then
  # shellcheck disable=SC1091
  set -a; . <(grep -E '^VPS_[A-Z_]+=' config/.env || true); set +a
fi
HOST="${VPS_HOST:-}"
USUARIO="${VPS_USUARIO:-maldonado}"
DESTINO="${VPS_CAMINHO:-/opt/maldonado/automacoes}"
PORTA="${VPS_PORTA_SSH:-22}"
ADMIN="${VPS_USUARIO_ADMIN:-root}"

if [ -z "$HOST" ]; then
  cat >&2 <<'MSG'
ERRO: VPS_HOST nao configurado.

Preencha em config/.env (copie o bloco de config/.env.example):
    VPS_HOST=
    VPS_USUARIO=maldonado
    VPS_CAMINHO=/opt/maldonado/automacoes
    VPS_PORTA_SSH=22
MSG
  exit 1
fi

SSH="ssh -p $PORTA"
ALVO="$USUARIO@$HOST"

echo "==> Enviando $PROJETO"
echo "    para $ALVO:$DESTINO  (porta $PORTA)${SIMULAR:+  [SIMULACAO]}"
echo

rsync -az --delete $SIMULAR -e "$SSH" \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.venv/' --exclude 'venv/' \
  --exclude '_trabalho/' \
  --exclude 'BASE_CONHECIMENTO/' \
  --exclude 'config/.env' \
  --exclude 'config/credentials.json' \
  --exclude 'config/oauth_credentials.json' \
  --exclude 'config/token*.json' \
  --exclude '.DS_Store' \
  --itemize-changes \
  ./ "$ALVO:$DESTINO/"

if [ -n "$SIMULAR" ]; then
  echo
  echo "SIMULACAO - nada foi enviado."
  exit 0
fi

echo
echo "==> Dependencias Python na VPS (venv)"
$SSH "$ALVO" "cd '$DESTINO' && (test -d .venv || python3 -m venv .venv) && \
  ./.venv/bin/pip install -q --upgrade pip wheel && \
  ./.venv/bin/pip install -q -r requirements.txt && echo '    ok'"

echo
echo "==> Timers (systemd)"
# Instalar unit e' coisa de root, e `maldonado` e' usuario de SERVICO (sem sudo,
# de proposito - quem le processo de cliente nao precisa de privilegio). Por isso
# este passo abre uma conexao separada com o usuario administrativo.
if $SSH "$ADMIN@$HOST" "install -m 644 '$DESTINO'/deploy/vps/systemd/*.service '$DESTINO'/deploy/vps/systemd/*.timer /etc/systemd/system/ && \
    systemctl daemon-reload && \
    systemctl enable --now maldonado-intimacoes.timer maldonado-kpi.timer && \
    systemctl list-timers 'maldonado-*' --no-pager" 2>/dev/null; then
  :
else
  echo "    [!] nao consegui entrar como $ADMIN@$HOST - instale os units a mao:"
  echo "        ssh $ADMIN@$HOST"
  echo "        install -m 644 $DESTINO/deploy/vps/systemd/*.service $DESTINO/deploy/vps/systemd/*.timer /etc/systemd/system/"
  echo "        systemctl daemon-reload"
  echo "        systemctl enable --now maldonado-intimacoes.timer maldonado-kpi.timer"
fi

echo
echo "PRONTO. Conferir a proxima rodada:"
echo "    ssh $ALVO 'systemctl list-timers maldonado-* --no-pager'"
echo "    ssh $ALVO 'bash $DESTINO/deploy/vps/saude.sh'"
