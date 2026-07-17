@echo off
setlocal

echo ============================================
echo   Koddle - gerando executavel
echo ============================================
echo.

if not exist "app.py" (
    echo [ERRO] Rode este script dentro da pasta do Koddle ^(onde esta o app.py^).
    pause
    exit /b 1
)

echo [1/4] Instalando dependencias do projeto...
python -m pip install -r requirements.txt
if errorlevel 1 goto :erro

echo.
echo [2/4] Instalando o PyInstaller...
python -m pip install pyinstaller
if errorlevel 1 goto :erro

echo.
echo [3/4] Limpando builds antigos...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [4/4] Gerando o executavel (isso pode demorar alguns minutos)...
python -m PyInstaller koddle.spec --noconfirm
if errorlevel 1 goto :erro

echo.
echo ============================================
echo   Pronto! O executavel esta em:
echo   dist\Koddle.exe
echo ============================================
pause
exit /b 0

:erro
echo.
echo [ERRO] Algo falhou durante o processo. Veja a mensagem acima.
pause
exit /b 1
