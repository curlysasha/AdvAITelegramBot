from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import async_translate_to_lang
from modules.core.database import get_feature_settings_collection
from config import ADMINS, OWNER_ID

# Default feature states
DEFAULT_FEATURE_STATES = {
    "maintenance_mode": False,
    "image_generation": True,
    "voice_features": True,
    "ai_response": True
}

# Cache for feature states to avoid frequent DB access
_feature_states_cache = None
_cache_initialized = False

async def get_feature_states() -> dict:
    """
    Get the current feature states from the database or initialize with defaults
    
    Returns:
        Dictionary of feature states
    """
    global _feature_states_cache, _cache_initialized
    
    # Return cached states if available
    if _cache_initialized:
        return _feature_states_cache
    
    # Get the feature settings collection
    feature_settings = get_feature_settings_collection()
    
    # Try to get the current settings
    settings_doc = feature_settings.find_one({"settings_id": "global"})
    
    if not settings_doc:
        # Initialize with defaults
        feature_settings.insert_one({
            "settings_id": "global",
            **DEFAULT_FEATURE_STATES
        })
        _feature_states_cache = DEFAULT_FEATURE_STATES.copy()
    else:
        # Remove _id and settings_id
        settings = settings_doc.copy()
        if "_id" in settings:
            del settings["_id"]
        if "settings_id" in settings:
            del settings["settings_id"]
        _feature_states_cache = settings
    
    _cache_initialized = True
    return _feature_states_cache

async def set_feature_state(feature: str, state: bool) -> None:
    """
    Set the state of a feature in the database
    
    Args:
        feature: Feature name
        state: New state (True/False)
    """
    global _feature_states_cache, _cache_initialized
    
    # Update the cache
    if _cache_initialized and _feature_states_cache:
        _feature_states_cache[feature] = state
    
    # Get the feature settings collection
    feature_settings = get_feature_settings_collection()
    
    # Update the feature state
    feature_settings.update_one(
        {"settings_id": "global"}, 
        {"$set": {feature: state}},
        upsert=True
    )

async def is_feature_enabled(feature: str) -> bool:
    """
    Check if a feature is enabled
    
    Args:
        feature: Feature name
        
    Returns:
        True if feature is enabled, False otherwise
    """
    states = await get_feature_states()
    return states.get(feature, DEFAULT_FEATURE_STATES.get(feature, False))

async def is_admin_user(user_id: int) -> bool:
    """
    Check if a user is an admin or owner
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if user is admin or owner, False otherwise
    """
    return user_id in ADMINS or user_id == OWNER_ID

async def maintenance_check(user_id: int) -> bool:
    """
    Check if the bot is in maintenance mode and the user is not an admin
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if bot is in maintenance AND user is not admin
    """
    if await is_admin_user(user_id):
        return False
        
    return await is_feature_enabled("maintenance_mode")

async def maintenance_message(user_id: int) -> str:
    maintenance_text = """
🚧 <b>Бот на техническом обслуживании</b> 🚧\n\nНаш бот сейчас проходит обслуживание для улучшения работы и добавления новых функций.\n\nПриносим извинения за неудобства и благодарим за терпение!\n\nСистема будет доступна как можно скорее.\n\nПо срочным вопросам:\n• Разработчик: @techycsr\n• Сайт: techycsr.me
"""
    return maintenance_text

async def settings_others_callback(client, callback: CallbackQuery):
    """Handle settings_others callback - redirects to maintenance section now"""
    await maintenance_settings(client, callback)

