from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from pymongo import MongoClient # Keep for direct calls if any remain, though ideally use user_db.py
from config import DATABASE_URL
# Assuming these lang functions are/will be Aiogram compatible
from modules.lang import async_translate_to_lang 
import database.user_db as user_db # Import user_db for its async functions
import asyncio # For asyncio.to_thread

# Router for assistant/mode settings
assistant_settings_router = Router()

# MongoDB Client - This direct usage should be minimized, prefer user_db.py
# client = MongoClient(DATABASE_URL) # Already in user_db.py or core.database.py
# db = client["aibotdb"]
# ai_mode_collection = db['ai_mode'] # Prefer get_ai_mode_collection from core.database or use user_db functions
# For this specific file, direct usage of ai_mode_collection was there.
# If we want to fully move to user_db.py functions, we'd remove direct ai_mode_collection usage.
# For now, let's assume we keep direct usage for this file and wrap it,
# OR switch to user_db.py functions if they cover all needs.
# The prompt asks to wrap calls in user_db.py OR other direct DB interaction points.
# Since user_db.py now has get_ai_mode_async and set_ai_mode_async, we should use those.
# So, direct ai_mode_collection usage will be replaced.

# Dictionary of modes with labels (ensure this is the single source of truth or imported)
modes = {
    "chatbot": "Chatbot", "coder": "Coder/Developer", "professional": "Professional",
    "teacher": "Teacher", "therapist": "Therapist", "assistant": "Personal Assistant",
    "gamer": "Gamer", "translator": "Translator"
}

# Display assistant mode selection menu
@assistant_settings_router.callback_query(F.data == "settings_assistant_menu") 
async def assistant_settings_menu_callback(callback_query: types.CallbackQuery, bot: Bot): 
    user_id = callback_query.from_user.id
    
    # Fetch current mode using the async function from user_db.py
    current_mode_code = await user_db.get_ai_mode_async(user_id)
    # Ensure default mode is set in DB if get_ai_mode_async returned default because no record found
    if current_mode_code == 'chatbot': # Assuming 'chatbot' is the default from get_ai_mode_async
        # Check if it was actually in DB or just a default return
        def _check_and_set_default_mode():
            mode_doc_check = user_db.ai_mode_collection.find_one({"user_id": user_id}) # Direct check
            if not mode_doc_check or 'mode' not in mode_doc_check:
                user_db.ai_mode_collection.update_one({"user_id": user_id}, {"$set": {"mode": "chatbot"}}, upsert=True)
        await asyncio.to_thread(_check_and_set_default_mode)

    current_mode_label = modes.get(current_mode_code, "Chatbot") 
    
    # Translate "Current mode:" and the current mode's label
    # User's current language should be fetched for accurate translation.
    # Assuming async_translate_to_lang(text, user_id) handles language fetching.
    current_mode_intro_translated = await async_translate_to_lang("Current mode:", user_id)
    current_mode_label_translated = await async_translate_to_lang(current_mode_label, user_id)
    message_text = f"{current_mode_intro_translated} **{current_mode_label_translated}**"

    # Translate button labels
    buttons_texts_to_translate = {
        "chatbot": "🤖 Chatbot", "coder": "💻 Coder/Developer", "professional": "👔 Professional",
        "teacher": "📚 Teacher", "therapist": "🩺 Therapist", "assistant": "📝 Assistant",
        "gamer": "🎮 Gamer", "translator": "🌐 Translator", "back": "🔙 Back"
    }
    
    translated_button_labels = {}
    for key, text in buttons_texts_to_translate.items():
        translated_button_labels[key] = await async_translate_to_lang(text, user_id)

    # Create keyboard with mode options
    keyboard_buttons = []
    mode_keys = list(modes.keys())
    for i in range(0, len(mode_keys), 2):
        row = []
        row.append(InlineKeyboardButton(text=translated_button_labels[mode_keys[i].lower()], callback_data=f"set_mode_{mode_keys[i]}"))
        if i + 1 < len(mode_keys):
            row.append(InlineKeyboardButton(text=translated_button_labels[mode_keys[i+1].lower()], callback_data=f"set_mode_{mode_keys[i+1]}"))
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([InlineKeyboardButton(text=translated_button_labels["back"], callback_data="settings")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback_query.message.edit_text(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode="Markdown" 
    )
    await callback_query.answer()

# Handle assistant mode change
@assistant_settings_router.callback_query(F.data.startswith("set_mode_")) 
async def change_assistant_mode_callback(callback_query: types.CallbackQuery, bot: Bot): 
    user_id = callback_query.from_user.id
    new_mode_code = callback_query.data.split("_")[2] 

    # Use the async function from user_db.py to set the mode
    await user_db.set_ai_mode_async(user_id, new_mode_code)

    current_mode_label = modes.get(new_mode_code, "Chatbot")
    
    # Fetch user's current language for translations
    # This part is crucial: if language settings are in a different module, how do we get current lang?
    # Assuming async_translate_to_lang handles it by user_id.
    current_mode_intro_translated = await async_translate_to_lang("Current mode:", user_id)
    current_mode_label_translated = await async_translate_to_lang(current_mode_label, user_id)
    message_text = f"{current_mode_intro_translated} **{current_mode_label_translated}**"
    
    alert_text_translated = await async_translate_to_lang("Assistant mode updated!", user_id)

    buttons_texts_to_translate = {
        "chatbot": "🤖 Chatbot", "coder": "💻 Coder/Developer", "professional": "👔 Professional",
        "teacher": "📚 Teacher", "therapist": "🩺 Therapist", "assistant": "📝 Assistant",
        "gamer": "🎮 Gamer", "translator": "🌐 Translator", "back": "🔙 Back"
    }
    
    translated_button_labels = {}
    for key, text in buttons_texts_to_translate.items():
        translated_button_labels[key] = await async_translate_to_lang(text, user_id)
    
    keyboard_buttons = []
    mode_keys = list(modes.keys())
    for i in range(0, len(mode_keys), 2):
        row = []
        row.append(InlineKeyboardButton(text=translated_button_labels[mode_keys[i].lower()], callback_data=f"set_mode_{mode_keys[i]}"))
        if i + 1 < len(mode_keys):
            row.append(InlineKeyboardButton(text=translated_button_labels[mode_keys[i+1].lower()], callback_data=f"set_mode_{mode_keys[i+1]}"))
        keyboard_buttons.append(row)
        
    keyboard_buttons.append([InlineKeyboardButton(text=translated_button_labels["back"], callback_data="settings")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback_query.message.edit_text(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )
    await callback_query.answer(alert_text_translated)

# Synchronous helper function is now replaced by user_db.get_ai_mode_async
# If still needed for synchronous parts of the code (not recommended from async flow),
# it would need to use the synchronous user_db functions or direct PyMongo.
# For Aiogram handlers, always use the async version.
# def get_current_ai_mode(user_id: int) -> str: 
#     # This would be a synchronous call, ensure it's not called from async event loop directly
#     mode_doc = user_db.ai_mode_collection.find_one({"user_id": user_id}) # Direct usage for example
#     if mode_doc and 'mode' in mode_doc:
#         return mode_doc['mode']
#     return "chatbot"

# For this migration, we assume all calls from handlers will be to async versions.
# The get_current_ai_mode function is removed to avoid confusion and enforce async usage.
