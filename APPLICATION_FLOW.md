# SLT IVR Application Flow - Complete Documentation

## Overview
This is an intelligent IVR (Interactive Voice Response) chatbot system for SLT (Sri Lanka Telecom) that helps identify customer issues through a conversational interface and routes them to appropriate support agents.

---

## 1. Application Initialization

### 1.1 Server Startup (`app.py`)
```
1. Flask application starts on port 5007
2. CORS enabled for API endpoints
3. ML model loading (optional - answer classifier)
4. Question bank loaded from questionbank.json
5. Global session storage initialized (in-memory dictionary)
```

**Key Components Loaded:**
- Question bank structure with categories:
  - Identification questions
  - Internal factors (network, billing, activation, equipment, premise)
  - External factors (weather, power, infrastructure)
- District mapping CSV files
- Weather API configuration (OpenWeatherMap)

---

## 2. User Interface Initialization

### 2.1 Frontend Load (`index.html` + `script.js`)
```
1. User opens index.html in browser
2. Chatbot interface displays welcome message
3. Phone input field is shown
4. User enters phone number
5. User clicks "Start Chat" or presses Enter
```

**Initial State:**
- Chat status: "Ready"
- Question count: 0/5
- Phone input area visible
- Answer buttons hidden

---

## 3. Session Start Flow

### 3.1 Frontend Request (`script.js` → `startChat()`)
```javascript
POST /api/start-session
Body: { "phone_number": "011861547" }
```

### 3.2 Backend Processing (`app.py` → `start_session()`)

#### Step 1: District Identification
```
1. Read issues_with_issue_type_column.csv
   - Look for phone number match
   - Extract district and issue type
   
2. If not found, read district_mapping.csv
   - Match phone number exactly
   - Extract district
   
3. If district not found → Return error 400
```

#### Step 2: Weather Detection
```
1. Map district to city name (DISTRICT_TO_CITY mapping)
2. Call OpenWeatherMap API:
   GET https://api.openweathermap.org/data/2.5/weather?q={city},LK&appid={API_KEY}
3. Extract temperature and weather description
4. Format: "Clear (28°C)" or "Rainy (25°C)" or "normal"
```

#### Step 3: Issue Type Detection
```
1. Read issues_with_issue_type_column.csv again
2. Find all issues for this phone number:
   - Main issue type from "Issue Type" column
   - Secondary issues from other columns:
     * Network Connectivity
     * Billing & Account
     * Service Activation
     * Equipment & Infrastructure
     * Premise Setup
3. Map issue types to question bank sections:
   - "network issue" → "network_connectivity"
   - "billing issue" → "billing_account"
   - "activation issue" → "service_activation"
   - "equipment issue" → "equipment_infrastructure"
   - "premise issue" → "premise_setup"
```

#### Step 4: Question Queue Building
```
1. For each identified issue type:
   - Load ALL questions from corresponding section
   - Add to session_questions queue
   
2. Limit total questions to maximum 5:
   - Strategy: Give each section at least 1 question
   - Distribute remaining slots round-robin
   
3. Fallback: If no issues found, use identification questions
```

#### Step 5: Session Creation
```python
session = {
    "phone_number": "011861547",
    "district": "Colombo",
    "weather": "Rainy (25°C)",
    "asked_questions": [],
    "responses": {},
    "question_queue": [
        {
            "section": "network_connectivity",
            "questions": [q1, q2, q3]
        },
        {
            "section": "billing_account",
            "questions": [q1, q2]
        }
    ],
    "current_section": 0,
    "current_question": 0,
    "current_section_name": "network_connectivity",
    "issue_sections": ["network_connectivity", "billing_account"],
    "main_issue_type": "network issue",
    "is_random_questions_mode": False,
    "confirmed_section": None,
    "confidence_level": 0,  # 0=low, 1=medium, 2=high
    "yes_count": 0
}
```

#### Step 6: Response to Frontend
```json
{
    "session_id": "session_1234567890",
    "district": "Colombo",
    "phone_number": "011861547",
    "weather": "Rainy (25°C)",
    "initial_question": {
        "id": "NET_01",
        "question": "Are you currently experiencing slow internet or buffering?",
        "type": "yes_no"
    },
    "issue_type": "network issue",
    "welcome_message": "Hello! I've identified you're calling from Colombo district. Current weather: Rainy (25°C). Let me ask you a few questions..."
}
```

### 3.3 Frontend Display (`script.js`)
```
1. Display welcome message
2. Display district information
3. Display first question
4. Show Yes/No buttons
5. Hide phone input area
6. Update progress: 1/5
7. Update session info in admin panel
```

---

## 4. Question-Answer Loop

### 4.1 User Answers Question
```
User clicks "Yes" or "No" button
```

### 4.2 Frontend Request (`script.js` → `answerQuestion()`)
```javascript
POST /api/answer-question
Body: {
    "session_id": "session_1234567890",
    "answer": "yes",
    "question_id": "NET_01"
}
```

