from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.bot.telegram_bot import AthenaTelegramBot
from src.config.settings import Settings

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

# Initialize Telegram bot
bot = AthenaTelegramBot()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook requests."""
    try:
        update = await request.json()
        await bot.handle_update(update)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 