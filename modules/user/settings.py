from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from pymongo import MongoClient
from config import DATABASE_URL
# Assuming these lang functions are/will be Aiogram compatible
from modules.lang import async_translate_to_lang, translate_ui_element, batch_translate, format_with_mention
# from modules.chatlogs import channel_log # Not used in this file

# Router for settings
settings_router = Router()

# MongoDB Client (ensure this is handled appropriately in an async context if it's blocking)
client = MongoClient(DATABASE_URL)
db = client["aibotdb"]
user_voice_collection = db["user_voice_setting"]
user_lang_collection = db['user_lang']
ai_mode_collection = db['ai_mode']

# Data dictionaries (copied from global_setting.py for self-containment if needed, or import from a central place)
modes = {
    "chatbot": "Chatbot", "coder": "Coder/Developer", "professional": "Professional",
    "teacher": "Teacher", "therapist": "Therapist", "assistant": "Personal Assistant",
    "gamer": "Gamer", "translator": "Translator"
}
languages = {
    "en": "🇬🇧 English", "hi": "🇮🇳 Hindi", "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic", "fr": "🇫🇷 French", "ru": "🇷🇺 Russian"
}

settings_text_template = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User Language:** {language}
**User Voice**: {voice_setting}
**User Mode**: {mode}

You can change your settings from below options.

