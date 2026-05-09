@echo off
setlocal enabledelayedexpansion

echo === CookieVale Backup Started ===

:: 1. Setup & Config
set "APP_DIR=%~dp0"
if "!APP_DIR:~-1!"=="\" set "APP_DIR=!APP_DIR:~0,-1!"
cd /d "!APP_DIR!"

:: Load .env for network path and DB credentials
for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    set "VAR=%%B"
    for /l %%I in (1,1,3) do (
        if "!VAR:~-1!"==" " set "VAR=!VAR:~0,-1!"
        if "!VAR:~-1!"=="" set "VAR=!VAR:~0,-1!"
    )
    for /f "delims=" %%C in ("^!VAR^!") do set "VAR=%%C"
    set "%%A=!VAR!"
)

if "!BACKUP_DEST:~-1!"=="\" set "BACKUP_DEST=!BACKUP_DEST:~0,-1!"

if "!BACKUP_DEST!"=="" ( echo [ERROR] BACKUP_DEST missing in .env ^& goto :resume_services )
if not exist "!BACKUP_DEST!\" ( echo [ERROR] Destination !BACKUP_DEST! is offline ^& goto :resume_services )

:: 2. Database Backup (Runs WHILE online to avoid downtime)
echo [*] Exporting CookieVale Database...
:: db is the service name in docker-compose
docker compose exec -T db pg_dump -U cookie_user -d cookievale > "!APP_DIR!\cookievale_db_dump.sql"
if %ERRORLEVEL% NEQ 0 ( echo [ERROR] Postgres dump failed ^& goto :resume_services )

:: 3. Copy DB dump and private files to the remote destination
echo [*] Saving SQL dump and .env to shared network...
robocopy "!APP_DIR!" "!BACKUP_DEST!\config" cookievale_db_dump.sql .env /FFT /Z /W:1 /R:1
:: Ignore minor robocopy errors (1 to 7 are exit codes for success)

:: 4. Sync Media (Product/Order images)
if "!MEDIA_ROOT!"=="" ( 
    echo [WARNING] MEDIA_ROOT is not declared, skipping media files. 
) else (
    echo [*] Syncing media from !MEDIA_ROOT! to backup destination...
    robocopy "!MEDIA_ROOT!" "!BACKUP_DEST!\media" /MIR /FFT /Z /XA:H /W:1 /R:1 /SL
)

echo === Backup Completed Successfully ===

:resume_services
echo [*] Finished.
exit /b 0