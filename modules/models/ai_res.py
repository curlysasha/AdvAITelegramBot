import logging
from typing import List, Dict, Optional, Generator

from aiogram import Bot, types
from aiogram.enums import ChatAction
import asyncio # For asyncio.to_thread

from g4f.client import Client as GPTClient
# Assuming these are or will be Aiogram-compatible
from modules.core.database import get_history_collection
from modules.chatlogs import user_log, error_log
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled

logger = logging.getLogger(__name__)

# Initialize the GPT client
# Consider making provider and model configurable
gpt_client = GPTClient(provider="PollinationsAI") 

# DEFAULT_SYSTEM_MESSAGE structure (full content should be used in actual deployment)
DEFAULT_SYSTEM_MESSAGE: List[Dict[str, str]] = [
    {"role": "system", "content": "I'm your advanced AI assistant (@AdvChatGptBot)..."},
    {"role": "assistant", "content": "🎨 **Image Generation**\n..."},
    {"role": "user", "content": "Can you create an image of a futuristic city?"},
    {"role": "assistant", "content": "I'll help you generate that image..."},
    # ... (Include other essential default messages)
]

# --- Core AI Response Functions ---
def get_response_from_model(history: List[Dict[str, str]]) -> str:
    try:
        if not isinstance(history, list): history = [{"role": "user", "content": str(history)}]
        if not history: history = DEFAULT_SYSTEM_MESSAGE.copy()
        for i, msg in enumerate(history):
            if not isinstance(msg, dict): history[i] = {"role": "user", "content": str(msg)}
        
        # Assuming gpt_client.chat.completions.create is synchronous
        # For Aiogram, if this is blocking, it should be run in an executor:
        # response = await asyncio.get_event_loop().run_in_executor(None, lambda: gpt_client.chat.completions.create(...))
        response = gpt_client.chat.completions.create(model="gpt-4o", messages=history)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating G4F response: {e}")
        return "I'm experiencing technical difficulties. Please try again in a moment."

def get_streaming_response_from_model(history: List[Dict[str, str]]) -> Optional[Generator]:
    try:
        if not isinstance(history, list): history = [{"role": "user", "content": str(history)}]
        if not history: history = DEFAULT_SYSTEM_MESSAGE.copy()
        for i, msg in enumerate(history):
            if not isinstance(msg, dict): history[i] = {"role": "user", "content": str(msg)}
        
        # As above, if blocking, needs executor for Aiogram
        return gpt_client.chat.completions.create(model="gpt-4o", messages=history, stream=True)
    except Exception as e:
        logger.error(f"Error generating G4F streaming response: {e}")
        return None

def sanitize_markdown(text: str) -> str: # Keep as is
    backticks_opened = text.count('```')
    if backticks_opened % 2 != 0: text += '\n```'
    single_backticks = text.count('`') - (backticks_opened * 3)
    if single_backticks % 2 != 0: text += '`'
    if text.count('*') % 2 != 0: text += '*'
    if text.count('[') > text.count(']'): text += ']'
    if text.count('(') > text.count(')'): text += ')'
    return text

# --- Main AI Response Handler Function (Adapted for Aiogram) ---
async def aires(bot: Bot, message: types.Message, custom_prompt: Optional[str] = None):
    user_id = message.from_user.id
    if await maintenance_check(user_id) or not await is_feature_enabled("ai_response", user_id=user_id):
        maint_msg_text = await maintenance_message(user_id)
        await message.answer(maint_msg_text)
        return

    temp_msg = None
    query_text = custom_prompt if custom_prompt else (message.text or message.caption or "")
    if not query_text:
        # If called with a message that has no text/caption and no custom_prompt
        await message.answer("I need some text to respond to!")
        return

    try:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        temp_msg = await message.answer("⏳") 
        
        history_collection = get_history_collection()
        
        def _get_history_sync():
            return history_collection.find_one({"user_id": user_id})
        user_history_doc = await asyncio.to_thread(_get_history_sync)
        
        history = user_history_doc['history'] if user_history_doc and 'history' in user_history_doc and isinstance(user_history_doc['history'], list) else DEFAULT_SYSTEM_MESSAGE.copy()
        history.append({"role": "user", "content": query_text})

        # For Aiogram, blocking calls should be run in an executor
        # loop = asyncio.get_event_loop()
        # ai_response_content = await loop.run_in_executor(None, get_response_from_model, history)
        # loop = asyncio.get_event_loop()
        # ai_response_content = await loop.run_in_executor(None, get_response_from_model, history)
        ai_response_content = await asyncio.to_thread(get_response_from_model, history)


        if not ai_response_content:
            ai_response_content = "I'm sorry, I couldn't generate a response for that."
            # Optionally log this specific failure case

        history.append({"role": "assistant", "content": ai_response_content})
        
        def _update_history_sync():
            history_collection.update_one({"user_id": user_id}, {"$set": {"history": history}}, upsert=True)
        await asyncio.to_thread(_update_history_sync)
        
        # Consider using specific parse_mode if AI responses are expected to contain Markdown/HTML
        await temp_msg.edit_text(ai_response_content, disable_web_page_preview=True) 
        
        await user_log(bot, message, f"\nUser: {query_text}\nAI: {ai_response_content}") # Assumes user_log is adapted

    except Exception as e:
        logger.error(f"Error in aires function: {e}")
        await error_log(bot, "aires_general_error", str(e), user_id, message_obj=message) # Assumes error_log adapted
        error_reply = "I'm experiencing technical difficulties. Please try again in a moment."
        if temp_msg:
            await temp_msg.edit_text(error_reply)
        else:
            await message.answer(error_reply)

# --- New Chat Function (Adapted for Aiogram) ---
async def new_chat_utility(bot: Bot, message: types.Message): # Renamed to avoid conflict if imported directly by handler
    try:
        user_id = message.from_user.id
        history_collection = get_history_collection()
        
        def _update_history_for_new_chat_sync():
            history_collection.update_one(
                {"user_id": user_id},
                {"$set": {"history": DEFAULT_SYSTEM_MESSAGE.copy()}},
                upsert=True 
            )
        await asyncio.to_thread(_update_history_for_new_chat_sync)
        
        await message.answer(
            "🔄 **Conversation Reset**\n\nYour chat history has been cleared. Ready for a fresh conversation!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in new_chat_utility function: {e}")
        await error_log(bot, "new_chat_error", str(e), message.from_user.id, message_obj=message)
        await message.answer(f"Error clearing chat history: {str(e)}")
