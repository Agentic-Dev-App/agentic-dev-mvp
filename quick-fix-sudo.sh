#!/bin/bash
# Quick fix for sudo issue - RUN THIS ON YOUR SERVER

echo "Run these commands ON YOUR SERVER as justin:"
echo ""
echo "ssh justin@147.182.236.230"
echo ""
echo "# Then run (you'll need to enter your password once):"
echo 'echo "justin ALL=(ALL) NOPASSWD: /usr/bin/docker" | sudo tee /etc/sudoers.d/justin-docker'
echo ""
echo "# This allows justin to run docker with sudo but without password"
echo "# Test it works:"
echo "sudo docker ps"
echo ""
echo "# Should work without asking for password"