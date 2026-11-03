@echo off
rem Cree un raccourci "Aide FM Dofus" sur le Bureau, qui met a jour puis lance l'outil.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Aide FM Dofus.lnk');" ^
  "$s.TargetPath='%~dp0Mettre_a_jour_et_lancer.bat';$s.WorkingDirectory='%~dp0';$s.WindowStyle=7;" ^
  "$s.IconLocation='%SystemRoot%\System32\imageres.dll,76';$s.Save()"
echo Raccourci "Aide FM Dofus" cree sur le Bureau.
pause
