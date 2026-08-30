"""
Demand Generation Agent

Autonomous agent for:
- Identifying trending topics & pain points
- Generating demand generation content
- Publishing to multiple channels
- Analyzing engagement
"""


from .base import AgentExecution, AgentType, BaseAgent, ToolRegistry, ToolType
from ..llm.providers import LLMModel, get_completion


class DemandGenAgent(BaseAgent):
    """Agent specialized in demand generation"""
    
    def __init__(self, agent_id: str, tenant_id: str, tool_registry: ToolRegistry):
        super().__init__(
            agent_id=agent_id,
            tenant_id=tenant_id,
            agent_type=AgentType.DEMAND_GEN,
            tool_registry=tool_registry,
        )
        self.llm_model = LLMModel.GPT_4_TURBO
    
    async def think(self, execution: AgentExecution) -> str:
        """Think about what to do next based on execution history"""
        
        # Build context from previous steps
        step_history = ""
        for step in execution.steps:
            step_history += f"\nStep {step.step_number}: {step.thought}\n"
            if step.tool_result:
                step_history += f"Result: {step.tool_result.data}\n"
        
        # Ask LLM what to do next
        messages = [
            {"role": "system", "content": """You are a Demand Generation Agent. Your goal is to:
1. Identify trending topics and pain points in your industry
2. Generate compelling content that addresses these topics
3. Recommend publishing channels (Twitter, LinkedIn, email, blog)
4. Ensure content is optimized for engagement

After analyzing the situation, determine the next action:
- If you need to generate content, respond with: "GENERATE_CONTENT: [topic] | [tone] | [channel]"
- If you need to analyze competitors, respond with: "ANALYZE_COMPETITORS"
- If done, respond with: "DONE: [summary of generated content]"
"""},
            {"role": "user", "content": f"Current execution:\n{step_history}\n\nWhat should I do next?"}
        ]
        
        response = await get_completion(
            messages=messages,
            model=self.llm_model,
            max_tokens=500,
        )
        
        execution.input_tokens += response.input_tokens
        execution.output_tokens += response.output_tokens
        execution.estimated_cost_usd += response.cost_usd
        
        return response.content
    
    async def select_tool(self, thought: str) -> ToolType | None:
        """Select which tool to use based on agent's thought"""
        
        thought_lower = thought.lower()
        
        if "generate_content" in thought_lower or "write" in thought_lower:
            return ToolType.GENERATE_TEXT
        
        elif "analyze" in thought_lower or "sentiment" in thought_lower:
            return ToolType.ANALYZE_SENTIMENT
        
        elif "summarize" in thought_lower:
            return ToolType.SUMMARIZE
        
        elif "done" in thought_lower or "complete" in thought_lower:
            return None  # Signal completion
        
        else:
            return None

class BrandAgent(BaseAgent):
    """Agent specialized in brand monitoring and analysis"""
    
    def __init__(self, agent_id: str, tenant_id: str, tool_registry: ToolRegistry):
        super().__init__(
            agent_id=agent_id,
            tenant_id=tenant_id,
            agent_type=AgentType.BRAND,
            tool_registry=tool_registry,
        )
    
    async def think(self, execution: AgentExecution) -> str:
        """Brand agent thinking"""
        
        step_history = ""
        for step in execution.steps:
            step_history += f"\nStep {step.step_number}: {step.thought}\n"
            if step.tool_result:
                step_history += f"Result: {step.tool_result.data}\n"
        
        messages = [
            {"role": "system", "content": """You are a Brand Agent. Your responsibilities:
1. Monitor brand mentions and sentiment across channels
2. Identify brand health trends
3. Recommend response strategies
4. Track competitor activity

Determine next action:
- If analyzing brand mentions, respond with: "ANALYZE_SENTIMENT"
- If comparing with competitors, respond with: "ANALYZE_COMPETITORS"
- If generating response content, respond with: "GENERATE_CONTENT: [response strategy]"
- If done, respond with: "DONE: [brand health summary]"
"""},
            {"role": "user", "content": f"Current brand analysis:\n{step_history}\n\nNext action?"}
        ]
        
        response = await get_completion(
            messages=messages,
            model=self.llm_model,
            max_tokens=500,
        )
        
        execution.input_tokens += response.input_tokens
        execution.output_tokens += response.output_tokens
        execution.estimated_cost_usd += response.cost_usd
        
        return response.content
    
    async def select_tool(self, thought: str) -> ToolType | None:
        thought_lower = thought.lower()
        
        if "sentiment" in thought_lower or "analyze" in thought_lower:
            return ToolType.ANALYZE_SENTIMENT
        elif "generate" in thought_lower or "write" in thought_lower:
            return ToolType.GENERATE_TEXT
        elif "done" in thought_lower:
            return None
        else:
            return None

