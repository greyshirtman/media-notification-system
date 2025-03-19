import os
from dotenv import load_dotenv

load_dotenv()

# ntfy configuration
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "media-processing")
NTFY_TOKEN = os.getenv("NTFY_TOKEN", "")  # Token-based auth (preferred)
NTFY_USER = os.getenv("NTFY_USER", "")    # Legacy user/pass auth
NTFY_PASS = os.getenv("NTFY_PASS", "")    # Legacy user/pass auth

# Topic splitting configuration
NTFY_USE_SEPARATE_TOPICS = os.getenv("NTFY_USE_SEPARATE_TOPICS", "False").lower() in ("true", "1", "t", "yes")
NTFY_TV_TOPIC = os.getenv("NTFY_TV_TOPIC", "media-tv")
NTFY_MOVIE_TOPIC = os.getenv("NTFY_MOVIE_TOPIC", "media-movies")
NTFY_MUSIC_TOPIC = os.getenv("NTFY_MUSIC_TOPIC", "media-music")

# API keys for services
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
LIDARR_API_KEY = os.getenv("LIDARR_API_KEY", "")
PROWLARR_API_KEY = os.getenv("PROWLARR_API_KEY", "")
TDARR_API_KEY = os.getenv("TDARR_API_KEY", "")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "")

# Service URLs
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
RADARR_URL = os.getenv("RADARR_URL", "http://localhost:7878")
LIDARR_URL = os.getenv("LIDARR_URL", "http://localhost:8686")
PROWLARR_URL = os.getenv("PROWLARR_URL", "http://localhost:9696")
TDARR_URL = os.getenv("TDARR_URL", "http://localhost:8265")
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
TAPEARR_URL = os.getenv("TAPEARR_URL", "http://localhost:9999")  # If applicable

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "data/media_notification.log")
ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "True").lower() in ("true", "1", "t", "yes")

if not ENABLE_FILE_LOGGING:
    LOG_FILE = None

# Service enable/disable flags
ENABLE_TDARR = os.getenv("ENABLE_TDARR", "False").lower() in ("true", "1", "t", "yes")
ENABLE_TAPEARR = os.getenv("ENABLE_TAPEARR", "False").lower() in ("true", "1", "t", "yes")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./media_tracker.db")

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
