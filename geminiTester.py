from dotenv import load_dotenv
from aiTester import AiTester
import sys
from google import genai
from google.genai import types
import json

load_dotenv()

class Gemini(AiTester):
    
    def obtain_score(self, instructions: str, data: str) -> str:
        client = genai.Client(
            vertexai=True,
            project="ia-analyzer",
            location="us-central1",
        )

        model = self.model
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

    def get_model(self) -> str:
        return self.model


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python gemini.py <attendance_id>")
        sys.exit(1)
    attendance_id = sys.argv[1]
    Gemini("gemini-2.0-flash-001").main(attendance_id)
