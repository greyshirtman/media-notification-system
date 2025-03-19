from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn
from typing import Optional
import logging

from notifier import Notifier
from config import HOST, PORT, ENABLE_TDARR, ENABLE_TAPEARR, LOG_LEVEL, LOG_FILE
from logging_config import configure_logging

# Configure logging
loggers = configure_logging(LOG_LEVEL, LOG_FILE)
logger = loggers['main']

# Initialize the app
app = FastAPI(title="Media Processing Notification System")
notifier = Notifier()

logger.info("Media Processing Notification System starting up")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Service configuration - Tdarr: {'enabled' if ENABLE_TDARR else 'disabled'}, "
                f"Tapearr: {'enabled' if ENABLE_TAPEARR else 'disabled'}")

# Health check endpoint
@app.get("/health")
def health_check():
    logger.debug("Health check requested")
    return {"status": "healthy", "tdarr_enabled": ENABLE_TDARR, "tapearr_enabled": ENABLE_TAPEARR}

# Prowlarr webhook endpoint
@app.post("/webhook/prowlarr")
async def prowlarr_webhook(request: Request):
    try:
        data = await request.json()
        
        # Log the entire webhook structure (with sensitive data redacted)
        debug_data = str(data)
        if len(debug_data) > 1000:
            debug_data = debug_data[:1000] + "... [truncated]"
        logger.debug(f"Prowlarr webhook raw data: {debug_data}")
        
        # Check if this is a test event
        if data.get("eventType") == "Test":
            logger.info("Prowlarr test webhook received")
            return {"status": "success", "message": "Test webhook received"}
        
        # Extract relevant information based on Prowlarr's actual webhook structure
        # First try to locate the title, categories, and indexer
        title = "Unknown"
        download_type = "torrent"
        media_type = "unknown"
        
        # Check if this is a release grab event
        if "release" in data and "releaseTitle" in data["release"]:
            # Extract title from the releaseTitle field (correct field name)
            title = data["release"]["releaseTitle"]
        elif "download" in data and "title" in data["download"]:
            # Fallback to download.title if present
            title = data["download"]["title"]
        
        # Extract the download type (indexer)
        if "release" in data and "indexer" in data["release"]:
            download_type = data["release"]["indexer"]
        elif "indexer" in data:
            download_type = data["indexer"]
        
        # Try different locations for media type/category
        if "release" in data and "categories" in data["release"]:
            media_type = data["release"]["categories"][0] if data["release"]["categories"] else "unknown"
        elif "categories" in data:
            # Direct categories field
            media_type = data["categories"][0] if data["categories"] else "unknown"
        
        logger.info(f"Prowlarr webhook received for: {title}")
        logger.debug(f"Prowlarr data: type={media_type}, download={download_type}")
        
        # Send notification directly
        notifier.notify_prowlarr_found(title, download_type)
        
        return {"status": "success", "message": "Prowlarr webhook processed"}
    except Exception as e:
        logger.exception(f"Error processing Prowlarr webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

# Sonarr webhook endpoint
@app.post("/webhook/sonarr")
async def sonarr_webhook(request: Request):
    try:
        data = await request.json()
        
        # Extract relevant information
        event_type = data.get("eventType", "")
        series_title = data.get("series", {}).get("title", "Unknown")
        
        logger.info(f"Sonarr webhook received: {event_type} for {series_title}")
        
        if event_type == "Grab":
            # Extract episode details if available
            episodes = data.get("episodes", [])
            episode_title = ""
            season_num = None
            episode_num = None
            
            if episodes and len(episodes) > 0:
                episode = episodes[0]
                episode_title = episode.get("title", "")
                season_num = episode.get("seasonNumber")
                episode_num = episode.get("episodeNumber")
            
            title = f"{series_title} - {episode_title}" if episode_title else series_title
            
            # Create metadata dict
            metadata = {
                "media_type": "series",
                "season": season_num,
                "episode": episode_num,
                "series_title": series_title,
                "episode_title": episode_title
            }
            
            # Get download details
            download_id = data.get("downloadId", "Unknown")
            download_title = data.get("downloadTitle", title)
            
            logger.debug(f"Sonarr grab detected for {title} (Download ID: {download_id})")
            
            # Send notification directly
            notifier.notify_arr_status("sonarr", title, "download_started", None, metadata)
            
        elif event_type == "Download":
            # Extract episode details
            episodes = data.get("episodes", [{}])
            episode = episodes[0] if episodes else {}
            episode_title = episode.get("title", "")
            season_num = episode.get("seasonNumber")
            episode_num = episode.get("episodeNumber")
            
            # Fix: Assign the full title correctly using series_title, not title
            title = f"{series_title} - {episode_title}" if episode_title else series_title
            file_path = data.get("episodeFile", {}).get("path", None)
            
            # Create metadata dict
            metadata = {
                "media_type": "series",
                "season": season_num,
                "episode": episode_num,
                "series_title": series_title,
                "episode_title": episode_title
            }
            
            # Check if manual interaction is needed
            if data.get("manualInteraction", False):
                status = "manual_interaction"
                logger.info(f"Manual interaction required for {title}")
            # Map event to our status
            elif data.get("isUpgrade", False):
                status = "download_complete"
                logger.debug(f"Sonarr event is an upgrade for {title}")
            else:
                status = "import_complete"
                logger.debug(f"Sonarr import complete for {title}")
            
            logger.debug(f"File path: {file_path}")
            
            # Send notification directly
            notifier.notify_arr_status("sonarr", title, status, file_path, metadata)
            
        # Add handling for ManualInteractionRequired event type
        elif event_type == "ManualInteractionRequired":
            # Extract episode details if available
            episodes = data.get("episodes", [])
            if episodes and len(episodes) > 0:
                episode_title = episodes[0].get("title", "")
                # Fix: Use series_title here instead of title
                title = f"{series_title} - {episode_title}" if episode_title else series_title
            else:
                title = series_title
            
            # Get download details
            download_id = data.get("downloadId", "Unknown")
            download_title = data.get("downloadTitle", title)
            
            logger.info(f"Manual interaction required for {title} (Download ID: {download_id})")
            
            # Send notification directly
            notifier.notify_arr_status("sonarr", title, "manual_interaction", None, None)
            
        # Handle both EpisodeFileDelete and EpisodeFileDeleted events
        elif event_type in ["EpisodeFileDelete", "EpisodeFileDeleted"]:
            delete_reason = data.get("deleteReason", "Unknown")
            episode_title = data.get("episodeFile", {}).get("relativePath", "Unknown Episode")
            # Fix: Use series_title here instead of title
            title = f"{series_title} - {episode_title}"
            file_path = data.get("episodeFile", {}).get("path", None)
            
            logger.info(f"File deletion detected for {title}, reason: {delete_reason}")
            
            # Send notification directly
            if delete_reason == "Manual":
                notifier.notify_arr_status("sonarr", title, "manual_interaction", file_path, None)
            else:
                notifier.notify_arr_status("sonarr", title, "file_deleted", file_path, None)
            
        elif event_type == "Test":
            logger.info("Sonarr test webhook received")
            return {"status": "success", "message": "Test webhook received"}
        else:
            # Handle other event types
            logger.debug(f"Unhandled Sonarr event type: {event_type}")
            return {"status": "success", "message": f"Event {event_type} not processed"}
        
        return {"status": "success", "message": "Sonarr webhook processed"}
    except Exception as e:
        logger.exception(f"Error processing Sonarr webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

# Similar webhook endpoints for Radarr and Lidarr - simplify using same pattern
@app.post("/webhook/radarr")
async def radarr_webhook(request: Request):
    try:
        data = await request.json()
        
        # Extract relevant information
        event_type = data.get("eventType", "")
        movie = data.get("movie", {})
        title = movie.get("title", "Unknown")
        year = movie.get("year")
        
        logger.info(f"Radarr webhook received: {event_type} for {title}")
        
        # Create metadata dict
        metadata = {
            "media_type": "movie",
            "year": year,
            "imdbId": movie.get("imdbId"),
            "tmdbId": movie.get("tmdbId")
        }
        
        if event_type == "Grab":
            # Get download details
            download_id = data.get("downloadId", "Unknown")
            download_title = data.get("downloadTitle", title)
            
            logger.debug(f"Radarr grab detected for {title} (Download ID: {download_id})")
            
            # Send notification directly
            notifier.notify_arr_status("radarr", title, "download_started", None, metadata)
            
        elif event_type == "Download":
            file_path = data.get("movieFile", {}).get("path", None)
            
            # Check if manual interaction is needed
            if data.get("manualInteraction", False):
                status = "manual_interaction"
                logger.info(f"Manual interaction required for {title}")
            # Map event to our status
            elif data.get("isUpgrade", False):
                status = "download_complete"
                logger.debug(f"Radarr event is an upgrade for {title}")
            else:
                status = "import_complete"
                logger.debug(f"Radarr import complete for {title}")
            
            logger.debug(f"File path: {file_path}")
            
            # Send notification directly
            notifier.notify_arr_status("radarr", title, status, file_path, metadata)
            
        # Add handling for ManualInteractionRequired event type
        elif event_type == "ManualInteractionRequired":
            # Get download details
            download_id = data.get("downloadId", "Unknown")
            download_title = data.get("downloadTitle", title)
            
            logger.info(f"Manual interaction required for {title} (Download ID: {download_id})")
            
            # Send notification directly
            notifier.notify_arr_status("radarr", title, "manual_interaction", None, None)
            
        # Handle both MovieFileDelete and MovieFileDeleted events
        elif event_type in ["MovieFileDelete", "MovieFileDeleted"]:
            delete_reason = data.get("deleteReason", "Unknown")
            file_path = data.get("movieFile", {}).get("path", None)
            
            logger.info(f"File deletion detected for {title}, reason: {delete_reason}")
            
            # Send notification directly
            if delete_reason == "Manual":
                notifier.notify_arr_status("radarr", title, "manual_interaction", file_path, None)
            else:
                notifier.notify_arr_status("radarr", title, "file_deleted", file_path, None)
            
        elif event_type == "Test":
            logger.info("Radarr test webhook received")
            return {"status": "success", "message": "Test webhook received"}
        else:
            # Handle other event types
            logger.debug(f"Unhandled Radarr event type: {event_type}")
            return {"status": "success", "message": f"Event {event_type} not processed"}
        
        return {"status": "success", "message": "Radarr webhook processed"}
    except Exception as e:
        logger.exception(f"Error processing Radarr webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

@app.post("/webhook/lidarr")
async def lidarr_webhook(request: Request):
    try:
        data = await request.json()
        
        # Extract relevant information
        event_type = data.get("eventType", "")
        artist = data.get("artist", {})
        artist_name = artist.get("name", "Unknown")
        albums = data.get("albums", [{}])
        album = albums[0] if albums else {}
        album_title = album.get("title", "Unknown")
        title = f"{artist_name} - {album_title}"
        
        # Create metadata dict
        metadata = {
            "media_type": "music",
            "artist": artist_name,
            "album": album_title,
            "albumType": album.get("albumType"),
            "releaseDate": album.get("releaseDate")
        }
        
        logger.info(f"Lidarr webhook received: {event_type} for {title}")
        
        if event_type == "Grab":
            # Get download details
            download_id = data.get("downloadId", "Unknown")
            download_title = data.get("downloadTitle", title)
            
            logger.debug(f"Lidarr grab detected for {title} (Download ID: {download_id})")
            
            # Send notification directly
            notifier.notify_arr_status("lidarr", title, "download_started", None, metadata)
            
        elif event_type == "Download":
            file_path = data.get("trackFiles", [{}])[0].get("path", None) if data.get("trackFiles") else None
            
            # Check if manual interaction is needed
            if data.get("manualInteraction", False):
                status = "manual_interaction"
                logger.info(f"Manual interaction required for {title}")
            # Map event to our status
            elif data.get("isUpgrade", False):
                status = "download_complete"
                logger.debug(f"Lidarr event is an upgrade for {title}")
            else:
                status = "import_complete"
                logger.debug(f"Lidarr import complete for {title}")
            
            # Send notification directly
            notifier.notify_arr_status("lidarr", title, status, file_path, metadata)
            
        # Add handling for ManualInteractionRequired event type
        elif event_type == "ManualInteractionRequired":
            # Get download details
            download_id = data.get("downloadId", "Unknown")
            download_title = data.get("downloadTitle", title)
            
            logger.info(f"Manual interaction required for {title} (Download ID: {download_id})")
            
            # Send notification directly
            notifier.notify_arr_status("lidarr", title, "manual_interaction", None, None)
            
        # Handle both TrackFileDelete and TrackFileDeleted events
        elif event_type in ["TrackFileDelete", "TrackFileDeleted"]:
            delete_reason = data.get("deleteReason", "Unknown")
            file_path = data.get("trackFile", {}).get("path", None)
            
            logger.info(f"File deletion detected for {title}, reason: {delete_reason}")
            
            # Send notification directly
            if delete_reason == "Manual":
                notifier.notify_arr_status("lidarr", title, "manual_interaction", file_path, None)
            else:
                notifier.notify_arr_status("lidarr", title, "file_deleted", file_path, None)
            
        # Add handling for download failure events
        elif event_type == "DownloadFailed":
            # Get details about the failed download
            download_id = data.get("downloadId", "Unknown")
            download_title = data.get("downloadTitle", title)
            error_message = data.get("message", "Unknown error")
            
            logger.info(f"Lidarr download failed for {title} (Download ID: {download_id}): {error_message}")
            
            # Send notification directly
            notifier.notify_arr_status("lidarr", title, "download_failed", None, None)
            
        # Add handling for import failure events
        elif event_type == "ImportFailed":
            # Get details about the failed import
            error_message = data.get("message", "Unknown import error")
            file_path = None
            if "trackFiles" in data and data["trackFiles"]:
                file_path = data["trackFiles"][0].get("path", None)
            
            logger.info(f"Lidarr import failed for {title}: {error_message}")
            
            # Send notification directly
            notifier.notify_arr_status("lidarr", title, "import_failed", file_path, None)
            
        elif event_type == "Test":
            logger.info("Lidarr test webhook received")
            return {"status": "success", "message": "Test webhook received"}
        else:
            # Handle other event types
            logger.debug(f"Unhandled Lidarr event type: {event_type}")
            return {"status": "success", "message": f"Event {event_type} not processed"}
        
        return {"status": "success", "message": "Lidarr webhook processed"}
    except Exception as e:
        logger.exception(f"Error processing Lidarr webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

# Tdarr webhook endpoint
@app.post("/webhook/tdarr")
async def tdarr_webhook(request: Request):
    if not ENABLE_TDARR:
        return {"status": "disabled", "message": "Tdarr integration is disabled"}
    
    try:
        data = await request.json()
        
        # Extract relevant information
        status = data.get("status", "")
        title = data.get("title", "Unknown")
        file_path = data.get("file_path", None)
        error = data.get("error", None)
        
        # Extract media type for topic routing
        media_type = data.get("media_type", "unknown")
        
        # Create metadata dict for notification routing
        metadata = {
            "media_type": media_type
        }
        
        logger.info(f"Tdarr webhook received: {status} for {title} (type: {media_type})")
        
        # Send notification directly with metadata
        notifier.notify_parallel_process("tdarr", title, status, error, file_path, metadata)
        
        return {"status": "success", "message": "Tdarr webhook processed"}
    except Exception as e:
        logger.exception(f"Error processing Tdarr webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

# Plex webhook endpoint
@app.post("/webhook/plex")
async def plex_webhook(request: Request):
    try:
        form = await request.form()
        payload = form.get("payload", "{}")
        data = json.loads(payload)
        
        event = data.get("event", "")
        
        logger.info(f"Plex webhook received: {event}")
        
        if event == "library.new":
            metadata = data.get("Metadata", {})
            
            # Extract common fields
            title = metadata.get("title", "Unknown")
            media_type = metadata.get("type", "unknown")
            
            # Extract structured metadata based on media type
            if media_type == "movie":
                # For movies
                formatted_title = title
                extracted_metadata = {
                    "media_type": "movie",
                    "year": metadata.get("year"),
                    "studio": metadata.get("studio"),
                    "contentRating": metadata.get("contentRating"),
                    "summary": metadata.get("summary", "")[:100] if metadata.get("summary") else None
                }
            
            elif media_type == "episode":
                # For TV episodes
                series_title = metadata.get("grandparentTitle", "Unknown Series")
                season_num = metadata.get("parentIndex")  # Season number
                episode_num = metadata.get("index")       # Episode number
                formatted_title = f"{series_title} - {title}"
                
                extracted_metadata = {
                    "media_type": "series",
                    "series_title": series_title,
                    "season": season_num,
                    "episode": episode_num,
                    "episode_title": title
                }
            
            elif media_type == "track":
                # For music
                artist = metadata.get("grandparentTitle", "Unknown Artist")
                album = metadata.get("parentTitle", "Unknown Album")
                formatted_title = f"{artist} - {album} - {title}"
                
                extracted_metadata = {
                    "media_type": "music",
                    "artist": artist,
                    "album": album,
                    "track": title
                }
            
            else:
                # Fallback for other types
                formatted_title = title
                extracted_metadata = {
                    "media_type": media_type
                }
            
            # Extract file path
            file_path = None
            media_parts = []
            
            if "Media" in metadata:
                for media_item in metadata.get("Media", []):
                    for part in media_item.get("Part", []):
                        if "file" in part:
                            media_parts.append(part)
            
            if media_parts:
                file_path = media_parts[0].get("file")
            
            logger.debug(f"Plex new library item: {formatted_title}, file path: {file_path}")
            logger.debug(f"Extracted metadata: {extracted_metadata}")
            
            # Send notification directly
            notifier.notify_parallel_process("plex", formatted_title, "added", None, file_path, extracted_metadata)
        
        return {"status": "success", "message": "Plex webhook processed"}
    except Exception as e:
        logger.exception(f"Error processing Plex webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

# Tapearr webhook endpoint
@app.post("/webhook/tapearr")
async def tapearr_webhook(request: Request):
    if not ENABLE_TAPEARR:
        return {"status": "disabled", "message": "Tapearr integration is disabled"}
    
    try:
        data = await request.json()
        
        # Extract relevant information
        status = data.get("status", "")
        title = data.get("title", "Unknown")
        file_path = data.get("file_path", None)
        error = data.get("error", None)
        
        # Extract media type for topic routing
        media_type = data.get("media_type", "unknown")
        
        # Create metadata dict for notification routing
        metadata = {
            "media_type": media_type
        }
        
        logger.info(f"Tapearr webhook received: {status} for {title} (type: {media_type})")
        
        # Send notification directly with metadata
        notifier.notify_parallel_process("tapearr", title, status, error, file_path, metadata)
        
        return {"status": "success", "message": "Tapearr webhook processed"}
    except Exception as e:
        logger.exception(f"Error processing Tapearr webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

# Manual notification endpoint for testing
@app.post("/notify")
async def send_notification(
    title: str, 
    message: str, 
    priority: str = "default", 
    tags: Optional[str] = None
):
    logger.info(f"Manual notification requested: {title}")
    tag_list = tags.split(",") if tags else []
    success = notifier.send_notification(title, message, priority, tag_list)
    
    if not success:
        logger.error("Failed to send manual notification")
        raise HTTPException(status_code=500, detail="Failed to send notification")
    
    return {"status": "success", "message": "Notification sent"}

if __name__ == "__main__":
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True, log_level=LOG_LEVEL.lower())
