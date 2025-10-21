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
    print("✅ Ollama enabled for intelligent conversation flow")
except Exception as e:
    print(f"Warning: Ollama not available: {e}")
    OLLAMA_AVAILABLE = False


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
    if not OPENWEATHER_API_KEY:
        return "unknown (no API key configured)"

    try:
        resp = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        desc = data.get("weather", [{}])[0].get("description", "unknown")
        temp = data.get("main", {}).get("temp", None)
        if temp is None:
            return desc
        return f"{desc}, {temp}°C"
    except Exception:
        return "unknown"


# -----------------------------
# Chat session management
# -----------------------------
class Session:
    def __init__(self, district: str, weather: str):
        self.district = district
        self.weather = weather
        if OLLAMA_AVAILABLE:
            self.conversation, self.memory = create_chatbot()
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
                  chat.innerHTML = `<div class="message system-message">${data.system_message}</div>`;
                  
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
    # Predict district
    phone_norm = normalize_phone(req.phone)
    features = phone_to_features(phone_norm)
    try:
        X = pd.DataFrame([features])
        district = district_model.predict(X)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"District prediction failed: {e}")

    # Weather lookup based on district
    weather = get_weather_summary(district)

    # Create chat session
    sid = str(uuid.uuid4())
    session = Session(district=district, weather=weather)
    SESSIONS[sid] = session

    system_message = f"Detected district: {district}. Weather: {weather}. I will ask up to 5 questions to identify your issue."
    return {
        "session_id": sid,
        "district": district,
        "weather": weather,
        "system_message": system_message,
    }


def _handle_smart_fallback(session: Session, user_message: str, session_id: str = None):
    """Handle smart fallback when Ollama fails"""
    session.turns += 1
    user_msg = (user_message or "").lower()
    
    # Store conversation context in session for better routing
    if not hasattr(session, 'conversation_context'):
        session.conversation_context = {
            'service_type': None,
            'weather_related': False,
            'problem_description': None,
            'timing': None
        }
    
    # Check if weather is already bad based on district weather data
    weather_lower = session.weather.lower()
    is_bad_weather = any(word in weather_lower for word in ["rain", "storm", "thunder", "heavy", "severe", "stormy", "windy"])
    
    # Analyze user input to provide contextual responses
    if session.turns == 1:
        if any(word in user_msg for word in ["internet", "wifi", "wi-fi", "wiif", "connection", "network", "broadband"]):
            session.conversation_context['service_type'] = 'internet'
            if is_bad_weather:
                session.conversation_context['weather_related'] = True
                return {"response": f"I understand you're having internet connectivity issues. I can see there's {session.weather} in your area, which often affects connectivity. Can you describe the specific problem you're facing?"}
            else:
                return {"response": "I understand you're having internet connectivity issues. Is this problem related to weather conditions in your area?"}
        elif any(word in user_msg for word in ["landline", "phone", "telephone"]):
            session.conversation_context['service_type'] = 'landline'
            if is_bad_weather:
                session.conversation_context['weather_related'] = True
                return {"response": f"I see you're having landline issues. I notice there's {session.weather} in your area, which can affect phone lines. Can you describe the specific problem you're experiencing?"}
            else:
                return {"response": "I see you're having landline issues. Are you experiencing this during bad weather conditions?"}
        elif any(word in user_msg for word in ["mobile", "cell", "phone"]):
            session.conversation_context['service_type'] = 'mobile'
            if is_bad_weather:
                session.conversation_context['weather_related'] = True
                return {"response": f"You're having mobile service problems. I can see there's {session.weather} in your area, which often impacts mobile signals. Can you describe the specific issue?"}
            else:
                return {"response": "You're having mobile service problems. Is this happening during stormy weather?"}
        else:
            return {"response": "What type of service issue are you experiencing? (Internet/WiFi/Landline/Mobile)"}
    
    elif session.turns == 2:
        # If weather was already detected as bad, skip weather question and go to problem description
        if session.conversation_context.get('weather_related', False):
            session.conversation_context['problem_description'] = user_msg
            if any(word in user_msg for word in ["disconnect", "disconnecting", "drop", "dropping", "cut", "cutting", "not working", "isn't working"]):
                return {"response": "I see you're experiencing connection issues. When did this problem first start?"}
            elif any(word in user_msg for word in ["slow", "slowly", "speed", "lag", "lagging"]):
                return {"response": "You're experiencing slow speeds. When did you first notice this performance issue?"}
            else:
                return {"response": "When did this issue first occur?"}
        else:
            # Only ask about weather if it wasn't already detected as bad
            if any(word in user_msg for word in ["yes", "yeah", "yep", "rain", "storm", "weather", "wind", "thunder", "raining", "stormy"]):
                session.conversation_context['weather_related'] = True
                return {"response": "Since this is weather-related, can you describe the specific problem you're facing with your connection?"}
            elif any(word in user_msg for word in ["no", "nope", "not", "unrelated"]):
                session.conversation_context['weather_related'] = False
                return {"response": "I understand this isn't weather-related. Can you describe the specific technical issue you're experiencing?"}
            else:
                return {"response": "Is this issue related to weather conditions in your area? (Yes/No)"}
    
    elif session.turns == 3:
        # If problem description wasn't captured in turn 2, capture it now
        if not session.conversation_context.get('problem_description'):
            session.conversation_context['problem_description'] = user_msg
            if any(word in user_msg for word in ["disconnect", "disconnecting", "drop", "dropping", "cut", "cutting", "not working", "isn't working"]):
                return {"response": "I see you're experiencing connection issues. When did this problem first start?"}
            elif any(word in user_msg for word in ["slow", "slowly", "speed", "lag", "lagging"]):
                return {"response": "You're experiencing slow speeds. When did you first notice this performance issue?"}
            else:
                return {"response": "When did this issue first occur?"}
        else:
            # Problem description already captured, now ask about timing
            session.conversation_context['timing'] = user_msg
            return {"response": "Thank you for providing the details. Let me route you to the appropriate support agent."}
    
    elif session.turns == 4:
        session.conversation_context['timing'] = user_msg
        # Check if we have enough info to route - if so, route immediately
        if session.conversation_context.get('service_type') and session.conversation_context.get('problem_description'):
            # Determine routing based on conversation context
            if session.conversation_context.get('weather_related', False):
                service_type = session.conversation_context.get('service_type', 'WiFi')
                result = {"final": {"issue_type": "Weather", "sub_category": service_type.title(), "agent": "weather"}}
            else:
                service_type = session.conversation_context.get('service_type', 'Technical')
                result = {"final": {"issue_type": "Network", "sub_category": service_type.title(), "agent": "default"}}
            
            # Clean up session after determining result
            if session_id:
                SESSIONS.pop(session_id, None)
            return result
        else:
            return {"response": "Thank you for providing the details. Let me route you to the appropriate support agent."}
    
    else:
        # Final response after 5 turns - determine routing based on conversation context
        # Determine routing based on conversation context
        if session.conversation_context.get('weather_related', False):
            service_type = session.conversation_context.get('service_type', 'WiFi')
            result = {"final": {"issue_type": "Weather", "sub_category": service_type.title(), "agent": "weather"}}
        else:
            service_type = session.conversation_context.get('service_type', 'Technical')
            result = {"final": {"issue_type": "Network", "sub_category": service_type.title(), "agent": "default"}}
        
        # Clean up session after determining result
        if session_id:
            SESSIONS.pop(session_id, None)
        return result


