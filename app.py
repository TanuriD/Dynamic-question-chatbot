# import os
# import re
# import uuid
# import json
# from pathlib import Path
# from typing import Dict, Optional

# import joblib
# import pandas as pd
# import requests
# from fastapi import FastAPI, HTTPException
# from fastapi.responses import HTMLResponse, FileResponse
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel, field_validator

# # Chatbot pieces (reuse your existing LangChain + Ollama wiring)
# try:
#     from chatbot_core import create_chatbot
#     OLLAMA_AVAILABLE = True
#     print("✅ Ollama enabled for weather-aware intelligent conversation flow")
# except Exception as e:
#     print(f"Warning: Ollama not available: {e}")
#     OLLAMA_AVAILABLE = False

# # Force enable Ollama for dynamic conversation (like chatbot_member3.py)
# OLLAMA_AVAILABLE = True
# print("🚀 FORCING OLLAMA ENABLED - Dynamic conversation mode activated!")

# # -----------------------------
# # Config
# # -----------------------------
# ROOT_DIR = Path(__file__).resolve().parent
# MODEL_PATH = ROOT_DIR / "district_knn_model.joblib"

# OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "f72d16875c109d22d0c9119ed9d5c288")

# # -----------------------------
# # Utilities: phone -> features
# # -----------------------------
# def normalize_phone(ph: str) -> str:
#     if ph is None:
#         return ""
#     s = re.sub(r"\D", "", str(ph))
#     if s.startswith("94") and len(s) > 2:
#         s = s[2:]
#     if s.startswith("0"):
#         s = s[1:]
#     return s

# def phone_to_features(phone_str: str):
#     return {
#         "pref2": phone_str[:2] if len(phone_str) >= 2 else "NA",
#         "pref3": phone_str[:3] if len(phone_str) >= 3 else "NA",
#         "pref4": phone_str[:4] if len(phone_str) >= 4 else "NA",
#     }

# # -----------------------------
# # Load district model
# # -----------------------------
# if not MODEL_PATH.exists():
#     raise RuntimeError(
#         f"District model not found at {MODEL_PATH}. Please run train_model.py in Dynamic-question-chatbot-Sumayya first."
#     )
# district_model = joblib.load(MODEL_PATH)

# # -----------------------------
# # Weather fetcher
# # -----------------------------
# def get_weather_summary(city: str) -> str:
#     """Return a short weather description for the given city using OpenWeather."""
#     print(f"🌤️ Fetching weather for: {city}")
#     if not OPENWEATHER_API_KEY:
#         print("❌ No API key configured")
#         return "unknown (no API key configured)"

#     try:
#         print(f"🌤️ Making API request for {city}")
#         resp = requests.get(
#             "http://api.openweathermap.org/data/2.5/weather",
#             params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
#             timeout=10,
#         )
#         print(f"🌤️ API response status: {resp.status_code}")
#         resp.raise_for_status()
#         data = resp.json()
#         desc = data.get("weather", [{}])[0].get("description", "unknown")
#         temp = data.get("main", {}).get("temp", None)
#         if temp is None:
#             print(f"🌤️ No temperature data, returning: {desc}")
#             return desc
#         result = f"{desc}, {temp}°C"
#         print(f"🌤️ Weather result: {result}")
#         return result
#     except Exception as e:
#         print(f"❌ Weather API error: {e}")
#         return "unknown"

# # -----------------------------
# # Chat session management
# # -----------------------------
# class Session:
#     def __init__(self, district: str, weather: str):
#         self.district = district
#         self.weather = weather
#         if OLLAMA_AVAILABLE:
#             self.conversation, self.memory = create_chatbot(district=district, weather=weather)
#         else:
#             self.conversation = None
#             self.memory = None
#         self.turns = 0

# SESSIONS: Dict[str, Session] = {}

# # -----------------------------
# # FINAL SUMMARIZER (NEW)
# # -----------------------------
# # We import here to avoid hard dependency if LangChain message classes change
# try:
#     from langchain_core.messages import HumanMessage, AIMessage
# except Exception:
#     HumanMessage = type("HumanMessage", (), {})
#     AIMessage = type("AIMessage", (), {})

