import os
import re
import uuid
import json
from pathlib import Path
from typing import Dict, Optional

import joblib
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Chatbot pieces (reuse your existing LangChain + Ollama wiring)
try:
    from chatbot_core import create_chatbot
    OLLAMA_AVAILABLE = True
    print("✅ Ollama enabled for weather-aware intelligent conversation flow")
except Exception as e:
    print(f"Warning: Ollama not available: {e}")
    OLLAMA_AVAILABLE = False

# Force enable Ollama for dynamic conversation (like chatbot_member3.py)
OLLAMA_AVAILABLE = True
print("🚀 FORCING OLLAMA ENABLED - Dynamic conversation mode activated!")


# -----------------------------
# Config
# -----------------------------
ROOT_DIR = Path(__file__).resolve().parent
MODEL_PATH = ROOT_DIR / "district_knn_model.joblib"

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "f72d16875c109d22d0c9119ed9d5c288")


# -----------------------------
# Utilities: phone -> features
# -----------------------------
def normalize_phone(ph: str) -> str:
    if ph is None:
        return ""
    s = re.sub(r"\D", "", str(ph))
    if s.startswith("94") and len(s) > 2:
        s = s[2:]
    if s.startswith("0"):
        s = s[1:]
    return s


def phone_to_features(phone_str: str):
    return {
        "pref2": phone_str[:2] if len(phone_str) >= 2 else "NA",
        "pref3": phone_str[:3] if len(phone_str) >= 3 else "NA",
        "pref4": phone_str[:4] if len(phone_str) >= 4 else "NA",
    }


# -----------------------------
# Load district model
# -----------------------------
if not MODEL_PATH.exists():
    raise RuntimeError(
        f"District model not found at {MODEL_PATH}. Please run train_model.py in Dynamic-question-chatbot-Sumayya first."
    )
district_model = joblib.load(MODEL_PATH)


