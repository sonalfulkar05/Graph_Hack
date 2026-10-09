events = [
    {
        "user": "Asha",
        "device": "Laptop-01",
        "ip": "192.168.1.10",
        "failed_attempts": 1
    },
    {
        "user": "Rahul",
        "device": "Laptop-02",
        "ip": "192.168.1.20",
        "failed_attempts": 5
    },
    {
        "user": "Priya",
        "device": "Laptop-01",
        "ip": "192.168.1.10",
        "failed_attempts": 2
    },
    {
        "user": "Neha",
        "failed_attempts": 3
    }
]

for event in events:
    
    if event["device"] == "Laptop-01":
        print("Alert: Multiple failed login attempts detected on Laptop-01")
    print("User:", event["user"])
    print("Device:", event["device"])
    print("IP:", event["ip"])

    if event["failed_attempts"] >= 5:
        print("Status: Investigate")
    else:
        print("Status: No alert from this rule")

    print("-" * 25)