class ContentAgent(BaseAgent):
    """Agent specialized in content creation and optimization"""
    
    def __init__(self, agent_id: str, tenant_id: str, tool_registry: ToolRegistry):
        super().__init__(
            agent_id=agent_id,
            tenant_id=tenant_id,
            agent_type=AgentType.CONTENT,
            tool_registry=tool_registry,
        )
    
    async def think(self, execution: AgentExecution) -> str:
        """Content agent thinking"""
        
        step_history = ""
        for step in execution.steps:
            step_history += f"\nStep {step.step_number}: {step.thought}\n"
            if step.tool_result:
                step_history += f"Result: {step.tool_result.data}\n"
        
        messages = [
            {"role": "system", "content": """You are a Content Agent. Your role:
1. Generate high-quality, engaging content
2. Optimize content for SEO and readability
3. Adapt content for different formats (blog, social, email)
4. Ensure brand voice consistency

Actions available:
- "GENERATE_CONTENT: [topic] | [format] | [tone]" - Generate new content
- "SUMMARIZE" - Create summary versions
- "ANALYZE_SENTIMENT" - Check content tone
- "DONE: [content pieces created]" - Finish

Decide your next action."""},
            {"role": "user", "content": f"Content creation progress:\n{step_history}\n\nWhat's next?"}
        ]
        
        response = await get_completion(
            messages=messages,
            model=self.llm_model,
            max_tokens=500,
        )
        
        execution.input_tokens += response.input_tokens
        execution.output_tokens += response.output_tokens
        execution.estimated_cost_usd += response.cost_usd
        
        return response.content
    
    async def select_tool(self, thought: str) -> ToolType | None:
        thought_lower = thought.lower()
        
        if "generate" in thought_lower or "write" in thought_lower or "create" in thought_lower:
            return ToolType.GENERATE_TEXT
        elif "summarize" in thought_lower:
            return ToolType.SUMMARIZE
        elif "sentiment" in thought_lower or "tone" in thought_lower:
            return ToolType.ANALYZE_SENTIMENT
        elif "done" in thought_lower:
            return None
        else:
            return None

class AEOAgent(BaseAgent):
    """Answer Engine Optimization Agent - optimize for AI search engines"""
    
    def __init__(self, agent_id: str, tenant_id: str, tool_registry: ToolRegistry):
        super().__init__(
            agent_id=agent_id,
            tenant_id=tenant_id,
            agent_type=AgentType.AEO,
            tool_registry=tool_registry,
        )
    
    async def think(self, execution: AgentExecution) -> str:
        """AEO agent thinking"""
        
        step_history = ""
        for step in execution.steps:
            step_history += f"\nStep {step.step_number}: {step.thought}\n"
            if step.tool_result:
                step_history += f"Result: {step.tool_result.data}\n"
        
        messages = [
            {"role": "system", "content": """You are an AEO (Answer Engine Optimization) Agent. Your mission:
1. Optimize content for AI search engines (ChatGPT, Perplexity, Gemini, Claude)
2. Identify answer-friendly content structures
3. Generate FAQ-style content that AI engines prefer
4. Ensure featured snippet optimization

Strategy:
- "GENERATE_CONTENT: [AEO optimization] | [FAQ format] | [answer-engine-friendly]"
- "SUMMARIZE" - Create concise answers
- "ANALYZE" - Check content for AI-friendliness
- "DONE: [optimization complete]"

Next step?"""},
            {"role": "user", "content": f"AEO optimization progress:\n{step_history}\n\nContinue?"}
        ]
        
        response = await get_completion(
            messages=messages,
            model=self.llm_model,
            max_tokens=500,
        )
        
        execution.input_tokens += response.input_tokens
        execution.output_tokens += response.output_tokens
        execution.estimated_cost_usd += response.cost_usd
        
        return response.content
    
    async def select_tool(self, thought: str) -> ToolType | None:
        thought_lower = thought.lower()
        
        if "generate" in thought_lower or "create" in thought_lower or "faq" in thought_lower:
            return ToolType.GENERATE_TEXT
        elif "summarize" in thought_lower:
            return ToolType.SUMMARIZE
        elif "analyze" in thought_lower:
            return ToolType.ANALYZE_SENTIMENT
        elif "done" in thought_lower:
            return None
        else:
            return None