# -----------------------------
# Weather fetcher
# -----------------------------
def get_weather_summary(city: str) -> str:
    """Return a short weather description for the given city using OpenWeather."""
    print(f"🌤️ Fetching weather for: {city}")
    if not OPENWEATHER_API_KEY:
        print("❌ No API key configured")
        return "unknown (no API key configured)"

    try:
        print(f"🌤️ Making API request for {city}")
        resp = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
        print(f"🌤️ API response status: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        desc = data.get("weather", [{}])[0].get("description", "unknown")
        temp = data.get("main", {}).get("temp", None)
        if temp is None:
            print(f"🌤️ No temperature data, returning: {desc}")
            return desc
        result = f"{desc}, {temp}°C"
        print(f"🌤️ Weather result: {result}")
        return result
    except Exception as e:
        print(f"❌ Weather API error: {e}")
        return "unknown"


# -----------------------------
# Chat session management
# -----------------------------
class Session:
    def __init__(self, district: str, weather: str):
        self.district = district
        self.weather = weather
        if OLLAMA_AVAILABLE:
            self.conversation, self.memory = create_chatbot(district=district, weather=weather)
        else:
            self.conversation = None
            self.memory = None
        self.turns = 0


SESSIONS: Dict[str, Session] = {}


# -----------------------------
# API
# -----------------------------
app = FastAPI(title="SLT-CHATBOT", version="1.0.0")


class InitRequest(BaseModel):
    phone: str


class ChatRequest(BaseModel):
    session_id: str
    message: Optional[str] = ""


@app.get("/", response_class=HTMLResponse)
def index():
    # Minimal UI for testing
    return (
        """
        <html>
          <head>
            <title>SLT-CHATBOT</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
              * { box-sizing: border-box; }
              body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
              }
              .container { 
                max-width: 800px; margin: 0 auto; 
                background: white; border-radius: 20px; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
              }
              .header { 
                background: linear-gradient(135deg, #ff6b6b, #ee5a24); 
                color: white; padding: 30px; text-align: center;
              }
              .header h1 { margin: 0; font-size: 2.5em; font-weight: 300; }
              .header p { margin: 10px 0 0 0; opacity: 0.9; }
              .content { padding: 30px; }
              .input-group { 
                display: flex; gap: 10px; margin-bottom: 20px; 
                align-items: center;
              }
              .input-group input { 
                flex: 1; padding: 15px; border: 2px solid #e0e0e0; 
                border-radius: 10px; font-size: 16px;
                transition: border-color 0.3s;
              }
              .input-group input:focus { 
                outline: none; border-color: #667eea; 
              }
              .btn { 
                padding: 15px 25px; background: linear-gradient(135deg, #667eea, #764ba2); 
                color: white; border: none; border-radius: 10px; 
                font-size: 16px; font-weight: 600; cursor: pointer;
                transition: transform 0.2s;
              }
              .btn:hover { transform: translateY(-2px); }
              .btn:disabled { opacity: 0.6; cursor: not-allowed; }
              .meta { 
                background: #f8f9fa; padding: 15px; border-radius: 10px; 
                margin-bottom: 20px; font-weight: 500;
                border-left: 4px solid #667eea;
              }
              .chat-container { 
                border: 2px solid #e0e0e0; border-radius: 15px; 
                height: 400px; overflow-y: auto; padding: 20px;
                background: #fafafa;
              }
              .message { 
                margin-bottom: 15px; padding: 12px 16px; 
                border-radius: 15px; max-width: 80%;
              }
              .user-message { 
                background: linear-gradient(135deg, #667eea, #764ba2); 
                color: white; margin-left: auto; text-align: right;
              }
              .bot-message { 
                background: white; border: 1px solid #e0e0e0; 
                margin-right: auto;
              }
              .system-message { 
                background: #e3f2fd; border: 1px solid #2196f3; 
                text-align: center; margin: 0 auto;
              }
              .final-message { 
                background: linear-gradient(135deg, #4caf50, #45a049); 
                color: white; text-align: center; margin: 0 auto;
                font-weight: 600;
              }
              .typing { 
                opacity: 0.7; font-style: italic; 
              }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>🏢 SLT-CHATBOT</h1>
                <p>Intelligent Telecom Support Assistant</p>
              </div>
              <div class="content">
                <div class="input-group">
                  <input id="phone" placeholder="Enter landline number (e.g., 011861547)" />
                  <button class="btn" onclick="initSession()">🚀 Start Session</button>
                </div>
                <div id="meta" style="display:none;"></div>
                <div id="chat" class="chat-container" style="display:none;">
                  <div class="message system-message">
                    💬 Chat session will begin here...
                  </div>
                </div>
                <div id="input-area" style="display:none; margin-top:20px;">
                  <div class="input-group">
                    <input id="msg" placeholder="Type your message..." />
                    <button class="btn" onclick="sendMsg()">📤 Send</button>
                  </div>
                </div>
              </div>
            </div>
            <script>
              let sessionId = null;
              let isTyping = false;
              
              async function initSession(){
                const phone = document.getElementById('phone').value.trim();
                if(!phone) { alert('Please enter a landline number'); return; }
                
                const btn = document.querySelector('.btn');
                btn.disabled = true;
                btn.textContent = '⏳ Starting...';
                
                try {
                  const res = await fetch('/init', {
                    method:'POST', 
                    headers:{'Content-Type':'application/json'}, 
                    body: JSON.stringify({phone})
                  });
                  const data = await res.json();
                  
                  if(data.error){ 
                    alert('Error: ' + data.error); 
                    return; 
                  }
                  
                  sessionId = data.session_id;
                  document.getElementById('meta').innerHTML = 
                    `<strong>📍 District:</strong> ${data.district} | <strong>🌤️ Weather:</strong> ${data.weather}`;
                  document.getElementById('meta').style.display = 'block';
                  document.getElementById('chat').style.display = 'block';
                  document.getElementById('input-area').style.display = 'block';
                  
                  const chat = document.getElementById('chat');
                  chat.innerHTML = `
                    <div class="message system-message">${data.system_message}</div>
                    <div class="message bot-message">${data.first_question}</div>
                  `;
                  
                } catch(error) {
                  alert('Connection error: ' + error.message);
                } finally {
                  btn.disabled = false;
                  btn.textContent = '🚀 Start Session';
                }
              }
              
              async function sendMsg(){
                if(!sessionId){ alert('Please start a session first'); return; }
                
                const message = document.getElementById('msg').value.trim();
                if(!message) return;
                
                const chat = document.getElementById('chat');
                const msgInput = document.getElementById('msg');
                const sendBtn = document.querySelector('#input-area .btn');
                
                // Add user message
                chat.innerHTML += `<div class="message user-message">${message}</div>`;
                msgInput.value = '';
                sendBtn.disabled = true;
                sendBtn.textContent = '⏳ Sending...';
                
                // Add typing indicator
                chat.innerHTML += `<div class="message bot-message typing">🤖 Assistant is typing...</div>`;
                chat.scrollTop = chat.scrollHeight;
                
                try {
                  const res = await fetch('/chat', {
                    method:'POST', 
                    headers:{'Content-Type':'application/json'}, 
                    body: JSON.stringify({session_id: sessionId, message})
                  });
                  const data = await res.json();
                  
                  // Remove typing indicator
                  chat.innerHTML = chat.innerHTML.replace('<div class="message bot-message typing">🤖 Assistant is typing...</div>', '');
                  
                  if(data.final){
                    chat.innerHTML += `<div class="message final-message">🎯 Routing Complete: ${JSON.stringify(data.final, null, 2)}</div>`;
                    sessionId = null; // End session
                    document.getElementById('input-area').style.display = 'none';
                  } else if(data.response){
                    chat.innerHTML += `<div class="message bot-message">🤖 ${data.response}</div>`;
                  } else if(data.error){
                    chat.innerHTML += `<div class="message bot-message" style="background:#ffebee;border-color:#f44336;">❌ Error: ${data.error}</div>`;
                  }
                  
                } catch(error) {
                  chat.innerHTML = chat.innerHTML.replace('<div class="message bot-message typing">🤖 Assistant is typing...</div>', '');
                  chat.innerHTML += `<div class="message bot-message" style="background:#ffebee;border-color:#f44336;">❌ Connection Error: ${error.message}</div>`;
                } finally {
                  sendBtn.disabled = false;
                  sendBtn.textContent = '📤 Send';
                  chat.scrollTop = chat.scrollHeight;
                }
              }
              
              // Allow Enter key to send message
              document.getElementById('msg').addEventListener('keypress', function(e) {
                if(e.key === 'Enter') sendMsg();
              });
            </script>
          </body>
        </html>
        """
    )


@app.post("/init")
def init(req: InitRequest):
    try:
        # Predict district
        phone_norm = normalize_phone(req.phone)
        features = phone_to_features(phone_norm)
        try:
            X = pd.DataFrame([features])
            district = district_model.predict(X)[0]
        except Exception as e:
            print(f"❌ District prediction error: {e}")
            raise HTTPException(status_code=500, detail=f"District prediction failed: {e}")

        # Weather lookup based on district
        try:
            print(f"🌤️ Looking up weather for district: {district}")
            weather = get_weather_summary(district)
            print(f"🌤️ Weather lookup result: {weather}")
        except Exception as e:
            print(f"❌ Weather lookup error: {e}")
            import traceback
            traceback.print_exc()
            weather = "unknown"

        # Create chat session
        try:
            sid = str(uuid.uuid4())
            session = Session(district=district, weather=weather)
            SESSIONS[sid] = session
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            raise HTTPException(status_code=500, detail=f"Session creation failed: {e}")

        # Generate first question using the chatbot
        try:
            first_response = session.conversation.invoke({"input": f"(System context: The user is in {district} where the weather is {weather}.) Start asking questions to identify their telecom issue."})["response"]
            session.turns += 1
        except Exception as e:
            print(f"❌ Error generating first question: {e}")
            # Fallback to static question
            weather_lower = weather.lower()
            is_bad_weather = any(word in weather_lower for word in ["rain", "storm", "thunder", "heavy", "severe", "stormy", "windy"])
            
            if is_bad_weather:
                first_response = f"I can see it's {weather} in {district}, which often affects connectivity. Which service is having issues - WiFi, Internet, Landline, or Mobile?"
            else:
                first_response = f"Which service is having issues - WiFi, Internet, Landline, or Mobile?"
        
        system_message = f"Detected district: {district}. Weather: {weather}. I will ask up to 5 questions to identify your issue."
        return {
            "session_id": sid,
            "district": district,
            "weather": weather,
            "system_message": system_message,
            "first_question": first_response,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in init: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# Removed rule-based fallback - now using pure dynamic Ollama conversation


def _maybe_route_final(json_text: str) -> Dict[str, str]:
    """Determine routing based on model's final JSON output."""
    if not json_text or not json_text.strip():
        return {}
    
    # Clean the text - remove any non-JSON content
    json_text = json_text.strip()
    
    # Check for error messages first
    if any(error_word in json_text.lower() for error_word in ["internal", "error", "server", "failed", "exception"]):
        print(f"⚠️ Detected error message in response: {json_text}")
        return {}
    
    # Try to find JSON in the text if it's mixed with other content
    # Look for JSON object anywhere in the text
    start_pos = json_text.find("{")
    if start_pos >= 0:
        # Find the end of JSON object
        brace_count = 0
        end_pos = -1
        for i in range(start_pos, len(json_text)):
            char = json_text[i]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > 0:
            json_text = json_text[start_pos:end_pos]
    
    try:
        result = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON decode error: {e}")
        print(f"⚠️ Problematic text: {json_text}")
        # Some models might return single quotes; last resort attempt
        try:
            result = eval(json_text)
        except Exception as eval_error:
            print(f"⚠️ Eval also failed: {eval_error}")
            return {}

    if not isinstance(result, dict):
        print(f"⚠️ Result is not a dict: {type(result)}")
        return {}

    issue_type = str(result.get("issue_type", "")).strip().lower()
    if issue_type == "weather":
        result["agent"] = "weather"
    elif issue_type:
        result["agent"] = "default"
    else:
        result["agent"] = "default"
    return result


@app.post("/chat")
def chat(req: ChatRequest):
    session = SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    # DYNAMIC OLLAMA CONVERSATION (like chatbot_member3.py template)
    user_message = req.message or ""

    # Run through dynamic chatbot (like the template)
    try:
        response = session.conversation.invoke({"input": user_message})["response"]
        session.turns += 1
        
        # Check if model returned JSON (like the template)
        response_stripped = (response or "").strip()
        
        # Look for JSON in the response (could be wrapped in markdown code blocks)
        json_text = response_stripped
        if "```json" in response_stripped:
            # Extract JSON from markdown code block
            start = response_stripped.find("```json") + 7
            end = response_stripped.find("```", start)
            if end > start:
                json_text = response_stripped[start:end].strip()
        elif response_stripped.startswith("```"):
            # Extract JSON from generic code block
            start = response_stripped.find("```") + 3
            end = response_stripped.find("```", start)
            if end > start:
                json_text = response_stripped[start:end].strip()
        
        if json_text.startswith("{"):
            try:
                final = _maybe_route_final(json_text)
                if final:
                    SESSIONS.pop(req.session_id, None)  # End session
                    return {"final": final}
            except Exception as e:
                print(f"⚠️ JSON parsing error: {e}")
        
        # Enforce max 5 questions (like the template)
        if session.turns >= 5:
            SESSIONS.pop(req.session_id, None)
            return {"final": {"issue_type": "Other", "sub_category": "Unknown", "agent": "default"}}
        
        # Return dynamic response
        return {"response": response}
        
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        # If Ollama fails, provide a simple fallback message
        return {"response": "I'm having trouble connecting to my AI system. Please try again or contact support directly."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8083
                , reload=True)


