from langchain_ollama import OllamaLLM
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate


def create_chatbot():
    """
    Creates and returns a LangChain-based chatbot that interacts with users
    to identify their complaint type (issue_type + sub_category).
    """

    # 1️⃣ Load local model through Ollama
    llm = OllamaLLM(model="llama3")  # you can use "mistral" or "phi3" too

    # 2️⃣ Set up memory to store previous chat context
    memory = ConversationBufferMemory()

    # 3️⃣ Define the prompt structure for the chatbot
    prompt = PromptTemplate.from_template("""
You are a helpful telecom complaint assistant for Sri Lanka Telecom (SLT).
Your task is to identify the user's complaint in maximum 5 questions.

You must find and return:
- issue_type: (Weather / Billing / Network / Other)
- sub_category: (WiFi / Landline / Mobile / etc.)

When you are confident, stop the conversation and reply **only** with JSON:
{{"issue_type": "...", "sub_category": "..."}}

If not confident yet, ask the next best question to clarify.

Conversation history:
{history}

User: {input}
Assistant:
""")

    # 4️⃣ Create the conversation chain
    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=prompt
    )

    return conversation, memory
