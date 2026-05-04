# ==============================
# IMPORTS
# ==============================
from datetime import datetime
from collections import Counter
import math
import sqlite3

# ==============================
# BASE DE DATOS (PRIMERO)
# ==============================
conexion = sqlite3.connect("datos.db")
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
# DATA INICIAL
# ==============================
informacion = {
    "julio": ("a1","b2","c3","d4","1001","no","no","oño","ono"),
    "julo": ("x1","y2","z3","p9","2002","si","no","uno","una"),
    "julian": ("k1","k2","k3","k4","3003","no","si","dos","dos"),
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
            if letra not in nodo.hijos:
                nodo.hijos[letra] = NodoTrie()
            nodo = nodo.hijos[letra]
        nodo.es_fin = True

    def _buscar_nodo(self, prefijo):
        nodo = self.raiz
        for letra in prefijo.lower():
            if letra not in nodo.hijos:
                return None
            nodo = nodo.hijos[letra]
        return nodo

    def sugerir(self, prefijo):
        nodo = self._buscar_nodo(prefijo)
        if not nodo:
            return []

        resultados = []
        self._recolectar(nodo, prefijo.lower(), resultados)
        return resultados

    def _recolectar(self, nodo, palabra, resultados):
        if nodo.es_fin:
            resultados.append(palabra)
        for letra, hijo in nodo.hijos.items():
            self._recolectar(hijo, palabra + letra, resultados)

# ==============================
# FUNCIONES DE BUSQUEDA
# ==============================
def ngramas(texto, n=3):
    texto = texto.lower().replace(" ", "")
    return [texto[i:i+n] for i in range(len(texto)-n+1)]

def texto_a_vector(texto, n=3):
    return Counter(ngramas(texto, n))

def similitud_coseno(a, b):
    inter = set(a) & set(b)
    num = sum(a[x] * b[x] for x in inter)

    den_a = math.sqrt(sum(v*v for v in a.values()))
    den_b = math.sqrt(sum(v*v for v in b.values()))

    if den_a == 0 or den_b == 0:
        return 0

    return num / (den_a * den_b)

def buscar(trie, catalogo, query):
    palabras = query.lower().split()

    candidatos = set()
    for p in palabras:
        candidatos.update(trie.sugerir(p))

    vec_q = texto_a_vector(query)
    resultados = []

    for item in catalogo:
        item_lower = item.lower()

        if candidatos:
            if not any(c in item_lower for c in candidatos):
                continue

        vec_item = texto_a_vector(item)
        score = similitud_coseno(vec_q, vec_item)
        resultados.append((score, item))

    resultados.sort(reverse=True)
    return [i for s, i in resultados if s > 0]

# ==============================
# CREAR TRIE Y POBLARLO
# ==============================
trie = Trie()

for nombre in informacion.keys():
    trie.insertar(nombre)

# ==============================
# FUNCION CREAR PACIENTE
# ==============================
def crear():
    nomb = input("Nombre del paciente: ")

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    procedimiento = input("Procedimiento: ")

    while True:
        try:
            nro_sesiones = int(input("Nro sesiones: "))
            break
        except:
            print("Debe ser número")

    proxima_sesion = input("Próxima sesión: ")
    nro_whatsapp = input("WhatsApp: ")
    tiene_diabetes = input("Diabetes: ")
    tiene_hipertension = input("Hipertensión: ")
    antecedentes = input("Antecedentes: ")

    while True:
        try:
            edad = int(input("Edad: "))
            break
        except:
            print("Debe ser número")

    # insertar en trie
    trie.insertar(nomb)

    # guardar en memoria
    informacion[nomb] = (
        fecha, procedimiento, nro_sesiones, proxima_sesion,
        nro_whatsapp, tiene_diabetes, tiene_hipertension,
        antecedentes, edad
    )

    # guardar en sqlite
    cursor.execute("""
    INSERT INTO productos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nomb, fecha, procedimiento, nro_sesiones, proxima_sesion,
        nro_whatsapp, tiene_diabetes, tiene_hipertension,
        antecedentes, edad
    ))

    conexion.commit()

    print("Paciente guardado correctamente")

# ==============================
# MAIN
# ==============================
while True:
    print("\n1. Buscar paciente")
    print("2. Crear paciente")
    print("3. Salir")

    op = input("Opción: ")

    if op == "1":
        q = input("Buscar: ")
        res = buscar(trie, list(informacion.keys()), q)
        print("Resultados:", res)

    elif op == "2":
        crear()

    elif op == "3":
        break