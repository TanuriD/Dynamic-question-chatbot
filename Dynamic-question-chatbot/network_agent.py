"""
Network Agent - Handles network-related issues
"""
from langchain_ollama import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
import os


def create_network_agent(network_issue: str = None):
    """
    Creates a network agent chatbot to handle network-related issues.
    """
    model_name = os.getenv("OLLAMA_MODEL", "gemma3")
    llm = ChatOllama(model=model_name, temperature=0.6)
    
    memory = ConversationBufferMemory(
        return_messages=True,
        memory_key="history"
    )

    network_context = ""
    if network_issue:
        network_context = f"""
IMPORTANT CONTEXT: The customer has a network issue: {network_issue}
This is a NETWORK-RELATED problem that needs technical investigation.

NETWORK AGENT FOCUS:
1. Diagnose network connectivity problems
2. Check service status and maintenance
3. Troubleshoot connection issues
4. Verify network infrastructure
5. Coordinate with technical team if needed
"""

    system_prompt = """
You are SLT Network Agent - a specialized assistant for handling network issues.

Your role:
- Diagnose network connectivity problems
- Check service status and outages
- Troubleshoot connection issues
- Verify network infrastructure status
- Coordinate with technical teams
- Provide technical solutions

""" + network_context + """

IMPORTANT RULES:
1. Be technical but clear in explanations
2. Ask diagnostic questions systematically
3. Check for known outages or maintenance
4. Provide step-by-step troubleshooting
5. Escalate to technical team when needed
6. Keep responses concise and actionable
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
                    conversation_text += f"Network Agent: {msg.content}\n"
            else:
                role = "User" if isinstance(msg, HumanMessage) else "Network Agent"
                conversation_text += f"{role}: {msg.content}\n"
        
        conversation_text += f"\nUser: {user_input}\nNetwork Agent:"
        
        try:
            result = llm.invoke(conversation_text)
            response_text = result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            print(f"❌ Network Agent LLM error: {e}")
            response_text = "I'm having trouble processing your request. Could you please rephrase that?"
        
        memory.chat_memory.add_message(HumanMessage(content=user_input))
        memory.chat_memory.add_message(AIMessage(content=response_text))
        
        return {"response": response_text}
    
    return conversation, memory

