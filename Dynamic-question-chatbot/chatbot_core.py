from langchain_ollama import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
import os


def create_chatbot(district=None, weather=None, issue_type=None, billing_issue=None, network_issue=None):
    """
    Creates and returns a LangChain-based chatbot that interacts with users
    to identify their complaint type (issue_type + sub_category).
    Now includes weather-aware contextual questioning and billing/network detection.
    """

    # Use ChatOllama instead of OllamaLLM for better compatibility
    model_name = os.getenv("OLLAMA_MODEL", "gemma3")
    llm = ChatOllama(model=model_name, temperature=0.6)
    
    memory = ConversationBufferMemory(
        return_messages=True,
        memory_key="history"
    )

    # Billing/Network detection context
    issue_context = ""
    first_question_hint = ""
    
    if issue_type == "billing" and billing_issue:
        issue_context = f"""
IMPORTANT CONTEXT: SLT has detected a BILLING ISSUE for this customer: {billing_issue}
The customer may not be aware of this issue yet. SLT knows about it.

BILLING-AWARE QUESTIONING STRATEGY:
1. CRITICAL: DO NOT ask the generic "Which service is having issues - WiFi, Internet, Landline, or Mobile?" question.
2. FIRST question MUST be: "I see you have a billing issue: {billing_issue}. Which service is affected by this billing issue - WiFi, Internet, Landline, or Mobile?"
3. After the customer tells you which service is affected, continue asking dynamic questions to understand more details
4. Ask about charges, discrepancies, payment issues, or specific billing problems related to that service
5. Keep the conversation dynamic - don't hardcode questions, adapt based on customer responses
6. NEVER repeat the same question - always ask NEW questions
7. Route to billing agent at the end if confirmed as billing issue
"""
        first_question_hint = f"FIRST inform customer about the billing issue: {billing_issue}, then ask which service (WiFi/Internet/Landline/Mobile) is affected by this billing issue"
    elif issue_type == "network" and network_issue:
        issue_context = f"""
IMPORTANT CONTEXT: SLT has detected a NETWORK ISSUE/MAINTENANCE for this customer: {network_issue}
The customer may not be aware of this issue yet. SLT knows about it (e.g., maintenance in area, service disruptions).

NETWORK-AWARE QUESTIONING STRATEGY:
1. CRITICAL: DO NOT ask the generic "Which service is having issues - WiFi, Internet, Landline, or Mobile?" question.
2. FIRST question MUST be: "I see there's a network issue: {network_issue}. Which service is affected by this network issue - WiFi, Internet, Landline, or Mobile?"
3. After the customer tells you which service is affected, continue asking dynamic questions to understand more details
4. Ask about connectivity problems, service status, maintenance impact, or specific network issues related to that service
5. Keep the conversation dynamic - don't hardcode questions, adapt based on customer responses
6. NEVER repeat the same question - always ask NEW questions
7. Route to network agent at the end if confirmed as network issue
"""
        first_question_hint = f"FIRST inform customer about the network issue/maintenance: {network_issue}, then ask which service (WiFi/Internet/Landline/Mobile) is affected by this network issue"
    elif issue_type == "both":
        issue_context = f"""
IMPORTANT CONTEXT: SLT has detected BOTH billing and network issues for this customer:
- Billing: {billing_issue}
- Network: {network_issue}
The customer may not be aware of these issues yet. SLT knows about them.

DUAL ISSUE QUESTIONING STRATEGY:
1. CRITICAL: DO NOT ask the generic "Which service is having issues - WiFi, Internet, Landline, or Mobile?" question.
2. FIRST question MUST be: "I see you have both a billing issue ({billing_issue}) and a network issue ({network_issue}). Which would you like to address first - your billing issue or network issue?"

3. After they choose, inform them about that specific issue and ask which service is affected
   - If billing: "I see you have a billing issue: {billing_issue}. Which service is affected by this billing issue - WiFi, Internet, Landline, or Mobile?"
   - If network: "I see there's a network issue: {network_issue}. Which service is affected by this network issue - WiFi, Internet, Landline, or Mobile?"

4. Continue asking dynamic questions based on their responses
5. Keep the conversation dynamic - don't hardcode questions, adapt based on customer responses
6. NEVER repeat the same question - always ask NEW questions
7. Route to appropriate agent based on their choice
"""
        first_question_hint = f"FIRST inform customer about both issues (billing: {billing_issue}, network: {network_issue}), then ask which they want to address first"

    # Weather-aware prompt template (YOUR ORIGINAL LOGIC)
    weather_context = ""
    if district and weather:
        weather_lower = weather.lower()
        is_bad_weather = any(word in weather_lower for word in ["rain", "storm", "thunder", "heavy", "severe", "stormy", "windy"])
        
        if is_bad_weather:
            weather_context = f"""
IMPORTANT CONTEXT: The customer is in {district} where the weather is: {weather}
This is BAD WEATHER that commonly affects telecom services.

WEATHER-AWARE QUESTIONING STRATEGY:
1. If no billing/network issue detected, FIRST question should acknowledge the weather and ask which service is affected
   Example: "I can see it's {weather} in {district}, which often affects connectivity. Which service is having issues - WiFi, Internet, Landline, or Mobile?"

2. If they mention weather-related issues, ask for specific problems
3. If they don't mention weather, still ask about specific problems
4. Focus on weather-related routing if applicable

BAD WEATHER KEYWORDS: rain, storm, thunder, heavy, severe, stormy, windy
"""
        else:
            weather_context = f"""
IMPORTANT CONTEXT: The customer is in {district} where the weather is: {weather}
This is NORMAL/GOOD WEATHER.

NORMAL WEATHER QUESTIONING STRATEGY:
1. If no billing/network issue detected, FIRST question should ask which service is affected (don't mention weather)
   Example: "Which service is having issues - WiFi, Internet, Landline, or Mobile?"

2. Ask about specific problems
3. Don't assume weather-related issues unless customer mentions them

GOOD WEATHER - focus on technical issues, billing, or other non-weather problems.
"""

    # Build the dynamic system prompt (YOUR ORIGINAL LOGIC)
    system_prompt = """
You are SLT Complaint Assistant chatbot.
Ask the user up to 5 short questions to identify their issue. You can ask a maximum of 5 questions.

You already know:
- SLT provides Internet, Wi-Fi, Landline, and Mobile services.
- Possible issues: Weather, Network, Billing, Technical.
- After 5 questions, summarize issue_type and sub_category in JSON.

""" + issue_context + weather_context + """

IMPORTANT RULES:
1. Start asking questions immediately. Don't wait for greetings.
2. Be proactive and direct in your questioning.
3. CRITICAL: NEVER repeat the same question - always ask a NEW question. Check conversation history before asking.
4. """ + (f"FIRST QUESTION PRIORITY: {first_question_hint}" if first_question_hint else "") + """
5. """ + ("CRITICAL: If billing/network issue is detected, DO NOT ask the generic service question. Use the issue-specific question format shown above." if first_question_hint else "") + """
6. CRITICAL: When user answers "wifi", "internet", "landline", or "mobile" to your question, they have ANSWERED the service question. DO NOT ask the service question again. Move to the next question immediately.
7. The sub_category is DETERMINED by the user's answer about which service is having issues.
8. REMEMBER: If user says "wifi" then sub_category = WiFi. If "internet" then Internet. If "landline" then Landline. If "mobile" then Mobile.
9. After the customer tells you which service is affected, IMMEDIATELY ask a DIFFERENT follow-up question about that specific service and billing/network issue. Do NOT repeat the service question.
10. CONTINUE DYNAMICALLY - ask follow-up questions based on their responses. Don't hardcode the flow.
11. Adapt your questions based on what the customer tells you. Each conversation should be unique and responsive to their specific situation.
12. NEVER change the sub_category - it is locked in from the user's answer.
13. After asking 5 questions OR when you have enough information, STOP asking questions and return JSON.
14. ALWAYS check conversation history to see what has already been asked - NEVER repeat a question.
15. Each response must be a NEW question that hasn't been asked before in this conversation.
16. CRITICAL: The sub_category MUST ALWAYS be one of: WiFi, Internet, Landline, or Mobile - NEVER Unknown.
17. CRITICAL: If billing issue was detected, issue_type should be "Billing". If network issue was detected, issue_type should be "Network".
18. When you have enough information, return ONLY JSON in this format with curly braces and quotes around keys and values
19. Do NOT ask more questions after returning JSON.

Example conversation flow (MEMORIZE THE SERVICE TYPE):
- Q1: "Which service is having issues - WiFi, Internet, Landline, or Mobile?"
- User: "wifi"
- [NOTE: User selected "wifi", so sub_category is LOCKED to WiFi for this entire conversation]
- Q2: "What specific problem are you experiencing with your WiFi?"
- User: "slow speed"
- Q3: "How long has this been happening?"
- User: "since yesterday"
- Q4: "Are other devices also experiencing slow speeds or just this one?"
- User: "all devices"
- Q5: "Have you tried restarting your router?"
- User: "yes"
- [FINAL JSON - MUST include sub_category: WiFi because user said wifi at the beginning]
- Response: {{"issue_type": "Technical", "sub_category": "WiFi"}}

CRITICAL REMINDER:
- If user says "wifi" then sub_category MUST be WiFi in final JSON
- If user says "internet" then sub_category MUST be Internet in final JSON
- If user says "landline" then sub_category MUST be Landline in final JSON
- If user says "mobile" then sub_category MUST be Mobile in final JSON
- sub_category MUST NEVER be Unknown - it is always one of the 4 service types the user selected

JSON FORMAT MUST BE EXACTLY:
{{"issue_type": "Weather or Network or Billing or Technical or Other", "sub_category": "WiFi or Internet or Landline or Mobile"}}

ROUTING RULES:
- If issue_type is "Billing" → route to billing agent
- If issue_type is "Network" → route to network agent  
- If issue_type is "Weather" → route to weather agent
- Otherwise → route to default agent
"""

    def conversation(input_dict):
        """Handle conversation with memory - maintains your original logic"""
        user_input = input_dict["input"]
        
        # Get conversation history
        history_msgs = memory.load_memory_variables({}).get("history", [])
        
        # Build conversation context with history
        conversation_text = system_prompt + "\n\nConversation so far:\n"
        
        # Track questions already asked to prevent duplicates
        asked_questions = []
        
        # Add history
        for msg in history_msgs[-10:]:  # Last 10 messages to keep context manageable
            if hasattr(msg, 'type'):
                if msg.type == "human":
                    conversation_text += f"User: {msg.content}\n"
                else:
                    # Track chatbot questions
                    bot_msg = msg.content.strip()
                    if bot_msg and not bot_msg.startswith("{"):  # Not JSON
                        asked_questions.append(bot_msg.lower())
                    conversation_text += f"Chatbot: {msg.content}\n"
            else:
                # Fallback for different message formats
                role = "User" if isinstance(msg, HumanMessage) else "Chatbot"
                if role == "Chatbot":
                    bot_msg = msg.content.strip()
                    if bot_msg and not bot_msg.startswith("{"):  # Not JSON
                        asked_questions.append(bot_msg.lower())
                conversation_text += f"{role}: {msg.content}\n"
        
        # Add warning about not repeating questions
        if asked_questions:
            conversation_text += f"\n⚠️ IMPORTANT: The following questions have already been asked. DO NOT repeat them:\n"
            for q in asked_questions[-5:]:  # Last 5 questions
                conversation_text += f"- {q[:100]}\n"  # Truncate long questions
            conversation_text += "\n"
        
        # Check if user has already answered the service question
        user_input_lower = user_input.lower().strip()
        service_keywords = ["wifi", "internet", "landline", "mobile"]
        service_answered = any(keyword in user_input_lower for keyword in service_keywords)
        detected_service = None
        
        if service_answered:
            # Extract which service was mentioned
            for keyword in service_keywords:
                if keyword in user_input_lower:
                    detected_service = keyword.capitalize() if keyword != "wifi" else "WiFi"
                    break
            
            if detected_service:
                conversation_text += f"\n✅ USER HAS ALREADY ANSWERED THE SERVICE QUESTION: {detected_service}\n"
                conversation_text += f"DO NOT ask about which service is affected again. Ask a DIFFERENT follow-up question about the {detected_service} service and the billing/network issue.\n"
        
        # Add current user input
        conversation_text += f"\nUser: {user_input}\nChatbot:"
        
        # Get response from LLM
        try:
            result = llm.invoke(conversation_text)
            response_text = result.content if hasattr(result, 'content') else str(result)
            
            # Check if response is a duplicate question (simple check)
            response_lower = response_text.strip().lower()
            
            # Check for duplicate service question patterns
            service_question_patterns = [
                "which service is affected",
                "which service is having issues",
                "which service",
                "wifi, internet, landline, or mobile"
            ]
            is_service_question = any(pattern in response_lower for pattern in service_question_patterns)
            
            if (response_lower in asked_questions or (is_service_question and service_answered)) and not response_text.strip().startswith("{"):
                if service_answered and detected_service:
                    print(f"⚠️ Detected duplicate service question after user already answered. Generating different question.")
                    retry_prompt = conversation_text + f"\n⚠️ CRITICAL: The user has already told you which service is affected ({detected_service}). DO NOT ask about the service again. Ask a DIFFERENT follow-up question about the {detected_service} service and the specific billing/network issue."
                else:
                    print(f"⚠️ Detected potential duplicate question, asking LLM to generate a different one")
                    retry_prompt = conversation_text + "\n⚠️ The response above was already asked. Please provide a DIFFERENT question that hasn't been asked yet."
                result = llm.invoke(retry_prompt)
                response_text = result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            print(f"❌ LLM invoke error: {e}")
            response_text = "I'm having trouble processing your request. Could you rephrase that?"
        
        # Save to memory
        memory.chat_memory.add_message(HumanMessage(content=user_input))
        memory.chat_memory.add_message(AIMessage(content=response_text))
        
        return {"response": response_text}
    
    # Return both conversation function and memory (YOUR ORIGINAL PATTERN)
    return conversation, memory