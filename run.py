import asyncio
import logging
from logging.handlers import RotatingFileHandler # Keep
import os
import config
import datetime # Keep for logging if needed, or remove if not used directly

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
# from aiogram.types import BotCommand # If needed later

# Import scheduler functions (adjust paths as necessary)
from modules.image.image_generation import start_cleanup_scheduler
from modules.image.inline_image_generation import cleanup_ongoing_generations as inline_cleanup_ongoing_generations
from modules.models.inline_ai_response import cleanup_ongoing_generations as ai_cleanup_ongoing_generations
# Import for check_restart_marker
from modules.admin.restart import check_restart_marker


# --- Logging Setup (as before) ---
# Ensure this is correctly placed.
if not os.path.exists("logs"):
    os.makedirs("logs")
MAIN_LOG_FILE = os.path.join("logs", "bot_main.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(MAIN_LOG_FILE, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# --- Bot and Dispatcher Initialization ---
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
# dp.workflow_data['scheduled_tasks'] = [] # Initialized in on_startup_tasks to be safe

# --- on_startup / on_shutdown functions ---
async def on_startup_tasks(bot_instance: Bot): # Renamed parameter
    logger.info("Starting background cleanup schedulers and restart check...")
    # Call check_restart_marker
    await check_restart_marker(bot_instance) # Pass the bot instance
    
    task1 = asyncio.create_task(start_cleanup_scheduler())
    task2 = asyncio.create_task(inline_cleanup_ongoing_generations())
    task3 = asyncio.create_task(ai_cleanup_ongoing_generations())
    
    if 'scheduled_tasks' not in dp.workflow_data:
        dp.workflow_data['scheduled_tasks'] = []
    dp.workflow_data['scheduled_tasks'].extend([task1, task2, task3])
    logger.info("Background cleanup schedulers and restart check complete.")

async def on_shutdown_tasks(bot_instance: Bot): # Renamed parameter
    logger.info("Stopping background cleanup schedulers...")
    if 'scheduled_tasks' in dp.workflow_data:
        for task in dp.workflow_data['scheduled_tasks']:
            if not task.done():
                task.cancel()
        # Wait for tasks to cancel
        await asyncio.gather(*[task for task in dp.workflow_data['scheduled_tasks'] if not task.done()], return_exceptions=True)
    logger.info("Background cleanup schedulers stopped.")


# --- Placeholder for handlers (to be added in later steps) ---
# For now, run.py will not have any handlers from Pyrogram.

# --- bot_stats dictionary ---
bot_stats = {
    "messages_processed": 0,
    "images_generated": 0,
    "voice_messages_processed": 0,
    "active_users": set()
}

# --- Main function ---
async def main():
    dp.startup.register(on_startup_tasks)
    dp.shutdown.register(on_shutdown_tasks)
    
    logger.info("🤖 Advanced AI Telegram Bot (Aiogram) starting...")
    print("🤖 Advanced AI Telegram Bot (Aiogram) starting...")
    print("✨ Optimized for performance and modern UI")
        
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
