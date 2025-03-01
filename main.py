import os
import json
import requests
import boto3
import time
import re
import shutil
from supabase import create_client

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

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print("Conectando a Supabase:", SUPABASE_URL)
print("Llave de Supabase:", SUPABASE_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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


def clean_filename(text):
    """
    Limpia y prepara un texto para ser usado como nombre de archivo.
    Toma los primeros 20 caracteres y reemplaza espacios por guiones bajos.
    """
    # Removemos caracteres especiales y espacios extras
    clean_text = re.sub(r'[^\w\s-]', '', text)
    # Reemplazamos espacios por guiones bajos
    clean_text = re.sub(r'\s+', '_', clean_text.strip())
    # Tomamos los primeros 20 caracteres
    return clean_text[:20]


def ensure_tmp_dir():
    """
    Asegura que existe el directorio tmp y lo limpia si ya existe
    """
    tmp_dir = "./tmp"
    if os.path.exists(tmp_dir):
        # Limpia el contenido existente
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)

def cleanup_tmp_dir():
    """
    Limpia el directorio tmp al finalizar
    """
    tmp_dir = "./tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)


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
def save_analysis_results(attendance_id, analysis_data):
    """
    Guarda los resultados del análisis en Supabase usando columnas individuales para cada habilidad
    """
    try:
        # Convertir el texto JSON a diccionario si es necesario
        if isinstance(analysis_data, str):
            try:
                analysis_data = json.loads(analysis_data)
            except json.JSONDecodeError as e:
                print("Error al decodificar JSON:", str(e))
                print("Texto recibido:", analysis_data)
                return None

        # Verify we have a valid JSON object
        if not isinstance(analysis_data, dict):
            print("Los datos no son un objeto JSON válido")
            return None

        # Validar que el JSON tiene la estructura esperada
        required_fields = ["habilities", "summary", "pros", "cons", "next_questions"]
        missing_fields = [field for field in required_fields if field not in analysis_data]
        if missing_fields:
            print(f"Faltan campos requeridos en el JSON: {missing_fields}")
            return None
        
        # Preparar los datos para insertar con las columnas individuales
        data = {
            "attendance_id": attendance_id,
            "communication": analysis_data["habilities"]["communication"],
            "emotional_intelligence": analysis_data["habilities"]["emotional_intelligence"],
            "leadership": analysis_data["habilities"]["leadership"],
            "problem_solving": analysis_data["habilities"]["problem_solving"],
            "teamwork": analysis_data["habilities"]["teamwork"],
            "work_ethic": analysis_data["habilities"]["work_ethic"],
            "persuasion": analysis_data["habilities"]["persuasion"],
            "adaptability": analysis_data["habilities"]["adaptability"],
            "feedback_handling": analysis_data["habilities"]["feedback_handling"],
            "stress_management": analysis_data["habilities"]["stress_management"],
            "summary": analysis_data["summary"],
            "pros": analysis_data["pros"],
            "cons": analysis_data["cons"],
            "next_questions": analysis_data["next_questions"]
        }
        
        print("Intentando guardar en Supabase con datos:", json.dumps(data, indent=2))
        
        # Verificar conexión a Supabase
        try:
            # Test query to verify connection
            supabase.table("analysis_results").select("id").limit(1).execute()
        except Exception as e:
            print("Error de conexión con Supabase:", str(e))
            return None
            
        # Insertar en la tabla analysis_results
        result = supabase.table("analysis_results").insert(data).execute()
        print("Respuesta de Supabase:", result)
        return result

    except Exception as e:
        print("Error al guardar en Supabase:", str(e))
        print("Tipo de error:", type(e).__name__)
        if 'data' in locals():
            print("Datos que se intentaron guardar:", json.dumps(data, indent=2))
        return None

