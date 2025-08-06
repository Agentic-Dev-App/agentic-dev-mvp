#!/bin/bash
# Manual deployment script for testing

echo "🚀 Starting deployment to agenticdev.app..."

# Build Docker image locally
echo "📦 Building Docker image..."
docker build -t agenticdev:latest .

# Save image to file
echo "💾 Saving Docker image..."
docker save agenticdev:latest | gzip > /tmp/agenticdev.tar.gz

# Copy to server
echo "📤 Copying to server..."
scp /tmp/agenticdev.tar.gz justin@147.182.236.230:/tmp/

# Deploy on server
echo "🔄 Deploying on server..."
ssh justin@147.182.236.230 << 'ENDSSH'
  # Load the new image
  echo "Loading Docker image..."
  sudo docker load < /tmp/agenticdev.tar.gz
  
  # Stop old container
  echo "Stopping old container..."
  sudo docker stop agenticdev-app 2>/dev/null || true
  sudo docker rm agenticdev-app 2>/dev/null || true
  
  # Ensure directories and env file exist
  sudo mkdir -p /data
  sudo chown justin:justin /data
  
  # Check for env file
  if [ ! -f /home/justin/.env ]; then
    echo "⚠️  Warning: /home/justin/.env not found!"
    echo "Please create it with:"
    echo "  ALBY_ACCESS_TOKEN=your_token"
    echo "  ALBY_WEBHOOK_SECRET=your_secret"
    echo "  ANTHROPIC_API_KEY=your_key"
    exit 1
  fi
  
  # Start new container
  echo "Starting new container..."
  sudo docker run -d \
    --name agenticdev-app \
    --restart unless-stopped \
    -p 80:80 \
    -v /data:/data \
    --env-file /home/justin/.env \
    agenticdev:latest
  
  # Clean up
  rm /tmp/agenticdev.tar.gz
  sudo docker image prune -f
  
  # Check status
  sleep 3
  if sudo docker ps | grep -q agenticdev-app; then
    echo "✅ Container is running!"
    echo "Checking health endpoint..."
    if curl -f http://localhost/docs 2>/dev/null; then
      echo "✅ API is responding!"
    else
      echo "⚠️  API not responding yet, checking logs..."
      sudo docker logs agenticdev-app --tail 20
    fi
  else
    echo "❌ Container failed to start!"
    sudo docker logs agenticdev-app
    exit 1
  fi
ENDSSH

# Clean up local temp file
rm /tmp/agenticdev.tar.gz

echo "✨ Deployment complete!"
echo "🌐 Visit https://agenticdev.app/docs to see the API"