import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import InlineQuery
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
from modules.chatlogs import channel_log
from config import ADMINS


command__text = """
**🤖 Команды бота 🤖**

Выберите функцию ниже, чтобы увидеть подробные команды и примеры.

**@AdvChatGptBot**
"""

ai_commands_text = """
**🧠 Команды AI-чата**

**В личных чатах:**
- Просто напишите сообщение, и я отвечу
- Отправьте голосовое сообщение для распознавания
- Используйте `/new` или `/newchat` для нового диалога

**В группах:**
- Используйте `/ai [вопрос]` чтобы спросить напрямую
  Пример: `/ai Какая погода в Париже?`
- Отвечайте на мои сообщения для продолжения диалога
- Можно также использовать `/ask [вопрос]` или `/say [вопрос]`

**Советы:**
- Я помню контекст в личных чатах
- Для вопросов по коду указывайте язык программирования
- Используйте `/new` для сброса истории

**@AdvChatGptBot**
"""

image_commands_text = """
**🖼️ Команды генерации изображений**

**В личных чатах:**
- Используйте `/generate [запрос]` или `/img [запрос]` для создания изображений
  Пример: `/img горный пейзаж на закате`
- После ввода запроса выберите стиль
- Используйте кнопку регенерации для нового варианта

**В группах:**
- Используйте те же команды, что и в личных чатах
- Все могут просматривать и реагировать на изображения
- Только автор запроса может регенерировать изображение

**Анализ изображений:**
- Отправьте любое изображение для извлечения текста
- В группах добавьте "ai" в подпись к фото для анализа

**Советы:**
- Уточняйте детали для лучшего результата
- Пробуйте разные стили
- Добавляйте художественные референсы

**@AdvChatGptBot**
"""

main_commands_text = """
**📋 Основные команды**

**/start** — Запустить бота и увидеть приветствие
**/help** — Показать справку
**/settings** — Настроить бота
**/rate** — Оценить работу бота

**@AdvChatGptBot**
"""

admin_commands_text = """
**⚙️ Админ-команды**

Эти команды доступны только администраторам бота.

**/restart** — Перезапустить бота (требует подтверждения)
**/stats** — Показать статистику и данные использования
**/logs** — Получить последние записи журнала
**/announce** — Отправить сообщение всем пользователям
**/gleave** — Выйти из группового чата
**/invite** — Добавить бота в группу
**/uinfo** — Получить информацию о пользователях

**Внимание:** Только для администраторов из конфигурации.

**@AdvChatGptBot**
"""


async def command_inline(client, callback):
    user_id = callback.from_user.id
    
    # Русские кнопки
    ai_btn = "🧠 AI-чат"
    img_btn = "🖼️ Генерация изображений"
    main_btn = "📋 Основные команды"
    back_btn = "🔙 Назад"
    
    # Create base keyboard
    keyboard_buttons = [
        [InlineKeyboardButton(ai_btn, callback_data="cmd_ai")],
        [InlineKeyboardButton(img_btn, callback_data="cmd_img")],
        [InlineKeyboardButton(main_btn, callback_data="cmd_main")]
    ]
    
    # Add admin button if user is an admin
    if user_id in ADMINS:
        admin_btn = "⚙️ Админ-команды"
        keyboard_buttons.append([InlineKeyboardButton(admin_btn, callback_data="cmd_admin")])
    
    # Исправлено: callback_data для возврата к help-меню теперь "back_to_help"
    keyboard_buttons.append([InlineKeyboardButton(back_btn, callback_data="back_to_help")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    await client.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        text=command__text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

    await callback.answer()
    return

async def handle_command_callbacks(client, callback):
    user_id = callback.from_user.id
    callback_data = callback.data
    
    if callback_data == "cmd_ai":
        # Show AI commands
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_help")]
        ])
        
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=ai_commands_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    elif callback_data == "cmd_img":
        # Show Image commands
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_help")]
        ])
        
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=image_commands_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    elif callback_data == "cmd_main":
        # Show main commands
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_help")]
        ])
        
        await client.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            text=main_commands_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    elif callback_data == "cmd_admin":
        # Show admin commands (only for admins)
        if user_id in ADMINS:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_help")]
            ])
            
            await client.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.id,
                text=admin_commands_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            # User is not an admin, show unauthorized message
            await callback.answer("У вас нет прав для просмотра админ-команд", show_alert=True)
    elif callback_data == "back_to_help":
        # Возврат к help-меню
        from modules.user.help import help_inline
        await help_inline(client, callback)
    await callback.answer()
    return


