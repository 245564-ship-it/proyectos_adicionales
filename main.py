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
    nro_whatsapp TEXT,
    tiene_diabetes TEXT,
    tiene_hipertension TEXT,
    antecedentes TEXT,
    edad INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS procedimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_paciente TEXT NOT NULL,
    nombre_procedimiento TEXT NOT NULL,
    nro_sesiones INTEGER NOT NULL DEFAULT 1,
    fecha_inicio TEXT,
    estado TEXT DEFAULT 'en_progreso',
    FOREIGN KEY (nombre_paciente) REFERENCES productos(nombre)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_paciente TEXT NOT NULL,
    procedimiento_id INTEGER,
    fecha_sesion TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    duracion_minutos INTEGER NOT NULL DEFAULT 60,
    procedimiento TEXT,
    notas TEXT,
    estado TEXT DEFAULT 'pendiente',
    asistencia TEXT DEFAULT NULL,
    fecha_registro TEXT DEFAULT NULL,
    FOREIGN KEY (nombre_paciente) REFERENCES productos(nombre),
    FOREIGN KEY (procedimiento_id) REFERENCES procedimientos(id)
)
""")

# Migraciones para BD existentes
for sql in [
    "ALTER TABLE sesiones ADD COLUMN asistencia TEXT DEFAULT NULL",
    "ALTER TABLE sesiones ADD COLUMN fecha_registro TEXT DEFAULT NULL",
    "ALTER TABLE sesiones ADD COLUMN procedimiento_id INTEGER",
    "ALTER TABLE productos ADD COLUMN procedimiento TEXT",
    "ALTER TABLE productos ADD COLUMN nro_sesiones INTEGER",
]:
    try:
        cursor.execute(sql)
    except Exception:
        pass

conexion.commit()

# Migrar datos viejos: procedimiento/nro_sesiones de productos → tabla procedimientos
try:
    cursor.execute("SELECT nombre, procedimiento, nro_sesiones FROM productos WHERE procedimiento IS NOT NULL AND procedimiento != ''")
    for row in cursor.fetchall():
        nombre, proc, nro = row
        cursor.execute("SELECT COUNT(*) FROM procedimientos WHERE nombre_paciente=? AND nombre_procedimiento=?", (nombre, proc))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO procedimientos (nombre_paciente, nombre_procedimiento, nro_sesiones, fecha_inicio, estado)
                VALUES (?,?,?,?,'en_progreso')
            """, (nombre, proc or "Sin nombre", nro or 1, datetime.now().strftime("%Y-%m-%d")))
    conexion.commit()
except Exception:
    pass

# ==============================
# DATOS DE EJEMPLO
# ==============================
informacion = {"julio": (), "julo": (), "julian": ()}

