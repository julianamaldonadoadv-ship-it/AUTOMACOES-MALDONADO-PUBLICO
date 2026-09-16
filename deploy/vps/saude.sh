#!/bin/bash
# =============================================================================
#  CHECAGEM DE SAUDE DA VPS - Maldonado Advogados
# =============================================================================
#
#  Responde a UMA pergunta: "a automacao esta de pe e rodou hoje?"
#
#      bash deploy/vps/saude.sh          # na VPS
#      ssh maldonado@IP 'bash /opt/maldonado/automacoes/deploy/vps/saude.sh'
#
#  Sai com status 0 se estiver tudo certo, 1 se houver [X]. E' isso que permite
#  usar o script em monitoramento depois.
#
#  Somente leitura: nao grava nada, nao chama a API do ADVBOX para escrever.
# =============================================================================
set -uo pipefail

PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJETO" || exit 1
FALHAS=0
ok()   { echo "  [ok] $1"; }
alerta(){ echo "  [!]  $1"; }
falha(){ echo "  [X]  $1"; FALHAS=$((FALHAS+1)); }

echo "==============================================================="
echo "  Saude da automacao - $(date '+%d/%m/%Y %H:%M %Z')"
echo "  $(hostname) | $PROJETO"
echo "==============================================================="

echo
echo "-- 1. Fuso horario"
TZ_ATUAL="$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null)"
if [ "$TZ_ATUAL" = "America/Porto_Velho" ]; then
  ok "America/Porto_Velho ($(date '+%H:%M'))"
else
  falha "fuso e' '$TZ_ATUAL', deveria ser America/Porto_Velho - o timer das 08:00 esta disparando na hora errada"
fi

echo
echo "-- 2. Credenciais (config/)"
for arq in config/.env; do
  if [ -f "$arq" ]; then
    PERM="$(stat -c '%a' "$arq" 2>/dev/null || stat -f '%Lp' "$arq")"
    if [ "$PERM" = "600" ] || [ "$PERM" = "400" ]; then ok "$arq (permissao $PERM)"
    else alerta "$arq com permissao $PERM - deveria ser 600 (chmod 600 $arq)"; fi
  else
    falha "$arq nao existe - a rotina nao tem token do ADVBOX nem do DJEN"
  fi
done
for chave in ADVBOX_API_TOKEN DJEN_OAB_LISTA; do
  if grep -qE "^${chave}=.+" config/.env 2>/dev/null; then ok "$chave preenchido"
  else falha "$chave vazio em config/.env"; fi
done
if [ -f config/token.json ]; then
  ok "config/token.json presente (Google Drive)"
else
  alerta "config/token.json ausente - a rotina roda, mas nao arquiva relatorio no Zeus"
fi

echo
echo "-- 3. Dependencias"
if [ -x "$PROJETO/.venv/bin/python" ]; then
  PY="$PROJETO/.venv/bin/python"; ok "venv em .venv"
else
  PY="$(command -v python3)"; alerta "sem .venv - usando $PY do sistema"
fi
FALTANDO="$("$PY" - <<'PYEOF' 2>/dev/null
mods = ['requests','dotenv','docx','fitz','markdown','dateutil','googleapiclient']
falta = []
for m in mods:
    try: __import__(m)
    except Exception: falta.append(m)
print(' '.join(falta))
PYEOF
)"
if [ -z "$FALTANDO" ]; then ok "bibliotecas Python completas"
else falha "faltam: $FALTANDO  (./.venv/bin/pip install -r requirements.txt)"; fi
if command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1 \
   || command -v google-chrome-stable >/dev/null 2>&1; then
  ok "Chromium presente (motor de PDF)"
else
  alerta "sem Chromium - 'kpi --pdf' gera o .md e falha no .pdf"
fi

echo
echo "-- 4. Timers"
for t in maldonado-intimacoes maldonado-kpi; do
  if systemctl is-enabled "$t.timer" >/dev/null 2>&1; then
    PROX="$(systemctl show "$t.timer" -p NextElapseUSecRealtime --value 2>/dev/null)"
    ok "$t.timer ativo - proxima: ${PROX:-?}"
  else
    falha "$t.timer NAO esta habilitado (systemctl enable --now $t.timer)"
  fi
done

echo
echo "-- 5. Ultima rodada"
for par in "rotina_intimacoes:Intimacoes" "kpi_diario:KPI"; do
  ARQ="_trabalho/logs/${par%%:*}.log"; NOME="${par##*:}"
  if [ -f "$ARQ" ]; then
    IDADE=$(( ( $(date +%s) - $(stat -c %Y "$ARQ" 2>/dev/null || stat -f %m "$ARQ") ) / 3600 ))
    if [ "$IDADE" -le 72 ]; then ok "$NOME: log de ${IDADE}h atras"
    else falha "$NOME: ultimo log ha ${IDADE}h - a rodada parou"; fi
    if tail -60 "$ARQ" | grep -q '\[FALHA\]'; then
      alerta "$NOME: a ultima rodada registrou [FALHA] - ver tail -40 $ARQ"
    fi
  else
    alerta "$NOME: ainda sem log (nenhuma rodada ate agora)"
  fi
done

echo
echo "-- 6. Conexao com o ADVBOX"
if "$PY" OPERACIONAL/main.py advbox >/tmp/saude_advbox.txt 2>&1; then
  ok "ADVBOX respondeu (token e IDs da equipe conferidos)"
else
  falha "diagnostico do ADVBOX falhou - ver /tmp/saude_advbox.txt"
fi

echo
echo "-- 7. Modo da rotina de intimacoes"
if grep -qE '^VPS_ROTINA_GRAVAR=1' config/.env 2>/dev/null; then
  ok "GRAVANDO no ADVBOX (autonomia liberada)"
else
  ok "SIMULACAO - nada e' gravado (padrao)"
fi

echo
echo "==============================================================="
if [ "$FALHAS" -eq 0 ]; then
  echo "  RESULTADO: tudo certo."
else
  echo "  RESULTADO: $FALHAS item(ns) com [X] - ver acima."
fi
echo "==============================================================="
exit $(( FALHAS > 0 ? 1 : 0 ))
