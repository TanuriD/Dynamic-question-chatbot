#!/usr/bin/env python3
"""
Test script to debug the repetitive question issue
"""

import requests
import json
import time

def test_debug_conversation():
    """Test the conversation with debugging to see what's happening"""
    
    print("🔍 DEBUGGING REPETITIVE QUESTIONS")
    print("=" * 50)
    
    base_url = "http://localhost:8082"
    
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
            print(f"   First Question: {session_data.get('first_question')}")
            
            if session_id:
                # Test 2: First response
                print(f"\n📋 Test 2: First response")
                chat_response = requests.post(f"{base_url}/chat", json={
                    "session_id": session_id,
                    "message": "internet"
                })
                print(f"   Status: {chat_response.status_code}")
                
                if chat_response.status_code == 200:
                    chat_data = chat_response.json()
                    print(f"   Response: {chat_data.get('response', 'No response')}")
                    
                    # Test 3: Second response (this should NOT repeat the same question)
                    print(f"\n📋 Test 3: Second response")
                    chat_response2 = requests.post(f"{base_url}/chat", json={
                        "session_id": session_id,
                        "message": "internet"
                    })
                    print(f"   Status: {chat_response2.status_code}")
                    
                    if chat_response2.status_code == 200:
                        chat_data2 = chat_response2.json()
                        print(f"   Response: {chat_data2.get('response', 'No response')}")
                        
                        # Check if it's repeating the same question
                        if chat_data2.get('response') == chat_data.get('response'):
                            print(f"   ❌ PROBLEM: Same question repeated!")
                        else:
                            print(f"   ✅ Good: Different question asked")
                    else:
                        print(f"   ❌ Second chat request failed: {chat_response2.text}")
                else:
                    print(f"   ❌ First chat request failed: {chat_response.text}")
            else:
                print("   ❌ No session ID received")
        else:
            print(f"   ❌ Init request failed: {init_response.text}")
            
    except Exception as e:
        print(f"   ❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Check the server logs for DEBUG messages to see what's happening!")

if __name__ == "__main__":
    test_debug_conversation()
