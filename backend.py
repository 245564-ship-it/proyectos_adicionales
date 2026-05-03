# ENTONCES LAS COLUMNAS SERAN 10, lo primero seria el id para el diccionario 

#los datos en orden son fecha, nombre del paciente, procedimiento, cuantas sesiones, proxima fecha,
#nro whatsapp, si tiene diabetes, si tiene hipertencion, antecedentes, edad

#el dato que va a mandar es el nombre del paciente, principalmente una funcion para ver su informacion 
#por fechas
#fechas automaticas

#estructura de dato para almacenar la informacion aqui
informacion = {}


#pagina principal

#barra de busqueda input para el nombre y que al poner tipo yape busque y si no hay coincidencia sugiera crear 

nomb = str(input("Nombre del paciente: "))

def buscar():
    pass

def crear():
    fecha = str(input("introduzca dato"))
    procedimiento = str(input("introduzca dato"))
    nro_sesiones = str(input("introduzca dato"))
    proxima_sesion = str(input("introduzca dato"))
    nro_whatsapp = str(input("introduzca dato"))
    tiene_diabetes = str(input("introduzca dato"))
    tiene_hipertension = str(input("introduzca dato"))
    antecedentes = str(input("introduzca dato"))
    edad = str(input("introduzca dato"))

    
    informacion[nomb] = (fecha, procedimiento, nro_sesiones, proxima_sesion, nro_whatsapp, tiene_diabetes, tiene_hipertension, 
    antecedentes, edad)
    pass

#mostrar por fecha esta semana que pacientes tienen consulta y su hora 



#opcion de mostrar en pantalla informacion del paciente
#aun no