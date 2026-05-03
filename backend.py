#importacion de modulos
from datetime import datetime
from collections import Counter
import math


                                    # ENTONCES LAS COLUMNAS SERAN 10, lo primero seria el id para el diccionario 

                                    #los datos en orden son fecha, nombre del paciente, procedimiento, cuantas sesiones, proxima fecha,
                                    #nro whatsapp, si tiene diabetes, si tiene hipertencion, antecedentes, edad

                                    #el dato que va a mandar es el nombre del paciente, principalmente una funcion para ver su informacion 
                                    #por fechas
                                    #fechas automaticas

#algoritmos y estructura de datos
###diccionario master####
informacion = {
    "julio": ("a1", "b2", "c3", "d4", "1001", "no", "no", "oño", "ono"),
    "julo": ("x1", "y2", "z3", "p9", "2002", "si", "no", "uno", "una"),
    "julian": ("k1", "k2", "k3", "k4", "3003", "no", "si", "dos", "dos"),
    "julia": ("m1", "m2", "m3", "m4", "4004", "si", "si", "tres", "tres"),
    "julieta": ("q1", "q2", "q3", "q4", "5005", "no", "no", "cuatro", "cuatro"),
    
    "juan": ("u1", "u2", "u3", "u4", "6006", "si", "no", "cinco", "cinco"),
    "juam": ("v1", "v2", "v3", "v4", "6007", "no", "si", "seis", "seis"),
    "juán": ("w1", "w2", "w3", "w4", "6008", "si", "si", "siete", "siete"),
    
    "maria": ("r1", "r2", "r3", "r4", "7007", "no", "no", "ocho", "ocho"),
    "maría": ("s1", "s2", "s3", "s4", "7008", "si", "no", "nueve", "nueve"),
    "marya": ("t1", "t2", "t3", "t4", "7009", "no", "si", "diez", "diez"),
    
    "pedro": ("p1", "p2", "p3", "p4", "8008", "si", "no", "once", "once"),
    "petero": ("p5", "p6", "p7", "p8", "8009", "no", "si", "doce", "doce"),
    "pedroa": ("p9", "p10", "p11", "p12", "8010", "si", "si", "trece", "trece"),
    
    "carlos": ("c1", "c2", "c3", "c4", "9009", "no", "no", "catorce", "catorce"),
    "carlo": ("c5", "c6", "c7", "c8", "9010", "si", "no", "quince", "quince"),
    "karlo": ("c9", "c10", "c11", "c12", "9011", "no", "si", "dieciseis", "dieciseis"),
    
    "andres": ("a10", "a11", "a12", "a13", "1111", "si", "no", "diecisiete", "diecisiete"),
    "andrez": ("a14", "a15", "a16", "a17", "1112", "no", "si", "dieciocho", "dieciocho"),
    "andre": ("a18", "a19", "a20", "a21", "1113", "si", "si", "diecinueve", "diecinueve"),
}

####trie para el nombre####
class NodoTrie:
    def __init__(self):
        self.hijos = {}        # {'a': NodoTrie, 'b': NodoTrie, ...}
        self.es_fin = False    # marca si aquí termina una palabra

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
        """Navega hasta el nodo donde termina el prefijo."""
        nodo = self.raiz
        for letra in prefijo.lower():
            if letra not in nodo.hijos:
                return None  # el prefijo no existe
            nodo = nodo.hijos[letra]
        return nodo

    def sugerir(self, prefijo):
        """Devuelve todas las palabras que empiezan con el prefijo."""
        nodo = self._buscar_nodo(prefijo)
        if not nodo:
            return []

        resultados = []
        self._recolectar(nodo, prefijo.lower(), resultados)
        return resultados

    def _recolectar(self, nodo, palabra_actual, resultados):
        """Recorre el árbol en profundidad acumulando palabras completas."""
        if nodo.es_fin:
            resultados.append(palabra_actual)
        for letra, hijo in nodo.hijos.items():
            self._recolectar(hijo, palabra_actual + letra, resultados)


#######transofrmar texto a ngramas#####
def ngramas(texto, n=3):
    texto = texto.lower().replace(" ", "")
    return [texto[i:i+n] for i in range(len(texto)-n+1)]

###vectorizando los ngramas#####
def texto_a_vector(texto, n=3):
    return Counter(ngramas(texto, n))

####producto coseno par sugerencias###
def similitud_coseno(vec_a, vec_b):
    interseccion = set(vec_a) & set(vec_b)

    num = sum(vec_a[x] * vec_b[x] for x in interseccion)

    denom_a = math.sqrt(sum(v*v for v in vec_a.values()))
    denom_b = math.sqrt(sum(v*v for v in vec_b.values()))

    if denom_a == 0 or denom_b == 0:
        return 0

    return num / (denom_a * denom_b)








#pagina principal

#barra de busqueda input para el nombre y que al poner tipo yape busque y si no hay coincidencia sugiera crear 
####################################################
####nomb = str(input("Nombre del paciente: "))######
####################################################
def buscar(trie, catalogo, query):

    palabras_query = query.lower().split()

    # -------------------------
    # 1. FILTRO TRIE
    # -------------------------
    candidatos = set()
    for palabra in palabras_query:
        candidatos.update(trie.sugerir(palabra))

    # -------------------------
    # 2. VECTOR QUERY (n-gramas)
    # -------------------------
    vec_query = texto_a_vector(query)

    resultados = []

    # -------------------------
    # 3. FILTRADO + COSENO
    # -------------------------
    for item in catalogo:
        item_lower = item.lower()

        # fallback importante:
        # si no hay candidatos, no bloquear búsqueda
        if candidatos:
            if not any(c in item_lower for c in candidatos):
                continue

        vec_item = texto_a_vector(item)

        score = similitud_coseno(vec_query, vec_item)
        resultados.append((score, item))

    # -------------------------
    # 4. ORDENAR
    # -------------------------
    resultados.sort(reverse=True)

    return [item for score, item in resultados if score > 0]

def crear():
    fecha = datetime.now()
    procedimiento = str(input("que procedimiento tuvo el paciente: "))
    nro_sesiones = str(input("que nro de sesion del paciente es esta: "))
    proxima_sesion = str(input("cuando sera la proxima sesion: "))
    nro_whatsapp = str(input("cual es el numero de whatsapp del paciente: "))
    tiene_diabetes = str(input("¿el paciente tiene diabetes?: "))
    tiene_hipertension = str(input("¿el paciente tiene hipertension?: "))
    antecedentes = str(input("antecedentes del paciente: "))
    edad = str(input("edad del paciente: "))

    trie.insertar(nomb)

    informacion[nomb] = (fecha, procedimiento, nro_sesiones, proxima_sesion, nro_whatsapp, tiene_diabetes, tiene_hipertension, 
    antecedentes, edad)
    
    return informacion[nomb]





###uso del programa###

trie = Trie()
query = str(input("introduce el nombre que deseas buscar"))
#crear()
resultados = buscar(trie, list(informacion.keys()), query)
print(resultados)

#mostrar por fecha esta semana que pacientes tienen consulta y su hora 



#opcion de mostrar en pantalla informacion del paciente
#aun no
