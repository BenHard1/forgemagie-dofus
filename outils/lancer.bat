@echo off
rem Trouve un Python 3.10+ qui fonctionne vraiment, installe les dependances si besoin, lance l'outil.
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0.."
set "LOG=%CD%\fmhelper_erreur.log"

rem --- 1. Trouver un interpreteur valide (on l'execute pour verifier : "py" peut pointer vers un Python desinstalle) ---
set "PY="
for %%C in ("python" "py -3.13" "py -3.12" "py -3.11" "py -3.10" "py -3" "py") do (
  if not defined PY (
    %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=%%~C"
  )
)
if not defined PY (
  echo Aucun Python 3.10 ou plus recent ne fonctionne sur ce PC.> "%LOG%"
  echo.
  echo  Aucun Python 3.10+ utilisable n'a ete trouve.
  echo  Installe Python depuis https://www.python.org/downloads/ en cochant "Add python.exe to PATH",
  echo  puis relance ce fichier.
  echo.
  pause
  exit /b 1
)

rem Chemin exact de cet interpreteur, et de pythonw.exe (sans fenetre noire) a cote
for /f "usebackq delims=" %%P in (`%PY% -c "import sys; print(sys.executable)"`) do set "PYEXE=%%P"
for %%D in ("%PYEXE%") do set "PYW=%%~dpDpythonw.exe"
echo Python utilise : %PYEXE%

rem --- 2. Dependances : reinstallees seulement si requirements.txt a change ---
fc /b requirements.txt .requirements.installed >nul 2>nul || (
  echo Installation des dependances...
  "%PYEXE%" -m pip install --disable-pip-version-check -q -r requirements.txt
  if errorlevel 1 (
    echo.
    echo  [!] L'installation des dependances a echoue ^(voir le message ci-dessus^).
    pause
    exit /b 1
  )
  copy /y requirements.txt .requirements.installed >nul
)

rem --- 3. Lancement ---
if exist "%PYW%" (
  start "" "%PYW%" -m fmhelper %*
) else (
  "%PYEXE%" -m fmhelper %*
  if errorlevel 1 pause
)
endlocal
