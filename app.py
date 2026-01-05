import os
import joblib
import json
import csv
import random
import re
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime


app = Flask(__name__, static_folder='.')
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins for API

# ML model loading (only answer classifier - optional, has endpoint but not used in main flow)
models_dir = os.path.join(os.path.dirname(__file__), "models")
answer_model = None
try:
    answer_model = joblib.load(os.path.join(models_dir, "answer_classifier.pkl"))
except Exception as e:
    print(f"Warning: Could not load answer classifier model: {e}")

@app.route("/classify-answer", methods=["POST"])
def classify_answer():
    """Optional endpoint for answer classification (not used in main flow)"""
    if answer_model is None:
        return jsonify({"error": "Answer classifier model not available"}), 503
    try:
        reply = request.json["reply"]
        label = answer_model.predict([reply])[0]
        return jsonify({"answer_class": label})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
with open('questionbank.json', 'r') as f:
    question_bank_raw = json.load(f)
if "questions" in question_bank_raw:
    questions_data = question_bank_raw["questions"]
    external_factors_data = questions_data.get("external_factors", [])
    if isinstance(external_factors_data, list):
        external_factors_dict = {
            "weather_climate": external_factors_data,
            "power_electricity": [],
            "area_infrastructure": [],
            "technical_interference": []
        }
    else:
        external_factors_dict = external_factors_data
    question_bank = {
        "complaint_question_bank": {
            "identification": questions_data.get("identification", []),
            "internal_factors": {
                "network_connectivity": questions_data.get("network_connectivity", []),
                "billing_account": questions_data.get("billing_account", []),
                "service_activation": questions_data.get("service_activation", []),
                "equipment_infrastructure": questions_data.get("equipment_infrastructure", []),
                "premise_setup": questions_data.get("premise_setup", [])
            },
            "external_factors": external_factors_dict,
            "nature_of_complaint": questions_data.get("nature_of_complaint", []),
            "advanced_diagnostics": questions_data.get("advanced_diagnostics", [])
        }
    }
else:
    question_bank = question_bank_raw

# ...existing code for ML endpoints and question bank loading...

# Global session storage (in production, use Redis or database)
sessions = {}


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/'):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory('.', path)

# ...existing code for static file serving...



# --- ML-based session/question logic with district and weather detection ---
def get_district_from_phone(phone_number):
    # Read district_mapping.csv and match full phone number
    try:
        with open('district_mapping.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row.get('phone') or row.get('Phone')
                district = row.get('district') or row.get('District')
                if phone and district and phone_number == phone:
                    return district
    except Exception as e:
        print(f"Error reading district_mapping.csv: {e}")
    return "Unknown"


# --- Weather API integration ---
OPENWEATHERMAP_API_KEY = "f72d16875c109d22d0c9119ed9d5c288"
DISTRICT_TO_CITY = {
    'Colombo': 'Colombo',
    'Jaffna': 'Jaffna',
    'Vavuniya': 'Vavuniya',
    # Add more mappings as needed
}

def get_weather_for_district(district):
    city = DISTRICT_TO_CITY.get(district, district)
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city},LK&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            temp = data.get('main', {}).get('temp')
            desc = data.get('weather', [{}])[0].get('description', '').title()
            if temp is not None and desc:
                return f"{desc} ({temp}°C)"
            elif temp is not None:
                return f"{temp}°C"
            elif desc:
                return desc
    except Exception as e:
        print(f"Error fetching weather for {district}: {e}")
    return "normal"


@app.route('/api/start-session', methods=['POST'])