cursor.execute("SELECT COUNT(*) FROM sesiones")
if cursor.fetchone()[0] == 0:
    for nombre in ["julio", "julo", "julian"]:
        cursor.execute("SELECT COUNT(*) FROM productos WHERE nombre=?", (nombre,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO productos (nombre, fecha, nro_whatsapp, tiene_diabetes, tiene_hipertension, antecedentes, edad)
                VALUES (?,?,?,?,?,?,?)
            """, (nombre, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", "no", "no", "", 30))

    cursor.execute("""
        INSERT INTO procedimientos (nombre_paciente, nombre_procedimiento, nro_sesiones, fecha_inicio)
        VALUES ('julio','Limpieza facial',3,'2025-07-01'),
               ('julian','Tratamiento capilar',5,'2025-07-01'),
               ('julo','Hidratacion',2,'2025-07-01')
    """)
    # Obtener los IDs insertados
    cursor.execute("SELECT id, nombre_paciente FROM procedimientos ORDER BY id")
    procs = {row[1]: row[0] for row in cursor.fetchall()}

    sesiones_ej = [
        ("julio",  procs.get("julio"),  "2025-07-14", "09:00", 60,  "Limpieza facial",    "", "pendiente"),
        ("julian", procs.get("julian"), "2025-07-14", "11:00", 90,  "Tratamiento capilar","", "pendiente"),
        ("julo",   procs.get("julo"),   "2025-07-15", "10:00", 60,  "Hidratacion",         "", "pendiente"),
        ("julio",  procs.get("julio"),  "2025-07-16", "14:00", 60,  "Limpieza facial",    "", "pendiente"),
        ("julian", procs.get("julian"), "2025-07-17", "09:30", 120, "Tratamiento capilar","", "pendiente"),
    ]
    cursor.executemany("""
        INSERT INTO sesiones (nombre_paciente, procedimiento_id, fecha_sesion, hora_inicio,
            duracion_minutos, procedimiento, notas, estado)
        VALUES (?,?,?,?,?,?,?,?)
    """, sesiones_ej)
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
cursor.execute("SELECT nombre FROM productos")
for row in cursor.fetchall():
    trie.insertar(row[0])
    informacion[row[0]] = ()

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
    return num / (den_a * den_b)

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
# HELPERS
# ==============================
def sesiones_asistidas(nombre_paciente, procedimiento_id):
    cursor.execute("""
        SELECT COUNT(*) FROM sesiones
        WHERE nombre_paciente=? AND procedimiento_id=? AND asistencia='si'
    """, (nombre_paciente, procedimiento_id))
    return cursor.fetchone()[0]

def estado_procedimiento(nro_programadas, asistidas):
    if nro_programadas > 0 and asistidas >= nro_programadas:
        return "completado"
    return "en_progreso"

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

@app.get("/paciente_base")
def obtener_paciente_base(nombre: str):
    """Datos base del paciente para pre-rellenar formulario de creación."""
    cursor.execute("SELECT * FROM productos WHERE nombre=?", (nombre,))
    row = cursor.fetchone()
    if not row:
        return {"existe": False}
    col_names = [d[0] for d in cursor.description]
    pac = dict(zip(col_names, row))
    pac["existe"] = True
    # Último procedimiento para sugerir
    cursor.execute("""
        SELECT nombre_procedimiento, nro_sesiones FROM procedimientos
        WHERE nombre_paciente=? ORDER BY id DESC LIMIT 1
    """, (nombre,))
    ultimo = cursor.fetchone()
    pac["ultimo_procedimiento"] = ultimo[0] if ultimo else ""
    pac["ultima_nro_sesiones"] = ultimo[1] if ultimo else 1
    return pac

@app.get("/paciente")
def obtener_paciente(nombre: str):
    cursor.execute("SELECT * FROM productos WHERE nombre=?", (nombre,))
    row = cursor.fetchone()
    if not row:
        return {"error": "No encontrado"}
    col_names = [d[0] for d in cursor.description]
    paciente = dict(zip(col_names, row))

    cursor.execute("""
        SELECT id, nombre_procedimiento, nro_sesiones, fecha_inicio, estado
        FROM procedimientos WHERE nombre_paciente=? ORDER BY id
    """, (nombre,))
    procs_rows = cursor.fetchall()

    procedimientos_out = []
    for p in procs_rows:
        pid, pnombre, nro, fecha_inicio, estado_proc = p
        asistidas = sesiones_asistidas(nombre, pid)
        estado_real = estado_procedimiento(nro, asistidas)
        if estado_real != estado_proc:
            cursor.execute("UPDATE procedimientos SET estado=? WHERE id=?", (estado_real, pid))
            conexion.commit()

        cursor.execute("""
            SELECT id, fecha_sesion, hora_inicio, duracion_minutos, procedimiento,
                   notas, estado, asistencia, fecha_registro
            FROM sesiones WHERE nombre_paciente=? AND procedimiento_id=?
            ORDER BY fecha_sesion, hora_inicio
        """, (nombre, pid))
        sesiones_list = []
        for s in cursor.fetchall():
            sesiones_list.append({
                "id": s[0], "fecha_sesion": s[1], "hora_inicio": s[2],
                "duracion_minutos": s[3], "procedimiento": s[4] or pnombre,
                "notas": s[5] or "", "estado": s[6],
                "asistencia": s[7], "fecha_registro": s[8] or ""
            })

        procedimientos_out.append({
            "id": pid,
            "nombre_procedimiento": pnombre,
            "nro_sesiones": nro,
            "fecha_inicio": fecha_inicio or "",
            "estado": estado_real,
            "sesiones_asistidas": asistidas,
            "sesiones": sesiones_list
        })

    return {"paciente": paciente, "procedimientos": procedimientos_out}

@app.post("/crear_paciente")
def crear_paciente(data: dict):
    try:
        nombre = data.get("nombre", "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre es obligatorio")
        nro_sesiones = int(data.get("nro_sesiones", 1) or 1)
        edad = int(data.get("edad", 0) or 0)
    except ValueError:
        raise HTTPException(status_code=400, detail="Sesiones y edad deben ser números")

    fecha_ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nombre_proc = data.get("procedimiento", "").strip()

    cursor.execute("SELECT nombre FROM productos WHERE nombre=?", (nombre,))
    existe = cursor.fetchone() is not None

    if existe:
        cursor.execute("""
            UPDATE productos SET nro_whatsapp=?, tiene_diabetes=?,
            tiene_hipertension=?, antecedentes=?, edad=? WHERE nombre=?
        """, (
            data.get("nro_whatsapp", ""), data.get("tiene_diabetes", ""),
            data.get("tiene_hipertension", ""), data.get("antecedentes", ""),
            edad, nombre
        ))
    else:
        cursor.execute("""
            INSERT INTO productos (nombre, fecha, nro_whatsapp, tiene_diabetes, tiene_hipertension, antecedentes, edad)
            VALUES (?,?,?,?,?,?,?)
        """, (
            nombre, fecha_ahora,
            data.get("nro_whatsapp", ""), data.get("tiene_diabetes", ""),
            data.get("tiene_hipertension", ""), data.get("antecedentes", ""),
            edad
        ))

    proc_id = None
    if nombre_proc:
        cursor.execute("""
            SELECT id FROM procedimientos WHERE nombre_paciente=? AND nombre_procedimiento=?
        """, (nombre, nombre_proc))
        proc_existente = cursor.fetchone()

        if proc_existente:
            proc_id = proc_existente[0]
            cursor.execute("UPDATE procedimientos SET nro_sesiones=? WHERE id=?", (nro_sesiones, proc_id))
        else:
            cursor.execute("""
                INSERT INTO procedimientos (nombre_paciente, nombre_procedimiento, nro_sesiones, fecha_inicio, estado)
                VALUES (?,?,?,?,'en_progreso')
            """, (nombre, nombre_proc, nro_sesiones, datetime.now().strftime("%Y-%m-%d")))
            proc_id = cursor.lastrowid

    fecha_sesion = data.get("fecha_sesion", "").strip()
    hora_inicio = data.get("hora_inicio", "").strip()
    if fecha_sesion and hora_inicio and proc_id:
        try:
            dur = int(data.get("duracion_minutos") or 60)
        except (ValueError, TypeError):
            dur = 60
        cursor.execute("""
            INSERT INTO sesiones (nombre_paciente, procedimiento_id, fecha_sesion, hora_inicio,
                duracion_minutos, procedimiento, notas, estado, fecha_registro)
            VALUES (?,?,?,?,?,?,?,'pendiente',?)
        """, (nombre, proc_id, fecha_sesion, hora_inicio, dur,
              nombre_proc, data.get("notas", ""), fecha_ahora))

    conexion.commit()
    trie.insertar(nombre)
    informacion[nombre] = ()
    return {"ok": True, "nombre": nombre, "es_nuevo": not existe}

@app.post("/procedimiento/nuevo")
def nuevo_procedimiento(data: dict):
    nombre = data.get("nombre_paciente", "").strip()
    nombre_proc = data.get("nombre_procedimiento", "").strip()
    nro_sesiones = int(data.get("nro_sesiones", 1) or 1)

    if not nombre or not nombre_proc:
        raise HTTPException(status_code=400, detail="Nombre de paciente y procedimiento son obligatorios")

    cursor.execute("SELECT nombre FROM productos WHERE nombre=?", (nombre,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    cursor.execute("""
        SELECT id FROM procedimientos WHERE nombre_paciente=? AND nombre_procedimiento=?
    """, (nombre, nombre_proc))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Ese procedimiento ya existe para este paciente")

    cursor.execute("""
        INSERT INTO procedimientos (nombre_paciente, nombre_procedimiento, nro_sesiones, fecha_inicio, estado)
        VALUES (?,?,?,?,'en_progreso')
    """, (nombre, nombre_proc, nro_sesiones, datetime.now().strftime("%Y-%m-%d")))
    conexion.commit()
    return {"ok": True, "id": cursor.lastrowid}

@app.get("/calendario")
def calendario_api(fecha_inicio: str = ""):
    if not fecha_inicio:
        hoy = datetime.now()
        import datetime as dt2
        lunes = hoy - dt2.timedelta(days=hoy.weekday())
        fecha_inicio = lunes.strftime("%Y-%m-%d")

    import datetime as dt
    lunes = dt.datetime.strptime(fecha_inicio, "%Y-%m-%d")
    sabado = lunes + dt.timedelta(days=5)

    cursor.execute("""
        SELECT s.id, s.nombre_paciente, s.fecha_sesion, s.hora_inicio,
               s.duracion_minutos, s.procedimiento, s.notas, s.estado, s.asistencia,
               s.procedimiento_id
        FROM sesiones s
        WHERE s.fecha_sesion >= ? AND s.fecha_sesion <= ?
          AND (s.estado = 'pendiente' OR s.estado = 'completada')
        ORDER BY s.fecha_sesion, s.hora_inicio
    """, (fecha_inicio, sabado.strftime("%Y-%m-%d")))

    sesiones = []
    for f in cursor.fetchall():
        sesiones.append({
            "id": f[0], "paciente": f[1], "fecha": f[2],
            "hora_inicio": f[3], "duracion_minutos": f[4],
            "procedimiento": f[5] or "", "notas": f[6] or "",
            "estado": f[7], "asistencia": f[8], "procedimiento_id": f[9]
        })

    return {
        "semana_inicio": fecha_inicio,
        "semana_fin": sabado.strftime("%Y-%m-%d"),
        "sesiones": sesiones
    }

@app.post("/sesion/marcar_asistencia/{sesion_id}")
def marcar_asistencia(sesion_id: int, data: dict):
    asistencia = data.get("asistencia", "no")
    fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE sesiones SET estado='completada', asistencia=?, fecha_registro=? WHERE id=?
    """, (asistencia, fecha_registro, sesion_id))
    conexion.commit()

    cursor.execute("SELECT nombre_paciente, procedimiento_id FROM sesiones WHERE id=?", (sesion_id,))
    row = cursor.fetchone()
    if row:
        nombre, proc_id = row
        asistidas = sesiones_asistidas(nombre, proc_id)
        nro_programadas = 0
        if proc_id:
            cursor.execute("SELECT nro_sesiones FROM procedimientos WHERE id=?", (proc_id,))
            p = cursor.fetchone()
            nro_programadas = p[0] if p else 0
            estado_real = estado_procedimiento(nro_programadas, asistidas)
            cursor.execute("UPDATE procedimientos SET estado=? WHERE id=?", (estado_real, proc_id))
            conexion.commit()

        procedimiento_completado = nro_programadas > 0 and asistidas >= nro_programadas
        return {
            "ok": True, "sesion_id": sesion_id, "asistencia": asistencia,
            "sesiones_asistidas": asistidas,
            "procedimiento_completado": procedimiento_completado
        }

    return {"ok": True, "sesion_id": sesion_id}

@app.post("/sesion/nueva")
def nueva_sesion(data: dict):
    nombre_paciente = data.get("nombre_paciente", "")
    procedimiento_id = data.get("procedimiento_id")
    fecha_sesion = data.get("fecha_sesion", "")
    hora_inicio = data.get("hora_inicio", "")
    duracion_minutos = int(data.get("duracion_minutos", 60) or 60)
    procedimiento = data.get("procedimiento", "")
    notas = data.get("notas", "")
    fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO sesiones (nombre_paciente, procedimiento_id, fecha_sesion, hora_inicio,
            duracion_minutos, procedimiento, notas, estado, fecha_registro)
        VALUES (?,?,?,?,?,?,?,'pendiente',?)
    """, (nombre_paciente, procedimiento_id, fecha_sesion, hora_inicio,
          duracion_minutos, procedimiento, notas, fecha_registro))
    conexion.commit()
    return {"ok": True, "id": cursor.lastrowid}

@app.get("/registros")
def obtener_registros():
    cursor.execute("""
        SELECT s.id, s.nombre_paciente, s.fecha_sesion, s.hora_inicio,
               s.duracion_minutos, s.procedimiento, s.notas, s.estado,
               s.asistencia, s.fecha_registro, s.procedimiento_id,
               pr.nombre_procedimiento, pr.nro_sesiones,
               (SELECT COUNT(*) FROM sesiones s2
                WHERE s2.nombre_paciente=s.nombre_paciente
                  AND s2.procedimiento_id=s.procedimiento_id
                  AND s2.asistencia='si') as sesiones_asistidas
        FROM sesiones s
        LEFT JOIN procedimientos pr ON pr.id = s.procedimiento_id
        WHERE s.fecha_registro IS NOT NULL
        ORDER BY s.fecha_registro DESC
    """)
    registros = []
    for f in cursor.fetchall():
        registros.append({
            "id": f[0], "paciente": f[1], "fecha_sesion": f[2],
            "hora_inicio": f[3], "duracion_minutos": f[4],
            "procedimiento": f[11] or f[5] or "", "notas": f[6] or "",
            "estado": f[7], "asistencia": f[8], "fecha_registro": f[9],
            "procedimiento_id": f[10],
            "nro_sesiones_programadas": f[12] or 0,
            "sesiones_asistidas": f[13] or 0
        })
    return {"registros": registros}
