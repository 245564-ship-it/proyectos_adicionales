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
informacion = {}

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
    """
    Calcula el coseno del ángulo entre dos vectores.
    Resultado: 0.0 (nada parecidos) a 1.0 (idénticos)
    """
    # Producto punto: suma de (frecuencia_a * frecuencia_b) por cada palabra común
    palabras_comunes = set(vec_a.keys()) & set(vec_b.keys())
    producto_punto = sum(vec_a[p] * vec_b[p] for p in palabras_comunes)

    # Magnitud de cada vector: raíz de la suma de cuadrados
    magnitud_a = math.sqrt(sum(v**2 for v in vec_a.values()))
    magnitud_b = math.sqrt(sum(v**2 for v in vec_b.values()))

    if magnitud_a == 0 or magnitud_b == 0:
        return 0.0

    return producto_punto / (magnitud_a * magnitud_b)








#pagina principal

#barra de busqueda input para el nombre y que al poner tipo yape busque y si no hay coincidencia sugiera crear 

nomb = str(input("Nombre del paciente: "))

def buscar(trie, catalogo, query):
    # Paso 1: el Trie filtra candidatos por prefijo (rápido)
    palabras_query = query.lower().split()
    candidatos = set()
    for palabra in palabras_query:
        candidatos.update(trie.sugerir(palabra))

    # Paso 2: el coseno rankea los candidatos por similitud (preciso)
    vec_query = texto_a_vector(query)
    resultados = []
    for item in catalogo:
        # solo procesar ítems que contienen alguna palabra del Trie
        if any(c in item.lower() for c in candidatos):
            score = similitud_coseno(vec_query, texto_a_vector(item))
            resultados.append((score, item))

    # Paso 3: ordenar de mayor a menor similitud
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

    trie = Trie()
    trie.insertar(nomb)

    informacion[nomb] = (fecha, procedimiento, nro_sesiones, proxima_sesion, nro_whatsapp, tiene_diabetes, tiene_hipertension, 
    antecedentes, edad)
    
    return informacion[nomb]

crear()
print(informacion)

#mostrar por fecha esta semana que pacientes tienen consulta y su hora 



#opcion de mostrar en pantalla informacion del paciente
#aun no



#para la busqueda y sugerencia nos vendrian bien los tries y el producto del coceno, entonces haremos uso de ellos en esta seccion
#crear entorno de conda para la version de python y las librerias a usar


####uso<###

for palabra in ["archivo", "árbol", "arte", "artículo", "búsqueda"]:
    trie.insertar(palabra)

print(trie.sugerir("art"))  # ['arte', 'artículo']
print(trie.sugerir("ar"))   # ['archivo', 'árbol', 'arte', 'artículo']

####producto del coceno#####


###uso
###

query = "editor de texto"
documentos = [
    "editor de código fuente",
    "visor de imágenes",
    "editor de texto enriquecido",
    "reproductor de audio",
]

vec_query = texto_a_vector(query)

for doc in documentos:
    score = similitud_coseno(vec_query, texto_a_vector(doc))
    print(f"{score:.2f} → {doc}")

# 0.82 → editor de texto enriquecido
# 0.41 → editor de código fuente
# 0.00 → visor de imágenes
# 0.00 → reproductor de audio

####combinados###

