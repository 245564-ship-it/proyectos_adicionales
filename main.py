from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
from datetime import datetime
from collections import Counter
import math
 
app = FastAPI()
 
# ==============================
# STATIC FILES (CSS)
# ==============================
app.mount("/static", StaticFiles(directory="static"), name="static")
 
# ==============================
# BD
# ==============================
conexion = sqlite3.connect("datos.db", check_same_thread=False)
cursor = conexion.cursor()
 
cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    nombre TEXT PRIMARY KEY,
    fecha TEXT,
    procedimiento TEXT,
    nro_sesiones INTEGER,
    nro_whatsapp TEXT,
    tiene_diabetes TEXT,
    tiene_hipertension TEXT,
    antecedentes TEXT,
    edad INTEGER
)
""")
 
# Cola de sesiones: cada fila es una sesion pendiente de un paciente
# estado: 'pendiente' | 'completada' | 'cancelada'
cursor.execute("""
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_paciente TEXT NOT NULL,
    fecha_sesion TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    duracion_minutos INTEGER NOT NULL DEFAULT 60,
    procedimiento TEXT,
    notas TEXT,
    estado TEXT DEFAULT 'pendiente',
    FOREIGN KEY (nombre_paciente) REFERENCES productos(nombre)
)
""")
 
conexion.commit()
 
# ==============================
# DATA DE EJEMPLO
# ==============================
informacion = {
    "julio": (),
    "julo": (),
    "julian": (),
}
 
# Insertar datos de ejemplo si la tabla esta vacia
cursor.execute("SELECT COUNT(*) FROM sesiones")
if cursor.fetchone()[0] == 0:
    sesiones_ejemplo = [
        ("julio", "2025-07-14", "09:00", 60, "Limpieza facial", "Primera sesion", "pendiente"),
        ("julian", "2025-07-14", "11:00", 90, "Tratamiento capilar", "", "pendiente"),
        ("julo", "2025-07-15", "10:00", 60, "Hidratacion", "", "pendiente"),
        ("julio", "2025-07-16", "14:00", 60, "Seguimiento", "", "pendiente"),
        ("julian", "2025-07-17", "09:30", 120, "Tratamiento completo", "", "pendiente"),
    ]
    cursor.executemany(
        "INSERT INTO sesiones (nombre_paciente, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado) VALUES (?,?,?,?,?,?,?)",
        sesiones_ejemplo
    )
    conexion.commit()
 
# ==============================
# TRIE
# ==============================
class NodoTrie:
    def __init__(self):
        self.hijos = {}
        self.es_fin = False
 
class Trie:
    def __init__(self):
        self.raiz = NodoTrie()
 
    def insertar(self, palabra):
        nodo = self.raiz
        for letra in palabra.lower():
            nodo = nodo.hijos.setdefault(letra, NodoTrie())
        nodo.es_fin = True
 
    def sugerir(self, prefijo):
        def dfs(nodo, palabra):
            if nodo.es_fin:
                resultados.append(palabra)
            for l, h in nodo.hijos.items():
                dfs(h, palabra + l)
        nodo = self.raiz
        for letra in prefijo.lower():
            if letra not in nodo.hijos:
                return []
            nodo = nodo.hijos[letra]
        resultados = []
        dfs(nodo, prefijo.lower())
        return resultados
 
trie = Trie()
for nombre in informacion:
    trie.insertar(nombre)
 
# ==============================
# BUSQUEDA
# ==============================
def ngramas(texto, n=3):
    texto = texto.lower().replace(" ", "")
    return [texto[i:i+n] for i in range(len(texto)-n+1)]
 
def texto_a_vector(texto):
    return Counter(ngramas(texto))
 
def similitud_coseno(a, b):
    inter = set(a) & set(b)
    num = sum(a[x]*b[x] for x in inter)
    den_a = math.sqrt(sum(v*v for v in a.values()))
    den_b = math.sqrt(sum(v*v for v in b.values()))
    if not den_a or not den_b:
        return 0
    return num/(den_a*den_b)
 
def buscar(query):
    vec_q = texto_a_vector(query)
    resultados = []
    for item in informacion:
        vec_item = texto_a_vector(item)
        score = similitud_coseno(vec_q, vec_item)
        if score > 0:
            resultados.append((score, item))
    resultados.sort(reverse=True)
    nombres = [r[1] for r in resultados]
    nombres.insert(0, f"➕ Crear '{query}'")
    return nombres
 
# ==============================
# RUTAS
# ==============================
@app.get("/", response_class=HTMLResponse)
def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()
 
@app.get("/buscar")
def buscar_api(q: str = ""):
    return buscar(q)
 
@app.get("/calendario")
def calendario_api(fecha_inicio: str = ""):
    """
    Devuelve las sesiones de la semana indicada.
    fecha_inicio: lunes de la semana en formato YYYY-MM-DD
    Si no se indica, usa la semana actual.
    """
    if not fecha_inicio:
        hoy = datetime.now()
        lunes = hoy - __import__('datetime').timedelta(days=hoy.weekday())
        fecha_inicio = lunes.strftime("%Y-%m-%d")
 
    import datetime as dt
    lunes = dt.datetime.strptime(fecha_inicio, "%Y-%m-%d")
    sabado = lunes + dt.timedelta(days=5)
 
    cursor.execute("""
        SELECT s.id, s.nombre_paciente, s.fecha_sesion, s.hora_inicio,
               s.duracion_minutos, s.procedimiento, s.notas, s.estado
        FROM sesiones s
        WHERE s.fecha_sesion >= ? AND s.fecha_sesion <= ?
          AND s.estado = 'pendiente'
        ORDER BY s.fecha_sesion, s.hora_inicio
    """, (fecha_inicio, sabado.strftime("%Y-%m-%d")))
 
    filas = cursor.fetchall()
    sesiones = []
    for f in filas:
        sesiones.append({
            "id": f[0],
            "paciente": f[1],
            "fecha": f[2],
            "hora_inicio": f[3],
            "duracion_minutos": f[4],
            "procedimiento": f[5] or "",
            "notas": f[6] or "",
            "estado": f[7]
        })
 
    return {
        "semana_inicio": fecha_inicio,
        "semana_fin": sabado.strftime("%Y-%m-%d"),
        "sesiones": sesiones
    }
 
@app.post("/sesion/completar/{sesion_id}")
def completar_sesion(sesion_id: int):
    """Marca la sesion como completada (desencola la cabeza de la cola del paciente)."""
    cursor.execute("UPDATE sesiones SET estado='completada' WHERE id=?", (sesion_id,))
    conexion.commit()
    return {"ok": True, "sesion_id": sesion_id}
 
@app.post("/sesion/nueva")
def nueva_sesion(
    nombre_paciente: str,
    fecha_sesion: str,
    hora_inicio: str,
    duracion_minutos: int = 60,
    procedimiento: str = "",
    notas: str = ""
):
    """Agrega una nueva sesion a la cola del paciente."""
    cursor.execute("""
        INSERT INTO sesiones (nombre_paciente, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado)
        VALUES (?,?,?,?,?,?,'pendiente')
    """, (nombre_paciente, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas))
    conexion.commit()
    return {"ok": True, "id": cursor.lastrowid}
