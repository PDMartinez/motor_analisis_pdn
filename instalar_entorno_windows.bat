@echo off
setlocal
py -3.9 -m venv .venv
if errorlevel 1 goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto error
pip install -r requirements-produccion.txt
if errorlevel 1 goto error
echo.
echo Entorno creado correctamente.
pause
exit /b 0
:error
echo.
echo Ocurrio un error. Verifica que Python 3.9 este instalado.
pause
exit /b 1
