import requests
from dotenv import load_dotenv
from variables import instructions
import sys
from google import genai
from google.genai import types
import json

load_dotenv()

AImodel = "gemini-2.0-pro-exp-02-05"

def obtener_calificacion(data):
    client = genai.Client(
        vertexai=True,
        project="ia-analyzer",
        location="us-central1",
    )

    model = AImodel
    contents = [
        types.Content(
            role="user", parts=[types.Part.from_text(text=json.dumps(data))]
        )
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        response_mime_type = "application/json",
        response_schema = {"type":"OBJECT","properties":{"scores":{"type":"ARRAY","items":{"type":"NUMBER"}}}},
        system_instruction=[types.Part.from_text(text=instructions)],
    )

    response_text = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        response_text += chunk.text

    return response_text


def process_data(data):
    return obtener_calificacion(data)


def main(attendance_id):
    response = requests.get(
        f"http://localhost:3000/v1/public/questions/qa/{attendance_id}"
    )
    data = response.json()
    calificacion = process_data(data)
    print(f"Calificación: {calificacion}")


def getModel():
    return AImodel


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python gemini.py <attendance_id>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    main(attendance_id)
