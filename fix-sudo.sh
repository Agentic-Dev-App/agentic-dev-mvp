#!/bin/bash
# Script to fix sudo permissions for justin user on server
# Run this ON THE SERVER as root or with sudo access

echo "🔧 Fixing sudo permissions for CI/CD..."
echo ""
echo "This script needs to be run ON THE SERVER with root access."
echo "Copy and paste these commands on the server:"
echo ""
echo "# Option 1: Add justin to docker group (recommended)"
echo "sudo usermod -aG docker justin"
echo "# Then logout and login again for changes to take effect"
echo ""
echo "# Option 2: Allow passwordless sudo for docker commands only"
echo "echo 'justin ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose' | sudo tee /etc/sudoers.d/justin-docker"
echo ""
echo "# Option 3: Allow passwordless sudo for all commands (less secure)"
echo "echo 'justin ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/justin"
echo ""
echo "After running one of these options, the CI/CD should work!"