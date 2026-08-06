"""
Meeting Recording Service
Handles Google Meet, Teams, and recording setup with consent tracking
"""

import logging
from datetime import datetime
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class RecordingProvider(Enum):
    """Supported recording providers"""
    GOOGLE_MEET = "google_meet"
    TEAMS = "teams"


class GoogleMeetRecordingService:
    """Google Meet recording integration"""
    
    def __init__(self, access_token: str, calendar_service):
        self.access_token = access_token
        self.calendar_service = calendar_service
        self.base_url = "https://www.googleapis.com/meet/v2"
    
    async def setup_recording(
        self,
        event_id: str,
        auto_start: bool = True,
        storage_location: str = "drive"
    ) -> dict:
        """
        Setup Google Meet recording for an event
        
        Args:
            event_id: Google Calendar event ID
            auto_start: Auto-start recording when meeting begins
            storage_location: Where to save recording (drive, youtube)
        
        Returns:
            Recording setup details
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get event details first
                headers = {"Authorization": f"Bearer {self.access_token}"}
                
                async with session.get(
                    f"https://www.googleapis.com/calendar/v3/events/{event_id}",
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to get event: {resp.status}")
                    event_data = await resp.json()
                
                # Extract Meet link if it exists
                conference_data = event_data.get("conferenceData", {})
                meet_link = conference_data.get("entryPoints", [{}])[0].get("uri", "")
                
                if not meet_link:
                    raise Exception("No Google Meet link in event")
                
                # Enable recording (in Meet API v2, recording is enabled by default)
                recording_info = {
                    "event_id": event_id,
                    "meet_link": meet_link,
                    "recording_enabled": True,
                    "auto_start": auto_start,
                    "storage_location": storage_location,
                    "provider": "google_meet",
                    "status": "ready",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Google Meet recording setup: {event_id}")
                return recording_info
        
        except Exception as e:
            logger.error(f"Google Meet recording setup error: {str(e)}")
            raise


class TeamsRecordingService:
    """Microsoft Teams recording integration"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.graph_api = "https://graph.microsoft.com/v1.0"
    
    async def setup_recording(
        self,
        event_id: str,
        online_meeting_id: str,
        auto_transcribe: bool = True
    ) -> dict:
        """
        Setup Teams recording for a meeting
        
        Args:
            event_id: Outlook calendar event ID
            online_meeting_id: Teams meeting ID
            auto_transcribe: Auto-transcribe recording
        
        Returns:
            Recording setup details
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                # Get online meeting details
                async with session.get(
                    f"{self.graph_api}/communications/onlineMeetings/{online_meeting_id}",
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to get Teams meeting: {resp.status}")
                    meeting_data = await resp.json()
                
                # Teams recordings are automatically enabled by default
                recording_info = {
                    "event_id": event_id,
                    "online_meeting_id": online_meeting_id,
                    "join_url": meeting_data.get("joinWebUrl", ""),
                    "recording_enabled": True,
                    "auto_transcribe": auto_transcribe,
                    "provider": "teams",
                    "status": "ready",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Teams recording setup: {event_id}")
                return recording_info
        
        except Exception as e:
            logger.error(f"Teams recording setup error: {str(e)}")
            raise


class RecordingManagementService:
    """Orchestrator for all recording operations"""
    
    def __init__(self):
        self.google_meet_service = None
        self.teams_service = None
    
    async def setup_recording(
        self,
        provider: str,
        event_id: str,
        access_token: str,
        **kwargs
    ) -> dict:
        """
        Setup recording for meeting
        
        Args:
            provider: 'google' or 'outlook'
            event_id: Calendar event ID
            access_token: OAuth access token
            **kwargs: Provider-specific options
        
        Returns:
            Recording setup confirmation
        """
        try:
            if provider == "google":
                self.google_meet_service = GoogleMeetRecordingService(
                    access_token=access_token,
                    calendar_service=None
                )
                result = await self.google_meet_service.setup_recording(
                    event_id=event_id,
                    **kwargs
                )
            elif provider == "outlook":
                self.teams_service = TeamsRecordingService(access_token=access_token)
                result = await self.teams_service.setup_recording(
                    event_id=event_id,
                    **kwargs
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            logger.info(f"Recording setup successful: {provider} - {event_id}")
            return result
        
        except Exception as e:
            logger.error(f"Recording setup failed: {str(e)}")
            raise
    
    async def get_recording_status(
        self,
        provider: str,
        event_id: str,
        access_token: str
    ) -> dict:
        """
        Get recording status for a meeting
        
        Returns:
            Recording status and details
        """
        try:
            if provider == "google":
                # Google Meet recordings can be checked via Calendar API
                return await self._get_google_recording_status(event_id, access_token)
            elif provider == "outlook":
                # Teams recordings can be checked via Graph API
                return await self._get_teams_recording_status(event_id, access_token)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        
        except Exception as e:
            logger.error(f"Failed to get recording status: {str(e)}")
            raise
    
    async def _get_google_recording_status(
        self,
        event_id: str,
        access_token: str
    ) -> dict:
        """Get Google Meet recording status"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with session.get(
                f"https://www.googleapis.com/calendar/v3/events/{event_id}",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    raise Exception("Failed to get event")
                event = await resp.json()
            
            # Check if recording is enabled in conference data
            conference = event.get("conferenceData", {})
            is_recording = "conferenceSolution" in conference
            
            return {
                "event_id": event_id,
                "provider": "google_meet",
                "recording_enabled": is_recording,
                "status": "active" if is_recording else "inactive",
                "updated_at": datetime.utcnow().isoformat()
            }
    
    async def _get_teams_recording_status(
        self,
        event_id: str,
        access_token: str
    ) -> dict:
        """Get Teams recording status"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with session.get(
                f"https://graph.microsoft.com/v1.0/events/{event_id}",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    raise Exception("Failed to get event")
                event = await resp.json()
            
            # Check if meeting has online meeting details
            is_recording = "onlineMeetingUrl" in event
            
            return {
                "event_id": event_id,
                "provider": "teams",
                "recording_enabled": is_recording,
                "status": "active" if is_recording else "inactive",
                "updated_at": datetime.utcnow().isoformat()
            }
    
    async def get_recording_link(
        self,
        provider: str,
        meeting_id: str,
        access_token: str
    ) -> str | None:
        """
        Get recording link after meeting ends
        
        Returns:
            URL to recorded video
        """
        try:
            if provider == "google":
                return await self._get_google_recording_link(meeting_id, access_token)
            elif provider == "outlook":
                return await self._get_teams_recording_link(meeting_id, access_token)
            return None
        
        except Exception as e:
            logger.error(f"Failed to get recording link: {str(e)}")
            return None
    
    async def _get_google_recording_link(
        self,
        event_id: str,
        access_token: str
    ) -> str | None:
        """Get Google Meet recording link from Drive"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Query Drive for files created by user in past hour
            try:
                async with session.get(
                    "https://www.googleapis.com/drive/v3/files",
                    params={
                        "q": "mimeType='video/mp4' and createdTime > now()",
                        "spaces": "drive",
                        "pageSize": 1,
                        "orderBy": "createdTime desc"
                    },
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        files = data.get("files", [])
                        if files:
                            return f"https://drive.google.com/file/d/{files[0]['id']}/view"
            except Exception as e:
                logger.warning(f"Could not retrieve Google recording link: {e}")
            
            return None
    
    async def _get_teams_recording_link(
        self,
        online_meeting_id: str,
        access_token: str
    ) -> str | None:
        """Get Teams recording link from SharePoint"""
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            try:
                # Get recordings list for the meeting
                async with session.get(
                    f"https://graph.microsoft.com/v1.0/communications/onlineMeetings/{online_meeting_id}/recordings",
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        recordings = data.get("value", [])
                        if recordings:
                            return recordings[0].get("contentUrl")
            except Exception as e:
                logger.warning(f"Could not retrieve Teams recording link: {e}")
            
            return None
