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
