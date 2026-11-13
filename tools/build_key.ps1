$ErrorActionPreference = 'Stop'

# Ключ активации Экранник (AE) — сборка из act_key.c компилятором из состава Windows.
Write-Host '[1/4] поиск компилятора'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { Write-Host '[!] vswhere не найден'; exit 1 }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { Write-Host '[!] Visual Studio C++ не найден'; exit 1 }
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
Write-Host ('   ' + $vcvars)
if (-not (Test-Path $vcvars)) { Write-Host '[!] vcvars64.bat не найден'; exit 1 }

Write-Host '[2/4] окружение'
$envFile = Join-Path $env:RUNNER_TEMP 'vcenv.txt'
cmd /c ('""' + $vcvars + '" >nul 2>&1 && set > "' + $envFile + '"')
if ($LASTEXITCODE -ne 0) { Write-Host '[!] vcvars64 не выполнился'; exit $LASTEXITCODE }
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') { $n = $matches[1]; $v = $matches[2]; Set-Item -Path ('env:' + $n) -Value $v }
}
Write-Host ('   cl: ' + (Get-Command cl -ErrorAction SilentlyContinue).Source)
Write-Host ('   rc: ' + (Get-Command rc -ErrorAction SilentlyContinue).Source)

Write-Host '[3/4] компиляция'
& rc /nologo act_key.rc
if ($LASTEXITCODE -ne 0) { Write-Host '[!] RC не удался'; exit 1 }
& cl /nologo /O2 /MT act_key.c act_key.res /link /SUBSYSTEM:WINDOWS /OUT:act_key.exe user32.lib shell32.lib advapi32.lib
if ($LASTEXITCODE -ne 0) { Write-Host '[!] CL не удался'; exit 1 }

Write-Host '[4/4] готово'
Remove-Item act_key.obj, act_key.res -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force dist | Out-Null
Copy-Item act_key.exe 'dist\Ekrannik-Unlock.exe' -Force
$k = Get-Item 'dist\Ekrannik-Unlock.exe'
Write-Host ('[OK] ' + $k.Name + '  ' + [math]::Round($k.Length/1KB,1) + ' KB')
