"""
Agent Framework Core

Base classes and infrastructure for autonomous agents:
- Agent scheduler
- Agent state machine
- Tool registry
- Execution pipeline
- Cost tracking
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum
from typing import Any

from backend.fastapi.app.llm.providers import LLMModel, get_completion
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class AgentType(StrEnum):
    """Agent types"""
    DEMAND_GEN = "demand_gen"
    BRAND = "brand"
    CONTENT = "content"
    AEO = "aeo"  # Answer Engine Optimization
    PR = "pr"
    CUSTOM = "custom"

class ToolType(StrEnum):
    """Available tools for agents"""
    # CMS Tools
    CONTENTFUL_CREATE = "contentful_create"
    CONTENTFUL_PUBLISH = "contentful_publish"
    CONTENTFUL_DELETE = "contentful_delete"
    SANITY_MUTATE = "sanity_mutate"
    WORDPRESS_POST = "wordpress_post"
    WORDPRESS_PUBLISH = "wordpress_publish"
    FRAMER_UPDATE = "framer_update"
    
    # Social Tools
    TWITTER_POST = "twitter_post"
    LINKEDIN_POST = "linkedin_post"
    FACEBOOK_POST = "facebook_post"
    
    # Search & Analysis
    SEARCH_WEB = "search_web"
    ANALYZE_SENTIMENT = "analyze_sentiment"
    EXTRACT_ENTITIES = "extract_entities"
    
    # Content Generation
    GENERATE_TEXT = "generate_text"
    SUMMARIZE = "summarize"
    BRAINSTORM_IDEAS = "brainstorm_ideas"
    
    # Analytics
    GET_METRICS = "get_metrics"
    ANALYZE_COMPETITORS = "analyze_competitors"

class ToolResult(BaseModel):
    """Result from executing a tool"""
    tool: ToolType
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: int

class AgentStep(BaseModel):
    """Single step in agent execution"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Agent thinking & action
    thought: str  # What the agent thinks it needs to do
    action: str  # The action to take
    tool: ToolType | None = None
    tool_input: dict[str, Any] | None = None
    tool_result: ToolResult | None = None

class AgentExecution(BaseModel):
    """Record of a single agent execution"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    agent_id: str
    agent_type: AgentType
    
    status: str = "running"  # running, completed, failed
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    
    steps: list[AgentStep] = Field(default_factory=list)
    
    # Results
    final_output: str | None = None
    error_message: str | None = None
    
    # Cost tracking
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    
    # Performance
    total_duration_ms: int = 0
    total_tool_calls: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dict for storage"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [step.dict() for step in self.steps],
            "final_output": self.final_output,
            "error_message": self.error_message,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "total_duration_ms": self.total_duration_ms,
            "total_tool_calls": self.total_tool_calls,
        }

class BaseTool(ABC):
    """Base class for all tools that agents can use"""
    
    def __init__(self, tool_type: ToolType, credentials: dict[str, str]):
        self.tool_type = tool_type
        self.credentials = credentials
    
    @abstractmethod
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def validate_input(self, input_params: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate input parameters - return (valid, error_message)"""
        return True, None

