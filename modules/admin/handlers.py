import os
import datetime
import logging
from typing import Dict, Any, Union

from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext # For more complex state if needed, otherwise simple dict
from aiogram.types import FSInputFile # For sending files

from config import ADMINS # Assuming this is a list of int IDs
from filters.admin_filters import IsAdminFilter # The custom filter

# Assuming these modules are or will be Aiogram-compatible
# For bot_stats, it's often managed in the main dispatcher or passed via middleware
# For simplicity, if it's a global/importable dict, it could be imported.
# Let's assume bot_stats is accessible via dp.workflow_data or a similar mechanism.
# from run import bot_stats # This would be a circular import if run.py imports this router.

# --- Database & Service Imports ---
# (These will be called by the handlers)
import database.user_db as user_db # For announce_command
from modules.models.image_service import ImageService # For clear_user_cache
from modules.admin.user_management import handle_user_management # Assuming adapted for Aiogram
from modules.admin.user_history import (
    get_user_chat_history, 
    show_history_search_panel,
    handle_history_user_selection,
    handle_history_pagination,
    get_history_download,
    show_user_search_form
) # Assuming these are adapted for Aiogram

logger = logging.getLogger(__name__)

admin_commands_router = Router()
admin_callbacks_router = Router() # Separate router for callbacks for organization

# --- State management for admin text input (simple version) ---
# Stores user_id: {"state": "awaiting_user_id_for_history", "original_message_id": message.id}
admin_awaiting_input: Dict[int, Dict[str, Any]] = {}


# === COMMAND HANDLERS ===

@admin_commands_router.message(Command("stats"), IsAdminFilter())
async def stats_command_handler(message: types.Message, bot: Bot, bot_stats: Dict): # Assuming bot_stats is passed via middleware/dp
    # If bot_stats is not passed, this needs to be fetched, e.g. from dp.workflow_data
    # For example:
    # from aiogram import Dispatcher
    # dp = Dispatcher.get_current()
    # bot_stats = dp.workflow_data.get("bot_stats", {"messages_processed": 0, ...}) # Get it safely
    
    stats_text = (
        "📊 **Bot Statistics**\n\n"
        f"💬 Messages Processed: {bot_stats.get('messages_processed', 0)}\n"
        f"🖼️ Images Generated: {bot_stats.get('images_generated', 0)}\n"
        f"🎙️ Voice Messages: {bot_stats.get('voice_messages_processed', 0)}\n"
        f"👥 Active Users: {len(bot_stats.get('active_users', set()))}\n"
    )
    await message.answer(stats_text, parse_mode="Markdown")
    # Assuming channel_log is adapted and available if logging is needed here
    # await channel_log(bot, message, "/stats", "Admin requested bot statistics")

@admin_commands_router.message(Command(["announce", "broadcast", "acc"]), IsAdminFilter())
async def announce_command_handler(message: types.Message, bot: Bot):
    if not message.reply_to_message and len(message.text.split()) == 1:
        await message.answer(
            "⚠️ Please provide a message to broadcast.\n\n"
            "Example: `/announce Hello everyone! We've added new features.`\n"
            "Or reply to a message with `/announce`."
        )
        return

    text_to_broadcast = ""
    if message.reply_to_message:
        # Broadcasting the replied message (text, caption, or just forwarding)
        # This part needs careful implementation depending on what exactly needs to be broadcasted
        # For now, let's assume we take the text/caption of the replied message.
        if message.reply_to_message.text:
            text_to_broadcast = message.reply_to_message.text
        elif message.reply_to_message.caption:
            text_to_broadcast = message.reply_to_message.caption
        # Add more complex logic here if you need to forward the actual message (photos, videos etc.)
        # For now, focusing on text broadcast.
        if not text_to_broadcast:
            await message.answer("Cannot broadcast this type of message. Please provide text.")
            return
    else:
        text_to_broadcast = message.text.split(" ", 1)[1]

    logger.info(f"Admin {message.from_user.id} broadcasting: {text_to_broadcast[:50]}...")
    processing_msg = await message.answer("📣 Preparing to broadcast message...")
    
    # Assuming user_db.get_usernames_message is adapted for Aiogram
    # It would need to fetch users and send messages using the 'bot' instance.
    # This is a potentially long operation.
    # Consider running it in background or notifying about progress.
    # For now, direct await:
    await user_db.broadcast_message_to_users(bot, text_to_broadcast) # Assuming adapted function name
    
    await processing_msg.edit_text("✅ Broadcast sent to all users.")
    # await channel_log(bot, message, "/announce", "Admin broadcast message")

