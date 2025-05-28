from pyrogram import Client, filters
from config import DATABASE_URL, LOG_CHANNEL
from pymongo import MongoClient
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from modules.lang import async_translate_to_lang

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
user_voice_collection = db["user_voice_setting"]
ai_mode_collection = db['ai_mode']

modes = {
    "chatbot": "Чат-бот",
    "coder": "Программист",
    "professional": "Профессионал",
    "teacher": "Учитель",
    "therapist": "Терапевт",
    "assistant": "Помощник",
    "gamer": "Геймер",
    "translator": "Переводчик"
}

languages = {
    "en": "🇬🇧 Английский",
    "hi": "🇮🇳 Хинди",
    "zh": "🇨🇳 Китайский",
    "ar": "🇸🇦 Арабский",
    "fr": "🇫🇷 Французский",
    "ru": "🇷🇺 Русский"
}

async def global_setting_command(client, message):
    global_settings_text = """
⚙️ <b>Меню настроек для пользователя {mention}</b>

<b>ID пользователя</b>: {user_id}
<b>Язык интерфейса</b>: {language}
<b>Голосовой режим</b>: {voice_setting}
<b>Режим ассистента</b>: {mode}

Вы можете изменить настройки через меню настроек @AdvChatGptBot.

<b>@AdvChatGptBot</b>
"""
    temp = await message.reply_text("**Получение ваших настроек...**")

    user_id = message.from_user.id
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})

    if user_lang_doc:
        current_language = user_lang_doc['language']
    else:
        current_language = "ru"
        user_lang_collection.insert_one({"user_id": user_id, "language": current_language})
    
    current_language_label = languages[current_language]

    user_settings = user_voice_collection.find_one({"user_id": user_id})
    if user_settings:
        voice_setting = user_settings.get("voice", "voice")
        if voice_setting == "text":
            voice_setting = "Text"
    else:
        voice_setting = "voice"
        user_voice_collection.insert_one({"user_id": user_id, "voice": "voice"})
    
    user_mode_doc = ai_mode_collection.find_one({"user_id": user_id})

    if user_mode_doc:
        current_mode = user_mode_doc['mode']
    else:
        current_mode = "chatbot"
        ai_mode_collection.insert_one({"user_id": user_id, "mode": current_mode})
    
    current_mode_label = modes[current_mode]

    translated_text = await async_translate_to_lang(global_settings_text, user_id)
    formatted_text = translated_text.format(
        mention=message.from_user.mention,
        user_id=message.from_user.id,
        language=current_language_label,
        voice_setting=voice_setting,
        mode=current_mode_label,
    )

    kbd = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔧 Bot Settings", url=f"https://t.me/{client.me.username}?start=settings")
            ]
        ]
    )

    await message.reply_text(formatted_text, reply_markup=kbd)
    await temp.delete()