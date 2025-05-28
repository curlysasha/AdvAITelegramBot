import pyrogram
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.types import Message
from pyrogram.types import CallbackQuery
from modules.lang import async_translate_to_lang, batch_translate, format_with_mention, translate_ui_element
from modules.chatlogs import channel_log
import database.user_db as user_db
from config import ADMINS
import asyncio
import logging

logger = logging.getLogger(__name__)

# Define button texts with emojis for groups
group_button_list = [
    "🛠️ Команды",
    "🤖 О боте",
    "📞 Поддержка"
]

group_welcome_text = """
🚀 <b>Продвинутый AI-бот</b> присоединился к чату!

<b>Привет, {group_name}!</b>

Теперь я готов помогать всем в этой группе:

• 💬 <b>Умные групповые беседы</b>
• 🔍 <b>Доступ к базе знаний</b>
• 🖼️ <b>Генерация изображений</b>
• 🎙️ <b>Распознавание голоса</b>
• 🌐 <b>Мгновенный перевод</b>
• 📝 <b>Анализ текста</b>

Администраторы группы могут управлять моими правами и настройками с помощью кнопок ниже.
"""

group_tip_text = "💡 **Совет для группы:** используйте /ai с вашим вопросом или отвечайте на мои сообщения, чтобы взаимодействовать со мной. ИЛИ\nиспользуйте /img с вашим запросом, чтобы генерировать изображения!\n**Для получения дополнительных команд используйте /help.**"

LOGO = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdnp4MnR0YXk3ZGNjenR6NGRoaDNkc2h2NDgxa285NnExaGM1MTZmYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/S60CrN9iMxFlyp7uM8/giphy.gif"

# Command section for groups
group_command_text = """
**🤖 Команды бота для групп 🤖**

Выберите функцию ниже, чтобы увидеть подробные команды и примеры для групповых чатов.

**@AdvChatGptBot**
"""

group_ai_commands_text = """
**🧠 Команды AI для групп**

**Основное взаимодействие с AI:**
- Используйте `/ai [вопрос]`, чтобы задать мне вопрос напрямую
  Пример: `/ai Какова столица Японии?`
- Отвечайте на мои сообщения, чтобы продолжить беседу
- Используйте `/ask [вопрос]` или `/say [вопрос]` в качестве альтернатив

**Контекст и память:**
- Я сохраняю контекст в пределах одной темы ответов
- Начните новый запрос с любой команды, чтобы сбросить контекст
- Групповые беседы отделены от личных чатов

**Советы для групп:**
- Для вопросов по программированию я правильно отформатирую код
- Для длинных ответов я разбиваю сообщения при необходимости
- Администраторы могут настроить стиль моих ответов в настройках

****
"""

group_image_commands_text = """
**🖼️ Генерация изображений в группах**

**Создание изображений:**
- Используйте `/generate [запрос]` или `/img [запрос]`, чтобы создать изображения
  Пример: `/img киберпанковский городской пейзаж ночью`
- Сгенерированные изображения видны всем в группе
- Используйте элементы управления изображениями, чтобы регенерировать или пробовать разные стили

**Анализ изображений:**
- Отправьте любое изображение с упоминанием меня в подписи, чтобы извлечь текст
- Для сканирования документов добавьте "сканировать" в подпись
- Для анализа изображений ответьте на изображение с помощью `/ai analyze this`

**Настройки изображений в группе:**
- Администраторы группы могут включать/выключать генерацию изображений
- Доступны настройки фильтров для соответствующего контента
- Могут применяться суточные лимиты, чтобы предотвратить спам

**@AdvChatGptBot**
"""

group_main_commands_text = """
**📋 Основные команды группы**

**/start** - Получить это приветственное сообщение
**/help** - Показать информацию о командах, специфичных для группы
**/settings** - Настроить параметры бота для группы (только для администраторов)

**Команды для администраторов группы:**
- `/pin` - Закрепить сообщение (требуются права администратора)
- `/unpin` - Открепить сообщение (требуются права администратора) 
- `/warn` - Предупредить пользователя (требуются права администратора)
- Настройки группы могут настраиваться только администраторами группы

**@AdvChatGptBot**
"""

