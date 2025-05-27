from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from modules.lang import async_translate_to_lang
from config import OWNER_ID

router = Router()

developer_ids = {
    "CSR": OWNER_ID,
    "Ankit": 987654321,
    "Aarushi": 192837465,
}

@router.callback_query(lambda c: c.data == "support_developers")
async def support_developers_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    developer_info = """
🧑‍💻 **Meet the Developer**

**Chandan Singh** (@techycsr)
Tech Enthusiast & Student Developer

• **Portfolio:** [techycsr.me](https://techycsr.me)
• **GitHub:** [TechyCSR](https://github.com/TechyCSR)
• **Email:** csr.info.in@gmail.com
• **Specializations:** Python, AI/ML, Telegram Bots, Web Development

**About Me:**
I'm a tech enthusiast with a strong passion for Python, AI/ML, and open-source development. I specialize in building Telegram bots using Pyrogram and MongoDB, developing AI-powered applications, and managing web development projects.

**Project Details:**
• This advanced AI Telegram bot integrates multiple AI services
• Built with Python, Pyrogram, and MongoDB
• Includes image generation, voice processing, and AI chat capabilities

**Support the Development:**
Consider donating to help maintain and improve this bot.
"""
    translated_dev_info = await async_translate_to_lang(developer_info, user_id)
    back_btn = await async_translate_to_lang("🔙 Back", user_id)
    github_btn = await async_translate_to_lang("📁 GitHub", user_id)
    contact_btn = await async_translate_to_lang("💬 Contact", user_id)
    portfolio_btn = await async_translate_to_lang("🌐 Portfolio", user_id)
    donate_btn = await async_translate_to_lang("💰 Support Development", user_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=portfolio_btn, url="https://techycsr.me"),
             InlineKeyboardButton(text=github_btn, url="https://github.com/TechyCSR/AdvAITelegramBot")],
            [InlineKeyboardButton(text=contact_btn, url="https://t.me/techycsr"),
             InlineKeyboardButton(text=donate_btn, callback_data="support_donate")],
            [InlineKeyboardButton(text=back_btn, callback_data="support")]
        ]
    )
    await callback.message.edit_text(
        text=translated_dev_info,
        reply_markup=keyboard,
        disable_web_page_preview=False
    )
    await callback.answer()

def register_dev_support_handlers(dp: Router):
    dp.include_router(router)
