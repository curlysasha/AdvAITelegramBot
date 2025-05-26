import os
import sys
import logging
import asyncio
import time

from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# Assuming IsAdminFilter is in filters.admin_filters and ADMINS is in config
from filters.admin_filters import IsAdminFilter 

logger = logging.getLogger(__name__)
restart_router = Router()

RESTART_MARKER_FILE = "restart_marker.txt" # Define at module level

@restart_router.message(Command("restart"), IsAdminFilter())
async def restart_command_handler(message: types.Message, bot: Bot): # bot: Bot is not used but good practice
    user_name = message.from_user.username or message.from_user.first_name
    
    restart_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, Restart Now", callback_data="confirm_restart"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_restart")
        ]
    ])
    
    await message.answer(
        f"🔄 **Restart Confirmation**\n\n"
        f"Are you sure you want to restart the bot, {user_name}?\n\n"
        "All current operations will be interrupted and the bot will be unavailable for a few seconds.",
        reply_markup=restart_keyboard,
        parse_mode="Markdown"
    )
    logger.info(f"Admin {message.from_user.id} requested restart confirmation")

@restart_router.callback_query(F.data.in_({"confirm_restart", "cancel_restart"}), IsAdminFilter())
async def handle_restart_callback_handler(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot is not used here
    # IsAdminFilter already applied by the router decorator

    if callback_query.data == "confirm_restart":
        try:
            await callback_query.message.edit_text(
                "🔄 **Restarting Bot**\n\n"
                "The bot is shutting down and will restart momentarily...\n\n"
                "This typically takes 5-10 seconds. Thanks for your patience.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error editing message for restart confirmation: {e}")
            # Attempt to send a new message if edit fails
            try:
                await callback_query.message.answer(
                    "🔄 **Restarting Bot**\n\n"
                    "The bot is shutting down and will restart momentarily...",
                    parse_mode="Markdown"
                )
            except Exception as e_send:
                 logger.error(f"Error sending new message for restart confirmation: {e_send}")


        logger.warning(f"Admin {callback_query.from_user.id} initiated bot restart")
        await asyncio.sleep(1) 
        await _perform_restart_logic(callback_query) 
        
    elif callback_query.data == "cancel_restart":
        try:
            await callback_query.message.edit_text(
                "✅ **Restart Cancelled**\n\n"
                "Bot restart has been cancelled. The bot will continue to run normally.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error editing message for restart cancellation: {e}")
        logger.info(f"Admin {callback_query.from_user.id} cancelled restart")
    
    try:
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Error answering callback query for restart: {e}")


async def _perform_restart_logic(callback_query: types.CallbackQuery):
    try:
        script_path = sys.argv[0]
        logger.info(f"Preparing to restart with script: {script_path}")
        
        # Ensure message and chat objects exist before accessing their attributes
        chat_id_for_marker = callback_query.message.chat.id if callback_query.message and callback_query.message.chat else "unknown_chat"
        message_id_for_marker = callback_query.message.message_id if callback_query.message else "unknown_message"

        with open(RESTART_MARKER_FILE, "w") as f:
            restart_data = (f"{time.time()},{callback_query.from_user.id},"
                            f"{chat_id_for_marker},{message_id_for_marker}")
            f.write(restart_data)
            logger.info(f"Restart marker created with data: {restart_data}")
            os.fsync(f.fileno())
        
        logger.warning("🔄 BOT RESTARTING NOW...")
        await asyncio.sleep(1)
        
        python_executable = sys.executable
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception as e_flush:
            logger.debug(f"Error flushing stdio during restart: {e_flush}")
            
        os.execv(python_executable, [python_executable, script_path])
        
    except Exception as e:
        error_msg = f"Error during restart: {str(e)}"
        logger.error(error_msg)
        if callback_query.message: # Check if message exists
            try:
                await callback_query.message.edit_text(
                    f"❌ **Restart Failed**\n\n"
                    f"An error occurred: {str(e)}\n\n"
                    f"Manual restart may be required.",
                    parse_mode="Markdown"
                )
            except Exception as e_edit_fail:
                 logger.error(f"Failed to edit message about restart failure: {e_edit_fail}")

async def check_restart_marker(bot: Bot): 
    try:
        if not os.path.exists(RESTART_MARKER_FILE):
            logger.debug("No restart marker found - normal startup")
            return
            
        logger.info("Restart marker found - processing")
        
        with open(RESTART_MARKER_FILE, "r") as f:
            data = f.read().strip().split(",")
            
        if len(data) < 4:
            logger.warning(f"Restart marker file has invalid format: {data}")
            os.remove(RESTART_MARKER_FILE)
            return
            
        timestamp_str, user_id_str, chat_id_str, message_id_str = data
        
        # Validate chat_id and message_id before trying to use them
        if chat_id_str == "unknown_chat" or message_id_str == "unknown_message":
            logger.warning(f"Cannot send restart confirmation due to unknown chat/message ID in marker: {data}")
            os.remove(RESTART_MARKER_FILE)
            return

        restarted_at_orig = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(float(timestamp_str)))
        completed_at_now = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(time.time()))

        logger.info(f"Bot was restarted by admin {user_id_str} at {restarted_at_orig}")
        
        try:
            await bot.edit_message_text(
                chat_id=int(chat_id_str),
                message_id=int(message_id_str),
                text=(f"✅ **Bot Restarted Successfully!**\n\n"
                      f"Restart initiated at: {restarted_at_orig}\n"
                      f"Restart completed at: {completed_at_now}\n"
                      f"The bot is now fully operational."),
                parse_mode="Markdown"
            )
            logger.info(f"Sent restart confirmation to admin {user_id_str}")
        except Exception as e:
            logger.error(f"Failed to send restart confirmation: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error processing restart marker: {str(e)}")
    finally:
        if os.path.exists(RESTART_MARKER_FILE):
            try:
                os.remove(RESTART_MARKER_FILE)
                logger.info("Restart marker file deleted")
            except Exception as e_remove:
                logger.error(f"Failed to delete restart marker file: {e_remove}")