class GenerateTextTool(BaseTool):
    """Tool for generating text content using LLM"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """Generate text based on prompt and context"""
        import time
        start = time.time()
        
        try:
            prompt = input_params.get("prompt", "")
            context = input_params.get("context", "")
            tone = input_params.get("tone", "professional")
            max_length = input_params.get("max_length", 500)
            
            # Build message
            system_message = f"You are a professional content creator. Generate {tone} content."
            user_message = f"Context: {context}\n\nTask: {prompt}\n\nGenerate content (max {max_length} words):"
            
            response = await get_completion(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                model=LLMModel.GPT_4_TURBO,
                max_tokens=max_length // 4,  # Rough estimate
            )
            
            return ToolResult(
                tool=self.tool_type,
                success=True,
                data={
                    "generated_text": response.content,
                    "tokens_used": response.total_tokens,
                    "cost_usd": response.cost_usd,
                },
                execution_time_ms=int((time.time() - start) * 1000)
            )
        
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start) * 1000)
            )

class SummarizeTool(BaseTool):
    """Tool for summarizing content"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """Summarize given content"""
        import time
        start = time.time()
        
        try:
            content = input_params.get("content", "")
            max_length = input_params.get("max_length", 200)
            
            response = await get_completion(
                messages=[
                    {"role": "user", "content": f"Summarize this content in {max_length} words:\n\n{content}"}
                ],
                model=LLMModel.GPT_4_TURBO,
                max_tokens=max_length // 4,
            )
            
            return ToolResult(
                tool=self.tool_type,
                success=True,
                data={
                    "summary": response.content,
                    "tokens_used": response.total_tokens,
                    "cost_usd": response.cost_usd,
                },
                execution_time_ms=int((time.time() - start) * 1000)
            )
        
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start) * 1000)
            )

class SentimentAnalysisTool(BaseTool):
    """Tool for analyzing sentiment"""
    
    async def execute(self, input_params: dict[str, Any]) -> ToolResult:
        """Analyze sentiment of text"""
        import time
        start = time.time()
        
        try:
            text = input_params.get("text", "")
            
            response = await get_completion(
                messages=[
                    {"role": "user", "content": f"Analyze the sentiment of this text. Return a JSON object with 'sentiment' (positive/neutral/negative), 'score' (0-1), and 'explanation' fields:\n\n{text}"}
                ],
                model=LLMModel.GPT_35_TURBO,
                max_tokens=200,
            )
            
            try:
                result_json = json.loads(response.content)
            except json.JSONDecodeError:
                result_json = {
                    "sentiment": "neutral",
                    "score": 0.5,
                    "explanation": response.content
                }
            
            return ToolResult(
                tool=self.tool_type,
                success=True,
                data={
                    "sentiment": result_json.get("sentiment", "neutral"),
                    "score": result_json.get("score", 0.5),
                    "explanation": result_json.get("explanation", ""),
                    "cost_usd": response.cost_usd,
                },
                execution_time_ms=int((time.time() - start) * 1000)
            )
        
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return ToolResult(
                tool=self.tool_type,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start) * 1000)
            )

class ToolRegistry:
    """Registry of all available tools"""
    
    def __init__(self):
        self.tools: dict[ToolType, BaseTool] = {}
    
    def register(self, tool_type: ToolType, tool: BaseTool):
        """Register a tool"""
        self.tools[tool_type] = tool
        logger.info(f"Registered tool: {tool_type}")
    
    def get(self, tool_type: ToolType) -> BaseTool | None:
        """Get a tool by type"""
        return self.tools.get(tool_type)
    
    def list_tools(self) -> list[ToolType]:
        """List all registered tools"""
        return list(self.tools.keys())
    
    async def execute_tool(self, tool_type: ToolType, input_params: dict[str, Any]) -> ToolResult:
        """Execute a tool"""
        tool = self.get(tool_type)
        if not tool:
            return ToolResult(
                tool=tool_type,
                success=False,
                error=f"Tool {tool_type} not found",
                execution_time_ms=0,
            )
        
        # Validate input
        valid, error = tool.validate_input(input_params)
        if not valid:
            return ToolResult(
                tool=tool_type,
                success=False,
                error=error,
                execution_time_ms=0,
            )
        
        # Execute
        return await tool.execute(input_params)

class BaseAgent(ABC):
    """Base class for all agent types"""
    
    def __init__(
        self,
        agent_id: str,
        tenant_id: str,
        agent_type: AgentType,
        tool_registry: ToolRegistry,
        credentials: dict[str, str] | None = None,
    ):
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.agent_type = agent_type
        self.tool_registry = tool_registry
        self.credentials = credentials or {}
        self.max_steps = 15  # Prevent infinite loops
        self.llm_model = LLMModel.GPT_4_TURBO
    
    @abstractmethod
    async def think(self, execution: AgentExecution) -> str:
        """Think about what to do next"""
        pass
    
    @abstractmethod
    async def select_tool(self, thought: str) -> ToolType | None:
        """Select a tool based on thought"""
        pass
    
    async def execute(self, goal: str, context: dict[str, Any] | None = None) -> AgentExecution:
        """Execute agent to achieve goal"""
        import time
        start = time.time()
        
        execution = AgentExecution(
            tenant_id=self.tenant_id,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
        )
        
        try:
            for step_num in range(1, self.max_steps + 1):
                # Think about next action
                thought = await self.think(execution)
                
                # Determine if we need a tool or are done
                tool_type = await self.select_tool(thought)
                
                if tool_type is None:
                    # Agent is done
                    execution.final_output = thought
                    execution.status = "completed"
                    break
                
                # Create step record
                step = AgentStep(
                    step_number=step_num,
                    thought=thought,
                    action=f"Use {tool_type}",
                    tool=tool_type,
                )
                
                # Execute tool
                result = await self.tool_registry.execute_tool(tool_type, {"goal": goal})
                step.tool_result = result
                execution.steps.append(step)
                execution.total_tool_calls += 1
                
                if not result.success:
                    execution.error_message = result.error
                    execution.status = "failed"
                    break
            
            if execution.status == "running":
                execution.status = "completed"
                execution.final_output = "Max steps reached"
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            execution.status = "failed"
            execution.error_message = str(e)
        
        finally:
            execution.completed_at = datetime.utcnow()
            execution.total_duration_ms = int((time.time() - start) * 1000)
        
        return execution

# Global tool registry
tool_registry = ToolRegistry()  # type: ignore[no-untyped-call]

# Initialize with built-in tools
def initialize_tools():
    """Initialize built-in tools"""
    tool_registry.register(
        ToolType.GENERATE_TEXT,
        GenerateTextTool(ToolType.GENERATE_TEXT, {})
    )
    tool_registry.register(
        ToolType.SUMMARIZE,
        SummarizeTool(ToolType.SUMMARIZE, {})
    )
    tool_registry.register(
        ToolType.ANALYZE_SENTIMENT,
        SentimentAnalysisTool(ToolType.ANALYZE_SENTIMENT, {})
    )
    logger.info("Built-in tools initialized")
