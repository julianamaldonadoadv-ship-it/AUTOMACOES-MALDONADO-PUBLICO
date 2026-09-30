#!/bin/bash
# =============================================================================
#  RODADA DAS 08:00 DA CONTROLADORIA (Mac) - intimacoes + despachos
# =============================================================================
#
#  Pedido da Dra. Juliana (21/09/2026): toda manha, as 08:00, as duas planilhas
#  da Controladoria atualizadas:
#
#    1. Intimacoes (POP-CJ-003) - rotina em SIMULACAO: nada e' gravado no
#       ADVBOX; a rodada entra nas abas AGENDAMENTOS e INTIMACOES da planilha
#       "CONFERENCIA DA ROTINA DE INTIMACOES" para as controllers conferirem.
#    2. Despachos (POP-CJ-DESP-001) - planilha "CONTROLE DE DESPACHOS -
#       CONTROLADORIA". Somente leitura no ADVBOX; a unica escrita e' a
#       planilha, que preserva as colunas Confere?/Observacao da equipe.
#    3. Custas (POP-CJ-006), em duas passadas. SO RELATORIO nas duas: nenhuma
#       tarefa e' criada aqui (quem cria e' a controller, com --criar-tarefa).
#       3a. FILA: o que vai a protocolo nos proximos dias (tarefas PECA APROVADA
#           PARA PROTOCOLO e PROTOCOLO D-3/D-2/D-1) sem guia, pagamento ou
#           gratuidade registrados. E' a passada que chega ANTES do protocolo.
#       3b. AUDITORIA: a inicial que ja foi protocolada nos ultimos 7 dias sem
#           registro de custas — rede de seguranca do que escapou.
#
#  Dia perdido se repoe sozinho: intimacoes pelo rotina_recuperar.py (marco em
#  _trabalho/logs/ultima_rodada_intimacoes.txt) e despachos pela janela de 7 dias.
#  Roda aqui ate a VPS ser configurada (VPS_HOST vazio em 21/09/2026); quando a
#  VPS assumir, descarregar o plist para nao rodar em dobro.
#
#  Instalar:
#      cp deploy/com.maldonado.controladoria.plist ~/Library/LaunchAgents/
#      launchctl load ~/Library/LaunchAgents/com.maldonado.controladoria.plist
#  Log:
#      tail -60 _trabalho/logs/controladoria_diaria.log
# =============================================================================
set -uo pipefail

PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJETO" || exit 1

LOG_DIR="$PROJETO/_trabalho/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/controladoria_diaria.log"

DIAS=1
[ "$(date +%u)" = "1" ] && DIAS=3

if [ -x "$PROJETO/.venv/bin/python" ]; then
  PY="$PROJETO/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

{
  echo
  echo "==============================================================="
  echo "  Controladoria 08:00 - $(date '+%d/%m/%Y %H:%M')  |  $DIAS dia(s)"
  echo "==============================================================="
  echo "  [1/3] Intimacoes (simulacao + planilha; repoe dias perdidos)"
} >> "$LOG"

# Repoe o que faltou: o launchd nao replica rodada perdida, e a planilha de
# conferencia ficou dias parada em 09/2026 sem ninguem notar. O modulo guarda a
# ultima rodada publicada e refaz cada dia util que falta, com a data do dia.
"$PY" OPERACIONAL/rotina_recuperar.py >> "$LOG" 2>&1
S1=$?
[ $S1 -ne 0 ] && echo "  [FALHA] intimacoes terminou com status $S1" >> "$LOG"

echo "  [2/3] Despachos (planilha de controle)" >> "$LOG"
"$PY" OPERACIONAL/main.py despachos --dias 7 --gravar >> "$LOG" 2>&1   # 7 dias: repoe rodada perdida
S2=$?
[ $S2 -ne 0 ] && echo "  [FALHA] despachos terminou com status $S2" >> "$LOG"

echo "  [3/3] Custas: fila de protocolo + auditoria (so relatorio)" >> "$LOG"
"$PY" OPERACIONAL/main.py custas fila --dias 5 >> "$LOG" 2>&1
S3=$?
"$PY" OPERACIONAL/main.py custas auditar --dias 7 >> "$LOG" 2>&1
S3=$(( S3 + $? ))
[ $S3 -ne 0 ] && echo "  [FALHA] custas terminou com status $S3" >> "$LOG"

echo "  Fim: $(date '+%H:%M')  |  intimacoes=$S1 despachos=$S2 custas=$S3" >> "$LOG"

if [ "$(wc -l < "$LOG")" -gt 6000 ]; then
  tail -3000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

[ $S1 -eq 0 ] && [ $S2 -eq 0 ] && [ $S3 -eq 0 ]
