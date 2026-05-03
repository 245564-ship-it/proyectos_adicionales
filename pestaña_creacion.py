from datetime import datetime
import barra_busqueda

nomb = str(input("Nombre del paciente: "))

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

crear()