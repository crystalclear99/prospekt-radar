@echo off
REM Prospekt-Radar Wrapper fuer den Windows-Aufgabenplaner.
REM Faengt den Exit-Code ab und schreibt ins Log.
cd /d "%~dp0"
python pipeline.py --plz 1010 --min-pct 30 >> "data\run.log" 2>&1
echo [%date% %time%] exit=%errorlevel% >> "data\run.log"
