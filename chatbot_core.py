from langchain_ollama import OllamaLLM
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate


def create_chatbot(district=None, weather=None):
    """
    Creates and returns a LangChain-based chatbot that interacts with users
    to identify their complaint type (issue_type + sub_category).
    Now includes weather-aware contextual questioning.
    """

    llm = OllamaLLM(model="gemma3")
    memory = ConversationBufferMemory()

    # Weather-aware prompt template
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

    # Build the dynamic prompt template like the template
    prompt_template = """
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
4. If user answers "wifi", "internet", "landline", or "mobile", ask about specific problems.
5. If user describes a problem, ask follow-up questions to understand better.
6. After asking 5 questions OR when you have enough information, STOP asking questions and return JSON.
7. Look at the conversation history to see what has already been asked.
8. Each response should be a NEW question that hasn't been asked before.
9. CRITICAL: The sub_category MUST be the service type the user mentioned (wifi, internet, landline, mobile).
10. If user says "wifi", sub_category should be "WiFi". If "internet", sub_category should be "Internet", etc.
11. When you have enough information, return ONLY JSON in this format: {{"issue_type": "Technical", "sub_category": "WiFi"}}
12. Do NOT ask more questions after returning JSON.

Example conversation flow:
- Q1: "Which service is having issues - WiFi, Internet, Landline, or Mobile?"
- User: "wifi"
- Q2: "What specific problem are you experiencing with your WiFi?"
- User: "slow speed"
- Q3: "How long has this been happening?"
- User: "since yesterday"
- Q4: "Are other devices also slow or just this one?"
- User: "all devices"
- Q5: "Have you tried restarting your router?"
- User: "yes"
- Response: {{"issue_type": "Technical", "sub_category": "WiFi"}}

IMPORTANT: When user says "wifi", sub_category must be "WiFi". When user says "internet", sub_category must be "Internet". When user says "landline", sub_category must be "Landline". When user says "mobile", sub_category must be "Mobile".

Conversation so far:
{history}

User: {input}
Chatbot:
"""

    prompt = PromptTemplate.from_template(prompt_template)

    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=prompt,
    )

    return conversation, memory


