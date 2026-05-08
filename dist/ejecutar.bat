@echo off
REM Ejecutar API y abrir navegador en Windows

REM Inicia la API en background
start /B api.exe

REM Espera 2 segundos para que se inicie
timeout /t 2 /nobreak

REM Abre el navegador en http://127.0.0.1:8000
start http://127.0.0.1:8000

REM Muestra un mensaje
echo.
echo ============================================================
echo API INICIADA
echo ============================================================
echo Tu navegador se abrira en: http://127.0.0.1:8000
echo QR disponible en: http://127.0.0.1:8000/qr
echo ============================================================
echo.

REM Mantiene la ventana abierta
pause