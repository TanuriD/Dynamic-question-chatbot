"""
Billing Agent - Handles billing-related issues
"""
from langchain_ollama import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
import os


def create_billing_agent(billing_issue: str = None):
    """
    Creates a billing agent chatbot to handle billing-related issues.
    """
    model_name = os.getenv("OLLAMA_MODEL", "gemma3")
    llm = ChatOllama(model=model_name, temperature=0.6)
    
    memory = ConversationBufferMemory(
        return_messages=True,
        memory_key="history"
    )

    billing_context = ""
    if billing_issue:
        billing_context = f"""
IMPORTANT CONTEXT: The customer has a billing issue: {billing_issue}
This is a BILLING-RELATED problem that needs to be resolved.

BILLING AGENT FOCUS:
1. Understand the specific billing problem
2. Verify account details and billing history
3. Investigate discrepancies
4. Provide resolution steps
5. Escalate if needed
"""

    system_prompt = """
You are SLT Billing Agent - a specialized assistant for handling billing issues.

Your role:
- Help customers resolve billing problems
- Verify billing discrepancies
- Explain charges and fees
- Process refunds or adjustments when appropriate
- Escalate complex issues to billing department

""" + billing_context + """

IMPORTANT RULES:
1. Be professional, empathetic, and helpful
2. Ask specific questions about the billing issue
3. Verify account information when needed
4. Provide clear explanations of charges
5. Offer solutions and next steps
6. Keep responses concise and clear
"""

    def conversation(input_dict):
        """Handle conversation with memory"""
        user_input = input_dict["input"]
        
        history_msgs = memory.load_memory_variables({}).get("history", [])
        
        conversation_text = system_prompt + "\n\nConversation so far:\n"
        
        for msg in history_msgs[-10:]:
            if hasattr(msg, 'type'):
                if msg.type == "human":
                    conversation_text += f"User: {msg.content}\n"
                else:
                    conversation_text += f"Billing Agent: {msg.content}\n"
            else:
                role = "User" if isinstance(msg, HumanMessage) else "Billing Agent"
                conversation_text += f"{role}: {msg.content}\n"
        
        conversation_text += f"\nUser: {user_input}\nBilling Agent:"
        
        try:
            result = llm.invoke(conversation_text)
            response_text = result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            print(f"❌ Billing Agent LLM error: {e}")
            response_text = "I'm having trouble processing your request. Could you please rephrase that?"
        
        memory.chat_memory.add_message(HumanMessage(content=user_input))
        memory.chat_memory.add_message(AIMessage(content=response_text))
        
        return {"response": response_text}
    
    return conversation, memory

