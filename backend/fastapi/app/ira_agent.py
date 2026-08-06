import importlib.util
import os
import uuid
from collections.abc import Callable
from typing import Any, Literal, cast

AgentFramework = Literal['auto', 'langchain', 'semantic_kernel', 'autogpt', 'crewai', 'native_secure_loop']


class IRAAgentRuntime:
    """Autonomy runtime that plans tasks, invokes tools, and iterates until done."""

    def __init__(
        self,
        *,
        now_iso_fn: Callable[[], str],
        retrieve_knowledge: Callable[[str, int, float], list[dict[str, Any]]],
        upsert_structured_memory: Callable[[str, str, dict[str, Any]], dict[str, Any]],
        get_short_term_messages: Callable[[str, int], list[dict[str, Any]]],
        compose_response: Callable[[str, list[dict[str, Any]]], str],
        brain_reason: Callable[[str, str, list[dict[str, Any]]], dict[str, Any]] | None = None,
        get_auto_framework_preference: Callable[[str], str | None] | None = None,
    ) -> None:
        self._now_iso_fn = now_iso_fn
        self._retrieve_knowledge = retrieve_knowledge
        self._upsert_structured_memory = upsert_structured_memory
        self._get_short_term_messages = get_short_term_messages
        self._compose_response = compose_response
        self._brain_reason = brain_reason
        self._get_auto_framework_preference = get_auto_framework_preference

    def framework_status(self) -> dict[str, Any]:
        langchain_ready = importlib.util.find_spec('langchain') is not None
        semantic_kernel_ready = importlib.util.find_spec('semantic_kernel') is not None
        autogpt_ready = importlib.util.find_spec('autogpt') is not None
        crewai_installed = importlib.util.find_spec('crewai') is not None

        # CrewAI is only marked secure when explicitly allowed.
        crewai_enabled = os.getenv('IRA_ENABLE_CREWAI', '0').strip() == '1'
        crewai_secure_mode = os.getenv('IRA_CREWAI_SECURE_MODE', '0').strip() == '1'
        crewai_ready = crewai_installed and crewai_enabled and crewai_secure_mode

        return {
            'native_secure_loop': {
                'available': True,
                'secure': True,
                'notes': 'Built-in planner + tool loop with bounded iterations and audit-friendly traces.',
            },
            'langchain': {
                'available': langchain_ready,
                'secure': True,
                'notes': 'Use if installed; runtime still enforces bounded execution and approved tools only.',
            },
            'semantic_kernel': {
                'available': semantic_kernel_ready,
                'secure': True,
                'notes': 'Use if installed; runtime still enforces bounded execution and approved tools only.',
            },
            'autogpt': {
                'available': autogpt_ready,
                'secure': False,
                'notes': 'Experimental adapter only; disabled by default for production safety.',
            },
            'crewai': {
                'available': crewai_ready,
                'secure': crewai_ready,
                'notes': 'Enabled only when IRA_ENABLE_CREWAI=1 and IRA_CREWAI_SECURE_MODE=1.',
            },
        }

    def _is_framework_ready(self, status: dict[str, Any], framework: str) -> bool:
        entry = cast(dict[str, Any], status.get(framework, {}))
        return bool(entry.get('available', False)) and bool(entry.get('secure', False))

    def _resolve_auto_framework(self, *, status: dict[str, Any], tenant_id: str) -> tuple[str, str]:
        preferred: str | None = None
        if callable(self._get_auto_framework_preference):
            preferred = self._get_auto_framework_preference(tenant_id)

        if preferred in {'langchain', 'semantic_kernel', 'native_secure_loop'} and self._is_framework_ready(status, preferred):
            return preferred, f'tenant policy preference selected: {preferred}'

        if self._is_framework_ready(status, 'langchain'):
            return 'langchain', 'selected best available framework adapter'
        if self._is_framework_ready(status, 'semantic_kernel'):
            return 'semantic_kernel', 'selected best available framework adapter'
        return 'native_secure_loop', 'fallback secure runtime used'

    def _resolve_framework(self, requested: AgentFramework, *, tenant_id: str) -> tuple[str, str]:
        status = self.framework_status()

        if requested == 'auto':
            return self._resolve_auto_framework(status=status, tenant_id=tenant_id)

        if requested == 'native_secure_loop':
            return 'native_secure_loop', 'explicitly requested secure built-in runtime'

        if self._is_framework_ready(status, requested):
            return requested, 'requested framework is available and marked secure'

        return 'native_secure_loop', f'{requested} unavailable or not secure; using native secure runtime'

    def _plan(self, *, goal: str, context_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        context_size = len(context_messages)
        return [
            {
                'phase': 'analyze_goal',
                'task': f'Clarify objective and constraints for: {goal[:180]}',
                'tool': 'retrieve_knowledge',
                'priority': 'high',
            },
            {
                'phase': 'ground_with_memory',
                'task': f'Load recent conversation context ({context_size} messages) and relevant knowledge chunks.',
                'tool': 'retrieve_knowledge',
                'priority': 'high',
            },
            {
                'phase': 'persist_plan_state',
                'task': 'Write intermediate plan and confidence signals into structured memory.',
                'tool': 'upsert_structured_memory',
                'priority': 'medium',
            },
            {
                'phase': 'finalize',
                'task': 'Return a grounded operator response with explicit next actions.',
                'tool': 'compose_response',
                'priority': 'high',
            },
        ]

    def _run_langchain_adapter(self, *, goal: str, knowledge_hits: list[dict[str, Any]]) -> dict[str, Any]:
        """Run a lightweight direct LangChain adapter path without unbounded agent plugins."""
        try:
            prompt_text = ''
            if importlib.util.find_spec('langchain_core.prompts') is not None:
                prompts_module = __import__('langchain_core.prompts', fromlist=['PromptTemplate'])
                prompt_template = getattr(prompts_module, 'PromptTemplate', None)
                if prompt_template is not None:
                    template = prompt_template.from_template(
                        'Goal: {goal}\nKnowledge: {knowledge}\nReturn secure operator actions as concise bullets.'
                    )
                    prompt_text = str(template.format(
                        goal=goal,
                        knowledge=' | '.join(str(item.get('title', 'knowledge')) for item in knowledge_hits[:3]) or 'none',
                    ))
            elif importlib.util.find_spec('langchain.prompts') is not None:
                prompts_module = __import__('langchain.prompts', fromlist=['PromptTemplate'])
                prompt_template = getattr(prompts_module, 'PromptTemplate', None)
                if prompt_template is not None:
                    template = prompt_template.from_template(
                        'Goal: {goal}\nKnowledge: {knowledge}\nReturn secure operator actions as concise bullets.'
                    )
                    prompt_text = str(template.format(
                        goal=goal,
                        knowledge=' | '.join(str(item.get('title', 'knowledge')) for item in knowledge_hits[:3]) or 'none',
                    ))

            if not prompt_text:
                prompt_text = (
                    f'LangChain adapter: goal={goal[:180]} knowledge_hits={len(knowledge_hits)} '
                    'secure-tools-only=true'
                )

            return {
                'adapter': 'langchain',
                'status': 'ok',
                'prompt_preview': prompt_text[:320],
                'knowledge_used': len(knowledge_hits),
            }
        except Exception as ex:
            return {
                'adapter': 'langchain',
                'status': 'fallback',
                'reason': str(ex)[:200],
            }

    def _run_semantic_kernel_adapter(self, *, goal: str, knowledge_hits: list[dict[str, Any]]) -> dict[str, Any]:
        """Run a lightweight direct Semantic Kernel adapter path without dynamic plugin execution."""
        try:
            sk_module = __import__('semantic_kernel')
            kernel_class = getattr(sk_module, 'Kernel', None)
            kernel_initialized = False
            if callable(kernel_class):
                _ = kernel_class()
                kernel_initialized = True

            return {
                'adapter': 'semantic_kernel',
                'status': 'ok',
                'kernel_initialized': kernel_initialized,
                'knowledge_used': len(knowledge_hits),
                'goal_preview': goal[:220],
            }
        except Exception as ex:
            return {
                'adapter': 'semantic_kernel',
                'status': 'fallback',
                'reason': str(ex)[:200],
            }

    def _build_tool_contracts(self) -> list[dict[str, Any]]:
        return [
            {
                'type': 'function',
                'function': {
                    'name': 'retrieve_knowledge',
                    'description': 'Retrieve relevant tenant knowledge chunks for grounding.',
                    'parameters': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']},
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'upsert_structured_memory',
                    'description': 'Persist workflow state and task context for future agent runs.',
                    'parameters': {'type': 'object', 'properties': {'memory_key': {'type': 'string'}}, 'required': ['memory_key']},
                },
            },
        ]

    def _generate_final_response(self, *, final_prompt: str, knowledge_hits: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        if self._brain_reason is None:
            return self._compose_response(final_prompt, knowledge_hits[:3]), {}

        try:
            brain_output = self._brain_reason(final_prompt, 'auto', self._build_tool_contracts())
        except Exception:
            return self._compose_response(final_prompt, knowledge_hits[:3]), {}

        reasoning = brain_output.get('reasoning') if isinstance(brain_output, dict) else None
        reasoning_map = cast(dict[str, Any], reasoning) if isinstance(reasoning, dict) else {}
        output_text = str(reasoning_map.get('output_text', '')).strip()
        if output_text:
            return output_text, brain_output
        return self._compose_response(final_prompt, knowledge_hits[:3]), brain_output

    def run(
        self,
        *,
        tenant_id: str,
        goal: str,
        requested_framework: AgentFramework,
        max_iterations: int,
        dry_run: bool,
        memory_key: str,
    ) -> dict[str, Any]:
        run_id = f'agent_run_{uuid.uuid4().hex[:12]}'
        selected_framework, framework_reason = self._resolve_framework(requested_framework, tenant_id=tenant_id)

        short_term = self._get_short_term_messages(tenant_id, 12)
        plan = self._plan(goal=goal, context_messages=short_term)

        tool_traces: list[dict[str, Any]] = []
        knowledge_hits: list[dict[str, Any]] = []
        status = 'completed'
        iterations_executed = 0
        framework_adapter: dict[str, Any] = {
            'adapter': 'native_secure_loop',
            'status': 'ok',
            'notes': 'Native secure planner/tool loop in use.',
        }

        capped_iterations = max(1, min(max_iterations, 12))
        for iteration in range(1, capped_iterations + 1):
            iterations_executed = iteration

            if iteration == 1:
                knowledge_hits = self._retrieve_knowledge(goal, 5, 0.1)
                tool_traces.append({
                    'iteration': iteration,
                    'tool': 'retrieve_knowledge',
                    'input': {'query': goal, 'top_k': 5, 'min_score': 0.1},
                    'result_summary': {'hits': len(knowledge_hits)},
                    'at': self._now_iso_fn(),
                })
                continue

            if iteration == 2:
                record = self._upsert_structured_memory(
                    'workflow_state',
                    memory_key,
                    {
                        'run_id': run_id,
                        'goal': goal,
                        'framework': selected_framework,
                        'status': 'running',
                        'knowledge_hits': len(knowledge_hits),
                        'dry_run': dry_run,
                        'updated_at': self._now_iso_fn(),
                    },
                )
                tool_traces.append({
                    'iteration': iteration,
                    'tool': 'upsert_structured_memory',
                    'input': {'memory_type': 'workflow_state', 'memory_key': memory_key},
                    'result_summary': {'source': str(record.get('source', 'in_memory'))},
                    'at': self._now_iso_fn(),
                })
                continue

            # Once we have retrieval + state persisted, we can finish safely.
            break

        if selected_framework == 'langchain':
            framework_adapter = self._run_langchain_adapter(goal=goal, knowledge_hits=knowledge_hits)
        elif selected_framework == 'semantic_kernel':
            framework_adapter = self._run_semantic_kernel_adapter(goal=goal, knowledge_hits=knowledge_hits)

        tool_traces.append({
            'iteration': iterations_executed,
            'tool': 'framework_adapter',
            'input': {'framework': selected_framework},
            'result_summary': {
                'adapter': str(framework_adapter.get('adapter', selected_framework)),
                'status': str(framework_adapter.get('status', 'ok')),
            },
            'at': self._now_iso_fn(),
        })

        next_actions = [
            'Validate approvals before any high-impact execution.',
            'Run dry-run actions first, then require explicit consent for real execution.',
            'Keep structured workflow state updated per phase.',
        ]
        if not knowledge_hits:
            next_actions.insert(0, 'Add tenant-specific knowledge documents to improve grounding quality.')

        final_prompt = (
            f'Agent goal: {goal}. '
            f'Framework: {selected_framework}. '
            f'Iterations: {iterations_executed}. '
            f"Adapter status: {str(framework_adapter.get('status', 'ok'))}. "
            'Return the safest practical next-step guidance.'
        )
        final_response, brain_output = self._generate_final_response(final_prompt=final_prompt, knowledge_hits=knowledge_hits)

        self._upsert_structured_memory(
            'workflow_state',
            memory_key,
            {
                'run_id': run_id,
                'goal': goal,
                'framework': selected_framework,
                'framework_reason': framework_reason,
                'status': status,
                'knowledge_hits': len(knowledge_hits),
                'iterations_executed': iterations_executed,
                'dry_run': dry_run,
                'next_actions': next_actions,
                'updated_at': self._now_iso_fn(),
            },
        )

        return {
            'run_id': run_id,
            'status': status,
            'goal': goal,
            'framework_requested': requested_framework,
            'framework_selected': selected_framework,
            'framework_reason': framework_reason,
            'dry_run': dry_run,
            'iterations_executed': iterations_executed,
            'max_iterations': capped_iterations,
            'plan': plan,
            'tool_traces': tool_traces,
            'framework_adapter': framework_adapter,
            'brain': brain_output,
            'knowledge_hits': knowledge_hits[:5],
            'next_actions': next_actions,
            'response': final_response,
            'created_at': self._now_iso_fn(),
            'updated_at': self._now_iso_fn(),
        }
