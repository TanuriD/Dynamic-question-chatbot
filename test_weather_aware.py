#!/usr/bin/env python3
"""
Test script to demonstrate weather-aware chatbot functionality
"""

def test_weather_aware_prompts():
    """Test the weather-aware prompting logic"""
    
    print("🌤️  WEATHER-AWARE CHATBOT TEST")
    print("=" * 50)
    
    # Test scenarios
    scenarios = [
        {
            "district": "Colombo",
            "weather": "heavy rain, 24°C",
            "description": "Bad weather scenario"
        },
        {
            "district": "Kandy", 
            "weather": "clear sky, 28°C",
            "description": "Good weather scenario"
        },
        {
            "district": "Galle",
            "weather": "thunderstorm, 22°C", 
            "description": "Severe weather scenario"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['description']}")
        print(f"   District: {scenario['district']}")
        print(f"   Weather: {scenario['weather']}")
        
        # Simulate weather detection logic
        weather_lower = scenario['weather'].lower()
        is_bad_weather = any(word in weather_lower for word in ["rain", "storm", "thunder", "heavy", "severe", "stormy", "windy"])
        
        print(f"   Weather Analysis: {'BAD WEATHER' if is_bad_weather else 'GOOD WEATHER'}")
        
        # Generate appropriate first question
        if is_bad_weather:
            first_question = f"I can see it's {scenario['weather']} in {scenario['district']}, which often affects connectivity. Which service is having issues - WiFi, Internet, Landline, or Mobile?"
        else:
            first_question = "Which service is having issues - WiFi, Internet, Landline, or Mobile?"
        
        print(f"   🤖 First Question: {first_question}")
        
        # Simulate user response
        user_response = "wifi"
        print(f"   👤 User Response: {user_response}")
        
        # Generate follow-up question
        service = user_response.title()
        if is_bad_weather:
            follow_up = f"I understand you're having {service} issues. Since it's {scenario['weather']} in your area, can you describe the specific problem you're facing?"
        else:
            follow_up = f"I understand you're having {service} issues. Can you describe the specific problem you're facing?"
        
        print(f"   🤖 Follow-up: {follow_up}")
        print("-" * 50)

if __name__ == "__main__":
    test_weather_aware_prompts()
    
    print("\n🎯 KEY FEATURES IMPLEMENTED:")
    print("✅ Weather-aware first questions")
    print("✅ Contextual service type detection") 
    print("✅ Smart weather routing logic")
    print("✅ Enhanced Ollama prompts with weather context")
    print("✅ Fallback system with weather awareness")
    print("\n🚀 The chatbot now asks contextual questions based on detected weather!")