@admin_commands_router.message(Command("logs"), IsAdminFilter())
async def logs_command_handler(message: types.Message, bot: Bot): # bot is not used if only sending local file
    logger.info(f"Admin {message.from_user.id} requested logs")
    status_msg = await message.answer("📊 Retrieving logs...")
    
    main_log_file = os.path.join("logs", "bot_main.log") # Assuming this path is correct
    if os.path.exists(main_log_file):
        try:
            # Send the main log file directly
            await message.answer_document(
                document=FSInputFile(main_log_file),
                caption=f"📋 **Latest Bot Logs**\nAs of {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await status_msg.edit_text("✅ Logs sent.")
        except Exception as e:
            logger.error(f"Error sending log file: {e}")
            await status_msg.edit_text(f"❌ Error sending logs: {str(e)}")
    else:
        await status_msg.edit_text("❌ Log file not found.")
    # await channel_log(bot, message, "/logs", "Admin requested logs")

@admin_commands_router.message(Command(["clear_cache", "clearcache", "clear_images"])) # No admin filter in original
async def clear_user_cache_command_handler(message: types.Message, bot: Bot): # bot might not be needed by ImageService
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested to clear their image cache via command.")
    
    # Assuming ImageService.clear_user_image_cache is async or thread-safe
    success = await ImageService.clear_user_image_cache(user_id)
    
    if success:
        await message.answer("✅ **Your image cache has been cleared.**")
    else:
        await message.answer("ℹ️ **No image cache found for you to clear.**")
    # await channel_log(bot, message, "/clear_cache", "User cleared their image cache")


@admin_commands_router.message(Command("history"), IsAdminFilter())
async def history_command_handler(message: types.Message, bot: Bot):
    command_parts = message.text.split()
    if len(command_parts) < 2:
        # Prompt to use the interactive panel or provide User ID
        # For now, redirecting to the panel search.
        # Create a mock CallbackQuery object to pass to show_history_search_panel
        # This is a bit of a hack. Ideally, show_history_search_panel would accept a Message too.
        # Or, we send a message with a button that triggers the panel.
        # For now, let's send a message with a button.
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔍 Open History Panel", callback_data="admin_view_history")]
        ])
        await message.answer("Please specify a User ID or use the History Panel.", reply_markup=keyboard)
        return

    try:
        target_user_id = int(command_parts[1])
        status_msg = await message.answer(f"🔍 Retrieving chat history for user {target_user_id}...")
        # Assuming get_user_chat_history is adapted for Aiogram
        await get_user_chat_history(bot, message, target_user_id, status_msg) # Pass Aiogram message and bot
    except ValueError:
        await message.answer("❌ User ID must be an integer.")
    except Exception as e:
        logger.error(f"Error in /history command: {e}")
        await message.answer(f"❌ Error: {str(e)}")