class PRAgent(BaseAgent):
    """PR and Communications Agent - media outreach and relations"""
    
    def __init__(self, agent_id: str, tenant_id: str, tool_registry: ToolRegistry):
        super().__init__(
            agent_id=agent_id,
            tenant_id=tenant_id,
            agent_type=AgentType.PR,
            tool_registry=tool_registry,
        )
    
    async def think(self, execution: AgentExecution) -> str:
        """PR agent thinking"""
        
        step_history = ""
        for step in execution.steps:
            step_history += f"\nStep {step.step_number}: {step.thought}\n"
            if step.tool_result:
                step_history += f"Result: {step.tool_result.data}\n"
        
        messages = [
            {"role": "system", "content": """You are a PR Agent. Your responsibilities:
1. Draft press releases and media pitches
2. Monitor media mentions and sentiment
3. Identify key influencers and journalists
4. Plan media outreach campaigns

Tasks:
- "GENERATE_CONTENT: [press release | media pitch | announcement]"
- "ANALYZE_SENTIMENT" - Monitor media coverage
- "SUMMARIZE" - Create talking points
- "DONE: [PR campaign plan]" - Finalize

What should I do?"""},
            {"role": "user", "content": f"PR campaign progress:\n{step_history}\n\nNext step?"}
        ]
        
        response = await get_completion(
            messages=messages,
            model=self.llm_model,
            max_tokens=500,
        )
        
        execution.input_tokens += response.input_tokens
        execution.output_tokens += response.output_tokens
        execution.estimated_cost_usd += response.cost_usd
        
        return response.content
    
    async def select_tool(self, thought: str) -> ToolType | None:
        thought_lower = thought.lower()
        
        if "generate" in thought_lower or "write" in thought_lower or "draft" in thought_lower:
            return ToolType.GENERATE_TEXT
        elif "summarize" in thought_lower or "talking" in thought_lower:
            return ToolType.SUMMARIZE
        elif "sentiment" in thought_lower or "monitor" in thought_lower:
            return ToolType.ANALYZE_SENTIMENT
        elif "done" in thought_lower:
            return None
        else:
            return None

class CustomAgent(BaseAgent):
    """Custom agent - configurable for user-defined workflows"""
    
    def __init__(
        self,
        agent_id: str,
        tenant_id: str,
        tool_registry: ToolRegistry,
        system_prompt: str,
        available_tools: list[ToolType],
    ):
        super().__init__(
            agent_id=agent_id,
            tenant_id=tenant_id,
            agent_type=AgentType.CUSTOM,
            tool_registry=tool_registry,
        )
        self.system_prompt = system_prompt
        self.available_tools = available_tools
    
    async def think(self, execution: AgentExecution) -> str:
        """Custom agent thinking based on user prompt"""
        
        step_history = ""
        for step in execution.steps:
            step_history += f"\nStep {step.step_number}: {step.thought}\n"
            if step.tool_result:
                step_history += f"Result: {step.tool_result.data}\n"
        
        available_tools_str = ", ".join([t.value for t in self.available_tools])
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Current execution progress:
{step_history}

Available tools: {available_tools_str}

Continue with next action or respond DONE when finished."""}
        ]
        
        response = await get_completion(
            messages=messages,
            model=self.llm_model,
            max_tokens=500,
        )
        
        execution.input_tokens += response.input_tokens
        execution.output_tokens += response.output_tokens
        execution.estimated_cost_usd += response.cost_usd
        
        return response.content
    
    async def select_tool(self, thought: str) -> ToolType | None:
        """Select tool based on thought"""
        thought_lower = thought.lower()
        
        # Simple matching - can be enhanced
        for tool in self.available_tools:
            if tool.value in thought_lower:
                return tool
        
        if "done" in thought_lower:
            return None
        
        return self.available_tools[0] if self.available_tools else None

# Factory function to create agents
def create_agent(
    agent_type: str,
    agent_id: str,
    tenant_id: str,
    tool_registry: ToolRegistry,
    **kwargs,
) -> BaseAgent:
    """Factory function to create agent by type"""
    
    if agent_type == AgentType.DEMAND_GEN.value:
        return DemandGenAgent(agent_id, tenant_id, tool_registry)
    
    elif agent_type == AgentType.BRAND.value:
        return BrandAgent(agent_id, tenant_id, tool_registry)
    
    elif agent_type == AgentType.CONTENT.value:
        return ContentAgent(agent_id, tenant_id, tool_registry)
    
    elif agent_type == AgentType.AEO.value:
        return AEOAgent(agent_id, tenant_id, tool_registry)
    
    elif agent_type == AgentType.PR.value:
        return PRAgent(agent_id, tenant_id, tool_registry)
    
    elif agent_type == AgentType.CUSTOM.value:
        return CustomAgent(
            agent_id,
            tenant_id,
            tool_registry,
            system_prompt=kwargs.get("system_prompt", "You are a helpful AI agent."),
            available_tools=kwargs.get("available_tools", list(ToolRegistry().list_tools())),  # type: ignore[no-untyped-call]
        )
    
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
