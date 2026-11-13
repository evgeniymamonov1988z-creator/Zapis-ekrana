$ErrorActionPreference = 'Continue'

# Ключ активации Экранник (AE) — сборка из act_key.c компилятором из состава Windows.
function Say($m) { Write-Host $m }

Say '[0] кто я'
Say ('powershell: ' + $PSVersionTable.PSVersion.ToString())
Say ('arch env: ' + $env:PROCESSOR_ARCHITECTURE)
Say ('ProgramFiles: ' + $env:ProgramFiles)
Say ('vsinstalldir: ' + $env:VSINSTALLDIR)

Say '[1] поиск cl.exe (where)'
$where = cmd /c "where cl 2>nul"
Say ('where cl -> ' + $where)

Say '[1b] поиск cl.exe (файлы)'
$msvc = Get-ChildItem "$env:ProgramFiles\Microsoft Visual Studio" -Filter cl.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match 'Hostx64.x64' } | Select-Object -First 1
Say ('cl found: ' + $msvc.FullName)
if (-not $msvc) { exit 1 }
$bin = $msvc.DirectoryName

Say '[2] vswhere'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
Say ('vswhere exists: ' + (Test-Path $vswhere))
$vs = cmd /c ('"' + $vswhere + '" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath')
Say ('VS: ' + $vs)

Say '[3] заголовки и библиотеки'
$ver = Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
Say ('MSVC: ' + $ver.FullName)
$sdkroot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10'
$sdk = Get-ChildItem (Join-Path $sdkroot 'Include') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
Say ('SDK: ' + $sdk.FullName)
$libsdk = Get-ChildItem (Join-Path $sdkroot 'Lib') -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
Say ('SDK lib: ' + $libsdk.FullName)

$env:INCLUDE = @(
  (Join-Path $ver.FullName 'include'),
  (Join-Path $sdk.FullName 'ucrt'), (Join-Path $sdk.FullName 'shared'), (Join-Path $sdk.FullName 'um')
) -join ';'
$env:LIB = @(
  (Join-Path $ver.FullName 'lib\x64'),
  (Join-Path $libsdk.FullName 'ucrt\x64'), (Join-Path $libsdk.FullName 'um\x64')
) -join ';'
$env:PATH = $bin + ';' + $env:PATH
Say ('INCLUDE ok: ' + (Test-Path (Join-Path $ver.FullName 'include\windows.h')))
Say ('SDK ucrt ok: ' + (Test-Path (Join-Path $sdk.FullName 'ucrt\stdlib.h')))

Say '[4] ресурсы'
& (Join-Path $bin 'cl.exe') /nologo /c act_key.rc /fo act_key.res
Say ('rc exit: ' + $LASTEXITCODE)

Say '[5] компиляция'
& (Join-Path $bin 'cl.exe') /nologo /O2 /MT /EHsc act_key.c act_key.res /link /SUBSYSTEM:WINDOWS /OUT:act_key.exe user32.lib shell32.lib advapi32.lib
$rc = $LASTEXITCODE
Say ('cl exit: ' + $rc)
if ($rc -ne 0) { exit 1 }

Say '[6] готово'
Remove-Item act_key.obj, act_key.res -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force dist | Out-Null
Copy-Item act_key.exe 'dist\Ekrannik-Unlock.exe' -Force
$k = Get-Item 'dist\Ekrannik-Unlock.exe'
Say ('[OK] ' + $k.Name + '  ' + [math]::Round($k.Length/1KB,1) + ' KB')
