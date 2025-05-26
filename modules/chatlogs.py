import os
import logging
import json
from datetime import datetime
from typing import Union, Optional

from aiogram import Bot, types # Aiogram imports
from aiogram.utils.markdown import hlink, hcode, hbold # For HTML formatting if needed

from config import LOG_CHANNEL, DATABASE_URL # Assuming LOG_CHANNEL is an int chat_id
from pymongo import MongoClient

# Setup logging (remains the same)
logger = logging.getLogger(__name__)

# MongoDB Client (Consider centralizing DB client initialization)
# This client is only used in user_log. If user_log is removed or DB part is refactored, this might not be needed here.
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb'] # Or your specific DB name
logs_collection = db.user_logs # Collection for user_log

async def channel_log(bot: Bot, event: Union[types.Message, types.CallbackQuery, types.InlineQuery], action_text: str, level: str = "INFO", additional_info: Optional[str] = None):
    """
    Send a standardized log message to the log channel using Aiogram types.
    """
    try:
        user_id: Optional[int] = None
        username: Optional[str] = None
        user_mention: str = "Unknown User"
        chat_id: Optional[int] = None
        chat_type_str: Optional[str] = None
        
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
            username = event.from_user.username
            user_mention = event.from_user.mention_html(event.from_user.full_name if event.from_user.full_name else f"User {user_id}")

        if isinstance(event, types.Message):
            chat_id = event.chat.id
            chat_type_str = str(event.chat.type)
        elif isinstance(event, types.CallbackQuery):
            if event.message: # CallbackQuery may not always have a message
                chat_id = event.message.chat.id
                chat_type_str = str(event.message.chat.type)
        elif isinstance(event, types.InlineQuery):
            # Inline queries don't have a chat context in the same way
            chat_id = None # Or set to user_id if that's the convention
            chat_type_str = "inline_query"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        tags = f"#{level.upper()}"
        if action_text.startswith('/'):
            tags += " #Command"
            command = action_text.split()[0].replace("/", "")
            tags += f" #{command.capitalize()}"
        else:
            action_category = action_text.split('_')[0] if '_' in action_text else action_text
            tags += f" #{action_category.capitalize()}"
        
        log_message_parts = [
            f"{hbold(tags)}",
            f"👤 User: {user_mention} (ID: {hcode(str(user_id)) if user_id else 'N/A'})",
            f"🎬 Action: {hcode(action_text)}",
        ]
        if chat_id and chat_type_str:
             log_message_parts.append(f"💬 Chat: {hcode(str(chat_id))} ({chat_type_str})")
        log_message_parts.append(f"⏱️ Time: {timestamp}")
        
        if additional_info:
            # Sanitize additional_info if it could contain HTML/Markdown special chars
            # For now, assuming it's plain text or pre-formatted.
            log_message_parts.append(f"📋 Details: {additional_info}") # Use hcode for details if they are raw data
            
        log_message_final = "\n".join(log_message_parts)
            
        if LOG_CHANNEL:
            try:
                await bot.send_message(chat_id=int(LOG_CHANNEL), text=log_message_final, parse_mode="HTML")
            except ValueError:
                logger.error(f"Invalid LOG_CHANNEL ID: {LOG_CHANNEL}")
            except Exception as e_send:
                logger.error(f"Failed to send log to channel {LOG_CHANNEL}: {e_send}")
        
        # Local Python logging
        local_log_msg = f"CHANNEL_LOG: Action='{action_text}' by UserID='{user_id}'"
        if additional_info: local_log_msg += f" Details='{additional_info}'"
        
        if level.upper() == "INFO": logger.info(local_log_msg)
        elif level.upper() == "WARNING": logger.warning(local_log_msg)
        elif level.upper() == "ERROR": logger.error(local_log_msg)
            
    except Exception as e:
        logger.error(f"General failure in channel_log function: {e}", exc_info=True)

