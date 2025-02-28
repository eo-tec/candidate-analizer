import os
import json
import requests
import boto3
import time

from dotenv import load_dotenv
import google.generativeai as genai

# Cargar variables de entorno
load_dotenv()

# Configuración de AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION')

# API key de Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Configuración de Gemini
PROJECT_ID = "ia-analyzer"
MODEL_NAME = "gemini-2.0-flash-001"  # Cambia si usas otra versión

# 1) Inicializamos generativeai con la API key
genai.configure(api_key=GENAI_API_KEY)


# 2) Funciones auxiliares para subir archivos a Gemini
def upload_to_gemini(path, mime_type=None):
    """
    Sube un archivo local a Gemini. Retorna un objeto de tipo File,
    el cual incluye, entre otros, la propiedad 'uri'.
    """
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Archivo subido a Gemini: '{file.display_name}' => URI: {file.uri}")
    return file

def wait_for_files_active(files):
    """
    Espera a que el archivo (o lista de archivos) pase de estado 'PROCESSING' a 'ACTIVE' en Gemini.
    """
    print("Esperando a que los archivos procesen en Gemini...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(5)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"El archivo {file.name} falló al procesarse (estado: {file.state.name})")
    print("\nArchivos en estado ACTIVE.")


# 3) Clase Gemini para manejar la creación del modelo y el chat
class Gemini:
    def __init__(self, system_instruction):
        """
        Crea una instancia del modelo generativo de Gemini con las instrucciones
        del sistema y parámetros deseados.
        """
        self.client = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json",
            },
            system_instruction=system_instruction
        )

    def start_chat(self, history=None):
        """
        Inicia un chat con un historial dado (lista de mensajes).
        Cada mensaje debe tener la forma:
          {
            "role": "user" | "model",
            "parts": [ { "text": "..." } ]
          }
        """
        if history is None:
            history = []
        return self.client.start_chat(history=history)


