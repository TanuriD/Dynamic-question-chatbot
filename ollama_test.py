import subprocess
import json

# Simple function to run ollama from Python
def ask_ollama(prompt):
    process = subprocess.Popen(
        ["ollama", "run", "llama3"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    output, error = process.communicate(input=prompt)
    return output

if __name__ == "__main__":
    response = ask_ollama("Explain how AI chatbots work in simple terms.")
    print("Ollama says:\n", response)

