#!/bin/bash
# =============================================================================
#  VERIFICACAO DIARIA DO KPI DE EXITO - Maldonado Advogados
# =============================================================================
#
#  Roda a apuracao do KPI todo dia util (seg-sex, 08:00) e regera os relatorios
#  da competencia INTEIRA (do dia 1o do mes ate hoje), nao so do dia. E' de
#  proposito: a taxa do mes so faz sentido acumulada, e o diario ja separa por
#  dia e por semana.
#
#  As 08:00 a rodada reflete ate as publicacoes do dia ANTERIOR - as de hoje
#  entram na rodada de amanha. E' o mesmo horario da rotina de intimacoes da
#  Controladoria (POP-CJ-003).
#
#  Nao grava no ADVBOX. A unica escrita no Drive e' a planilha da competencia
#  ("KPI DE EXITO - <MES>", reescrita a cada rodada - ver kpi_planilha.py).
#
#  NAO EDITE ESTE ARQUIVO COM UMA RODADA EM ANDAMENTO. O bash le o script por
#  deslocamento de bytes, entao alterar o cabecalho no meio da execucao faz a
#  rodada retomar no meio de uma palavra ("tencia: command not found"). A
#  rodada ate termina, mas com erros que nao existem no arquivo. Se acontecer,
#  basta rodar de novo com o arquivo estavel.
#
#  Instalar (macOS, launchd):
#      cp deploy/com.maldonado.kpi.plist ~/Library/LaunchAgents/
#      launchctl load ~/Library/LaunchAgents/com.maldonado.kpi.plist
#
#  Conferir a ultima rodada:
#      tail -40 _trabalho/logs/kpi_diario.log
#
#  Desinstalar:
#      launchctl unload ~/Library/LaunchAgents/com.maldonado.kpi.plist
# =============================================================================
set -uo pipefail

PROJETO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJETO" || exit 1

LOG_DIR="$PROJETO/_trabalho/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/kpi_diario.log"

# Competencia corrente: do dia 1o ate hoje.
DE="$(date +%Y-%m-01)"
ATE="$(date +%Y-%m-%d)"
SAIDA="docs/kpi_exito"

{
  echo
  echo "==============================================================="
  echo "  KPI diario - $(date '+%d/%m/%Y %H:%M')  |  competencia $DE a $ATE"
  echo "==============================================================="
} >> "$LOG"

# O venv do projeto e' quem tem as dependencias (requests, dotenv, pymupdf).
if [ -x "$PROJETO/.venv/bin/python" ]; then
  PY="$PROJETO/.venv/bin/python"
elif [ -x "$PROJETO/venv/bin/python" ]; then
  PY="$PROJETO/venv/bin/python"
else
  PY="$(command -v python3)"
fi

RESSALVAS="$SAIDA/RESSALVAS_$(date +%Y-%m).md"
ARGS=(OPERACIONAL/main.py kpi --de "$DE" --ate "$ATE"
      --csv "$SAIDA/kpi_${DE}_a_${ATE}.csv" --pdf "$SAIDA" --planilha)
# As ressalvas da competencia sao escritas a mao pela GJ; se o arquivo do mes
# ainda nao existe, a rodada segue sem ele em vez de falhar.
[ -f "$RESSALVAS" ] && ARGS+=(--ressalvas "$RESSALVAS")

"$PY" "${ARGS[@]}" >> "$LOG" 2>&1
STATUS=$?

if [ $STATUS -ne 0 ]; then
  # A API do DJEN e' instavel e da falso-vazio: falha de uma rodada nao e'
  # motivo para parar o agendamento, mas precisa ficar visivel no log.
  echo "  [FALHA] a rodada terminou com status $STATUS - conferir acima" >> "$LOG"
else
  echo "  [ok] relatorios regerados em $SAIDA/" >> "$LOG"
fi

# Mantem o log em tamanho gerenciavel (ultimas ~2000 linhas).
if [ "$(wc -l < "$LOG")" -gt 4000 ]; then
  tail -2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

exit $STATUS
