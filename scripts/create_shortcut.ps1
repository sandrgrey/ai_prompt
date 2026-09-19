$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonWindowless = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (!(Test-Path -LiteralPath $pythonWindowless)) { throw 'Run setup_windows.bat first.' }
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'Image to Prompt.lnk'
$shellObject = New-Object -ComObject WScript.Shell
$shortcut = $shellObject.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonWindowless
$shortcut.Arguments = '"' + (Join-Path $projectRoot 'launcher.py') + '"'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = 'Launch Image to Prompt and open browser'
$shortcut.IconLocation = "$pythonWindowless,0"
$shortcut.Save()
Write-Output $shortcutPath
