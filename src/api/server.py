import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="Phone Free Desk API",
        description="API for controlling phone detection and spray system",
        version="1.0.0"
    )

    # Add CORS middleware (allow all origins for simplicity)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router)

    @app.on_event("startup")
    async def startup_event():
        logger.info("FastAPI server started")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("FastAPI server stopped")

    return app
