"""The single composition root for the Nuxtron FastAPI application.

``create_app`` is the only supported way to build the application: it creates
the FastAPI instance, installs the middleware stack and error handlers, and
registers every router exactly once. ``app`` is the one module-level instance
kept for ASGI servers and for the historical ``main``/``composition``/
``legacy_main`` import paths.
"""

from __future__ import annotations

from fastapi import FastAPI

from .context_registry import register_all_contexts, register_shared_application_state
from .lifespan import application_lifespan
from .middleware import allow_api_docs, configure_exception_handlers, configure_middleware

APPLICATION_TITLE = 'Nuxtron FastAPI Services'
APPLICATION_VERSION = '2.1.0'


def create_app() -> FastAPI:
    """Build a fully wired, independent FastAPI application."""
    docs_enabled = allow_api_docs()
    application = FastAPI(
        title=APPLICATION_TITLE,
        version=APPLICATION_VERSION,
        lifespan=application_lifespan,
        docs_url='/api/docs' if docs_enabled else None,
        redoc_url='/api/redoc' if docs_enabled else None,
        openapi_url='/api/openapi.json' if docs_enabled else None,
    )

    register_shared_application_state(application)
    configure_middleware(application)
    configure_exception_handlers(application)
    register_all_contexts(application)
    return application


app = create_app()
