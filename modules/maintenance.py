from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest # For handling MessageNotModified

# Assuming these are or will be Aiogram-compatible
from modules.lang import async_translate_to_lang
from modules.core.database import get_feature_settings_collection
from config import ADMINS, OWNER_ID # Direct import for admin checks

# Assuming Theme module is or will be Aiogram-compatible
from modules.ui.theme import Theme, Colors 

maintenance_router = Router()

# Default feature states (remains the same)
DEFAULT_FEATURE_STATES = {
    "maintenance_mode": False, "image_generation": True,
    "voice_features": True, "ai_response": True
}

# Cache for feature states (logic remains the same)
_feature_states_cache: Optional[Dict[str, bool]] = None
_cache_initialized: bool = False

async def get_feature_states() -> dict:
    global _feature_states_cache, _cache_initialized
    if _cache_initialized and _feature_states_cache is not None: # Ensure cache is not None
        return _feature_states_cache
    
    feature_settings_collection = get_feature_settings_collection()
    settings_doc = feature_settings_collection.find_one({"settings_id": "global"})
    
    if not settings_doc:
        feature_settings_collection.insert_one({"settings_id": "global", **DEFAULT_FEATURE_STATES})
        _feature_states_cache = DEFAULT_FEATURE_STATES.copy()
    else:
        settings = settings_doc.copy()
        if "_id" in settings: del settings["_id"]
        if "settings_id" in settings: del settings["settings_id"]
        _feature_states_cache = settings
    
    _cache_initialized = True
    return _feature_states_cache if _feature_states_cache is not None else {}


async def set_feature_state(feature: str, state: bool) -> None:
    global _feature_states_cache, _cache_initialized
    if _cache_initialized and _feature_states_cache is not None:
        _feature_states_cache[feature] = state
    
    feature_settings_collection = get_feature_settings_collection()
    feature_settings_collection.update_one(
        {"settings_id": "global"}, 
        {"$set": {feature: state}},
        upsert=True
    )

# Added user_id parameter as per usage in handlers.py, though original didn't have it.
# If it's truly global, user_id isn't needed. If per-user features exist, this needs more thought.
# For now, assuming it's global as per DB structure.
async def is_feature_enabled(feature: str, user_id: Optional[int] = None) -> bool:
    states = await get_feature_states()
    return states.get(feature, DEFAULT_FEATURE_STATES.get(feature, False))

async def is_admin_user(user_id: int) -> bool:
    # Ensure ADMINS are integers for comparison
    int_admins = {int(admin_id) for admin_id in ADMINS if str(admin_id).isdigit()}
    return user_id in int_admins or user_id == int(OWNER_ID) if str(OWNER_ID).isdigit() else False


async def maintenance_check(user_id: int) -> bool:
    if await is_admin_user(user_id):
        return False
    return await is_feature_enabled("maintenance_mode")

# Added feature_specific_key for more targeted maintenance messages
async def maintenance_message(user_id: int, feature_specific_key: Optional[str] = None) -> str:
    # This function can be expanded to return different messages based on feature_specific_key
    if feature_specific_key == "image_analysis_disabled":
        text = "🖼️ Image analysis is currently disabled by the admin."
    elif feature_specific_key == "image_analysis_group_disabled":
        text = "🖼️ Image analysis in groups is currently disabled by the admin."
    else: # Default maintenance message
        text = """
🚧 **Bot Maintenance in Progress** 🚧
Our bot is currently undergoing maintenance. We apologize for any inconvenience.
The system will be back online as soon as possible.
For urgent inquiries, contact @techycsr.
"""
    return await async_translate_to_lang(text, user_id)


@maintenance_router.callback_query(F.data == "settings_others")
async def settings_others_callback_handler(callback_query: types.CallbackQuery, bot: Bot):
    # This now directly calls the logic that was in maintenance_settings
    user_id = callback_query.from_user.id
    if await is_admin_user(user_id):
        await show_admin_panel_handler(callback_query, bot) # Call adapted show_admin_panel
    else:
        await show_user_maintenance_info(callback_query, bot) # New function for user view

