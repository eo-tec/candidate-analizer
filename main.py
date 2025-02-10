from google import genai
from google.genai import types
import base64
import psycopg2
import boto3
import requests
from dotenv import load_dotenv
import os
import json

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

def generate(attendanceId):
    # Obtener las preguntas relacionadas con el attendanceId
    bucketName = "novahiring-uploads"
    response = requests.get(f"http://localhost:3000/v1/public/questions/by-attendance/{attendanceId}")
    questions_data = response.json()
    if isinstance(questions_data, str):
        questions_data = json.loads(questions_data)
    print(questions_data)
    questions = [q['title'] for q in questions_data]

    # Conectar a S3 y obtener los presigned URLs de los vídeos
    s3_client = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

    prefix = f"response_videos/attendance-{attendanceId}/"
    response = s3_client.list_objects_v2(Bucket=bucketName, Prefix=prefix)
    
    print(response)

    video_urls = []
    if 'Contents' in response:
      for obj in response['Contents']:
        key = obj['Key']
            
        # Generar URL prefirmada
        url_prefirmada = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucketName,
                'Key': key
            },
            ExpiresIn=900  # 900s = 15 minutos
        )
        video_urls.append(url_prefirmada)
        
    print(video_urls)
    # Crear la conversación con las preguntas y los links a los videos
    contents = []
    for question, video_url in zip(questions, video_urls):
        video_part = types.Part.from_uri(file_uri=video_url, mime_type="video/mp4")
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=question),
                    video_part
                ]
            )
        )

    client = genai.Client(
        vertexai=True,
        project="ia-analyzer",
        location="us-central1",
    )

    textsi_1 = """El agente de IA evaluará al candidato analizando su lenguaje corporal en vídeo y sus respuestas a preguntas para construir un perfil progresivo basado en 10 habilidades clave: comunicación, inteligencia emocional, liderazgo, resolución de problemas, trabajo en equipo, ética laboral, persuasión, adaptabilidad, enfoque ante la retroalimentación y manejo del estrés. Evaluará la confianza mediante el contacto visual, postura y gestos; la inteligencia emocional observando reacciones faciales y escucha activa; y la gestión de la presión mediante la respuesta a preguntas desafiantes y la aceptación del feedback. En las respuestas verbales analizará claridad, concisión, argumentación, creatividad y adaptabilidad. El perfil se actualizará continuamente hasta que se solicite un informe final con la evaluación completa.
Este informe se devolverá en JSON que tendrá el siguiente formato:
{
  \"habilities\": {
    \"communication\": 8,
    \"leadership\": 7,
    \"problem_solving\": 5,
    \"...\": \"...\",
  },
  \"summary\": \"Daniel is a 26 years old civil engineer with a lot experiences in this field. He use to work for......\",
  \"pros\": \"Is a good candidate because it has a lot of experience in this kind of positions\",
  \"cons\": \"It has low emotional intelligence, so it can lead to environment problems\",
  \"next_questions\": [\"Why are you looking for another job?\", \"How was your experience working with the teammate you told you had a problem with?\"]
}
Habilities ha de ser una nota de 0 a 10 de todas las habilidades nombradas anteriormente. Si la habilidad no ha podido ser evaluada se pondrá un -1.
Summary es un resumen en general del perfil del candidato.
Pros son los puntos fuertes del candidato en relación a el puesto de trabajo para el que está aplicando.
Cons los puntos más débiles para del candidato.
Next_questions son preguntas interesante que hacerle al candidato teniendo en cuenta algo que haya dicho.
Hasta que no se solicite que se haga el informe responde solamente con un mensaje que ponga \"Esperando siguiente pregunta\""""

    model = "gemini-2.0-pro-exp-02-05"

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ],
        response_mime_type="application/json",
        response_schema={"type": "OBJECT", "properties": {"response": {"type": "STRING"}}},
        system_instruction=[types.Part.from_text(text=textsi_1)],
    )

    # for chunk in client.models.generate_content_stream(
    #     model=model,
    #     contents=contents,
    #     config=generate_content_config,
    # ):
    #     print(chunk.text, end="")
    conversation_history = [types.Content(role="user", parts=[types.Part.from_text(text="Vamos a comenzar con la evaluación")])]
    current_question = 0
    all_questions_received = False

    while not all_questions_received:
      if current_question < len(questions):
        question = questions[current_question]
        video_url = video_urls[current_question]
        video_part = types.Part.from_uri(file_uri=video_url, mime_type="video/mp4")
        new_message = types.Content(role="user", parts=[types.Part.from_text(text=question), video_part])
        conversation_history.append(new_message)
      else:
        all_questions_received = True
        new_message = types.Content(role="user", parts=[types.Part.from_text(text="Solicitar informe final")])
        conversation_history.append(new_message)

      for chunk in client.models.generate_content_stream(
        model=model,
        contents=conversation_history,
        config=generate_content_config,
      ):
        if current_question < len(questions):
          print(f"Pregunta {current_question + 1} de {len(questions)}")
        else:
          print("Solicitando informe final")
        print(chunk.text, end="")

      current_question += 1

# Llamar a la función generate con un attendanceId de ejemplo
generate(2)