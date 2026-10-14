# Builds dist\Pomodoro\Pomodoro.exe (portable folder, no installer).
# Usage:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -r requirements.txt
}
$py = ".\.venv\Scripts\python"

# Generate the app icon (red tomato-ish circle) so no binary assets live in the repo.
New-Item -ItemType Directory -Force build | Out-Null
& $py -c "from pomodoro.tray import make_icon; make_icon('#ff5f57', 256).save('build/icon.ico', sizes=[(16,16),(32,32),(48,48),(256,256)])"

& $py -m PyInstaller --noconfirm --noconsole --onedir `
    --name Pomodoro --icon build/icon.ico `
    --exclude-module numpy --exclude-module matplotlib `
    run.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE). Close Pomodoro.exe if it is running and retry." }

Write-Host "`nBuilt: $PSScriptRoot\dist\Pomodoro\Pomodoro.exe"
