"""
Meeting Transcription Service
Real-time and batch transcription using AssemblyAI
"""

import asyncio
import logging
import os
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)


class AssemblyAITranscriptionService:
    """AssemblyAI integration for real-time and batch transcription"""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ASSEMBLYAI_API_KEY")
        self.base_url = "https://api.assemblyai.com/v2"
        
        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY environment variable not set")
    
    async def transcribe_audio_file(
        self,
        audio_url: str,
        language_code: str = "en",
        speaker_labels: bool = True,
        auto_chapters: bool = True
    ) -> dict:
        """
        Transcribe audio file from URL
        
        Args:
            audio_url: URL to audio file (recording)
            language_code: Language code (e.g., 'en', 'es', 'fr')
            speaker_labels: Enable speaker diarization
            auto_chapters: Automatically generate chapters
        
        Returns:
            Transcription job ID and metadata
        """
        try:
            headers = {"Authorization": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                # Submit transcription job
                payload = {
                    "audio_url": audio_url,
                    "language_code": language_code,
                    "speaker_labels": speaker_labels,
                    "auto_chapters": auto_chapters,
                    "sentiment_analysis": True,
                    "entity_detection": True,
                    "auto_highlights": True
                }
                
                async with session.post(
                    f"{self.base_url}/transcript",
                    json=payload,
                    headers=headers
                ) as resp:
                    if resp.status not in [200, 201]:
                        error = await resp.text()
                        raise Exception(f"Failed to submit transcription: {error}")
                    
                    job_data = await resp.json()
                
                logger.info(f"Transcription job submitted: {job_data.get('id')}")
                
                return {
                    "job_id": job_data.get("id"),
                    "status": job_data.get("status"),
                    "audio_url": audio_url,
                    "language": language_code,
                    "speaker_labels_enabled": speaker_labels,
                    "submitted_at": datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Transcription submission error: {str(e)}")
            raise
    
    async def get_transcription_status(self, job_id: str) -> dict:
        """
        Get status of transcription job
        
        Args:
            job_id: AssemblyAI job ID
        
        Returns:
            Job status and progress
        """
        try:
            headers = {"Authorization": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/transcript/{job_id}",
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to get status: {resp.status}")
                    
                    job_data = await resp.json()
            
            return {
                "job_id": job_id,
                "status": job_data.get("status"),
                "progress": job_data.get("progress"),
                "completed": job_data.get("status") == "completed",
                "error": job_data.get("error")
            }
        
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            raise
    
    async def get_transcript(self, job_id: str) -> dict | None:
        """
        Get completed transcript with full details
        
        Args:
            job_id: AssemblyAI job ID
        
        Returns:
            Complete transcript or None if not ready
        """
        try:
            headers = {"Authorization": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/transcript/{job_id}",
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to get transcript: {resp.status}")
                    
                    data = await resp.json()
            
            if data.get("status") != "completed":
                return None
            
            # Extract transcript components
            transcript_data = {
                "job_id": job_id,
                "full_text": data.get("text", ""),
                "status": data.get("status"),
                "duration": data.get("audio_duration"),
                "confidence": data.get("confidence", 0.0),
                "language": data.get("language_code"),
                "paragraphs": [],
                "speakers": [],
                "chapters": [],
                "sentiment_analysis": [],
                "entities": [],
                "highlights": [],
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Parse paragraphs with speaker info
            if data.get("paragraphs"):
                for para in data["paragraphs"]:
                    transcript_data["paragraphs"].append({
                        "text": para.get("text", ""),
                        "speaker": para.get("speaker"),
                        "start": para.get("start"),
                        "end": para.get("end")
                    })
            
            # Parse speaker labels
            if data.get("speakers"):
                for speaker in data.get("speakers", []):
                    transcript_data["speakers"].append({
                        "speaker_id": speaker,
                        "name": f"Speaker {speaker}"
                    })
            
            # Parse auto chapters
            if data.get("chapters"):
                for chapter in data["chapters"]:
                    transcript_data["chapters"].append({
                        "title": chapter.get("summary", ""),
                        "start": chapter.get("start"),
                        "end": chapter.get("end")
                    })
            
            # Parse sentiment analysis
            if data.get("sentiment_analysis"):
                for sent in data["sentiment_analysis"]:
                    transcript_data["sentiment_analysis"].append({
                        "text": sent.get("text", ""),
                        "sentiment": sent.get("sentiment"),
                        "confidence": sent.get("confidence", 0.0)
                    })
            
            # Parse entities
            if data.get("entities"):
                for entity in data["entities"]:
                    transcript_data["entities"].append({
                        "text": entity.get("text", ""),
                        "entity_type": entity.get("entity_type"),
                        "start": entity.get("start"),
                        "end": entity.get("end")
                    })
            
            # Parse highlights
            if data.get("auto_highlights"):
                for highlight in data["auto_highlights"]:
                    transcript_data["highlights"].append({
                        "text": highlight.get("text", ""),
                        "count": highlight.get("count", 1)
                    })
            
            logger.info(f"Transcript retrieved: {job_id}")
            return transcript_data
        
        except Exception as e:
            logger.error(f"Transcript retrieval error: {str(e)}")
            raise
    
    async def poll_until_complete(
        self,
        job_id: str,
        timeout_seconds: int = 3600,
        poll_interval: int = 5
    ) -> dict | None:
        """
        Poll transcription job until completion
        
        Args:
            job_id: AssemblyAI job ID
            timeout_seconds: Max seconds to wait
            poll_interval: Seconds between polls
        
        Returns:
            Complete transcript or None if timeout
        """
        import time
        start_time = time.time()
        
        while True:
            try:
                status = await self.get_transcription_status(job_id)
                
                if status["completed"]:
                    return await self.get_transcript(job_id)
                
                if status["error"]:
                    raise Exception(f"Transcription error: {status['error']}")
                
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    logger.warning(f"Transcription timeout: {job_id}")
                    return None
                
                await asyncio.sleep(poll_interval)
            
            except Exception as e:
                logger.error(f"Polling error: {str(e)}")
                raise


class TranscriptionManagementService:
    """Orchestrator for transcription operations"""
    
    def __init__(self):
        self.assemblyai = AssemblyAITranscriptionService()
    
    async def start_transcription(
        self,
        audio_url: str,
        meeting_id: str,
        language: str = "en",
        speaker_diarization: bool = True
    ) -> dict:
        """
        Start async transcription job
        
        Returns:
            Job tracking information
        """
        try:
            job_info = await self.assemblyai.transcribe_audio_file(
                audio_url=audio_url,
                language_code=language,
                speaker_labels=speaker_diarization
            )
            
            return {
                "meeting_id": meeting_id,
                "job_id": job_info["job_id"],
                "status": "submitted",
                "audio_url": audio_url,
                "language": language,
                "speaker_diarization": speaker_diarization,
                "submitted_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Transcription start error: {str(e)}")
            raise
    
    async def check_transcription_status(self, job_id: str) -> dict:
        """
        Check current transcription status
        
        Returns:
            Status information
        """
        try:
            return await self.assemblyai.get_transcription_status(job_id)
        
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            raise
    
    async def retrieve_transcript(self, job_id: str) -> dict | None:
        """
        Retrieve completed transcript
        
        Returns:
            Full transcript with metadata
        """
        try:
            return await self.assemblyai.get_transcript(job_id)
        
        except Exception as e:
            logger.error(f"Transcript retrieval error: {str(e)}")
            raise
    
    async def wait_for_transcription(
        self,
        job_id: str,
        timeout: int = 3600
    ) -> dict | None:
        """
        Wait for transcription to complete
        
        Args:
            job_id: AssemblyAI job ID
            timeout: Max seconds to wait
        
        Returns:
            Complete transcript when ready
        """
        try:
            return await self.assemblyai.poll_until_complete(
                job_id=job_id,
                timeout_seconds=timeout
            )
        
        except Exception as e:
            logger.error(f"Wait error: {str(e)}")
            raise
    
    def extract_action_items_from_transcript(
        self,
        transcript: dict
    ) -> list[dict]:
        """
        Extract action items from transcript
        
        Args:
            transcript: Full transcript with entities/highlights
        
        Returns:
            List of identified action items
        """
        action_items = []
        
        try:
            # Look for action item indicators in text
            action_keywords = [
                "action item", "todo", "to do", "follow up", "next step",
                "need to", "should", "must", "will", "assign", "owner"
            ]
            
            transcript.get("full_text", "").lower()
            
            # Extract highlights that might be action items
            for highlight in transcript.get("highlights", []):
                text_lower_highlight = highlight.get("text", "").lower()
                
                # Check if highlight contains action keywords
                if any(keyword in text_lower_highlight for keyword in action_keywords):
                    action_items.append({
                        "text": highlight["text"],
                        "type": "action_item",
                        "confidence": 0.85,
                        "source": "highlight"
                    })
            
            logger.info(f"Extracted {len(action_items)} action items")
            return action_items
        
        except Exception as e:
            logger.error(f"Action item extraction error: {str(e)}")
            return []
    
    def extract_key_points_from_transcript(
        self,
        transcript: dict
    ) -> list[dict]:
        """
        Extract key points from transcript
        
        Args:
            transcript: Full transcript
        
        Returns:
            List of key points
        """
        key_points = []
        
        try:
            # Use auto highlights as key points
            for highlight in transcript.get("highlights", []):
                key_points.append({
                    "text": highlight["text"],
                    "mention_count": highlight.get("count", 1),
                    "type": "key_point"
                })
            
            # Also use chapters
            for chapter in transcript.get("chapters", []):
                if chapter.get("title"):
                    key_points.append({
                        "text": chapter["title"],
                        "type": "chapter",
                        "time_range": f"{chapter.get('start', 0)}ms-{chapter.get('end', 0)}ms"
                    })
            
            logger.info(f"Extracted {len(key_points)} key points")
            return key_points
        
        except Exception as e:
            logger.error(f"Key point extraction error: {str(e)}")
            return []