### 4.3 Backend Processing (`app.py` → `answer_question()`)

#### Step 1: Validate Request
```
- Check session exists
- Save answer to session['responses'][question_id]
- Get current question queue and indices
```

#### Step 2: Check Termination Conditions
```
1. Max questions reached (5)?
   → Terminate and route to agent
   
2. High confidence (2+ YES answers)?
   → Terminate early with high confidence
```

#### Step 3: Routing Logic Based on Answer

**If Answer = "YES":**

```
1. Update confidence:
   - yes_count += 1
   - If yes_count >= 2: confidence_level = 2 (high)
   - If yes_count == 1: confidence_level = 1 (medium)
   
2. Confirm section:
   - confirmed_section = current_section_name
   
3. Check if random questions mode:
   - If YES → Terminate immediately (issue found)
   
4. Find next question:
   - If first question (Q1) → Skip Q2, go to Q3
   - Otherwise → Find next unasked question in same section
   
5. Check termination:
   - If high confidence (2+ YES) → Terminate early
   - If max questions → Terminate
   - Otherwise → Continue with next question
```

**If Answer = "NO":**

```
1. Check if first question of section:
   
   a) If YES (first question):
      - Move to NEXT issue type section
      - section_idx += 1
      - Ask first question from next section
      
      - If no more sections:
        → Switch to random questions mode
        → Ask random network questions
        
   b) If NO (follow-up question):
      - Continue with more questions from SAME section
      - Find next unasked question
      - If no more questions → Terminate
```

**If Answer = Invalid:**
```
→ Terminate with invalid response error
```

#### Step 4: Response Generation

**If Continuing:**
```json
{
    "next_question": {
        "id": "NET_03",
        "question": "Is the LOS or red light blinking on your router/ONT?",
        "type": "yes_no"
    },
    "question_number": 2,
    "completed": false
}
```

**If Terminating:**
```json
{
    "completed": true,
    "category": "confirmed_issue",
    "issue_type": "network_connectivity",
    "solution": {
        "agent": "Network Agent",
        "priority": "high",
        "solution": "Issue confirmed with high confidence. Routing to specialized agent for resolution."
    }
}
```

### 4.4 Frontend Display Update

**If Continuing:**
```
1. Display user's answer in chat
2. Display next question
3. Update progress bar (question_number/5)
4. Re-enable Yes/No buttons
```

**If Terminating:**
```
1. Display user's answer
2. Hide answer buttons
3. Display solution card with:
   - Category
   - Issue Type
   - Assigned Agent
   - Priority badge
   - Solution description
4. Update chat status to "Resolved"
```

---

## 5. Routing Logic Details

### 5.1 Section Navigation
```
Initial Queue: [Section1, Section2, Section3]

Flow:
1. Ask Q1 from Section1
   - YES → Continue Section1 (skip Q2, ask Q3)
   - NO → Move to Section2, ask Q1
   
2. In Section1:
   - YES to Q3 → Continue Section1
   - NO to Q3 → Continue Section1 (more questions)
   
3. If NO to first question of any section:
   - Move to next section
   - If last section → Random questions mode
```

### 5.2 Confidence Levels
```
confidence_level = 0 (Low):
   - No YES answers yet
   - All NOs or first question
   
confidence_level = 1 (Medium):
   - Exactly 1 YES answer
   - Some confidence in issue type
   
confidence_level = 2 (High):
   - 2+ YES answers
   - High confidence in issue type
   - Can terminate early
```

### 5.3 Agent Routing
```python
agent_map = {
    'network_connectivity': 'Network Agent',
    'billing_account': 'Billing Agent',
    'service_activation': 'Activation Agent',
    'equipment_infrastructure': 'Equipment Agent',
    'premise_setup': 'Premise Agent',
}

# Routing priority:
1. Use confirmed_section if available
2. Otherwise use current_section_name
3. If no confidence → 'General Support Agent'
```

### 5.4 Termination Scenarios

**Scenario 1: High Confidence (Early Termination)**
```
- 2+ YES answers in same section
- Questions asked < 5
- Terminate immediately
- Route to specialized agent
- Priority: High
```

**Scenario 2: Max Questions Reached**
```
- Exactly 5 questions asked
- Terminate regardless of confidence
- Route based on confirmed_section or current_section
- Priority: High if confidence >= 1, else Medium
```

**Scenario 3: All Sections Exhausted**
```
- NO to first question of all sections
- Switch to random questions mode
- Ask random network questions
- If YES → Terminate immediately
- If NO → Continue until max questions
```

**Scenario 4: No More Questions in Section**
```
- All questions in current section asked
- Terminate with current section info
- Route to appropriate agent
```

---

## 6. Data Flow Diagram

