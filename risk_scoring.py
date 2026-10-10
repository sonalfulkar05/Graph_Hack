def calculate_risk(event):
    score = 0
    reasons = []

    if event["failed_attempts"] >= 3:
        score += 30
        reasons.append("Multiple failed login attempts")

    if event["unfamiliar_device"]:
        score += 25
        reasons.append("Unfamiliar device")

    if event["unusual_time"]:
        score += 20
        reasons.append("Unusual login time")

    if score >= 50:
        level = "High"
    elif score >= 25:
        level = "Medium"
    else:
        level = "Low"

    return score, level, reasons


event = {
    "user": "Rahul",
    "failed_attempts": 4,
    "unfamiliar_device": True,
    "unusual_time": False
}

score, level, reasons = calculate_risk(event)

print("User:", event["user"])
print("Risk score:", score)
print("Risk level:", level)
print("Reasons:")

for reason in reasons:
    print("-", reason)