import logging

from aiogram import types, F, Router, Bot
from aiogram.filters import Command

# Assuming new_chat_utility is the adapted function in ai_res.py
from .ai_res import new_chat_utility 
# Assuming channel_log is adapted for Aiogram and bot_stats is handled
from modules.chatlogs import channel_log 
# For bot_stats, it's better to handle it via middleware or directly in run.py if it's a global state.
# For this example, I'll comment out direct bot_stats manipulation here.
# from run import bot_stats # Avoid direct import from run.py due to potential circularity

logger = logging.getLogger(__name__)
ai_models_router = Router()

NEWCHAT_COMMANDS = ["newchat", "reset", "new_conversation", "clear_chat", "new"]

@ai_models_router.message(Command(commands=NEWCHAT_COMMANDS))
async def new_chat_command_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    
    # bot_stats handling:
    # If bot_stats is managed via dp.workflow_data:
    # from aiogram import Dispatcher
    # dp = Dispatcher.get_current()
    # if dp and "bot_stats" in dp.workflow_data:
    #     dp.workflow_data["bot_stats"]["active_users"].add(user_id)
    # else:
    #     logger.warning("bot_stats not found in dispatcher workflow_data for /newchat command.")
    # For now, direct manipulation is avoided here.
    
    logger.info(f"User {user_id} initiated /newchat command.")
    
    # Call the utility function from ai_res.py
    await new_chat_utility(bot, message) 
    
    # Log to channel (assuming channel_log is Aiogram compatible)
    # The command used might be any of the aliases, so log a generic "/newchat" or the specific command.
    command_used = message.text.split()[0] if message.text else "/newchat" # Get the actual command like /new or /reset
    await channel_log(bot, message, command_used) # Pass Aiogram bot and message

# Note: The original run.py handler for /newchat also updated bot_stats.
# This should be handled either by passing bot_stats to this handler (e.g., via middleware)
# or by having a central mechanism for stats updates.
# The channel_log function also needs to be Aiogram compatible.
