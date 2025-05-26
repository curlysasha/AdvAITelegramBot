import os
import asyncio
import logging
import time
import uuid
import hashlib
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
import requests

from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError

from ImgGenModel.g4f.client import Client as ImageClient
from ImgGenModel.g4f.Provider import PollinationsAI # Using a specific provider
from config import LOG_CHANNEL

logger = logging.getLogger(__name__)

# --- Data Structures ---
ongoing_generations: Dict[str, Dict[str, Any]] = {} # task_id -> {user_id, prompt, start_time}
image_cache: Dict[int, Dict[str, List[Any]]] = {} # user_id -> {"file_ids": [], "prompts": [], "timestamps": []}
MAX_CACHE_PER_USER = 5
temp_query_cache: Dict[int, Dict[str, Any]] = {} # user_id -> {query, file_id, prompt, timestamp}

# --- Core Inline Image Generation ---
async def generate_inline_image_api_g4f(prompt: str) -> List[str]:
    logger.info(f"G4F: Generating inline image with prompt: '{prompt}'")
    enhanced_prompt = f"{prompt}, ultra realistic, detailed, photographic quality"
    
    image_paths: List[str] = [] # Store local paths or URLs
    
    img_client = ImageClient() # Default client, may need specific provider initialization
    
    # Define the synchronous part of the g4f call
    def _g4f_sync_call_inline():
        # If g4f's async_generate is a true coroutine function, it should not be called directly here.
        # Instead, its synchronous equivalent (if available) or the execution of the coroutine
        # in a separate loop (as shown below) would be wrapped.
        async def _actual_g4f_coroutine_inline(): # Renamed to avoid conflict
            return await img_client.images.async_generate(
                model="dall-e-3", 
                prompt=enhanced_prompt,
                n=1,
                provider=PollinationsAI, 
                width=512, 
                height=512,
                quality="standard"
            )
        # Run the coroutine in a new event loop within the thread
        return asyncio.run(_actual_g4f_coroutine_inline())

    try:
        # Wrap the synchronous execution of the g4f operation
        response = await asyncio.wait_for(
            asyncio.to_thread(_g4f_sync_call_inline), 
            timeout=50 # Slightly longer timeout for thread overhead + generation
        )
        
        if not os.path.exists("./generated_images_inline"):
            os.makedirs("./generated_images_inline")

        for i, image_data in enumerate(response.data):
            # g4f returns image data typically as bytes or a URL
            # Assuming image_data.url holds the URL or path marker
            url_or_marker = image_data.url 
            
            if isinstance(image_data.bytes, bytes): # If raw bytes are available
                filename = f"inline_{uuid.uuid4()}.png" # Assume png if bytes
                local_path = os.path.join("./generated_images_inline", filename)
                with open(local_path, "wb") as f:
                    f.write(image_data.bytes)
                image_paths.append(local_path)
                logger.info(f"Saved image from bytes to {local_path}")
            elif isinstance(url_or_marker, str):
                if url_or_marker.startswith("http"): # It's a URL, download it
                    try:
                        img_response = requests.get(url_or_marker, timeout=20)
                        img_response.raise_for_status()
                        filename = f"inline_{uuid.uuid4()}.jpg" # Assume jpg for URLs
                        local_path = os.path.join("./generated_images_inline", filename)
                        with open(local_path, "wb") as f:
                            f.write(img_response.content)
                        image_paths.append(local_path)
                        logger.info(f"Downloaded image from {url_or_marker} to {local_path}")
                    except Exception as e:
                        logger.error(f"Failed to download image from URL {url_or_marker}: {e}")
                elif url_or_marker.startswith("/images/"): # Pollinations local path marker
                    # This assumes Pollinations saves files to a predictable local path structure
                    # that might be accessible relative to where g4f is run.
                    # The original code had: resolved_path = f"./generated_images{url_or_marker}"
                    # This needs to align with how g4f + PollinationsAI provider actually saves files.
                    # If it's always a web URL, then the http path above handles it.
                    # If it's truly a local path that g4f makes available, this could work.
                    # This is a common point of failure if the path resolution is incorrect.
                    # For now, let's assume it's a URL or raw bytes.
                    logger.warning(f"Received a local path marker {url_or_marker} from PollinationsAI, but direct local file access from g4f provider output is unreliable. Prefer URLs or raw bytes.")
                    # If you are certain g4f saves these locally and makes them accessible:
                    # potential_local_path = os.path.join("./generated_images", os.path.basename(url_or_marker))
                    # if os.path.exists(potential_local_path):
                    #    image_paths.append(potential_local_path)
                    # else:
                    #    logger.error(f"Marked local path {potential_local_path} not found.")

            if len(image_paths) >= 1: # Max 1 image for inline
                break
        
        if not image_paths:
            logger.warning(f"No images processed for inline prompt: {prompt}")
            return []
        return image_paths

    except asyncio.TimeoutError:
        logger.warning(f"Inline image generation API timed out for prompt: {prompt}")
        return []
    except Exception as e:
        logger.error(f"Error in inline image generation API for prompt '{prompt}': {e}")
        return []

