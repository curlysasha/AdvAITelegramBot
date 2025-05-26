import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any
import re 
import uuid # For unique IDs in InlineQueryResultArticle

from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError

# Assuming get_response_from_model is the adapted non-streaming function from ai_res.py
from modules.models.ai_res import get_response_from_model, DEFAULT_SYSTEM_MESSAGE # Added DEFAULT_SYSTEM_MESSAGE
# config.LOG_CHANNEL was not used here.

logger = logging.getLogger(__name__)

# --- Data Structures ---
ongoing_inline_ai_generations: Dict[str, Dict[str, Any]] = {} 
ai_response_cache: Dict[int, Dict[str, List[Any]]] = {} 
MAX_AI_CACHE_PER_USER = 10
temp_ai_query_cache: Dict[int, Dict[str, Any]] = {} 

# --- Helper Functions ---
def _create_ai_task_id(user_id: int, prompt: str) -> str:
    return hashlib.md5(f"{user_id}:ai_resp:{prompt}:{time.time()}".encode()).hexdigest()[:10]

def _format_ai_response_for_inline_article(response: str, prompt: str, bot_username: str) -> str:
    # This text will be the content of the message when a user clicks an inline result
    response_preview = response
    if len(response_preview) > 3800: 
        response_preview = response_preview[:3797] + "..."
    
    return (f"🤖 **AI Response**\n\n"
            f"📝 **Your Query**: {prompt}\n\n"
            f"🔍 **My Response**:\n{response_preview}\n\n"
            f"Shared via @{bot_username}")

# --- Cache Functions ---
def get_cached_ai_response_text(user_id: int, prompt: str) -> Optional[str]: # Renamed for clarity
    norm_prompt = re.sub(r'\s+', ' ', prompt.lower()).strip()
    if user_id in ai_response_cache and ai_response_cache[user_id]["responses"]:
        try:
            for i, cached_prompt in enumerate(ai_response_cache[user_id]["prompts"]):
                if re.sub(r'\s+', ' ', cached_prompt.lower()).strip() == norm_prompt:
                    return ai_response_cache[user_id]["responses"][i]
        except Exception as e:
            logger.error(f"Error during exact cache match for AI inline: {e}")

    if user_id in temp_ai_query_cache:
        if re.sub(r'\s+', ' ', temp_ai_query_cache[user_id]["query"].lower()).strip() == norm_prompt:
            return temp_ai_query_cache[user_id]["response_text"] # Store raw text
    return None

def add_ai_response_text_to_cache(user_id: int, prompt: str, raw_response_text: str): # Renamed
    if user_id not in ai_response_cache:
        ai_response_cache[user_id] = {"prompts": [], "responses": [], "timestamps": []}
    
    norm_prompt = re.sub(r'\s+', ' ', prompt.lower()).strip()
    for i, cached_prompt in enumerate(ai_response_cache[user_id]["prompts"]):
        if re.sub(r'\s+', ' ', cached_prompt.lower()).strip() == norm_prompt:
            ai_response_cache[user_id]["responses"][i] = raw_response_text
            ai_response_cache[user_id]["timestamps"][i] = time.time()
            return

    ai_response_cache[user_id]["prompts"].insert(0, prompt) # Store original prompt
    ai_response_cache[user_id]["responses"].insert(0, raw_response_text)
    ai_response_cache[user_id]["timestamps"].insert(0, time.time())
    if len(ai_response_cache[user_id]["prompts"]) > MAX_AI_CACHE_PER_USER:
        for key_list in ["prompts", "responses", "timestamps"]: ai_response_cache[user_id][key_list].pop()
    
    # Store raw response text in temp cache
    temp_ai_query_cache[user_id] = {"query": prompt, "response_text": raw_response_text, "timestamp": time.time()}


def clear_user_ai_inline_cache(user_id: int):
    if user_id in ai_response_cache: del ai_response_cache[user_id]
    if user_id in temp_ai_query_cache: del temp_ai_query_cache[user_id]
    logger.info(f"Cleared inline AI response cache for user {user_id}")

async def _generate_ai_response_for_inline(prompt: str) -> str: # Internal utility
    logger.info(f"Generating inline AI response with prompt: '{prompt}'")
    try:
        history = DEFAULT_SYSTEM_MESSAGE.copy() # Start with default system context
        history.append({"role": "user", "content": prompt})
        # loop = asyncio.get_event_loop()
        # response_content = await loop.run_in_executor(None, get_response_from_model, history)
        response_content = get_response_from_model(history) # Assuming g4f is async or non-blocking

        if not response_content:
            return "Sorry, I couldn't generate a response. Please try again."
        return response_content
    except Exception as e:
        logger.error(f"Error generating inline AI response: {e}")
        return f"Sorry, an error occurred: {str(e)}"

