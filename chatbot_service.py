from flask import Flask, request, jsonify
from chatbot_core import create_chatbot

# Initialize Flask app
app = Flask(__name__)

# Create chatbot and memory
conversation, memory = create_chatbot()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    district = data.get("district", None)
    weather = data.get("weather", None)

    # Add context if district and weather are provided
    if district and weather:
        context_msg = f"(System context: The user is in {district} where the weather is {weather}.)"
        user_message = context_msg + " " + user_message

    # Run the message through the chatbot
    response = conversation.run(input=user_message)

    # Check if model produced final JSON
    if response.strip().startswith("{"):
        try:
            result = eval(response)
            memory.clear()  # clear memory for next conversation
            return jsonify(result)
        except Exception:
            pass  # continue chatting if not valid JSON

    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(port=8503, debug=True)