# --- Helper Functions ---
def _create_task_id(user_id: int, prompt: str) -> str:
    return hashlib.md5(f"{user_id}:{prompt}:{time.time()}".encode()).hexdigest()[:10]

def _get_image_caption(prompt: str, bot_username: str) -> str:
    return f"🖼️ **AI Image**\n📝 **Prompt**: `{prompt}`\n\n@{bot_username}"

# --- Cache Functions ---
def _get_cached_file_id(user_id: int, prompt: str) -> Optional[str]:
    if user_id in image_cache and image_cache[user_id]["file_ids"]:
        try:
            idx = image_cache[user_id]["prompts"].index(prompt)
            return image_cache[user_id]["file_ids"][idx]
        except ValueError:
            pass
    if user_id in temp_query_cache and temp_query_cache[user_id]["prompt"] == prompt:
        return temp_query_cache[user_id]["file_id"]
    return None

def _add_to_cache(user_id: int, file_id: str, prompt: str):
    if user_id not in image_cache:
        image_cache[user_id] = {"file_ids": [], "prompts": [], "timestamps": []}
    if prompt in image_cache[user_id]["prompts"]: # Update existing
        idx = image_cache[user_id]["prompts"].index(prompt)
        image_cache[user_id]["file_ids"][idx] = file_id
        image_cache[user_id]["timestamps"][idx] = time.time()
    else: # Add new
        image_cache[user_id]["file_ids"].insert(0, file_id)
        image_cache[user_id]["prompts"].insert(0, prompt)
        image_cache[user_id]["timestamps"].insert(0, time.time())
        if len(image_cache[user_id]["file_ids"]) > MAX_CACHE_PER_USER:
            for key_list in ["file_ids", "prompts", "timestamps"]: image_cache[user_id][key_list].pop()
    temp_query_cache[user_id] = {"query": prompt, "file_id": file_id, "prompt": prompt, "timestamp": time.time()}

def _clear_user_inline_cache(user_id: int):
    if user_id in image_cache: del image_cache[user_id]
    if user_id in temp_query_cache: del temp_query_cache[user_id]

# --- Main Inline Query Handler ---
async def handle_inline_image_query(inline_query: types.InlineQuery, bot: Bot):
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    prompt = query[6:-1].strip() # Assumes "image " prefix and "." suffix are already handled by main router
    
    if not prompt or len(prompt) < 3:
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="Prompt too short",
            input_message_content=types.InputTextMessageContent(message_text="Prompt too short for image generation.")
        )], cache_time=1)
        return

    if prompt.lower() == "clear cache":
        _clear_user_inline_cache(user_id)
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="Cache Cleared",
            input_message_content=types.InputTextMessageContent(message_text="✅ Inline image cache cleared.")
        )], cache_time=1)
        return

    cached_file_id = _get_cached_file_id(user_id, prompt)
    if cached_file_id:
        try:
            await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultCachedPhoto(
                id=str(uuid.uuid4()), photo_file_id=cached_file_id,
                caption=_get_image_caption(prompt, bot_username), parse_mode="Markdown"
            )], cache_time=3600)
            return
        except TelegramAPIError as e: logger.error(f"Error with cached inline: {e}")

    active_task = next((data for data in ongoing_generations.values() if data["user_id"] == user_id and time.time() - data["start_time"] < 45), None)
    if active_task:
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="Processing previous request...",
            input_message_content=types.InputTextMessageContent(message_text=f"Still generating for: {active_task['prompt']}")
        )], cache_time=1)
        return

    task_id = _create_task_id(user_id, prompt)
    ongoing_generations[task_id] = {"user_id": user_id, "prompt": prompt, "start_time": time.time()}
    
    # Send initial "Generating..." result
    # This is important so the user doesn't see "No results" if generation takes time
    try:
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=task_id, # Use task_id as result id
            title="🎨 Generating your image...",
            description=f"Prompt: {prompt}",
            input_message_content=types.InputTextMessageContent(message_text=f"🖼️ Generating: `{prompt}`", parse_mode="Markdown"),
            thumb_url="https://img.icons8.com/color/452/hourglass.png" # Placeholder
        )], cache_time=5) # Short cache time for this placeholder
    except TelegramAPIError as e:
        logger.error(f"Error sending initial 'Generating...' inline answer: {e}")
        # If this fails, the rest might not matter for this specific query
        if task_id in ongoing_generations: del ongoing_generations[task_id]
        return


    local_image_paths = await generate_inline_image_api_g4f(prompt)
    
    final_results = []
    if local_image_paths:
        for path in local_image_paths:
            try:
                log_caption = f"Inline gen for {user_id}: {prompt}"
                # Upload to a channel (or self) to get a persistent file_id
                # Ensure LOG_CHANNEL is an int
                sent_photo_msg = await bot.send_photo(chat_id=int(LOG_CHANNEL), photo=types.FSInputFile(path), caption=log_caption)
                if sent_photo_msg.photo:
                    file_id = sent_photo_msg.photo[-1].file_id
                    _add_to_cache(user_id, file_id, prompt)
                    final_results.append(types.InlineQueryResultCachedPhoto(
                        id=str(uuid.uuid4()), photo_file_id=file_id,
                        caption=_get_image_caption(prompt, bot_username), parse_mode="Markdown"
                    ))
                os.remove(path)
            except Exception as e:
                logger.error(f"Error processing/uploading generated file {path}: {e}")
                if os.path.exists(path): os.remove(path) # Attempt cleanup

    # After generation, we can't use inline_query.answer again for the *same query_id*
    # if the first answer was an article.
    # The proper way to update is via `edit_message_media` on a `chosen_inline_result`,
    # or by sending the image directly to the user in the chat if they selected the placeholder.
    # For this migration, if results are found, we'll log them. The user would have chosen the "Generating..." result.
    # A more advanced setup would involve chosen_inline_result and editing.
    # For now, the user would have to re-type the query if the initial "Generating..." placeholder was too slow to be replaced.
    # If final_results is populated, it means we successfully got file_ids.
    # The user has already received the "Generating..." placeholder.
    # The cached file_id will be used if they re-issue the query or type more.

    if not final_results: # If, after everything, no results
         logger.warning(f"Fully failed to provide inline image for {prompt}, user {user_id}")
         # At this point, the user has the "Generating..." placeholder. Nothing more to do for *this* query.

    if task_id in ongoing_generations: del ongoing_generations[task_id]


