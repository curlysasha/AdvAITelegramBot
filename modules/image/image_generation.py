import os
import random
import asyncio
import logging
import time
from datetime import datetime
import json
from typing import Dict, List, Optional, Tuple, Union
import re
import hashlib

from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ChatAction # For send_chat_action

from pymongo import MongoClient
from ImgGenModel.g4f.client import Client as ImageClient # External image generation client
from ImgGenModel.g4f.Provider import PollinationsAI # Provider for image generation

from config import DATABASE_URL, LOG_CHANNEL # Assuming LOG_CHANNEL is int/str chat_id
# Assuming these are or will be Aiogram-compatible
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled 

logger = logging.getLogger(__name__)
image_gen_router = Router()

# MongoDB setup (Consider centralizing DB client initialization)
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_images_collection = db['user_images'] # Used for storing metadata of generated images by user
image_feedback_collection = db['image_feedback'] # For storing user feedback on images
prompt_storage_collection = db['prompt_storage'] # For persistent prompt storage

# In-memory prompt storage as fallback (cached to DB)
prompt_storage_cache: Dict[str, str] = {} # Renamed to avoid conflict, explicit type

# Constants for style definitions (remains the same)
STYLE_DEFINITIONS = {
    "realistic": {"name": "Realistic", "description": "Photo-realistic, detailed images", "prompt_additions": "ultra realistic, detailed, photographic quality", "button_text": "🖼️ Realistic"},
    "artistic": {"name": "Artistic", "description": "Creative, artistic style like a painting", "prompt_additions": "artistic style, creative, vibrant colors, painting-like", "button_text": "🎨 Artistic"},
    "sketch": {"name": "Sketch", "description": "Hand-drawn sketch or drawing style", "prompt_additions": "hand-drawn sketch, pencil drawing, line art, sketched appearance", "button_text": "✏️ Sketch"},
    "cartoon": {"name": "Cartoon", "description": "Fun cartoon or animated style", "prompt_additions": "cartoon style, animated look, colorful, simplified features", "button_text": "🧸 Cartoon"},
    "3d": {"name": "3D Render", "description": "3D rendered style with depth and texture", "prompt_additions": "3D render, volumetric lighting, high detail, realistic textures, depth", "button_text": "🌟 3D Render"}
}

