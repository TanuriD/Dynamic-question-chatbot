from langchain_ollama import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
import os


def create_chatbot(district=None, weather=None):
    """
    Creates and returns a LangChain-based chatbot that interacts with users
    to identify their complaint type (issue_type + sub_category).
    Now includes weather-aware contextual questioning.
    """

    # Use ChatOllama instead of OllamaLLM for better compatibility
    model_name = os.getenv("OLLAMA_MODEL", "gemma3")
    llm = ChatOllama(model=model_name, temperature=0.6)
    
    memory = ConversationBufferMemory(
        return_messages=True,
        memory_key="history"
    )

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
1. FIRST question should acknowledge the weather and ask which service is affected
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
1. FIRST question should ask which service is affected (don't mention weather)
   Example: "Which service is having issues - WiFi, Internet, Landline, or Mobile?"

2. Ask about specific problems
3. Don't assume weather-related issues unless customer mentions them

GOOD WEATHER - focus on technical issues, billing, or other non-weather problems.
"""

    # Build the dynamic system prompt (YOUR ORIGINAL LOGIC)
    system_prompt = """
You are SLT Complaint Assistant chatbot.
Ask the user up to 5 short questions to identify their issue.

You already know:
- SLT provides Internet, Wi-Fi, Landline, and Mobile services.
- Possible issues: Weather, Network, Billing, Technical.
- After 5 questions, summarize issue_type and sub_category in JSON.

""" + weather_context + """

IMPORTANT RULES:
1. Start asking questions immediately. Don't wait for greetings.
2. Be proactive and direct in your questioning.
3. NEVER repeat the same question - always ask a NEW question.
4. When user answers "wifi", "internet", "landline", or "mobile" to your FIRST question, you MUST REMEMBER this for the entire conversation.
5. The sub_category is DETERMINED by the user's FIRST answer to "Which service is having issues?"
6. REMEMBER: If user says "wifi" then sub_category = WiFi. If "internet" then Internet. If "landline" then Landline. If "mobile" then Mobile.
7. After the user tells you the service type, ask about specific problems to determine issue_type.
8. NEVER change the sub_category - it is locked in from the user's first answer.
9. After asking 5 questions OR when you have enough information, STOP asking questions and return JSON.
10. Look at the conversation history to see what has already been asked.
11. Each response should be a NEW question that hasn't been asked before.
12. CRITICAL: The sub_category MUST ALWAYS be one of: WiFi, Internet, Landline, or Mobile - NEVER Unknown.
13. When you have enough information, return ONLY JSON in this format with curly braces and quotes around keys and values
14. Do NOT ask more questions after returning JSON.

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
"""

    def conversation(input_dict):
        """Handle conversation with memory - maintains your original logic"""
        user_input = input_dict["input"]
        
        # Get conversation history
        history_msgs = memory.load_memory_variables({}).get("history", [])
        
        # Build conversation context with history
        conversation_text = system_prompt + "\n\nConversation so far:\n"
        
        # Add history
        for msg in history_msgs[-10:]:  # Last 10 messages to keep context manageable
            if hasattr(msg, 'type'):
                if msg.type == "human":
                    conversation_text += f"User: {msg.content}\n"
                else:
                    conversation_text += f"Chatbot: {msg.content}\n"
            else:
                # Fallback for different message formats
                role = "User" if isinstance(msg, HumanMessage) else "Chatbot"
                conversation_text += f"{role}: {msg.content}\n"
        
        # Add current user input
        conversation_text += f"\nUser: {user_input}\nChatbot:"
        
        # Get response from LLM
        try:
            result = llm.invoke(conversation_text)
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