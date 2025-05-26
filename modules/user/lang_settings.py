from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from pymongo import MongoClient # Keep for direct calls if any remain, though ideally use user_db.py
from config import DATABASE_URL
# Assuming these lang functions are/will be Aiogram compatible
from modules.lang import async_translate_to_lang 
import database.user_db as user_db # Import user_db for its async functions
import asyncio # For asyncio.to_thread

# Router for language settings
lang_settings_router = Router()

# MongoDB Client - This direct usage should be minimized, prefer user_db.py
# client = MongoClient(DATABASE_URL) # Already in user_db.py or core.database.py
# db = client["aibotdb"]
# user_lang_collection = db['user_lang'] # Prefer get_user_lang_collection from core.database or use user_db functions

# Dictionary of languages with flags (ensure this is the single source of truth or imported)
languages = {
    "en": "🇬🇧 English", "hi": "🇮🇳 Hindi", "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic", "fr": "🇫🇷 French", "ru": "🇷🇺 Russian"
}

# Display language selection menu
@lang_settings_router.callback_query(F.data == "settings_languages_menu") # Renamed from "settings_lans"
async def language_selection_menu_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    
    # Use the async function from user_db.py
    current_language_code = await user_db.get_user_language_async(user_id)
    # The find_one call below is now redundant if get_user_language_async is comprehensive
    # and if we need to ensure the default 'en' is set, get_user_language_async should handle it
    # or we call a separate ensure_user_lang_exists_async if needed.
    # For now, just relying on get_user_language_async.
    # If current_language_code is 'en' (default) and no doc existed, user_db.get_user_language_async
    # doesn't currently create one. Let's assume for now that's okay, or it's handled at user creation.
    
    current_language_label = languages.get(current_language_code, "Unknown")
    
    # Translate "Current language:" text
    # Pass current_language_code to ensure translation happens in the user's currently selected language
    current_lang_text_translated = await async_translate_to_lang("Current language:", lang=current_language_code)
    message_text = f"{current_lang_text_translated} **{current_language_label}**"

    # Translate "Back" button text
    back_btn_text_translated = await async_translate_to_lang("🔙 Back", lang=current_language_code)

    # Create keyboard with language options
    # Buttons show flag and language name (not translated, as per original logic)
    # Callback data normalized to "set_lang_{code}"
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="🇮🇳 Hindi", callback_data="set_lang_hi"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")
        ],
        [
            InlineKeyboardButton(text="🇨🇳 Chinese", callback_data="set_lang_zh"),
            InlineKeyboardButton(text="🇸🇦 Arabic", callback_data="set_lang_ar")
        ],
        [
            InlineKeyboardButton(text="🇫🇷 French", callback_data="set_lang_fr"),
            InlineKeyboardButton(text="🇷🇺 Russian", callback_data="set_lang_ru")
        ],
        [
            InlineKeyboardButton(text=back_btn_text_translated, callback_data="settings") # Back to main settings
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback_query.message.edit_text(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode="Markdown" # For the bold current language
    )
    await callback_query.answer()

# Handle language change
@lang_settings_router.callback_query(F.data.startswith("set_lang_")) # Renamed from "language_"
async def change_language_setting_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    new_language_code = callback_query.data.split("_")[2] # e.g., "en" from "set_lang_en"

    # Use the async function from user_db.py to set the language
    await user_db.set_user_language_async(user_id, new_language_code)

    current_language_label = languages.get(new_language_code, "Unknown")
    
    # Translate "Current language:" and "Back" button using the NEW language
    current_lang_text_translated = await async_translate_to_lang("Current language:", lang=new_language_code)
    message_text = f"{current_lang_text_translated} **{current_language_label}**"
    
    back_btn_text_translated = await async_translate_to_lang("🔙 Back", lang=new_language_code)
    alert_text_translated = await async_translate_to_lang("Language updated!", lang=new_language_code)


    keyboard_buttons = [
        [
            InlineKeyboardButton(text="🇮🇳 Hindi", callback_data="set_lang_hi"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en")
        ],
        [
            InlineKeyboardButton(text="🇨🇳 Chinese", callback_data="set_lang_zh"),
            InlineKeyboardButton(text="🇸🇦 Arabic", callback_data="set_lang_ar")
        ],
        [
            InlineKeyboardButton(text="🇫🇷 French", callback_data="set_lang_fr"),
            InlineKeyboardButton(text="🇷🇺 Russian", callback_data="set_lang_ru")
        ],
        [
            InlineKeyboardButton(text=back_btn_text_translated, callback_data="settings") # Back to main settings
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback_query.message.edit_text(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )
    await callback_query.answer(alert_text_translated)

# The languages dictionary was duplicated at the end of the original file. 
# It's defined once at the top here.
