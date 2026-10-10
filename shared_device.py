
from falkordb import FalkorDB

db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("CyberSecurity")

# Create two users sharing one device
graph.query("""
MERGE (r:User {name: 'Rahul'})
MERGE (a:User {name: 'Asha'})
MERGE (d:Device {name: 'Laptop-Shared'})
MERGE (r)-[:USES]->(d)
MERGE (a)-[:USES]->(d)
""")

# Find devices used by multiple users
result = graph.query("""
MATCH (u1:User)-[:USES]->(d:Device)<-[:USES]-(u2:User)
WHERE u1.name < u2.name
RETURN u1.name, u2.name, d.name
""")

print("Shared-device investigation:")
for record in result.result_set:
    print(record)
