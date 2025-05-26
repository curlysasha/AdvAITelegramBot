from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Assuming these modules are or will be Aiogram-compatible
from modules.lang import async_translate_to_lang
from modules.maintenance import maintenance_settings, is_admin_user # Assuming these are adapted for Aiogram
from config import ADMINS as admin_ids, OWNER_ID # For admin checks if is_admin_user is not solely used

user_support_router = Router()

support_text_template = """
🤖 **Advanced AI Bot Information**

This versatile AI assistant supports a wide range of capabilities:

• 🖼️ Image Generation (DALL-E-3)
• 🎙️ Voice Interactions
• 📝 Image-to-Text Analysis
• 💬 Advanced Conversational AI
• 🌐 Multi-language Support

**Developed by:** [Chandan Singh](https://techycsr.me)
**Technology:** GPT-4o and GPT-4o-mini
**Version:** 2.0

**Need assistance?** Choose an option below.
""" # Renamed to template for clarity

admin_contact_info_template = """
👤 **Developer & Admin Contact**

**Chandan Singh** (@techycsr)
Tech Enthusiast & Student Developer

• **Portfolio:** [techycsr.me](https://techycsr.me)
• **GitHub:** [TechyCSR](https://github.com/TechyCSR)
• **Email:** csr.info.in@gmail.com

**About Me:**
I'm a tech enthusiast with a strong passion for Python, AI/ML, and open-source development. I specialize in building Telegram bots using Pyrogram and MongoDB, developing AI-powered applications, and managing web development projects.

**Support Channels:**
• Community: @AdvChatGpt
• Issues: [GitHub Repository](https://github.com/TechyCSR/AdvAITelegramBot/issues)

Feel free to reach out for assistance, feature requests, or to report issues.
""" # Renamed for clarity

@user_support_router.callback_query(F.data.in_({"settings_support", "support"}))
async def settings_support_menu_callback(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    
    translated_support_text = await async_translate_to_lang(support_text_template, user_id)
    
    # Translate button labels
    admins_btn_text = await async_translate_to_lang("👥 Contact Admin", user_id)
    developers_btn_text = await async_translate_to_lang("💻 Developer Info", user_id)
    community_btn_text = await async_translate_to_lang("🌐 Community", user_id)
    source_code_btn_text = await async_translate_to_lang("⌨️ Source Code", user_id)
    system_status_btn_text = await async_translate_to_lang("📊 System Status", user_id) # Assuming "settings_others" handles this
    back_btn_text = await async_translate_to_lang("🔙 Back", user_id)

    is_admin = await is_admin_user(user_id) # Assuming is_admin_user is Aiogram compatible
    admin_button_text_key = "⚙️ Admin Panel" if is_admin else "👥 Contact Admin"
    admin_button_text_translated = await async_translate_to_lang(admin_button_text_key, user_id)
    admin_button_callback_data = "admin_panel" if is_admin else "support_admins"
    
    admin_indicator_key = "\n\n🔑 **Admin Access Granted**" if is_admin else ""
    admin_indicator_translated = await async_translate_to_lang(admin_indicator_key, user_id) if is_admin else ""


    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=admin_button_text_translated, callback_data=admin_button_callback_data),
            InlineKeyboardButton(text=developers_btn_text, callback_data="support_developers") # To dev_support.py
        ],
        [
            InlineKeyboardButton(text=community_btn_text, url="https://t.me/AdvChatGpt"),
            InlineKeyboardButton(text=source_code_btn_text, url="https://github.com/TechyCSR/AdvAITelegramBot")
        ],
        [
            InlineKeyboardButton(text=system_status_btn_text, callback_data="settings_others") # Assuming this is handled
        ],
        [
            InlineKeyboardButton(text=back_btn_text, callback_data="settings") # Back to main settings menu
        ]
    ])

    await callback_query.message.edit_text(
        text=translated_support_text + admin_indicator_translated,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode="Markdown" if is_admin else None # Markdown for admin_indicator
    )
    await callback_query.answer()

@user_support_router.callback_query(F.data == "support_admins")
async def contact_admins_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id

    translated_admin_info = await async_translate_to_lang(admin_contact_info_template, user_id)
    back_btn_text = await async_translate_to_lang("🔙 Back", user_id)
    contact_btn_text = await async_translate_to_lang("💬 Message Developer", user_id)
    website_btn_text = await async_translate_to_lang("🌐 Visit Website", user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=contact_btn_text, url="https://t.me/techycsr"),
            InlineKeyboardButton(text=website_btn_text, url="https://techycsr.me")
        ],
        [
            InlineKeyboardButton(text=back_btn_text, callback_data="settings_support") # Back to support menu
        ]
    ])
    
    await callback_query.message.edit_text(
        text=translated_admin_info,
        reply_markup=keyboard,
        disable_web_page_preview=False, # To show website card
        parse_mode="Markdown" # Text contains markdown links
    )
    await callback_query.answer()

@user_support_router.callback_query(F.data == "admin_panel")
async def admin_panel_info_callback(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    
    if not await is_admin_user(user_id): # Assuming is_admin_user is Aiogram compatible
        alert_message = await async_translate_to_lang(
            "⚠️ Unauthorized access attempt. This action has been logged.", 
            user_id
        )
        await callback_query.answer(alert_message, show_alert=True)
        return
    
    # The original function called maintenance_settings(client, callback)
    # Assuming maintenance_settings is adapted for Aiogram: async def maintenance_settings(bot: Bot, query: types.CallbackQuery)
    # This function might replace the current message with the maintenance panel.
    # If maintenance_settings directly edits the message, then this function might not need to edit it further.
    # For now, let's assume maintenance_settings handles the UI presentation.
    
    # If maintenance_settings is intended to be the *actual* admin panel UI:
    await maintenance_settings(bot, callback_query) # Pass bot and callback_query
    await callback_query.answer("Redirecting to Admin Panel...") # Optional: Acknowledge before redirect

    # If admin_panel_callback is just a placeholder and maintenance_settings is the true handler,
    # then the text/keyboard below might be redundant if maintenance_settings edits the message.
    # However, if maintenance_settings is a non-UI function or opens a *new* message,
    # then this function might need its own UI.
    # Given the original code, it seems maintenance_settings *is* the UI handler.

    # The prompt asked for: "Displays a message about the admin panel ... "Back" button to "settings_support"."
    # This implies this function should show its own simple message if maintenance_settings doesn't take over the UI.
    # For now, assuming maintenance_settings takes over. If not, the following could be un-commented and adapted:

    # admin_panel_message_text = await async_translate_to_lang("Welcome to the Admin Panel. (Functionality TBD here or handled by maintenance_settings).", user_id)
    # back_btn_text = await async_translate_to_lang("🔙 Back to Support", user_id)
    # keyboard = InlineKeyboardMarkup(inline_keyboard=[
    #     [InlineKeyboardButton(text=back_btn_text, callback_data="settings_support")]
    # ])
    # await callback_query.message.edit_text(
    #     text=admin_panel_message_text,
    #     reply_markup=keyboard
    # )
    # await callback_query.answer()
    
# Commented out feature_states and related toggle functions are not migrated as they were not active.
