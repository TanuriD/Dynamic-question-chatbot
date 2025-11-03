# app_fastapi.py
import re
import joblib
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd

# Model path
MODEL_PATH = Path("district_knn_model.joblib")

# Load model
if not MODEL_PATH.exists():
    raise RuntimeError("❌ Model file not found. Run train_model.py first.")
model = joblib.load(MODEL_PATH)
print(f"✅ Loaded KNN model from {MODEL_PATH}")

# FastAPI app
app = FastAPI(
    title="District Prediction API",
    description="Predicts the Sri Lankan district based on the phone number.",
    version="1.0.0"
)

class PhoneInput(BaseModel):
    phone: str

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

@app.get("/")
def root():
    return {"service": "district-predictor", "model": "KNN"}

@app.post("/predict_district")
def predict_district(data: PhoneInput):
    phone = data.phone
    phone_norm = normalize_phone(phone)
    features = phone_to_features(phone_norm)

    # <-- FIX: convert to 2-D DataFrame so the sklearn pipeline can transform it -->
    try:
        X = pd.DataFrame([features])   # one-row DataFrame
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare features: {e}")

    try:
        prediction = model.predict(X)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return {
        "input_phone": phone,
        "normalized_phone": phone_norm,
        "district": prediction
    }