group_admin_commands_text = """
**⚙️ Команды администратора бота**

Эти команды доступны только администраторам бота.

**/restart** - Перезапустить бота (требуется подтверждение)
**/stats** - Просмотреть статистику и данные использования бота
**/gleave** - Удалить бота из группы
**/announce** - Отправить сообщение всем пользователям/группам

**Примечание:** Эти команды доступны только авторизованным администраторам, указанным в конфигурации.

**@AdvChatGptBot**
"""

async def group_start(client, message):
    """Handle the start command in groups with a modern welcome message"""
    
    # Add the group to database if not already exists
    group_id = message.chat.id
    group_name = message.chat.title
    
    # Get admin user's info who sent the command
    user_id = message.from_user.id
    
    # Check and add user to database
    await user_db.check_and_add_user(user_id)
    if message.from_user.username:
        await user_db.check_and_add_username(user_id, message.from_user.username)
    
    # Get language for translation
    user_lang = user_db.get_user_language(user_id)
    
    # Format the welcome text with group name
    formatted_text = group_welcome_text.replace("{group_name}", group_name)
    translated_welcome = await async_translate_to_lang(formatted_text, user_lang)
    
    # Translate tip text and replace bot username
    translated_tip = await async_translate_to_lang(
        group_tip_text.replace("{bot_username}", client.me.username), 
        user_lang
    )
    
    # Translate button texts
    translated_buttons = await batch_translate(group_button_list, user_id)
    
    # Create the inline keyboard buttons with translated text (arranged in two rows)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translated_buttons[0], callback_data="group_commands"),
         InlineKeyboardButton(translated_buttons[1], callback_data="about_bot")],
        [InlineKeyboardButton(translated_buttons[2], callback_data="group_support")]
    ])
    
    # Send the welcome message with the GIF and the keyboard
    await client.send_animation(
        chat_id=group_id,
        animation=LOGO,
        caption=translated_welcome,
        reply_markup=keyboard
    )
    
    await message.reply_text(translated_tip)
    
    # Check bot permissions and update group stats
    from modules.group.group_permissions import check_bot_permissions, update_group_stats, send_permissions_message
    
    try:
        # Check permissions
        permissions = await check_bot_permissions(client, group_id)
        
        # Update group stats
        await update_group_stats(group_id, permissions, user_id)
        
        # Send permissions message if needed
        await asyncio.sleep(1)  # Small delay to let welcome message be seen first
        await send_permissions_message(client, group_id, permissions)
        
        # Schedule permission check and potential leave after 5 minutes
        from modules.group.group_permissions import leave_group_if_no_permissions
        asyncio.create_task(delayed_permission_check(client, group_id))
    except Exception as e:
        # Log error but continue
        logger.error(f"Error checking permissions in group_start: {e}")
    
    # Log the bot being added to a group
    log_text = f"Bot started in group: {group_name} (ID: {group_id}) by user {message.from_user.mention}"
    await channel_log(client, message, "/start", log_text)

async def delayed_permission_check(client, chat_id, delay_seconds=300):
    """
    Check permissions after a delay and leave if required permissions are missing
    
    Args:
        client: Telegram client
        chat_id: Chat ID to check
        delay_seconds: Delay before checking (default: 5 minutes)
    """
    try:
        # Wait for the specified delay
        await asyncio.sleep(delay_seconds)
        
        # Import and check permissions
        from modules.group.group_permissions import leave_group_if_no_permissions
        await leave_group_if_no_permissions(client, chat_id)
        
    except Exception as e:
        logger.error(f"Error in delayed permission check: {e}")

# Content for group-specific callback handlers
group_commands_text = """
## 🛠️ **Команды бота** для групповых чатов

**Основные команды:**
• `/start` - Показать это приветственное сообщение
• `/help` - Получить помощь по функциям бота
• `/settings` - Настроить предпочтения бота

**Взаимодействие с AI:**
• Прямой ответ на сообщения бота
• Используйте `/ai [вопрос]` для конкретных запросов к AI

**Генерация изображений:**
• `/generate [описание]` - Создать изображения
• `/image [идея]` - Сгенерировать визуальный контент

**Администрирование группы:**
• Только администраторы группы могут изменять настройки бота
• Настройка прав в настройках группы

**Нужна дополнительная помощь?** Используйте кнопку Поддержка ниже.
"""