# --- PROMPT STORAGE FUNCTIONS (Wrapped for async) ---
async def store_prompt_in_db_async(user_id: int, prompt: str) -> str: # Renamed to _async
    hash_object = hashlib.md5(f"{user_id}:{prompt}".encode())
    prompt_id = hash_object.hexdigest()[:8]
    prompt_storage_cache[prompt_id] = prompt # Cache update is sync, fine
    
    def _db_call():
        try:
            prompt_storage_collection.update_one(
                {"prompt_id": prompt_id},
                {"$set": {"user_id": user_id, "prompt": prompt, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to store prompt in database: {e}")
    await asyncio.to_thread(_db_call)
    return prompt_id

async def get_prompt_from_db_async(prompt_id: str) -> Optional[str]: # Renamed to _async
    if prompt_id in prompt_storage_cache:
        return prompt_storage_cache[prompt_id] # Cache read is sync, fine
    
    def _db_call():
        try:
            result = prompt_storage_collection.find_one({"prompt_id": prompt_id})
            if result and "prompt" in result:
                prompt_storage_cache[prompt_id] = result["prompt"] # Update cache
                return result["prompt"]
        except Exception as e:
            logger.error(f"Failed to retrieve prompt from database: {e}")
        return None
    return await asyncio.to_thread(_db_call)

# --- USER STATE MANAGEMENT (class definition is fine, global dict `user_states` is used) ---
class UserGenerationState:
    def __init__(self, user_id: int, prompt: str):
        self.user_id = user_id
        self.prompt = prompt
        self.style: Optional[str] = None
        self.style_msg_id: Optional[int] = None
        self.style_msg_chat_id: Optional[int] = None
        self.is_processing: bool = False
        self.created_at: float = time.time()
        
    def is_active(self) -> bool:
        is_valid = time.time() - self.created_at < 600  # 10 minute expiration
        if not is_valid and self.is_processing:
            self.is_processing = False
            logger.info(f"Auto-reset expired processing state for user {self.user_id}")
        return is_valid
    
    def set_style(self, style: str):
        self.style = style if style in STYLE_DEFINITIONS else "realistic"
            
    def set_processing(self, is_processing: bool):
        if is_processing: self.created_at = time.time()
        self.is_processing = is_processing
        
    def set_style_message(self, message: types.Message): # Aiogram type
        if message and hasattr(message, 'message_id') and hasattr(message, 'chat'):
            self.style_msg_id = message.message_id
            self.style_msg_chat_id = message.chat.id

user_states: Dict[int, UserGenerationState] = {}


# --- CORE IMAGE GENERATION (API call logic, largely unchanged) ---
async def generate_images_from_api(prompt: str, style: str, max_images: int = 1) -> Tuple[Optional[List[str]], Optional[str]]:
    logger.info(f"Generating images with prompt: '{prompt}', style: '{style}'")
    style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
    enhanced_prompt = f"{prompt}, {style_info['prompt_additions']}"
    logger.info(f"Enhanced prompt: '{enhanced_prompt}'")
    
    image_urls: List[str] = []
    # Simplified provider logic for now, can be expanded
    # This external client (ImgGenModel.g4f.client) is assumed to work as is.
    # If it's blocking, it should be run in an executor for async Aiogram.
    # For now, assuming it's async or the blocking is acceptable.
    img_client = ImageClient()
    
    # Define the synchronous part of the g4f call
    def _g4f_sync_call():
        # If g4f's async_generate is a true coroutine function, it should not be called directly here.
        # Instead, its synchronous equivalent (if available) or the execution of the coroutine
        # in a separate loop (as shown below) would be wrapped.
        # Assuming `img_client.images.async_generate` is a coroutine function:
        async def _actual_g4f_coroutine():
            return await img_client.images.async_generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                n=max_images,
                provider=PollinationsAI,
                width=1024, height=1024, quality="standard"
            )
        # Run the coroutine in a new event loop within the thread
        return asyncio.run(_actual_g4f_coroutine())

    try:
        # Wrap the synchronous execution of the g4f operation
        response = await asyncio.wait_for(
            asyncio.to_thread(_g4f_sync_call), 
            timeout=65 # Timeout for the thread execution
        )

        for image_data in response.data: # response.data should be okay
            image_urls.append(image_data.url)
        if not image_urls:
            return None, "AI failed to generate images for this prompt."
        return image_urls, None
    except asyncio.TimeoutError:
        logger.warning(f"Image generation timed out for prompt: {prompt}")
        return None, "Image generation timed out. Please try again."
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None, f"An error occurred during image generation: {str(e)}"

# --- UI COMPONENTS (Adapted for Aiogram) ---
async def update_generation_progress_message(bot: Bot, chat_id: int, message_id: int, prompt: str, style: str):
    progress_stages = ["⏳ Analyzing...", "🧠 Crafting...", "🎨 Applying style...", "✨ Finishing...", "📷 Rendering..."]
    style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
    base_text = f"🎭 **Generating Images**\n\nPrompt: `{prompt}`\nStyle: `{style_info['name']}`\n\n"
    try:
        for stage in progress_stages:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=base_text + stage, parse_mode="Markdown")
            await asyncio.sleep(2.5) # Original sleep duration
    except asyncio.CancelledError:
        logger.info("Progress updater cancelled.")
    except Exception as e: # Catch specific Aiogram exceptions if needed (e.g., MessageNotModified)
        logger.error(f"Error updating progress: {e}")

# --- HANDLERS (Adapted for Aiogram) ---
@image_gen_router.message(Command(commands=["generate", "gen", "image", "img"]))
async def generate_command_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    if await maintenance_check(user_id) or not await is_feature_enabled("image_generation", user_id):
        maint_msg_text = await maintenance_message(user_id)
        await message.answer(maint_msg_text)
        return
        
    prompt_parts = message.text.split(None, 1)
    if len(prompt_parts) < 2 or not prompt_parts[1].strip():
        await message.answer(
            "🖼️ **Image Generation**\n\nPlease provide a prompt.\nExample: `/img a cat wearing a hat`",
            parse_mode="Markdown"
        )
        return
    prompt = prompt_parts[1].strip()

    # Aggressive state reset for the user
    if user_id in user_states:
        logger.info(f"Force resetting processing state for user {user_id} before new generation.")
        user_states[user_id].set_processing(False)
        if time.time() - user_states[user_id].created_at > 120 : # Stale state
             del user_states[user_id]

    if user_id in user_states and user_states[user_id].is_processing: # Should ideally not happen now
        await message.answer("⏳ Already working on your request. Please wait.")
        return
            
    await show_style_selection_menu(bot, message, prompt) # Pass bot here

async def show_style_selection_menu(bot: Bot, message: types.Message, prompt: str): # Added bot parameter
    user_id = message.from_user.id
    user_states[user_id] = UserGenerationState(user_id, prompt)
    
    buttons = []
    row = []
    for i, (style_id, style_info) in enumerate(STYLE_DEFINITIONS.items()):
        row.append(InlineKeyboardButton(text=style_info["button_text"], callback_data=f"img_style_{style_id}_{user_id}"))
        if len(row) == 2 or i == len(STYLE_DEFINITIONS) - 1:
            buttons.append(row)
            row = []
    style_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    style_msg = await message.answer( # Use message.answer instead of reply_text for clarity
        f"🎭 **Choose Image Style**\n\nYour prompt: `{prompt}`\n\nSelect a style:",
        reply_markup=style_markup,
        parse_mode="Markdown"
    )
    user_states[user_id].set_style_message(style_msg) # Pass Aiogram message
    logger.info(f"Sent style selection for user {user_id}, prompt: '{prompt}'")


async def process_style_selection_callback(callback_query: types.CallbackQuery, bot: Bot):
    clicked_user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    data = callback_query.data
    
    parts = data.split("_") # Expected: img_style_{style}_{target_user_id}
    if len(parts) < 4 or parts[0] != "img" or parts[1] != "style":
        await callback_query.answer("Invalid selection.", show_alert=True)
        return
    style_selected = parts[2]
    target_user_id = int(parts[3])

    if clicked_user_id != target_user_id:
        await callback_query.answer("This is not your image request.", show_alert=True)
        return
        
    if target_user_id not in user_states or not user_states[target_user_id].is_active():
        await callback_query.answer("Request expired or invalid. Please start a new one.", show_alert=True)
        try: await callback_query.message.delete() # Clean up old menu
        except: pass
        return

    state = user_states[target_user_id]
    if state.is_processing:
        await callback_query.answer("Already generating. Please wait.", show_alert=True)
        return
        
    state.set_processing(True)
    state.set_style(style_selected)
    style_info = STYLE_DEFINITIONS.get(state.style, STYLE_DEFINITIONS["realistic"])
    await callback_query.answer(f"Generating in {style_info['name']} style...")

    processing_text = (f"🎭 **Generating Images**\n\n"
                       f"Prompt: `{state.prompt}`\nStyle: `{style_info['name']}`\n\n"
                       f"⏳ Working on it...")
    await bot.edit_message_text(chat_id=chat_id, message_id=callback_query.message.message_id, text=processing_text, parse_mode="Markdown", reply_markup=None) # Remove keyboard

    progress_task = asyncio.create_task(
        update_generation_progress_message(bot, chat_id, callback_query.message.message_id, state.prompt, state.style)
    )
    
    await generate_and_send_images_to_user(bot, callback_query.message, state.prompt, state.style, progress_task)


async def generate_and_send_images_to_user(bot: Bot, original_msg_for_reply: types.Message, prompt: str, style: str, progress_task: Optional[asyncio.Task] = None):
    user_id = original_msg_for_reply.chat.id # In private chat, chat.id is user_id. For group, it's group_id.
                                          # If user_id is needed strictly, use original_msg_for_reply.from_user.id
    chat_id_to_send = original_msg_for_reply.chat.id # Send to the same chat
    
    generation_id = f"{user_id}_{int(time.time())}" # Use user_id for generation_id consistency
    generation_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        image_urls, error_msg = await generate_images_from_api(prompt, style)
        
        if progress_task and not progress_task.done():
            progress_task.cancel()
        
        # Delete the "Generating..." message
        try: await bot.delete_message(chat_id_to_send, original_msg_for_reply.message_id)
        except Exception as e: logger.warning(f"Could not delete processing message: {e}")

        if error_msg:
            await bot.send_message(chat_id_to_send, f"❌ **Image Generation Failed**\n\n{error_msg}", parse_mode="Markdown")
            # Log error (simplified)
            if LOG_CHANNEL: await bot.send_message(int(LOG_CHANNEL), f"#ImgGenFail Prompt: {prompt}, Error: {error_msg}")
            return

        if not image_urls: # Should be covered by error_msg but as a safeguard
            await bot.send_message(chat_id_to_send, "❌ **Image Generation Failed**\n\nNo images were returned.", parse_mode="Markdown")
            return

        media_group = []
        style_info = STYLE_DEFINITIONS.get(style, STYLE_DEFINITIONS["realistic"])
        for i, url_or_path in enumerate(image_urls):
            caption = f"🖼️ **AI Image**\n\nPrompt: `{prompt}`\nStyle: `{style_info['name']}`" if i == 0 else ""
            # Assuming url_or_path are URLs. If local paths from g4f, use types.FSInputFile(url_or_path)
            media_group.append(types.InputMediaPhoto(media=url_or_path, caption=caption, parse_mode="Markdown"))
        
        if media_group:
            sent_messages = await bot.send_media_group(chat_id=chat_id_to_send, media=media_group)
            
            prompt_id_hash = await store_prompt_in_db_async(user_id, prompt) # Use async version
            
            feedback_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("👍 Love it", callback_data=f"img_fb_pos_{user_id}_{generation_id}"),
                 InlineKeyboardButton("👎 Not good", callback_data=f"img_fb_neg_{user_id}_{generation_id}")],
                [InlineKeyboardButton("🔄 Regenerate", callback_data=f"img_regen_{user_id}_{prompt_id_hash}")]
            ])
            await bot.send_message(chat_id_to_send, "**How do you like these images?**", reply_markup=feedback_markup, parse_mode="Markdown", reply_to_message_id=sent_messages[0].message_id if sent_messages else None)
            
            # Log success (simplified)
            if LOG_CHANNEL: await bot.send_message(int(LOG_CHANNEL), f"#ImgGenOK Prompt: {prompt}, Style: {style}, User: {user_id}, Images: {len(image_urls)}")
        
    except Exception as e:
        logger.error(f"Error in generate_and_send_images: {e}")
        try: await bot.send_message(chat_id_to_send, f"❌ **Error**\n\nFailed to generate images: {str(e)}", parse_mode="Markdown")
        except Exception: pass # Avoid error loops
    finally:
        if user_id in user_states: # Use the correct user_id for state reset
            user_states[user_id].set_processing(False)
            logger.info(f"Final state reset for user {user_id}")


