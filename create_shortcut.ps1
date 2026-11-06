$desktopPath = [System.Environment]::GetFolderPath('Desktop')
$wsh = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path $desktopPath "BPMKeySearch.lnk"

$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "C:\Users\facimoto\.gemini\antigravity\scratch\music_detector_app\run.bat"
$shortcut.WorkingDirectory = "C:\Users\facimoto\.gemini\antigravity\scratch\music_detector_app"
$shortcut.IconLocation = "C:\Users\facimoto\.gemini\antigravity\scratch\music_detector_app\icon.ico,0"
$shortcut.Description = "BPMKeySearch - Detector de Tom, BPM e Tempo (Spotify & YouTube)"
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Output "Atalho criado com sucesso em: $shortcutPath"
