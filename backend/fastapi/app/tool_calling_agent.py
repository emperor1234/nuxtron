"""
Tool-Calling Agent Loop

Implements an agentic loop where the AI makes decisions about what
actions to take next, iteratively refining output through:
- Thought: Agent thinks about the current state
- Action: Agent calls a tool (generate content, post to provider, query data, etc.)
- Observation: Tool result is fed back
- Loop until Final Answer

Supports multi-step workflows and branching logic.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx


class ToolRegistry:
    """Registry of available tools for agents to call."""

    def __init__(self):
        self.tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any], description: str = "") -> None:
        """Register a tool."""
        self.tools[name] = func

    def get_tool_schema(self) -> dict[str, Any]:
        """Generate JSON Schema for tools (for LLM context)."""
        return {
            "type": "object",
            "properties": {tool_name: {"type": "string", "description": f"Tool: {tool_name}"} for tool_name in self.tools},
        }

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> tuple[bool, Any]:
        """Execute a tool and return result."""
        if tool_name not in self.tools:
            return False, {"error": f"Tool '{tool_name}' not found"}
        try:
            result = self.tools[tool_name](**kwargs)
            # Handle async tools
            if hasattr(result, "__await__"):
                result = await result
            return True, result
        except Exception as e:
            return False, {"error": str(e)[:500]}


class AgentThought:
    """Represents a single thought/action cycle."""

    def __init__(self, step: int, thought: str, action: str, action_input: dict[str, Any], observation: Any = None):
        self.step = step
        self.thought = thought
        self.action = action
        self.action_input = action_input
        self.observation = observation


class ToolCallingAgent:
    """Multi-step agent that calls tools to accomplish goals."""

    def __init__(
        self,
        name: str,
        role: str,
        tool_registry: ToolRegistry,
        ai_gateway_url: str,
        ai_model_provider: str = "auto",
        max_steps: int = 10,
    ):
        self.name = name
        self.role = role
        self.tool_registry = tool_registry
        self.ai_gateway_url = ai_gateway_url
        self.ai_model_provider = ai_model_provider
        self.max_steps = max_steps
        self.thoughts: list[AgentThought] = []
        self.final_answer: str | None = None

    def _format_thought_chain(self) -> str:
        """Format the thought chain for context."""
        lines = []
        for thought in self.thoughts:
            lines.append(f"Step {thought.step}: [THOUGHT] {thought.thought}")
            lines.append(f"Step {thought.step}: [ACTION] {thought.action}({json.dumps(thought.action_input)})")
            if thought.observation:
                obs_text = json.dumps(thought.observation) if not isinstance(thought.observation, str) else thought.observation
                lines.append(f"Step {thought.step}: [OBSERVATION] {obs_text[:500]}")
        return "\n".join(lines)

    async def _call_ai_for_next_step(self, goal: str, context: dict[str, Any]) -> dict[str, Any]:
        """Ask AI what step to take next."""
        prompt = f"""You are an autonomous agent: {self.name} with role: {self.role}.

Goal: {goal}

Context: {json.dumps(context)}

Available tools: {json.dumps(list(self.tool_registry.tools.keys()))}

Current thought chain:
{self._format_thought_chain() if self.thoughts else "No steps yet."}

Respond with JSON:
{{"thought": "brief reasoning", "action": "tool_name", "action_input": {{...}}, "final_answer": "optional"}}

If you have the final answer, include final_answer field and omit action/action_input.
"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "test-key",  # Replace with actual key from context
        }
        request_body = {
            "provider": self.ai_model_provider,
            "prompt": prompt,
            "system_prompt": f"You are {self.role}. Make decisions step-by-step.",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.ai_gateway_url, json=request_body, headers=headers)
            if response.status_code >= 400:
                return {"error": f"AI gateway failed: {response.status_code}"}

            raw = response.json()
            # Extract JSON from response
            text = raw.get("content") or raw.get("text") or str(raw)
            if isinstance(text, str):
                try:
                    # Try to extract JSON from text
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        return json.loads(text[start:end])
                except Exception:
                    pass
            return raw if isinstance(raw, dict) else {"error": "Invalid AI response"}
        except Exception as e:
            return {"error": str(e)[:500]}

    async def run(self, goal: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the agent loop."""
        context = context or {}
        self.thoughts = []
        self.final_answer = None

        for step_num in range(1, self.max_steps + 1):
            # Ask AI what to do next
            ai_decision = await self._call_ai_for_next_step(goal, context)

            if "error" in ai_decision:
                return {"success": False, "error": ai_decision["error"], "thoughts": self.thoughts}

            # Check for final answer
            if ai_decision.get("final_answer"):
                self.final_answer = ai_decision["final_answer"]
                return {
                    "success": True,
                    "final_answer": self.final_answer,
                    "thoughts": self.thoughts,
                    "step_count": len(self.thoughts),
                }

            # Execute action
            thought_text = ai_decision.get("thought", "")
            action = ai_decision.get("action", "").strip().lower()
            action_input = ai_decision.get("action_input", {})

            if not action:
                return {"success": False, "error": "AI did not specify action", "thoughts": self.thoughts}

            tool_ok, observation = await self.tool_registry.execute_tool(action, **action_input)

            thought = AgentThought(
                step=step_num,
                thought=thought_text,
                action=action,
                action_input=action_input,
                observation=observation,
            )
            self.thoughts.append(thought)

            if not tool_ok:
                return {"success": False, "error": f"Tool {action} failed: {observation}", "thoughts": self.thoughts}

        return {
            "success": False,
            "error": f"Max steps ({self.max_steps}) exceeded",
            "thoughts": self.thoughts,
        }


def create_tool_registry_for_mission(
    tenant_id: str,
    mission: dict[str, Any],
    ai_gateway_url: str,
) -> ToolRegistry:
    """Create a tool registry with mission-specific tools."""
    registry = ToolRegistry()  # type: ignore[no-untyped-call]

    # Tool: Generate content
    async def generate_content(topic: str, format: str = "text") -> dict[str, Any]:
        return {"topic": topic, "format": format, "generated": f"Content for {topic}"}

    # Tool: Query data
    async def query_data(source: str, query: str) -> dict[str, Any]:
        return {"source": source, "query": query, "results": []}

    # Tool: Post to provider
    async def post_to_provider(provider: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"provider": provider, "status": "queued", "content": content[:100]}

    # Tool: Make decision
    async def make_decision(options: list[str], criteria: str) -> dict[str, Any]:
        return {"selected": options[0] if options else None, "reason": criteria}

    registry.register("generate_content", generate_content, "Generate content for a topic")
    registry.register("query_data", query_data, "Query data from sources")
    registry.register("post_to_provider", post_to_provider, "Post content to a provider")
    registry.register("make_decision", make_decision, "Make a decision between options")

    return registry
