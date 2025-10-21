from langchain_ollama import OllamaLLM
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate


def create_chatbot():
    """
    Creates and returns a LangChain-based chatbot that interacts with users
    to identify their complaint type (issue_type + sub_category).
    """

    llm = OllamaLLM(model="llama3")
    memory = ConversationBufferMemory()

    prompt = PromptTemplate.from_template(
        """
You are a helpful telecom complaint assistant for Sri Lanka Telecom (SLT).
Your task is to identify the user's complaint in maximum 5 questions.

You must find and return:
- issue_type: (Weather / Billing / Network / Other)
- sub_category: (WiFi / Landline / Mobile / etc.)

When you are confident, stop the conversation and reply only with JSON:
{{"issue_type": "...", "sub_category": "..."}}

If not confident yet, ask the next best question to clarify.

Conversation history:
{history}

User: {input}
Assistant:
"""
    )

    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=prompt,
    )

    return conversation, memory


