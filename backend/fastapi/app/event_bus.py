"""
ULTIMATE Event Bus Service

Central pub/sub system for all inter-module communication.
Every module publishes events. Other modules subscribe and react.
This is the nervous system of the platform.

Usage:
    bus = EventBus(redis_url="redis://localhost:6379")
    await bus.connect()

    # Publish an event
    await bus.emit(
        site_id="acme-com",
        event_type="pages_analyzed",
        source_module="seo-ai",
        payload={"pages_count": 150, "keywords": ["ai seo", "search"]}
    )

    # Subscribe to events
    async def on_pages_analyzed(event: Event):
        print(f"Event: {event.type}, Payload: {event.payload}")

    bus.subscribe(
        site_id="acme-com",
        event_type="pages_analyzed",
        handler=on_pages_analyzed
    )

    # Listen for events
    await bus.listen()
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import redis.asyncio as redis
from pydantic import Field

logger = logging.getLogger(__name__)


# ============================================================================
# Event Definitions
# ============================================================================

class EventSeverity(StrEnum):
    """Event severity level"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EventType(StrEnum):
    """Standard event types across all modules"""

    # SEO Analysis
    PAGES_ANALYZED = "pages_analyzed"
    KEYWORDS_EXTRACTED = "keywords_extracted"
    TECHNICAL_ISSUES_FOUND = "technical_issues_found"
    RANKINGS_UPDATED = "rankings_updated"

    # Entities
    ENTITIES_EXTRACTED = "entities_extracted"
    ENTITY_GRAPH_UPDATED = "entity_graph_updated"
    ENTITY_GAPS_IDENTIFIED = "entity_gaps_identified"

    # UX/Experience
    UX_ISSUES_DETECTED = "ux_issues_detected"
    CWV_IMPROVEMENTS_NEEDED = "cwv_improvements_needed"

    # Actions & Autonomy
    ACTIONS_SUGGESTED = "actions_suggested"
    LINKS_SUGGESTED = "links_suggested"
    LINKS_READY_FOR_REVIEW = "links_ready_for_review"
    LINKS_EXECUTED = "links_executed"

    # Anomalies & Alerts
    ANOMALY_DETECTED = "anomaly_detected"
    RANK_DROP_DETECTED = "rank_drop_detected"
    RECOVERY_DETECTED = "recovery_detected"
    REALTIME_OPPORTUNITY_FOUND = "realtime_opportunity_found"

    # Content & Optimization
    CONTENT_GENERATED = "content_generated"
    CONTENT_OPTIMIZED = "content_optimized"
    SCHEMA_UPDATED = "schema_updated"

    # Measurements & Results
    METRICS_COMPUTED = "metrics_computed"
    TEST_COMPLETED = "test_completed"
    WINNER_DETECTED = "winner_detected"

    # System
    SCHEDULE_FIRED = "schedule_fired"
    CONFIG_UPDATED = "config_updated"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """Standard event structure"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.PAGES_ANALYZED
    site_id: str = ""
    source_module_id: str = ""
    source_module_type: str = ""
    source_run_id: str | None = None
    severity: EventSeverity = EventSeverity.INFO
    payload: dict[str, Any] = Field(default_factory=dict)
    targets: list[str] = Field(default_factory=list)  # which modules should react
    processed_by: list[str] = Field(default_factory=list)  # modules that handled this
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    expires_at: str = Field(
        default_factory=lambda: (datetime.now() + timedelta(hours=24)).isoformat()
    )

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, data: str) -> "Event":
        """Deserialize from JSON"""
        obj = json.loads(data)
        obj["type"] = EventType(obj["type"])
        obj["severity"] = EventSeverity(obj["severity"])
        return cls(**obj)


# ============================================================================
# Event Bus
# ============================================================================

class EventBus:
    """
    Central event bus using Redis pub/sub.
    Coordinates all inter-module communication.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None
        self.subscribers: dict[str, list[Callable]] = {}  # event_type -> handlers
        self.running = False

    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis event bus")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self) -> None:
        """Close Redis connection"""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        self.running = False
        logger.info("Closed Redis event bus")

    def subscribe(
        self,
        event_type: EventType | str,
        handler: Callable,
        site_id: str | None = None,
    ):
        """
        Subscribe to an event type.

        Args:
            event_type: e.g., EventType.PAGES_ANALYZED or "pages_analyzed"
            handler: async function to call when event occurs
            site_id: if specified, only listen to events for this site
        """
        if isinstance(event_type, str):
            event_type = EventType(event_type)

        key = f"{event_type.value}"
        if site_id:
            key = f"{site_id}:{key}"

        if key not in self.subscribers:
            self.subscribers[key] = []

        self.subscribers[key].append(handler)
        logger.info(f"Subscribed to {key}")

    async def unsubscribe(
        self,
        event_type: EventType | str,
        handler: Callable | None = None,
        site_id: str | None = None,
    ):
        """Unsubscribe from an event type"""
        if isinstance(event_type, str):
            event_type = EventType(event_type)

        key = f"{event_type.value}"
        if site_id:
            key = f"{site_id}:{key}"

        if key in self.subscribers:
            if handler:
                self.subscribers[key] = [h for h in self.subscribers[key] if h != handler]
            else:
                del self.subscribers[key]

        logger.info(f"Unsubscribed from {key}")

    async def emit(
        self,
        event_type: EventType | str,
        site_id: str,
        source_module_id: str,
        source_module_type: str,
        payload: dict[str, Any],
        source_run_id: str | None = None,
        targets: list[str] | None = None,
        severity: EventSeverity = EventSeverity.INFO,
    ) -> str:
        """
        Emit an event to the bus.

        Args:
            event_type: e.g., EventType.PAGES_ANALYZED
            site_id: which site this event concerns
            source_module_id: UUID of the module that created the event
            source_module_type: string like "seo-ai", "entity-first-seo"
            payload: event-specific data
            source_run_id: UUID of the run that created the event
            targets: list of module types that should react (optional)
            severity: info, warning, error

        Returns:
            event_id
        """
        if isinstance(event_type, str):
            event_type = EventType(event_type)

        event = Event(
            type=event_type,
            site_id=site_id,
            source_module_id=source_module_id,
            source_module_type=source_module_type,
            source_run_id=source_run_id,
            payload=payload,
            targets=targets or [],
            severity=severity,
        )

        # Publish to Redis channels
        channel = f"events:{site_id}:{event_type.value}"

        try:
            await self.redis_client.publish(channel, event.to_json())
            logger.info(
                f"Emitted event {event.id} ({event_type.value}) on {channel}"
            )
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
            raise

        return event.id

    async def listen(self):
        """
        Listen for events and dispatch to subscribers.
        This should run in a background task.
        """
        if not self.redis_client:
            raise RuntimeError("Event bus not connected. Call connect() first.")

        self.running = True
        self.pubsub = self.redis_client.pubsub()

        # Subscribe to all event channels
        channels = ["events:*"]
        await self.pubsub.psubscribe(*channels)

        logger.info(f"Listening for events on {channels}")

        try:
            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        event = Event.from_json(message["data"])
                        await self._dispatch_event(event)
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")

        except Exception as e:
            logger.error(f"Listener error: {e}")
        finally:
            self.running = False

    async def _dispatch_event(self, event: Event):
        """Dispatch event to all registered handlers"""
        # Find matching subscribers
        handlers_to_call = []

        # Global handlers for event type
        key = f"{event.type.value}"
        if key in self.subscribers:
            handlers_to_call.extend(self.subscribers[key])

        # Site-specific handlers
        key_site = f"{event.site_id}:{event.type.value}"
        if key_site in self.subscribers:
            handlers_to_call.extend(self.subscribers[key_site])

        # Dispatch to all handlers
        if handlers_to_call:
            await asyncio.gather(
                *[self._call_handler(handler, event) for handler in handlers_to_call],
                return_exceptions=True,
            )
            logger.info(
                f"Dispatched event {event.id} to {len(handlers_to_call)} handlers"
            )

    async def _call_handler(self, handler: Callable, event: Event):
        """Call a handler with error handling"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"Handler error: {e}")

    async def wait_for_event(
        self,
        event_type: EventType | str,
        site_id: str,
        timeout_seconds: float = 30,
    ) -> Event | None:
        """
        Wait for a specific event (useful for testing/synchronization).

        Args:
            event_type: which event to wait for
            site_id: which site
            timeout_seconds: max time to wait

        Returns:
            Event if received, None if timeout
        """
        event_received = asyncio.Event()
        received_event: Event | None = None

        async def handler(event: Event):
            nonlocal received_event
            received_event = event
            event_received.set()

        self.subscribe(event_type, handler, site_id)

        try:
            await asyncio.wait_for(event_received.wait(), timeout=timeout_seconds)
            return received_event
        except TimeoutError:
            logger.warning(
                f"Timeout waiting for {event_type} on site {site_id}"
            )
            return None
        finally:
            await self.unsubscribe(event_type, handler, site_id)


# ============================================================================
# Global Event Bus Instance
# ============================================================================

_event_bus: EventBus | None = None


def get_event_bus(redis_url: str = "redis://localhost:6379") -> EventBus:
    """Get or create the global event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus(redis_url)
    return _event_bus


