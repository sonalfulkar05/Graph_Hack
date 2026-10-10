from falkordb import FalkorDB

db = FalkorDB(host="localhost", port=6379)
graph = db.select_graph("CyberSecurity")

# Create users, devices, and IP addresses
graph.query("""
MERGE (asha:User {name: 'Asha'})
MERGE (rahul:User {name: 'Rahul'})
MERGE (priya:User {name: 'Priya'})

MERGE (laptop1:Device {name: 'Laptop-01'})
MERGE (laptop2:Device {name: 'Laptop-02'})
MERGE (laptop3:Device {name: 'Laptop-03'})

MERGE (ip1:IPAddress {address: '192.168.1.10'})
MERGE (ip2:IPAddress {address: '192.168.1.30'})

MERGE (asha)-[:USES]->(laptop1)
MERGE (rahul)-[:USES]->(laptop2)
MERGE (priya)-[:USES]->(laptop3)

MERGE (laptop1)-[:CONNECTED_TO]->(ip1)
MERGE (laptop2)-[:CONNECTED_TO]->(ip1)
MERGE (laptop3)-[:CONNECTED_TO]->(ip2)
""")

print("Security events added!")

# Find users connected to the same IP address
result = graph.query("""
MATCH (u1:User)-[:USES]->(:Device)-[:CONNECTED_TO]->(ip:IPAddress)
      <-[:CONNECTED_TO]-(:Device)<-[:USES]-(u2:User)
WHERE u1.name < u2.name
RETURN u1.name, u2.name, ip.address
""")

print("\nUsers sharing an IP address:")

for record in result.result_set:
    print(record)