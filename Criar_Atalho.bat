@echo off
title Criar Atalho na Area de Trabalho - BPMKeySearch
chcp 65001 >nul
cd /d "%~dp0"

echo Criando atalho na Area de Trabalho...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$wsh = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [System.Environment]::GetFolderPath('Desktop'); " ^
  "$shortcutPath = Join-Path $desktop 'BPMKeySearch.lnk'; " ^
  "$s = $wsh.CreateShortcut($shortcutPath); " ^
  "$s.TargetPath = '%~dp0run.bat'; " ^
  "$s.WorkingDirectory = '%~dp0'; " ^
  "$s.IconLocation = '%~dp0icon.ico,0'; " ^
  "$s.Description = 'BPMKeySearch - Detector de Tom, BPM e Tempo (Spotify & YouTube)'; " ^
  "$s.Save(); " ^
  "Write-Output 'Atalho criado com sucesso na Area de Trabalho: ' + $shortcutPath"

echo.
echo Concluido! Agora voce pode abrir o BPMKeySearch direto pela sua Area de Trabalho.
echo.
pause
