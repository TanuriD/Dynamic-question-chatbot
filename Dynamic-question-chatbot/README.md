# SLT-CHATBOT

A complete, integrated AI system for dynamic question chatbot that predicts district from landline numbers, fetches weather data, and intelligently routes customer issues to appropriate agents.

## Features

- **District Prediction**: Automatically detects district from landline number using trained KNN model
- **Weather Integration**: Fetches real-time weather data for the detected district
- **Proactive Chatbot**: Starts asking questions immediately - no waiting for greetings
- **Dynamic Conversation**: Fully dynamic using Ollama LLM (like chatbot_member3.py template)
- **Weather-Aware Intelligence**: Ollama receives weather context for intelligent questioning
- **Weather-Aware Routing**: Automatically routes weather-related issues to weather agent
- **Modern UI**: Beautiful, responsive web interface
- **Self-Contained**: All dependencies included in this folder

### 🌤️ Weather-Aware Features

- **Contextual First Questions**: 
  - If raining/stormy: "I can see it's raining in Colombo, which often affects connectivity. Which service is having issues?"
  - If good weather: "Which service is having issues - WiFi, Internet, Landline, or Mobile?"

- **Smart Service Detection**: Automatically detects service type from user responses

- **Weather-Based Routing**: 
  - Bad weather → Weather agent
  - Good weather → Technical/default agent

## How It Works

1. **Input**: User enters landline number
2. **District Detection**: System predicts district using trained ML model
3. **Weather Lookup**: Fetches current weather for that district
4. **Smart Chat**: Asks up to 5 intelligent questions to identify the issue
5. **Routing**: Routes to weather agent (if weather-related) or default agent

## Quick Start

### Prerequisites
- Python 3.9+
- Ollama installed (optional - has smart fallback)

### Installation

1. **Clone this repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set OpenWeather API key** (optional):
   ```bash
   export OPENWEATHER_API_KEY=your_api_key
   ```
4. **Start the server**:
   ```bash
   python app.py
   ```
5. **Open browser**: `http://localhost:8081`

## Files Included

- `app.py` - Main FastAPI application
- `chatbot_core.py` - LangChain + Ollama integration
- `district_knn_model.joblib` - Trained district prediction model
- `district_mapping.csv` - Training data for district prediction
- `train_model.py` - Enhanced model training with comprehensive evaluation
- `requirements.txt` - Python dependencies
- `test_system.py` - Test script
- `README.md` - This file

## Usage

1. Enter a landline number (e.g., 011861547)
2. System detects district and weather
3. Chat with the intelligent assistant
4. Get routed to appropriate support agent

## Retraining the Model

To retrain the district prediction model with enhanced evaluation:

```bash
python train_model.py
```

This will generate:
- **Comprehensive evaluation report** with train/test accuracy
- **Classification report** with precision, recall, F1-score
- **Confusion matrix** visualization (saved as PNG)
- **Evaluation metrics CSV** file
- **Overfitting analysis**

## Notes

- Uses Ollama with `llama3` model for intelligent conversation
- Falls back to rule-based system if Ollama unavailable
- Automatically detects weather-related issues
- Maximum 5 questions before routing
- Modern, responsive UI with chat bubbles