async def maintenance_settings(client, callback: CallbackQuery):
    """Display maintenance settings page with admin options if applicable"""
    user_id = callback.from_user.id
    
    if await is_admin_user(user_id):
        # User is admin, show admin panel
        await show_admin_panel(client, callback)
    else:
        # Regular user, show maintenance info
        message = "⚙️ <b>Системная информация</b>\n\nВ этом разделе отображается текущий статус функций бота. Если какие-то функции отключены, попробуйте позже или обратитесь в поддержку."
        
        # Show current feature states
        states = await get_feature_states()
        
        # Translate status texts
        enabled_text = "✅ Включено"
        disabled_text = "❌ Отключено"
        back_text = "🔙 Назад"
        
        # Feature texts
        ai_text = "🤖 Ответы ИИ"
        img_text = "🖼️ Генерация изображений"
        voice_text = "🎙️ Голосовые функции"
        
        # Build status message
        status_message = f"\n\n<b>Текущий статус функций:</b>\n\n"
        status_message += f"• {ai_text}: {enabled_text if states.get('ai_response', True) else disabled_text}\n"
        status_message += f"• {img_text}: {enabled_text if states.get('image_generation', True) else disabled_text}\n"
        status_message += f"• {voice_text}: {enabled_text if states.get('voice_features', True) else disabled_text}\n"
        
        # Add maintenance mode message if enabled
        if states.get('maintenance_mode', False):
            maintenance_info = "\n⚠️ <b>Бот сейчас в режиме обслуживания.</b>\nНекоторые функции могут быть недоступны."
            status_message += maintenance_info
        
        # Build keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(back_text, callback_data="support")]
        ])
        
        await callback.message.edit(
            text=message + status_message,
            reply_markup=keyboard
        )
        
