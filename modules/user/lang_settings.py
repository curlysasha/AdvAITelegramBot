from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from pymongo import MongoClient
from config import DATABASE_URL
# Assuming these lang functions are/will be Aiogram compatible
from modules.lang import async_translate_to_lang # batch_translate, translate_ui_element not used here

# Router for language settings
lang_settings_router = Router()

# MongoDB Client
client = MongoClient(DATABASE_URL)
db = client["aibotdb"]
user_lang_collection = db['user_lang']

# Dictionary of languages with flags (ensure this is the single source of truth or imported)
languages = {
    "en": "🇬🇧 English", "hi": "🇮🇳 Hindi", "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic", "fr": "🇫🇷 French", "ru": "🇷🇺 Russian"
}

# Display language selection menu
@lang_settings_router.callback_query(F.data == "settings_languages_menu") # Renamed from "settings_lans"
async def language_selection_menu_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    current_language_code = user_lang_doc['language'] if user_lang_doc and 'language' in user_lang_doc else "en"
    
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

    user_lang_collection.update_one(
        {"user_id": user_id},
        {"$set": {"language": new_language_code}},
        upsert=True
    )

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
