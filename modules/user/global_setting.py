from aiogram import types, Router, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from pymongo import MongoClient # Assuming pymongo is used correctly
from config import DATABASE_URL # Assuming config is accessible
# Assuming these lang functions are/will be Aiogram compatible
from modules.lang import async_translate_to_lang 

# Router for global settings command
global_settings_router = Router()

# Initialize the MongoDB client (remains the same, ensure it's handled correctly in async env)
# Consider moving DB initialization to a central place if not already done.
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
user_voice_collection = db["user_voice_setting"]
ai_mode_collection = db['ai_mode']

# Data dictionaries (remain the same)
modes = {
    "chatbot": "Chatbot",
    "coder": "Coder/Developer",
    "professional": "Professional",
    "teacher": "Teacher",
    "therapist": "Therapist",
    "assistant": "Personal Assistant",
    "gamer": "Gamer",
    "translator": "Translator"
}

languages = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 Hindi",
    "zh": "🇨🇳 Chinese",
    "ar": "🇸🇦 Arabic",
    "fr": "🇫🇷 French",
    "ru": "🇷🇺 Russian"
}

global_settings_text_template = """
**Setting Menu for User {mention}**

**User ID**: {user_id}
**User language:** {language}
**User voice**: {voice_setting}
**User mode**: {mode}

You can change your settings from @{bot_username}'s settings menu.

**@{bot_username}**
"""

@global_settings_router.message(Command("settings"))
async def global_settings_command_handler(message: types.Message, bot: Bot): 
    temp_message = await message.answer("<i>Fetching your settings...</i>", parse_mode="HTML") 

    user_id = message.from_user.id
    
    # Fetch user settings from MongoDB
    # For PyMongo, these are blocking operations. For a fully async bot, consider using an async MongoDB driver like Motor.
    # For this migration, we'll keep the PyMongo calls as they were, assuming they are acceptable for now.
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    user_voice_doc = user_voice_collection.find_one({"user_id": user_id})
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})

    # Determine current language
    if user_lang_doc and 'language' in user_lang_doc: 
        current_language_code = user_lang_doc['language']
    else:
        current_language_code = "en" # Default language
        user_lang_collection.update_one({"user_id": user_id}, {"$set": {"language": current_language_code}}, upsert=True)
    current_language_label = languages.get(current_language_code, "Unknown") 

    # Determine current voice setting
    if user_voice_doc and 'voice' in user_voice_doc: 
        voice_setting_value = user_voice_doc.get("voice", "voice") 
        voice_setting_label = "Text" if voice_setting_value == "text" else "Voice"
    else:
        voice_setting_label = "Voice" # Default setting label
        user_voice_collection.update_one({"user_id": user_id}, {"$set": {"voice": "voice"}}, upsert=True) # Store default value "voice"
    
    # Determine current AI mode
    if user_mode_doc and 'mode' in user_mode_doc: 
        current_mode_code = user_mode_doc['mode']
    else:
        current_mode_code = "chatbot" # Default mode
        ai_mode_collection.update_one({"user_id": user_id}, {"$set": {"mode": current_mode_code}}, upsert=True)
    current_mode_label = modes.get(current_mode_code, "Chatbot") 

    bot_username = (await bot.get_me()).username
    
    # Translate the template
    # Note: async_translate_to_lang itself needs to be Aiogram compatible if it uses bot/client objects
    translated_template = await async_translate_to_lang(global_settings_text_template, user_id)

    formatted_text = translated_template.format(
        mention=message.from_user.mention_html(), 
        user_id=message.from_user.id,
        language=current_language_label,
        voice_setting=voice_setting_label, 
        mode=current_mode_label,
        bot_username=bot_username 
    )

    # Translate button text
    button_text = await async_translate_to_lang("🔧 Bot Settings", user_id)

    # Create keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=button_text, url=f"https://t.me/{bot_username}?start=settings")
        ]
    ])

    # Edit the temporary message with the final content
    try:
        await temp_message.edit_text(formatted_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e: 
        # If editing fails (e.g., message too old, or content identical), send a new message and delete old temp.
        # This is a fallback, ideally edit should work.
        await message.answer(formatted_text, reply_markup=keyboard, parse_mode="HTML")
        await temp_message.delete()
        # Log the exception `e` for debugging if needed.
        print(f"Error editing message in global_settings: {e}")
