#!/bin/bash
# =============================================================================
#  PROVISIONAMENTO DA VPS - Maldonado Advogados
# =============================================================================
#
#  Roda UMA VEZ, DENTRO DA VPS, como root (ou com sudo):
#
#      ssh root@SEU_IP
#      bash provisionar.sh
#
#  O que faz:
#    1. fuso horario America/Porto_Velho  (sem isso o timer das 08:00 dispara
#       as 04:00 da manha no horario de Porto Velho - a VPS nasce em UTC)
#    2. usuario de servico `maldonado` (a automacao NAO roda como root)
#    3. Python 3 + venv + Chromium (motor de PDF do kpi --pdf)
#    4. pastas /opt/maldonado/automacoes e /opt/maldonado/automacoes/config
#
#  NAO instala credencial nenhuma. O .env, o credentials.json e o token.json
#  sao copiados a mao depois (ver deploy/vps/README.md, passo 4).
# =============================================================================
set -euo pipefail

USUARIO="${MALDONADO_USER:-maldonado}"
BASE="${MALDONADO_BASE:-/opt/maldonado/automacoes}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERRO: rode como root (ou com sudo)." >&2
  exit 1
fi

echo "==> 1/5  Fuso horario America/Porto_Velho (UTC-4)"
timedatectl set-timezone America/Porto_Velho
date

echo "==> 2/5  Pacotes do sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
# chromium ....: motor de PDF do md_para_pdf.py / kpi --pdf
# rsync .......: e' por ele que o Mac envia o projeto
# tesseract ...: OCR em portugues. No Mac o OCR do acervo saiu do Vision da
#                Apple, que nao existe no Linux; sem o pacote -por, o tesseract
#                le em ingles e erra todo acento de peca juridica.
# libgl1/glib .: bibliotecas de imagem que o PyMuPDF pede para renderizar PDF.
#                Faltando, o `import fitz` passa e o render quebra so na hora.
apt-get install -y -qq python3 python3-venv python3-pip rsync ca-certificates tzdata \
  tesseract-ocr tesseract-ocr-por libgl1 libglib2.0-0
apt-get install -y -qq chromium || apt-get install -y -qq chromium-browser || \
  echo "    [!] chromium nao instalado - 'kpi --pdf' gera o .md e falha no .pdf"

# Firewall: instalado sempre, LIGADO so a pedido. Rodar `ufw enable` sem antes
# liberar a porta do SSH derruba a propria conexao e tranca voce para fora da
# VPS - por isso o default e' nao ligar, e quando liga, o SSH vem primeiro.
apt-get install -y -qq ufw
if [ "${MALDONADO_UFW:-0}" = "1" ]; then
  PORTA_SSH="${MALDONADO_PORTA_SSH:-22}"
  echo "    ligando o firewall (liberando SSH na porta $PORTA_SSH antes)"
  ufw allow "$PORTA_SSH/tcp"
  ufw --force enable
  ufw status numbered
else
  echo "    ufw instalado e DESLIGADO (ligar com MALDONADO_UFW=1)"
fi

echo "==> 3/5  Usuario de servico: $USUARIO"
if ! id "$USUARIO" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$USUARIO"
  echo "    usuario criado"
else
  echo "    ja existia"
fi

echo "==> 4/5  Pastas em $BASE"
mkdir -p "$BASE/config" "$BASE/_trabalho/logs" "$BASE/_trabalho/relatorios"
chown -R "$USUARIO:$USUARIO" "$(dirname "$BASE")"
# config/ guarda .env, credentials.json e token.json: so o dono le.
chmod 700 "$BASE/config"

echo "==> 5/5  Chave SSH do Mac (para o enviar.sh funcionar sem senha)"
install -d -m 700 -o "$USUARIO" -g "$USUARIO" "/home/$USUARIO/.ssh"
if [ -f /root/.ssh/authorized_keys ] && [ ! -s "/home/$USUARIO/.ssh/authorized_keys" ]; then
  cp /root/.ssh/authorized_keys "/home/$USUARIO/.ssh/authorized_keys"
  chown "$USUARIO:$USUARIO" "/home/$USUARIO/.ssh/authorized_keys"
  chmod 600 "/home/$USUARIO/.ssh/authorized_keys"
  echo "    chave do root copiada para $USUARIO"
else
  echo "    nada a copiar - adicione a chave publica do Mac em"
  echo "    /home/$USUARIO/.ssh/authorized_keys"
fi

echo
echo "PRONTO. Proximo passo, NO MAC:"
echo "    bash deploy/vps/enviar.sh"
echo "e depois copiar as credenciais (README.md, passo 4)."