# def _render_transcript(memory) -> str:
#     """Render a short Q/A transcript from ConversationBufferMemory."""
#     try:
#         msgs = getattr(memory, "chat_memory").messages
#     except Exception:
#         return ""
#     lines = []
#     for m in msgs:
#         role = getattr(m, "type", None) or m.__class__.__name__.lower()
#         content = getattr(m, "content", "")
#         if "human" in role:
#             lines.append(f"User: {content}")
#         else:
#             lines.append(f"Assistant: {content}")
#     # keep recent snippet
#     return "\n".join(lines[-14:])  # last ~7 exchanges

# def _summarize_conclusion(session: Session, final_json: Dict[str, str]) -> str:
#     """
#     Ask the LLM to produce a concise, user-friendly conclusion using:
#     - district, weather
#     - the chat transcript
#     - final routing labels (issue_type, sub_category, agent)
#     """
#     sub_category = final_json.get("sub_category", "Unknown")
#     issue_type   = final_json.get("issue_type", "Other")
#     agent        = final_json.get("agent", "default")

#     transcript = _render_transcript(session.memory) if session.memory else ""
#     district = session.district
#     weather  = session.weather

#     # Prefer using the same LLM instance inside the conversation chain
#     # Since we changed to function-based conversation, we'll create a simple LLM call
#     try:
#         from langchain_ollama import ChatOllama
#         llm = ChatOllama(model=os.getenv("OLLAMA_MODEL", "gemma3"), temperature=0.6)
#     except:
#         llm = None

#     prompt = f"""
# You are "SLT Resolution Summarizer". Write a concise, friendly conclusion for the customer.
# Use ONLY the conversation and context; do not invent facts.

# GOAL:
# 1) One sentence explaining the most likely cause in plain language (tailored to their answers).
# 2) 2–3 short bullet points on what the assigned agent will do next (no heavy jargon).
# 3) One final line: "Service: <SubCategory>. Agent: <Agent>."

# CONTEXT:
# - District: {district}
# - Weather: {weather}
# - Issue type: {issue_type}
# - Sub-category: {sub_category}
# - Transcript:
# {transcript}

# RESPONSE RULES:
# - Keep it under ~80–120 words.
# - Be specific to what the user told us (symptoms, timing, devices, etc.).
# - If uncertainty remains, state what we will check first.
# - Output plain text only (no JSON, no markdown fences).
# """.strip()

#     try:
#         if llm:
#             result = llm.invoke(prompt)
#             return result.content if hasattr(result, 'content') else str(result)
#         # fallback text if LLM missing
#         return (f"Summary: Based on your answers, this looks like a {issue_type} issue on {sub_category}. "
#                 f"Our {agent} agent will assist you next with targeted checks and fixes.")
#     except Exception:
#         return (f"Summary: Based on your answers, this looks like a {issue_type} issue on {sub_category}. "
#                 f"Our {agent} agent will assist you next with targeted checks and fixes.")

# # -----------------------------
# # API
# # -----------------------------
# app = FastAPI(title="SLT-CHATBOT", version="1.0.0")

# # Serve static assets (CSS/JS/HTML)
# app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")

# class InitRequest(BaseModel):
#     phone: str

#     # ✅ Updated to Pydantic V2 syntax
#     @field_validator("phone")
#     @classmethod
#     def must_be_valid_landline(cls, v: str):
#         digits = re.sub(r"\D", "", v or "")
#         # Accept 7–10 digits after stripping +94/leading 0 (tweak if your dataset requires)
#         if not re.fullmatch(r"\d{7,10}", digits):
#             raise ValueError("Please enter a valid landline number (digits only).")
#         return v

# class ChatRequest(BaseModel):
#     session_id: str
#     message: Optional[str] = ""

# @app.get("/", response_class=HTMLResponse)
# def index():
#     index_path = ROOT_DIR / "static" / "index.html"
#     return FileResponse(index_path)

# @app.post("/init")
# def init(req: InitRequest):
#     try:
#         # Normalize and re-validate defensively (double-check on server)
#         phone_norm = normalize_phone(req.phone)
#         if (not phone_norm) or (not phone_norm.isdigit()) or (not (7 <= len(phone_norm) <= 10)):
#             raise HTTPException(status_code=422, detail="Please enter a valid landline number (digits only).")

#         # Predict district
#         features = phone_to_features(phone_norm)
#         try:
#             X = pd.DataFrame([features])
#             district = district_model.predict(X)[0]
#         except Exception as e:
#             print(f"❌ District prediction error: {e}")
#             raise HTTPException(status_code=500, detail=f"District prediction failed: {e}")

