#!/bin/bash
# Script to verify SSH setup for CI/CD

echo "🔍 Verifying SSH Setup for CI/CD..."
echo ""

# Check if we can connect from local machine
echo "1️⃣ Testing SSH from your local machine to server..."
if ssh -o ConnectTimeout=5 justin@147.182.236.230 "echo 'Local SSH: ✅ Connected successfully'" 2>/dev/null; then
  echo "   Local connection works!"
else
  echo "   ❌ Cannot connect from local machine"
  echo "   Make sure your local SSH key is added to the server"
fi

echo ""
echo "2️⃣ Checking your current SSH key..."
if [ -f ~/.ssh/id_rsa.pub ]; then
  echo "   Your public key is:"
  cat ~/.ssh/id_rsa.pub
  echo ""
  echo "   This key should be in /home/justin/.ssh/authorized_keys on the server"
elif [ -f ~/.ssh/id_ed25519.pub ]; then
  echo "   Your public key is:"
  cat ~/.ssh/id_ed25519.pub
  echo ""
  echo "   This key should be in /home/justin/.ssh/authorized_keys on the server"
else
  echo "   ❌ No SSH key found locally"
  echo "   Generate one with: ssh-keygen -t ed25519"
fi

echo ""
echo "3️⃣ For GitHub Actions to work:"
echo "   a) The PRIVATE key needs to be in GitHub Secrets as SSH_PRIVATE_KEY"
echo "   b) The PUBLIC key needs to be in server's /home/justin/.ssh/authorized_keys"
echo ""
echo "   To add your private key to GitHub:"
echo "   1. Copy your private key: cat ~/.ssh/id_rsa (or id_ed25519)"
echo "   2. Go to: https://github.com/Agentic-Dev-App/agentic-dev-mvp/settings/secrets/actions"
echo "   3. Update SSH_PRIVATE_KEY with the ENTIRE private key including:"
echo "      -----BEGIN RSA PRIVATE KEY----- (or -----BEGIN OPENSSH PRIVATE KEY-----)"
echo "      [key content]"
echo "      -----END RSA PRIVATE KEY----- (or -----END OPENSSH PRIVATE KEY-----)"
echo ""
echo "4️⃣ To add public key to server (if not already done):"
echo "   ssh-copy-id justin@147.182.236.230"
echo "   OR manually:"
echo "   ssh justin@147.182.236.230 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys' < ~/.ssh/id_rsa.pub"