# SLT IVR Chatbot System

An intelligent chatbot complaint handling system that automatically identifies customer districts from phone numbers and uses real-time data factors (weather, billing, maintenance) to identify customer issues and route them to appropriate agents with solutions.

## Features

- **Phone Number to District Mapping**: Automatically identifies customer district from phone number using CSV mapping
- **District-Based Issue Detection**: Automatically detects weather conditions, billing issues, and maintenance activities based on district
- **Chatbot Interface**: Modern, conversational chatbot UI with chat bubbles
- **AI-Powered Question Selection**: Uses Ollama LLM for intelligent question routing (optional, falls back to rule-based if unavailable)
- **Intelligent Question Routing**: Asks the most relevant questions (max 5) based on detected factors and customer responses
- **Yes/No Responses**: Simple interaction - customers only need to answer yes or no
- **Issue Categorization**: Automatically categorizes issues into internal/external factors using AI
- **Agent Routing**: Routes to appropriate agents (Billing, Network Support, Technical Support, etc.)
- **Solution Provision**: Provides specific solutions based on identified issues

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Install and setup Ollama for AI-powered question selection:
```bash
# Install Ollama from https://ollama.ai
# Then pull a model (recommended: llama3.2 or mistral)
ollama pull llama3.2
```

The system will automatically use Ollama if available, or fall back to rule-based selection if not.

## Running the System

1. Start the Flask backend server:
```bash
python app.py
```

The server will run on `http://localhost:5000`

2. Open `index.html` in your web browser (or use a local server)

## How to Use

### 1. Start a Chat Session

1. Enter your phone number in the chat input (e.g., `011861547`)
2. Click "Start Chat" or press Enter
3. The system will:
   - Identify your district from the phone number
   - Detect any issues in your area (weather, billing, maintenance)
   - Start asking relevant questions

### 2. Answer Questions

- Answer each question by clicking "Yes" or "No"
- The system will ask up to 5 questions
- Questions are dynamically selected based on:
  - Your district's real-time factors
  - Your previous answers
  - Issue category detection

### 3. View Solution

After answering questions (or reaching the 5-question limit), the system will:
- Categorize the issue
- Identify the specific issue type
- Route to the appropriate agent
- Provide a solution with description

## District Mapping

The system uses `district_mapping.csv` to map phone numbers to districts. The CSV file contains:
- Phone numbers (with area codes)
- Corresponding districts

### District-Specific Issues Configuration

District-specific issues are configured in `app.py` in the `district_issues_config` dictionary. You can configure:
- Weather conditions (normal, rainy, stormy)
- Billing issues (outstanding payments)
- Maintenance activities (active maintenance)

Example configuration:
```python
district_issues_config = {
    "Colombo": {"weather": "rainy", "billing": True, "maintenance": False},
    "Gampaha": {"weather": "normal", "billing": False, "maintenance": True},
    "Matara": {"weather": "stormy", "billing": False, "maintenance": False},
    # ... more districts
}
```

## System Architecture

### Backend (Flask API)

- `/api/start-session`: Start a new complaint session with phone number
- `/api/answer-question`: Answer a question and get the next one
- `/api/lookup-district`: Lookup district from phone number (for testing)
- `/api/test-weather`: Test weather API for a specific district
- `/api/ollama-status`: Check Ollama service status and availability
- `/api/update-factors`: Update real-time factors (for testing)
- `/api/get-factors`: Get current real-time factors

### Phone Number to District Mapping

The system:
1. Loads phone-to-district mapping from `district_mapping.csv`
2. Matches incoming phone numbers to districts
3. Retrieves district-specific issues
4. Configures real-time factors for that district

### Question Selection Algorithm

The system uses an intelligent question selection algorithm with two modes:

**AI-Powered Mode (Ollama)** - When Ollama is available:
1. Uses LLM to analyze all customer responses and context
2. Intelligently selects the most relevant next question from the entire question bank
3. Considers detected factors, previous answers, and current category
4. Provides more accurate issue categorization

**Rule-Based Mode (Fallback)** - When Ollama is unavailable:
1. Analyzes district-specific real-time factors (weather, billing, maintenance)
2. Selects initial questions from relevant categories
3. Adapts based on customer responses using predefined rules
4. Switches categories dynamically (e.g., from general to network if network issues are detected)
5. Limits to maximum 5 questions