async def show_user_maintenance_info(callback_query: types.CallbackQuery, bot: Bot): # bot may not be needed
    user_id = callback_query.from_user.id
    message_text = await async_translate_to_lang(
        "⚙️ **System Information**\n\nThis section shows the current status of the bot's features. "
        "If features are disabled, please check back later or contact support.", 
        user_id
    )
    states = await get_feature_states()
    enabled_text = await async_translate_to_lang("✅ Enabled", user_id)
    disabled_text = await async_translate_to_lang("❌ Disabled", user_id)
    back_text = await async_translate_to_lang("🔙 Back", user_id)
    
    feature_labels = {
        "ai_response": await async_translate_to_lang("AI Response", user_id),
        "image_generation": await async_translate_to_lang("Image Generation", user_id),
        "voice_features": await async_translate_to_lang("Voice Features", user_id)
    }
    
    status_lines = [f"• {label}: {enabled_text if states.get(key, DEFAULT_FEATURE_STATES.get(key)) else disabled_text}" 
                    for key, label in feature_labels.items()]
    status_message = "\n\n**Current Feature Status:**\n" + "\n".join(status_lines)
    
    if states.get('maintenance_mode', False):
        maintenance_info = await async_translate_to_lang(
            "\n⚠️ **The bot is currently in maintenance mode.** Some features may be unavailable.", user_id
        )
        status_message += maintenance_info
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data="settings_support")] # Back to support menu
    ])
    await callback_query.message.edit_text(text=message_text + status_message, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()

# This is the new handler for showing the admin panel, replacing the direct call to show_admin_panel
# if show_admin_panel was called by `admin_panel` callback from user_support.py
# For `settings_others` when user is admin, it's called by settings_others_callback_handler
async def show_admin_panel_handler(callback_query: types.CallbackQuery, bot: Bot): # bot might not be needed
    user_id = callback_query.from_user.id
    states = await get_feature_states()
    
    # Translations (assuming Theme class doesn't handle translations internally for labels)
    admin_title = await async_translate_to_lang("⚙️ **Advanced Admin Control Panel**", user_id)
    admin_desc = await async_translate_to_lang(
        "Control bot features and maintenance from this dashboard. Changes are immediate.", user_id
    )
    maint_label = await async_translate_to_lang("🚧 Maintenance Mode", user_id)
    img_label = await async_translate_to_lang("🖼️ Image Generation", user_id)
    voice_label = await async_translate_to_lang("🎙️ Voice Features", user_id)
    ai_label = await async_translate_to_lang("🤖 AI Response", user_id)
    stats_text = await async_translate_to_lang("📊 Statistics", user_id)
    users_text = await async_translate_to_lang("👥 Users", user_id)
    # donate_text = await async_translate_to_lang("💰 Donations", user_id) # Original had this, but Theme might not

    # Assuming Theme.toggle_control_layout and Theme.admin_button are Aiogram compatible
    # and generate lists of InlineKeyboardButton lists.
    keyboard_layout = [
        [InlineKeyboardButton(text=f"{Colors.ADMIN} System Controls", callback_data="admin_header_ignore")],
        *Theme.toggle_control_layout(maint_label, Colors.WARNING, states.get("maintenance_mode", False), "maintenance_mode"),
        [InlineKeyboardButton(text=f"{Colors.SETTINGS} Feature Controls", callback_data="features_header_ignore")],
        *Theme.toggle_control_layout(img_label, Colors.IMAGE, states.get("image_generation", True), "image_generation"),
        *Theme.toggle_control_layout(voice_label, Colors.VOICE, states.get("voice_features", True), "voice_features"),
        *Theme.toggle_control_layout(ai_label, Colors.AI, states.get("ai_response", True), "ai_response"),
        [InlineKeyboardButton(text=f"{Colors.STATS} Admin Tools", callback_data="admin_tools_header_ignore")],
        [Theme.admin_button(stats_text, "admin_view_stats"), Theme.admin_button(users_text, "admin_users")],
        # [Theme.admin_button(donate_text, "support_donate")], # This was in original, check if Theme supports it or add manually
        [Theme.back_button("settings_support")] # Back to support menu
    ]
    
    status_summary_list = [
        f"• {maint_label}: {'✅' if states.get('maintenance_mode', False) else '❌'}",
        f"• {img_label}: {'✅' if states.get('image_generation', True) else '❌'}",
        f"• {voice_label}: {'✅' if states.get('voice_features', True) else '❌'}",
        f"• {ai_label}: {'✅' if states.get('ai_response', True) else '❌'}"
    ]
    status_summary = "\n\n**Current Status:**\n" + "\n".join(status_summary_list)
    message_text = f"{admin_title}\n\n{admin_desc}{status_summary}"
    
    try:
        await callback_query.message.edit_text(text=message_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_layout), parse_mode="Markdown")
    except TelegramBadRequest as e: # More specific exception
        if "MESSAGE_NOT_MODIFIED" in str(e):
            await callback_query.answer("Panel already up to date.")
        else:
            # logger.error(f"Error showing admin panel: {e}") # Requires logger setup
            await callback_query.answer(f"Error: {str(e)[:150]}", show_alert=True)
    await callback_query.answer()


