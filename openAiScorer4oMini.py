import os
import re
import openai
import requests
import sys
import json
from variables import instructions
from dotenv import load_dotenv

load_dotenv()
AImodel = "gpt-4o-mini"

openai.api_key = os.getenv("OPENAI_API_KEY")  # Asegúrate de tener tu clave en la variable de entorno

def obtener_calificacion(data):
    """
    Envía una conversación a la API de OpenAI para obtener una calificación (0-100)
    que evalúe qué tan bien responde `answer` a la `question` en el contexto 
    de `job_description`.
    """
    
    # 1) Mensaje de SISTEMA: define el rol principal del modelo.
    system_message = {
        "role": "system",
        "content": instructions
    }

    # 2) Mensaje de USUARIO: pasa el contexto real (job description, pregunta y respuesta).
    user_message = {
        "role": "user",
        "content": json.dumps(data)
    }

    # Llamada a la API de OpenAI usando la nueva forma (1.0.0+):
    response = openai.chat.completions.create(
        model=AImodel,  # o el modelo que estés utilizando realmente
        messages=[system_message, user_message],
        temperature=1.0
    )
    
    # Obtenemos el texto devuelto por el modelo (rol "assistant")
    calificacion_str = response.choices[0].message.content.strip()
    match = re.search(r'\{.*\}', calificacion_str, re.DOTALL)

    return match.group(0)

def process_data(data):
    # Procesar los datos y calcular los puntajes
    return obtener_calificacion(data)

def main(attendance_id):
    # Obtener las preguntas y respuestas desde la API de tu servidor
    response = requests.get(f"http://localhost:3000/v1/public/questions/qa/{attendance_id}")
    data = response.json()

    # Enviar el JSON completo como un único mensaje
    calificacion = obtener_calificacion(data)
    
    print(f"Calificación: {calificacion}")
    
def getModel():
    return AImodel

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python openAiScorer4o.py <attendance_id>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    main(attendance_id)
