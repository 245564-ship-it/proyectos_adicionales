from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
from datetime import datetime
from collections import Counter
import math
 
app = FastAPI()
 
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
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_paciente TEXT NOT NULL,
    fecha_sesion TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    duracion_minutos INTEGER NOT NULL DEFAULT 60,
    procedimiento TEXT,
    notas TEXT,
    estado TEXT DEFAULT 'pendiente',
    asistencia TEXT DEFAULT NULL,
    fecha_registro TEXT DEFAULT NULL,
    FOREIGN KEY (nombre_paciente) REFERENCES productos(nombre)
)
""")

# Migrar columnas si no existen (para bases de datos existentes)
try:
    cursor.execute("ALTER TABLE sesiones ADD COLUMN asistencia TEXT DEFAULT NULL")
except:
    pass
try:
    cursor.execute("ALTER TABLE sesiones ADD COLUMN fecha_registro TEXT DEFAULT NULL")
except:
    pass

conexion.commit()
 
# ==============================
# DATA DE EJEMPLO
# ==============================
informacion = {
    "julio": (),
    "julo": (),
    "julian": (),
}
 
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

    # Contar sesiones asistidas (completadas con asistencia=si)
    cursor.execute("""
        SELECT COUNT(*) FROM sesiones
        WHERE nombre_paciente = ? AND asistencia = 'si'
    """, (nombre,))
    sesiones_asistidas = cursor.fetchone()[0]
    paciente["sesiones_asistidas"] = sesiones_asistidas

    # Determinar estado del procedimiento
    nro_programadas = paciente.get("nro_sesiones", 0) or 0
    if nro_programadas > 0 and sesiones_asistidas >= nro_programadas:
        paciente["estado_procedimiento"] = "completado"
    else:
        paciente["estado_procedimiento"] = "en_progreso"

    cursor.execute("""
        SELECT id, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado, asistencia, fecha_registro
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
            "estado": f[6],
            "asistencia": f[7],
            "fecha_registro": f[8] or ""
        })

    return {
        "paciente": paciente,
        "sesiones": sesiones
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
    duracion_minutos = data.get("duracion_minutos", "").strip() if isinstance(data.get("duracion_minutos", ""), str) else data.get("duracion_minutos", 60)

    if fecha_sesion and hora_inicio:
        try:
            duracion_minutos = int(duracion_minutos or 60)
        except (ValueError, TypeError):
            duracion_minutos = 60

        cursor.execute("""
            INSERT INTO sesiones
            (nombre_paciente, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?, 'pendiente', ?)
        """, (
            nombre,
            fecha_sesion,
            hora_inicio,
            duracion_minutos,
            data.get("procedimiento", ""),
            data.get("notas", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
               s.duracion_minutos, s.procedimiento, s.notas, s.estado, s.asistencia
        FROM sesiones s
        WHERE s.fecha_sesion >= ? AND s.fecha_sesion <= ?
          AND (s.estado = 'pendiente' OR s.estado = 'completada')
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
            "estado": f[7],
            "asistencia": f[8]
        })
 
    return {
        "semana_inicio": fecha_inicio,
        "semana_fin": sabado.strftime("%Y-%m-%d"),
        "sesiones": sesiones
    }

@app.post("/sesion/marcar_asistencia/{sesion_id}")
def marcar_asistencia(sesion_id: int, data: dict):
    """
    Marca si el paciente asistió o no a la sesión.
    asistencia: 'si' | 'no'
    Si asistió, marca la sesión como completada.
    """
    asistencia = data.get("asistencia", "no")
    fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if asistencia == "si":
        cursor.execute("""
            UPDATE sesiones 
            SET estado='completada', asistencia='si', fecha_registro=?
            WHERE id=?
        """, (fecha_registro, sesion_id))
    else:
        cursor.execute("""
            UPDATE sesiones 
            SET estado='completada', asistencia='no', fecha_registro=?
            WHERE id=?
        """, (fecha_registro, sesion_id))

    conexion.commit()
    
    # Devolver info actualizada del paciente para el contador
    cursor.execute("SELECT nombre_paciente FROM sesiones WHERE id=?", (sesion_id,))
    row = cursor.fetchone()
    if row:
        nombre = row[0]
        cursor.execute("""
            SELECT COUNT(*) FROM sesiones
            WHERE nombre_paciente = ? AND asistencia = 'si'
        """, (nombre,))
        asistidas = cursor.fetchone()[0]
        
        cursor.execute("SELECT nro_sesiones FROM productos WHERE nombre=?", (nombre,))
        p = cursor.fetchone()
        nro_programadas = p[0] if p else 0

        # Verificar si se completó el procedimiento
        procedimiento_completado = nro_programadas > 0 and asistidas >= nro_programadas

        return {
            "ok": True,
            "sesion_id": sesion_id,
            "asistencia": asistencia,
            "sesiones_asistidas": asistidas,
            "procedimiento_completado": procedimiento_completado
        }

    return {"ok": True, "sesion_id": sesion_id}

@app.post("/sesion/completar/{sesion_id}")
def completar_sesion(sesion_id: int):
    cursor.execute("UPDATE sesiones SET estado='completada' WHERE id=?", (sesion_id,))
    conexion.commit()
    return {"ok": True, "sesion_id": sesion_id}
 
@app.post("/sesion/nueva")
def nueva_sesion(data: dict):
    """Agrega una nueva sesion a la cola del paciente."""
    nombre_paciente = data.get("nombre_paciente", "")
    fecha_sesion = data.get("fecha_sesion", "")
    hora_inicio = data.get("hora_inicio", "")
    duracion_minutos = int(data.get("duracion_minutos", 60))
    procedimiento = data.get("procedimiento", "")
    notas = data.get("notas", "")
    fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO sesiones (nombre_paciente, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, estado, fecha_registro)
        VALUES (?,?,?,?,?,?,'pendiente',?)
    """, (nombre_paciente, fecha_sesion, hora_inicio, duracion_minutos, procedimiento, notas, fecha_registro))
    conexion.commit()
    return {"ok": True, "id": cursor.lastrowid}

@app.get("/registros")
def obtener_registros():
    """Devuelve todos los registros de sesiones ordenados por fecha de registro."""
    cursor.execute("""
        SELECT s.id, s.nombre_paciente, s.fecha_sesion, s.hora_inicio,
               s.duracion_minutos, s.procedimiento, s.notas, s.estado,
               s.asistencia, s.fecha_registro,
               p.nro_sesiones,
               (SELECT COUNT(*) FROM sesiones s2 WHERE s2.nombre_paciente = s.nombre_paciente AND s2.asistencia = 'si') as sesiones_asistidas
        FROM sesiones s
        LEFT JOIN productos p ON p.nombre = s.nombre_paciente
        WHERE s.fecha_registro IS NOT NULL
        ORDER BY s.fecha_registro DESC
    """)
    filas = cursor.fetchall()
    registros = []
    for f in filas:
        registros.append({
            "id": f[0],
            "paciente": f[1],
            "fecha_sesion": f[2],
            "hora_inicio": f[3],
            "duracion_minutos": f[4],
            "procedimiento": f[5] or "",
            "notas": f[6] or "",
            "estado": f[7],
            "asistencia": f[8],
            "fecha_registro": f[9],
            "nro_sesiones_programadas": f[10] or 0,
            "sesiones_asistidas": f[11] or 0
        })
    return {"registros": registros}