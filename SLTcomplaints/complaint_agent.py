# complaint_agent.py

import csv
import datetime

# 1️⃣ Dummy complaints (for testing)
dummy_complaint1 = {
    "district": "Colombo",
    "weather": "Rainy",
    "issue_type": "Weather",
    "sub_category": "WiFi"
}

dummy_complaint2 = {
    "district": "Galle",
    "weather": "Stormy",
    "issue_type": "Weather",
    "sub_category": "TV"
}

dummy_complaint3 = {
    "district": "Kandy",
    "weather": "Sunny",
    "issue_type": "Default",
    "sub_category": "Billing"
}

dummy_complaint4 = {
    "district": "Matara",
    "weather": "Sunny",
    "issue_type": "Default",
    "sub_category": "Installation"
}

# 2️⃣ Routing function (optional: by sub-category)
def route_complaint(complaint):
    if complaint["issue_type"] == "Weather":
        # Optional advanced routing by sub-category
        if complaint["sub_category"] == "WiFi":
            agent = "Weather WiFi Agent"
        elif complaint["sub_category"] == "Landline":
            agent = "Weather Landline Agent"
        elif complaint["sub_category"] == "TV":
            agent = "Weather TV Agent"
        else:
            agent = "Weather General Agent"
    else:
        # Default issues go to one agent
        agent = "Default Solution Agent"
    print(f"Redirecting {complaint['sub_category']} issue to {agent}…")
    return agent

# 3️⃣ Logging function
def log_complaint(complaint, agent):
    with open("complaints.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            complaint["district"],
            complaint["weather"],
            complaint["issue_type"],
            complaint["sub_category"],
            datetime.datetime.now(),
            agent
        ])

# 4️⃣ Combined handler
def handle_complaint(complaint):
    agent = route_complaint(complaint)
    log_complaint(complaint, agent)

# 5️⃣ Test with dummy complaints
for dummy in [dummy_complaint1, dummy_complaint2, dummy_complaint3, dummy_complaint4]:
    handle_complaint(dummy)

# 6️⃣ View logs
def view_logs():
    print("\n--- Logged Complaints ---")
    with open("complaints.csv", "r") as file:
        reader = csv.reader(file)
        for row in reader:
            print(row)

# Call it to display the logs
view_logs()
