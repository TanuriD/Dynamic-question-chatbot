# -------------------------------
# 🌤️ Weather App using OpenWeather API
# Language: Python 3
# -------------------------------

import requests

# Your OpenWeather API key
API_KEY = "f72d16875c109d22d0c9119ed9d5c288"  # 🔹 Replace with your own API key

def get_weather(city_name):
    """Fetch weather data for a given city using OpenWeather API."""
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    # Parameters for the API request
    params = {
        'q': city_name,
        'appid': API_KEY,
        'units': 'metric'  # Use 'imperial' for Fahrenheit
    }

    try:
        # Send a GET request to OpenWeather API
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an error for bad status codes

        # Convert the response to JSON
        data = response.json()

        # Extract and display weather information
        print("\n🌍 Weather Details for:", data['name'])
        print("--------------------------------------------------")
        print("Weather:", data['weather'][0]['description'].capitalize())
        print("Temperature:", data['main']['temp'], "°C")
        print("Feels Like:", data['main']['feels_like'], "°C")
        print("Humidity:", data['main']['humidity'], "%")
        print("Pressure:", data['main']['pressure'], "hPa")
        print("Wind Speed:", data['wind']['speed'], "m/s")
        print("--------------------------------------------------")

    except requests.exceptions.HTTPError as errh:
        print("❌ HTTP Error:", errh)
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error. Check your internet connection.")
    except requests.exceptions.Timeout:
        print("⏰ Request Timed Out.")
    except requests.exceptions.RequestException as e:
        print("⚠️ Something went wrong:", e)
    except KeyError:
        print("⚠️ Invalid city name or missing data. Try again!")

# -------------------------------
# 🏁 Main Program Starts Here
# -------------------------------
if __name__ == "__main__":
    print("🌦️ Welcome to the Python Weather App 🌦️")
    print("-------------------------------------------")
    city = input("Enter a city name: ").strip()
    get_weather(city)
