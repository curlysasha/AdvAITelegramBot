import asyncio
import logging
from logging.handlers import RotatingFileHandler 
import os
import config
import datetime 

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# --- Scheduler Function Imports ---
# Assuming these functions are defined and Aiogram compatible
from modules.image.image_generation import get_cleanup_scheduler_task_coro as get_img_gen_cleanup_coro
from modules.image.inline_image_generation import get_inline_cleanup_scheduler_task_coro as get_inline_img_cleanup_coro
from modules.models.inline_ai_response import get_inline_ai_cleanup_scheduler_task_coro # Renamed for clarity

# --- Restart Check ---
from modules.admin.restart import check_restart_marker

# --- Filter Imports ---
from filters.custom_filters import IsChatTextFilter # For private text message handler
from aiogram.filters import ChatTypeFilter # For private chat type filter

# --- Router Imports ---
from modules.user.start import start_router
from modules.user.help import help_router
from modules.user.commands import commands_router
from modules.user.global_setting import global_settings_router
from modules.user.settings import settings_router
from modules.user.lang_settings import lang_settings_router
from modules.user.assistant import assistant_settings_router
from modules.user.user_support import user_support_router
from modules.user.dev_support import dev_support_router

from modules.speech.handlers import speech_router

from modules.image.img_to_text import img_to_text_router
from modules.image.image_generation import image_gen_router
from modules.image.handlers import image_message_router
from modules.image.inline_image_generation import route_inline_query # Inline query handler function

from modules.admin.restart import restart_router
from modules.admin.handlers import admin_commands_router, admin_callbacks_router

from modules.maintenance import maintenance_router

from modules.group.new_group import group_events_router
from modules.user.group_start import group_start_router # Handles /start in groups & its callbacks
from modules.group.handlers import group_commands_router # Handles other group commands & messages

from modules.models.handlers import ai_models_router # Handles /newchat etc.

# --- General Text & Unhandled Message Handlers (Example, if needed later) ---
# These would typically be defined in their own modules and imported if they exist.
# For now, we are only registering the specific module routers.
# from modules.core.handlers import unhandled_message_router # Example

# --- Model Imports (for aires) ---
from modules.models.ai_res import aires
from modules.maintenance import maintenance_check, maintenance_message # For private text handler

# --- Logging Setup ---
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
default_props = DefaultBotProperties(parse_mode=ParseMode.HTML) # Or ParseMode.MARKDOWN_V2
bot = Bot(token=config.BOT_TOKEN, default=default_props)
dp = Dispatcher()

# --- Bot Stats (Example of managing it in workflow_data) ---
# Initialize bot_stats in dispatcher's workflow_data
dp["bot_stats"] = {
    "messages_processed": 0,
    "images_generated": 0,
    "voice_messages_processed": 0,
    "active_users": set()
}
# Middleware can be used to pass bot_stats to handlers if preferred over direct dp access.


# --- on_startup / on_shutdown functions ---
async def on_startup_tasks(bot_instance: Bot, dispatcher: Dispatcher): # Added dispatcher argument
    logger.info("Bot starting up...")
    await check_restart_marker(bot_instance)
    
    # Initialize schedulers
    # These functions should return the coroutine to be created as a task
    img_gen_cleanup_coro = get_img_gen_cleanup_coro()
    inline_img_cleanup_coro = get_inline_img_cleanup_coro()
    inline_ai_cleanup_coro = get_inline_ai_cleanup_scheduler_task_coro()

    task1 = asyncio.create_task(img_gen_cleanup_coro())
    task2 = asyncio.create_task(inline_img_cleanup_coro())
    task3 = asyncio.create_task(inline_ai_cleanup_coro())
    
    # Store tasks in dispatcher workflow_data for access during shutdown
    if 'scheduled_tasks' not in dispatcher.workflow_data:
        dispatcher.workflow_data['scheduled_tasks'] = []
    dispatcher.workflow_data['scheduled_tasks'].extend([task1, task2, task3])
    logger.info("Background cleanup schedulers started.")

