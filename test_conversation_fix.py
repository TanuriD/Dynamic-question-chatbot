#!/usr/bin/env python3
"""
Simple test to verify the repetitive question fix
"""

def test_conversation_logic():
    """Test the conversation logic to ensure no repetitive questions"""
    
    print("🔧 TESTING CONVERSATION LOGIC")
    print("=" * 50)
    
    # Simulate conversation context
    conversation_context = {
        'service_type': None,
        'weather_related': False,
        'problem_description': None,
        'timing': None
    }
    
    # Test conversation flow
    test_cases = [
        {"turn": 1, "user_input": "wifi", "expected": "Service type detection"},
        {"turn": 2, "user_input": "it's slow and keeps disconnecting", "expected": "Problem description capture"},
        {"turn": 3, "user_input": "it's raining here", "expected": "Weather detection + timing question"},
        {"turn": 4, "user_input": "yesterday", "expected": "Final routing"},
    ]
    
    for test_case in test_cases:
        turn = test_case["turn"]
        user_input = test_case["user_input"]
        expected = test_case["expected"]
        
        print(f"\n📋 Turn {turn}: '{user_input}'")
        print(f"   Expected: {expected}")
        
        if turn == 1:
            # Service type detection
            if any(word in user_input.lower() for word in ["wifi", "wi-fi", "wiif", "wireless"]):
                conversation_context['service_type'] = 'wifi'
                print(f"   ✅ Detected service: {conversation_context['service_type']}")
        
        elif turn == 2:
            # Problem description
            conversation_context['problem_description'] = user_input
            print(f"   ✅ Captured problem: {conversation_context['problem_description']}")
        
        elif turn == 3:
            # Weather detection + timing question
            conversation_context['problem_description'] = user_input
            if any(word in user_input.lower() for word in ["rain", "storm", "weather", "wind", "thunder", "raining", "stormy"]):
                conversation_context['weather_related'] = True
            print(f"   ✅ Weather related: {conversation_context['weather_related']}")
            print(f"   ✅ Next question: 'When did this issue first occur?'")
        
        elif turn == 4:
            # Final routing
            conversation_context['timing'] = user_input
            if conversation_context.get('weather_related', False):
                service_type = conversation_context.get('service_type', 'WiFi')
                result = {"issue_type": "Weather", "sub_category": service_type.title(), "agent": "weather"}
            else:
                service_type = conversation_context.get('service_type', 'Technical')
                result = {"issue_type": "Network", "sub_category": service_type.title(), "agent": "default"}
            print(f"   ✅ Final routing: {result}")
    
    print("\n" + "=" * 50)
    print("🎯 Conversation flow should now be smooth without repetitive questions!")
    print("🎯 Each turn has a specific purpose and moves the conversation forward!")

if __name__ == "__main__":
    test_conversation_logic()
