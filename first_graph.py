from falkordb import FalkorDB

db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("CyberSecurity")

# Create or reuse the users, device and IP address
graph.query("""
MERGE (asha:User {name: 'Asha'})
MERGE (rahul:User {name: 'Rahul'})
MERGE (d:Device {name: 'Laptop-01'})
MERGE (ip:IPAddress {address: '192.168.1.10'})

MERGE (asha)-[:USES]->(d)
MERGE (rahul)-[:USES]->(d)
MERGE (d)-[:CONNECTED_TO]->(ip)
""")

print("Security graph updated!")

# Find users who share a device
result = graph.query("""
MATCH (u1:User)-[:USES]->(d:Device)<-[:USES]-(u2:User)
WHERE u1.name < u2.name
RETURN u1.name, u2.name, d.name
""")

print("\nUsers sharing a device:")

for record in result.result_set:
    print(record)