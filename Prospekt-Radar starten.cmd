@echo off
chcp 65001 >nul 2>&1
title Prospekt-Radar
cd /d "%~dp0"

REM ===== Einstellungen (hier anpassen) =====
set "PLZ=4652"
set "MINPCT=30"
REM =========================================

echo.
echo   ####################################
echo   #        PROSPEKT-RADAR            #
echo   ####################################
echo.
echo   PLZ %PLZ%  ^|  ab -%MINPCT%%% Rabatt
echo.

REM --- Python finden ---
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY ( where py >nul 2>&1 && set "PY=py" )

if not defined PY (
  echo   [FEHLER] Python wurde nicht gefunden.
  echo   Bitte Python 3.11+ installieren: https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

REM --- httpx vorhanden? ---
%PY% -c "import httpx" >nul 2>&1
if errorlevel 1 (
  echo   [Hinweis] Das Paket 'httpx' fehlt - wird jetzt installiert...
  %PY% -m pip install --quiet httpx
  if errorlevel 1 (
    echo   [FEHLER] Installation fehlgeschlagen. Bitte manuell:  pip install httpx
    echo.
    pause
    exit /b 1
  )
)

echo   Hole aktuelle Angebote... ^(dauert ca. 1-2 Minuten^)
echo   Die Quellen werden bewusst langsam abgefragt ^(1 Anfrage/Sekunde^).
echo.

%PY% pipeline.py --plz %PLZ% --min-pct %MINPCT%
set "RC=%errorlevel%"

echo.
if "%RC%"=="0" goto :oeffnen
if "%RC%"=="2" goto :mitwarnung

echo   [FEHLER] Der Lauf ist fehlgeschlagen ^(Code %RC%^).
if exist "out\angebote.html" (
  echo   Es gibt noch ein aelteres Ergebnis - ich oeffne das.
  echo.
  ping -n 3 127.0.0.1 >nul 2>&1
  start "" "out\angebote.html"
  exit /b 0
)
echo.
pause
exit /b %RC%

:mitwarnung
echo   [WARNUNG] Der Lauf meldet ein Problem ^(siehe Zeilen oben^) -
echo   z.B. eine Quelle ohne Treffer oder deutlich weniger Angebote als sonst.
echo   Die Seite wird trotzdem geoeffnet.
echo.

:oeffnen
if not exist "out\angebote.html" (
  echo   [FEHLER] out\angebote.html wurde nicht erstellt.
  echo.
  pause
  exit /b 1
)
echo   Fertig. Oeffne die Angebote im Browser...
start "" "out\angebote.html"
exit /b 0
