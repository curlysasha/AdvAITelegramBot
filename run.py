import os
import sys
import config
import time
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.constants import ChatAction, ChatType
from modules.user.start import start, start_inline
from modules.user.help import help, help_inline
from modules.user.commands import command_inline
from modules.user.settings import settings_inline, settings_language_callback, change_voice_setting
from modules.user.settings import settings_voice_inlines
from modules.user.assistant import settings_assistant_callback, change_mode_setting
from modules.user.lang_settings import settings_langs_callback, change_language_setting
from modules.user.user_support import settings_support_callback, support_admins_callback, admin_panel_callback
from modules.user.dev_support import support_developers_callback
from modules.speech import text_to_voice, voice_to_text
from modules.image.img_to_text import extract_text_res, handle_show_text_callback, handle_followup_callback
from modules.maintenance import settings_others_callback, handle_feature_toggle, handle_feature_info, maintenance_check, maintenance_message, handle_donation
from modules.group.group_settings import leave_group, invite_command
from modules.feedback_nd_rating import rate_command, handle_rate_callback
from modules.group.group_info import info_command
from modules.models.ai_res import aires, new_chat
from modules.image.image_generation import generate_command, handle_image_feedback, start_cleanup_scheduler, handle_generate_command
from modules.image.inline_image_generation import handle_inline_query, cleanup_ongoing_generations
from modules.models.inline_ai_response import cleanup_ongoing_generations as ai_cleanup_ongoing_generations
from modules.chatlogs import channel_log, user_log, error_log
from modules.user.global_setting import global_setting_command
from modules.speech.voice_to_text import handle_voice_toggle
from modules.admin.restart import restart_command, handle_restart_callback, check_restart_marker
import modules.models.user_db as user_db
import asyncio
import logging
import datetime
from logging.handlers import RotatingFileHandler
import json
from modules.models.image_service import ImageService

# Configure logging
MAIN_LOG_FILE = os.path.join("logs", "bot_main.log")
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

for handler in logger.handlers[:]:
    logger.removeHandler(handler)

rotating_file_handler = RotatingFileHandler(
    MAIN_LOG_FILE,
    maxBytes=10*1024*1024,
    backupCount=5,
    encoding='utf-8'
)
rotating_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger.addHandler(rotating_file_handler)
logger.addHandler(stream_handler)

# Clean up sessions directory if exists
if os.path.exists("sessions"):
    logger.info("Cleaning up sessions directory...")
    shutil.rmtree("sessions")

# Initialize bot application with custom timeout settings
from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=8,
    connect_timeout=30.0,
    read_timeout=30.0,
    write_timeout=30.0,
    http_version="1.1"
)
application = Application.builder().token(config.BOT_TOKEN).request(request).build()

# Track bot statistics
bot_stats = {
    "messages_processed": 0,
    "images_generated": 0,
    "voice_messages_processed": 0,
    "active_users": set()
}

# Add handlers
async def start_handler(update: Update, context):
    # Start cleanup schedulers
    cleanup_scheduler = start_cleanup_scheduler()
    cleanup_scheduler_task = asyncio.create_task(cleanup_scheduler())
    ongoing_generations_cleanup_task = asyncio.create_task(cleanup_ongoing_generations())
    ai_ongoing_generations_cleanup_task = asyncio.create_task(ai_cleanup_ongoing_generations())
    
    # Check for restart marker
    await check_restart_marker(update, context)
    
    bot_stats["active_users"].add(update.effective_user.id)
    
    if update.effective_chat.type == ChatType.PRIVATE:
        await start(update, context)
    else:
        from modules.user.group_start import group_start
        await group_start(update, context)
    
    await channel_log(update, context, "/start")

application.add_handler(CommandHandler("start", start_handler))
application.add_handler(CommandHandler("help", help))
application.add_handler(CommandHandler("settings", global_setting_command))
application.add_handler(CommandHandler("rate", rate_command))
application.add_handler(CommandHandler("newchat", new_chat))
application.add_handler(CommandHandler("generate", handle_generate_command))
application.add_handler(CommandHandler("gleave", leave_group))
application.add_handler(CommandHandler("invite", invite_command))
application.add_handler(CommandHandler("uinfo", info_command))
application.add_handler(CommandHandler("restart", restart_command))

# Add other handlers as needed...

if __name__ == "__main__":
    logger.info("🤖 Advanced AI Telegram Bot starting...")
    print("🤖 Advanced AI Telegram Bot starting...")
    print("✨ Optimized for performance and modern UI")
    application.run_polling()
