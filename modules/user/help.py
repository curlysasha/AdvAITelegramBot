import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
from modules.chatlogs import channel_log


help_text = """
✨ **PocketChatGPT - ЦЕНТР ПОМОЩИ** ✨

━━━━━━━━━━━━━━━━━━━

Этот интеллектуальный бот создан
чтобы принести мощные AI-функции прямо в ваши чаты Telegram.

**ВЫБЕРИТЕ КАТЕГОРИЮ НИЖЕ:**
"""

ai_chat_help = """
🧠 **AI ЧАТ-АССИСТЕНТ** 🧠

━━━━━━━━━━━━━━━━━━━

Бот использует **GPT-4o** для предоставления умных ответов на любые вопросы.

**ОСНОВНЫЕ ВОЗМОЖНОСТИ:**
• 💬 **Контекст** — Помнит историю переписки
• 🧩 **Сложные вопросы** — Подробные, продуманные ответы
• 💻 **Генерация кода** — С подсветкой синтаксиса
• 🔢 **Математика** — Решает уравнения и задачи
• 🌎 **Перевод** — Работает на разных языках

**КОМАНДЫ:**
• 💬 В личных чатах: Просто напишите сообщение
• 🔄 В группах: Используйте `/ai`, `/ask` или `/say` + вопрос
• 🆕 Сбросить чат: `/new` или `/newchat`

**ПРИМЕР:**
`/ai Чем квантовые вычисления отличаются от классических?`

**💡 СОВЕТ:** Для вопросов по коду указывайте язык программирования для лучшего форматирования.
"""

image_gen_help = """
🖼️ **ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ** 🖼️

━━━━━━━━━━━━━━━━━━━

Создавайте потрясающие изображения по текстовому описанию с помощью ИИ.

**ОСНОВНЫЕ ВОЗМОЖНОСТИ:**
• 🎨 **Качественные изображения** — Детализированные и реалистичные
• 🏞️ **Множество стилей** — Реализм, Арт, Эскиз, 3D
• 🔄 **Регенерация** — Повтор с тем же запросом в один клик
• 👥 **Работает везде** — В личных и групповых чатах

**КОМАНДЫ:**
• 📝 `/generate [запрос]` — Полная команда
• 📸 `/img [запрос]` — Короткая альтернатива
• 🖌️ `/gen [запрос]` — Самая короткая версия

**ПРИМЕР:**
`/img киберпанк-город ночью с неоновыми огнями и летающими машинами`

**💡 СОВЕТЫ:**
• Уточняйте детали, освещение и ракурс
• Добавляйте художественные референсы для лучшего результата
• Пробуйте разные стили для разнообразия
"""

voice_features_help = """
🎙️ **ГОЛОСОВЫЕ ФУНКЦИИ** 🎙️

━━━━━━━━━━━━━━━━━━━

Преобразуйте голос в текст и обратно с помощью ИИ.

**ОСНОВНЫЕ ВОЗМОЖНОСТИ:**
• 🗣️ **Голос в текст** — Распознаёт голосовые сообщения
• 🔊 **Текст в голос** — Озвучивает ответы бота
• 🌐 **Мультиязычность** — Работает на разных языках
• 💬 **Диалог** — Можно задавать вопросы голосом

**КАК ИСПОЛЬЗОВАТЬ:**
1. 🎤 Отправьте голосовое сообщение
2. 📝 Бот преобразует в текст и поймёт
3. 💬 Бот ответит на ваш вопрос
4. ⚙️ Настройте голосовые параметры в меню настроек

**💡 СОВЕТЫ:**
• Говорите чётко в тихой обстановке
• Сообщения до 1 минуты — лучший результат
• Установите предпочитаемый язык голоса в настройках
"""

image_analysis_help = """
🔍 **АНАЛИЗ ИЗОБРАЖЕНИЙ** 🔍

━━━━━━━━━━━━━━━━━━━

Извлекайте и анализируйте текст с изображений с помощью OCR.

**ОСНОВНЫЕ ВОЗМОЖНОСТИ:**
• 📱 **Извлечение текста** — С фото и скриншотов
• 📄 **Сканирование документов** — Чтение печатных документов
• ❓ **Вопросы по тексту** — Задавайте вопросы по извлечённому тексту
• 📊 **Распознавание данных** — Таблицы, чеки и др.

**КАК ИСПОЛЬЗОВАТЬ:**
1. 📷 Отправьте изображение с текстом
2. 🔍 Бот извлечёт весь читаемый текст
3. 💬 Задайте вопросы по содержимому
4. 📱 В группах добавьте "ai" в подпись к фото

**💡 СОВЕТЫ:**
• Используйте хорошее освещение
• Фотографируйте текст прямо, не под углом
• Обрезайте фото, чтобы оставить только нужный текст
"""

