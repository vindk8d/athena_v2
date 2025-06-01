"""
Main FastAPI Application for Athena Digital Executive Assistant.

This module sets up the FastAPI server with all necessary routes,
middleware, and integrations for the Athena bot system.
"""

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.api.webhook_handler import router as webhook_router, setup_telegram_webhook, cleanup_webhooks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info("Starting Athena Digital Executive Assistant API")
    
    settings = get_settings()
    
    # Initialize webhook handler
    from src.api.webhook_handler import webhook_handler
    await webhook_handler.ensure_initialized()
    
    # Setup webhook if in production mode and webhook URL is configured
    if settings.environment == "production" and settings.webhook_url:
        webhook_success = await setup_telegram_webhook(settings.webhook_url)
        if webhook_success:
            logger.info("Telegram webhook configured successfully")
        else:
            logger.error("Failed to configure Telegram webhook")
    
    logger.info("Athena API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Athena API")
    await cleanup_webhooks()
    logger.info("Athena API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Athena Digital Executive Assistant API",
    description="API for Athena, a Telegram bot that helps schedule meetings and manage contacts",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(webhook_router, prefix="/webhook")


@app.get("/")
async def root():
    """
    Root endpoint for health checking and basic information.
    
    Returns:
        API information and status
    """
    settings = get_settings()
    
    return {
        "service": "Athena Digital Executive Assistant API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
        "endpoints": {
            "webhooks": "/webhook",
            "health": "/health",
            "docs": "/docs",
            "debug_env": "/debug/env",
            "webhook_status": "/webhook/telegram/status",
            "webhook_setup": "/webhook/telegram/setup"
        }
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns:
        Health status of all system components
    """
    try:
        settings = get_settings()
        
        # Check configuration
        config_status = {
            "telegram_bot_configured": bool(settings.telegram_bot_token),
            "openai_configured": bool(settings.openai_api_key),
            "supabase_configured": bool(settings.supabase_url and settings.supabase_anon_key),
            "webhook_secret_configured": bool(settings.webhook_secret)
        }
        
        # Overall health
        all_configured = all(config_status.values())
        
        health_data = {
            "status": "healthy" if all_configured else "degraded",
            "timestamp": "2024-01-01T00:00:00Z",  # This would be current timestamp
            "version": "1.0.0",
            "environment": settings.environment,
            "configuration": config_status
        }
        
        status_code = 200 if all_configured else 503
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint was not found"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )


@app.get("/debug/env")
async def debug_environment():
    """
    Debug endpoint to check environment configuration.
    
    Returns:
        Environment configuration status (without sensitive values)
    """
    settings = get_settings()
    
    return {
        "environment": settings.environment,
        "webhook_url_set": bool(settings.webhook_url),
        "webhook_url_value": settings.webhook_url[:50] + "..." if settings.webhook_url else None,
        "webhook_secret_set": bool(settings.webhook_secret),
        "telegram_token_set": bool(settings.telegram_bot_token),
        "port": settings.port
    }


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    # Development server configuration
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info"
    ) 