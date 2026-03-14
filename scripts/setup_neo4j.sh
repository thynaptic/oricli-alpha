#!/bin/bash
# Oricli-Alpha: Setup Neo4j for Local Knowledge Graph
# Requires Docker and Docker Compose

echo "--- Oricli-Alpha: Initializing Neo4j Infrastructure ---"

# 1. Pull the official Neo4j image
docker pull neo4j:latest

# 2. Check if already running
if [ $(docker ps -q -f name=oricli-neo4j) ]; then
    echo "oricli-neo4j is already running."
else
    # 3. Start Neo4j in Docker with persistence
    echo "Starting Neo4j Docker container..."
    docker run \
        --name oricli-neo4j \
        -p 7474:7474 -p 7687:7687 \
        -d \
        -v $HOME/neo4j/data:/data \
        -v $HOME/neo4j/logs:/logs \
        -v $HOME/neo4j/import:/var/lib/neo4j/import \
        -v $HOME/neo4j/plugins:/plugins \
        --env NEO4J_AUTH=neo4j/password \
        neo4j:latest
fi

# 4. Wait for it to be ready
echo "Waiting for Neo4j to stabilize..."
sleep 5

# 5. Check logs for success
docker logs oricli-neo4j | tail -n 10

echo "--- Neo4j setup complete ---"
echo "URI: bolt://localhost:7687"
echo "User: neo4j"
echo "Password: password"
echo "Update your .env or export NEO4J_URI/NEO4J_PASSWORD to use this backend."
