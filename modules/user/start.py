from aiogram import types, F, Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
# Message, CallbackQuery are part of types

from modules.lang import async_translate_to_lang, batch_translate, format_with_mention # Assuming these are compatible or will be adapted
from modules.chatlogs import channel_log # Assuming this is compatible or will be adapted
import database.user_db as user_db # Assuming this is compatible or will be adapted

# Router for start command and related callbacks
start_router = Router()

# Define button texts with emojis (remains the same)
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

tip_text = "💡 **Pro Tip:** Type any message to start chatting with me,OR\nuse /img with your prompt to generate images!\n**For more commands use /help.**"

LOGO = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdnp4MnR0YXk3ZGNjenR6NGRoaDNkc2h2NDgxa285NnExaGM1MTZmYyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/S60CrN9iMxFlyp7uM8/giphy.gif"

@start_router.message(CommandStart())
async def start_command(message: types.Message, bot: Bot):
    await user_db.check_and_add_user(message.from_user.id)
    if message.from_user.username:
        await user_db.check_and_add_username(message.from_user.id, message.from_user.username)

    # Get user info
    user_id = message.from_user.id
    # Use mention_html() for Aiogram, assuming format_with_mention can handle HTML
    mention = message.from_user.mention_html() 
    
    # First safely format the welcome text with mention preservation
    user_lang = user_db.get_user_language(user_id)
    # Assuming format_with_mention signature: (text, mention_html, user_id, lang_code)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    
    # Translate other texts
    # Assuming batch_translate signature: (list_of_texts, user_id)
    translated_texts = await batch_translate([tip_text] + button_list, user_id)
    translated_tip = translated_texts[0]
    translated_buttons = translated_texts[1:]

    bot_username = (await bot.get_me()).username
    # Create the inline keyboard buttons with translated text
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=translated_buttons[0], url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton(text=translated_buttons[1], callback_data="commands"),
         InlineKeyboardButton(text=translated_buttons[2], callback_data="help")],
        [InlineKeyboardButton(text=translated_buttons[3], callback_data="settings"),
         InlineKeyboardButton(text=translated_buttons[4], callback_data="support")]
    ])

    # Send the welcome message with the GIF and the keyboard
    await bot.send_animation(
        chat_id=message.chat.id,
        animation=LOGO,
        caption=translated_welcome,
        reply_markup=keyboard
    )
    await message.answer(translated_tip) # Use message.answer for replying

    # Assuming channel_log signature: (bot_instance, update_like_object, text_log)
    await channel_log(bot, message, "/start")

@start_router.callback_query(F.data == "main_menu") # Placeholder callback_data
async def start_menu_callback(callback_query: types.CallbackQuery, bot: Bot):
    user_id = callback_query.from_user.id
    # Use mention_html() for Aiogram, assuming format_with_mention can handle HTML
    mention = callback_query.from_user.mention_html() 

    # First safely format the welcome text with mention preservation
    user_lang = user_db.get_user_language(user_id)
    translated_welcome = await format_with_mention(welcome_text.replace("{user_mention}", "{mention}"), mention, user_id, user_lang)
    
    # Translate button texts
    translated_buttons = await batch_translate(button_list, user_id)

    bot_username = (await bot.get_me()).username
    # Create the inline keyboard buttons with translated text
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=translated_buttons[0], url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton(text=translated_buttons[1], callback_data="commands"),
         InlineKeyboardButton(text=translated_buttons[2], callback_data="help")],
        [InlineKeyboardButton(text=translated_buttons[3], callback_data="settings"),
         InlineKeyboardButton(text=translated_buttons[4], callback_data="support")]
    ])

    # Edit the message caption
    if callback_query.message and callback_query.message.caption: # Can only edit caption if original message had media/caption
        try:
            await callback_query.message.edit_caption(
                caption=translated_welcome,
                reply_markup=keyboard
            )
        except Exception as e: # Fallback if edit_caption fails (e.g. not a media message)
            # Check if the message is a text message
            if callback_query.message.text:
                 await callback_query.message.edit_text(
                    text=translated_welcome, # If GIF fails, send as text
                    reply_markup=keyboard
                )
            else: # If it's neither caption nor text, send a new message
                await callback_query.message.answer( # Use .answer on message
                    animation=LOGO, # Send as a new message with GIF
                    caption=translated_welcome,
                    reply_markup=keyboard
                )
    elif callback_query.message and callback_query.message.text: # If it's a text message originally
         await callback_query.message.edit_text(
            text=translated_welcome, 
            reply_markup=keyboard
        )
    else: # Fallback: send as new message
        await callback_query.message.answer(
            animation=LOGO, 
            caption=translated_welcome,
            reply_markup=keyboard
        )

    await callback_query.answer() # Acknowledge the callback
