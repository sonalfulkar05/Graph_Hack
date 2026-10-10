
from falkordb import FalkorDB

# Connect to FalkorDB
db = FalkorDB(host="localhost", port=6379)

# Select our graph
graph = db.select_graph("LearningGraph")

# Create a user node
graph.query("""
CREATE (u:User {name: 'Rahul', age: 22})
RETURN u
""")

print("My first node was created!")

# Find the user
result = graph.query("""
MATCH (u:User {name: 'Rahul'})
RETURN u.name, u.age
""")

for record in result.result_set:
    print(record)
