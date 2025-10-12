from langchain.llms import Ollama
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

# 1️⃣ Load local LLaMA 3 model
llm = Ollama(model="llama3")

# 2️⃣ Add memory so chatbot remembers previous answers
memory = ConversationBufferMemory()

# 3️⃣ Define how chatbot should behave
template = """
You are SLT Complaint Assistant chatbot.
Ask the user up to 5 short questions to identify their issue.

You already know:
- SLT provides Internet, Wi-Fi, and landline services.
- Possible issues: Weather, Network, Billing, Technical.
- After 5 questions, summarize issue_type and sub_category in JSON.

Example Output:
{"issue_type": "Weather", "sub_category": "WiFi"}

Conversation so far:
{history}

User: {input}
Chatbot:
"""

prompt = PromptTemplate(input_variables=["history", "input"], template=template)

# 4️⃣ Build the conversation chain
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    prompt=prompt
)

# 5️⃣ Run chatbot loop
print("💬 SLT Complaint Chatbot (type 'exit' to quit)")
while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        print("👋 Goodbye!")
        break
    response = conversation.predict(input=user_input)
    print("Bot:", response)