group_features_text = """
## ⚡ **Расширенные функции** в группах

**Умные групповые взаимодействия:**
• Поддержка нескольких языков для разнообразных групп
• Контекстно-осведомленные беседы
• Ответы на основе тем для организованных чатов

**ГенерацияRich Content:**
• Текст-в-изображение с несколькими стилями
• Транскрипция и ответ голосом
• Анализ документов и изображений

**Инструменты знаний:**
• Веб-поиск для получения последней информации
• Анализ данных и визуализация
• Объяснение и отладка кода

**Оптимизация группы:**
• Авто-модерация контента (настройка администратора)
• Пользовательские стили ответов для каждой группы
• Сохранение ответов на часто задаваемые вопросы для быстрого доступа
"""

about_bot_text = """
## 🤖 **О Продвинутом AI-боте**

**Создан с использованием передовых технологий AI:**
• GPT-4o для интеллектуальных ответов
• DALL·E 3 для генерации изображений
• Whisper для распознавания голоса
• Возможности понимания мультимодальных данных

**Конфиденциальность и данные:**
• История сообщений хранится временно
• Без обучения на частных беседах
• Содержимое группы остается конфиденциальным

**Производительность:**
• Быстрое время отклика
• Обработка нескольких бесед одновременно
• Регулярные обновления с новыми функциями

**
"""

group_settings_text = """
## ⚙️ **Настройки группы**

**Опции для владельца/администратора группы:**
• Установить язык по умолчанию для ответов
• Настроить стиль и тон ответа
• Включить/выключить определенные функции
• Контроль за тем, кто может использовать бота

**Скоро будет доступно:**
• Пользовательские приветственные сообщения
• Настройки авто-модерации
• Запланированные действия бота
• Отчеты о деятельности

**Примечание:** Изменять эти настройки могут только администраторы группы.
"""

group_support_text = """
🤖 **Информация о Продвинутом AI-боте**

Этот универсальный AI-ассистент предлагает множество возможностей для групп:

• 🖼️ Генерация изображений с помощью DALL-E-3
• 🎙️ Понимание голосовых сообщений
• 📝 Анализ изображений и извлечение текста
• 💬 Продвинутые групповые беседы
• 🌐 Поддержка нескольких языков для разнообразных команд

**
**Технология:** GPT-4o и GPT-4o-mini
**Версия:** 2.0

**Нужна помощь?** Выберите вариант ниже.
"""

async def handle_group_command_inline(client, callback):
    user_id = callback.from_user.id
    
    # Translate the command text and buttons
    texts_to_translate = [group_command_text, "🧠 AI в группах", "🖼️ Команды изображений", "📋 Основные команды", "🔙 Назад"]
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    # Extract translated results
    translated_command = translated_texts[0]
    ai_btn = translated_texts[1]
    img_btn = translated_texts[2]
    main_btn = translated_texts[3]
    back_btn = translated_texts[4]
    
    # Create base keyboard
    keyboard_buttons = [
        [InlineKeyboardButton(ai_btn, callback_data="group_cmd_ai")],
        [InlineKeyboardButton(img_btn, callback_data="group_cmd_img")],
        [InlineKeyboardButton(main_btn, callback_data="group_cmd_main")]
    ]
    
    # Add admin button if user is an admin
    if user_id in ADMINS:
        admin_btn = "⚙️ Команды администратора"
        keyboard_buttons.append([InlineKeyboardButton(admin_btn, callback_data="group_cmd_admin")])
    
    # Add back button
    keyboard_buttons.append([InlineKeyboardButton(back_btn, callback_data="back_to_group_start")])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    await client.edit_message_caption(
        chat_id=callback.message.chat.id,
        message_id=callback.message.id,
        caption=translated_command,
        reply_markup=keyboard
    )

    await callback.answer()
    return