def generate(candidateId):
    """
    1. Obtiene las preguntas del endpoint local de questions/qa.
    2. Obtiene los videos de S3 mediante URL prefirmada.
    3. Crea un chat con Gemini y envía cada video+p+regunta.
    4. Solicita el informe final.
    5. Guarda los resultados en Supabase.
    """
    # Aseguramos que tmp está limpio al inicio
    ensure_tmp_dir()

    # --- A) OBTENCIÓN DE PREGUNTAS Y VIDEOS ---
    # 1. Obtener las preguntas
    response = requests.get(f"https://api.novahiring.com/v1/public/questions/qa/{candidateId}")
    questions_data = response.json()
    if isinstance(questions_data, str):
        questions_data = json.loads(questions_data)
        
    print("Respuesta de preguntas:", questions_data)

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

    # Crear diccionario de video_urls usando question.id
    video_urls = {}
    for question in questions_data["questions"]:
        question_id = question['id']
        video_key = question['videoUrl']
        
        try:
            # Verificar si el objeto existe
            s3_client.head_object(Bucket=bucketName, Key=video_key)
            # Si existe, generar URL prefirmada
            url_prefirmada = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucketName, 'Key': video_key},
                ExpiresIn=900  # 15 minutos
            )
            video_urls[question_id] = url_prefirmada
        except:
            print(f"No se encontró el video para la pregunta {question_id}")
            continue

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
    for question in questions_data["questions"]:
        question_id = question['id']
        if question_id not in video_urls:
            print(f"Saltando pregunta {question_id} - No se encontró video")
            continue
            
        print(f"\n=== Procesando pregunta {question['title']} ===")

        # 1. Descargar el video
        video_resp = requests.get(video_urls[question_id])
        if video_resp.status_code != 200:
            print(f"Error al descargar el video para pregunta {question_id}:", video_resp.status_code)
            continue

        # Crear nombre de archivo basado en la pregunta
        video_filename = clean_filename(question['title'])
        local_video_path = os.path.join("tmp", f"video_{video_filename}_{candidateId}.mp4")
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
                "Pregunta: " + question['title'],     # Texto
                video_file                 # El objeto 'File' subido
            ]
        )

        print("Pregunta enviada al modelo:", question['title'])
        print("Respuesta del modelo:\n", response_msg.text)
        bot_responses.append({"role": "model", "text": response_msg.text})

    # --- E) SOLICITAR INFORME FINAL ---
    print("\n=== Solicitando informe final... ===")
    final_msg = chat_session.send_message({"parts": [{"text": "Solicitar informe final"}]})
    print("Informe final:\n", final_msg.text)

    bot_responses.append({"role": "model", "text": final_msg.text})

    # Guardar resultados en Supabase (solo el informe final que sí es JSON)
    result = save_analysis_results(candidateId, final_msg.text)
    if result is None:
        print("No se pudo guardar el análisis en Supabase")

    # Limpiar directorio tmp al finalizar
    cleanup_tmp_dir()

    return bot_responses, final_msg.text


def test_db():
    """
    Verifica la conexión a la base de datos intentando insertar y eliminar un registro de prueba
    """
    try:
        # Datos de prueba con las nuevas columnas individuales
        test_data = {
            "attendance_id": -1,  # ID negativo para prueba
            "communication": -1,
            "emotional_intelligence": -1,
            "leadership": -1,
            "problem_solving": -1,
            "teamwork": -1,
            "work_ethic": -1,
            "persuasion": -1,
            "adaptability": -1,
            "feedback_handling": -1,
            "stress_management": -1,
            "summary": "Test connection",
            "pros": "Test connection",
            "cons": "Test connection",
            "next_questions": ["Test question 1", "Test question 2"]
        }
        
        # Insertar registro de prueba
        result = supabase.table("analysis_results").insert(test_data).execute()
        test_id = result.data[0]['id']
        print("Registro de prueba insertado correctamente")
        
        # Eliminar el registro de prueba
        supabase.table("analysis_results").delete().eq('id', test_id).execute()
        print("Registro de prueba eliminado correctamente")
        
        return True
        
    except Exception as e:
        print("Error verificando base de datos:", str(e))
        return False

# Modificar la sección principal para usar test_db
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Uso: python main.py <candidateId>")
        sys.exit(1)
    
    # Probar conexión a base de datos antes de procesar
    if not test_db():
        print("Error: No se pudo verificar la conexión a la base de datos")
        sys.exit(1)
    
    candidateId = int(sys.argv[1])
    generate(candidateId)
