from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from pymongo import MongoClient
from config import DATABASE_URL
# Assuming these lang functions are/will be Aiogram compatible
from modules.lang import async_translate_to_lang 

# Router for assistant/mode settings
assistant_settings_router = Router()

# MongoDB Client
# Consider moving DB initialization to a central place if not already done.
client = MongoClient(DATABASE_URL)
db = client["aibotdb"]
ai_mode_collection = db['ai_mode']

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
    
    # Fetch current mode from DB
    # These DB calls are synchronous. For a fully async app, consider an async driver like Motor.
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    current_mode_code = user_mode_doc['mode'] if user_mode_doc and 'mode' in user_mode_doc else "chatbot"
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

    ai_mode_collection.update_one(
        {"user_id": user_id},
        {"$set": {"mode": new_mode_code}},
        upsert=True
    )

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

# Synchronous helper function (consider making async or moving to a db utility module)
def get_current_ai_mode(user_id: int) -> str: 
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    if user_mode_doc and 'mode' in user_mode_doc:
        return user_mode_doc['mode']
    # Default to "chatbot" and optionally store it if not found
    # ai_mode_collection.update_one({"user_id": user_id}, {"$set": {"mode": "chatbot"}}, upsert=True)
    return "chatbot"
