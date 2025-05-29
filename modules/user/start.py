import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, format_with_mention
from modules.chatlogs import channel_log
import database.user_db as user_db

# Define button texts with emojis
button_list = [
    "➕ Добавить в группу",
    "🛠️ Команды",
    "❓ Помощь",
    "⚙️ Настройки"
    # "📞 Поддержка"  # Временно убрана из меню
]

welcome_text = """
✨ **Добро пожаловать, {user_mention}!** ✨

🤖 **Продвинутый ИИ-бот**

Я могу помочь вам с:

🧠 **Умный чат** — Интеллектуальные беседы с GPT-4o  
🗣️ **Голос и текст** — Преобразование голоса в текст и обратно  
🖼️ **Создание изображений** — Генерация впечатляющих визуалов из текста  
📝 **Извлечение текста** — Анализ текста из любого изображения  
🌐 **Многоязычность** — Общение на вашем языке

━━━━━━━━━━━━━━━━━━━━━

👨‍💻 👨‍💻 **Вайбкодинг by [%NeuroTemp%](https://t.me/neurotemporary)**

****
"""

tip_text = "💡 **Совет:** Введите любое сообщение, чтобы начать чат со мной, ИЛИ используй /img с промтом для генерации изображений!\n**Для получения списка команд используй /help.**"

LOGO = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMmNzeGptdm8xeDR4ZXFkODFxaXdxbmJyODF4eWtwcjB4bzl0Znc3ZSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/09YEygqh7LhUV7sNMY/giphy.gif"

async def start(client, message):
    await user_db.check_and_add_user(message.from_user.id)
    if message.from_user.username:
        await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

    # Get user info
    user_id = message.from_user.id
    mention = message.from_user.mention
    
    # First safely format the welcome text with mention preservation
    user_lang = user_db.get_user_language(user_id)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    
    # Translate other texts
    translated_texts = await batch_translate([tip_text], user_id)
    translated_tip = translated_texts[0]
    translated_buttons = button_list  # Всегда использовать русский вариант

    # Create the inline keyboard buttons with translated text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translated_buttons[0], url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton(translated_buttons[1], callback_data="commands"),
         InlineKeyboardButton(translated_buttons[2], callback_data="help")],
        [InlineKeyboardButton(translated_buttons[3], callback_data="settings")]
        # Кнопка поддержки убрана
    ])

    # Send the welcome message with the GIF and the keyboard
    await client.send_animation(
        chat_id=message.chat.id,
        animation=LOGO,
        caption=translated_welcome,
        reply_markup=keyboard
    )
    await message.reply_text(translated_tip)

async def start_inline(bot, callback):
    user_id = callback.from_user.id
    mention = callback.from_user.mention
    user_lang = user_db.get_user_language(user_id)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    translated_buttons = button_list  # Всегда использовать русский вариант
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translated_buttons[0], url=f"https://t.me/{bot.me.username}?startgroup=true")],
        [InlineKeyboardButton(translated_buttons[1], callback_data="commands"),
         InlineKeyboardButton(translated_buttons[2], callback_data="help")],
        [InlineKeyboardButton(translated_buttons[3], callback_data="settings")]
        # Кнопка поддержки убрана
    ])
    await bot.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        caption=translated_welcome,
        reply_markup=keyboard
    )

