import asyncio
import logging
from typing import Optional, Tuple, Union # Added Union
from datetime import datetime

from aiogram import Bot, types
from aiogram.enums import ChatType, ChatMemberStatus # For chat type and member status checks
from aiogram.exceptions import TelegramAPIError # For specific error handling

from pymongo import MongoClient

from config import LOG_CHANNEL as STCLOG, DATABASE_URL, ADMINS, OWNER_ID
# Assuming these are or will be Aiogram-compatible
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled 

logger = logging.getLogger(__name__)
# No router needed in this file if it only contains utility functions.
# Handlers will be in a separate group/handlers.py or admin/handlers.py file.

# MongoDB Client (Consider centralizing DB client initialization)
mongo_client = MongoClient(DATABASE_URL)  
db = mongo_client['aibotdb']  
groups_collection = db.groups 

async def is_group_admin_utility(bot: Bot, chat_id: int, user_id: int) -> bool: # Renamed for clarity
    """Check if a user is an admin or creator in a group using Aiogram."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except TelegramAPIError as e: 
        logger.error(f"Error checking group admin status for user {user_id} in chat {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking group admin status: {e}")
        return False

async def leave_group_utility(bot: Bot, chat_id_to_leave: int, leaving_user_id: int) -> Tuple[bool, str]:
    """
    Utility function for the bot to leave a specific group.
    Returns (success_status, message_to_reply_with).
    Called by an admin command handler.
    """
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    try:
        await bot.leave_chat(chat_id_to_leave)
        logger.info(f"Bot @{bot_username} left group {chat_id_to_leave} initiated by user {leaving_user_id}.")
        
        try:
            groups_collection.update_one(
                {"chat_id": chat_id_to_leave},
                {"$set": {
                    "left": True,
                    "left_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "left_by": leaving_user_id
                }},
                upsert=True 
            )
        except Exception as e_db:
            logger.error(f"Error updating database after leaving group {chat_id_to_leave}: {e_db}")

        if STCLOG:
            try:
                log_chat_id = int(STCLOG)
                await bot.send_message(
                    log_chat_id, 
                    f"#GroupLeave\nBot: @{bot_username}\nGroup ID: {chat_id_to_leave}\nInitiated by: User {leaving_user_id}"
                )
            except ValueError: logger.error(f"Invalid STCLOG channel ID: {STCLOG}")
            except Exception as e_log: logger.error(f"Failed to send leave log to STCLOG: {e_log}")
        
        return True, f"Left the group {chat_id_to_leave} successfully."

    except TelegramAPIError as e:
        logger.error(f"Telegram API error leaving group {chat_id_to_leave}: {e}")
        return False, f"Failed to leave group {chat_id_to_leave}. API Error: {e.message}"
    except Exception as e:
        logger.error(f"Unexpected error leaving group {chat_id_to_leave}: {e}")
        return False, f"Failed to leave group {chat_id_to_leave}. Error: {str(e)}"


async def get_invite_link_utility(bot: Bot, target_chat_id_str: str, requesting_user_id: int) -> Tuple[Optional[str], str]:
    """
    Utility function to create or get an invite link for a chat.
    Returns (invite_link_string_or_None, message_to_reply_with).
    Called by an admin command handler.
    """
    try:
        target_chat_id: Union[int, str]
        if target_chat_id_str.startswith("@"):
            target_chat_id = target_chat_id_str 
        else:
            try:
                target_chat_id = int(target_chat_id_str)
            except ValueError:
                return None, "Invalid chat ID format. Must be an integer or a @username."
        
        chat = await bot.get_chat(target_chat_id)
        chat_id_for_link = chat.id 
        chat_title = chat.title or f"Chat {chat_id_for_link}"

        invite_link_obj = await bot.create_chat_invite_link(chat_id=chat_id_for_link)
        
        link_info_text = (f"🔗 **Invite Link for {chat_title}**\n\n"
                          f"{invite_link_obj.invite_link}\n\n")
        if invite_link_obj.expire_date:
            link_info_text += f"Expires: {invite_link_obj.expire_date.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        else:
            link_info_text += "Expires: Never\n"
        link_info_text += f"Created by: Bot (requested by user {requesting_user_id})"

        return invite_link_obj.invite_link, link_info_text

    except TelegramAPIError as e:
        logger.error(f"Telegram API error getting invite link for {target_chat_id_str}: {e}")
        return None, f"Failed to get invite link for {target_chat_id_str}. Error: {e.message}"
    except Exception as e:
        logger.error(f"Unexpected error getting invite link for {target_chat_id_str}: {e}")
        return None, f"Failed to get invite link for {target_chat_id_str}. Error: {str(e)}"

# The `leave_group` function that takes message.chat.id (for leaving current group)
# will be implemented as a command handler in `group/handlers.py` or `admin/handlers.py`
# which might call `is_group_admin_utility` for permission checks.
# The original file had a `leave_group` that seemed to operate on the current chat context.
# That logic is better placed in a handler that then calls a utility if needed.
# The `leave_group_utility` here is for targeted leaving by ID.