#         # Weather lookup based on district
#         try:
#             print(f"🌤️ Looking up weather for district: {district}")
#             weather = get_weather_summary(district)
#             print(f"🌤️ Weather lookup result: {weather}")
#         except Exception as e:
#             print(f"❌ Weather lookup error: {e}")
#             import traceback
#             traceback.print_exc()
#             weather = "unknown"

#         # Create chat session
#         try:
#             sid = str(uuid.uuid4())
#             session = Session(district=district, weather=weather)
#             SESSIONS[sid] = session
#         except Exception as e:
#             print(f"❌ Session creation error: {e}")
#             raise HTTPException(status_code=500, detail=f"Session creation failed: {e}")

#         # Generate first question using the chatbot
#         try:
#             first_response = session.conversation({
#                 "input": f"Start asking questions to identify their telecom issue."
#             })["response"]
#             session.turns += 1
#         except Exception as e:
#             print(f"❌ Error generating first question: {e}")
#             # Fallback to static question
#             weather_lower = weather.lower()
#             is_bad_weather = any(word in weather_lower for word in ["rain", "storm", "thunder", "heavy", "severe", "stormy", "windy"])
#             if is_bad_weather:
#                 first_response = (
#                     f"I can see it's {weather} in {district}, which often affects connectivity. "
#                     f"Which service is having issues - WiFi, Internet, Landline, or Mobile?"
#                 )
#             else:
#                 first_response = "Which service is having issues - WiFi, Internet, Landline, or Mobile?"

#         system_message = f"Detected district: {district}. Weather: {weather}. I will ask up to 5 questions to identify your issue."
#         return {
#             "session_id": sid,
#             "district": district,
#             "weather": weather,
#             "system_message": system_message,
#             "first_question": first_response,
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         print(f"❌ Unexpected error in init: {e}")
#         raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

# # Removed rule-based fallback - now using pure dynamic Ollama conversation

# def _maybe_route_final(json_text: str) -> Dict[str, str]:
#     """Determine routing based on model's final JSON output."""
#     if not json_text or not json_text.strip():
#         return {}

#     # Clean the text - remove any non-JSON content
#     json_text = json_text.strip()

#     # Check for error messages first
#     if any(error_word in json_text.lower() for error_word in ["internal", "error", "server", "failed", "exception"]):
#         print(f"⚠️ Detected error message in response: {json_text}")
#         return {}

#     # Try to find JSON in the text if it's mixed with other content
#     start_pos = json_text.find("{")
#     if start_pos >= 0:
#         brace_count = 0
#         end_pos = -1
#         for i in range(start_pos, len(json_text)):
#             char = json_text[i]
#             if char == "{":
#                 brace_count += 1
#             elif char == "}":
#                 brace_count -= 1
#                 if brace_count == 0:
#                     end_pos = i + 1
#                     break
#         if end_pos > 0:
#             json_text = json_text[start_pos:end_pos]

#     try:
#         result = json.loads(json_text)
#     except json.JSONDecodeError as e:
#         print(f"⚠️ JSON decode error: {e}")
#         print(f"⚠️ Problematic text: {json_text}")
#         try:
#             result = eval(json_text)
#         except Exception as eval_error:
#             print(f"⚠️ Eval also failed: {eval_error}")
#             return {}

#     if not isinstance(result, dict):
#         print(f"⚠️ Result is not a dict: {type(result)}")
#         return {}

#     issue_type = str(result.get("issue_type", "")).strip().lower()
#     if issue_type == "weather":
#         result["agent"] = "weather"
#     elif issue_type:
#         result["agent"] = "default"
#     else:
#         result["agent"] = "default"
#     return result

# @app.post("/chat")
# def chat(req: ChatRequest):
#     session = SESSIONS.get(req.session_id)
#     if not session:
#         raise HTTPException(status_code=404, detail="Invalid session_id")

#     user_message = req.message or ""

#     # If we're at turn 4, remind the model to return JSON next turn with the service type
#     if session.turns == 4:
#         user_message = (
#             f"{user_message} [REMINDER: This is your 4th question. On your next response, you MUST return JSON "
#             f"with the correct sub_category based on the service type the user mentioned earlier "
#             f"(WiFi/Internet/Landline/Mobile). Do NOT return Unknown.]"
#         )