async def handle_group_callbacks(client, callback):
    """Handle callbacks for group-specific buttons"""
    
    user_id = callback.from_user.id
    callback_data = callback.data
    user_lang = user_db.get_user_language(user_id)
    
    # Prepare back button for all menus
    back_btn_text = "↩️ Назад в главное меню"
    translated_back = await async_translate_to_lang(back_btn_text, user_lang)
    back_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(translated_back, callback_data="back_to_group_start")
    ]])
    
    # Handle different callback types
    if callback_data == "group_commands":
        # Show commands menu
        await handle_group_command_inline(client, callback)
        
    elif callback_data == "group_cmd_ai":
        # Show AI commands for groups
        translated_text = await async_translate_to_lang(group_ai_commands_text, user_lang)
        back_btn = await translate_ui_element("🔙 Назад к командам", user_lang)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="group_commands")]
        ])
        
        await client.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            caption=translated_text,
            reply_markup=keyboard
        )
        
    elif callback_data == "group_cmd_img":
        # Show Image commands for groups
        translated_text = await async_translate_to_lang(group_image_commands_text, user_lang)
        back_btn = await translate_ui_element("🔙 Назад к командам", user_lang)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="group_commands")]
        ])
        
        await client.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            caption=translated_text,
            reply_markup=keyboard
        )
        
    elif callback_data == "group_cmd_main":
        # Show main commands for groups
        translated_text = await async_translate_to_lang(group_main_commands_text, user_lang)
        back_btn = await translate_ui_element("🔙 Назад к командам", user_lang)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_btn, callback_data="group_commands")]
        ])
        
        await client.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            caption=translated_text,
            reply_markup=keyboard
        )
    
    elif callback_data == "group_cmd_admin":
        # Show admin commands (only for admins)
        if user_id in ADMINS:
            back_btn = await translate_ui_element("🔙 Назад к командам", user_lang)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(back_btn, callback_data="group_commands")]
            ])
            
            translated_text = await async_translate_to_lang(group_admin_commands_text, user_lang)
            
            await client.edit_message_caption(
                chat_id=callback.message.chat.id,
                message_id=callback.message.id,
                caption=translated_text,
                reply_markup=keyboard
            )
        else:
            # User is not an admin, show unauthorized message
            await callback.answer("У вас нет прав для просмотра команд администратора", show_alert=True)
        
    elif callback_data == "about_bot":
        # Show information about the bot
        translated_text = await async_translate_to_lang(about_bot_text, user_lang)
        
        await client.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            caption=translated_text,
            reply_markup=back_keyboard
        )
        
    elif callback_data == "group_support":
        # Show support information similar to private chat support
        translated_support = await async_translate_to_lang(group_support_text, user_lang)
        
        # Translate button labels
        contact_btn = await async_translate_to_lang("👥 Связаться с разработчиком", user_lang)
        community_btn = await async_translate_to_lang("🌐 Сообщество", user_lang)
        source_code_btn = await async_translate_to_lang("⌨️ Исходный код", user_lang)
        back_btn = await async_translate_to_lang("🔙 Назад", user_lang)
        
        # Create keyboard with support options
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(contact_btn, url="https://t.me/techycsr"),
                InlineKeyboardButton(community_btn, url="https://t.me/AdvChatGpt")
            ],
            [
                InlineKeyboardButton(source_code_btn, url="https://github.com/TechyCSR/AdvAITelegramBot")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="back_to_group_start")
            ]
        ])
        
        await client.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            caption=translated_support,
            reply_markup=keyboard
        )
        
    elif callback_data == "back_to_group_start":
        # Return to the main group welcome screen
        group_name = callback.message.chat.title
        
        # Format the welcome text with group name
        formatted_text = group_welcome_text.replace("{group_name}", group_name)
        translated_welcome = await async_translate_to_lang(formatted_text, user_lang)
        
        # Translate button texts
        translated_buttons = await batch_translate(group_button_list, user_id)
        
        # Create the inline keyboard buttons with translated text (arranged in two rows)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translated_buttons[0], callback_data="group_commands"),
             InlineKeyboardButton(translated_buttons[1], callback_data="about_bot")],
            [InlineKeyboardButton(translated_buttons[2], callback_data="group_support")]
        ])
        
        await client.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.id,
            caption=translated_welcome,
            reply_markup=keyboard
        )
    
    # Acknowledge the callback
    await callback.answer()

