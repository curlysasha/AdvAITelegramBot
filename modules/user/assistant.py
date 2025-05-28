from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import async_translate_to_lang

from config import DATABASE_URL

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
ai_mode_collection = db['ai_mode']

# Dictionary of modes with labels
modes = {
    "chatbot": "Чат-бот",
    "coder": "Программист",
    "professional": "Профессионал",
    "teacher": "Учитель",
    "therapist": "Терапевт",
    "assistant": "Персональный помощник",
    "gamer": "Геймер",
    "translator": "Переводчик"
}

# Function to handle settings assistant callback
async def settings_assistant_callback(client, callback):
    user_id = callback.from_user.id
    
    # Fetch the user's current mode from the database
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    
    current_mode_label = modes[current_mode]
    message_text = f"Текущий режим: {current_mode_label}"

    # Жёстко задаём русские надписи для кнопок
    chatbot_text = "🤖 Чат-бот"
    coder_text = "💻 Программист"
    professional_text = "👔 Профессионал"
    teacher_text = "📚 Учитель"
    therapist_text = "🩺 Терапевт"
    assistant_text = "📝 Помощник"
    gamer_text = "🎮 Геймер"
    translator_text = "🌐 Переводчик"
    back_btn = "🔙 Назад"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(chatbot_text, callback_data="mode_chatbot"),
             InlineKeyboardButton(coder_text, callback_data="mode_coder")],
            [InlineKeyboardButton(professional_text, callback_data="mode_professional"),
             InlineKeyboardButton(teacher_text, callback_data="mode_teacher")],
            [InlineKeyboardButton(therapist_text, callback_data="mode_therapist"),
             InlineKeyboardButton(assistant_text, callback_data="mode_assistant")],
            [InlineKeyboardButton(gamer_text, callback_data="mode_gamer"),
             InlineKeyboardButton(translator_text, callback_data="mode_translator")],
            [InlineKeyboardButton(back_btn, callback_data="settings_back")]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Function to handle mode setting change
async def change_mode_setting(client, callback):
    mode = callback.data.split("_")[1]
    user_id = callback.from_user.id

    # Update the user's mode in the database
    ai_mode_collection.update_one(
        {"user_id": user_id},
        {"$set": {"mode": mode}},
        upsert=True
    )

    current_mode_label = modes[mode]
    message_text = f"Текущий режим: {current_mode_label}"

    # Жёстко задаём русские надписи для кнопок
    chatbot_text = "🤖 Чат-бот"
    coder_text = "💻 Программист"
    professional_text = "👔 Профессионал"
    teacher_text = "📚 Учитель"
    therapist_text = "🩺 Терапевт"
    assistant_text = "📝 Помощник"
    gamer_text = "🎮 Геймер"
    translator_text = "🌐 Переводчик"
    back_btn = "🔙 Назад"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(chatbot_text, callback_data="mode_chatbot"),
             InlineKeyboardButton(coder_text, callback_data="mode_coder")],
            [InlineKeyboardButton(professional_text, callback_data="mode_professional"),
             InlineKeyboardButton(teacher_text, callback_data="mode_teacher")],
            [InlineKeyboardButton(therapist_text, callback_data="mode_therapist"),
             InlineKeyboardButton(assistant_text, callback_data="mode_assistant")],
            [InlineKeyboardButton(gamer_text, callback_data="mode_gamer"),
             InlineKeyboardButton(translator_text, callback_data="mode_translator")],
            [InlineKeyboardButton(back_btn, callback_data="settings_back")]
        ]
    )

    await callback.message.edit(
        text=message_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

def current_mode(user_id):
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})
    if user_mode_doc:
        return user_mode_doc['mode']
    else:
        return "chatbot"