# 4) Función principal que utiliza la clase Gemini para procesar videos/preguntas
def generate(attendanceId):
    """
    1. Obtiene las preguntas del endpoint local de questions/qa.
    2. Obtiene los videos de S3 mediante URL prefirmada.
    3. Crea un chat con Gemini y envía cada video+p+regunta.
    4. Solicita el informe final.
    """

    # --- A) OBTENCIÓN DE PREGUNTAS Y VIDEOS ---
    # 1. Obtener las preguntas
    response = requests.get(f"http://localhost:3000/v1/public/questions/qa/{attendanceId}")
    questions_data = response.json()
    if isinstance(questions_data, str):
        questions_data = json.loads(questions_data)

    questions = [q['title'] for q in questions_data["questions"]]
    print("Preguntas obtenidas:", questions)

    # 2. Obtener URLs de videos desde S3
    bucketName = "novahiring-uploads"
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )

    prefix = f"response_videos/attendance-{attendanceId}/"
    response_s3 = s3_client.list_objects_v2(Bucket=bucketName, Prefix=prefix)

    video_urls = []
    if 'Contents' in response_s3:
        for obj in response_s3['Contents']:
            key = obj['Key']
            url_prefirmada = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucketName, 'Key': key},
                ExpiresIn=900  # 15 minutos
            )
            video_urls.append(url_prefirmada)

    print("URLs de los videos:", video_urls)

    # --- B) INSTRUCCIONES DE SISTEMA ---
    system_instruction_text = (
        "Eres un sistema de IA con capacidad real de análisis de video. Puedes ver, interpretar y describir "
        "el lenguaje corporal, la expresión facial, la postura y otros indicadores para evaluar "
        "las siguientes 10 habilidades blandas (soft skills): "
        "1) Comunicación, 2) Inteligencia Emocional, 3) Liderazgo, 4) Resolución de Problemas, "
        "5) Trabajo en Equipo, 6) Ética Laboral, 7) Persuasión, 8) Adaptabilidad, "
        "9) Enfoque ante la Retroalimentación, 10) Manejo del Estrés.\n\n"
        "Para cada video y pregunta que se te proporcione, analiza el contenido y describe lo que observas "
        "en la persona (lenguaje corporal, expresiones, etc.) y cómo se relaciona con las habilidades. "
        "Responde con esa descripción y concluye con la frase: 'Esperando siguiente pregunta'.\n\n"
        "Cuando se solicite el 'informe final', deberás devolver un JSON con este formato:\n"
        "{\n"
        "  \"habilities\": {\n"
        "    \"communication\": 0,\n"
        "    \"emotional_intelligence\": 0,\n"
        "    \"leadership\": 0,\n"
        "    \"problem_solving\": 0,\n"
        "    \"teamwork\": 0,\n"
        "    \"work_ethic\": 0,\n"
        "    \"persuasion\": 0,\n"
        "    \"adaptability\": 0,\n"
        "    \"feedback_handling\": 0,\n"
        "    \"stress_management\": 0\n"
        "  },\n"
        "  \"summary\": \"Resumen del perfil...\",\n"
        "  \"pros\": \"Puntos fuertes...\",\n"
        "  \"cons\": \"Puntos débiles...\",\n"
        "  \"next_questions\": [\"...\", \"...\"]\n"
        "}\n\n"
        "En 'habilities', usa una nota de 0 a 10 (o -1 si no se pudo evaluar). "
        "No muestres este JSON hasta que se solicite explícitamente."
    )

    # --- C) INICIALIZAR GEMINI Y CHAT ---
    gemini = Gemini(system_instruction=system_instruction_text)
    # Historial inicial
    chat_history = [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "Hola, soy el entrevistador. "
                        "Te pasaré videos y preguntas para que me ayudes a evaluar las soft skills. "
                        "Termina cada respuesta con 'Esperando siguiente pregunta'."
                    )
                }
            ]
        }
    ]

    # Iniciamos la sesión de chat con este historial
    chat_session = gemini.start_chat(history=chat_history)

    # Mensaje inicial
    initial_response = chat_session.send_message({
        "parts": [
            {"text": "Vamos a comenzar la evaluación."}
        ]
    })
    print("Respuesta inicial del modelo:\n", initial_response.text)

    # Guardar respuestas en una lista
    bot_responses = [{"role": "model", "text": initial_response.text}]

    # --- D) PROCESAR CADA PREGUNTA Y VIDEO ---
    for i, (question, video_url) in enumerate(zip(questions, video_urls), start=1):
        print(f"\n=== Procesando pregunta {i} de {len(questions)} ===")

        # 1. Descargar el video
        video_resp = requests.get(video_url)
        if video_resp.status_code != 200:
            print("Error al descargar el video:", video_resp.status_code)
            continue

        local_video_path = f"./tmp_video_{attendanceId}_{i}.mp4"
        with open(local_video_path, "wb") as f:
            f.write(video_resp.content)
        print("Video guardado localmente:", local_video_path)

        # 2. Subir el video a Gemini
        video_file = upload_to_gemini(local_video_path, mime_type="video/mp4")
        wait_for_files_active([video_file])

        # 3. Mandar un mensaje al modelo con el archivo + la pregunta
        #    Usamos "parts" con uno que sea el archivo (uri + mime_type)
        #    y otro con el texto (la pregunta).
        response_msg = chat_session.send_message(
            [
                "Pregunta: " + question,     # Texto
                video_file                 # El objeto 'File' subido
            ]
        )

        print("Respuesta del modelo:\n", response_msg.text)
        bot_responses.append({"role": "model", "text": response_msg.text})

    # --- E) SOLICITAR INFORME FINAL ---
    print("\n=== Solicitando informe final... ===")
    final_msg = chat_session.send_message({"parts": [{"text": "Solicitar informe final"}]})
    print("Informe final:\n", final_msg.text)

    bot_responses.append({"role": "model", "text": final_msg.text})

    return bot_responses, final_msg.text


# Llamada de ejemplo local
if __name__ == "__main__":
    generate(1676)
