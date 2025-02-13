import json
from groq import Groq
import sys
from variables import instructions
from dotenv import load_dotenv
import re
from aiTester import AiTester
import os

load_dotenv()

AImodel = "deepseek-r1-distill-llama-70b"
class GroqTester(AiTester):
    def __init__(self, model: str):
        self.model = model
        super().__init__(model)
        
    def obtain_score(self, instructions: str, data: str) -> str:        
        client = Groq()
        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": instructions
                },
                {
                    "role": "user",
                    "content": json.dumps(data)
                },
            ],
            temperature=0.6,
            max_completion_tokens=4096,
            top_p=0.95,
            stream=True,
            stop=None,
        )
        response_text = ""
        for chunk in completion:
            response_text += chunk.choices[0].delta.content or ""
        
        print(response_text)
        
        match = re.search(r'\{.*\}', response_text, re.DOTALL)

        return match.group(0)

    def get_model(self) -> str:
        return self.model
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python openAiScorer4o.py <attendance_id>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    openai_instance = GroqTester(AImodel)
    openai_instance.obtain_score(instructions, attendance_id)

