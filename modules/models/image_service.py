import os
import time
import asyncio
import uuid
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime

# Changed Pyrogram imports to Aiogram
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup 

from modules.core.database import get_user_images_collection, get_prompt_storage_collection

# Configure logging
logger = logging.getLogger(__name__)

class ImageService:
    """
    Service class for handling image generation and management
    with efficient database operations and caching
    """
    
    AVAILABLE_STYLES = {
        "photorealistic": "📸 Photorealistic", "anime": "🎭 Anime Style", "3d_render": "🧊 3D Render",
        "cartoon": "🎨 Cartoon", "pixel_art": "👾 Pixel Art", "oil_painting": "🖼️ Oil Painting",
        "watercolor": "💦 Watercolor", "sketch": "✏️ Sketch", "vector_art": "📊 Vector Art",
        "cyberpunk": "🤖 Cyberpunk", "fantasy": "🧙‍♂️ Fantasy", "steampunk": "⚙️ Steampunk",
        "neon": "✨ Neon"
    }
    
    @staticmethod
    def get_image_styles_keyboard() -> InlineKeyboardMarkup:
        """
        Get a keyboard markup with available image styles, adapted for Aiogram.
        """
        keyboard_rows = []
        current_row = []
        
        for i, (style_id, style_name) in enumerate(ImageService.AVAILABLE_STYLES.items()):
            current_row.append(InlineKeyboardButton(text=style_name, callback_data=f"img_style_{style_id}"))
            if len(current_row) == 2: # Two buttons per row
                keyboard_rows.append(current_row)
                current_row = []
        
        if current_row: # Add any remaining button in the last row
            keyboard_rows.append(current_row)
            
        keyboard_rows.append([InlineKeyboardButton(text="🔄 Regenerate", callback_data="img_regenerate_default")])
        keyboard_rows.append([InlineKeyboardButton(text="⭐ Rate this image", callback_data="img_feedback_default")])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    @staticmethod
    def generate_unique_filename(user_id: int, style: Optional[str] = None) -> str:
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        style_suffix = f"_{style}" if style else ""
        return f"{user_id}_{timestamp}{style_suffix}_{unique_id}.jpg"
    
    @staticmethod
    async def store_user_image(user_id: int, filename: str, prompt: str, 
                               style: Optional[str] = None) -> None:
        try:
            user_images_collection = get_user_images_collection()
            user_images_collection.update_one(
                {"user_id": user_id},
                {"$push": {
                    "images": {
                        "filename": filename, "prompt": prompt, "style": style,
                        "timestamp": datetime.now(), "file_id": None 
                    }
                }},
                upsert=True
            )
            logger.info(f"Stored image metadata for user {user_id}: {filename}")
        except Exception as e:
            logger.error(f"Error storing user image metadata: {str(e)}")
    
    @staticmethod
    async def update_image_file_id(user_id: int, filename: str, file_id: str) -> None:
        try:
            user_images_collection = get_user_images_collection()
            user_images_collection.update_one(
                {"user_id": user_id, "images.filename": filename},
                {"$set": {"images.$.file_id": file_id}}
            )
            logger.info(f"Updated file_id for image {filename} (user {user_id})")
        except Exception as e:
            logger.error(f"Error updating image file_id: {str(e)}")
    
    @staticmethod
    async def get_user_recent_images(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            user_images_collection = get_user_images_collection()
            user_cache = user_images_collection.find_one({"user_id": user_id})
            if not user_cache or "images" not in user_cache:
                return []
            recent_images = user_cache["images"][-limit:]
            recent_images.reverse()
            return recent_images
        except Exception as e:
            logger.error(f"Error retrieving user images: {str(e)}")
            return []
    
    @staticmethod
    async def clear_user_image_cache(user_id: int) -> bool:
        try:
            user_images_collection = get_user_images_collection()
            result = user_images_collection.delete_one({"user_id": user_id})
            if result.deleted_count > 0:
                logger.info(f"Cleared image cache for user {user_id}")
                return True
            logger.info(f"No image cache found for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error clearing user image cache: {str(e)}")
            return False
    
    @staticmethod
    async def store_prompt(user_id: int, prompt: str, context: Optional[str] = None) -> None:
        try:
            prompt_storage = get_prompt_storage_collection()
            prompt_storage.insert_one({
                "user_id": user_id, "prompt": prompt, "context": context,
                "timestamp": datetime.now()
            })
        except Exception as e:
            logger.error(f"Error storing prompt: {str(e)}")
    
    @staticmethod
    async def delete_local_image(filename: str) -> None:
        try:
            if os.path.exists(filename) and os.path.isfile(filename):
                os.remove(filename)
                logger.info(f"Deleted local image file: {filename}")
        except Exception as e:
            logger.error(f"Error deleting local image file {filename}: {str(e)}")