#     try:
#         response = session.conversation({"input": user_message})["response"]
#         session.turns += 1

#         response_stripped = (response or "").strip()

#         # Look for JSON in code blocks
#         json_text = response_stripped
#         if "```json" in response_stripped:
#             start = response_stripped.find("```json") + 7
#             end = response_stripped.find("```", start)
#             if end > start:
#                 json_text = response_stripped[start:end].strip()
#         elif response_stripped.startswith("```"):
#             start = response_stripped.find("```") + 3
#             end = response_stripped.find("```", start)
#             if end > start:
#                 json_text = response_stripped[start:end].strip()

#         if json_text.startswith("{"):
#             try:
#                 final = _maybe_route_final(json_text)
#                 if final:
#                     # NEW: produce readable summary too
#                     summary = _summarize_conclusion(session, final)
#                     SESSIONS.pop(req.session_id, None)  # End session
#                     return {"final": final, "summary": summary}
#             except Exception as e:
#                 print(f"⚠️ JSON parsing error: {e}")

#         # Enforce max 5 questions
#         if session.turns >= 5:
#             try:
#                 final_prompt = (
#                     'You must now return JSON with issue_type and sub_category. '
#                     'Look back at the conversation - what service did the user mention (WiFi/Internet/Landline/Mobile)? '
#                     'Return ONLY JSON in format: {"issue_type": "Technical", "sub_category": "WiFi"}. '
#                     'sub_category MUST be one of: WiFi, Internet, Landline, or Mobile - NEVER Unknown.'
#                 )
#                 final_response = session.conversation({"input": final_prompt})["response"]

#                 final_stripped = (final_response or "").strip()
#                 final_json_text = final_stripped
#                 if "```json" in final_stripped:
#                     start = final_stripped.find("```json") + 7
#                     end = final_stripped.find("```", start)
#                     if end > start:
#                         final_json_text = final_stripped[start:end].strip()
#                 elif final_stripped.startswith("```"):
#                     start = final_stripped.find("```") + 3
#                     end = final_stripped.find("```", start)
#                     if end > start:
#                         final_json_text = final_stripped[start:end].strip()

#                 if final_json_text.startswith("{"):
#                     final_result = _maybe_route_final(final_json_text)
#                     if final_result and final_result.get("sub_category") and final_result.get("sub_category") != "Unknown":
#                         summary = _summarize_conclusion(session, final_result)  # NEW
#                         SESSIONS.pop(req.session_id, None)
#                         return {"final": final_result, "summary": summary}
#             except Exception as e:
#                 print(f"⚠️ Final JSON generation error: {e}")

#             SESSIONS.pop(req.session_id, None)
#             final_result = {"issue_type": "Other", "sub_category": "Unknown", "agent": "default"}
#             summary = _summarize_conclusion(session, final_result)  # NEW
#             return {"final": final_result, "summary": summary}

#         return {"response": response}

#     except Exception as e:
#         print(f"⚠️ Ollama error: {e}")
#         return {"response": "I'm having trouble connecting to my AI system. Please try again or contact support directly."}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app:app", host="0.0.0.0", port=8083, reload=True)


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
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

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
# FINAL SUMMARIZER (MODIFIED)
# -----------------------------
# We import here to avoid hard dependency if LangChain message classes change
try:
    from langchain_core.messages import HumanMessage, AIMessage
except Exception:
    HumanMessage = type("HumanMessage", (), {})
    AIMessage = type("AIMessage", (), {})

def _render_transcript(memory) -> str:
    """Render a short Q/A transcript from ConversationBufferMemory."""
    try:
        msgs = getattr(memory, "chat_memory").messages
    except Exception:
        return ""
    lines = []
    for m in msgs:
        role = getattr(m, "type", None) or m.__class__.__name__.lower()
        content = getattr(m, "content", "")
        if "human" in role:
            lines.append(f"User: {content}")
        else:
            lines.append(f"Assistant: {content}")
    # keep recent snippet
    return "\n".join(lines[-14:])  # last ~7 exchanges

