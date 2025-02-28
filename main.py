import os
import json
import requests
import boto3
import base64
import psycopg2
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Cargar las variables de entorno
load_dotenv()

def generate(attendanceId):
    # 1. Obtener las preguntas relacionadas con el attendanceId
    bucketName = "novahiring-uploads"
    response = requests.get(f"http://localhost:3000/v1/public/questions/qa/{attendanceId}")
    questions_data = response.json()
    if isinstance(questions_data, str):
        questions_data = json.loads(questions_data)
    questions = [q['title'] for q in questions_data["questions"]]
    print("Preguntas obtenidas:", questions)

    # 2. Conectar a S3 y obtener los presigned URLs de los vídeos
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )

    prefix = f"response_videos/attendance-{attendanceId}/"
    response_s3 = s3_client.list_objects_v2(Bucket=bucketName, Prefix=prefix)

    video_urls = []
    if 'Contents' in response_s3:
        for obj in response_s3['Contents']:
            key = obj['Key']
            # Generar URL prefirmada (15 min)
            url_prefirmada = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucketName, 'Key': key},
                ExpiresIn=900
            )
            video_urls.append(url_prefirmada)

    print("URLs de los videos:", video_urls)

    # 3. Configurar el cliente de PaLM/Gemini
    client = genai.Client(
        vertexai=True,
        project="ia-analyzer",
        location="us-central1",
    )

    # 4. Instrucción del sistema:
    system_instruction_text = (
        "Eres un sistema de IA con capacidad real de análisis de video. Puedes ver, interpretar y describir "
        "el lenguaje corporal, la expresión facial, la postura y otros indicadores para evaluar las siguientes "
        "10 habilidades blandas (soft skills):\n"
        "1) Comunicación,\n"
        "2) Inteligencia Emocional,\n"
        "3) Liderazgo,\n"
        "4) Resolución de Problemas,\n"
        "5) Trabajo en Equipo,\n"
        "6) Ética Laboral,\n"
        "7) Persuasión,\n"
        "8) Adaptabilidad,\n"
        "9) Enfoque ante la Retroalimentación,\n"
        "10) Manejo del Estrés.\n\n"
        "Para cada video y pregunta que se te proporcione, analiza el contenido y describe lo que observas "
        "en la persona (ej. lenguaje corporal, tono de voz, etc.) y cómo se relaciona con las habilidades blandas. "
        "Deberás responder con una descripción y terminar tu respuesta siempre con la frase: "
        "\"Esperando siguiente pregunta\".\n\n"
        "Cuando el usuario solicite el 'informe final', deberás devolver un JSON con el siguiente formato:\n"
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
        "  \"summary\": \"Breve resumen del perfil del candidato...\",\n"
        "  \"pros\": \"Puntos fuertes...\",\n"
        "  \"cons\": \"Puntos débiles...\",\n"
        "  \"next_questions\": [\"...\" , \"...\"]\n"
        "}\n\n"
        "En 'habilities', coloca una nota de 0 a 10 (o -1 si no se pudo evaluar). "
        "No muestres el JSON en tus respuestas intermedias, ni lo menciones. "
        "Solamente cuando se solicite explícitamente el informe final."
    )

    # 5. Configuración del modelo
    model_name = "gemini-2.0-pro-exp-02-05"
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
        system_instruction=[types.Part.from_text(text=system_instruction_text)],
    )

    # 6. Historial de conversación en texto (rol user/model)
    conversation_history = []

    # 7. Primer mensaje de usuario (inicial)
    initial_user_message = (
        "Hola, soy el entrevistador. Vamos a comenzar con la evaluación. "
        "Te mandaré varios videos y preguntas para que hagas tu descripción y evalúes brevemente "
        "lo que observes respecto a las habilidades blandas."
    )
    conversation_history.append(
        types.Content(role="user", parts=[types.Part.from_text(text=initial_user_message)])
    )

    # 7.1 Primera petición al modelo
    initial_response = client.models.generate_content(
        model=model_name,
        contents=conversation_history,
        config=generate_content_config,
    )
    print("Respuesta inicial del modelo:\n", initial_response.text)

    # Añadimos la respuesta del modelo al historial
    conversation_history.append(
        types.Content(role="model", parts=[types.Part.from_text(text=initial_response.text)])
    )

    # Guardamos esta respuesta en bot_responses
    bot_responses = [{"role": "model", "text": initial_response.text}]

    # 8. Iteramos cada pregunta con su video
    for i, (question, video_url) in enumerate(zip(questions, video_urls), start=1):
        print(f"\n=== Procesando pregunta {i}/{len(questions)} ===")
        print("Video URL:", video_url)
        print("Pregunta :", question)

        # a) Construir contents con historial + video + pregunta
        current_contents = list(conversation_history)

        # b) Añadimos el video como usuario
        current_contents.append(
            types.Content(role="user", parts=[types.Part.from_uri(file_uri=video_url, mime_type="video/mp4")])
        )

        # c) Añadimos la pregunta como usuario
        current_contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=question)])
        )

        # d) Petición al modelo
        response = client.models.generate_content(
            model=model_name,
            contents=current_contents,
            config=generate_content_config,
        )
        print(f"Respuesta del modelo tras la pregunta {i}:\n", response.text)

        # e) Añadimos al historial (solo el texto de la pregunta y de la respuesta)
        conversation_history.append(
            types.Content(role="user", parts=[types.Part.from_text(text=question)])
        )
        conversation_history.append(
            types.Content(role="model", parts=[types.Part.from_text(text=response.text)])
        )

        # f) Guardamos en bot_responses
        bot_responses.append({"role": "model", "text": response.text})

    # 9. Cuando se haya terminado, solicitamos el informe final
    final_contents = list(conversation_history)
    final_contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text="Solicitar informe final")])
    )

    final_response = client.models.generate_content(
        model=model_name,
        contents=final_contents,
        config=generate_content_config,
    )

    print("\n=== Informe final solicitado ===")
    print(final_response.text)

    bot_responses.append({"role": "model", "text": final_response.text})
    return bot_responses, final_response.text


if __name__ == "__main__":
    # Ejemplo de llamada
    generate(1676)
