#!/bin/bash

# Two-Node DStack P2P Demo Cleanup Script

echo "🛑 Stopping Two-Node DStack P2P Demo"

# Stop and remove containers
echo "Stopping Node 1..."
docker-compose -f docker-compose-node1.yml down --remove-orphans

echo "Stopping Node 2..."  
docker-compose -f docker-compose-node2.yml down --remove-orphans

# Optional: Remove images (uncomment if desired)
# echo "Removing Docker images..."
# docker rmi dstack-nft-cluster-dstack-node1 dstack-nft-cluster-dstack-node2 2>/dev/null || true

echo "✅ Demo stopped successfully!"
