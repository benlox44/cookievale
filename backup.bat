@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo   INICIANDO RESPALDO COOKIEVALE
echo   Fecha/Hora: %date% %time%
echo ==================================================

python backup.py
if %ERRORLEVEL% equ 0 (
    echo [OK] CookieVale respaldado con exito.
) else (
    echo [ERROR] CookieVale fallo con codigo %ERRORLEVEL%.
)