The system automatically detects Ollama availability and uses the best method available.

### Issue Categorization

Issues are categorized into:
- **Internal Factors**: Billing, Network Connectivity, Service Activation, Equipment, Premise Setup
- **External Factors**: Weather, Power, Area Infrastructure, Technical Interference

### Agent Routing

Based on the categorized issue, customers are routed to:
- Billing Agent
- Network Support Agent
- Technical Support Agent
- Network Operations Agent

## Example Scenarios

### Scenario 1: Colombo Customer (Rainy Weather + Billing Issues)
1. Customer enters phone: `011861547`
2. System identifies: Colombo district
3. System detects: Rainy weather + Billing issues
4. System asks: Weather and billing-related questions
5. Identifies issue and routes to appropriate agent

### Scenario 2: Gampaha Customer (Maintenance Active)
1. Customer enters phone: `033730049`
2. System identifies: Gampaha district
3. System detects: Active maintenance
4. System asks: Maintenance-related questions
5. Provides maintenance information and solution

### Scenario 3: Matara Customer (Stormy Weather)
1. Customer enters phone: `041760889`
2. System identifies: Matara district
3. System detects: Stormy weather
4. System asks: Weather-related questions
5. Routes to Technical Support with weather-specific solution

## File Structure

```
SLT IVR/
├── app.py                 # Flask backend API
├── index.html            # Chatbot frontend UI
├── styles.css            # UI styling
├── script.js             # Frontend JavaScript
├── questionbank.json     # Question bank database
├── district_mapping.csv  # Phone to district mapping
├── requirements.txt      # Python dependencies
└── README.md             # Documentation
```

## Testing

### Test Phone Numbers

You can use any phone number from `district_mapping.csv`:
- `011861547` → Colombo
- `021117691` → Jaffna
- `033730049` → Gampaha
- `041760889` → Matara
- `081981727` → Kandy

### API Testing

Test district lookup:
```bash
curl -X POST http://localhost:5000/api/lookup-district \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "011861547"}'
```

## Future Enhancements

- Integration with real weather APIs
- Integration with billing system APIs
- Integration with network monitoring systems
- Machine learning for better question selection
- Multi-language support
- Voice interface integration
- Real-time district issue updates from external systems

## Ollama Configuration

The system can use Ollama for AI-powered question selection. To configure:

1. **Enable/Disable Ollama**: Edit `app.py` and set `OLLAMA_ENABLED = True/False`
2. **Change Model**: Edit `OLLAMA_MODEL` in `app.py` (default: "llama3.2")
3. **Change URL**: Edit `OLLAMA_BASE_URL` if Ollama is running on a different port

### Recommended Models:
- `llama3.2` - Fast and efficient (recommended)
- `mistral` - Good balance of speed and quality
- `llama3` - More powerful but slower

### Check Ollama Status:
```bash
curl http://localhost:5000/api/ollama-status
```

The system automatically falls back to rule-based selection if Ollama is unavailable.

## OpenWeather API Integration

The system now uses **real-time weather data** from OpenWeather API!

### Features:
- ✅ Fetches real weather conditions for each district
- ✅ Maps weather to categories: normal, rainy, stormy
- ✅ Caching system (5-minute cache) to reduce API calls
- ✅ Automatic fallback if API fails

### Weather Mapping:
- **Rainy**: Light to moderate rain, drizzle
- **Stormy**: Heavy rain, thunderstorms, storms
- **Normal**: Clear, cloudy, or other conditions

### Configuration:
The OpenWeather API key is configured in `app.py`:
```python
OPENWEATHER_API_KEY = "f72d16875c109d22d0c9119ed9d5c288"
USE_REAL_WEATHER = True  # Set to False to use simulated weather
```

### Test Weather API:
```bash
curl -X POST http://localhost:5000/api/test-weather \
  -H "Content-Type: application/json" \
  -d '{"district": "Colombo"}'
```

## Notes

- Weather data is fetched in real-time from OpenWeather API
- Billing and maintenance issues are currently simulated (can be integrated with real APIs)
- The system is designed to handle up to 5 questions per session
- All questions require yes/no answers for simplicity
- Solutions are pre-defined but can be customized based on specific requirements
- Phone numbers are matched exactly first, then by prefix if exact match fails
- Ollama integration is optional - the system works perfectly without it using rule-based logic
