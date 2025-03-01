# Analizador de Candidatos - NovaHiring

Este script permite analizar videos de entrevistas de candidatos utilizando IA de Google (Gemini) para evaluar habilidades blandas. Los resultados se almacenan en una base de datos PostgreSQL.

## Requisitos Previos

- Python 3.8 o superior
- Acceso a una base de datos PostgreSQL
- Credenciales de AWS configuradas
- API key de Google Gemini
- Credenciales de Supabase

## Instalación

1. Clona el repositorio:
```bash
git clone <url-del-repositorio>
cd candidate-analizer
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:
```env
# AWS Credentials
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=tu_region
AWS_REGION=tu_region

# Gemini API Key
GEMINI_API_KEY=tu_api_key_de_gemini

# Supabase Credentials
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase
```

## Base de Datos

El sistema utiliza PostgreSQL como base de datos. La estructura de la tabla se encuentra en el archivo `create_table.sql`. Las habilidades evaluadas se almacenan en columnas independientes:

- communication
- emotional_intelligence
- leadership
- problem_solving
- teamwork
- work_ethic
- persuasion
- adaptability
- feedback_handling
- stress_management

## Uso

1. Obtén el ID del candidato desde [app.novahiring.com](https://app.novahiring.com)

2. Ejecuta el script con el ID del candidato:
```bash
python main.py <candidate_id>
```

Por ejemplo:
```bash
python main.py 12345
```

3. El script realizará las siguientes acciones:
   - Descargará los videos de las preguntas del candidato desde S3
   - Analizará cada video con IA para evaluar las habilidades blandas
   - Generará un informe final con puntuaciones para cada habilidad
   - Guardará los resultados en la base de datos

## Resultados

Los resultados incluyen:
- Puntuación de 0 a 10 para cada habilidad (-1 si no se pudo evaluar)
- Resumen del perfil del candidato
- Puntos fuertes
- Puntos débiles
- Sugerencias de preguntas adicionales

## Solución de Problemas

Si encuentras errores:

1. Verifica que todas las variables de entorno estén correctamente configuradas
2. Asegúrate de tener conexión a internet
3. Confirma que el ID del candidato existe y es válido
4. Verifica que tengas acceso a la base de datos

## Notas Adicionales

- Los videos se descargan temporalmente y se eliminan después del análisis
- El proceso puede tardar varios minutos dependiendo de la cantidad de videos
- Se requiere una conexión estable a internet durante todo el proceso