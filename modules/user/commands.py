from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Assuming these modules are or will be Aiogram-compatible
from modules.lang import async_translate_to_lang, batch_translate, translate_ui_element
# from modules.chatlogs import channel_log # Not used in this file
from config import ADMINS # For checking admin status
# import database.user_db as user_db # Not directly used in this file, but good to keep if sub-functions use it implicitly

commands_router = Router()

# --- Command Text Constants (remain the same) ---
command__text = """
**🤖 Bot Commands 🤖**

Select a feature below to see detailed commands and examples.

**@AdvChatGptBot**
"""

ai_commands_text = """
**🧠 AI Chat Commands**

**In Private Chats:**
- Simply type your message and I'll respond
- Send a voice message to get voice-to-text conversion
- Use `/new` or `/newchat` to start a fresh conversation

**In Group Chats:**
- Use `/ai [question]` to ask me directly
  Example: `/ai What's the weather like in Paris?`
- Reply to my messages to continue the conversation
- Use `/ask [question]` or `/say [question]` as alternatives

**Pro Tips:**
- I remember conversation context in private chats
- For coding questions, include language for better formatting
- Use `/new` to reset our conversation history

**@AdvChatGptBot**
"""

image_commands_text = """
**🖼️ Image Generation Commands**

**In Private Chats:**
- Use `/generate [prompt]` or `/img [prompt]` to create images
  Example: `/img a serene mountain landscape at sunset`
- Choose from multiple artistic styles after entering your prompt
- Use the regenerate button to try again with the same prompt

**In Group Chats:**
- Use the same commands as in private chats
- Everyone can view and react to generated images
- Only the person who requested can regenerate images

**Image Analysis:**
- Send any image to extract and analyze its text
- Add "ai" in caption with an image to analyze it in groups

**Pro Tips:**
- Be specific with details for better results
- Try different styles for varied outputs
- Include artistic references for specific aesthetics

**@AdvChatGptBot**
"""

main_commands_text = """
**📋 Main Commands**

**/start** - Start the bot and see the welcome message
**/help** - Show help information
**/settings** - Configure bot settings
**/rate** - Rate your experience with the bot

**@AdvChatGptBot**
"""

admin_commands_text = """
**⚙️ Admin Commands**

These commands are restricted to bot administrators only.

**/restart** - Restart the bot (requires confirmation)
**/stats** - View bot statistics and usage data 
**/logs** - Get the most recent log entries
**/announce** - Send a message to all users
**/gleave** - Leave a group chat
**/invite** - Add the bot to a group
**/uinfo** - Get information about users

**Note:** These commands are only available to authorized administrators listed in the configuration.

**@AdvChatGptBot**
"""
# --- End of Command Text Constants ---

@commands_router.callback_query(F.data == "commands")
async def commands_menu_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    
    texts_to_translate = [command__text, "🧠 AI Response", "🖼️ Image Generation", "📋 Main Commands", "🔙 Back"]
    # Assuming batch_translate is compatible
    translated_texts = await batch_translate(texts_to_translate, user_id)
    
    translated_command_text = translated_texts[0]
    ai_btn_text = translated_texts[1]
    img_btn_text = translated_texts[2]
    main_btn_text = translated_texts[3]
    back_btn_text = translated_texts[4]
    
    keyboard_buttons = [
        [InlineKeyboardButton(text=ai_btn_text, callback_data="cmd_ai")],
        [InlineKeyboardButton(text=img_btn_text, callback_data="cmd_img")],
        [InlineKeyboardButton(text=main_btn_text, callback_data="cmd_main")]
    ]
    
    if user_id in ADMINS:
        # Assuming translate_ui_element is compatible
        admin_btn_text = await translate_ui_element("⚙️ Admin Commands", user_id) 
        keyboard_buttons.append([InlineKeyboardButton(text=admin_btn_text, callback_data="cmd_admin")])
    
    keyboard_buttons.append([InlineKeyboardButton(text=back_btn_text, callback_data="main_menu")]) # Back to main menu
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback_query.message.edit_text(
        text=translated_command_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer()

@commands_router.callback_query(F.data.startswith("cmd_"))
async def command_category_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    text_map = {
        "cmd_ai": ai_commands_text,
        "cmd_img": image_commands_text,
        "cmd_main": main_commands_text,
        "cmd_admin": admin_commands_text,
    }

    if data == "cmd_admin" and user_id not in ADMINS:
        await callback_query.answer("You don't have permission to view admin commands.", show_alert=True)
        return

    command_text_to_translate = text_map.get(data)
    
    if not command_text_to_translate:
        await callback_query.answer("Unknown command category.", show_alert=True)
        return

    # Assuming async_translate_to_lang and translate_ui_element are compatible
    translated_text = await async_translate_to_lang(command_text_to_translate, user_id)
    back_btn_text = await translate_ui_element("🔙 Back to Commands", user_id)
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_btn_text, callback_data="commands")] # Back to main commands menu
    ])
        
    await callback_query.message.edit_text(
        text=translated_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    await callback_query.answer()
