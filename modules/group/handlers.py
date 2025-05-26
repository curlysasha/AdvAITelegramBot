import logging

from aiogram import types, F, Router, Bot
from aiogram.filters import Command, ChatTypeFilter
from aiogram.enums import ChatType, ParseMode

# Assuming these are or will be Aiogram-compatible
from filters.admin_filters import IsAdminFilter
from filters.custom_filters import IsReplyToBotFilter, IsNotCommandFilter # Assuming these exist

from modules.group.group_settings import leave_group_utility, get_invite_link_utility, is_group_admin_utility
from modules.group.group_info import get_user_info_utility
from modules.models.ai_res import aires # Main AI response function
from modules.maintenance import maintenance_check, is_feature_enabled, maintenance_message
from modules.chatlogs import channel_log, user_log, error_log # Logging utilities

logger = logging.getLogger(__name__)
group_commands_router = Router()

# --- Admin Commands for Group Management ---

@group_commands_router.message(Command("gleave"), IsAdminFilter())
async def group_leave_command_handler(message: types.Message, bot: Bot):
    # Command can be /gleave <chat_id_to_leave> or /gleave (to leave current chat if it's a group)
    command_parts = message.text.split()
    chat_to_leave_id: int

    if len(command_parts) > 1:
        try:
            chat_to_leave_id = int(command_parts[1])
        except ValueError:
            await message.reply("Invalid chat ID provided for /gleave.")
            return
    elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        chat_to_leave_id = message.chat.id
    else:
        await message.reply("Please use /gleave <chat_id> or run /gleave in the target group.")
        return

    success, reply_text = await leave_group_utility(bot, chat_to_leave_id, message.from_user.id)
    await message.reply(reply_text)
    if success:
        await channel_log(bot, message, f"/gleave successful for {chat_to_leave_id}")
    else:
        await channel_log(bot, message, f"/gleave failed for {chat_to_leave_id}: {reply_text}", level="WARNING")


@group_commands_router.message(Command("uinfo"), IsAdminFilter())
async def user_info_command_handler(message: types.Message, bot: Bot):
    target_identifier: Optional[str] = None
    if message.reply_to_message and message.reply_to_message.from_user:
        # Target is the replied-to user, identifier not needed for utility
        pass # Utility will handle it via message.reply_to_message
    else:
        command_parts = message.text.split(None, 1)
        if len(command_parts) > 1:
            target_identifier = command_parts[1]
        else:
            await message.reply("Usage: /uinfo <user_id/@username> or reply to a user's message.")
            return

    info_text, keyboard = await get_user_info_utility(bot, message, target_identifier)
    await message.answer(info_text, reply_markup=keyboard, parse_mode="Markdown")
    await channel_log(bot, message, f"/uinfo for target: {target_identifier or message.reply_to_message.from_user.id if message.reply_to_message else 'None'}")

@group_commands_router.message(Command("invite"), IsAdminFilter())
async def group_invite_command_handler(message: types.Message, bot: Bot):
    command_parts = message.text.split(None, 1)
    if len(command_parts) < 2:
        await message.reply("Usage: /invite <chat_id/@username>")
        return
    target_chat_id_str = command_parts[1]

    invite_link, reply_text = await get_invite_link_utility(bot, target_chat_id_str, message.from_user.id)
    await message.reply(reply_text, parse_mode="Markdown", disable_web_page_preview= not invite_link) # Enable preview if link exists
    if invite_link:
        await channel_log(bot, message, f"/invite successful for {target_chat_id_str}")


# --- Generic Group Admin Command Handler (for logging/maintenance) ---
@group_commands_router.message(
    Command(["pin", "unpin", "promote", "demote", "ban", "warn"]), # Add other admin commands if needed
    ChatTypeFilter(chat_type=[ChatType.GROUP, ChatType.SUPERGROUP])
)
async def generic_group_admin_command_handler(message: types.Message, bot: Bot):
    # This handler primarily exists to acknowledge admin commands and apply global checks.
    # The actual execution of these commands is usually handled by Telegram permissions.
    if await maintenance_check(message.from_user.id): # User is not bot admin, but might be group admin
        # If bot is in maintenance, even group admins might not be able to use bot-intercepted commands.
        # However, Telegram native commands like /pin will still work if the user has TG perms.
        # This check is more for bot commands that *mimic* admin actions.
        # For true TG admin actions, this check might be too restrictive or unnecessary.
        # For now, keeping it simple: if bot is in maintenance, it won't process these.
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return

    logger.info(f"Group admin command '{message.text.split()[0]}' used by {message.from_user.id} in chat {message.chat.id}")
    # No further action needed by the bot itself for these commands usually.
    # Add logging to channel_log if desired.
    # await channel_log(bot, message, message.text.split()[0], f"Admin command used in group {message.chat.id}")
    pass # Let Telegram handle the command execution based on user's group permissions.


# --- Reply to Bot in Group Handler ---
@group_commands_router.message(
    IsReplyToBotFilter(), # Custom filter: checks if message.reply_to_message is from the bot
    ChatTypeFilter(chat_type=[ChatType.GROUP, ChatType.SUPERGROUP]),
    IsNotCommandFilter(), # Custom filter: ensures it's not a command
    F.text # Ensure it's a text message
)
async def handle_reply_to_bot_in_group_handler(message: types.Message, bot: Bot, bot_stats: Dict): # Added bot_stats
    user_id = message.from_user.id
    # Maintenance and feature checks
    if await maintenance_check(user_id) or not await is_feature_enabled("ai_response", user_id):
        maint_msg = await maintenance_message(user_id)
        await message.reply(maint_msg)
        return
        
    # bot_stats["messages_processed"] += 1 # Assuming bot_stats is accessible and managed
    # bot_stats["active_users"].add(user_id)
    logger.info(f"Processing reply to bot in group {message.chat.id} from user {user_id}")
    
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await user_log(bot, message, message.text) # Assuming user_log is adapted
    
    # Call aires, assuming it's adapted for Aiogram (takes bot, message)
    await aires(bot, message)


# --- Group AI Command Handler (/ai, /ask, /say) ---
@group_commands_router.message(
    Command(["ai", "ask", "say"]),
    ChatTypeFilter(chat_type=[ChatType.GROUP, ChatType.SUPERGROUP]),
    F.text # Ensure there's text after the command for the prompt
)
async def group_ai_command_handler(message: types.Message, bot: Bot, bot_stats: Dict): # Added bot_stats
    user_id = message.from_user.id
    # Maintenance and feature checks
    if await maintenance_check(user_id) or not await is_feature_enabled("ai_response", user_id):
        maint_msg = await maintenance_message(user_id)
        await message.reply(maint_msg)
        return
        
    # bot_stats["messages_processed"] += 1 # Assuming bot_stats is accessible
    # bot_stats["active_users"].add(user_id)
    logger.info(f"Processing group AI command from user {user_id} in chat {message.chat.id}")
    
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    command_text = message.text.split()[0] # e.g., /ai
    await channel_log(bot, message, command_text) # Log the command
    await user_log(bot, message, message.text) # Log the full message
    
    # Call aires, assuming it's adapted for Aiogram
    await aires(bot, message)

# Note: `bot_stats` handling is commented out as its injection mechanism (middleware/dp) isn't part of this scope.
# It needs to be properly managed in the main application setup for these counters to work.
