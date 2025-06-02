from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.bot.telegram_bot import AthenaTelegramBot
from src.config.settings import Settings
from src.api.webhook_handler import WebhookHandler

app = FastAPI(title="Athena Digital Assistant API")
settings = Settings()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize webhook handler
webhook_handler = WebhookHandler()

@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming Telegram webhook requests."""
    try:
        # Try to parse JSON body
        try:
            update = await request.json()
        except Exception as e:
            raise HTTPException(status_code=422, detail="Invalid JSON format")
        
        # Acknowledge the webhook immediately
        background_tasks.add_task(webhook_handler.process_telegram_update, update)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 