async def init_event_bus(redis_url: str = "redis://localhost:6379") -> EventBus:
    """Initialize the global event bus"""
    bus = get_event_bus(redis_url)
    await bus.connect()
    return bus


async def shutdown_event_bus() -> None:
    """Shutdown the global event bus"""
    global _event_bus
    if _event_bus:
        await _event_bus.close()
        _event_bus = None


# ============================================================================
# Helper Functions
# ============================================================================

def emit_event_sync(
    event_type: EventType | str,
    site_id: str,
    source_module_type: str,
    source_module_id: str = "system",
    payload: dict[str, Any] | None = None,
) -> str:
    """
    Emit an event (sync wrapper).
    For use in sync contexts where you can't await.
    """
    bus = get_event_bus()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        bus.emit(
            event_type=event_type,
            site_id=site_id,
            source_module_id=source_module_id,
            source_module_type=source_module_type,
            payload=payload or {},
        )
    )


class EventHandler:
    """Decorator for event handlers"""

    def __init__(self, event_type: EventType | str):
        self.event_type = event_type

    def __call__(self, func: Callable) -> Callable:
        """Register function as event handler"""
        bus = get_event_bus()
        bus.subscribe(self.event_type, func)
        return func


# ============================================================================
# Event Examples
# ============================================================================

"""
# Example: Module emits event when pages are analyzed

from event_bus import EventBus, EventType

bus = get_event_bus()

# Emit
await bus.emit(
    event_type=EventType.PAGES_ANALYZED,
    site_id="acme-com",
    source_module_type="seo-ai",
    source_module_id="module-123",
    source_run_id="run-456",
    payload={
        "pages_count": 150,
        "keywords_found": 500,
        "technical_issues": [
            {"type": "missing_h1", "pages_affected": 5},
            {"type": "redirect_chain", "pages_affected": 3},
        ]
    },
    targets=["entity-first-seo", "ux-optimizer"],
)

# Subscribe
async def on_pages_analyzed(event: Event):
    print(f"Pages analyzed: {event.payload['pages_count']}")
    # Do something...

bus.subscribe(EventType.PAGES_ANALYZED, on_pages_analyzed)

# Listen (background)
asyncio.create_task(bus.listen())

# Or use decorator
@EventHandler(EventType.PAGES_ANALYZED)
async def handle_pages(event: Event):
    print(f"Handled: {event.type}")
"""