async def on_shutdown_tasks(bot_instance: Bot, dispatcher: Dispatcher): # Added dispatcher argument
    logger.info("Bot shutting down...")
    if 'scheduled_tasks' in dispatcher.workflow_data:
        for task in dispatcher.workflow_data['scheduled_tasks']:
            if not task.done():
                task.cancel()
        # Wait for tasks to cancel (with a timeout)
        try:
            await asyncio.wait_for(
                asyncio.gather(*[task for task in dispatcher.workflow_data['scheduled_tasks'] if not task.done()], return_exceptions=True),
                timeout=5.0  # Wait up to 5 seconds for tasks to cancel
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for scheduled tasks to cancel during shutdown.")
    logger.info("Background cleanup schedulers stopped.")


# --- Main function ---
async def main():
    # Register startup and shutdown handlers
    # Pass dispatcher to on_startup/on_shutdown if they need it (e.g., for workflow_data)
    dp.startup.register(lambda bot_instance: on_startup_tasks(bot_instance, dp))
    dp.shutdown.register(lambda bot_instance: on_shutdown_tasks(bot_instance, dp))

    # Register all routers
    # User-facing features first
    dp.include_router(start_router) 
    dp.include_router(help_router)
    dp.include_router(commands_router)
    
    # Settings sub-menus
    dp.include_router(settings_router) 
    dp.include_router(lang_settings_router)
    dp.include_router(assistant_settings_router)
    dp.include_router(user_support_router)
    dp.include_router(dev_support_router)
    
    # Global settings command (can be before or after specific settings menus)
    dp.include_router(global_settings_router) 

    # Core model interactions (e.g. /newchat)
    dp.include_router(ai_models_router)

    # Functional modules
    dp.include_router(speech_router)
    
    dp.include_router(img_to_text_router) # Callbacks for img_to_text results
    dp.include_router(image_gen_router)   # /generate command and image style/feedback callbacks
    dp.include_router(image_message_router) # Handles direct photo messages

    # Group specific handlers
    dp.include_router(group_events_router) # Handles bot being added to group
    dp.include_router(group_start_router)  # Handles /start in group & its menus
    dp.include_router(group_commands_router) # Handles other group commands like /ai, /gleave, replies

    # Admin and Maintenance features (often registered with higher precedence if they override common commands for admins)
    # Or registered based on specificity. For now, adding them here.
    dp.include_router(maintenance_router) 
    dp.include_router(restart_router)
    dp.include_router(admin_commands_router) # Admin text commands
    dp.include_router(admin_callbacks_router) # Admin callback query handlers

    # Register inline query handler directly to the dispatcher
    # The handler function `route_inline_query` decides further routing between image/AI inline.
    dp.inline_query.register(route_inline_query)
    logger.info("Inline query handler registered.")

    # Potentially, generic message handlers (text, unhandled commands) would be last
    # dp.include_router(unhandled_message_router) # Example

    # --- Register main private text message handler (should be after commands) ---
    # This handler uses dp directly as it's defined in run.py
    @dp.message(IsChatTextFilter(), ChatTypeFilter(chat_type=["private"]))
    async def private_text_message_handler(message: types.Message, bot: Bot):
        user_id = message.from_user.id
        # Maintenance check
        if await maintenance_check(user_id): # Assumes maintenance_check is Aiogram compatible
            maint_msg = await maintenance_message(user_id) # Assumes maintenance_message is Aiogram compatible
            await message.answer(maint_msg) # Use answer for new message
            return

        # Update bot_stats from dp.workflow_data
        # Ensure bot_stats is initialized in dp workflow_data
        if "bot_stats" in dp.workflow_data:
            dp.workflow_data["bot_stats"]["messages_processed"] += 1
            dp.workflow_data["bot_stats"]["active_users"].add(user_id)
        else:
            logger.warning("bot_stats not found in dp.workflow_data for private_text_message_handler")

        logger.info(f"Processing private text message from user {user_id}")
        await aires(bot, message) # Call aires, assumed Aiogram compatible

    # --- Miscellaneous Callback Handler (for simple acknowledgements) ---
    # Example: Handles callbacks that only need an answer() like headers
    # This should be registered after all specific callback routers
    misc_callback_data_to_ack = [
        "admin_header_ignore", 
        "features_header_ignore", 
        "admin_tools_header_ignore"
        # Add any other simple ack-only callback data here
    ]
    # Check if these were already handled in maintenance.py
    # maintenance.py already handles these with:
    # @maintenance_router.callback_query(F.data.in_({"admin_header_ignore", "features_header_ignore", "admin_tools_header_ignore"}))
    # async def ignore_header_callbacks(callback_query: types.CallbackQuery):
    #    await callback_query.answer()
    # So, no need for a separate handler here if they are in maintenance_router.
    # If there were others, they'd be added here.
    # For now, this section can be removed if all such callbacks are in their respective modules.

    logger.info("🤖 Advanced AI Telegram Bot (Aiogram) starting polling...")
    print("🤖 Advanced AI Telegram Bot (Aiogram) starting polling...")
    print("✨ Optimized for performance and modern UI")
        
    # Start polling
    # Remove any updates that were received while the bot was offline
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, bot_stats=dp["bot_stats"]) # Pass bot_stats if needed by polling or handlers directly (though middleware/workflow_data is better)

if __name__ == "__main__":
    asyncio.run(main())