def _summarize_conclusion(session: Session, final_json: Dict[str, str]) -> Dict[str, str]:
    """
    Ask the LLM to produce a concise, user-friendly conclusion using:
    - district, weather
    - the chat transcript
    - final routing labels (issue_type, sub_category, agent)
    
    Returns a dict with 'reason' and 'solution' keys
    """
    sub_category = final_json.get("sub_category", "Unknown")
    issue_type   = final_json.get("issue_type", "Other")
    agent        = final_json.get("agent", "default")

    transcript = _render_transcript(session.memory) if session.memory else ""
    district = session.district
    weather  = session.weather

    # Create LLM instance for summary generation
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model=os.getenv("OLLAMA_MODEL", "gemma3"), temperature=0.6)
    except:
        llm = None

    prompt = f"""
You are "SLT Resolution Summarizer". Write a concise, friendly conclusion for the customer.
Use ONLY the conversation and context; do not invent facts.

GOAL:
Provide TWO separate sections:

1. REASON (1-2 sentences): Explain the most likely cause in plain language based on what the user told us.
   - Be specific to their symptoms, timing, devices mentioned
   - Use simple, non-technical language
   
2. SOLUTION (2-3 bullet points): What our team will do next to help resolve this.
   - Keep it action-oriented and reassuring
   - No heavy jargon
   - Each point should be 1 short sentence

CONTEXT:
- District: {district}
- Weather: {weather}
- Issue type: {issue_type}
- Sub-category: {sub_category}
- Agent: {agent}
- Transcript:
{transcript}

RESPONSE FORMAT:
Output ONLY in this exact format (no extra text):
REASON: [Your 1-2 sentence explanation here]
SOLUTION: [Bullet point 1] | [Bullet point 2] | [Bullet point 3]

Use the pipe symbol | to separate solution bullet points.

RESPONSE RULES:
- Keep REASON under 40 words
- Keep each SOLUTION point under 15 words
- Be specific to what the user told us
- Output plain text only (no JSON, no markdown)
- Must start with "REASON:" and have "SOLUTION:" section
""".strip()

    try:
        if llm:
            result = llm.invoke(prompt)
            response_text = result.content if hasattr(result, 'content') else str(result)
            
            # Parse the response into reason and solution
            reason = ""
            solution = []
            
            if "REASON:" in response_text and "SOLUTION:" in response_text:
                parts = response_text.split("SOLUTION:")
                reason = parts[0].replace("REASON:", "").strip()
                solution_text = parts[1].strip()
                # Split by pipe or newline
                if "|" in solution_text:
                    solution = [s.strip() for s in solution_text.split("|") if s.strip()]
                else:
                    solution = [s.strip() for s in solution_text.split("\n") if s.strip() and not s.startswith("-")]
            else:
                # Fallback parsing
                reason = response_text[:200]  # First 200 chars as reason
                solution = ["Our technical team will investigate this issue", "We'll contact you with updates", "A resolution will be provided shortly"]
            
            return {
                "reason": reason,
                "solution": solution
            }
        
        # Fallback if LLM not available
        return {
            "reason": f"Based on your answers, this appears to be a {issue_type} issue with your {sub_category} service.",
            "solution": [
                "Our technical team will investigate the issue",
                "We'll run diagnostics on your service",
                "You'll receive an update within 24 hours"
            ]
        }
    except Exception as e:
        print(f"⚠️ Summary generation error: {e}")
        return {
            "reason": f"Based on your answers, this appears to be a {issue_type} issue with your {sub_category} service.",
            "solution": [
                "Our technical team will investigate the issue",
                "We'll run diagnostics on your service",
                "You'll receive an update within 24 hours"
            ]
        }

# -----------------------------
# API
# -----------------------------
app = FastAPI(title="SLT-CHATBOT", version="1.0.0")

# Serve static assets (CSS/JS/HTML)
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")

class InitRequest(BaseModel):
    phone: str

    # ✅ Updated to Pydantic V2 syntax
    @field_validator("phone")
    @classmethod
    def must_be_valid_landline(cls, v: str):
        digits = re.sub(r"\D", "", v or "")
        # Accept 7–10 digits after stripping +94/leading 0 (tweak if your dataset requires)
        if not re.fullmatch(r"\d{7,10}", digits):
            raise ValueError("Please enter a valid landline number (digits only).")
        return v

class ChatRequest(BaseModel):
    session_id: str
    message: Optional[str] = ""

@app.get("/", response_class=HTMLResponse)
def index():
    index_path = ROOT_DIR / "static" / "index.html"
    return FileResponse(index_path)

