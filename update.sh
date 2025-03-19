#!/bin/bash

# Auto-updater for Media Processing Notification System
# This script pulls the latest version from GitHub while preserving user configurations

set -e  # Exit on error

# Configuration
REPO_URL="https://github.com/username/media-notification-system.git"
BRANCH="main"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
CONFIG_FILES=(".env" "media_tracker.db")
SERVICE_NAME="media-notification.service"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Media Processing Notification System Updater${NC}"
echo "Starting update process..."

# Check if running as root when trying to restart service
if [[ "$1" == "--restart-service" ]] && [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: You need to run with sudo to restart the service.${NC}"
    echo "Try: sudo $0 --restart-service"
    exit 1
fi

# Check if Git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: Git is not installed. Please install Git and try again.${NC}"
    echo "On Ubuntu/Debian: sudo apt-get install git"
    exit 1
fi

# Check if this is a Git repository
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Git repository.${NC}"
    read -p "Would you like to initialize it as one? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git init
        git remote add origin $REPO_URL
    else
        echo "Update canceled. To update manually, download the latest release from:"
        echo "$REPO_URL"
        exit 1
    fi
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo "Creating backup in $BACKUP_DIR"

# Backup user configuration files
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Backing up $file"
        cp "$file" "$BACKUP_DIR/"
    fi
done

# Backup entire codebase (excluding backups, venv, and large directories)
echo "Backing up current codebase..."
tar --exclude="./venv" --exclude="./backups" --exclude="./data/*.log" -czf "$BACKUP_DIR/codebase.tar.gz" .

# Get the current commit hash before update
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# Fetch latest code
echo "Fetching latest updates from GitHub..."
git fetch origin $BRANCH

# Check if there are updates available
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}Already up-to-date!${NC}"
    exit 0
fi

# Pull latest code
echo "Updating to latest version..."
git pull origin $BRANCH

# Restore configuration files
echo "Restoring user configuration..."
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$BACKUP_DIR/$file" ]; then
        echo "Restoring $file"
        cp "$BACKUP_DIR/$file" .
    fi
done

# Check for new requirements and install them
if [ -f "requirements.txt" ] && [ -d "venv" ]; then
    echo "Updating Python dependencies..."
    source venv/bin/activate
    pip install --upgrade -r requirements.txt
    deactivate
fi

# Check for database changes and apply migrations if needed
if [ -f "migrate_db.py" ]; then
    echo "Checking for database migrations..."
    source venv/bin/activate
    python migrate_db.py
    deactivate
fi

# Restart service if installed and requested
if [[ "$1" == "--restart-service" ]]; then
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "Restarting service..."
        systemctl restart $SERVICE_NAME
        echo "Service restarted."
    else
        echo -e "${YELLOW}Service $SERVICE_NAME is not active, not restarting.${NC}"
    fi
fi

# Get the new commit hash after update
NEW_COMMIT=$(git rev-parse HEAD)

echo -e "${GREEN}Update complete!${NC}"
echo "Updated from commit $CURRENT_COMMIT to $NEW_COMMIT"
echo "Backup stored in $BACKUP_DIR"

if [[ "$1" != "--restart-service" ]]; then
    echo -e "${YELLOW}Note: You may need to restart the service for changes to take effect.${NC}"
    echo "To restart the service: sudo systemctl restart $SERVICE_NAME"
fi

echo -e "${GREEN}Thank you for using Media Processing Notification System!${NC}"
