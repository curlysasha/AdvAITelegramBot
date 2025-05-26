from aiogram import types, F, Router, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup # For reply_markup in toggle

# Assuming these are or will be Aiogram-compatible
from modules.speech.voice_to_text import handle_voice_message as process_user_voice_message # Renamed for clarity
from modules.maintenance import maintenance_check, is_feature_enabled, maintenance_message 
from modules.core.database import db_service # For voice toggle db access

# Access user_voice_setting_collection for the toggle handler
user_voice_setting_collection = db_service.get_collection('user_voice_setting')

speech_router = Router()

# --- Voice Message Handler ---
@speech_router.message(F.voice)
async def voice_message_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    
    # Maintenance and feature checks (assuming these are Aiogram compatible)
    if await maintenance_check(user_id): # Needs to be async if it involves DB/API calls
        maint_msg_text = await maintenance_message(user_id) # Needs to be async
        await message.answer(maint_msg_text)
        return
    
    # Assuming is_feature_enabled takes (feature_name, user_id) and is async
    if not await is_feature_enabled("voice_features", user_id=user_id): 
        # Send a message if feature is disabled (optional, or rely on maintenance_message)
        # For now, let's assume maintenance_message covers this or it's handled elsewhere.
        # Or, provide a specific message:
        # feature_disabled_msg = await async_translate_to_lang("Voice features are currently disabled.", user_id)
        # await message.answer(feature_disabled_msg)
        # return
        # For this migration, if feature is off, we can just use maintenance_message or a generic one.
        maint_msg_text = await maintenance_message(user_id) # Or a specific "feature disabled" message
        await message.answer(maint_msg_text)
        return

    # bot_stats updates:
    # Accessing bot_stats directly like this might not work if it's not a global or passed object.
    # If bot_stats is part of dp.workflow_data:
    # dispatcher = Dispatcher.get_current()
    # if dispatcher and 'bot_stats' in dispatcher.workflow_data:
    #     dispatcher.workflow_data['bot_stats']["voice_messages_processed"] += 1
    #     dispatcher.workflow_data['bot_stats']["active_users"].add(user_id)
    # For now, commenting out direct bot_stats manipulation as its context isn't defined here.
    # logger.info(f"Processing voice message from user {user_id}")

    await process_user_voice_message(bot, message) # Call the adapted function

# --- Voice Preference Toggle Callback Handler ---
# This handler was originally named handle_voice_toggle in voice_to_text.py (Pyrogram)
# It was triggered by callback_data like "toggle_voice_{user_id}"
# The voice_to_text.py migration now creates buttons with "speech_toggle_voice_pref_{user_id}"
@speech_router.callback_query(F.data.startswith("speech_toggle_voice_pref_"))
async def toggle_voice_preference_callback(callback_query: types.CallbackQuery, bot: Bot):
    try:
        user_id_str = callback_query.data.split("_")[-1] # Get user_id from callback_data
        user_id = int(user_id_str)
    except (IndexError, ValueError):
        await callback_query.answer("Error: Could not parse user ID from callback.", show_alert=True)
        return

    # Ensure the user triggering the callback is the one whose preference is being changed
    if callback_query.from_user.id != user_id:
        await callback_query.answer("Error: You can only change your own preferences.", show_alert=True)
        return

    user_settings = user_voice_setting_collection.find_one({"user_id": user_id})
    current_setting = user_settings.get("voice", "voice") if user_settings and "voice" in user_settings else "voice"
    
    new_setting = "text" if current_setting == "voice" else "voice"
    
    user_voice_setting_collection.update_one(
        {"user_id": user_id},
        {"$set": {"voice": new_setting}},
        upsert=True
    )
    
    # Notify user of the change
    # Translation for "Changed to {setting} responses" would be ideal here.
    # For now, using English.
    setting_text_display = "Voice" if new_setting == "voice" else "Text"
    await callback_query.answer(f"Changed to {setting_text_display} responses")
    
    # Update the button text in the original message
    # The original message had a button like: "📝 Text Responses" or "🔊 Voice Responses"
    new_button_text = "📝 Text Responses" if new_setting == "voice" else "🔊 Voice Responses"
    
    # Reconstruct the keyboard or update the specific button
    # Assuming the original message had only one row with one button for this toggle
    if callback_query.message and callback_query.message.reply_markup:
        current_keyboard = callback_query.message.reply_markup.inline_keyboard
        updated_keyboard_rows = []
        button_updated = False
        for row in current_keyboard:
            new_row = []
            for button in row:
                if button.callback_data == callback_query.data: # Find the button that was pressed
                    new_row.append(InlineKeyboardButton(text=new_button_text, callback_data=callback_query.data))
                    button_updated = True
                else:
                    new_row.append(button) # Keep other buttons as they are
            updated_keyboard_rows.append(new_row)
        
        if button_updated:
            try:
                await callback_query.message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=updated_keyboard_rows)
                )
            except Exception as e:
                print(f"Error updating voice toggle button: {e}")
                # Could not edit, maybe message is too old or no change detected
        else:
            # If the button with the exact callback_data wasn't found (should not happen if logic is correct)
            print(f"Voice toggle button with data {callback_query.data} not found in markup.")
    else:
        # No reply_markup found to edit.
        print("No reply_markup to edit for voice toggle.")

# Placeholder for "new_voice_msg" if needed, from voice_to_text.py's commented out button
# @speech_router.callback_query(F.data.startswith("speech_new_voice_msg_"))
# async def new_voice_message_prompt_callback(callback_query: types.CallbackQuery, bot: Bot):
#     user_id = callback_query.from_user.id
#     # Logic to prompt user for a new voice message, e.g., send a message "Please send your new voice message."
#     await callback_query.message.answer("Recording a new voice message is not implemented via button yet. Just send a voice note.")
#     await callback_query.answer()
