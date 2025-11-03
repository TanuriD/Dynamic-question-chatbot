import json
from datetime import datetime
from langchain_ollama import OllamaLLM

# Connect to LLaMA 3
llm = OllamaLLM(model="llama3")

def classify_and_log(issue_text, district):
    """
    Classifies an issue into main category and sub-category,
    generates a summary, assigns a forward note, and logs the complaint.
    """

    # Strong prompt with examples
    prompt = f"""
You are a complaint-handling assistant. Classify the issue into main category and sub-category.

Main categories: Weather, Default
Sub-categories: WiFi, Broadband, Landline, TV/IPTV, Mobile network, Billing, Installation/Setup, Company issues

Examples:
1. Issue: "My WiFi is not working during the rain."
   JSON: {{"main_category": "Weather", "sub_category": "WiFi", "summary": "WiFi not working due to rain.", "forward_note": "Forwarded to Weather Solution Agent"}}

2. Issue: "I cannot set up my new broadband connection."
   JSON: {{"main_category": "Default", "sub_category": "Installation/Setup", "summary": "Customer unable to set up broadband.", "forward_note": "Forwarded to Default Solution Agent"}}

Now classify this issue:

Issue: {issue_text}

Return JSON ONLY, following the above format.
"""

    # Get LLM response
    result_text = llm.invoke(prompt).strip()

    # Sometimes LLM adds extra text, extract JSON
    try:
        # Attempt to parse directly
        result_json = json.loads(result_text)
    except json.JSONDecodeError:
        # fallback: try to extract JSON substring
        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        try:
            result_json = json.loads(result_text[start:end])
        except:
            # default fallback
            result_json = {
                "main_category": "Unknown",
                "sub_category": "Unknown",
                "summary": "Unable to classify precisely.",
                "forward_note": "Unable to forward automatically."
            }

    # Add logging info
    result_json["log"] = {
        "district": district,
        "predicted_main_category": result_json.get("main_category", "Unknown"),
        "predicted_sub_category": result_json.get("sub_category", "Unknown"),
        "timestamp": datetime.now().isoformat()
    }

    # Add role for member 4 agent
    result_json["role"] = "Specialised Agent"

    return result_json


# Example usage
if __name__ == "__main__":
    issues = [
        {"district": "Colombo", "text": "My WiFi is not working during the rain."},
        {"district": "Kandy", "text": "I cannot set up my new broadband connection."},
        {"district": "Galle", "text": "The TV signal is lost after the storm."},
        {"district": "Jaffna", "text": "My mobile network is very slow."}
    ]

    for issue in issues:
        print("-" * 50)
        classification = classify_and_log(issue["text"], issue["district"])
        print("Issue:", issue["text"])
        print("Classification:", classification)
