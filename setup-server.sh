#!/bin/bash
# Server setup script - run this on your server as justin user

echo "🔧 Setting up agenticdev.app server..."

# Create .env file if it doesn't exist
if [ ! -f /home/justin/.env ]; then
  echo "📝 Creating .env file..."
  cat > /home/justin/.env << 'EOF'
# Lightning Network (Alby) - Required for existing payment system
ALBY_ACCESS_TOKEN=your_alby_token_here
ALBY_WEBHOOK_SECRET=your_webhook_secret_here

# AI API Keys - At least one required for recipe extraction
ANTHROPIC_API_KEY=your_anthropic_key_here
# OPENAI_API_KEY=your_openai_key_here  # Optional alternative

# Stripe (for future payment integration)
# STRIPE_SECRET_KEY=your_stripe_key_here
# STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
EOF
  echo "⚠️  Please edit /home/justin/.env and add your API keys"
else
  echo "✅ .env file already exists"
fi

# Ensure justin is in docker group
if ! groups justin | grep -q docker; then
  echo "Adding justin to docker group..."
  sudo usermod -aG docker justin
  echo "⚠️  You may need to log out and back in for docker permissions to take effect"
fi

# Create data directory
if [ ! -d /data ]; then
  echo "Creating /data directory..."
  sudo mkdir -p /data
  sudo chown justin:justin /data
else
  echo "✅ /data directory exists"
fi

# Test Docker access
echo "Testing Docker access..."
if docker ps >/dev/null 2>&1; then
  echo "✅ Docker access working without sudo"
else
  if sudo docker ps >/dev/null 2>&1; then
    echo "⚠️  Docker requires sudo. You may need to re-login for group changes to take effect"
  else
    echo "❌ Docker not accessible. Please install Docker first"
    exit 1
  fi
fi

# Check if container is already running
if sudo docker ps | grep -q agenticdev-app; then
  echo "📦 Container 'agenticdev-app' is currently running"
  read -p "Do you want to restart it with the latest image? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Restarting container..."
    sudo docker stop agenticdev-app
    sudo docker rm agenticdev-app
  fi
fi

echo ""
echo "✅ Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit /home/justin/.env and add your API keys"
echo "2. Run the deployment from your local machine:"
echo "   ./deploy.sh"
echo "3. Or push to GitHub to trigger automatic deployment"
echo ""
echo "To check container status:"
echo "  sudo docker ps"
echo "  sudo docker logs agenticdev-app"