async def user_log(bot: Bot, message: types.Message, query_text: str, response_text: Optional[str] = None):
    """
    Log user interactions (AI queries/responses) to DB and optionally to LOG_CHANNEL (for private chats).
    The `query_text` parameter is now explicit, replacing `message.text` directly from original.
    """
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        chat_type_str = str(message.chat.type)
        timestamp = datetime.now() # Store as datetime object for MongoDB
        
        truncated_query = query_text[:500] + "..." if query_text and len(query_text) > 500 else query_text
        truncated_response = response_text[:500] + "..." if response_text and len(response_text) > 500 else response_text
        
        # Log to LOG_CHANNEL only for private chats (as per original logic)
        if chat_type_str == "private" and LOG_CHANNEL:
            channel_msg_parts = [
                f"{hbold('#UserInteractionLog')}",
                f"👤 User: {message.from_user.mention_html(message.from_user.full_name)} (ID: {hcode(str(user_id))})",
                f"⏱️ Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"❓ Query: {hcode(truncated_query)}",
            ]
            if truncated_response:
                channel_msg_parts.append(f"💡 Response: {hcode(truncated_response)}")
            
            try:
                await bot.send_message(chat_id=int(LOG_CHANNEL), text="\n".join(channel_msg_parts), parse_mode="HTML")
            except ValueError: logger.error(f"Invalid LOG_CHANNEL ID for user_log: {LOG_CHANNEL}")
            except Exception as e_send_userlog: logger.error(f"Failed to send user_log to channel: {e_send_userlog}")
        
        local_log_entry = f"User {user_id} in chat {chat_id} ({chat_type_str}): Query='{truncated_query}'"
        logger.info(local_log_entry)
        
        # Save to MongoDB
        log_data = {
            "user_id": user_id, # Stored as int
            "chat_id": chat_id,
            "chat_type": chat_type_str,
            "query": query_text, # Store full query
            "response": response_text, # Store full response
            "timestamp": timestamp # Store as datetime object
        }
        
        try:
            logs_collection.insert_one(log_data)
            logger.debug(f"Saved user interaction log to database for user {user_id}")
        except Exception as e_db:
            logger.error(f"Failed to save user_log to MongoDB for user {user_id}: {e_db}")
            
    except Exception as e:
        logger.error(f"General failure in user_log function: {e}", exc_info=True)

async def error_log(bot: Bot, function_tag: str, error_message_str: str, context: Optional[str] = None, user_id: Optional[int] = None, message_obj: Optional[types.Message] = None):
    """
    Log errors to LOG_CHANNEL and local logger.
    `function_tag` replaces `error_type` for more clarity.
    `error_message_str` replaces `error_message`.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        channel_msg_parts = [
            f"{hbold('#ERROR')} {hbold(f'#{function_tag.upper()}')}",
            f"⏱️ Time: {timestamp}",
            f"❗ Error: {hcode(str(error_message_str))}",
        ]
        
        if context:
            # Sanitize context or ensure it's plain text
            safe_context = str(context)[:1000] # Truncate context
            channel_msg_parts.append(f"📄 Context: {hcode(safe_context)}")
            
        actual_user_id = user_id
        if message_obj and message_obj.from_user: # Prefer user_id from message_obj if available
            actual_user_id = message_obj.from_user.id
        
        if actual_user_id:
            channel_msg_parts.append(f"👤 User ID: {hcode(str(actual_user_id))}")
            
        if LOG_CHANNEL:
            try:
                await bot.send_message(chat_id=int(LOG_CHANNEL), text="\n".join(channel_msg_parts), parse_mode="HTML")
            except ValueError: logger.error(f"Invalid LOG_CHANNEL ID for error_log: {LOG_CHANNEL}")
            except Exception as e_send_errlog: logger.error(f"Failed to send error_log to channel: {e_send_errlog}")
        
        local_error_log_msg = f"BOT_ERROR: Tag='{function_tag}' Error='{error_message_str}'"
        if context: local_error_log_msg += f" Context='{context}'"
        if actual_user_id: local_error_log_msg += f" UserID='{actual_user_id}'"
        logger.error(local_error_log_msg)
        
    except Exception as e:
        # This is the logger's own error handling, should be very robust
        logger.critical(f"ULTIMATE FAILURE in error_log function itself: {e}. Original error was Tag='{function_tag}', Msg='{error_message_str}'", exc_info=True)
