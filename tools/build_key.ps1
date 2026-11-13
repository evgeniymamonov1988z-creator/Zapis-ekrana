$ErrorActionPreference = 'Continue'

# Ключ активации Экранник (AE) — сборка из act_key.c компилятором из состава Windows.
$vs = 'C:\Program Files\Microsoft Visual Studio\18\Enterprise'
if (-not (Test-Path $vs)) {
    $vs = (cmd /c '"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -property installationPath').Trim()
}
Write-Host ('VS: ' + $vs)

$msvcver = Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory | Sort-Object Name -Descending | Select-Object -First 1
$bin = Join-Path $msvcver.FullName 'bin\Hostx64\x64'
Write-Host ('MSVC: ' + $msvcver.Name)
Write-Host ('cl: ' + (Test-Path (Join-Path $bin 'cl.exe')) + '  rc: ' + (Test-Path (Join-Path $bin 'rc.exe')))

$sdk = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\Include' -Directory | Sort-Object Name -Descending | Select-Object -First 1
$sdkver = $sdk.Name
Write-Host ('SDK: ' + $sdkver)

$env:INCLUDE = @(
  (Join-Path $msvcver.FullName 'include'),
  ('C:\Program Files (x86)\Windows Kits\10\Include\' + $sdkver + '\ucrt'),
  ('C:\Program Files (x86)\Windows Kits\10\Include\' + $sdkver + '\shared'),
  ('C:\Program Files (x86)\Windows Kits\10\Include\' + $sdkver + '\um')
) -join ';'
$env:LIB = @(
  (Join-Path $msvcver.FullName 'lib\x64'),
  ('C:\Program Files (x86)\Windows Kits\10\Lib\' + $sdkver + '\ucrt\x64'),
  ('C:\Program Files (x86)\Windows Kits\10\Lib\' + $sdkver + '\um\x64')
) -join ';'
$env:PATH = $bin + ';' + $env:PATH
Write-Host ('windows.h: ' + (Test-Path (Join-Path $msvcver.FullName 'include\windows.h')) + '  shellapi: ' + (Test-Path ('C:\Program Files (x86)\Windows Kits\10\Include\' + $sdkver + '\um\shellapi.h')))

Write-Host '[1/3] иконка и версия'
& (Join-Path $bin 'rc.exe') /nologo act_key.rc
Write-Host ('rc exit: ' + $LASTEXITCODE)

Write-Host '[2/3] компиляция'
& (Join-Path $bin 'cl.exe') /nologo /O2 /MT /EHsc act_key.c act_key.res /link /SUBSYSTEM:WINDOWS /OUT:act_key.exe user32.lib shell32.lib advapi32.lib
$rc = $LASTEXITCODE
Write-Host ('cl exit: ' + $rc)
if ($rc -ne 0) { exit 1 }

Write-Host '[3/3] готово'
Remove-Item act_key.obj, act_key.res -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force dist | Out-Null
Copy-Item act_key.exe 'dist\Ekrannik-Unlock.exe' -Force
$k = Get-Item 'dist\Ekrannik-Unlock.exe'
Write-Host ('[OK] ' + $k.Name + '  ' + [math]::Round($k.Length/1KB,1) + ' KB')
