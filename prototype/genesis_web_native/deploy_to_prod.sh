#!/bin/bash
echo "🚀 Deploying Dev to Prod..."
sudo cp index.html /var/www/infero.net/genesis/index.html
cp relay_server.py /home/ubuntu/pob_server/relay_service/relay_server.py
echo "🔄 Restarting Prod Relay Server (Port 8080)..."
cd /home/ubuntu/pob_server/relay_service
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
export PORT=8080
export HTML_PATH="/var/www/infero.net/genesis/index.html"
nohup python3 relay_server.py > relay.log 2>&1 &
echo "✅ Prod Deployment Complete!"
