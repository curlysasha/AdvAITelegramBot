from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import async_translate_to_lang
from modules.maintenance import maintenance_settings, is_admin_user
from config import ADMINS as admin_ids, OWNER_ID

router = Router()

support_text = """
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
"""

@router.callback_query(lambda c: c.data == "support")
async def settings_support_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    translated_support_text = await async_translate_to_lang(support_text, user_id)
    admins_btn = await async_translate_to_lang("👥 Contact Admin", user_id)
    developers_btn = await async_translate_to_lang("💻 Developer Info", user_id)
    community_btn = await async_translate_to_lang("🌐 Community", user_id)
    source_code_btn = await async_translate_to_lang("⌨️ Source Code", user_id)
    system_status_btn = await async_translate_to_lang("📊 System Status", user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    is_admin = await is_admin_user(user_id)
    admin_button_text = await async_translate_to_lang("⚙️ Admin Panel", user_id) if is_admin else admins_btn
    admin_button_callback = "admin_panel" if is_admin else "support_admins"
    admin_indicator = "\n\n🔑 **Admin Access Granted**" if is_admin else ""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=admin_button_text, callback_data=admin_button_callback),
             InlineKeyboardButton(text=developers_btn, callback_data="support_developers")],
            [InlineKeyboardButton(text=community_btn, url="https://t.me/AdvChatGpt"),
             InlineKeyboardButton(text=source_code_btn, url="https://github.com/TechyCSR/AdvAITelegramBot")],
            [InlineKeyboardButton(text=system_status_btn, callback_data="settings_others")],
            [InlineKeyboardButton(text=back_btn, callback_data="back")]
        ]
    )
    await callback.message.edit_text(
        text=translated_support_text + admin_indicator,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "support_admins")
async def support_admins_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    admin_contact_info = """
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
    """
    translated_admin_info = await async_translate_to_lang(admin_contact_info, user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    contact_btn = await async_translate_to_lang("💬 Message Developer", user_id)
    website_btn = await async_translate_to_lang("🌐 Visit Website", user_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=contact_btn, url="https://t.me/techycsr"),
             InlineKeyboardButton(text=website_btn, url="https://techycsr.me")],
            [InlineKeyboardButton(text=back_btn, callback_data="support")]
        ]
    )
    await callback.message.edit_text(
        text=translated_admin_info,
        reply_markup=keyboard,
        disable_web_page_preview=False
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await is_admin_user(user_id):
        alert_message = await async_translate_to_lang(
            "⚠️ Unauthorized access attempt. This action has been logged.",
            user_id
        )
        await callback.answer(alert_message, show_alert=True)
        return
    await maintenance_settings(callback.bot, callback)

# Developer info handled in dev_support.py

def register_support_handlers(dp: Router):
    dp.include_router(router)

