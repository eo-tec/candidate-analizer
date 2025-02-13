import os
import openai
import requests
import sys
import json
from variables import instructions
from dotenv import load_dotenv
import re
from aiTester import AiTester

load_dotenv()
AImodel = "gpt-4o"

class OpenAI(AiTester):
    def __init__(self, model: str):
        super().__init__(model)
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def obtain_score(self, instructions: str, data: str) -> str:
        system_message = {
            "role": "system",
            "content": instructions
        }

        user_message = {
            "role": "user",
            "content": json.dumps(data)
        }

        response = openai.chat.completions.create(
            model=self.model,
            messages=[system_message, user_message],
            temperature=1.0
        )

        calificacion_str = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', calificacion_str, re.DOTALL)

        return match.group(0)

    def get_model(self) -> str:
        return self.model
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python openAiScorer4o.py <attendance_id>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    openai_instance = OpenAI(AImodel)
    openai_instance.main(attendance_id)
