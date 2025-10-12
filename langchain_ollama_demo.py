from langchain_ollama import OllamaLLM

# Load a local model via Ollama
llm = OllamaLLM(model="llama3")

# Send a prompt
response = llm.invoke("Give me 3 uses of AI in telecom services.")

print("Response:\n", response)

