# Media Processing Notification System

A stateless webhook-based system that sends notifications via ntfy when media processing events occur.

## Overview

The system monitors the following workflow:

1. **Media Processing Flow**:
   - Prowlarr locates media files
   - Sonarr/Radarr/Lidarr manage downloads and imports
   - Plex adds the new media to its library
   - Tdarr (optional) performs health checks and transcoding 
   - Tapearr (optional) backs up the processed files

## Features

- Real-time notifications via ntfy
- Stateless design - no database required
- Simple webhook-based integration with minimal impact on services
- Clear process flow visualization in notifications
- Mobile-friendly notifications with condensed metadata
- Comprehensive error reporting
- Optional services can be enabled/disabled via configuration

## Installation

### Prerequisites

- Ubuntu 24.04 or similar Linux distribution
- Python 3.8+ (included in Ubuntu 24.04)
- ntfy account or self-hosted ntfy server
- Prowlarr, Sonarr, Radarr, Lidarr, Plex, and optionally Tdarr and Tapearr instances

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/username/media-notification-system.git
   cd media-notification-system
   ```

2. Create a Python virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy the sample .env file and edit with your configuration:
   ```bash
   cp .env.sample .env
   nano .env
   ```

4. Start the application:
   ```bash
   source venv/bin/activate
   python main.py
   ```

5. (Optional) Install as a system service:
   ```bash
   sudo ./install_service.sh
   ```

## Webhook Configuration

### Prowlarr
- Go to Settings > Connect
- Add a new notification of type "Webhook"
- URL: `http://your-server:8000/webhook/prowlarr`
- Method: POST
- **Required Event Triggers**:
  - ✅ On Release Grab - Be notified when releases are grabbed (essential)
  - ✅ Include Manual Grabs - Be notified when releases are grabbed manually (recommended)
- **Optional Event Triggers**:
  - ⚪ On Health Issue - For monitoring Prowlarr's health status (optional)
  - ⚪ Include Health Warnings - For more detailed health monitoring (optional)
  - ⚪ On Application Update - Be notified when Prowlarr is updated (optional)

### Sonarr
The media management system must be running before adding to Sonarr
- Go to Settings > Connect
- Add a new notification of type "Webhook"
- URL: `http://your-server:8000/webhook/sonarr`
- Method: POST
- **Required Event Triggers**:
  - ✅ On Grab - Be notified when episodes are sent to download client (essential)
  - ✅ On Import - Be notified when episodes are successfully imported (essential)
  - ✅ On Upgrade - Be notified when episodes are upgraded to better quality (essential)
  - ✅ On Episode File Delete - Be notified when episode files are deleted (essential for manual interaction detection)
  - ✅ On Episode File Delete For Upgrade - Be notified when files are deleted for upgrades (essential)
  - ✅ Include Manual Imports - Enable this checkbox to get notified about manual imports (essential)
- **Optional Event Triggers**:
  - ⚪ On Rename - Be notified when episodes are renamed (optional)
  - ⚪ On Series Delete - Be notified when series are deleted (optional)
  - ⚪ On Health Issue - For monitoring Sonarr's health status (optional)
  - ⚪ Include Health Warnings - For more detailed health monitoring (optional)
  - ⚪ On Application Update - Be notified when Sonarr is updated (optional)

### Radarr
The media management system must be running before adding to Radarr
- Go to Settings > Connect
- Add a new notification of type "Webhook"
- URL: `http://your-server:8000/webhook/radarr`
- Method: POST
- **Required Event Triggers**:
  - ✅ On Grab - Be notified when movies are sent to download client (essential)
  - ✅ On Import - Be notified when movies are successfully imported (essential)
  - ✅ On Upgrade - Be notified when movies are upgraded to better quality (essential)
  - ✅ On Movie File Delete - Be notified when movie files are deleted (essential for manual interaction detection)
  - ✅ On Movie File Delete For Upgrade - Be notified when files are deleted for upgrades (essential)
  - ✅ Include Manual Imports - Enable this checkbox to get notified about manual imports (essential)
- **Optional Event Triggers**:
  - ⚪ On Rename - Be notified when movies are renamed (optional)
  - ⚪ On Movie Added - Be notified when movies are added to library (optional)
  - ⚪ On Movie Delete - Be notified when movies are deleted (optional)
  - ⚪ On Health Issue - For monitoring Radarr's health status (optional)
  - ⚪ Include Health Warnings - For more detailed health monitoring (optional)
  - ⚪ On Application Update - Be notified when Radarr is updated (optional)

