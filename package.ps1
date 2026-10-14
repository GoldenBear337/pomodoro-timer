# Builds the app and prepares everything for GitHub in .\release:
#   release\Pomodoro-v<version>-win64.zip   -> attach to a GitHub Release (what users download)
#   release\github-upload\                  -> source files to upload to the repository
# Usage:  powershell -ExecutionPolicy Bypass -File package.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

& "$PSScriptRoot\build.ps1"

$version = (& .\.venv\Scripts\python -c "import pomodoro; print(pomodoro.__version__)").Trim()
$release = Join-Path $PSScriptRoot "release"
if (Test-Path $release) { Remove-Item -Recurse -Force $release }
New-Item -ItemType Directory -Force $release | Out-Null

# 1) App zip: Pomodoro\Pomodoro.exe + _internal\ + README
#    Retries because antivirus often locks a freshly built .exe for a few seconds while scanning it.
Copy-Item README.md dist\Pomodoro
$zip = Join-Path $release "Pomodoro-v$version-win64.zip"
for ($i = 1; $i -le 5; $i++) {
    try { Compress-Archive -Path dist\Pomodoro -DestinationPath $zip -Force; break }
    catch { if ($i -eq 5) { throw }; Write-Host "File busy, retrying in 5s..."; Start-Sleep 5 }
}

# 2) Source files for the repository (no venv/build/dist/caches)
$src = Join-Path $release "github-upload"
New-Item -ItemType Directory -Force $src | Out-Null
$items = "pomodoro", "tests", "docs", "run.py", "build.ps1", "package.ps1", "requirements.txt", "README.md", ".gitignore"
foreach ($item in $items) { Copy-Item -Recurse $item $src }
Get-ChildItem $src -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

Write-Host ""
Write-Host "App zip : $zip  ($([math]::Round((Get-Item $zip).Length / 1MB, 1)) MB)"
Write-Host "Source  : $src"