quick_start_help = """
🚀 **БЫСТРЫЙ СТАРТ** 🚀

━━━━━━━━━━━━━━━━━━━

**НАЧНИТЕ ЗА 3 ШАГА:**

1️⃣ **Общайтесь с ИИ**
   • В личке: Просто напишите сообщение
   • В группе: Используйте команду `/ai`

2️⃣ **Генерируйте изображения**
   • Используйте `/img` и описание
   • Пример: `/img закат над горами`

3️⃣ **Анализируйте изображения**
   • Отправьте изображение с текстом
   • Бот извлечёт и проанализирует текст

**ПОЛЕЗНЫЕ КОМАНДЫ:**
• `/start` — Главное меню
• `/help` — Центр помощи
• `/settings` — Настройки бота
• `/new` — Очистить историю чата

**ВОЗНИКЛИ ПРОБЛЕМЫ?**
• Выберите кнопку поддержки в главном меню
• Пробуйте более конкретные запросы для лучшего результата
"""


async def help(client, message):
    user_id = message.from_user.id
    
    # Translate help text and button labels
    texts_to_translate = [
        help_text, 
        "🧠 AI Chat", 
        "🖼️ Image Generation", 
        "🎙️ Voice Features",
        "🔍 Image Analysis",
        "🚀 Quick Start",
        "📋 Commands"
    ]
    
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    translated_help = translated_texts[0]
    ai_btn = translated_texts[1]
    img_btn = translated_texts[2]
    voice_btn = translated_texts[3]
    analysis_btn = translated_texts[4]
    quickstart_btn = translated_texts[5]
    cmd_btn = translated_texts[6]
    
    # Create interactive keyboard with feature categories
    # No back button when accessed directly through /help command
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ai_btn, callback_data="help_ai")],
        [InlineKeyboardButton(img_btn, callback_data="help_img")],
        [InlineKeyboardButton(voice_btn, callback_data="help_voice")],
        [InlineKeyboardButton(analysis_btn, callback_data="help_analysis")],
        [InlineKeyboardButton(quickstart_btn, callback_data="help_quickstart")],
        [InlineKeyboardButton(cmd_btn, callback_data="commands")]
    ])
    
    await client.send_message(
        chat_id=message.chat.id,
        text=translated_help,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

async def help_inline(client, callback):
    user_id = callback.from_user.id
    # Жёстко задаём русские надписи для кнопок
    ai_btn = "🧠 AI-чат"
    img_btn = "🖼️ Генерация изображений"
    voice_btn = "🎙️ Голосовые функции"
    analysis_btn = "🔍 Анализ изображений"
    quickstart_btn = "🚀 Быстрый старт"
    cmd_btn = "📋 Команды"
    back_btn = "🔙 Назад"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ai_btn, callback_data="help_ai")],
        [InlineKeyboardButton(img_btn, callback_data="help_img")],
        [InlineKeyboardButton(voice_btn, callback_data="help_voice")],
        [InlineKeyboardButton(analysis_btn, callback_data="help_analysis")],
        [InlineKeyboardButton(quickstart_btn, callback_data="help_quickstart")],
        [InlineKeyboardButton(cmd_btn, callback_data="commands")],
        [InlineKeyboardButton(back_btn, callback_data="back_to_help")]
    ])
    try:
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=help_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            raise
    await callback.answer()
    return
    
async def handle_help_category(client, callback):
    user_id = callback.from_user.id
    callback_data = callback.data
    
    help_content = help_text  # Default
    if callback_data == "help_ai":
        help_content = ai_chat_help
    elif callback_data == "help_img":
        help_content = image_gen_help
    elif callback_data == "help_voice":
        help_content = voice_features_help
    elif callback_data == "help_analysis":
        help_content = image_analysis_help
    elif callback_data == "help_quickstart":
        help_content = quick_start_help
    
    # Translate the selected help content
    translated_text = await async_translate_to_lang(help_content, user_id)
    back_btn = "🔙 Назад"
    
    # Use "help" as callback_data to return to main help menu
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(back_btn, callback_data="help")]
    ])
    
    await client.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=translated_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    
    await callback.answer()
    return

