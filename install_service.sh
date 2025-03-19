#!/bin/bash

# This script installs the Media Processing Notification System as a systemd service

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo"
  exit 1
fi

# Get the current directory
INSTALL_DIR=$(pwd)
USER=$(logname)

# Create systemd service file
cat > /etc/systemd/system/media-notification.service << EOF
[Unit]
Description=Media Processing Notification System
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start service
systemctl daemon-reload
systemctl enable media-notification.service
systemctl start media-notification.service

echo "Service installed and started!"
echo "Check service status with: systemctl status media-notification.service"
echo "View logs with: journalctl -u media-notification.service"
