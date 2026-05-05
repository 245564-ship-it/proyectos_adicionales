from fastapi import FastAPI
from fastapi import FastAPI, HTTPException
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
 
cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_paciente TEXT NOT NULL,
    sesion_id INTEGER,
    asistio INTEGER NOT NULL,
    fecha_registro TEXT NOT NULL,
    observacion TEXT,
    FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
)
""")
conexion.commit()

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
 
def resumen_paciente(nombre: str):
    cursor.execute("SELECT nro_sesiones FROM productos WHERE nombre = ?", (nombre,))
    row = cursor.fetchone()
    if not row:
        return None

    programadas = int(row[0] or 0)

    cursor.execute("""
        SELECT COUNT(*)
        FROM sesiones
        WHERE nombre_paciente = ? AND estado = 'completada'
    """, (nombre,))
    completadas = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM sesiones
        WHERE nombre_paciente = ? AND estado = 'no_asistio'
    """, (nombre,))
    no_asistio = cursor.fetchone()[0]

    estado = "Procedimiento completado" if programadas > 0 and completadas >= programadas else "En proceso"

    cursor.execute("""
        SELECT fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado
        FROM sesiones
        WHERE nombre_paciente = ? AND estado = 'pendiente'
        ORDER BY fecha_sesion, hora_inicio
        LIMIT 1
    """, (nombre,))
    prox = cursor.fetchone()

    proxima_sesion = None
    if prox:
        proxima_sesion = {
            "fecha_sesion": prox[0],
            "hora_inicio": prox[1],
            "duracion_minutos": prox[2],
            "procedimiento": prox[3] or "",
            "notas": prox[4] or "",
            "estado": prox[5]
        }

    return {
        "programadas": programadas,
        "completadas": completadas,
        "no_asistio": no_asistio,
        "estado": estado,
        "proxima_sesion": proxima_sesion
    }

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
 
def catalogo_nombres():
    cursor.execute("SELECT nombre FROM productos")
    nombres_db = [r[0] for r in cursor.fetchall()]
    return sorted(set(list(informacion.keys()) + nombres_db))


def buscar(query):
    query = query.strip()
    if not query:
        return []

    vec_q = texto_a_vector(query)
    resultados = []

    for item in catalogo_nombres():
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
 
@app.get("/paciente")
def obtener_paciente(nombre: str):
    cursor.execute("SELECT * FROM productos WHERE nombre = ?", (nombre,))
    row = cursor.fetchone()

    if not row:
        return {"error": "No encontrado"}

    keys = [
        "nombre", "fecha", "procedimiento", "nro_sesiones",
        "nro_whatsapp", "tiene_diabetes", "tiene_hipertension",
        "antecedentes", "edad"
    ]
    paciente = dict(zip(keys, row))

    cursor.execute("""
        SELECT id, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado
        FROM sesiones
        WHERE nombre_paciente = ?
        ORDER BY fecha_sesion, hora_inicio
    """, (nombre,))
    filas = cursor.fetchall()

    sesiones = []
    for f in filas:
        sesiones.append({
            "id": f[0],
            "fecha_sesion": f[1],
            "hora_inicio": f[2],
            "duracion_minutos": f[3],
            "procedimiento": f[4] or "",
            "notas": f[5] or "",
            "estado": f[6]
        })

    cursor.execute("""
        SELECT id, sesion_id, asistio, fecha_registro, observacion
        FROM registros
        WHERE nombre_paciente = ?
        ORDER BY fecha_registro DESC
    """, (nombre,))
    filas_reg = cursor.fetchall()

    registros = []
    for r in filas_reg:
        registros.append({
            "id": r[0],
            "sesion_id": r[1],
            "asistio": bool(r[2]),
            "fecha_registro": r[3],
            "observacion": r[4] or ""
        })

    return {
        "paciente": paciente,
        "sesiones": sesiones,
        "resumen": resumen_paciente(nombre),
        "registros": registros
    }

@app.post("/crear_paciente")
def crear_paciente(data: dict):
    try:
        nombre = data.get("nombre", "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre es obligatorio")

        nro_sesiones = int(data.get("nro_sesiones", 0))
        edad = int(data.get("edad", 0))
    except ValueError:
        raise HTTPException(status_code=400, detail="Sesiones y edad deben ser números")

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT OR REPLACE INTO productos
        (nombre, fecha, procedimiento, nro_sesiones, nro_whatsapp, tiene_diabetes, tiene_hipertension, antecedentes, edad)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nombre,
        fecha,
        data.get("procedimiento", ""),
        nro_sesiones,
        data.get("nro_whatsapp", ""),
        data.get("tiene_diabetes", ""),
        data.get("tiene_hipertension", ""),
        data.get("antecedentes", ""),
        edad
    ))

    fecha_sesion = data.get("fecha_sesion", "").strip()
    hora_inicio = data.get("hora_inicio", "").strip()
    duracion_minutos = data.get("duracion_minutos", "").strip()
    notas = data.get("notas", "").strip()

    if fecha_sesion and hora_inicio:
        try:
            duracion_minutos = int(duracion_minutos or 60)
        except ValueError:
            duracion_minutos = 60

        cursor.execute("""
            INSERT INTO sesiones
            (nombre_paciente, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado)
            VALUES (?, ?, ?, ?, ?, ?, 'pendiente')
        """, (
            nombre,
            fecha_sesion,
            hora_inicio,
            duracion_minutos,
            data.get("procedimiento", ""),
            notas
        ))

    conexion.commit()
    trie.insertar(nombre)
    informacion[nombre] = ()

    return {"ok": True, "nombre": nombre}

@app.get("/calendario")
def calendario_api(fecha_inicio: str = ""):
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

@app.post("/sesion/marcar/{sesion_id}")
def marcar_sesion(sesion_id: int, data: dict):
    asistio = bool(data.get("asistio", False))

    cursor.execute("""
        SELECT nombre_paciente, estado
        FROM sesiones
        WHERE id = ?
    """, (sesion_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    nombre_paciente, estado_actual = row
    nuevo_estado = "completada" if asistio else "no_asistio"

    cursor.execute("""
        UPDATE sesiones
        SET estado = ?
        WHERE id = ?
    """, (nuevo_estado, sesion_id))

    fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO registros (nombre_paciente, sesion_id, asistio, fecha_registro, observacion)
        VALUES (?, ?, ?, ?, ?)
    """, (
        nombre_paciente,
        sesion_id,
        1 if asistio else 0,
        fecha_registro,
        "Paciente asistió" if asistio else "Paciente no asistió"
    ))

    conexion.commit()
    return {"ok": True, "nombre_paciente": nombre_paciente, "estado": nuevo_estado}