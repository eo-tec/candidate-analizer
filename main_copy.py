from google import genai
from google.genai import types
import base64

def generate():
  client = genai.Client(
      vertexai=True,
      project="ia-analyzer",
      location="europe-southwest1",
  )

  video1 = types.Part.from_uri(
      file_uri="https://novahiring-uploads.s3.eu-west-3.amazonaws.com/response_videos/attendance-1060/response-4292.mp4?response-content-disposition=inline&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCWV1LXdlc3QtMyJGMEQCIC17aH0xU6qlsb5MJEtsRbBYxrrC3rFzPHvu9aYcaT3cAiBzlBgcrrEs76X3mdNK761Y48IcVRuyvDt8LxyE1%2FLEZCrnAwjC%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDMzOTcxMjk2MzI4MSIMP%2FHVTAgvQlIE14K8KrsDi5iP6PfS9iADlbYzM6%2BSnsjZSiOfG9xHB8%2FRj9hYDvdrgD6mEosixW3jJQsdhSCvCZ69lYjkJip%2FTkJlKmva8a0AxYYQcTQVFiBU80BK%2BwLSg4xah3%2BuZRD60QVM3P9LdpcF50gHBVDSQ54Nrwef1ZCkoiMDX6%2FSqcWbyZGjbTHcqr4%2F5YXnmGbGhWHR3fyoVQH5AIHu1l6ZJK3iElJPY82gqex6g00Pyk8uKkKLdVWIXc3SX5rC9xcgcLYb2gLpKY%2FPw1ZSps%2Flv40%2BszBKehjStQay6brtRNzrTiUxSRUkn6Ap4PghzNxAIMWmyBK4vqKW6fvaC8%2F0N1ogurC0DtPm6Hp50YWOFy3W3icRboVcl50KwkoeffJ9%2Bpw0AwAbbpqGFx55UraGv92lr49qmk%2FxdZvTSiw3FqG8iU3lKVaIAOeiPBrCQiGXT%2FAgWXOik7E9YXJQuBV10dbgf8cuVBKgkVGAEvTVRIrhZ33KUXDYma3Qiqg4K5Qevrkd8UpaQ1f59yZnkhOHapiDK0EEx9%2BLW5%2B%2FVyKO9XPAE6pw4kUaqRKrXEF2z3T3ipLUMwD6k9tc8mHqtKkKaLUwt9unvQY65QKtjiFtMSBzUno3guA2FnTWjqro0tcc%2BY%2BLbAgAe6WNPdFYYj8feay96Wl%2FJIKINU8eD82rY%2B%2F%2BOe54cf%2BPIgf86aVW1B8juEe05vcyu9FiahTEBwXhtKTZKbTk%2Fc2peVcITzwdMcF5k5JxpU1%2Fcxnm7D%2BdpXPvvE0Bz8FkR2HfOLNUo%2BHdrdffdkbQQzeag1a%2BpOc5QKXfmvtdNdIAnjp%2FQyJ7Fh53T2eApDX9JJqT7nzHaLeky3iMw%2FgOhfLTf9xoltvpr599EQd2ctfKmUNGUmHFHp4DZ59ppbsc0ciqrTfXGpRJi62LqsHPo%2FQ8yz2RlAHyjVTSLIl3ZZMF1zfg%2B%2B8rXqY5eOXD4eViaxRbmkV4RY24MvCK3sNEP%2B3PZGPGWHggUN4pzfekeeIgr%2B0dhqsuckzUnSHdD9IaVPriIg2l3PeRcVXKyY%2BHD5FTo7U0gYiGvjVVjrHVK1NCMkT7J56QAxM%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAU6GDYOLIS2NHIDHN%2F20250210%2Feu-west-3%2Fs3%2Faws4_request&X-Amz-Date=20250210T164842Z&X-Amz-Expires=600&X-Amz-SignedHeaders=host&X-Amz-Signature=6e66cfe3497c9e9f68b31a70ec26ed4b1982913926071db346d6e8b5f98a9ffb",
      mime_type="video/mp4",
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

  model = "gemini-2.0-flash-001"
  contents = [
    types.Content(
      role="user",
      parts=[
        types.Part.from_text(text="""Las preguntas son: Descríbete brevemente. Cuánto tiempo tienes de experiencia en programar?"""),
        video1
      ]
    )
  ]
  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    response_modalities = ["TEXT"],
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    response_mime_type = "application/json",
    response_schema = {"type":"OBJECT","properties":{"response":{"type":"STRING"}}},
    system_instruction=[types.Part.from_text(text=textsi_1)],
  )

  for chunk in client.models.generate_content_stream(
    model = model,
    contents = contents,
    config = generate_content_config,
    ):
    print(chunk.text, end="")

generate()