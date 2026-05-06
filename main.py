import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

TARGET_MODEL = 'gemini-3.1-flash-lite-preview'
client = genai.Client(api_key=os.environ["GOOGLE_GENERATIVEAI_API_KEY"])
CONFIG_FILE = "device_config.json"

# ==========================================
# 1. Tools (Hardware, File System & Web Search)
# ==========================================
def get_device_telemetry(device_id: str) -> dict:
    """
    Fetches current real-time telemetry data (voltage, temperature, pressure).
    You MUST call this tool FIRST to understand the physical state of the device.
    """
    print(f"[TOOL] Fetching telemetry for {device_id}...")
    return {
        "voltage": "230V", 
        "valve_status": "mechanically_ok", 
        "error": "timeout"
    }

def edit_local_config(filepath: str, key_to_change: str, new_value: int) -> dict:
    """Reads a local JSON config file and updates a specific key."""
    print(f"[TOOL] Editing {filepath} -> {key_to_change}: {new_value}")
    # Hier würde die echte Datei-Logik stehen (wie in unserem vorherigen Beispiel)
    return {"status": "success", "message": f"Updated {key_to_change} to {new_value}"}

def save_last_command_to_device(device_id: str, alert_type: str, last_command: str) -> dict:
    """
    Saves the final troubleshooting command directly to the device's local memory.
    You MUST call this tool BEFORE giving your final action plan to the user.
    """
    print(f"[TOOL] Saved alert to {device_id} memory.")
    return {"status": "success"}

# ==========================================
# 2. Die KI-Logik (Async Generator)
# ==========================================
async def stream_iot_resolution(device_id: str, alert_type: str, scenario: str):
    """Generiert die Antwort und nutzt Tools autonom."""
    
    google_search_tool = types.Tool(google_search=types.GoogleSearch())
    
    prompt = f"""
    You are an expert duty IoT engineer. Analyze the provided telemetry data and provide troubleshooting advice.
    DEVICE ID: {device_id}
    ERROR: {alert_type}
    DETAILS: {scenario}
    CONFIG: {CONFIG_FILE}

    <examples>
      <example>
        <context>
          This example shows how to handle a tricky physical installation error and format the output perfectly.
        </context>
        <sample_telemetry>
          <error_code>CRITICAL_DIRECTION</error_code>
          <physical_symptoms>The system is calling for cooling, but the temperature is rising rapidly.</physical_symptoms>
        </sample_telemetry>
        <ideal_output>
          {{
            "diagnosis": "The cooling valve is likely wired in reverse (polarity flipped) or mechanically installed backward, causing it to heat when it should cool.",
            "action_plan": [
              "Immediately override the valve to manual OFF to prevent further heating.",
              "Dispatch a technician to check the physical wiring polarity of the actuator.",
              "Save alert to device memory."
            ],
            "safety_risk": true
          }}
        </ideal_output>
      </example>
    </examples>
    
    <telemetry_data>
        <error_type>{alert_type}</error_type>
        <physical_symptoms>{scenario}</physical_symptoms>
    </telemetry_data>
    
    <process_steps>
        1. Check telemetry using `get_device_telemetry`.
        2. Use Google Search to find manufacturer docs if needed.
        3. Identify the root cause of the error.
        4. Determine if this poses a physical safety risk to the facility.
        5. Formulate a step-by-step repair plan.
        6. Use `edit_local_config` to fix settings.
        7. Use `save_last_command_to_device` to log actions.
        8. Write a clear Markdown report for the React frontend operator.
    </process_steps>

     <output_guidelines>
        - Do NOT return JSON. Write a professional, human-readable report in Markdown.
        - Start with a clear "Diagnosis" section.
        - Follow with an "Action Plan" using bullet points.
        - State the "Severity Risk" clearly (e.g., HIGH, CRITICAL).
        - Explicitly mention what tools you used (e.g., "I checked the telemetry...", "I saved the command to the device memory...").
    </output_guidelines>
    """
    
    chat = client.aio.chats.create(
        model=TARGET_MODEL,
        config=types.GenerateContentConfig(
            temperature=0.2,
            tools=[get_device_telemetry, edit_local_config, save_last_command_to_device, google_search_tool],
        )
    )
    
    response_stream = await chat.send_message_stream(prompt)
    async for chunk in response_stream:
        if chunk.text:
            yield chunk.text

# ==========================================
# 3. FastAPI Endpoints
# ==========================================
@app.get("/")
async def root():
    return {"message": "IoT AI Backend is running!"}

@app.websocket("/ws/troubleshoot")
async def websocket_endpoint(websocket: WebSocket):
    """
    Dieser Endpoint wird vom React-Frontend aufgerufen, 
    um eine Echtzeit-Verbindung aufzubauen.
    """
    await websocket.accept()
    try:
        # 1. Warte auf die Fehlermeldung vom React-Frontend
        data = await websocket.receive_json()
        device_id = data.get("device_id", "UNKNOWN")
        alert_type = data.get("alert_type", "UNKNOWN")
        scenario = data.get("scenario", "UNKNOWN")
        
        # 2. Starte die KI und streame die Text-Chunks zurück ans Frontend
        async for chunk in stream_iot_resolution(device_id, alert_type, scenario):
            await websocket.send_text(chunk)
            
        # 3. Sende ein Signal, dass die KI fertig ist
        await websocket.send_text("[DONE]")
        
    except WebSocketDisconnect:
        print("Client disconnected")