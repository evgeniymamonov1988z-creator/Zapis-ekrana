$ErrorActionPreference = 'Stop'

# Ключ активации Экранник (AE) — сборка из act_key.c компилятором из состава Windows.
$msvc = Get-ChildItem "$env:ProgramFiles\Microsoft Visual Studio", "${env:ProgramFiles(x86)}\Microsoft Visual Studio" `
            -Filter cl.exe -Recurse -ErrorAction SilentlyContinue `
            | Where-Object { $_.FullName -match 'Hostx64\\x64' } | Select-Object -First 1
if (-not $msvc) { Write-Host '[!] Компилятор (cl.exe) не найден'; exit 1 }
$bin = $msvc.DirectoryName
Write-Host ('[OK] cl.exe: ' + $bin)

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$inc = Join-Path $vs 'VC\Tools\MSVC'
$ver = Get-ChildItem $inc -Directory | Sort-Object Name -Descending | Select-Object -First 1
$sdk = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\Include" -Directory | Sort-Object Name -Descending | Select-Object -First 1
if (-not $ver -or -not $sdk) { Write-Host '[!] Заголовки MSVC/SDK не найдены'; exit 1 }

$env:INCLUDE = @(
  (Join-Path $ver.FullName 'include'),
  (Join-Path $sdk.FullName 'ucrt'), (Join-Path $sdk.FullName 'shared'), (Join-Path $sdk.FullName 'um')
) -join ';'
$libver = Join-Path $ver.FullName 'lib\x64'
$sdklib = Join-Path (Split-Path $sdk.FullName) 'Lib'
$libsdk = Get-ChildItem $sdklib -Directory | Sort-Object Name -Descending | Select-Object -First 1
$env:LIB = @(
  $libver, (Join-Path $libsdk.FullName 'ucrt\x64'), (Join-Path $libsdk.FullName 'um\x64')
) -join ';'
$env:PATH = $bin + ';' + $env:PATH

Write-Host '[1/3] ресурсы (иконка, версия)'
& cl /nologo /c act_key.rc /fo act_key.res
if ($LASTEXITCODE -ne 0) { Write-Host '[!] Ресурсы не собрались'; exit 1 }

Write-Host '[2/3] компиляция'
& cl /nologo /O2 /MT /EHsc act_key.c act_key.res /link /SUBSYSTEM:WINDOWS /OUT:act_key.exe user32.lib shell32.lib advapi32.lib
if ($LASTEXITCODE -ne 0) { Write-Host '[!] Компиляция не удалась'; exit 1 }

Write-Host '[3/3] готово'
Remove-Item act_key.obj, act_key.res -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force dist | Out-Null
Copy-Item act_key.exe 'dist\Ekrannik-Unlock.exe' -Force
$k = Get-Item 'dist\Ekrannik-Unlock.exe'
Write-Host ('[OK] ' + $k.Name + '  ' + [math]::Round($k.Length/1KB,1) + ' KB')