def start_session():
    data = request.json
    phone_number = data.get('phone_number', '')
    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400

    # Try issues_with_issue_type_column.csv first
    district = None
    issue_type = None
    try:
        with open('issues_with_issue_type_column.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Number'] == phone_number:
                    district = row['District']
                    issue_type = row.get('Issue Type', None)
                    break
    except Exception as e:
        print(f"CSV read error: {e}")

    # If not found, try district_mapping.csv
    if not district:
        try:
            with open('district_mapping.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    phone = row.get('phone') or row.get('Phone')
                    dist = row.get('district') or row.get('District')
                    if phone and dist and phone_number == phone:
                        district = dist
                        break
        except Exception as e:
            print(f"Error reading district_mapping.csv: {e}")

    if not district:
        return jsonify({"error": "Could not identify district from phone number"}), 400

    # Get weather for district (real-time)
    weather = get_weather_for_district(district)

    # Dynamic initial question selection based on main issue type
    qb = question_bank.get("complaint_question_bank", question_bank)
    # Build session-specific question queue: main issue, other issues, fallback
    # Find all issues for this number from CSV
    issues_for_number = []
    try:
        with open('issues_with_issue_type_column.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Number'] == phone_number:
                    # Main issue first
                    issue_type_val = row.get('Issue Type', '').strip() if row.get('Issue Type') else ''
                    if issue_type_val:
                        issues_for_number.append(issue_type_val)
                    
                    # Check other columns for secondary issues
                    # These columns represent issue types, so if they have a value, add the column name
                    for col in ['Network Connectivity', 'Billing & Account', 'Service Activation', 'Equipment & Infrastructure', 'Premise Setup']:
                        col_value = row.get(col, '').strip() if row.get(col) else ''
                        if col_value:  # If column has any value, it means customer has this issue type
                            # Add the column name (issue type), not the value
                            issues_for_number.append(col)
                    print(f"DEBUG CSV: phone={phone_number}, issues_for_number={issues_for_number}, row={dict(row)}")
                    break
    except Exception as e:
        print(f"CSV read error: {e}")

    # Map issues to question bank sections
    issue_type_map = {
        'network issue': 'network_connectivity',
        'billing issue': 'billing_account',
        'activation issue': 'service_activation',
        'equipment issue': 'equipment_infrastructure',
        'premise issue': 'premise_setup',
        'Network Connectivity': 'network_connectivity',
        'Billing & Account': 'billing_account',
        'Service Activation': 'service_activation',
        'Equipment & Infrastructure': 'equipment_infrastructure',
        'Premise Setup': 'premise_setup',
    }
    question_sections = []
    for issue in issues_for_number:
        issue_clean = issue.strip().lower()
        mapped = False
        for key, value in issue_type_map.items():
            key_clean = key.strip().lower()
            # Try exact match first, then substring match
            if key_clean == issue_clean or key_clean in issue_clean or issue_clean in key_clean:
                question_sections.append(value)
                print(f"DEBUG mapping: issue='{issue}' → matched key='{key}' → section='{value}'")
                mapped = True
                break
        if not mapped:
            print(f"DEBUG mapping: issue='{issue}' → NO MATCH FOUND")
    # Remove duplicates, keep order
    question_sections = list(dict.fromkeys(question_sections))
    print(f"DEBUG mapping result: question_sections={question_sections}")
    # Always fallback to network questions if all denied
    fallback_section = 'network_connectivity'
    # Build question queue: store as list of (section, questions)
    # Load ALL questions from each section, not just 2
    session_questions = []
    for section in question_sections:
        qs = qb["internal_factors"].get(section, [])  # Get ALL questions, not just 2
        session_questions.append({"section": section, "questions": [q if isinstance(q, dict) else {"question": q, "id": str(q)} for q in qs]})
    
    # Debug: Print queue info
    print(f"DEBUG start_session: phone={phone_number}, issues_for_number={issues_for_number}, question_sections={question_sections}, session_questions sections={[s['section'] for s in session_questions]}")
    # Fallback: if no questions, use identification
    if not session_questions:
        session_questions = [{"section": "identification", "questions": [q if isinstance(q, dict) else {"question": q, "id": str(q)} for q in qb.get("identification", [])[:2]]}]
    # Limit to max 5 questions total, but ensure we include at least 1 question from each section
    total_qs = sum(len(s["questions"]) for s in session_questions)
    if total_qs > 5:
        # Strategy: Give each section at least 1 question, then distribute remaining
        new_queue = []
        sections_count = len(session_questions)
        remaining_slots = 5
        
        # First pass: Give each section 1 question (if available)
        for s in session_questions:
            if remaining_slots > 0 and len(s["questions"]) > 0:
                new_queue.append({"section": s["section"], "questions": [s["questions"][0]]})
                remaining_slots -= 1
        
        # Second pass: Distribute remaining slots
        if remaining_slots > 0:
            section_idx = 0
            while remaining_slots > 0 and section_idx < len(session_questions):
                s = session_questions[section_idx]
                current_count = len(new_queue[section_idx]["questions"])
                if current_count < len(s["questions"]):
                    # Add one more question from this section
                    new_queue[section_idx]["questions"].append(s["questions"][current_count])
                    remaining_slots -= 1
                section_idx = (section_idx + 1) % len(session_questions)  # Round-robin
        
        session_questions = new_queue
        sections_info = [f"{s['section']}({len(s['questions'])})" for s in session_questions]
        print(f"DEBUG queue limit: Limited to {sum(len(s['questions']) for s in session_questions)} questions across {len(session_questions)} sections: {sections_info}")

    # If not found, try district_mapping.csv
    if not district:
        try:
            with open('district_mapping.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    phone = row.get('phone') or row.get('Phone')
                    dist = row.get('district') or row.get('District')
                    if phone and dist and phone_number == phone:
                        district = dist
                        break
        except Exception as e:
            print(f"Error reading district_mapping.csv: {e}")

    if not district:
        return jsonify({"error": "Could not identify district from phone number"}), 400

    # Get weather for district (real-time)
    weather = get_weather_for_district(district)

    # Dynamic initial question selection based on main issue type
    qb = question_bank.get("complaint_question_bank", question_bank)
    initial_question = None
    # Try to select a question related to the main issue type
    if issue_type:
        # Map common issue types to question bank sections
        issue_type_map = {
            'network issue': 'network_connectivity',
            'billing issue': 'billing_account',
            'activation issue': 'service_activation',
            'equipment issue': 'equipment_infrastructure',
            'premise issue': 'premise_setup',
        }
        section_key = None
        for key, value in issue_type_map.items():
            if key in issue_type.lower():
                section_key = value
                break
        found = False
        # Check mapped section first
        if section_key and section_key in qb.get("internal_factors", {}):
            for q in qb["internal_factors"][section_key]:
                if isinstance(q, dict):
                    initial_question = q.get('question')
                else:
                    initial_question = q
                found = True
                break
        # If not found, fallback to previous logic
        if not found:
            for section, questions in qb.get("internal_factors", {}).items():
                if section.lower().replace('_', ' ') in issue_type.lower():
                    for q in questions:
                        if isinstance(q, dict):
                            initial_question = q.get('question')
                        else:
                            initial_question = q
                        found = True
                        break
                if found:
                    break
        # If still not found, check nature_of_complaint
        if not found:
            for q in qb.get("nature_of_complaint", []):
                if isinstance(q, dict):
                    if issue_type.lower() in q.get('question', '').lower():
                        initial_question = q.get('question')
                        found = True
                        break
                else:
                    if issue_type.lower() in str(q).lower():
                        initial_question = q
                        found = True
                        break
    # Fallback: pick first question from identification or nature_of_complaint
    if not initial_question:
        id_questions = qb.get("identification", [])
        if id_questions:
            initial_question = id_questions[0].get('question') if isinstance(id_questions[0], dict) else id_questions[0]
        else:
            nc_questions = qb.get("nature_of_complaint", [])
            initial_question = nc_questions[0].get('question') if nc_questions and isinstance(nc_questions[0], dict) else (nc_questions[0] if nc_questions else "Can you describe your issue?")

    # Create a session
    session_id = f"session_{datetime.now().timestamp()}"
    sessions[session_id] = {
        "phone_number": phone_number,
        "district": district,
        "weather": weather,
        "asked_questions": [],
        "responses": {},
        "question_queue": session_questions,
        "current_section": 0,
        "current_question": 0,
        "current_section_name": session_questions[0]["section"] if session_questions else "network_connectivity",
        "issue_sections": question_sections,
        "main_issue_type": issue_type,
        "is_random_questions_mode": False,  # Track if we're asking random questions
        "confirmed_section": None,  # Track which section was confirmed (if any)
        "confidence_level": 0,  # Track confidence: 0=low, 1=medium (1 YES), 2=high (2+ YES)
        "yes_count": 0,  # Count of YES answers
    }

    welcome_msg = f"Hello! I've identified you're calling from {district} district. "
    if weather and weather != "normal":
        welcome_msg += f"Current weather: {weather}. "
    welcome_msg += "Let me ask you a few questions to help identify and resolve your issue."

    # Send first question from first section
    first_question = session_questions[0]["questions"][0] if session_questions and session_questions[0]["questions"] else initial_question
    sessions[session_id]["asked_questions"].append(first_question)
    return jsonify({
        "session_id": session_id,
        "district": district,
        "phone_number": phone_number,
        "weather": weather,
        "initial_question": first_question,
        "issue_type": issue_type,
        "welcome_message": welcome_msg
    })


# ...existing code for static file serving...


# --- ML-based answer-question endpoint ---
@app.route('/api/answer-question', methods=['POST'])
def answer_question():
    data = request.json
    session_id = data.get('session_id')
    answer = data.get('answer')
    question_id = data.get('question_id')
    if not session_id or not answer or not question_id:
        return jsonify({'error': 'Missing session_id, answer, or question_id'}), 400

    session = sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 400

    # Save the answer
    session['responses'][question_id] = answer

    # Improved routing logic
    queue = session.get('question_queue', [])
    section_idx = session.get('current_section', 0)
    question_idx = session.get('current_question', 0)
    last_answer = answer.lower() if isinstance(answer, str) else str(answer).lower()
    
    # Get current section name from session or queue
    current_section_name = session.get('current_section_name', 'network_connectivity')
    
    # If max questions reached (5), terminate regardless of confidence
    if len(session['asked_questions']) >= 5:
        confidence_level = session.get('confidence_level', 0)
        confirmed_section = session.get('confirmed_section', current_section_name)
        
        agent_map = {
            'network_connectivity': 'Network Agent',
            'billing_account': 'Billing Agent',
            'service_activation': 'Activation Agent',
            'equipment_infrastructure': 'Equipment Agent',
            'premise_setup': 'Premise Agent',
        }
        
        # Route based on confirmed section if any, otherwise use current section
        routing_section = confirmed_section if confirmed_section else current_section_name
        agent = agent_map.get(routing_section, 'General Support Agent')
        
        # If no confidence (all NOs), route to general support
        if confidence_level == 0 and not confirmed_section:
            agent = 'General Support Agent'
            return jsonify({
                'completed': True,
                'category': 'unresolved',
                'issue_type': 'unresolved',
                'solution': {
                    'agent': agent,
                    'priority': 'low',
                    'solution': 'Maximum questions reached. No specific issue identified. Routing to general support.'
                }
            })
        
        return jsonify({
            'completed': True,
            'category': 'max_questions_reached',
            'issue_type': routing_section if confirmed_section else 'unresolved',
            'solution': {
                'agent': agent,
                'priority': 'high' if confidence_level >= 1 else 'medium',
                'solution': 'Maximum questions reached. Routing to specialized agent based on responses.'
            }
        })
    
    current_section = queue[section_idx] if section_idx < len(queue) else None
    if not current_section:
        return jsonify({'error': 'Invalid section'}), 400
    
    current_section_questions = current_section['questions']
    current_section_name = current_section['section']  # Update from queue
    session['current_section_name'] = current_section_name  # Store in session
    
    # ROUTING LOGIC:
    # 1. If customer says YES → continue asking more questions from SAME section
    # 2. If customer says NO to FIRST question → move to NEXT issue type
    # 3. If customer says NO to follow-up question → continue with more questions from SAME section
    
    if last_answer == 'yes':
        # Customer confirmed issue - update confidence
        session['confirmed_section'] = current_section_name
        session['yes_count'] = session.get('yes_count', 0) + 1
        
        # Update confidence level: 1 YES = medium, 2+ YES = high
        if session['yes_count'] >= 2:
            session['confidence_level'] = 2  # High confidence
        elif session['yes_count'] == 1:
            session['confidence_level'] = 1  # Medium confidence
        
        # Check if we're in random questions mode
        if session.get('is_random_questions_mode'):
            # Customer said YES to a random question - we have confidence, route immediately
            agent_map = {
                'network_connectivity': 'Network Agent',
                'billing_account': 'Billing Agent',
                'service_activation': 'Activation Agent',
                'equipment_infrastructure': 'Equipment Agent',
                'premise_setup': 'Premise Agent',
            }
            agent = agent_map.get(current_section_name, 'General Support Agent')
            return jsonify({
                'completed': True,
                'category': 'confirmed_from_random',
                'issue_type': current_section_name,
                'solution': {
                    'agent': agent,
                    'priority': 'medium',
                    'solution': 'Issue identified from general questions. Routing to specialized agent.'
                }
            })
        
        # Normal flow: continue asking questions from same section
        # If customer said YES to first question (Q1), skip Q2 and go to Q3
        asked_ids = [q.get('id', '') if isinstance(q, dict) else '' for q in session['asked_questions']]
        next_question = None
        next_question_idx = None
        
        # Check if this was the first question (Q1)
        is_first_question = (question_idx == 0)
        
        if is_first_question and len(current_section_questions) > 2:
            # Skip Q2 (index 1), go directly to Q3 (index 2)
            next_question = current_section_questions[2]
            next_question_idx = 2
        else:
            # Normal flow: find next unasked question
            for idx, q in enumerate(current_section_questions):
                q_id = q.get('id', '') if isinstance(q, dict) else ''
                if q_id not in asked_ids:
                    next_question = q
                    next_question_idx = idx
                    break
        
        # Check confidence: Only terminate early if high confidence (2+ YES) OR max questions reached
        confidence_level = session.get('confidence_level', 0)
        questions_asked = len(session['asked_questions'])
        
        # High confidence (2+ YES answers) - terminate early with confidence
        if confidence_level >= 2 and questions_asked < 5:
            agent_map = {
                'network_connectivity': 'Network Agent',
                'billing_account': 'Billing Agent',
                'service_activation': 'Activation Agent',
                'equipment_infrastructure': 'Equipment Agent',
                'premise_setup': 'Premise Agent',
            }
            agent = agent_map.get(current_section_name, 'General Support Agent')
            return jsonify({
                'completed': True,
                'category': 'confirmed_issue',
                'issue_type': current_section_name,
                'solution': {
                    'agent': agent,
                    'priority': 'high',
                    'solution': 'Issue confirmed with high confidence. Routing to specialized agent for resolution.'
                }
            })
        
        # Continue asking if we have questions and haven't reached max
        if next_question and questions_asked < 5:
            session['current_question'] = next_question_idx
            session['asked_questions'].append(next_question)
            
            # If max questions reached, terminate
            if len(session['asked_questions']) >= 5:
                agent_map = {
                    'network_connectivity': 'Network Agent',
                    'billing_account': 'Billing Agent',
                    'service_activation': 'Activation Agent',
                    'equipment_infrastructure': 'Equipment Agent',
                    'premise_setup': 'Premise Agent',
                }
                agent = agent_map.get(current_section_name, 'General Support Agent')
                return jsonify({
                    'completed': True,
                    'category': 'confirmed_issue',
                    'issue_type': current_section_name,
                    'solution': {
                        'agent': agent,
                        'priority': 'high' if confidence_level >= 1 else 'medium',
                        'solution': 'Issue confirmed. Routing to specialized agent for resolution.'
                    }
                })
            
            return jsonify({
                'next_question': next_question,
                'question_number': len(session['asked_questions']),
                'completed': False
            })
        else:
            # No more questions in this section or max reached, terminate
            agent_map = {
                'network_connectivity': 'Network Agent',
                'billing_account': 'Billing Agent',
                'service_activation': 'Activation Agent',
                'equipment_infrastructure': 'Equipment Agent',
                'premise_setup': 'Premise Agent',
            }
            agent = agent_map.get(current_section_name, 'General Support Agent')
            return jsonify({
                'completed': True,
                'category': 'confirmed_issue',
                'issue_type': current_section_name,
                'solution': {
                    'agent': agent,
                    'priority': 'high' if confidence_level >= 1 else 'medium',
                    'solution': 'Issue confirmed. Routing to specialized agent for resolution.'
                }
            })
    
    elif last_answer == 'no':
        # Check if this was the FIRST question of this section
        is_first_question = (question_idx == 0)
        
        if is_first_question:
            # Customer said NO to first question of this section → move to next issue type
            section_idx += 1
            session['current_section'] = section_idx
            session['current_question'] = 0
            
            # Debug: Print queue info
            print(f"DEBUG NO answer: section_idx={section_idx}, queue length={len(queue)}, queue sections={[q['section'] for q in queue] if queue else 'EMPTY'}")
            print(f"DEBUG NO answer: current_section={current_section_name}, question_idx={question_idx}")
            
            if len(queue) > 0 and section_idx < len(queue):
                # Move to next issue type
                next_section = queue[section_idx]
                next_q = next_section['questions'][0] if next_section['questions'] else None
                
                print(f"DEBUG NO answer: next_section={next_section['section']}, next_q={next_q.get('id', 'NO_ID') if next_q and isinstance(next_q, dict) else 'NOT_DICT'}")
                
                if next_q:
                    session['current_section_name'] = next_section['section']  # Update section name
                    session['asked_questions'].append(next_q)
                    
                    if len(session['asked_questions']) >= 5:
                        agent_map = {
                            'network_connectivity': 'Network Agent',
                            'billing_account': 'Billing Agent',
                            'service_activation': 'Activation Agent',
                            'equipment_infrastructure': 'Equipment Agent',
                            'premise_setup': 'Premise Agent',
                        }
                        agent = agent_map.get(next_section['section'], 'General Support Agent')
                        return jsonify({
                            'completed': True,
                            'category': 'unresolved',
                            'issue_type': 'unresolved',
                            'solution': {
                                'agent': agent,
                                'priority': 'medium',
                                'solution': 'No specific issue confirmed. Routing to specialized agent.'
                            }
                        })
                    
                    return jsonify({
                        'next_question': next_q,
                        'question_number': len(session['asked_questions']),
                        'completed': False
                    })
                else:
                    print(f"DEBUG: No questions in next_section {next_section['section']}")
            else:
                print(f"DEBUG: Cannot move to next section - section_idx={section_idx}, queue length={len(queue)}")
            
            # No more issue types, switch to random questions mode
            session['is_random_questions_mode'] = True
            session['current_section_name'] = 'network_connectivity'  # Default to network for random questions
            
            # Ask random network question
            qb = question_bank.get("complaint_question_bank", question_bank)
            network_questions = qb.get("internal_factors", {}).get("network_connectivity", [])
            asked_ids = [q.get('id', '') if isinstance(q, dict) else '' for q in session['asked_questions']]
            
            # Find a network question not already asked
            random_net_q = None
            for q in network_questions:
                q_id = q.get('id', '') if isinstance(q, dict) else ''
                if q_id not in asked_ids:
                    random_net_q = q
                    break
            
            if random_net_q and len(session['asked_questions']) < 5:
                session['asked_questions'].append(random_net_q)
                
                return jsonify({
                    'next_question': random_net_q,
                    'question_number': len(session['asked_questions']),
                    'completed': False
                })
            else:
                # No more questions or max reached, terminate
                agent = 'General Support Agent'
                if session.get('confirmed_section'):
                    agent_map = {
                        'network_connectivity': 'Network Agent',
                        'billing_account': 'Billing Agent',
                        'service_activation': 'Activation Agent',
                        'equipment_infrastructure': 'Equipment Agent',
                        'premise_setup': 'Premise Agent',
                    }
                    agent = agent_map.get(session['confirmed_section'], 'General Support Agent')
                
                return jsonify({
                    'completed': True,
                    'category': 'unresolved',
                    'issue_type': 'unresolved',
                    'solution': {
                        'agent': agent,
                        'priority': 'medium',
                        'solution': 'No specific issue confirmed. Routing to general support.'
                    }
                })
        else:
            # Customer said NO to a follow-up question
            # Check if we're in random questions mode
            if session.get('is_random_questions_mode'):
                # Continue asking random questions
                qb = question_bank.get("complaint_question_bank", question_bank)
                network_questions = qb.get("internal_factors", {}).get("network_connectivity", [])
                asked_ids = [q.get('id', '') if isinstance(q, dict) else '' for q in session['asked_questions']]
                
                # Find another network question not already asked
                random_net_q = None
                for q in network_questions:
                    q_id = q.get('id', '') if isinstance(q, dict) else ''
                    if q_id not in asked_ids:
                        random_net_q = q
                        break
                
                if random_net_q and len(session['asked_questions']) < 5:
                    session['asked_questions'].append(random_net_q)
                    return jsonify({
                        'next_question': random_net_q,
                        'question_number': len(session['asked_questions']),
                        'completed': False
                    })
                else:
                    # No more questions or max reached, terminate
                    agent = 'General Support Agent'
                    if session.get('confirmed_section'):
                        agent_map = {
                            'network_connectivity': 'Network Agent',
                            'billing_account': 'Billing Agent',
                            'service_activation': 'Activation Agent',
                            'equipment_infrastructure': 'Equipment Agent',
                            'premise_setup': 'Premise Agent',
                        }
                        agent = agent_map.get(session['confirmed_section'], 'General Support Agent')
                    
                    return jsonify({
                        'completed': True,
                        'category': 'unresolved',
                        'issue_type': 'unresolved',
                        'solution': {
                            'agent': agent,
                            'priority': 'medium',
                            'solution': 'No specific issue confirmed. Routing to general support.'
                        }
                    })
            else:
                # Normal flow: continue with more questions from SAME section
                asked_ids = [q.get('id', '') if isinstance(q, dict) else '' for q in session['asked_questions']]
                next_question = None
                next_question_idx = None
                
                for idx, q in enumerate(current_section_questions):
                    q_id = q.get('id', '') if isinstance(q, dict) else ''
                    if q_id not in asked_ids:
                        next_question = q
                        next_question_idx = idx
                        break
                
                if next_question and len(session['asked_questions']) < 5:
                    # More questions available in this section
                    session['current_question'] = next_question_idx
                    session['asked_questions'].append(next_question)
                    
                    if len(session['asked_questions']) >= 5:
                        agent_map = {
                            'network_connectivity': 'Network Agent',
                            'billing_account': 'Billing Agent',
                            'service_activation': 'Activation Agent',
                            'equipment_infrastructure': 'Equipment Agent',
                            'premise_setup': 'Premise Agent',
                        }
                        agent = agent_map.get(current_section_name, 'General Support Agent')
                        return jsonify({
                            'completed': True,
                            'category': 'unresolved',
                            'issue_type': current_section_name,
                            'solution': {
                                'agent': agent,
                                'priority': 'medium',
                                'solution': 'No specific issue confirmed. Routing to specialized agent.'
                            }
                        })
                    
                    return jsonify({
                        'next_question': next_question,
                        'question_number': len(session['asked_questions']),
                        'completed': False
                    })
                else:
                    # No more questions in this section or max reached, terminate
                    agent_map = {
                        'network_connectivity': 'Network Agent',
                        'billing_account': 'Billing Agent',
                        'service_activation': 'Activation Agent',
                        'equipment_infrastructure': 'Equipment Agent',
                        'premise_setup': 'Premise Agent',
                    }
                    agent = agent_map.get(current_section_name, 'General Support Agent')
                    return jsonify({
                        'completed': True,
                        'category': 'unresolved',
                        'issue_type': current_section_name,
                        'solution': {
                            'agent': agent,
                            'priority': 'medium',
                            'solution': 'No specific issue confirmed. Routing to specialized agent.'
                        }
                    })
    # If answer is not yes/no, treat as invalid and terminate
    else:
        return jsonify({
            'completed': True,
            'category': 'invalid',
            'issue_type': 'invalid',
            'solution': {
                'agent': 'General Support Agent',
                'priority': 'low',
                'solution': 'Invalid response. Please contact support.'
            }
        })


# ...existing code for static file serving...

# ...existing code for static file serving...

# ...existing code for static file serving...

# ...existing code for static file serving...

# ...existing code for static file serving...

if __name__ == '__main__':
    print("\n" + "="*50)
    print("SLT IVR Backend Server Starting...")
    print("="*50)
    print(f"Server running on: http://localhost:5007")
    print(f"API Base URL: http://localhost:5007/api")
    print("="*50)
    print("Press Ctrl+C to stop the server\n")
    app.run(debug=True, port=5007, host='0.0.0.0')

