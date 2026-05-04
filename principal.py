#####################################################################
#########este sera el backend del programa, la parte web#############
#####################################################################

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

informacion = {}

class Persona(BaseModel):
    nombre: str
    valores: list

@app.post("/agregar")
def agregar(persona: Persona):
    informacion[persona.nombre] = tuple(persona.valores)
    return {
        "mensaje": f"Persona {persona.nombre} agregada correctamente",
        "datos": informacion[persona.nombre]        
    }

@app.get('/')
async def read_root():
    return {"message": "hola mundo"}

@app.get("/informacion")
def obtener_informacion():
    return informacion

@app.get("/informacion/{nombre}")
def obtener_persona(nombre: str):
    if nombre in informacion:
        return {nombre: informacion[nombre]}
    return {"error": f"La persona {nombre} no existe"}