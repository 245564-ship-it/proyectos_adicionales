# wrapper.py
import sys
import os
import socket
import threading
import webbrowser
import uvicorn
from pathlib import Path

# Cambia al directorio del script
os.chdir(Path(__file__).parent)

# Importa tu app (SIN MODIFICAR main.py)
from main import app

def get_local_ip():
    """Obtiene la IP local de la PC"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def agregar_endpoint_qr():
    """Agrega el endpoint del QR a tu app (sin modificar main.py)"""
    from fastapi.responses import HTMLResponse
    import qrcode
    from io import BytesIO
    import base64
    
    @app.get("/qr", response_class=HTMLResponse)
    async def get_qr():
        ip = get_local_ip()
        url = f"http://{ip}:8000"
        
        # Genera QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convierte a base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>QR - Conecta tu dispositivo</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    font-family: 'Arial', sans-serif;
                    color: white;
                    padding: 20px;
                }}
                .container {{
                    background: rgba(0,0,0,0.3);
                    padding: 40px;
                    border-radius: 20px;
                    text-align: center;
                    backdrop-filter: blur(10px);
                    max-width: 400px;
                }}
                h1 {{
                    margin-bottom: 30px;
                    font-size: 28px;
                }}
                .qr-box {{
                    background: white;
                    padding: 20px;
                    border-radius: 15px;
                    display: inline-block;
                    margin-bottom: 30px;
                }}
                .qr-box img {{
                    width: 300px;
                    height: 300px;
                    display: block;
                }}
                .url-box {{
                    background: rgba(0,0,0,0.4);
                    padding: 15px;
                    border-radius: 10px;
                    margin-top: 20px;
                    word-break: break-all;
                    font-size: 16px;
                    font-weight: bold;
                }}
                .instruction {{
                    margin-top: 30px;
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .status {{
                    margin-top: 20px;
                    padding: 10px;
                    background: rgba(76, 175, 80, 0.3);
                    border-radius: 5px;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📱 Escanea para conectarte</h1>
                
                <div class="qr-box">
                    <img src="data:image/png;base64,{img_str}" alt="QR Code">
                </div>
                
                <h2>O usa esta URL:</h2>
                <div class="url-box">{url}</div>
                
                <div class="instruction">
                    <p>✅ Asegúrate que tu dispositivo está en la <strong>misma WiFi</strong></p>
                </div>
                
                <div class="status">
                    🟢 API EN LÍNEA | Puerto: 8000
                </div>
            </div>
        </body>
        </html>
        """

def abrir_navegador(ip, puerto):
    """Abre el navegador automáticamente después de 1 segundo"""
    import time
    time.sleep(1)
    try:
        webbrowser.open(f"http://{ip}:{puerto}/qr")
    except:
        pass

def run_server():
    """Ejecuta el servidor FastAPI"""
    ip = get_local_ip()
    puerto = 8000
    
    # Agrega el endpoint del QR (sin tocar main.py)
    agregar_endpoint_qr()
    
    # Muestra información en la consola
    print("\n" + "="*70)
    print("🚀 API INICIADA CORRECTAMENTE")
    print("="*70)
    print(f"📱 DESDE CELULAR: http://{ip}:{puerto}")
    print(f"💻 DESDE ESTA PC: http://localhost:{puerto}")
    print(f"🎯 QR CODE: http://localhost:{puerto}/qr")
    print("="*70)
    print("✅ Se abrirá automáticamente una ventana con el QR...")
    print("="*70 + "\n")
    
    # Abre el navegador automáticamente
    threading.Thread(target=abrir_navegador, args=(ip, puerto), daemon=True).start()
    
    # Inicia el servidor
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=puerto,
        log_level="info"
    )

if __name__ == "__main__":
    # Oculta la consola en Windows si se ejecuta como .exe
    if sys.platform == 'win32' and getattr(sys, 'frozen', False):
        import ctypes
        try:
            ctypes.windll.kernel32.FreeConsole()
        except:
            pass
    
    run_server()