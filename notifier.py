import requests
import json
import logging
import re
from config import (
    NTFY_SERVER, NTFY_TOPIC, NTFY_USER, NTFY_PASS, NTFY_TOKEN, 
    ENABLE_TDARR, ENABLE_TAPEARR, NTFY_USE_SEPARATE_TOPICS,
    NTFY_TV_TOPIC, NTFY_MOVIE_TOPIC, NTFY_MUSIC_TOPIC
)

# Get logger for this module
logger = logging.getLogger('notifier')

class Notifier:
    def __init__(self):
        self.server = NTFY_SERVER
        self.default_topic = NTFY_TOPIC
        self.use_separate_topics = NTFY_USE_SEPARATE_TOPICS
        self.tv_topic = NTFY_TV_TOPIC
        self.movie_topic = NTFY_MOVIE_TOPIC
        self.music_topic = NTFY_MUSIC_TOPIC
        
        self.auth = None
        self.auth_header = {}
        
        # Use token-based auth if available (preferred)
        if NTFY_TOKEN:
            logger.info(f"Using token-based authentication for ntfy server {self.server}")
            self.auth_header = {"Authorization": f"Bearer {NTFY_TOKEN}"}
        # Fall back to basic auth if no token but username/password provided
        elif NTFY_USER and NTFY_PASS:
            logger.info(f"Using username/password authentication for ntfy server {self.server}")
            self.auth = (NTFY_USER, NTFY_PASS)
        else:
            logger.info(f"No authentication configured for ntfy server {self.server}")
        
        # Log topic configuration
        if self.use_separate_topics:
            logger.info("Using separate ntfy topics based on media type:")
            logger.info(f"TV Shows: {self.tv_topic}")
            logger.info(f"Movies: {self.movie_topic}")
            logger.info(f"Music: {self.music_topic}")
        else:
            logger.info(f"Using single ntfy topic for all notifications: {self.default_topic}")
        
        # Define the process flow stages
        self.process_stages = [
            "search",      # Prowlarr found the media
            "download",    # *arr service is downloading
            "import",      # *arr service has imported
            "library",     # Plex has added to library
            "transcode",   # Tdarr is processing (optional)
            "backup"       # Tapearr is backing up (optional)
        ]
        
        # Special stages that don't fit into the normal flow
        self.special_stages = {
            "deleted": {
                "emoji": "🗑️",  # Trash can emoji
                "progress": "[0/{total}]"  # Will be formatted with total stages
            }
        }
        
        # Adjust stages based on enabled services
        if not ENABLE_TDARR:
            self.process_stages.remove("transcode")
        if not ENABLE_TAPEARR:  
            self.process_stages.remove("backup")
            
        self.total_stages = len(self.process_stages)
        logger.debug(f"Process flow stages: {self.process_stages} (total: {self.total_stages})")
    
    def get_topic_for_media_type(self, metadata=None, webhook_source=None):
        """
        Determine which topic to use based on media type in metadata and webhook source
        
        Args:
            metadata: Dict with media information including media_type
            webhook_source: Source of the webhook (sonarr, radarr, lidarr, plex, tdarr, tapearr)
            
        Returns:
            Topic name to use for notification
        """
        if not self.use_separate_topics:
            return self.default_topic
        
        # Direct mapping for *arr services
        if webhook_source:
            webhook_source = webhook_source.lower()
            if webhook_source == "sonarr":
                return self.tv_topic
            elif webhook_source == "radarr":
                return self.movie_topic
            elif webhook_source == "lidarr":
                return self.music_topic
        
        # For tdarr, tapearr, plex, and other services, use metadata
        if metadata and "media_type" in metadata:
            media_type = metadata.get("media_type").lower()
            
            # Map Plex media types to our standardized types
            if media_type == "episode" or media_type == "show" or media_type == "series":
                return self.tv_topic
            elif media_type == "movie":
                return self.movie_topic
            elif media_type == "track" or media_type == "music" or media_type == "album":
                return self.music_topic
        
        # Default to the general topic if we can't determine media type
        logger.debug(f"Using default topic due to unknown media type: {metadata.get('media_type') if metadata else 'None'} from source {webhook_source}")
        return self.default_topic
    
    def get_stage_info(self, stage_name):
        """Get stage number and emoji for a given stage name"""
        # Check if this is a special stage outside the normal flow
        if stage_name in self.special_stages:
            special_stage = self.special_stages[stage_name]
            # Format the progress string with the total number of stages
            progress = special_stage["progress"].format(total=self.total_stages)
            return {
                "index": -1,  # Special index for deleted files
                "emoji": special_stage["emoji"],
                "progress": progress
            }
            
        try:
            stage_index = self.process_stages.index(stage_name)
            # Use emoji to visually indicate progress - these will be put in message body, not headers
            stage_emoji = {
                "search": "🔍",    # Magnifying glass
                "download": "⬇️",   # Down arrow
                "import": "📥",     # Inbox tray
                "library": "📚",    # Books
                "transcode": "🔄",  # Arrows in circle
                "backup": "💾"      # Floppy disk
            }.get(stage_name, "⚙️")  # Gear as default
            
            return {
                "index": stage_index,
                "emoji": stage_emoji,
                "progress": f"[{stage_index + 1}/{self.total_stages}]"
            }
        except ValueError:
            return {
                "index": -1, 
                "emoji": "⚠️", 
                "progress": "[?/?]"
            }
    
    def format_media_title(self, title, metadata=None, max_length=60): # was 60
        """
        Format media title with metadata for display on mobile
        
        Args:
            title: The base media title
            metadata: Dict with additional metadata (year, season, episode, etc.)
            max_length: Maximum length for the formatted title
            
        Returns:
            Formatted title suitable for mobile display
        """
        if not metadata:
            # Fall back to simple truncation if no metadata
            return title[:max_length-3] + "..." if len(title) > max_length else title
        
        # Format based on media type
        if metadata.get("media_type") == "movie":
            # For movies: "Title (Year)" or just "Title" if no year
            year = metadata.get("year")
            if year:
                # Always preserve the year, shortening the title if necessary
                # Reserve 7 chars for " (YYYY)"
                base_title = title
                if len(title) > max_length - 7:
                    base_title = title[:max_length-10] + "..."
                return f"{base_title} ({year})"
            return title[:max_length-3] + "..." if len(title) > max_length else title
            
        elif metadata.get("media_type") == "series":
            # For TV: "Title S01E01" or just "Title" if no season/episode
            season = metadata.get("season")
            episode = metadata.get("episode")
            
            # Debug logging to track what values we're receiving
            logger.debug(f"Season: {season} ({type(season)}), Episode: {episode} ({type(episode)})")
            
            # Ensure both season and episode are integers and not None
            try:
                if season is not None and episode is not None:
                    season_int = int(season)
                    episode_int = int(episode)
                    
                    # ALWAYS include the S01E01 format, even if title needs heavy truncation
                    episode_suffix = f" S{season_int:02d}E{episode_int:02d}"
                    
                    # Check if the title plus suffix would exceed max length
                    if len(title) + len(episode_suffix) > max_length:
                        # Truncate title to fit within max_length with the suffix
                        # Leave 3 chars for "..." plus episode_suffix length
                        trunc_length = max_length - len(episode_suffix) - 3
                        if trunc_length > 0:  # Ensure we don't try to get a negative slice
                            base_title = title[:trunc_length] + "..."
                        else:
                            # If we can't fit both title and episode properly, prioritize the episode info
                            # Use at least the first 10 chars of title + episode suffix
                            max_title_len = max(10, max_length - len(episode_suffix))
                            base_title = title[:max_title_len]
                    else:
                        base_title = title  # No truncation needed
                    
                    formatted_title = f"{base_title}{episode_suffix}    " # four extra spaces to offset the title
                    # Add debug log to see what's being returned
                    logger.debug(f"Formatted TV title: '{formatted_title}' (length: {len(formatted_title)})")
                    return formatted_title
                    
            except (TypeError, ValueError) as e:
                logger.error(f"Error formatting season/episode numbers: {e}")
                # If conversion fails, still include whatever we have in text form
                if season is not None:
                    # Make sure we have room for " S01" at minimum
                    if len(title) > max_length - 4:
                        title = title[:max_length-7] + "..."
                    return f"{title} S{season}"
            
            return title[:max_length-3] + "..." if len(title) > max_length else title
            
        elif metadata.get("media_type") == "music":
            # For music tracks: Ensure we include at least artist info
            artist = metadata.get("artist")
            album = metadata.get("album")
            
            if artist and album:
                # Check if the title already contains the artist and album info
                if artist.lower() in title.lower() and album.lower() in title.lower():
                    return title[:max_length-3] + "..." if len(title) > max_length else title
                
                # If not, prioritize artist - album format
                formatted = f"{artist} - {album}"
                if len(formatted) > max_length:
                    # Truncate if too long
                    formatted = formatted[:max_length-3] + "..."
                return formatted
            elif artist:
                # Just include artist if that's all we have
                if artist.lower() not in title.lower():
                    if len(title) + len(artist) + 3 > max_length:
                        # Not enough room for both, prioritize artist
                        return f"{artist[:max_length-3]}..."
                    return f"{artist} - {title[:max_length-len(artist)-3]}"
            
            # Default music handling
            return title[:max_length-3] + "..." if len(title) > max_length else title
            
        # Default case for unknown media types
        return title[:max_length-3] + "..." if len(title) > max_length else title
    
    def send_notification(self, title, message, priority="default", tags=None, file_path=None, stage=None, metadata=None, webhook_source=None):
        """
        Send notification through ntfy
        
        Priority levels: min, low, default, high, urgent
        Stage: current processing stage (for progress indication)
        """
        # Determine which topic to use
        topic = self.get_topic_for_media_type(metadata, webhook_source)
        url = f"{self.server}/{topic}"
        
        # Get stage information if provided
        stage_info = None
        if stage:
            stage_info = self.get_stage_info(stage)
            # Only add ASCII progress to title in headers (no emoji)
            title = f"{stage_info['progress']} {title}"
        
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": ",".join(tags) if tags else ""
        }
        
        # Add authorization header if using token auth
        if self.auth_header:
            headers.update(self.auth_header)
        
        # Remove file path from notification - we no longer include it in the headers
        # This keeps user's file paths private
        if file_path:
            # We still log it for debugging purposes but don't include in notification
            logger.debug(f"File: {file_path} (not included in notification)")
        
        logger.debug(f"Sending notification to topic {topic}: {title} (priority: {priority})")
        if tags:
            logger.debug(f"Tags: {tags}")
        
        # Add emoji to the beginning of the message body instead of headers
        if stage_info:
            # Format the message if it's a media title
            if isinstance(message, str):
                message = self.format_media_title(message, metadata)
            message = f"{stage_info['emoji']} {message}"
            
        try:
            response = requests.post(
                url,
                data=message,
                headers=headers,
                auth=self.auth
            )
            if response.status_code == 200:
                logger.debug(f"Notification sent successfully to {topic}")
                return True
            else:
                logger.error(f"Notification failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.exception(f"Error sending notification: {e}")
            return False
    
    def notify_prowlarr_found(self, title, download_type, source="unknown"):
        """
        Notify when Prowlarr has found a torrent
        
        Args:
            title: Release title
            download_type: Type of download/indexer
            source: Source application that triggered the search (Sonarr, Radarr, Lidarr)
        """
        logger.info(f"Notifying: Prowlarr found {title} (source: {source})")
        
        # Determine media type based on the source application
        media_type = "unknown"
        
        # Set media type based on source application
        if source.lower() == "sonarr":
            media_type = "series"
        elif source.lower() == "radarr":
            media_type = "movie"
        elif source.lower() == "lidarr":
            media_type = "music"
        else:
            # Log that we couldn't determine media type from source
            logger.debug(f"Unknown source '{source}', trying to determine media type from title patterns")
            
            # If source doesn't match known apps, fall back to title pattern matching
            if any(x in title.lower() for x in ["s01e", "season", "episode"]):
                media_type = "series"
            elif any(x in title.lower() for x in ["1080p", "720p", "2160p", "bluray", "web-dl"]) and not any(x in title.lower() for x in ["s01e", "season", "episode"]):
                media_type = "movie"
            elif any(x in title.lower() for x in ["mp3", "flac", "album", "discography"]):
                media_type = "music"
        
        metadata = {"media_type": media_type}
        
        return self.send_notification(
            "Media Found",
            self.format_media_title(title, metadata),
            tags=["search", "prowlarr", download_type, media_type],
            priority="low",
            stage="search",
            metadata=metadata,
            webhook_source="prowlarr"
        )
    
    def notify_arr_status(self, service, title, status, file_path=None, metadata=None):
        """
        Notify about status from *arr services
        
        Args:
            service: Service name (sonarr, radarr, lidarr)
            title: Media title
            status: Current status
            file_path: Path to the media file (optional)
            metadata: Additional metadata about the media (optional)
        """
        # Define more concise messages
        status_descriptions = {
            "manual_interaction": "needs manual interaction",
            "download_started": "downloading",
            "download_complete": "downloaded",
            "import_complete": "imported",
            "download_failed": "download failed",
            "import_failed": "import failed",
            "file_deleted": "file deleted"
        }
        
        # Get the appropriate status description
        status_desc = status_descriptions.get(status, status.replace('_', ' '))
        
        # Set priorities
        priorities = {
            "manual_interaction": "high",
            "download_started": "low",
            "download_complete": "default",
            "import_complete": "default",
            "download_failed": "high",
            "import_failed": "high",
            "file_deleted": "default"
        }
        
        # Map status to process flow stage
        stage_mapping = {
            "manual_interaction": "download",  # Still in download phase but needs help
            "download_started": "download",
            "download_complete": "download",
            "import_complete": "import",
            "download_failed": "download",
            "import_failed": "import",
            "file_deleted": "deleted"  # Special stage for deleted files (step 0)
        }
        
        # Create a formatted title using available metadata
        formatted_title = self.format_media_title(title, metadata)
        
        # Determine media type from service if not specified in metadata
        if metadata is None:
            metadata = {}
        
        if "media_type" not in metadata:
            if service == "sonarr":
                metadata["media_type"] = "series"
            elif service == "radarr":
                metadata["media_type"] = "movie"
            elif service == "lidarr":
                metadata["media_type"] = "music"
        
        tags = [service, status]
        
        logger.info(f"Notifying: {service} status {status} for {title}")
        return self.send_notification(
            f"{service.capitalize()} {status_desc.title()}",
            formatted_title,
            priority=priorities.get(status, "default"),
            tags=tags,
            file_path=file_path,
            stage=stage_mapping.get(status),
            metadata=metadata,
            webhook_source=service
        )
    
    def notify_parallel_process(self, process, title, status, error=None, file_path=None, metadata=None):
        """
        Notify about parallel processes
        
        Args:
            process: Process name (plex, tdarr, tapearr)
            title: Media title
            status: Current status
            error: Error message if applicable
            file_path: Path to the media file
            metadata: Additional metadata about the media (optional)
        """
        # Determine priority
        if status == "started":
            priority = "low"
        elif status == "complete":
            priority = "default"
        elif status == "error":
            priority = "high"
        else:
            priority = "default"
        
        # Format title with metadata if available
        if metadata:
            formatted_message = self.format_media_title(title, metadata)
        else:
            formatted_message = self.format_media_title(title)
        
        if error:
            # Even shorter for error messages to make room for the error text
            short_title = self.format_media_title(title, metadata, max_length=40) if metadata else self.format_media_title(title, max_length=40)
            formatted_message = f"{short_title} - Error: {error}"
        
        # Map process to stage
        process_stage = {
            "plex": "library",
            "tdarr": "transcode",
            "tapearr": "backup"
        }.get(process.lower())

        # Create tags list with process and status
        tags = [process, status]
        
        # Add media type to tags if available
        if metadata and "media_type" in metadata:
            tags.append(metadata["media_type"])
        
        logger.info(f"Notifying: {process} status {status} for {title}")
        return self.send_notification(
            f"{process.capitalize()} {status}",
            formatted_message,
            priority=priority,
            tags=tags,
            file_path=file_path,
            stage=process_stage,
            metadata=metadata,
            webhook_source=process
        )
    
    def notify_processing_complete(self, title, file_path=None, metadata=None, webhook_source=None):
        """Notify when all processing is complete for a file"""
        logger.info(f"Notifying: Processing complete for {title}")
        
        # Use the last stage in the flow for completion
        last_stage = self.process_stages[-1] if self.process_stages else None
        
        return self.send_notification(
            "Processing Complete",
            title,
            priority="default",
            tags=["complete", "success"],
            file_path=file_path,
            stage=last_stage,
            metadata=metadata,
            webhook_source=webhook_source
        )
    
    def notify_error(self, title, error_message, file_path=None, stage=None, metadata=None, webhook_source=None):
        """Notify about errors in processing"""
        logger.error(f"Notifying: Error processing {title}")
        return self.send_notification(
            "Processing Error",
            f"{title}: {error_message}",
            priority="urgent",
            tags=["error"],
            file_path=file_path,
            stage=stage,
            metadata=metadata,
            webhook_source=webhook_source
        )
    
    def notify_companion_file_update(self, file_type, parent_title, file_path, status, service, error=None):
        """
        Notify about companion file updates (not used by default).
        This is here for completeness but doesn't get called since companion files
        don't need notifications.
        """
        # This method is implemented but not used in the default configuration
        # It's here in case you want to enable notifications for companion files in the future
        pass
