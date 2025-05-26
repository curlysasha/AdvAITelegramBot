from aiogram import types, F, Router, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Assuming these modules are or will be Aiogram-compatible
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element 
from modules.chatlogs import channel_log
# import database.user_db as user_db # Not directly used in this file, but good to keep if sub-functions use it implicitly

help_router = Router()

# --- Help Text Constants (remain the same) ---
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
• `/start` - Main menu (or use "main_menu" callback)
• `/help` - This help center
• `/settings` - Configure bot preferences
• `/new` - Clear conversation history

**HAVING TROUBLE?**
• Select the Support button from main menu
• Try more specific prompts for better results
"""
# --- End of Help Text Constants ---

@help_router.message(Command("help"))
async def help_command(message: types.Message, bot: Bot): # Added bot: Bot
    user_id = message.from_user.id
    
    texts_to_translate = [
        help_text, 
        "🧠 AI Chat", 
        "🖼️ Image Generation", 
        "🎙️ Voice Features",
        "🔍 Image Analysis",
        "🚀 Quick Start",
        "📋 Commands"
    ]
    
    # Assuming batch_translate is compatible or will be adapted
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    translated_help_text = translated_texts[0]
    ai_btn_text = translated_texts[1]
    img_btn_text = translated_texts[2]
    voice_btn_text = translated_texts[3]
    analysis_btn_text = translated_texts[4]
    quickstart_btn_text = translated_texts[5]
    cmd_btn_text = translated_texts[6]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ai_btn_text, callback_data="help_ai")],
        [InlineKeyboardButton(text=img_btn_text, callback_data="help_img")],
        [InlineKeyboardButton(text=voice_btn_text, callback_data="help_voice")],
        [InlineKeyboardButton(text=analysis_btn_text, callback_data="help_analysis")],
        [InlineKeyboardButton(text=quickstart_btn_text, callback_data="help_quickstart")],
        [InlineKeyboardButton(text=cmd_btn_text, callback_data="commands")] # Assuming "commands" callback exists elsewhere
    ])
    
    await message.answer(
        text=translated_help_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    # Assuming channel_log is compatible or will be adapted
    await channel_log(bot, message, "/help")


@help_router.callback_query(F.data == "help")
async def help_menu_callback(callback_query: types.CallbackQuery, bot: Bot): # Added bot: Bot
    user_id = callback_query.from_user.id
    
    texts_to_translate = [
        help_text, 
        "🧠 AI Chat", 
        "🖼️ Image Generation", 
        "🎙️ Voice Features",
        "🔍 Image Analysis",
        "🚀 Quick Start",
        "📋 Commands",
        "🔙 Back" # Standard back button text
    ]
    
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    translated_help_text = translated_texts[0]
    ai_btn_text = translated_texts[1]
    img_btn_text = translated_texts[2]
    voice_btn_text = translated_texts[3]
    analysis_btn_text = translated_texts[4]
    quickstart_btn_text = translated_texts[5]
    cmd_btn_text = translated_texts[6]
    back_btn_text = translated_texts[7]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ai_btn_text, callback_data="help_ai")],
        [InlineKeyboardButton(text=img_btn_text, callback_data="help_img")],
        [InlineKeyboardButton(text=voice_btn_text, callback_data="help_voice")],
        [InlineKeyboardButton(text=analysis_btn_text, callback_data="help_analysis")],
        [InlineKeyboardButton(text=quickstart_btn_text, callback_data="help_quickstart")],
        [InlineKeyboardButton(text=cmd_btn_text, callback_data="commands")], # Assuming "commands" callback
        [InlineKeyboardButton(text=back_btn_text, callback_data="main_menu")] # Callback to main menu (from start.py)
    ])

    await callback_query.message.edit_text(
        text=translated_help_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer()

    
@help_router.callback_query(F.data.startswith("help_"))
async def help_category_callback(callback_query: types.CallbackQuery, bot: Bot): # Added bot: Bot
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    content_map = {
        "help_ai": ai_chat_help,
        "help_img": image_gen_help,
        "help_voice": voice_features_help,
        "help_analysis": image_analysis_help,
        "help_quickstart": quick_start_help,
    }
    
    help_content_to_translate = content_map.get(data, help_text) # Default to main help_text if not found
    
    # Assuming async_translate_to_lang and translate_ui_element are compatible
    translated_text = await async_translate_to_lang(help_content_to_translate, user_id)
    back_btn_text = await translate_ui_element("🔙 Back to Help Menu", user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_btn_text, callback_data="help")] # Callback to main help menu
    ])
    
    await callback_query.message.edit_text(
        text=translated_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer()
