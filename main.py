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
    proxima_sesion TEXT,
    nro_whatsapp TEXT,
    tiene_diabetes TEXT,
    tiene_hipertension TEXT,
    antecedentes TEXT,
    edad INTEGER
)
""")
conexion.commit()

# ==============================
# DATA
# ==============================
informacion = {
    "julio": (),
    "julo": (),
    "julian": (),
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


################agregado en el commit owo###############

@app.get("/paciente")
def obtener_paciente(nombre: str):
    cursor.execute("SELECT * FROM productos WHERE nombre = ?", (nombre,))
    row = cursor.fetchone()

    if not row:
        return {"error": "No encontrado"}

    keys = ["nombre","fecha","procedimiento","nro_sesiones","proxima_sesion",
            "nro_whatsapp","tiene_diabetes","tiene_hipertension","antecedentes","edad"]

    return dict(zip(keys, row))


@app.post("/crear")
def crear_paciente(data: dict):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO productos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nombre"],
        fecha,
        data["procedimiento"],
        int(data["nro_sesiones"]),
        data["proxima_sesion"],
        data["nro_whatsapp"],
        data["tiene_diabetes"],
        data["tiene_hipertension"],
        data["antecedentes"],
        int(data["edad"])
    ))

    conexion.commit()

    # actualizar trie en caliente
    trie.insertar(data["nombre"])

    return {"ok": True}