async def show_admin_panel(client, callback: CallbackQuery):
    """Show the admin panel with feature toggle options"""
    user_id = callback.from_user.id
    
    # Get current states
    states = await get_feature_states()
    
    # Translate UI elements
    admin_title = "⚙️ <b>Админ-панель управления</b>"
    admin_desc = "Управляйте функциями и режимом обслуживания бота из этого централизованного меню.\n\nВключайте и выключайте функции одной кнопкой. Изменения применяются сразу."
    
    # Feature labels
    maint_label = "🚧 Режим обслуживания"
    img_label = "🖼️ Генерация изображений"
    voice_label = "🎙️ Голосовые функции"
    ai_label = "🤖 Ответы ИИ"
    
    # Status indicators
    maint_status = "✅" if states.get("maintenance_mode", False) else "❌"
    img_status = "✅" if states.get("image_generation", True) else "❌"
    voice_status = "✅" if states.get("voice_features", True) else "❌"
    ai_status = "✅" if states.get("ai_response", True) else "❌"
    
    # Button labels
    toggle_text = "Переключить"
    info_text = "Инфо"
    back_text = "🔙 Назад"
    stats_text = "📊 Статистика"
    users_text = "👥 Пользователи"
    donate_text = "💰 Донаты"
    
    # Import the Theme module
    from modules.ui.theme import Theme, Colors
    
    # Create modern control panel - flat list of rows
    keyboard = []
    
    # Header section
    keyboard.append([InlineKeyboardButton(f"{Colors.ADMIN} Управление системой", callback_data="admin_header")])
    
    # Get toggle layouts and add each row separately
    maintenance_toggle_rows = Theme.toggle_control_layout(
        feature_name=maint_label,
        emoji=Colors.WARNING,
        is_enabled=states.get("maintenance_mode", False),
        feature_id="maintenance_mode"
    )
    for row in maintenance_toggle_rows:
        keyboard.append(row)
    
    # Feature Controls header
    keyboard.append([InlineKeyboardButton(f"{Colors.SETTINGS} Управление функциями", callback_data="features_header")])
    
    # Image generation toggle
    image_toggle_rows = Theme.toggle_control_layout(
        feature_name=img_label,
        emoji=Colors.IMAGE,
        is_enabled=states.get("image_generation", True),
        feature_id="image_generation"
    )
    for row in image_toggle_rows:
        keyboard.append(row)
    
    # Voice features toggle
    voice_toggle_rows = Theme.toggle_control_layout(
        feature_name=voice_label,
        emoji=Colors.VOICE,
        is_enabled=states.get("voice_features", True),
        feature_id="voice_features"
    )
    for row in voice_toggle_rows:
        keyboard.append(row)
    
    # AI response toggle
    ai_toggle_rows = Theme.toggle_control_layout(
        feature_name=ai_label,
        emoji=Colors.AI,
        is_enabled=states.get("ai_response", True),
        feature_id="ai_response"
    )
    for row in ai_toggle_rows:
        keyboard.append(row)
    
    # Advanced Admin Tools
    keyboard.append([InlineKeyboardButton(f"{Colors.STATS} Админ-инструменты", callback_data="admin_tools_header")])
    
    # Stats and Users buttons row
    keyboard.append([
        Theme.admin_button(stats_text, "admin_view_stats"),
        Theme.admin_button(users_text, "admin_users")
    ])
    
    # Donation button row
    keyboard.append([
        Theme.admin_button(donate_text, "support_donate")
    ])
    
    # Back button
    keyboard.append([Theme.back_button("support")])
    
    # Create status summary
    status_summary = "\n\n<b>Текущий статус:</b>\n"
    status_summary += f"• {maint_label}: {maint_status}\n"
    status_summary += f"• {img_label}: {img_status}\n"
    status_summary += f"• {voice_label}: {voice_status}\n"
    status_summary += f"• {ai_label}: {ai_status}\n"
    
    message_text = f"{admin_title}\n\n{admin_desc}{status_summary}"
    
    try:
        await callback.message.edit(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        # Handle MessageNotModified error by silently ignoring it
        if "MESSAGE_NOT_MODIFIED" in str(e):
            # Just acknowledge the callback instead
            await callback.answer("Панель уже актуальна")
            pass
        else:
            # For other errors, log and notify
            # logger.error(f"Error showing admin panel: {str(e)}")
            await callback.answer(f"Ошибка: {str(e)[:20]}...", show_alert=True)

async def handle_feature_toggle(client, callback: CallbackQuery):
    """Handle feature toggle callback"""
    if not await is_admin_user(callback.from_user.id):
        await callback.answer("У вас нет прав для изменения настроек.", show_alert=True)
        return
    
    # Extract feature and state from callback data
    # Format: toggle_FEATURE_STATE
    parts = callback.data.split('_')
    feature = '_'.join(parts[1:-1])  # Handle feature names with underscores
    state = parts[-1].lower() == 'true'
    
    # Update feature state
    await set_feature_state(feature, state)
    
    # Show confirmation
    feature_name = feature.replace('_', ' ').title()
    state_text = "включено" if state else "отключено"
    await callback.answer(f"{feature_name} {state_text}", show_alert=True)
    
    # Refresh admin panel
    await show_admin_panel(client, callback)

async def handle_feature_info(client, callback: CallbackQuery):
    """Show information about a specific feature"""
    user_id = callback.from_user.id
    
    # Extract feature from callback data
    # Format: feature_info_FEATURE
    feature = callback.data.replace('feature_info_', '')
    
    # Feature descriptions - SHORTENED to avoid MESSAGE_TOO_LONG errors
    descriptions = {
        "maintenance_mode": "Если включено, обычные пользователи видят сообщение о тех. работах. Только админы могут пользоваться ботом.",
        "image_generation": "Включает/выключает генерацию изображений (/generate, /img). Отключайте при проблемах с сервисом.",
        "voice_features": "Включает/выключает обработку голосовых сообщений. Можно отключить для снижения нагрузки.",
        "ai_response": "Включает/выключает ответы бота на текстовые сообщения. Основная функция."
    }
    
    # Get current state
    states = await get_feature_states()
    current_state = states.get(feature, DEFAULT_FEATURE_STATES.get(feature, False))
    state_text = "✅ Включено" if current_state else "❌ Отключено"
    
    description = descriptions.get(feature, "Нет информации.")
    feature_name = feature.replace('_', ' ').title()
    
    # Translate the message - kept very short for alert
    info_text = f"{feature_name}: {description}\nСтатус: {state_text}"
    
    try:
        await callback.answer(info_text, show_alert=True)
    except Exception as e:
        # If too long, try an even shorter version
        short_info = f"{feature_name}\nСтатус: {state_text}"
        await callback.answer(short_info, show_alert=True)

async def handle_donation(client, callback: CallbackQuery):
    """Show donation options with UPI ID"""
    user_id = callback.from_user.id
    
    # Create donation message
    donation_text = """
💰 <b>Поддержка разработки бота</b>\n\nВаши донаты помогают поддерживать и развивать этот бот, добавлять новые функции и улучшать производительность.\n\n
"""
    
    back_btn = "🔙 Назад"
    
    # Create keyboard with back button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(back_btn, callback_data="support_developers")]
    ])
    
    # Show donation message
    await callback.message.edit(
        text=donation_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