### Lidarr
The media management system must be running before adding to Lidarr
- Go to Settings > Connect
- Add a new notification of type "Webhook"
- URL: `http://your-server:8000/webhook/lidarr`
- Method: POST
- **Required Event Triggers**:
  - ✅ On Grab - Be notified when releases are sent to download client (essential)
  - ✅ On Release Import - Be notified when albums are successfully imported (essential)
  - ✅ On Upgrade - Be notified when albums are upgraded to better quality (essential)
  - ✅ On Album Delete - Be notified when album files are deleted (essential for manual interaction detection)
  - ✅ On Download Failure - Be notified when downloads fail (essential for error tracking)
  - ✅ On Import Failure - Be notified when imports fail (essential for error tracking)
  - ✅ Include Manual Imports - Enable this checkbox to get notified about manual imports (essential)
- **Optional Event Triggers**:
  - ⚪ On Rename - Be notified when releases are renamed (optional)
  - ⚪ On Artist Add - Be notified when artists are added to library (optional)
  - ⚪ On Artist Delete - Be notified when artists are deleted (optional)
  - ⚪ On Track Retag - Be notified when tracks are retagged (optional)
  - ⚪ On Health Issue - For monitoring Lidarr's health status (optional)
  - ⚪ On Health Restored - Be notified when health issues are resolved (optional)
  - ⚪ On Application Update - Be notified when Lidarr is updated (optional)

### Plex
- Go to Settings > Webhooks
- Add a new webhook
- URL: `http://your-server:8000/webhook/plex`
- **Required Events to Enable**:
  - ✅ "Library" events - Specifically focused on the "library.new" event

### Tdarr/Tapearr
Configure these services with appropriate webhook settings as per your setup.

#### Tdarr Webhook Configuration
If ENABLE_TDARR is set to True in your .env file, Tdarr webhooks should fire at these processing stages:
- When transcoding/health check process starts
- When processing completes successfully
- When an error occurs during processing

Expected JSON payload format:
```json
{
  "status": "started|complete|error",
  "title": "Media Title",
  "file_path": "/path/to/media/file.mp4",
  "media_type": "movie|series|music",  
  "error": "Error message (only required when status is 'error')"
}
```

Configure Tdarr to have a variable for each library that contains either movie|series|music
include that variable in the web request flow

#### Tapearr Webhook Configuration
If ENABLE_TAPEARR is set to True in your .env file, Tapearr webhooks should fire at these backup stages:
- When backup process starts
- When backup completes successfully
- When an error occurs during backup

Expected JSON payload format:
```json
{
  "status": "started|complete|error",
  "title": "Media Title",
  "file_path": "/path/to/media/file.mp4",
  "media_type": "movie|series|music",
  "error": "Error message (only required when status is 'error')"
}
```

Configure Tapearr to send this payload when backup status changes. Refer to Tapearr documentation for specific instructions on setting up webhooks in your environment.

## Topic Configuration

The notification system offers two modes for organizing notifications:

### Single Topic Mode (Default)
By default, all notifications are sent to a single ntfy topic specified by `NTFY_TOPIC` in your .env file. This provides a unified timeline of all media processing events.

### Media Type-Based Topics
For users who prefer to separate notifications by media type, set `NTFY_USE_SEPARATE_TOPICS=True` in your .env file. This routes notifications to different topics based on content type:

- TV Shows: `NTFY_TV_TOPIC` (default: media-tv)
- Movies: `NTFY_MOVIE_TOPIC` (default: media-movies)
- Music: `NTFY_MUSIC_TOPIC` (default: media-music)

This separation allows you to subscribe to only the content types you're interested in or to apply different notification settings to each content type in your ntfy client.

## Updating

There are two ways to update the Media Processing Notification System to the latest version:

### Using the Update Script (Recommended)

The system comes with an automatic update script that preserves your configuration while updating the codebase:

```bash
# Simple update
./update.sh

# Update and restart the service (requires sudo)
sudo ./update.sh --restart-service
```

The update script:
- Creates a backup of your current installation
- Pulls the latest code from GitHub
- Restores your configuration files (.env and database)
- Updates dependencies
- Optionally restarts the service

### Manual Update

If you prefer to update manually:

1. Backup your configuration:
   ```bash
   cp .env .env.backup
   cp media_tracker.db media_tracker.db.backup  # If using database
   ```

2. Pull the latest code:
   ```bash
   git pull origin main
   ```

3. Update dependencies:
   ```bash
   source venv/bin/activate
   pip install --upgrade -r requirements.txt
   ```

4. Restart the service if running as a systemd service:
   ```bash
   sudo systemctl restart media-notification
   ```

## Logging Configuration

The application includes comprehensive logging capabilities to help with debugging and monitoring:

- Configure log level using the LOG_LEVEL environment variable (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Logs are written to the console and optionally to a log file specified by LOG_FILE
- Log files use rotation to prevent disk space issues (10MB per file, 5 backup files)
- Different components log with their own identifiers for easier troubleshooting

## Service Management

Tdarr and Tapearr integrations can be enabled/disabled via environment variables:

```
ENABLE_TDARR=True|False
ENABLE_TAPEARR=True|False
```

When disabled, the system will skip waiting for these services during media processing.
