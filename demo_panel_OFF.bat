@echo off
rem Vyklyuchit pokaz paneli (vernut zaschitu ot zapisi).
rem Udalyaet fayl-metku ryadom s programmoy.
del /q "%~dp0demo_show_panel*" 2>nul
echo.
echo [OK] Demo-rezhim VYKLYUCHEN: panel snova spryatana ot zapisi.
echo Zapustite programmu zanovo, chtoby izmenenie primenilos.
echo.
pause
