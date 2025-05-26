from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Assuming these modules are or will be Aiogram-compatible
from modules.lang import async_translate_to_lang
from config import OWNER_ID # Used in developer_ids

dev_support_router = Router()

# Developer user IDs (remains the same, though not directly used in the handler below)
developer_ids = {
    "CSR": OWNER_ID,      
    "Ankit": 987654321,    
    "Aarushi": 192837465,  
}

developer_info_template = """
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
• Built with Python, Pyrogram, and MongoDB (Note: Pyrogram will be Aiogram after migration)
• Includes image generation, voice processing, and AI chat capabilities

**Support the Development:**
Consider donating to help maintain and improve this bot.
""" # Renamed for clarity

@dev_support_router.callback_query(F.data == "support_developers")
async def developer_info_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    
    # Update project details text to reflect Aiogram
    updated_developer_info = developer_info_template.replace(
        "Built with Python, Pyrogram, and MongoDB",
        "Built with Python, Aiogram, and MongoDB" 
    )

    translated_dev_info = await async_translate_to_lang(updated_developer_info, user_id)
    
    # Translate button labels
    back_btn_text = await async_translate_to_lang("🔙 Back", user_id)
    github_btn_text = await async_translate_to_lang("📁 GitHub", user_id)
    contact_btn_text = await async_translate_to_lang("💬 Contact", user_id)
    portfolio_btn_text = await async_translate_to_lang("🌐 Portfolio", user_id)
    # Assuming "support_donate" callback is handled elsewhere, or it's a placeholder for a URL/action
    donate_btn_text = await async_translate_to_lang("💰 Support Development", user_id) 
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=portfolio_btn_text, url="https://techycsr.me"),
            InlineKeyboardButton(text=github_btn_text, url="https://github.com/TechyCSR/AdvAITelegramBot")
        ],
        [
            InlineKeyboardButton(text=contact_btn_text, url="https://t.me/techycsr"),
            InlineKeyboardButton(text=donate_btn_text, callback_data="support_donate") # Assuming this callback exists
        ],
        [
            InlineKeyboardButton(text=back_btn_text, callback_data="settings_support") # Back to main support menu
        ]
    ])
    
    await callback_query.message.edit_text(
        text=translated_dev_info,
        reply_markup=keyboard,
        disable_web_page_preview=False, # To show website card
        parse_mode="Markdown" # Text contains markdown links
    )
    await callback_query.answer()
