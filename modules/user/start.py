from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from modules.lang import async_translate_to_lang, batch_translate, format_with_mention
from modules.chatlogs import channel_log
import database.user_db as user_db

router = Router()

# Define button texts with emojis
button_list = [
    "➕ Add to Group",
    "🛠️ Commands",
    "❓ Help",
    "⚙️ Settings",
    "📞 Support"
]

welcome_text = """
✨ **Welcome {user_mention}!** ✨

🤖 **Advanced AI Bot **

I can help you with:

🧠 **Smart Chat** - Intelligent conversations with GPT-4o
🗣️ **Voice & Text** - Convert voice to text and back
🖼️ **Image Creation** - Generate stunning visuals from text
📝 **Text Extraction** - Analyze text from any image
🌐 **Multilingual** - Communicate in your language

━━━━━━━━━━━━━━━━━━━━━

👨‍💻 **Developed by [Chandan Singh](https://techycsr.me)**(**@techycsr**)

**Select a button below to get started!**
"""

@router.message(CommandStart())
async def start_handler(message: Message):
    user_mention = message.from_user.mention_html() if message.from_user else "User"
    text = welcome_text.format(user_mention=user_mention)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn, callback_data=btn.lower().replace(" ", "_"))] for btn in button_list
        ]
    )
    await message.answer(text, reply_markup=keyboard, disable_web_page_preview=True)

def register_start_handlers(dp):
    dp.include_router(router)