@maintenance_router.callback_query(F.data.startswith("toggle_"))
async def handle_feature_toggle_callback(callback_query: types.CallbackQuery, bot: Bot): # bot might not be needed
    if not await is_admin_user(callback_query.from_user.id):
        await callback_query.answer("You don't have permission.", show_alert=True)
        return
    
    parts = callback_query.data.split('_') # Expected: toggle_FEATUREID_true or toggle_FEATUREID_false
    feature_id = '_'.join(parts[1:-1]) 
    new_state = parts[-1].lower() == 'true'
    
    await set_feature_state(feature_id, new_state)
    
    feature_name_display = feature_id.replace('_', ' ').title()
    state_text_display = "enabled" if new_state else "disabled"
    await callback_query.answer(f"{feature_name_display} {state_text_display}", show_alert=True)
    
    await show_admin_panel_handler(callback_query, bot) # Refresh panel

@maintenance_router.callback_query(F.data.startswith("feature_info_"))
async def handle_feature_info_callback(callback_query: types.CallbackQuery, bot: Bot): # bot might not be needed
    user_id = callback_query.from_user.id
    feature_id = callback_query.data.replace('feature_info_', '')
    
    descriptions = {
        "maintenance_mode": "When enabled, shows maintenance message to regular users. Admins can still use the bot.",
        "image_generation": "Controls image generation commands. Disable if the image service has issues or for cost control.",
        "voice_features": "Controls voice message processing (voice-to-text and text-to-voice).",
        "ai_response": "Controls the bot's ability to respond to text messages using AI. Core functionality."
    }
    
    states = await get_feature_states()
    current_state = states.get(feature_id, DEFAULT_FEATURE_STATES.get(feature_id, False))
    state_text_display = "✅ Enabled" if current_state else "❌ Disabled"
    
    description_text = descriptions.get(feature_id, "No detailed information available for this feature.")
    feature_name_display = feature_id.replace('_', ' ').title()
    
    info_alert_text = await async_translate_to_lang(
        f"{feature_name_display}: {description_text}\n\nStatus: {state_text_display}", user_id
    )
    
    try:
        await callback_query.answer(info_alert_text, show_alert=True)
    except TelegramBadRequest: # If message is too long for an alert
        short_info = await async_translate_to_lang(f"{feature_name_display} Status: {state_text_display}", user_id)
        await callback_query.answer(short_info, show_alert=True)

@maintenance_router.callback_query(F.data == "support_donate")
async def handle_donation_callback(callback_query: types.CallbackQuery, bot: Bot): # bot might not be needed
    user_id = callback_query.from_user.id
    donation_text_template = """
💰 **Support Bot Development**
Your donations help maintain and improve this bot.
Developer: Chandan Singh (@techycsr)
UPI ID: `csr.info.in@oksbi` (Scan QR or use any UPI app)
After donating, message @techycsr for premium features.
Thank you for your support! 🙏"""
    
    translated_donation_text = await async_translate_to_lang(donation_text_template, user_id)
    back_btn_text = await async_translate_to_lang("🔙 Back", user_id)
    
    # Assuming this callback came from dev_support.py, so back to "support_developers"
    # Or if it's from admin panel, it might be "admin_panel" or "settings_support"
    # The original had "support_developers"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_btn_text, callback_data="support_developers")] 
    ])
    
    await callback_query.message.edit_text(text=translated_donation_text, reply_markup=keyboard, disable_web_page_preview=True, parse_mode="Markdown")
    await callback_query.answer()

# Placeholder for header callbacks if they are not just for display
@maintenance_router.callback_query(F.data.in_({"admin_header_ignore", "features_header_ignore", "admin_tools_header_ignore"}))
async def ignore_header_callbacks(callback_query: types.CallbackQuery):
    await callback_query.answer() # Just acknowledge, do nothing