def _maybe_route_final(json_text: str) -> Dict[str, str]:
    """Determine routing based on model's final JSON output."""
    try:
        result = json.loads(json_text)
    except Exception:
        # Some models might return single quotes; last resort attempt
        try:
            result = eval(json_text)
        except Exception:
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

    if not OLLAMA_AVAILABLE:
        # Smart mock responses when Ollama is not available
        session.turns += 1
        user_msg = (req.message or "").lower()
        
        # Store conversation context in session for better routing
        if not hasattr(session, 'conversation_context'):
            session.conversation_context = {
                'service_type': None,
                'weather_related': False,
                'problem_description': None,
                'timing': None
            }
        
        # Analyze user input to provide contextual responses
        if session.turns == 1:
            # Check if weather is already bad based on district weather data
            weather_lower = session.weather.lower()
            is_bad_weather = any(word in weather_lower for word in ["rain", "storm", "thunder", "heavy", "severe", "stormy", "windy"])
            
            if any(word in user_msg for word in ["internet", "wifi", "wi-fi", "wiif", "connection", "network", "broadband"]):
                session.conversation_context['service_type'] = 'internet'
                if is_bad_weather:
                    session.conversation_context['weather_related'] = True
                    return {"response": f"I understand you're having internet connectivity issues. I can see there's {session.weather} in your area, which often affects connectivity. Can you describe the specific problem you're facing?"}
                else:
                    return {"response": "I understand you're having internet connectivity issues. Is this problem related to weather conditions in your area?"}
            elif any(word in user_msg for word in ["landline", "phone", "telephone"]):
                session.conversation_context['service_type'] = 'landline'
                if is_bad_weather:
                    session.conversation_context['weather_related'] = True
                    return {"response": f"I see you're having landline issues. I notice there's {session.weather} in your area, which can affect phone lines. Can you describe the specific problem you're experiencing?"}
                else:
                    return {"response": "I see you're having landline issues. Are you experiencing this during bad weather conditions?"}
            elif any(word in user_msg for word in ["mobile", "cell", "phone"]):
                session.conversation_context['service_type'] = 'mobile'
                if is_bad_weather:
                    session.conversation_context['weather_related'] = True
                    return {"response": f"You're having mobile service problems. I can see there's {session.weather} in your area, which often impacts mobile signals. Can you describe the specific issue?"}
                else:
                    return {"response": "You're having mobile service problems. Is this happening during stormy weather?"}
            else:
                return {"response": "What type of service issue are you experiencing? (Internet/WiFi/Landline/Mobile)"}
        
        elif session.turns == 2:
            # If weather was already detected as bad, skip weather question and go to problem description
            if session.conversation_context.get('weather_related', False):
                session.conversation_context['problem_description'] = user_msg
                if any(word in user_msg for word in ["disconnect", "disconnecting", "drop", "dropping", "cut", "cutting", "not working", "isn't working"]):
                    return {"response": "I see you're experiencing connection issues. When did this problem first start?"}
                elif any(word in user_msg for word in ["slow", "slowly", "speed", "lag", "lagging"]):
                    return {"response": "You're experiencing slow speeds. When did you first notice this performance issue?"}
                else:
                    return {"response": "When did this issue first occur?"}
            else:
                # Only ask about weather if it wasn't already detected as bad
                if any(word in user_msg for word in ["yes", "yeah", "yep", "rain", "storm", "weather", "wind", "thunder", "raining", "stormy"]):
                    session.conversation_context['weather_related'] = True
                    return {"response": "Since this is weather-related, can you describe the specific problem you're facing with your connection?"}
                elif any(word in user_msg for word in ["no", "nope", "not", "unrelated"]):
                    session.conversation_context['weather_related'] = False
                    return {"response": "I understand this isn't weather-related. Can you describe the specific technical issue you're experiencing?"}
                else:
                    return {"response": "Is this issue related to weather conditions in your area? (Yes/No)"}
        
        elif session.turns == 3:
            # If problem description wasn't captured in turn 2, capture it now
            if not session.conversation_context.get('problem_description'):
                session.conversation_context['problem_description'] = user_msg
                if any(word in user_msg for word in ["disconnect", "disconnecting", "drop", "dropping", "cut", "cutting", "not working", "isn't working"]):
                    return {"response": "I see you're experiencing connection issues. When did this problem first start?"}
                elif any(word in user_msg for word in ["slow", "slowly", "speed", "lag", "lagging"]):
                    return {"response": "You're experiencing slow speeds. When did you first notice this performance issue?"}
                else:
                    return {"response": "When did this issue first occur?"}
            else:
                # Problem description already captured, now ask about timing
                session.conversation_context['timing'] = user_msg
                return {"response": "Thank you for providing the details. Let me route you to the appropriate support agent."}
        
        elif session.turns == 4:
            session.conversation_context['timing'] = user_msg
            return {"response": "Thank you for providing the details. Let me route you to the appropriate support agent."}
        
        else:
            # Final response after 5 turns - determine routing based on conversation context
            SESSIONS.pop(req.session_id, None)
            
            # Determine routing based on conversation context
            if session.conversation_context.get('weather_related', False):
                service_type = session.conversation_context.get('service_type', 'WiFi')
                return {"final": {"issue_type": "Weather", "sub_category": service_type.title(), "agent": "weather"}}
            else:
                service_type = session.conversation_context.get('service_type', 'Technical')
                return {"final": {"issue_type": "Network", "sub_category": service_type.title(), "agent": "default"}}

    # Prepend district/weather context only on first user turn
    user_message = req.message or ""
    if session.turns == 0:
        ctx = f"(System context: The user is in {session.district} where the weather is {session.weather}.) "
        user_message = ctx + user_message

    # Run through chatbot using invoke method with error handling
    try:
        response = session.conversation.invoke({"input": user_message})["response"]
        session.turns += 1
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        # Fall back to smart system if Ollama fails
        return _handle_smart_fallback(session, req.message, req.session_id)

    # If model returns JSON, finalize and route
    response_stripped = (response or "").strip()
    if response_stripped.startswith("{"):
        final = _maybe_route_final(response_stripped)
        if final:
            # Cleanup the session when final reached
            try:
                session.memory.clear()
            except Exception:
                pass
            SESSIONS.pop(req.session_id, None)
            return {"final": final}

        # Enforce max 5 questions from assistant side
        if session.turns >= 5:
            # If not finalized, default route
            SESSIONS.pop(req.session_id, None)
            return {"final": {"issue_type": "Other", "sub_category": "Unknown", "agent": "default"}}

        return {"response": response}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8081, reload=True)