# --- Admin Text Input Handler (for history search by ID) ---
@admin_commands_router.message(IsAdminFilter(), F.text) # Order matters, this should be after specific commands
async def admin_text_input_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    if user_id in admin_awaiting_input:
        state_data = admin_awaiting_input[user_id]
        if state_data.get("awaiting") == "user_id_for_history":
            logger.info(f"Admin {user_id} providing user ID for history: {message.text}")
            del admin_awaiting_input[user_id] # Clear state

            try:
                target_user_id_search = int(message.text.strip())
                # We need the original callback_query.message object to edit for status.
                # This is tricky. The original message that prompted this input was a callback_query.message.
                # We stored its ID. We might need to fetch it or send a new message.
                # For now, sending a new status message.
                status_msg = await message.answer(f"🔍 Searching history for user ID {target_user_id_search}...")
                
                # We need to pass a "message-like" object or a "callback_query-like" object
                # to get_user_chat_history if it expects to edit an existing message.
                # Let's assume get_user_chat_history is adapted to handle a new message for status.
                # Or, we adapt get_user_chat_history to accept chat_id and send new messages.
                # For this migration, we'll pass the current `message` object.
                await get_user_chat_history(bot, message, target_user_id_search, status_msg)
            except ValueError:
                await message.answer("❌ Invalid User ID format. Please enter numbers only.")
            except Exception as e:
                logger.error(f"Error processing admin text input for history: {e}")
                await message.answer(f"❌ Error: {str(e)}")
            return # Stop further processing

    # If not a special admin input, let other general text handlers (if any) process it.
    # Or, if admins should not trigger general handlers, add specific logic here.
    # For now, if no state matched, we do nothing specific.
    # If this handler is too broad, add more specific F.text filters or use FSM.


# === CALLBACK QUERY HANDLERS ===

# --- User Management Callbacks ---
@admin_callbacks_router.callback_query(F.data == "admin_users", IsAdminFilter())
async def admin_users_panel_callback(callback_query: types.CallbackQuery, bot: Bot):
    # Assuming handle_user_management is adapted for Aiogram
    await handle_user_management(bot, callback_query) 
    await callback_query.answer()

@admin_callbacks_router.callback_query(F.data.startswith("admin_users_filter_"), IsAdminFilter())
async def admin_users_filter_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        parts = callback_query.data.split("_") # admin_users_filter_TYPE_PAGE
        filter_type = parts[3]
        page = int(parts[4])
        # Assuming handle_user_management is adapted for Aiogram
        await handle_user_management(bot, callback_query, page, filter_type)
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing admin_users_filter callback data: {callback_query.data}, Error: {e}")
        await callback_query.answer("Error processing filter. Try again.", show_alert=True)
    await callback_query.answer()


# --- User History Callbacks ---
@admin_callbacks_router.callback_query(F.data == "admin_view_history", IsAdminFilter())
async def admin_view_history_panel_callback(callback_query: types.CallbackQuery, bot: Bot):
    # Assuming show_history_search_panel is adapted for Aiogram
    await show_history_search_panel(bot, callback_query)
    await callback_query.answer()

@admin_callbacks_router.callback_query(F.data.startswith("history_user_"), IsAdminFilter())
async def history_user_select_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        user_id = int(callback_query.data.split("_")[2])
        # Assuming handle_history_user_selection is adapted
        await handle_history_user_selection(bot, callback_query, user_id)
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing history_user_ callback data: {callback_query.data}, Error: {e}")
        await callback_query.answer("Error processing selection.", show_alert=True)
    await callback_query.answer() # Acknowledge, function above handles edits

@admin_callbacks_router.callback_query(F.data.startswith("history_page_"), IsAdminFilter())
async def history_page_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        parts = callback_query.data.split("_") # history_page_USERID_PAGE
        user_id = int(parts[2])
        page_num = int(parts[3])
        # Assuming handle_history_pagination is adapted
        await handle_history_pagination(bot, callback_query, user_id, page_num)
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing history_page_ callback data: {callback_query.data}, Error: {e}")
        await callback_query.answer("Error processing pagination.", show_alert=True)
    await callback_query.answer() # Acknowledge

@admin_callbacks_router.callback_query(F.data == "history_search", IsAdminFilter()) # Back to search panel
async def history_back_to_search_callback(callback_query: types.CallbackQuery, bot: Bot):
    await show_history_search_panel(bot, callback_query)
    await callback_query.answer()

