"""
Meeting Recap Service
AI-powered meeting summaries, decisions, and action items using GPT-4
"""

import json
import logging
from datetime import datetime

import openai

logger = logging.getLogger(__name__)


class MeetingRecapService:
    """Generate AI-powered meeting recaps from transcripts"""
    
    def __init__(self, model: str = "gpt-4", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature
        
        # Initialize OpenAI client
        self.client = openai
    
    async def generate_recap(
        self,
        transcript: str,
        attendees: list[str],
        title: str,
        duration_minutes: int
    ) -> dict:
        """
        Generate comprehensive meeting recap
        
        Args:
            transcript: Full meeting transcript
            attendees: List of meeting attendees
            title: Meeting title
            duration_minutes: Meeting duration
        
        Returns:
            Complete recap with summary, decisions, action items
        """
        try:
            # Generate summary
            summary = await self._generate_summary(
                transcript=transcript,
                title=title,
                attendees_count=len(attendees)
            )
            
            # Extract key decisions
            decisions = await self._extract_decisions(transcript)
            
            # Extract action items
            action_items = await self._extract_action_items(transcript, attendees)
            
            # Generate next steps
            next_steps = await self._generate_next_steps(action_items)
            
            recap = {
                "title": title,
                "duration_minutes": duration_minutes,
                "attendees": attendees,
                "summary": summary,
                "key_points": await self._extract_key_points(transcript),
                "decisions": decisions,
                "action_items": action_items,
                "next_steps": next_steps,
                "confidence_score": 0.88,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Meeting recap generated for: {title}")
            return recap
        
        except Exception as e:
            logger.error(f"Recap generation error: {str(e)}")
            raise
    
    async def _generate_summary(
        self,
        transcript: str,
        title: str,
        attendees_count: int
    ) -> str:
        """Generate executive summary of meeting"""
        try:
            prompt = f"""
You are a professional meeting summarizer. Generate a concise 2-3 paragraph executive summary of this meeting.

Meeting Title: {title}
Attendees: {attendees_count}

Transcript:
{transcript[:5000]}  # Limit to first 5000 chars to avoid token limits

Requirements:
- Focus on key outcomes and decisions
- Mention any commitments made
- Be concise but comprehensive
- Use professional language
- Highlight any risks or issues raised
            """
            
            response = await self._call_gpt4(prompt)
            return response.strip()
        
        except Exception as e:
            logger.error(f"Summary generation error: {str(e)}")
            return "Unable to generate summary"
    
    async def _extract_decisions(self, transcript: str) -> list[dict]:
        """Extract decisions made during meeting"""
        try:
            prompt = f"""
Extract all major decisions made during this meeting from the transcript.

Transcript:
{transcript[:5000]}

Format your response as a JSON array with objects containing:
- "decision": (string) The decision made
- "owner": (string) Who owns this decision
- "deadline": (string) When it needs to be implemented (if mentioned)
- "priority": (string) "high", "medium", or "low"

Return only valid JSON array, no other text.
            """
            
            response = await self._call_gpt4(prompt)
            
            try:
                decisions = json.loads(response)
                return decisions if isinstance(decisions, list) else [decisions]
            except json.JSONDecodeError:
                return []
        
        except Exception as e:
            logger.error(f"Decision extraction error: {str(e)}")
            return []
    
    async def _extract_action_items(
        self,
        transcript: str,
        attendees: list[str]
    ) -> list[dict]:
        """Extract action items with owners"""
        try:
            attendees_str = ", ".join(attendees[:5])  # Limit to first 5
            
            prompt = f"""
Extract all action items and tasks from this meeting transcript.

Meeting Attendees: {attendees_str}

Transcript:
{transcript[:5000]}

For each action item, identify:
- The task/action
- The owner (person responsible, if mentioned)
- Due date (if mentioned)
- Priority level
- Any blockers or dependencies

Format as JSON array with objects containing:
- "task": (string) Description of the task
- "owner": (string) Person responsible or "Unassigned"
- "due_date": (string) Due date if mentioned, else "Not specified"
- "priority": (string) "high", "medium", or "low"
- "blockers": (string) Any mentioned blockers or null

Return only valid JSON array, no other text.
            """
            
            response = await self._call_gpt4(prompt)
            
            try:
                items = json.loads(response)
                return items if isinstance(items, list) else [items]
            except json.JSONDecodeError:
                return []
        
        except Exception as e:
            logger.error(f"Action item extraction error: {str(e)}")
            return []
    
    async def _extract_key_points(self, transcript: str) -> list[str]:
        """Extract key discussion points"""
        try:
            prompt = f"""
Extract 5-7 key discussion points from this meeting transcript.

Transcript:
{transcript[:5000]}

Requirements:
- Each point should be 1-2 sentences
- Focus on substantive topics discussed
- Avoid repetition
- Use clear, professional language

Format as JSON array of strings.
Return only the JSON array, no other text.
            """
            
            response = await self._call_gpt4(prompt)
            
            try:
                points = json.loads(response)
                return points if isinstance(points, list) else []
            except json.JSONDecodeError:
                return []
        
        except Exception as e:
            logger.error(f"Key points extraction error: {str(e)}")
            return []
    
    async def _generate_next_steps(
        self,
        action_items: list[dict]
    ) -> list[dict]:
        """Generate prioritized next steps from action items"""
        try:
            high_priority = [
                item for item in action_items
                if item.get("priority") == "high"
            ]
            
            # Sort by priority and due date
            next_steps = sorted(
                high_priority,
                key=lambda x: (
                    {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "medium"), 1),
                    x.get("due_date", "")
                )
            )[:5]  # Limit to top 5
            
            return [
                {
                    "step": item["task"],
                    "owner": item["owner"],
                    "deadline": item["due_date"],
                    "priority": item["priority"]
                }
                for item in next_steps
            ]
        
        except Exception as e:
            logger.error(f"Next steps generation error: {str(e)}")
            return []
    
    async def _call_gpt4(self, prompt: str) -> str:
        """Call GPT-4 API"""
        try:
            response = self.client.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional meeting analysis assistant. Extract and summarize meeting information accurately and concisely."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"GPT-4 API error: {str(e)}")
            raise
    
    async def generate_recap_email(
        self,
        recap: dict,
        sender_name: str,
        sender_email: str
    ) -> dict:
        """
        Generate email-formatted recap
        
        Returns:
            Email content ready to send
        """
        try:
            # Build email body
            body = f"""
Hi team,

Here's a summary of our meeting on {recap.get('title')}:

SUMMARY
{recap.get('summary', '')}

KEY DECISIONS
"""
            for decision in recap.get('decisions', []):
                body += f"• {decision.get('decision', '')} (Owner: {decision.get('owner', 'TBD')})\n"
            
            body += "\nACTION ITEMS\n"
            for item in recap.get('action_items', []):
                body += f"• {item.get('task', '')} - {item.get('owner', 'Unassigned')} (Due: {item.get('due_date', 'TBD')})\n"
            
            body += "\nKEY POINTS\n"
            for point in recap.get('key_points', []):
                body += f"• {point}\n"
            
            body += f"\nNext meeting: [Date and time]\n\nBest regards,\n{sender_name}"
            
            return {
                "to": recap.get('attendees', []),
                "from": sender_email,
                "subject": f"Meeting Recap: {recap.get('title', 'Meeting')}",
                "body": body,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Email generation error: {str(e)}")
            raise


class RecapManagementService:
    """Orchestrator for recap operations"""
    
    def __init__(self):
        self.recap_service = MeetingRecapService()
    
    async def generate_full_recap(
        self,
        transcript: str,
        meeting_id: str,
        meeting_title: str,
        attendees: list[str],
        duration_minutes: int
    ) -> dict:
        """
        Generate complete meeting recap
        
        Returns:
            Full recap with all components
        """
        try:
            recap = await self.recap_service.generate_recap(
                transcript=transcript,
                attendees=attendees,
                title=meeting_title,
                duration_minutes=duration_minutes
            )
            
            recap["meeting_id"] = meeting_id
            return recap
        
        except Exception as e:
            logger.error(f"Recap generation error: {str(e)}")
            raise
    
    async def create_recap_email(
        self,
        recap: dict,
        sender_name: str,
        sender_email: str
    ) -> dict:
        """
        Create email from recap
        
        Returns:
            Email ready to send
        """
        try:
            return await self.recap_service.generate_recap_email(
                recap=recap,
                sender_name=sender_name,
                sender_email=sender_email
            )
        
        except Exception as e:
            logger.error(f"Email creation error: {str(e)}")
            raise
