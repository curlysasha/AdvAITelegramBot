import os
from pymongo import MongoClient
from config import DATABASE_URL
import asyncio
from typing import List, Optional, Any, Dict # Added Dict

# client and db are synchronous PyMongo instances
client = MongoClient(DATABASE_URL)
db = client['aibotdb'] # Or your specific DB name
users_collection = db['users']
user_lang_collection = db['user_lang']
block_users_collection = db['blocked_users']
ai_mode_collection = db['ai_mode'] # Added ai_mode_collection


# === Async Wrapped Functions ===

async def check_and_add_username_async(user_id: int, username: str) -> None:
    """Async: Check if a username exists, and add/update it."""
    def _db_call():
        user = users_collection.find_one({"user_id": user_id})
        if user and user.get("username") == username:
            return
        # Use upsert=True to add if not exists, or update if exists
        users_collection.update_one({"user_id": user_id}, {"$set": {"username": username}}, upsert=True)
        print(f"Username {username} was added/updated for user ID {user_id}.")
    await asyncio.to_thread(_db_call)

async def check_and_add_user_async(user_id: int) -> None:
    """Async: Check if a user ID exists, and add it if it doesn't."""
    def _db_call():
        # Find if user exists, if not, insert. This is inherently an upsert operation.
        # A common pattern is to use update_one with upsert=True if you also want to set initial fields.
        # For just adding if not exists, find_one + insert_one is okay.
        if not users_collection.find_one({"user_id": user_id}):
            users_collection.insert_one({"user_id": user_id, "username": None}) # Initialize username field
            print(f"User ID {user_id} was added to the users collection.")
    await asyncio.to_thread(_db_call)

async def drop_user_id_async(user_id: int) -> None:
    """Async: Remove a specific user ID from the users collection."""
    def _db_call():
        result = users_collection.delete_one({"user_id": user_id})
        if result.deleted_count == 1:
            print(f"User ID {user_id} was successfully deleted.")
    await asyncio.to_thread(_db_call)

async def get_user_ids_async() -> List[Any]:
    """Async: Retrieve all distinct user IDs from the users collection."""
    def _db_call() -> List[Any]:
        user_ids_list = users_collection.distinct("user_id")
        print(f"Retrieved {len(user_ids_list)} user IDs.")
        return user_ids_list
    return await asyncio.to_thread(_db_call)

async def get_user_language_async(user_id: int) -> str:
    """Async: Get user's preferred language from database, default to 'en'."""
    def _db_call() -> str:
        user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
        if user_lang_doc and 'language' in user_lang_doc:
            return user_lang_doc['language']
        return 'en' 
    return await asyncio.to_thread(_db_call)

async def set_user_language_async(user_id: int, lang_code: str) -> None:
    """Async: Set user's preferred language."""
    def _db_call():
        user_lang_collection.update_one(
            {"user_id": user_id},
            {"$set": {"language": lang_code}},
            upsert=True
        )
        print(f"Language for user {user_id} set to {lang_code}.")
    await asyncio.to_thread(_db_call)

async def get_ai_mode_async(user_id: int) -> str:
    """Async: Get user's AI mode from database, default to 'chatbot'."""
    def _db_call() -> str:
        mode_doc = ai_mode_collection.find_one({"user_id": user_id})
        if mode_doc and 'mode' in mode_doc:
            return mode_doc['mode']
        # If no mode is set, default to "chatbot" and optionally store it
        # For now, just returning default without storing, user_db.py functions generally don't auto-create settings
        # This can be handled by the calling function if needed (e.g. in settings_menu_callback)
        return 'chatbot' 
    return await asyncio.to_thread(_db_call)

async def set_ai_mode_async(user_id: int, mode_code: str) -> None:
    """Async: Set user's AI mode."""
    def _db_call():
        ai_mode_collection.update_one(
            {"user_id": user_id},
            {"$set": {"mode": mode_code}},
            upsert=True
        )
        print(f"AI mode for user {user_id} set to {mode_code}.")
    await asyncio.to_thread(_db_call)

async def check_and_add_blocked_user_async(user_id: int) -> None:
    """Async: Check if a user ID exists in blocked_users, and add it if it doesn't."""
    def _db_call():
        if not block_users_collection.find_one({"user_id": user_id}):
            block_users_collection.insert_one({"user_id": user_id}) 
            print(f"User ID {user_id} was added to the blocked users collection.")
    await asyncio.to_thread(_db_call)


# --- Broadcast Functions ---
async def broadcast_message_to_users(bot, text_to_send: str) -> Tuple[int, int]: # Returns (sent_count, total_users)
    """Async: Send a message to all users. Wraps the DB call."""
    
    def _get_ids() -> List[Any]:
        return users_collection.distinct("user_id") # Get all unique user_ids
        
    user_ids = await asyncio.to_thread(_get_ids)
    
    total_users = len(user_ids)
    successfully_sent_count = 0
    
    for user_id_obj in user_ids:
        try:
            # Ensure user_id is an int, as distinct might return different types if schema is mixed
            current_user_id = int(user_id_obj) 
            await bot.send_message(current_user_id, text_to_send)
            successfully_sent_count += 1
            await asyncio.sleep(0.05) # Standard rate limit delay
        except ValueError:
            print(f"Skipping broadcast to invalid user ID: {user_id_obj}")
        except Exception as e:
            print(f"Error sending broadcast message to user ID {user_id_obj}: {e}")
            # Consider logging specific error types (e.g., BotBlocked, UserDeactivated)
            
    print(f"Broadcast attempt finished. Messages sent to {successfully_sent_count}/{total_users} users.")
    return successfully_sent_count, total_users

async def broadcast_message_to_users_with_username(bot, text_to_send: str) -> Tuple[int, int]:
    """Async: Send a message to all users with usernames. Wraps the DB call."""

    def _get_users_with_usernames() -> List[Dict[str, Any]]:
        # Ensure username exists and is not null or empty string
        return list(users_collection.find({"username": {"$exists": True, "$ne": None, "$ne": ""}}))

    users_with_usernames = await asyncio.to_thread(_get_users_with_usernames)
    
    total_users_with_usernames = len(users_with_usernames)
    successfully_sent_count = 0
    
    for user_doc in users_with_usernames:
        try:
            # Prefer sending by user_id if available and valid, it's more reliable
            user_id_to_send = int(user_doc["user_id"])
            await bot.send_message(user_id_to_send, text_to_send)
            successfully_sent_count += 1
            await asyncio.sleep(0.05)
        except ValueError:
             print(f"Skipping broadcast to user with invalid ID in doc: {user_doc}")
        except Exception as e:
            print(f"Error sending broadcast message to user ID {user_doc.get('user_id', 'N/A')} (@{user_doc.get('username')}): {e}")
            
    print(f"Username broadcast attempt finished. Messages sent to {successfully_sent_count}/{total_users_with_usernames} users.")
    return successfully_sent_count, total_users_with_usernames

# Note: The original synchronous functions have been removed to ensure only async versions are used.
# If any internal tools relied on synchronous versions, they would need separate adaptation or direct PyMongo usage.