@app.post("/init")
def init(req: InitRequest):
    try:
        # Normalize and re-validate defensively (double-check on server)
        phone_norm = normalize_phone(req.phone)
        if (not phone_norm) or (not phone_norm.isdigit()) or (not (7 <= len(phone_norm) <= 10)):
            raise HTTPException(status_code=422, detail="Please enter a valid landline number (digits only).")

        # Predict district
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
            first_response = session.conversation({
                "input": f"Start asking questions to identify their telecom issue."
            })["response"]
            session.turns += 1
        except Exception as e:
            print(f"❌ Error generating first question: {e}")
            # Fallback to static question
            weather_lower = weather.lower()
            is_bad_weather = any(word in weather_lower for word in ["rain", "storm", "thunder", "heavy", "severe", "stormy", "windy"])
            if is_bad_weather:
                first_response = (
                    f"I can see it's {weather} in {district}, which often affects connectivity. "
                    f"Which service is having issues - WiFi, Internet, Landline, or Mobile?"
                )
            else:
                first_response = "Which service is having issues - WiFi, Internet, Landline, or Mobile?"

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
    start_pos = json_text.find("{")
    if start_pos >= 0:
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

    user_message = req.message or ""

    # If we're at turn 4, remind the model to return JSON next turn with the service type
    if session.turns == 4:
        user_message = (
            f"{user_message} [REMINDER: This is your 4th question. On your next response, you MUST return JSON "
            f"with the correct sub_category based on the service type the user mentioned earlier "
            f"(WiFi/Internet/Landline/Mobile). Do NOT return Unknown.]"
        )

    try:
        response = session.conversation({"input": user_message})["response"]
        session.turns += 1

        response_stripped = (response or "").strip()

        # Look for JSON in code blocks
        json_text = response_stripped
        if "```json" in response_stripped:
            start = response_stripped.find("```json") + 7
            end = response_stripped.find("```", start)
            if end > start:
                json_text = response_stripped[start:end].strip()
        elif response_stripped.startswith("```"):
            start = response_stripped.find("```") + 3
            end = response_stripped.find("```", start)
            if end > start:
                json_text = response_stripped[start:end].strip()

        if json_text.startswith("{"):
            try:
                final = _maybe_route_final(json_text)
                if final:
                    # NEW: produce readable summary too
                    summary = _summarize_conclusion(session, final)
                    SESSIONS.pop(req.session_id, None)  # End session
                    return {"final": final, "summary": summary}
            except Exception as e:
                print(f"⚠️ JSON parsing error: {e}")

        # Enforce max 5 questions
        if session.turns >= 5:
            try:
                final_prompt = (
                    'You must now return JSON with issue_type and sub_category. '
                    'Look back at the conversation - what service did the user mention (WiFi/Internet/Landline/Mobile)? '
                    'Return ONLY JSON in format: {"issue_type": "Technical", "sub_category": "WiFi"}. '
                    'sub_category MUST be one of: WiFi, Internet, Landline, or Mobile - NEVER Unknown.'
                )
                final_response = session.conversation({"input": final_prompt})["response"]

                final_stripped = (final_response or "").strip()
                final_json_text = final_stripped
                if "```json" in final_stripped:
                    start = final_stripped.find("```json") + 7
                    end = final_stripped.find("```", start)
                    if end > start:
                        final_json_text = final_stripped[start:end].strip()
                elif final_stripped.startswith("```"):
                    start = final_stripped.find("```") + 3
                    end = final_stripped.find("```", start)
                    if end > start:
                        final_json_text = final_stripped[start:end].strip()

                if final_json_text.startswith("{"):
                    final_result = _maybe_route_final(final_json_text)
                    if final_result and final_result.get("sub_category") and final_result.get("sub_category") != "Unknown":
                        summary = _summarize_conclusion(session, final_result)  # NEW
                        SESSIONS.pop(req.session_id, None)
                        return {"final": final_result, "summary": summary}
            except Exception as e:
                print(f"⚠️ Final JSON generation error: {e}")

            SESSIONS.pop(req.session_id, None)
            final_result = {"issue_type": "Other", "sub_category": "Unknown", "agent": "default"}
            summary = _summarize_conclusion(session, final_result)  # NEW
            return {"final": final_result, "summary": summary}

        return {"response": response}

    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        return {"response": "I'm having trouble connecting to my AI system. Please try again or contact support directly."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8083, reload=True)


