from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
from modules.chatlogs import channel_log


router = Router()

help_text = """
✨ **ADVANCED AI BOT - HELP CENTER** ✨

━━━━━━━━━━━━━━━━━━━

This intelligent bot was created by **Chandan Singh** (@techycsr) 
to bring powerful AI features directly to your Telegram chats.

**SELECT A CATEGORY BELOW:**
"""

ai_chat_help = """
🧠 **AI CHAT ASSISTANT** 🧠

━━━━━━━━━━━━━━━━━━━

The bot uses **GPT-4o** to provide intelligent responses to any question.

**KEY FEATURES:**
• 💬 **Context-aware** - Remembers conversation history
• 🧩 **Complex questions** - Detailed, thoughtful answers
• 💻 **Code generation** - With syntax highlighting
• 🔢 **Math solver** - Works with equations & problems
• 🌎 **Translation** - Works in multiple languages

**COMMANDS:**
• 💬 In private chats: Just type your message
• 🔄 In groups: Use `/ai`, `/ask`, or `/say` + question
• 🆕 Reset chat: Use `/new` or `/newchat`

**EXAMPLE:** 
`/ai What makes quantum computing different from classical computing?`

**💡 PRO TIP:** For code questions, mention the programming language for better formatting.
"""

image_gen_help = """
🖼️ **IMAGE GENERATION** 🖼️

━━━━━━━━━━━━━━━━━━━

Create stunning images from text descriptions using advanced AI.

**KEY FEATURES:**
• 🎨 **High-quality images** - Detailed & realistic
• 🏞️ **Multiple styles** - Realistic, Artistic, Sketch, 3D
• 🔄 **Regeneration** - One-click retry with same prompt
• 👥 **Works everywhere** - Private chats & groups

**COMMANDS:**
• 📝 `/generate [prompt]` - Full command
• 📸 `/img [prompt]` - Shorter alternative
• 🖌️ `/gen [prompt]` - Shortest version

**EXAMPLE:**
`/img a cyberpunk city at night with neon lights and flying cars`

**💡 PRO TIPS:**
• Be specific about details, lighting, and perspective
• Include artistic references for better results
• Try different styles for varied outputs
"""

voice_features_help = """
🎙️ **VOICE FEATURES** 🎙️

━━━━━━━━━━━━━━━━━━━

Convert between voice and text with advanced speech processing.

**KEY FEATURES:**
• 🗣️ **Voice-to-text** - Transcribe voice messages
• 🔊 **Text-to-voice** - Listen to bot responses
• 🌐 **Multilingual** - Works in multiple languages
• 💬 **Conversation** - Ask questions by voice

**HOW TO USE:**
1. 🎤 Send a voice message
2. 📝 Bot converts to text & understands
3. 💬 Bot responds to your question
4. ⚙️ Adjust voice settings in Settings menu

**💡 PRO TIPS:**
• Speak clearly in a quiet environment
• Keep messages under 1 minute for best results
• Set your preferred voice language in settings
"""

image_analysis_help = """
🔍 **IMAGE ANALYSIS** 🔍

━━━━━━━━━━━━━━━━━━━

Extract and analyze text from any image with smart OCR technology.

**KEY FEATURES:**
• 📱 **Text extraction** - From photos & screenshots
• 📄 **Document scanning** - Read printed documents
• ❓ **Follow-up questions** - Ask about extracted text
• 📊 **Data recognition** - Tables, receipts & more

**HOW TO USE:**
1. 📷 Send any image with text
2. 🔍 Bot extracts all readable text
3. 💬 Ask follow-up questions about the content
4. 📱 In groups, add "ai" in image caption

**💡 PRO TIPS:**
• Use good lighting for clearer results
• Capture text straight-on, not at angles
• Crop to focus on the important text
"""

quick_start_help = """
🚀 **QUICK START GUIDE** 🚀

━━━━━━━━━━━━━━━━━━━

**GET STARTED IN 3 STEPS:**

1️⃣ **Chat with AI**
   • Private: Just type any message
   • Groups: Use `/ai` command

2️⃣ **Generate Images**
   • Use `/img` followed by description
   • Example: `/img sunset over mountains`

3️⃣ **Analyze Images**
   • Send any image with text
   • Bot will extract and analyze

**USEFUL COMMANDS:**
• `/start` - Main menu
• `/help` - This help center
• `/settings` - Configure bot preferences
• `/new` - Clear conversation history

**HAVING TROUBLE?**
• Select the Support button from main menu
• Try more specific prompts for better results
"""


@router.message(Command("help"))
async def help_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="AI Chat", callback_data="help_ai")],
            [InlineKeyboardButton(text="Image Generation", callback_data="help_img")],
            [InlineKeyboardButton(text="Voice Features", callback_data="help_voice")],
            [InlineKeyboardButton(text="Image Analysis", callback_data="help_analysis")],
            [InlineKeyboardButton(text="Quick Start", callback_data="help_quickstart")],
            [InlineKeyboardButton(text="Commands", callback_data="commands")]
        ]
    )
    await message.answer(help_text, reply_markup=keyboard, disable_web_page_preview=True)

@router.callback_query(lambda c: c.data == "help_ai")
async def help_ai_callback(callback: CallbackQuery):
    await callback.message.edit_text(ai_chat_help, reply_markup=help_menu_keyboard(), disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(lambda c: c.data == "help_img")
async def help_img_callback(callback: CallbackQuery):
    await callback.message.edit_text(image_gen_help, reply_markup=help_menu_keyboard(), disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(lambda c: c.data == "help_voice")
async def help_voice_callback(callback: CallbackQuery):
    await callback.message.edit_text(voice_features_help, reply_markup=help_menu_keyboard(), disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(lambda c: c.data == "help_analysis")
async def help_analysis_callback(callback: CallbackQuery):
    await callback.message.edit_text(image_analysis_help, reply_markup=help_menu_keyboard(), disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(lambda c: c.data == "help_quickstart")
async def help_quickstart_callback(callback: CallbackQuery):
    await callback.message.edit_text(quick_start_help, reply_markup=help_menu_keyboard(), disable_web_page_preview=True)
    await callback.answer()

# Helper to generate the help menu keyboard for navigation

def help_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="AI Chat", callback_data="help_ai")],
            [InlineKeyboardButton(text="Image Generation", callback_data="help_img")],
            [InlineKeyboardButton(text="Voice Features", callback_data="help_voice")],
            [InlineKeyboardButton(text="Image Analysis", callback_data="help_analysis")],
            [InlineKeyboardButton(text="Quick Start", callback_data="help_quickstart")],
            [InlineKeyboardButton(text="Commands", callback_data="commands")]
        ]
    )

def register_help_handlers(dp):
    dp.include_router(router)

