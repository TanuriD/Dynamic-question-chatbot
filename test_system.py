#!/usr/bin/env python3
"""
Test script for SLT-CHATBOT system
"""
import requests
import json
import time

def test_system():
    base_url = "http://localhost:8080"
    
    print("🧪 Testing SLT-CHATBOT System")
    print("=" * 50)
    
    # Test 1: Initialize session with Colombo landline
    print("\n1️⃣ Testing district prediction and weather lookup...")
    try:
        response = requests.post(f"{base_url}/init", json={"phone": "011861547"})
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session created: {data['session_id']}")
            print(f"✅ District detected: {data['district']}")
            print(f"✅ Weather: {data['weather']}")
            session_id = data['session_id']
        else:
            print(f"❌ Init failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure the server is running: python app.py")
        return
    
    # Test 2: Chat interaction
    print("\n2️⃣ Testing chat interaction...")
    messages = [
        "I'm having internet issues",
        "Yes, it's raining heavily",
        "My WiFi keeps disconnecting",
        "Started this morning",
        "It's been happening all day"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\n   Turn {i}: User says: '{message}'")
        try:
            response = requests.post(f"{base_url}/chat", json={
                "session_id": session_id,
                "message": message
            })
            if response.status_code == 200:
                data = response.json()
                if "final" in data:
                    print(f"   ✅ Final result: {json.dumps(data['final'], indent=2)}")
                    break
                elif "response" in data:
                    print(f"   ✅ Bot responds: '{data['response']}'")
                else:
                    print(f"   ❌ Unexpected response: {data}")
            else:
                print(f"   ❌ Chat failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Chat error: {e}")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    test_system()
