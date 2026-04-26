import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ["GOOGLE_GENERATIVEAI_API_KEY"])

def start_chat(system_prompt=None, temperature=0.7):
    config_params = {"max_output_tokens": 1000, "temperature": temperature}
    
    if system_prompt:
        config_params["system_instruction"] = system_prompt
        
    return client.chats.create(
        model='gemini-1.5-flash',
        config=types.GenerateContentConfig(**config_params)
    )

system = """
You are a patient math tutor.
Do not directly answer a student's questions.
Guide them to a solution step by step.
"""

#Low temperature (0.0) – precise, predictable results (ideal for code)
#High temperature (1.0) – creative, varied results (ideal for brainstorming)
tutor_chat = start_chat(system_prompt=system, temperature=0.0)

full_message = ""

answer1WithStream = tutor_chat.send_message_stream("I need help with 5 + 7")
for chunk in answer1WithStream:
    print(chunk.text, end="", flush=True)
    
    full_message += chunk.text
print("-" * 20)
print("Bot:", full_message)

answer2 = tutor_chat.send_message("Can you just tell me the answer?")
print("Bot:", answer2.text)