from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules.lang import async_translate_to_lang
from modules.maintenance import maintenance_settings, is_admin_user

from config import ADMINS as admin_ids, OWNER_ID

support_text ="""
🤖 **Информация о продвинутом AI-боте**

Этот универсальный AI-ассистент поддерживает широкий спектр возможностей:

• 🖼️ Генерация изображений (DALL-E-3)
• 🎙️ Голосовые взаимодействия
• 📝 Анализ изображений (текст из фото)
• 💬 Продвинутый диалоговый AI
• 🌐 Многоязычная поддержка

**Разработчик:** [Chandan Singh](https://techycsr.me)
**Технологии:** GPT-4o и GPT-4o-mini
**Версия:** 2.0

**Нужна помощь?** Выберите опцию ниже.
"""

# Функция для обработки колбэка поддержки
async def settings_support_callback(client, callback_query):
    user_id = callback_query.from_user.id
    # Жёстко задаём русские надписи для кнопок
    admin_button_text = "👑 Админ-панель"
    developers_btn = "👨‍💻 Разработчики"
    community_btn = "🌐 Сообщество"
    source_code_btn = "⌨️ Исходный код"
    system_status_btn = "🖥️ Статус системы"
    back_btn = "🔙 Назад"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(admin_button_text, callback_data="admin_panel"),
         InlineKeyboardButton(developers_btn, callback_data="support_developers")],
        [InlineKeyboardButton(community_btn, url="https://t.me/AdvChatGpt"),
         InlineKeyboardButton(source_code_btn, url="https://github.com/TechyCSR/AdvAITelegramBot")],
        [InlineKeyboardButton(system_status_btn, callback_data="settings_others")],
        [InlineKeyboardButton(back_btn, callback_data="back_to_help")],  # Кнопка поддержки временно убрана
    ])
    await callback_query.message.edit(
        text="<b>📞 Поддержка и информация</b>\n\nЗдесь вы можете получить помощь, узнать о разработчиках и статусе системы.",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# Функция для обработки колбэка с информацией об администраторах
async def support_admins_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id

    # Информация о контакте администратора
    admin_contact_info = """
👤 **Контакт разработчика и администратора**

**Chandan Singh** (@techycsr)
Техноэнтузиаст и разработчик

• **Портфолио:** [techycsr.me](https://techycsr.me)
• **GitHub:** [TechyCSR](https://github.com/TechyCSR)
• **Email:** csr.info.in@gmail.com

**Обо мне:**
Я увлечён Python, AI/ML и open-source. Специализируюсь на создании Telegram-ботов с Pyrogram и MongoDB, AI-приложениях и web-проектах.

**Каналы поддержки:**
• Сообщество: @AdvChatGpt
• Вопросы: [GitHub Repository](https://github.com/TechyCSR/AdvAITelegramBot/issues)

Пишите по любым вопросам, предложениям или для сообщения об ошибках.
    """
    
    # Переводим кнопки и текст (оставим на русском, чтобы не было лишних переводов)
    back_btn = "🔙 Назад"
    contact_btn = "💬 Написать разработчику"
    website_btn = "🌐 Открыть сайт"
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(contact_btn, url="https://t.me/techycsr"),
                InlineKeyboardButton(website_btn, url="https://techycsr.me")
            ],
            [
                InlineKeyboardButton(back_btn, callback_data="support")
            ]
        ]
    )
    
    await callback.message.edit(
        text=admin_contact_info,
        reply_markup=keyboard,
        disable_web_page_preview=False  # Показываем карточку сайта
    )

# Функция для перехода в админ-панель
async def admin_panel_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Verify user is admin before proceeding
    if not await is_admin_user(user_id):
        alert_message = await async_translate_to_lang(
            "⚠️ Unauthorized access attempt. This action has been logged.", 
            user_id
        )
        await callback.answer(alert_message, show_alert=True)
        return
        
    await maintenance_settings(client, callback)

# Feature states (defaults)
feature_states = {
    "image_generation": "off",
    "voice_feature": "off",
    "premium_service": "off"
}

# # Function to handle feature state toggling
# async def toggle_feature(client, callback: CallbackQuery, feature: str, state: str):
#     feature_states[feature] = state

#     # Update the admin panel
#     await support_admins_callback(client, callback)

# # Callback query handlers for toggling features
# async def toggle_image_generation(client, callback: CallbackQuery):
#     await toggle_feature(client, callback, "image_generation", "on" if feature_states["image_generation"] == "off" else "off")

# async def toggle_voice_feature(client, callback: CallbackQuery):
#     await toggle_feature(client, callback, "voice_feature", "on" if feature_states["voice_feature"] == "off" else "off")

# async def toggle_premium_service(client, callback: CallbackQuery):
#     await toggle_feature(client, callback, "premium_service", "on" if feature_states["premium_service"] == "off" else "off")

# # Callback query handlers for setting features directly
# async def set_image_generation(client, callback: CallbackQuery):
#     state = callback.data.split('_')[-1]
#     await toggle_feature(client, callback, "image_generation", state)

# async def set_voice_feature(client, callback: CallbackQuery):
#     state = callback.data.split('_')[-1]
#     await toggle_feature(client, callback, "voice_feature", state)

# async def set_premium_service(client, callback: CallbackQuery):
#     state = callback.data.split('_')[-1]
#     await toggle_feature(client, callback, "premium_service", state)

# async def handle_support(client, callback: CallbackQuery):
#     await settings_support_callback(client, callback)