```
┌─────────────┐
│   User      │
│  Browser    │
└──────┬──────┘
       │
       │ 1. Enter Phone Number
       ▼
┌─────────────────────┐
│   Frontend (HTML)   │
│   script.js         │
└──────┬──────────────┘
       │
       │ 2. POST /api/start-session
       ▼
┌─────────────────────┐
│   Backend (Flask)   │
│   app.py            │
└──────┬──────────────┘
       │
       ├─→ 3a. Read CSV files
       │   - district_mapping.csv
       │   - issues_with_issue_type_column.csv
       │
       ├─→ 3b. Call Weather API
       │   - OpenWeatherMap
       │
       ├─→ 3c. Build Question Queue
       │   - Map issues to sections
       │   - Load questions
       │   - Limit to 5 questions
       │
       └─→ 3d. Create Session
           - Store in sessions dict
           - Return session_id + first question
       
       │
       │ 4. Return Response
       ▼
┌─────────────────────┐
│   Frontend          │
│   Display Question  │
└──────┬──────────────┘
       │
       │ 5. User Answers (Yes/No)
       ▼
┌─────────────────────┐
│   Frontend          │
│   POST /api/answer  │
└──────┬──────────────┘
       │
       │ 6. Process Answer
       ▼
┌─────────────────────┐
│   Backend           │
│   Routing Logic     │
└──────┬──────────────┘
       │
       ├─→ YES: Update confidence, continue section
       ├─→ NO (first Q): Move to next section
       └─→ NO (follow-up): Continue same section
       
       │
       │ 7. Return Next Question or Solution
       ▼
┌─────────────────────┐
│   Frontend          │
│   Display Result    │
└─────────────────────┘
```

---

## 7. Key Files and Their Roles

### Backend Files
- **app.py**: Main Flask application
  - Session management
  - Question routing logic
  - API endpoints
  - Weather integration
  - CSV data reading

### Frontend Files
- **index.html**: UI structure
  - Chat interface
  - Input areas
  - Admin panel
- **script.js**: Frontend logic
  - API calls
  - UI updates
  - Message display
- **styles.css**: Styling

### Data Files
- **questionbank.json**: All questions organized by category
- **district_mapping.csv**: Phone number → District mapping
- **issues_with_issue_type_column.csv**: Phone number → Issues mapping
- **models/answer_classifier.pkl**: ML model (optional, not used in main flow)

---

## 8. Example Complete Flow

### Example: Colombo Customer with Network Issue

```
1. User enters: 011861547
   ↓
2. Backend identifies:
   - District: Colombo
   - Weather: Rainy (25°C)
   - Issues: Network Connectivity, Billing & Account
   ↓
3. Question Queue Built:
   - Section 1: network_connectivity (3 questions)
   - Section 2: billing_account (2 questions)
   ↓
4. First Question:
   "Are you currently experiencing slow internet or buffering?"
   ↓
5. User: YES
   - confidence_level = 1 (medium)
   - confirmed_section = network_connectivity
   - Skip Q2, ask Q3
   ↓
6. Second Question:
   "Is the LOS or red light blinking on your router/ONT?"
   ↓
7. User: YES
   - confidence_level = 2 (high)
   - Terminate early (high confidence)
   ↓
8. Solution Displayed:
   - Category: Confirmed Issue
   - Issue Type: Network Connectivity
   - Agent: Network Agent
   - Priority: High
   - Solution: "Issue confirmed with high confidence. Routing to specialized agent..."
```

---

## 9. Error Handling

### District Not Found
```
→ Return 400 error
→ Frontend displays error message
→ User can try different phone number
```

### Weather API Failure
```
→ Fallback to "normal" weather
→ Continue with session
→ Log error to console
```

### Session Not Found
```
→ Return 400 error
→ Frontend displays error
→ User needs to start new session
```

### Invalid Answer
```
→ Treat as invalid response
→ Terminate session
→ Route to General Support Agent
```

---

## 10. Session State Management

### Session Lifecycle
```
1. Created: /api/start-session
2. Updated: /api/answer-question (each answer)
3. Terminated: When completed or error
4. Stored: In-memory dictionary (sessions = {})
```

### Session Data Structure
```python
{
    "phone_number": str,
    "district": str,
    "weather": str,
    "asked_questions": list,
    "responses": dict,
    "question_queue": list,
    "current_section": int,
    "current_question": int,
    "current_section_name": str,
    "issue_sections": list,
    "main_issue_type": str,
    "is_random_questions_mode": bool,
    "confirmed_section": str | None,
    "confidence_level": int,
    "yes_count": int
}
```

---

## Summary

The application flow follows this pattern:
1. **Start** → User enters phone number
2. **Identify** → System identifies district, weather, and issues
3. **Question** → System asks relevant questions (max 5)
4. **Route** → Based on answers, system routes to appropriate section
5. **Confirm** → System builds confidence through YES answers
6. **Terminate** → When confident or max questions reached
7. **Resolve** → Display solution and route to appropriate agent

The system is designed to be intelligent, adaptive, and efficient, using real-time data (weather) and historical data (CSV files) to provide the best customer experience.

