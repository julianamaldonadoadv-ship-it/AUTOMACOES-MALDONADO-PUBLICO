@echo off
REM =============================================================================
REM  Instalador - Maldonado Advogados - Sistema de Automacao (WINDOWS)
REM  Rodar este arquivo de dentro da pasta MALDONADO_ADVOGADOS (duplo clique
REM  ou "instalar_windows.bat" no terminal).
REM =============================================================================

cd /d "%~dp0\.."

echo ===============================================
echo   Instalando o sistema Maldonado Advogados
echo ===============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instale o Python 3.11+ em https://python.org/downloads
    echo Durante a instalacao, marque a opcao "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/4] Criando ambiente virtual (venv)...
if not exist venv (
    python -m venv venv
) else (
    echo   venv ja existe, pulando.
)

echo [2/4] Instalando dependencias...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul
pip install -r requirements.txt

echo [3/4] Preparando config\.env...
if not exist config\.env (
    copy config\.env.example config\.env
    echo   config\.env criado a partir do modelo. PRECISA SER PREENCHIDO ainda.
) else (
    echo   config\.env ja existe, nao foi sobrescrito.
)

echo [4/4] Testando conexao com o ADVBOX (so funciona depois de preencher o token)...
python -c "import sys; sys.path.insert(0,'INTEGRACOES'); from dotenv import load_dotenv; load_dotenv('config/.env'); import advbox_integration as a; a.testar_conexao()"

echo.
echo ===============================================
echo   Instalacao concluida!
echo ===============================================
echo.
echo Proximos passos:
echo   1. Abra config\.env num editor de texto e preencha ADVBOX_API_TOKEN e DJEN_OAB_LISTA
echo   2. Preencha config\equipe.py com os IDs de usuario do ADVBOX
echo   3. Rode: venv\Scripts\activate.bat  (ativa o ambiente)
echo   4. Rode: python OPERACIONAL\main.py triagem --dias 7
echo.
echo Guia completo: docs\ONBOARDING.md
echo.
pause
