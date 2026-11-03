@echo off
rem Met a jour l'outil (git pull) puis le lance. La logique est dans outils\lancer.bat :
rem ce fichier reste court, car git peut le modifier pendant qu'il s'execute.
cd /d "%~dp0"
if exist ".git" (where git >nul 2>nul && (echo Recherche de mises a jour... & git pull --ff-only || echo [!] Mise a jour impossible : lancement de la version actuelle.)) & call "%~dp0outils\lancer.bat" %* & exit /b
call "%~dp0outils\lancer.bat" %*
