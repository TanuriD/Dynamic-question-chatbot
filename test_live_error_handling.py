#!/usr/bin/env python3
"""
Test script to simulate the exact JSON error and verify error handling
"""

import requests
import json
import time

def test_chatbot_error_handling():
    """Test the chatbot with simulated error scenarios"""
    
    print("🧪 CHATBOT ERROR HANDLING TEST")
    print("=" * 50)
    
    base_url = "http://localhost:8081"
    
    # Test 1: Initialize session
    print("\n📋 Test 1: Initialize session")
    try:
        init_response = requests.post(f"{base_url}/init", json={"phone": "011861547"})
        print(f"   Status: {init_response.status_code}")
        
        if init_response.status_code == 200:
            session_data = init_response.json()
            session_id = session_data.get("session_id")
            print(f"   Session ID: {session_id}")
            print(f"   District: {session_data.get('district')}")
            print(f"   Weather: {session_data.get('weather')}")
            
            if session_id:
                # Test 2: Send a message that might trigger Ollama error
                print(f"\n📋 Test 2: Send message (might trigger error)")
                chat_response = requests.post(f"{base_url}/chat", json={
                    "session_id": session_id,
                    "message": "hello"
                })
                print(f"   Status: {chat_response.status_code}")
                
                if chat_response.status_code == 200:
                    chat_data = chat_response.json()
                    print(f"   Response: {chat_data}")
                    
                    # Check if it's a final response or regular response
                    if "final" in chat_data:
                        print(f"   ✅ Got final response: {chat_data['final']}")
                    elif "response" in chat_data:
                        print(f"   ✅ Got regular response: {chat_data['response']}")
                    else:
                        print(f"   ⚠️ Unexpected response format: {chat_data}")
                else:
                    print(f"   ❌ Chat request failed: {chat_response.text}")
            else:
                print("   ❌ No session ID received")
        else:
            print(f"   ❌ Init request failed: {init_response.text}")
            
    except Exception as e:
        print(f"   ❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 If you see '✅ Got regular response' above, error handling is working!")
    print("🎯 If you see '❌' messages, there might be an issue to investigate.")

if __name__ == "__main__":
    test_chatbot_error_handling()
