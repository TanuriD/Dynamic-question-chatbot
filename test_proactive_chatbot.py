#!/usr/bin/env python3
"""
Test script to verify proactive chatbot behavior
"""

import requests
import json
import time

def test_proactive_chatbot():
    """Test the proactive chatbot behavior"""
    
    print("🚀 PROACTIVE CHATBOT TEST")
    print("=" * 50)
    
    base_url = "http://localhost:8082"
    
    # Test 1: Initialize session and check first question
    print("\n📋 Test 1: Initialize session with proactive first question")
    try:
        init_response = requests.post(f"{base_url}/init", json={"phone": "011861547"})
        print(f"   Status: {init_response.status_code}")
        
        if init_response.status_code == 200:
            session_data = init_response.json()
            session_id = session_data.get("session_id")
            print(f"   Session ID: {session_id}")
            print(f"   District: {session_data.get('district')}")
            print(f"   Weather: {session_data.get('weather')}")
            print(f"   First Question: {session_data.get('first_question')}")
            
            if session_id and session_data.get('first_question'):
                print(f"   ✅ Proactive first question generated!")
                
                # Test 2: Customer responds directly to the question
                print(f"\n📋 Test 2: Customer responds to proactive question")
                
                chat_response = requests.post(f"{base_url}/chat", json={
                    "session_id": session_id,
                    "message": "wifi"
                })
                print(f"   Status: {chat_response.status_code}")
                
                if chat_response.status_code == 200:
                    chat_data = chat_response.json()
                    print(f"   Response: {chat_data.get('response', 'No response')}")
                    
                    # Test 3: Continue conversation
                    print(f"\n📋 Test 3: Continue dynamic conversation")
                    
                    chat_response2 = requests.post(f"{base_url}/chat", json={
                        "session_id": session_id,
                        "message": "it's slow and keeps disconnecting"
                    })
                    print(f"   Status: {chat_response2.status_code}")
                    
                    if chat_response2.status_code == 200:
                        chat_data2 = chat_response2.json()
                        print(f"   Response: {chat_data2.get('response', 'No response')}")
                        
                        # Check if we got a final response
                        if "final" in chat_data2:
                            print(f"   ✅ Final routing: {chat_data2['final']}")
                        else:
                            print(f"   ✅ Dynamic conversation continues...")
                    else:
                        print(f"   ❌ Second chat request failed: {chat_response2.text}")
                else:
                    print(f"   ❌ First chat request failed: {chat_response.text}")
            else:
                print("   ❌ No session ID or first question received")
        else:
            print(f"   ❌ Init request failed: {init_response.text}")
            
    except Exception as e:
        print(f"   ❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 The chatbot should now be PROACTIVE!")
    print("🎯 No more waiting for 'hello' - starts asking immediately!")
    print("🎯 Weather-aware first questions based on detected conditions!")

if __name__ == "__main__":
    test_proactive_chatbot()