# --- Main Inline AI Query Handler ---
async def handle_inline_ai_query(bot: Bot, inline_query: types.InlineQuery, prompt: str):
    user_id = inline_query.from_user.id
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    if not prompt or len(prompt) < 3:
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="Prompt too short",
            input_message_content=types.InputTextMessageContent(message_text="🤔 Your prompt is too short for an AI response.")
        )], cache_time=1)
        return

    if prompt.lower() == "clear cache":
        clear_user_ai_inline_cache(user_id)
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="Cache Cleared",
            input_message_content=types.InputTextMessageContent(message_text="✅ Inline AI response cache cleared.")
        )], cache_time=1)
        return

    cached_response_text = get_cached_ai_response_text(user_id, prompt)
    if cached_response_text:
        formatted_text_for_message = _format_ai_response_for_inline_article(cached_response_text, prompt, bot_username)
        try:
            await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
                id=str(uuid.uuid4()), title="💡 AI Response (Cached)",
                description=f"Q: {prompt[:50]}...", # Show part of prompt in description
                input_message_content=types.InputTextMessageContent(
                    message_text=formatted_text_for_message, parse_mode="Markdown", disable_web_page_preview=True
                ),
                thumb_url="https://img.icons8.com/color/452/chatgpt.png" # Generic AI icon
            )], cache_time=300) # Longer cache for actual results
            return
        except TelegramAPIError as e: logger.error(f"Error answering with cached inline AI response: {e}")

    active_task_id = next((task_id for task_id, data in ongoing_inline_ai_generations.items() if data["user_id"] == user_id and time.time() - data["start_time"] < 45), None)
    if active_task_id:
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="⏳ Processing previous AI query...",
            input_message_content=types.InputTextMessageContent(message_text=f"Still processing AI query for: {ongoing_inline_ai_generations[active_task_id]['prompt']}")
        )], cache_time=1)
        return

    task_id = _create_ai_task_id(user_id, prompt)
    ongoing_inline_ai_generations[task_id] = {"user_id": user_id, "prompt": prompt, "start_time": time.time()}

    try:
        # Send a placeholder "Generating..." result first.
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=task_id, # Use a unique ID for this specific generation attempt
            title="🤖 Generating AI response...",
            description=f"Query: {prompt[:50]}...",
            input_message_content=types.InputTextMessageContent(
                message_text=f"🤖 Generating AI Response for:\n`{prompt}`\n\nPlease wait...", parse_mode="Markdown"
            ),
            thumb_url="https://img.icons8.com/color/452/artificial-intelligence.png"
        )], cache_time=5) # Short cache for placeholder
    except TelegramAPIError as e:
        logger.error(f"Error sending initial 'Generating AI...' inline answer: {e}")
        if task_id in ongoing_inline_ai_generations: del ongoing_inline_ai_generations[task_id]
        return

    ai_response_content = await _generate_ai_response_for_inline(prompt)
    add_ai_response_text_to_cache(user_id, prompt, ai_response_content)
    
    # After generation, the user would have clicked the placeholder.
    # The actual result is now in cache and will be served if they re-query or slightly change the query.
    # A more advanced implementation would use `chosen_inline_result` and `edit_message_text`
    # on the message sent when the user clicks the inline result.
    # For this migration, we are not implementing chosen_inline_result handling here.
    logger.info(f"Inline AI response generated and cached for user {user_id}, prompt: '{prompt}'")
    if task_id in ongoing_inline_ai_generations: del ongoing_inline_ai_generations[task_id]


# --- Cleanup Scheduler ---
def get_inline_ai_cleanup_scheduler_task_coro():
    async def run_scheduled_inline_ai_cleanup():
        logger.info("Started inline AI response cleanup scheduler")
        while True:
            await asyncio.sleep(60) 
            current_time = time.time()
            
            ongoing_to_remove = [tid for tid, data in ongoing_inline_ai_generations.items() if current_time - data["start_time"] > 120] # 2 mins
            for tid in ongoing_to_remove: del ongoing_inline_ai_generations[tid]
            if ongoing_to_remove: logger.info(f"Cleaned {len(ongoing_to_remove)} stale inline AI gen tasks.")

            temp_cache_to_remove = [uid for uid, data in temp_ai_query_cache.items() if current_time - data["timestamp"] > 300] # 5 mins
            for uid in temp_cache_to_remove: del temp_ai_query_cache[uid]
            if temp_cache_to_remove: logger.info(f"Cleaned temp AI query cache for {len(temp_cache_to_remove)} users.")
            
            cache_cleanup_count = 0
            for uid in list(ai_response_cache.keys()):
                indices_to_remove = [i for i, ts in enumerate(ai_response_cache[uid]["timestamps"]) if current_time - ts > 86400] # 24 hours
                for i in sorted(indices_to_remove, reverse=True):
                    for key_list in ["prompts", "responses", "timestamps"]: ai_response_cache[uid][key_list].pop(i)
                    cache_cleanup_count +=1
                if not ai_response_cache[uid]["prompts"]: del ai_response_cache[uid]
            if cache_cleanup_count > 0: logger.info(f"Cleaned {cache_cleanup_count} old inline AI response cache entries.")
    return run_scheduled_inline_ai_cleanup
