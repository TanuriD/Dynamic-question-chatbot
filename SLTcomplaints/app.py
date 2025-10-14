# app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv
import datetime

app = FastAPI(title="SLT Complaint Handling API")

# ----------------------------
# 1️⃣ Define the complaint model
# ----------------------------
class Complaint(BaseModel):
    district: str
    weather: str = None  # optional for Default issues
    issue_type: str  # "Weather" or "Default"
    sub_category: str

# ----------------------------
# 2️⃣ Routing function
# ----------------------------
def route_complaint(complaint: Complaint):
    if complaint.issue_type == "Weather":
        if complaint.sub_category == "WiFi":
            agent = "Weather WiFi Agent"
        elif complaint.sub_category == "Landline":
            agent = "Weather Landline Agent"
        elif complaint.sub_category == "TV":
            agent = "Weather TV Agent"
        else:
            agent = "Weather General Agent"
    else:
        agent = "Default Solution Agent"
    return agent

# ----------------------------
# 3️⃣ Logging function
# ----------------------------
def log_complaint(complaint: Complaint, agent: str):
    with open("complaints.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            complaint.district,
            complaint.weather if complaint.weather else "",
            complaint.issue_type,
            complaint.sub_category,
            datetime.datetime.now(),
            agent
        ])

# ----------------------------
# 4️⃣ POST endpoint to handle complaints
# ----------------------------
@app.post("/complaints")
def handle_complaint_api(complaint: Complaint):
    try:
        agent = route_complaint(complaint)
        log_complaint(complaint, agent)
        return {"message": f"Complaint routed to {agent}", "agent": agent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------
# 5️⃣ GET endpoint to view all complaints
# ----------------------------
@app.get("/logs")
def view_logs():
    logs = []
    try:
        with open("complaints.csv", "r") as file:
            reader = csv.reader(file)
            for row in reader:
                logs.append({
                    "district": row[0],
                    "weather": row[1],
                    "issue_type": row[2],
                    "sub_category": row[3],
                    "timestamp": row[4],
                    "agent": row[5]
                })
        return {"complaints": logs}
    except FileNotFoundError:
        return {"complaints": []}
