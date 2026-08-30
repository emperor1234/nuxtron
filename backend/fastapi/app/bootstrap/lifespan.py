"""Explicit owner of the application startup and shutdown sequence.

The order of startup validation, database initialisation, governance state
hydration and background worker startup — and the mirrored shutdown order — is
decided here. The individual steps are still implemented in ``legacy_main``
while that module is being decomposed, so they are reached through the named
adapters below and imported lazily: importing this module must never open a
database connection, touch the network, or start a worker.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from types import ModuleType

from fastapi import FastAPI

from ..database import close_db
from ..production_middleware import StructuredLogger
from ..rate_limiter import get_rate_buckets, get_rate_lock

AUTONOMOUS_WORKFORCE_WATCHDOG_ENABLED_VALUES = {'1', 'true', 'yes', 'on'}
CLOSE_DATABASE_TIMEOUT_SECONDS = 5.0

BackgroundWorker = tuple['asyncio.Event | None', 'asyncio.Task[None] | None']


@dataclass
class StartedWorkers:
    """Handles for the background workers this lifespan is responsible for."""

    security_alerts: BackgroundWorker = field(default=(None, None))
    ira_watchdog: BackgroundWorker = field(default=(None, None))
    autonomous_workforce_watchdog: BackgroundWorker = field(default=(None, None))


def _legacy_startup_steps() -> ModuleType:
    """Resolve the module that still implements the individual startup steps."""
    from .. import legacy_main

    return legacy_main


def autonomous_workforce_watchdog_enabled() -> bool:
    raw = os.getenv('AUTONOMOUS_WORKFORCE_WATCHDOG_ENABLED', '1').strip().lower()
    return raw in AUTONOMOUS_WORKFORCE_WATCHDOG_ENABLED_VALUES


async def _initialize_runtime_state(steps: ModuleType, logger: StructuredLogger) -> None:
    """Run secret, encryption, validation, database and governance bootstrap."""
    await steps._initialize_vault(logger)
    await steps._initialize_transparent_encryption(logger)
    await steps._initialize_database_state(logger)


def _start_background_workers(steps: ModuleType) -> StartedWorkers:
    """Start the workers this application owns and publish their handles."""
    workers = StartedWorkers()

    workers.security_alerts = steps._start_security_alert_worker()
    steps._security_alert_worker_stop, steps._security_alert_worker_task = workers.security_alerts

    workers.ira_watchdog = steps._start_ira_watchdog()
    steps._ira_watchdog_stop, steps._ira_watchdog_task = workers.ira_watchdog

    if autonomous_workforce_watchdog_enabled():
        workers.autonomous_workforce_watchdog = steps._start_autonomous_workforce_watchdog()
        (
            steps._autonomous_workforce_watchdog_stop,
            steps._autonomous_workforce_watchdog_task,
        ) = workers.autonomous_workforce_watchdog

    return workers


async def _stop_background_workers(
    steps: ModuleType,
    workers: StartedWorkers,
    logger: StructuredLogger,
) -> None:
    await steps._stop_security_worker(*workers.security_alerts, logger)
    await steps._stop_ira_watchdog(*workers.ira_watchdog, logger)
    await steps._stop_autonomous_workforce_watchdog(*workers.autonomous_workforce_watchdog, logger)


async def _release_runtime_state(logger: StructuredLogger) -> None:
    """Drop in-process limiter state and close pooled database connections."""
    with get_rate_lock():
        get_rate_buckets().clear()
    try:
        await asyncio.wait_for(asyncio.to_thread(close_db), timeout=CLOSE_DATABASE_TIMEOUT_SECONDS)
    except Exception:
        logger.warning('Error closing ORM database connections')


@asynccontextmanager
async def application_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Own the startup/shutdown sequence for one FastAPI application."""
    steps = _legacy_startup_steps()
    logger = StructuredLogger('nuxtron.startup')
    workers = StartedWorkers()

    try:
        logger.info('FastAPI Application Starting')
        await _initialize_runtime_state(steps, logger)
        workers = _start_background_workers(steps)
        logger.info('FastAPI Application Started Successfully', version='2.1.0')
    except Exception as ex:
        logger.critical('Startup failed', error=str(ex))
        raise

    try:
        yield
    except asyncio.CancelledError:
        # Uvicorn reload can cancel lifespan receive; treat as normal shutdown signal.
        logger.info('Lifespan cancelled during shutdown/reload')
        raise
    finally:
        logger.info('FastAPI Application Shutting Down')
        await _stop_background_workers(steps, workers, logger)
        await _release_runtime_state(logger)
        logger.info('Cleanup complete')