@admin_callbacks_router.callback_query(F.data.startswith("history_download_"), IsAdminFilter())
async def history_download_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        user_id = int(callback_query.data.split("_")[2])
        # Assuming get_history_download is adapted
        await get_history_download(bot, callback_query, user_id)
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing history_download_ callback data: {callback_query.data}, Error: {e}")
        await callback_query.answer("Error processing download.", show_alert=True)
    # get_history_download likely sends a message, so answer might not be needed or could be just .answer()

@admin_callbacks_router.callback_query(F.data == "admin_search_user", IsAdminFilter()) # Prompt for user ID
async def history_prompt_user_search_callback(callback_query: types.CallbackQuery, bot: Bot):
    # Set state for admin_text_input_handler
    admin_awaiting_input[callback_query.from_user.id] = {
        "awaiting": "user_id_for_history",
        "original_message_id": callback_query.message.message_id, # Store to potentially edit later or reference
        "chat_id": callback_query.message.chat.id
    }
    # Assuming show_user_search_form is adapted (it primarily edits a message to ask for input)
    await show_user_search_form(bot, callback_query) # This should edit the message
    await callback_query.answer("Please send the User ID.")


# --- Admin Panel Stats Callbacks (Example, if these were separate from maintenance.py) ---
# @admin_callbacks_router.callback_query(F.data == "admin_view_stats", IsAdminFilter())
# async def admin_view_stats_callback(callback_query: types.CallbackQuery, bot: Bot):
#     # Logic from modules.admin.handle_stats_panel or similar
#     # This seems to be covered by maintenance.py's admin panel now.
#     await callback_query.answer("Stats view (TBD)", show_alert=True)

# @admin_callbacks_router.callback_query(F.data == "admin_refresh_stats", IsAdminFilter())
# async def admin_refresh_stats_callback(callback_query: types.CallbackQuery, bot: Bot):
#     await callback_query.answer("Stats refresh (TBD)", show_alert=True)

# @admin_callbacks_router.callback_query(F.data == "admin_export_stats", IsAdminFilter())
# async def admin_export_stats_callback(callback_query: types.CallbackQuery, bot: Bot):
#     await callback_query.answer("Stats export (TBD)", show_alert=True)

# Note: The original run.py also had some admin panel callbacks handled directly.
# Many of these (like admin_panel, admin_view_stats, admin_users) are now routed to
# maintenance.py (for the panel itself) or user_management.py (via callbacks here).
# This structure centralizes admin command/callback handling.
# The `bot_stats` for the /stats command needs to be injected or made accessible.
# A common way is `dp["bot_stats"] = bot_stats_dict` in your main `run.py`
# and then accessing it in handlers via `dispatcher.get("bot_stats")` or middleware.
# For this migration, I'm using a placeholder `bot_stats: Dict` parameter.
# If using middleware: `async def stats_command_handler(message: types.Message, bot: Bot, bot_stats: Dict):`

# To make bot_stats accessible, you'd typically initialize it in run.py
# and pass it to the dispatcher's workflow data:
# dp["bot_stats"] = my_bot_stats_dictionary
# Then in handlers, you can access it:
# from aiogram import Dispatcher
# async def my_handler(message: types.Message, ..., bot_stats: dict):
# where middleware would inject bot_stats, or:
# dp = Dispatcher.get_current()
# stats = dp.workflow_data.get("bot_stats")

# The user_db.broadcast_message_to_users function needs to be created or adapted in user_db.py
# It should iterate through users and use `await bot.send_message(user_id, text_to_broadcast)`.
# Handling rate limits and errors during broadcast is crucial there.

# The functions from user_management.py and user_history.py (e.g., handle_user_management, get_user_chat_history)
# are assumed to be adapted to take Aiogram `Bot` and `CallbackQuery`/`Message` objects and perform
# their UI updates using Aiogram methods. This is a key dependency for these handlers to work.