# --- Main Inline Query Router Function ---
# This function is intended to be imported and registered with the dispatcher in run.py
async def route_inline_query(inline_query: types.InlineQuery, bot: Bot):
    """Routes inline queries to image generation or AI response handlers."""
    query = inline_query.query.strip()
    
    # Import here to avoid circular dependency with inline_ai_response
    from modules.models.inline_ai_response import handle_inline_ai_query as process_ai_inline_query

    if not query:
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="Type a prompt...",
            description="Image: 'image prompt.' | AI: 'question?' or 'prompt.'",
            input_message_content=types.InputTextMessageContent(
                message_text="**📝 How to use inline:**\n\n• **Images**: `image your prompt.`\n• **AI**: `your question?` or `your prompt.`",
                parse_mode="Markdown"
            )
        )], cache_time=1)
        return

    is_image_req = query.lower().startswith("image ") and query.endswith(".")
    is_ai_req = not is_image_req and (query.endswith(".") or query.endswith("?"))

    if is_image_req:
        await handle_inline_image_query(inline_query, bot)
    elif is_ai_req:
        prompt = query[:-1].strip()
        await process_ai_inline_query(bot, inline_query, prompt) # Pass bot instance
    else: # Incomplete query
        desc_text = "End with . for image" if query.lower().startswith("image ") else "End with . or ? for AI"
        await bot.answer_inline_query(inline_query.id, results=[types.InlineQueryResultArticle(
            id=str(uuid.uuid4()), title="Continue typing...", description=desc_text,
            input_message_content=types.InputTextMessageContent(message_text=f"Current prompt: {query}")
        )], cache_time=1)


# --- Cleanup Scheduler ---
def get_inline_cleanup_scheduler_task_coro():
    async def run_scheduled_inline_cleanup():
        logger.info("Started inline image generation cleanup scheduler")
        while True:
            await asyncio.sleep(60) 
            current_time = time.time()
            ongoing_to_remove = [tid for tid, data in ongoing_generations.items() if current_time - data["start_time"] > 120]
            for tid in ongoing_to_remove: del ongoing_generations[tid]
            if ongoing_to_remove: logger.info(f"Cleaned {len(ongoing_to_remove)} stale inline gen tasks.")

            temp_cache_to_remove = [uid for uid, data in temp_query_cache.items() if current_time - data["timestamp"] > 300]
            for uid in temp_cache_to_remove: del temp_query_cache[uid]
            if temp_cache_to_remove: logger.info(f"Cleaned temp query cache for {len(temp_cache_to_remove)} users.")

            cache_cleanup_count = 0
            for uid in list(image_cache.keys()):
                indices_to_remove = [i for i, ts in enumerate(image_cache[uid]["timestamps"]) if current_time - ts > 86400]
                for i in sorted(indices_to_remove, reverse=True):
                    for key_list in ["file_ids", "prompts", "timestamps"]: image_cache[uid][key_list].pop(i)
                    cache_cleanup_count +=1
                if not image_cache[uid]["file_ids"]: del image_cache[uid]
            if cache_cleanup_count > 0: logger.info(f"Cleaned {cache_cleanup_count} old inline image cache entries.")
            
            try: # Cleanup local files
                inline_dir = "./generated_images_inline"
                if os.path.exists(inline_dir):
                    cutoff = current_time - 3600 
                    for fname in os.listdir(inline_dir):
                        fpath = os.path.join(inline_dir, fname)
                        if os.path.getmtime(fpath) < cutoff:
                            try: os.remove(fpath); logger.info(f"Cleaned stray inline file: {fpath}")
                            except Exception as e_rem: logger.error(f"Error removing stray inline file {fpath}: {e_rem}")
            except Exception as e_list: logger.error(f"Error listing stray inline files: {e_list}")
    return run_scheduled_inline_cleanup
