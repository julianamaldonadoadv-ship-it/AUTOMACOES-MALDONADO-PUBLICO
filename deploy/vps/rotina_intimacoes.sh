#!/bin/bash
# =============================================================================
#  ROTINA DIARIA DE INTIMACOES (POP-CJ-003) - VPS
# =============================================================================
#
#  Roda na VPS todo dia util as 08:00, via maldonado-intimacoes.timer.
#
#  MODO SIMULACAO E' O PADRAO. A rotina monta tudo (triagem, roteamento por
#  controller, D-5/D-3, plano de tarefas, relatorio) e NAO grava nada no ADVBOX
#  nem no Zeus. E' a semana de simulacao combinada com a Dra. Juliana: primeiro
#  a automacao prova que acerta contra o que as controllers fariam a mao,
#  depois ganha autonomia.
#
#  Para liberar a gravacao, edite /opt/maldonado/automacoes/config/.env:
#      VPS_ROTINA_GRAVAR=1
#  (nao e' flag de linha de comando de proposito: assim a decisao fica escrita
#  no servidor, com data, e nao no historico de quem rodou o comando)
#
#  Segunda-feira varre sexta+sabado+domingo (--dias 3); nos demais dias, 1.
#
#  Log:  _trabalho/logs/rotina_intimacoes.log   e tambem journalctl
# =============================================================================
set -uo pipefail

PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJETO" || exit 1

LOG_DIR="$PROJETO/_trabalho/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/rotina_intimacoes.log"

if [ -f config/.env ]; then
  set -a; . <(grep -E '^VPS_[A-Z_]+=' config/.env || true); set +a
fi

# Segunda (1) pega o fim de semana; feriado longo se ajusta na mao com --dias.
DIAS=1
[ "$(date +%u)" = "1" ] && DIAS=3

MODO="SIMULACAO (nada e' gravado)"
ARGS=(OPERACIONAL/main.py rotina --dias "$DIAS")
if [ "${VPS_ROTINA_GRAVAR:-0}" = "1" ]; then
  ARGS+=(--gravar)
  MODO="GRAVANDO no ADVBOX/Zeus"
fi

{
  echo
  echo "==============================================================="
  echo "  Rotina de intimacoes - $(date '+%d/%m/%Y %H:%M %Z')  |  $DIAS dia(s)"
  echo "  Modo: $MODO"
  echo "==============================================================="
} >> "$LOG"

if [ -x "$PROJETO/.venv/bin/python" ]; then
  PY="$PROJETO/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

"$PY" "${ARGS[@]}" >> "$LOG" 2>&1
STATUS=$?

if [ $STATUS -ne 0 ]; then
  # O DJEN alterna "sistema ocupado" e falso-vazio para a mesma consulta: falha
  # de uma rodada nao derruba o agendamento, mas tem que ficar visivel.
  echo "  [FALHA] rodada terminou com status $STATUS - conferir acima" >> "$LOG"
else
  echo "  [ok] relatorio em _trabalho/relatorios/" >> "$LOG"
fi

# Custas (POP-CJ-006), duas passadas. SOMENTE LEITURA — nenhuma tarefa nasce
# aqui, mesmo com VPS_ROTINA_GRAVAR=1. Falha nao derruba a rodada.
#   fila     -> o que vai a protocolo nos proximos dias (chega ANTES do erro)
#   auditar  -> o que ja foi protocolado sem custas (rede de seguranca)
echo "  [custas] fila de protocolo dos proximos 5 dias" >> "$LOG"
"$PY" "$PROJETO/OPERACIONAL/main.py" custas fila --dias 5 >> "$LOG" 2>&1 \
  || echo "  [FALHA] fila de custas - conferir acima" >> "$LOG"
echo "  [custas] iniciais dos ultimos 7 dias sem registro de custas" >> "$LOG"
"$PY" "$PROJETO/OPERACIONAL/main.py" custas auditar --dias 7 >> "$LOG" 2>&1 \
  || echo "  [FALHA] auditoria de custas - conferir acima" >> "$LOG"

if [ "$(wc -l < "$LOG")" -gt 4000 ]; then
  tail -2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

exit $STATUS
