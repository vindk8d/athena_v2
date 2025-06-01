"""
FastAPI Webhook Handler for Athena Digital Executive Assistant.

This module handles incoming webhooks from external services:
- Telegram bot webhooks for message processing
- Google Calendar notifications
- Other webhook integrations
"""

import json
import logging
import hmac
import hashlib
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.error import TelegramError

from src.config.settings import get_settings
from src.bot.telegram_bot import get_bot

import asyncio
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request as StarletteRequest

# Configure logging
logger = logging.getLogger(__name__)

# Create router for webhook endpoints
router = APIRouter(prefix="/webhook", tags=["webhooks"])


class WebhookHandler:
    """Handler for various webhook integrations."""
    
    def __init__(self):
        """Initialize the webhook handler."""
        self.settings = get_settings()
        self.telegram_bot = get_bot()
        # Initialize bot application synchronously
        self._init_task = None
    
    async def ensure_initialized(self):
        """Ensure the bot is initialized."""
        if self._init_task is None:
            self._init_task = asyncio.create_task(self.telegram_bot.initialize())
        await self._init_task
    
    async def verify_telegram_webhook(
        self, 
        request_body: bytes, 
        secret_token: Optional[str] = None
    ) -> bool:
        """
        Verify Telegram webhook authenticity using secret token.
        
        Args:
            request_body: Raw request body bytes
            secret_token: Secret token from X-Telegram-Bot-Api-Secret-Token header
            
        Returns:
            True if webhook is authentic, False otherwise
        """
        if not self.settings.webhook_secret:
            # If no secret is configured, allow all requests (development mode)
            logger.warning("No webhook secret configured - accepting all requests")
            return True
        
        if not secret_token:
            logger.warning("No secret token provided in webhook request")
            return False
        
        # Verify the secret token matches our configured secret
        expected_token = self.settings.webhook_secret
        if not hmac.compare_digest(secret_token, expected_token):
            logger.warning("Invalid secret token in webhook request")
            return False
        
        return True
    
    async def process_telegram_update(self, update_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Process a Telegram update through the bot.
        
        Args:
            update_data: Telegram update data
            
        Returns:
            Response dictionary
        """
        try:
            # Ensure bot is initialized
            await self.ensure_initialized()
            
            # Create Telegram Update object
            update = Update.de_json(update_data, self.telegram_bot.bot)
            
            if not update:
                logger.error("Failed to parse Telegram update")
                raise HTTPException(status_code=400, detail="Invalid update format")
            
            # Process the update through the bot's application
            await self.telegram_bot.application.process_update(update)
            
            logger.info(f"Successfully processed update {update.update_id}")
            return {"status": "success", "message": "Update processed"}
            
        except TelegramError as e:
            logger.error(f"Telegram error processing update: {e}")
            raise HTTPException(status_code=500, detail="Telegram processing error")
        except Exception as e:
            logger.error(f"Unexpected error processing update: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


# Global webhook handler instance
webhook_handler = WebhookHandler()


async def get_webhook_handler() -> WebhookHandler:
    """Dependency to get the webhook handler instance."""
    return webhook_handler


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    handler: WebhookHandler = Depends(get_webhook_handler),
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
    background_tasks: BackgroundTasks = None
):
    """
    Handle incoming Telegram webhook requests with timeout and improved error handling.
    """
    try:
        # Set a timeout for the webhook processing (e.g., 10 seconds)
        try:
            return await asyncio.wait_for(_process_telegram_webhook(request, handler, x_telegram_bot_api_secret_token), timeout=10)
        except asyncio.TimeoutError:
            logger.error(f"Telegram webhook processing timed out for request from {request.client.host}")
            raise HTTPException(status_code=504, detail="Webhook processing timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Telegram webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def _process_telegram_webhook(request: Request, handler: WebhookHandler, x_telegram_bot_api_secret_token: Optional[str]):
    # Get raw request body for verification
    request_body = await request.body()
    # Verify webhook authenticity
    is_authentic = await handler.verify_telegram_webhook(
        request_body=request_body,
        secret_token=x_telegram_bot_api_secret_token
    )
    if not is_authentic:
        logger.warning(f"Unauthorized webhook attempt from {request.client.host}")
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Parse JSON body
    try:
        update_data = json.loads(request_body)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook request: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    # Log the incoming update (without sensitive data)
    update_id = update_data.get('update_id', 'unknown')
    message_info = ""
    if 'message' in update_data:
        user_id = update_data['message'].get('from', {}).get('id', 'unknown')
        message_info = f"from user {user_id}"
    logger.info(f"Received Telegram update {update_id} {message_info}")
    # Process the update
    response = await handler.process_telegram_update(update_data)
    return JSONResponse(
        status_code=200,
        content=response
    )


@router.post("/calendar")
async def calendar_webhook(
    request: Request,
    handler: WebhookHandler = Depends(get_webhook_handler)
):
    """
    Handle incoming Google Calendar webhook notifications.
    
    This endpoint receives notifications about calendar changes
    and can trigger appropriate responses.
    
    Args:
        request: FastAPI request object
        handler: Webhook handler dependency
        
    Returns:
        JSON response indicating success
    """
    try:
        # Get request headers and body
        headers = dict(request.headers)
        request_body = await request.body()
        
        # Log the calendar notification
        logger.info(f"Received calendar webhook notification from {request.client.host}")
        
        # For now, just acknowledge the webhook
        # This will be expanded when calendar integration is implemented
        logger.info("Calendar webhook received - processing not yet implemented")
        
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Calendar webhook received"}
        )
        
    except Exception as e:
        logger.error(f"Error processing calendar webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def webhook_health():
    """
    Health check endpoint for webhook services.
    
    Returns:
        Health status of webhook handler
    """
    try:
        # Check if Telegram bot is properly configured
        bot = get_bot()
        bot_info = await bot.get_bot_info()
        
        if bot_info:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "service": "webhook_handler",
                    "telegram_bot": {
                        "configured": True,
                        "username": bot_info.get("username"),
                        "id": bot_info.get("id")
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "webhook_handler",
                    "telegram_bot": {"configured": False}
                }
            )
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "webhook_handler",
                "error": str(e)
            }
        )


@router.post("/telegram/set")
async def set_telegram_webhook(
    webhook_url: str,
    handler: WebhookHandler = Depends(get_webhook_handler)
):
    """
    Set the Telegram webhook URL.
    
    This endpoint allows setting the webhook URL for the Telegram bot.
    Typically called during deployment or configuration.
    
    Args:
        webhook_url: The webhook URL to set
        handler: Webhook handler dependency
        
    Returns:
        Success or failure response
    """
    try:
        # Ensure bot is initialized
        await handler.ensure_initialized()
        
        # Set the webhook
        success = await handler.telegram_bot.set_webhook(webhook_url)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"Webhook set to {webhook_url}"
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Failed to set webhook"
                }
            )
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/telegram")
async def delete_telegram_webhook(
    handler: WebhookHandler = Depends(get_webhook_handler)
):
    """
    Delete the Telegram webhook.
    
    This endpoint removes the current webhook configuration.
    Useful for switching between webhook and polling modes.
    
    Args:
        handler: Webhook handler dependency
        
    Returns:
        Success or failure response
    """
    try:
        # Ensure bot is initialized
        await handler.ensure_initialized()
        
        # Delete the webhook
        success = await handler.telegram_bot.delete_webhook()
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Webhook deleted successfully"
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Failed to delete webhook"
                }
            )
            
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Additional utility functions for webhook management

async def setup_telegram_webhook(base_url: str) -> bool:
    """
    Setup Telegram webhook during application startup.
    
    Args:
        base_url: Base URL for the webhook endpoint
        
    Returns:
        True if successful, False otherwise
    """
    try:
        webhook_url = f"{base_url}/webhook/telegram"
        bot = get_bot()
        
        # Initialize bot if needed
        if not bot.application:
            await bot.initialize()
        
        # Set the webhook
        success = await bot.set_webhook(webhook_url)
        
        if success:
            logger.info(f"Telegram webhook configured: {webhook_url}")
        else:
            logger.error("Failed to configure Telegram webhook")
            
        return success
        
    except Exception as e:
        logger.error(f"Error setting up Telegram webhook: {e}")
        return False


async def cleanup_webhooks():
    """
    Cleanup webhooks during application shutdown.
    """
    try:
        bot = get_bot()
        
        if bot.application:
            await bot.delete_webhook()
            await bot.shutdown()
            
        logger.info("Webhook cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during webhook cleanup: {e}")


# Export the router and utility functions
__all__ = [
    "router", 
    "WebhookHandler", 
    "setup_telegram_webhook", 
    "cleanup_webhooks"
] 