import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_GENERATIVEAI_API_KEY"])

print("Available models for text generation:\n")

for model in client.models.list():
    if "generateContent" in model.supported_actions:
        print(f"Name for code: {model.name}")
        print(f"Description: {model.description}")
        print("-" * 40)