**@{bot_username}** 
""" # Added {bot_username}

# Main settings menu
@settings_router.callback_query(F.data.in_({"settings", "settings_back"})) # "settings_back" to return here
async def settings_menu_callback(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id

    # Fetch user data (similar to global_settings.py, consider refactoring to user_db.py)
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    current_language_code = user_lang_doc['language'] if user_lang_doc and 'language' in user_lang_doc else "en"
    current_language_label = languages.get(current_language_code, "Unknown")

    user_voice_doc = user_voice_collection.find_one({"user_id": user_id})
    voice_setting_value = user_voice_doc.get("voice", "voice") if user_voice_doc and 'voice' in user_voice_doc else "voice"
    voice_setting_label = "Text" if voice_setting_value == "text" else "Voice"

    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    current_mode_code = user_mode_doc['mode'] if user_mode_doc and 'mode' in user_mode_doc else "chatbot"
    current_mode_label = modes.get(current_mode_code, "Chatbot")

    mention = callback_query.from_user.mention_html()
    bot_username = (await bot.get_me()).username

    # Translate template and format
    # format_with_mention might need update if it expects Pyrogram's mention
    # For now, assuming it can handle HTML mention or the main text part is translated first
    translated_template_text = await async_translate_to_lang(settings_text_template.split("{mention}")[0], user_id) \
                               + mention \
                               + await async_translate_to_lang(settings_text_template.split("{mention}")[1], user_id)


    formatted_text = translated_template_text.format(
        mention=mention, # This is already in the translated_template_text
        user_id=user_id,
        language=current_language_label,
        voice_setting=voice_setting_label,
        mode=current_mode_label,
        bot_username=bot_username
    )
    
    button_labels_to_translate = ["🌐 Language", "🎙️ Voice", "🤖 Assistant", "🔧 Others", "🔙 Back"]
    translated_labels = await batch_translate(button_labels_to_translate, user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=translated_labels[0], callback_data="settings_languages_menu"), # To lang_settings.py
            InlineKeyboardButton(text=translated_labels[1], callback_data="settings_voice_menu")
        ],
        [
            InlineKeyboardButton(text=translated_labels[2], callback_data="settings_assistant_menu"), # To assistant.py
            InlineKeyboardButton(text=translated_labels[3], callback_data="settings_others") # Assuming "settings_others" exists
        ],
        [
            InlineKeyboardButton(text=translated_labels[4], callback_data="main_menu") # Back to start.py main menu
        ]
    ])

    await callback_query.message.edit_text(
        text=formatted_text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode="HTML" # Since mention is HTML
    )
    await callback_query.answer()

# Voice settings menu (previously settings_language_callback)
@settings_router.callback_query(F.data == "settings_voice_menu") # Renamed from "settings_v"
async def voice_settings_menu_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    
    user_voice_doc = user_voice_collection.find_one({"user_id": user_id})
    current_voice_setting = user_voice_doc.get("voice", "voice") if user_voice_doc and 'voice' in user_voice_doc else "voice"

    texts_to_translate = ["Voice", "Text", "Current setting: Answering in", "queries only.", "🔙 Back"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    voice_text_label = translated_texts[0]
    text_option_label = translated_texts[1]
    current_setting_intro = translated_texts[2]
    queries_only_suffix = translated_texts[3]
    back_btn_text = translated_texts[4]
    
    voice_button_display_text = f"🎙️ {voice_text_label} {'✅' if current_voice_setting == 'voice' else ''}".strip()
    text_button_display_text = f"💬 {text_option_label} {'✅' if current_voice_setting == 'text' else ''}".strip()

    message_text = f"{current_setting_intro} **{voice_text_label if current_voice_setting == 'voice' else text_option_label}** {queries_only_suffix}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=voice_button_display_text, callback_data="set_voice_voice"),
            InlineKeyboardButton(text=text_button_display_text, callback_data="set_voice_text")
        ],
        [
            InlineKeyboardButton(text=back_btn_text, callback_data="settings") # Back to main settings
        ]
    ])

    await callback_query.message.edit_text(
        text=message_text,
        reply_markup=keyboard,
        parse_mode="Markdown" # Text has Markdown
    )
    await callback_query.answer()

# Handler for changing voice setting
@settings_router.callback_query(F.data.startswith("set_voice_"))
async def change_voice_setting_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    new_voice_setting = callback_query.data.split("_")[2] # "voice" or "text"

    user_voice_collection.update_one(
        {"user_id": user_id},
        {"$set": {"voice": new_voice_setting}},
        upsert=True
    )

    # Re-display the voice settings menu with updated state
    # This avoids duplicating the message construction logic.
    # For this to work, the context (callback_query, bot) must be passed correctly.
    # Alternatively, just call the function directly if it's safe.
    # To be safe, we can reconstruct the message here or call the menu function.
    # For simplicity, let's call the menu function.
    # This creates a slight issue if the called function expects a different `data` pattern.
    # So, it's better to reconstruct or refactor message construction.

    texts_to_translate = ["Voice", "Text", "Current setting: Answering in", "queries only.", "🔙 Back", "Setting updated!"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    voice_text_label = translated_texts[0]
    text_option_label = translated_texts[1]
    current_setting_intro = translated_texts[2]
    queries_only_suffix = translated_texts[3]
    back_btn_text = translated_texts[4]
    alert_text = translated_texts[5]

    voice_button_display_text = f"🎙️ {voice_text_label} {'✅' if new_voice_setting == 'voice' else ''}".strip()
    text_button_display_text = f"💬 {text_option_label} {'✅' if new_voice_setting == 'text' else ''}".strip()

    message_text = f"{current_setting_intro} **{voice_text_label if new_voice_setting == 'voice' else text_option_label}** {queries_only_suffix}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=voice_button_display_text, callback_data="set_voice_voice"),
            InlineKeyboardButton(text=text_button_display_text, callback_data="set_voice_text")
        ],
        [
            InlineKeyboardButton(text=back_btn_text, callback_data="settings") # Back to main settings
        ]
    ])

    await callback_query.message.edit_text(
        text=message_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback_query.answer(alert_text)

# Note: settings_voice_inlines was identical to settings_inline in the provided Pyrogram code.
# It has been handled by settings_menu_callback with F.data.in_({"settings", "settings_back"}).
# If it was intended to be a different menu, it needs its own callback data and logic.
# For now, assuming "settings_back" callback is used to return to the main settings menu.
# The original `settings_voice_inlines` was triggered by `settings_voice_inlines` callback data.
# If this specific callback data is still used elsewhere, a handler for it might be needed.
# Based on the prompt, `settings_voice_inlines` was for "voice selection options", which is what `settings_voice_menu` now does.
# The prompt's `settings_v` for `settings_language_callback` (now `voice_settings_menu_callback`) implies `settings_voice_menu` is the correct new callback.
# The prompt's `settings_voice_inlines` with callback `settings_voice_inlines` seems to be a misinterpretation or a redundant function in original code.
# I'll map `settings_v` to `settings_voice_menu` for voice settings.
# And `settings_lans` to `settings_languages_menu` for language list (in lang_settings.py).
# The main settings menu is triggered by `settings` or `settings_back`.
# The "Voice" button in the main settings menu points to `settings_voice_menu`.
# The "Language" button in the main settings menu points to `settings_languages_menu`.
# This structure seems logical.
