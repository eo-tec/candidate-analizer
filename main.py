import requests
import sys
from dotenv import load_dotenv
import json
import os
from variables import instructions, new_instructions  # Asumiendo que tienes algo en este archivo
from supabase import create_client, Client  # pip install supabase
from geminiTester import Gemini
from openAiTester import OpenAI
from openAiTesterO import OpenAIO
from groqTester import GroqTester
import threading
load_dotenv()

# Array con los modelos y su clase
models_to_test = [
    {"model": "gemini-2.0-flash-001", "class": Gemini},
    #{"model": "gemini-2.0-flash-lite-preview-02-05", "class": Gemini},
    {"model": "gemini-2.0-pro-exp-02-05", "class": Gemini},
    # {"model": "gpt-4o", "class": OpenAI},
    {"model": "gpt-4o-mini", "class": OpenAI},
    #{"model": "o1-mini-2024-09-12", "class": OpenAIO},
    # {"model": "o3-mini", "class": OpenAIO},
    {"model": "deepseek-r1-distill-llama-70b", "class": GroqTester},
    #{"model": "llama-3.2-1b-preview", "class": GroqTester},
    #{"model": "llama-3.2-3b-preview", "class": GroqTester},
    #{"model": "gemma2-9b-it", "class": GroqTester},
    # Agrega más modelos según sea necesario
]


def main(attendance_id, expected_score=None):
    # 1. Obtenemos datos de tu endpoint
    response = requests.get(f"https://api.novahiring.com/v1/public/questions/qa/{attendance_id}")
    #response = requests.get(f"http://localhost:3000/v1/public/questions/qa/{attendance_id}")
    data = response.json()
    # Verificamos si hay un objeto llamado 'questions' y añadimos todas las 'model_response'
    modal_responses = [q["model_response"] for q in data["questions"]]

    # 2. Creamos cliente de Supabase
    #    -> Asegúrate de tener SUPABASE_URL y SUPABASE_KEY definidas en tu entorno
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: Falta SUPABASE_URL o SUPABASE_KEY en las variables de entorno.")
        sys.exit(1)

    supabase: Client = create_client(supabase_url, supabase_key)

    # 3. Iteramos sobre los modelos a probar
    threads = []
    for model_info in models_to_test:
        model_name = model_info["model"]
        model_class = model_info["class"]

        tester = model_class(model_name)
        model = tester.get_model()
        

        def run_test(tester, model_name, model):
            try:
                result = tester.obtain_score(new_instructions, data)


                parsed_result = json.loads(result)
                scores_list = parsed_result["scores"]
                print(f"Modelo: {model_name}")
                print(f"Resultado de obtain_score: {result}")

                # Calculamos la media
                average_score = sum(scores_list) / len(scores_list)

                # Preparamos el diccionario a insertar en Supabase
                row_to_insert = {
                    "model": model,
                    "attendance_id": int(attendance_id),
                    "instructions": instructions,  # Esto puede ser lo que tú quieras.
                    "average": average_score,
                    "scores": scores_list,
                    "model_answers": modal_responses,  # Añadimos las respuestas modales
                    "expected_score": expected_score  # Añadimos los comentarios
                }

                # 4. Insertamos en tu tabla "ai_benchmark"
                response = supabase.table("ai_benchmark").insert(row_to_insert).execute()

            except Exception as e:
                print(f"Error procesando {model_name}: {e}")

        thread = threading.Thread(target=run_test, args=(tester, model_name, model))
        threads.append(thread)
        thread.start()

    # Esperamos a que todos los hilos terminen
    for thread in threads:
        thread.join()

    print("Todos los modelos han sido procesados.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Uso: python main.py <candidate_id> <expected_score>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    expected_score = sys.argv[2] if len(sys.argv) == 3 else None
    n = 15  # Número de veces que quieres llamar a main
    for _ in range(n):
        main(attendance_id, expected_score)
