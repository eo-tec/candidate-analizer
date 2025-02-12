import requests
import sys
from dotenv import load_dotenv
import json
import os
import importlib
from variables import instructions  # Asumiendo que tienes algo en este archivo
from supabase import create_client, Client  # pip install supabase

load_dotenv()

def main(attendance_id):
    # 1. Obtenemos datos de tu endpoint
    response = requests.get(f"https://api.novahiring.com/v1/public/questions/qa/{attendance_id}")
    data = response.json()

    print(data)

    # 2. Obtenemos todos los archivos .py (excepto main.py)
    py_files = [f for f in os.listdir('.') if f.endswith('.py') and f != 'main.py']

    # 3. Creamos cliente de Supabase
    #    -> Asegúrate de tener SUPABASE_URL y SUPABASE_KEY definidas en tu entorno
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: Falta SUPABASE_URL o SUPABASE_KEY en las variables de entorno.")
        sys.exit(1)

    supabase: Client = create_client(supabase_url, supabase_key)

    # 4. Iteramos cada archivo, extraemos datos y subimos a Supabase
    for py_file in py_files:
        module_name = py_file[:-3]  # quitamos .py
        module = importlib.import_module(module_name)

        if hasattr(module, 'getModel') and hasattr(module, 'process_data'):
            model = module.getModel()
            print(f"Modelo en {py_file}: {model}")

            try:
                result = module.process_data(data)
                print(f"Resultado de process_data en {py_file}: {result}")
                
                parsed_result = json.loads(result)
                scores_list = parsed_result["scores"]
                
                # Calculamos la media
                average_score = sum(scores_list) / len(scores_list)

                # Preparamos el diccionario a insertar en Supabase
                row_to_insert = {
                    "model": model,
                    "attendance_id": int(attendance_id),
                    "instructions": instructions,  # Esto puede ser lo que tú quieras.
                    "average": average_score,
                    "scores": scores_list
                }

                # 5. Insertamos en tu tabla "ai_benchmark"
                response = supabase.table("ai_benchmark").insert(row_to_insert).execute()

            except Exception as e:
                print(f"Error procesando {py_file}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python main.py <attendance_id>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    main(attendance_id)
