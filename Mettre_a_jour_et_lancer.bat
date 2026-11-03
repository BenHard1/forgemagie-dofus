@echo off
rem Met a jour l'outil (git pull), installe les dependances si besoin, puis le lance.
chcp 65001 >nul
cd /d "%~dp0"

rem --- Python : py (lanceur Windows) ou python ---
set "PY=py"
where py >nul 2>nul || set "PY=python"
where %PY% >nul 2>nul || (
  echo Python est introuvable. Installe-le depuis https://www.python.org/downloads/
  echo en cochant "Add python.exe to PATH", puis relance ce fichier.
  pause
  exit /b 1
)

rem --- Mise a jour ---
if exist ".git" (
  where git >nul 2>nul && (
    echo Recherche de mises a jour...
    git pull --ff-only || echo [!] Mise a jour impossible : on lance la version actuelle.
  )
) else (
  echo Dossier telecharge en ZIP : pas de mise a jour automatique ^(utilise git clone pour l'avoir^).
)

rem --- Dependances : reinstallees seulement si requirements.txt a change ---
fc /b requirements.txt .requirements.installed >nul 2>nul || (
  echo Installation des dependances...
  %PY% -m pip install --disable-pip-version-check -q -r requirements.txt && copy /y requirements.txt .requirements.installed >nul
)

rem --- Lancement sans fenetre noire (pyw), sinon avec ---
set "PYW=pyw"
if "%PY%"=="python" set "PYW=pythonw"
where %PYW% >nul 2>nul && (
  start "" %PYW% -m fmhelper %*
) || (
  %PY% -m fmhelper %*
  if errorlevel 1 pause
)
