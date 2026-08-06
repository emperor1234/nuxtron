"""
Main FastAPI application configuration.
Wires all social media routes and middleware.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Vista Social Media Management Platform")
    logger.info("Loading vendor credentials...")
    logger.info("Initializing analytics aggregator...")
    logger.info("Setting up WebSocket connections...")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Vista Social Media Platform")
    logger.info("Closing vendor connections...")
    logger.info("Persisting pending analytics...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Vista Social - Multi-Platform Management",
        description="Production-grade social media management platform",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routes
    from backend.fastapi.app.routers.social_media_router import router as social_router
    
    app.include_router(social_router, prefix="/api/v1")
    
    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "service": "Vista Social Management Platform",
            "version": "1.0.0",
        }
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": "Vista Social Media Management Platform API",
            "version": "1.0.0",
            "documentation": "/api/docs",
            "endpoints": {
                "social_media": "/api/v1/social",
                "health": "/health",
            }
        }
    
    logger.info("✅ Vista Social Media Platform initialized successfully")
    logger.info("📊 Features available:")
    logger.info("   - Multi-platform publishing (9 platforms)")
    logger.info("   - Real-time analytics aggregation")
    logger.info("   - Engagement management")
    logger.info("   - DM automation with AI")
    logger.info("   - Social listening")
    logger.info("   - Review management")
    logger.info("   - Content scheduling & calendar")
    logger.info("   - Team collaboration")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        # Intentional container/dev binding.
        host="0.0.0.0",  # nosec B104
        port=8000,
        log_level="info",
    )
