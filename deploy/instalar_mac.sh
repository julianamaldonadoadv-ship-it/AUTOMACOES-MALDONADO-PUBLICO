#!/bin/bash
# =============================================================================
#  Instalador - Maldonado Advogados - Sistema de Automacao (macOS / Linux)
#  Rodar de dentro da pasta MALDONADO_ADVOGADOS:
#      chmod +x deploy/instalar_mac.sh && ./deploy/instalar_mac.sh
# =============================================================================
set -e
cd "$(dirname "$0")/.."

echo "==============================================="
echo "  Instalando o sistema Maldonado Advogados"
echo "==============================================="
echo

PYTHON=python3
if ! command -v $PYTHON &> /dev/null; then
    echo "ERRO: python3 nao encontrado."
    echo "Instale via https://www.python.org/downloads/macos/ ou 'brew install python3'"
    exit 1
fi

echo "[1/4] Criando ambiente virtual (venv)..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
else
    echo "  venv ja existe, pulando."
fi

echo "[2/4] Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

echo "[3/4] Preparando config/.env..."
if [ ! -f "config/.env" ]; then
    cp config/.env.example config/.env
    echo "  config/.env criado a partir do modelo. PRECISA SER PREENCHIDO ainda."
else
    echo "  config/.env ja existe, nao foi sobrescrito."
fi

echo "[4/4] Testando conexao com o ADVBOX (so funciona depois de preencher o token)..."
python -c "
import sys
sys.path.insert(0, 'INTEGRACOES')
from dotenv import load_dotenv
load_dotenv('config/.env')
import advbox_integration as a
a.testar_conexao()
" || true

echo
echo "==============================================="
echo "  Instalacao concluida!"
echo "==============================================="
echo
echo "Proximos passos:"
echo "  1. Abra config/.env num editor de texto e preencha ADVBOX_API_TOKEN e DJEN_OAB_LISTA"
echo "  2. Preencha config/equipe.py com os IDs de usuario do ADVBOX"
echo "  3. Rode: source venv/bin/activate   (ativa o ambiente)"
echo "  4. Rode: python OPERACIONAL/main.py triagem --dias 7"
echo
echo "Guia completo: docs/ONBOARDING.md"