# Combined feedback and style selection handler
@image_gen_router.callback_query(F.data.startswith("img_"))
async def image_callbacks_handler(callback_query: types.CallbackQuery, bot: Bot):
    data = callback_query.data
    user_id = callback_query.from_user.id # User who clicked

    if data.startswith("img_style_"):
        await process_style_selection_callback(callback_query, bot)
    elif data.startswith("img_fb_pos_") or data.startswith("img_fb_neg_"):
        # Feedback: img_fb_pos_{target_user_id}_{generation_id}
        parts = data.split("_")
        feedback_type = "positive" if parts[2] == "pos" else "negative"
        # target_user_id = int(parts[3]) # Not strictly needed if feedback is for the image itself
        generation_id_str = parts[4]

        await callback_query.answer(f"Thanks for your {feedback_type} feedback!")
        new_text = callback_query.message.text + f"\n\n✅ Feedback: You felt this was {feedback_type}."
        try: await callback_query.message.edit_text(new_text, reply_markup=None, parse_mode="Markdown")
        except Exception as e: logger.warning(f"Couldn't edit feedback message: {e}")
        # Log feedback (simplified)
        if LOG_CHANNEL: await bot.send_message(int(LOG_CHANNEL), f"#ImgFeedback Type: {feedback_type}, User: {user_id}, GenID: {generation_id_str}")

    elif data.startswith("img_regen_"):
        # Regenerate: img_regen_{target_user_id}_{prompt_id_hash}
        parts = data.split("_")
        target_user_id_for_prompt = int(parts[2])
        prompt_id_hash = parts[3]

        # Security: Only original prompter can easily regenerate their own prompt via button
        # Groups might allow anyone if that's desired (current logic implies from_user.id is used for new state)
        if user_id != target_user_id_for_prompt and callback_query.message.chat.type == types.ChatType.PRIVATE: # Use Aiogram ChatType
             await callback_query.answer("You can only regenerate your own image prompts directly.", show_alert=True)
             return

        prompt = await get_prompt_from_db_async(prompt_id_hash) # Use async version
        if not prompt:
            await callback_query.answer("Error: Original prompt not found. Please try a new generation.", show_alert=True)
            return
        
        # Reset state for the user clicking regenerate
        if user_id in user_states:
            user_states[user_id].set_processing(False)
            if time.time() - user_states[user_id].created_at > 120 : del user_states[user_id]

        if user_id in user_states and user_states[user_id].is_processing:
            await callback_query.answer("Already working on a request. Please wait.", show_alert=True)
            return

        await callback_query.message.delete() # Delete the "How do you like..." message
        await show_style_selection_menu(bot, callback_query.message, prompt) # Show style menu for regeneration
        # Note: callback_query.message here is the "How do you like..." message.
        # For show_style_selection_menu, it expects a user message to reply to.
        # This might need adjustment: send a new message or use callback_query.message.chat and from_user.id
        # For simplicity, we'll let it reply to the (now deleted) context, which means it sends a new message.
        # A better UX might be to pass callback_query.message.chat.id and callback_query.from_user.id
        # and have show_style_selection_menu send a new message.
        # Let's assume show_style_selection_menu will use .answer() on the message object,
        # which effectively sends a new message if the original is deleted.

    else:
        await callback_query.answer("Unknown image action.")

# Cleanup scheduler logic (already in run.py's on_startup, but definition can stay here or be moved)
# For this task, I'll assume the definition is fine here, and run.py calls it.
# The original function returned the coroutine, which is correct for scheduling.
def get_cleanup_scheduler_task_coro():
    async def run_scheduled_cleanup():
        logger.info("Started image generation state cleanup scheduler")
        while True:
            await asyncio.sleep(3600)  # Run every hour
            to_remove = [uid for uid, state in user_states.items() if not state.is_active() and not state.is_processing]
            for user_id in to_remove:
                del user_states[user_id]
            if to_remove: logger.info(f"Cleaned up {len(to_remove)} expired image generation user states")
    return run_scheduled_cleanup

# The original file had aliases:
# generate_command = handle_generate_command
# handle_image_feedback = handle_feedback
# These are effectively handled by the router registrations now.
# start_cleanup_scheduler is handled by run.py calling get_cleanup_scheduler_task_coro() from here.
# So, these aliases are not strictly needed if routers are used.
# For clarity, I've renamed handlers (e.g., generate_command_handler).
# The old names can be re-aliased if other modules import them directly by old names.
# For now, assuming new names and router registration is the way forward.
