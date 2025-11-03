from langchain_ollama import OllamaLLM

# Connect to LLaMA 3 model
llm = OllamaLLM(model="llama3")

# Simple test
response = llm.invoke("Hello! Can you tell me a joke?")
print("Ollama Response:", response)
