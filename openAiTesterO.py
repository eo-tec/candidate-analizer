import os
import openai
import sys
import json
from variables import instructions
from dotenv import load_dotenv
import re
from aiTester import AiTester

load_dotenv()
AImodel = "gpt-4o"

class OpenAIO(AiTester):
    def __init__(self, model: str):
        super().__init__(model)
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def obtain_score(self, instructions: str, data: str) -> str:
        # Llamada a la API de OpenAI usando la nueva forma (1.0.0+):
        user_message_content = f"{instructions}\n\nData:\n{json.dumps(data)}"

        response = openai.chat.completions.create(
            model=AImodel,
            messages=[{"role": "user", "content": user_message_content}],
            temperature=1.0
        )
        # Then parse the response
        completion_text = response.choices[0].message.content.strip()

        match = re.search(r'\{.*\}', completion_text, re.DOTALL)

        return match.group(0)

    def get_model(self) -> str:
        return self.model
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python openAiScorer4o.py <attendance_id>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    openai_instance = OpenAIO(AImodel)
    openai_instance.main(attendance_id)
