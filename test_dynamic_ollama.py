#!/usr/bin/env python3
"""
Test script to verify dynamic Ollama conversation (like chatbot_member3.py)
"""

import requests
import json

BASE_URL = "http://localhost:8082"

def test_dynamic_ollama_conversation():
    print("\n🚀 TESTING DYNAMIC OLLAMA CONVERSATION")
    print("=" * 50)
    print("🎯 This should now be DYNAMIC like chatbot_member3.py template!")
    print("🎯 No more rule-based fallback - pure Ollama intelligence!")
    
    session_id = None
    try:
        # 1. Initialize session
        init_payload = {"phone": "011861547"}
        init_res = requests.post(f"{BASE_URL}/init", json=init_payload)
        init_res.raise_for_status()
        init_data = init_res.json()
        session_id = init_data["session_id"]
        print(f"\n📋 Session initialized:")
        print(f"   🏢 District: {init_data['district']}")
        print(f"   🌤️ Weather: {init_data['weather']}")
        print(f"   🤖 First Question: {init_data['first_question']}")

        # 2. Test dynamic conversation
        test_messages = [
            "internet",
            "my internet is very slow and keeps disconnecting",
            "it started yesterday when it was raining heavily"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📋 Turn {i}: '{message}'")
            
            chat_payload = {"session_id": session_id, "message": message}
            chat_res = requests.post(f"{BASE_URL}/chat", json=chat_payload)
            chat_res.raise_for_status()
            chat_data = chat_res.json()
            
            if chat_data.get('final'):
                print(f"   🎯 FINAL ROUTING: {chat_data['final']}")
                print(f"   ✅ Dynamic conversation completed!")
                break
            elif chat_data.get('response'):
                print(f"   🤖 Bot: '{chat_data['response']}'")
                print(f"   ✅ Dynamic response received!")
            else:
                print(f"   ❌ Unexpected response: {chat_data}")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Test failed with exception: {e}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    finally:
        print("\n" + "=" * 50)
        print("🎯 DYNAMIC OLLAMA CONVERSATION TEST COMPLETE!")
        print("🎯 Should be intelligent and contextual like chatbot_member3.py!")

if __name__ == "__main__":
    test_dynamic_ollama_conversation()

