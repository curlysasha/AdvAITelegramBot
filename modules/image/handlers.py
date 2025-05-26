from aiogram import types, F, Router, Bot
from aiogram.filters import ChatTypeFilter # For F.chat.type
from aiogram.enums import ChatType # For explicit chat types if needed

# Assuming these are or will be Aiogram-compatible
from modules.image.img_to_text import extract_text_from_image_and_respond
from modules.maintenance import maintenance_check, is_feature_enabled, maintenance_message
# from modules.chatlogs import channel_log # If needed for logging these specific events
# from config import bot_stats # Accessing bot_stats needs careful consideration of its scope

image_message_router = Router()

# --- Private Photo Message Handler ---
@image_message_router.message(F.photo, ChatTypeFilter(chat_type=[ChatType.PRIVATE]))
async def private_photo_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    # Maintenance and feature checks
    if await maintenance_check(user_id): # Assuming async
        maint_msg_text = await maintenance_message(user_id) # Assuming async
        await message.answer(maint_msg_text)
        return
    
    # Example of a specific feature check for image processing
    if not await is_feature_enabled("image_analysis", user_id=user_id): # Assuming async
        # Using maintenance_message as a generic "feature unavailable" message
        # Or create a specific one:
        # feature_disabled_msg = await async_translate_to_lang("Image analysis is currently disabled.", user_id)
        # await message.answer(feature_disabled_msg)
        maint_msg_text = await maintenance_message(user_id, feature_specific_key="image_analysis_disabled")
        await message.answer(maint_msg_text)
        return

    # bot_stats update (assuming bot_stats is accessible, e.g., via dp.workflow_data or passed in)
    # Commenting out for now as context is not defined here.
    # dispatcher = Dispatcher.get_current()
    # if dispatcher and 'bot_stats' in dispatcher.workflow_data:
    #     dispatcher.workflow_data['bot_stats']["active_users"].add(user_id)
    # logger.info(f"Processing private photo from user {user_id}")

    # Call the core image processing logic from img_to_text.py
    # This function now handles sending responses and further actions.
    await extract_text_from_image_and_respond(bot, message)
    
    # Logging the event (optional, if extract_text_from_image_and_respond doesn't cover it sufficiently)
    # if channel_log: await channel_log(bot, message, "PrivatePhotoReceived")


# --- Group Photo Message Handler ---
@image_message_router.message(F.photo, ChatTypeFilter(chat_type=[ChatType.GROUP, ChatType.SUPERGROUP]))
async def group_photo_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    # Maintenance and feature checks (similar to private chat)
    if await maintenance_check(user_id):
        maint_msg_text = await maintenance_message(user_id)
        await message.answer(maint_msg_text)
        return

    if not await is_feature_enabled("image_analysis_group", user_id=user_id): # Potentially a different feature flag for groups
        maint_msg_text = await maintenance_message(user_id, feature_specific_key="image_analysis_group_disabled")
        await message.answer(maint_msg_text)
        return

    # Caption check for AI trigger
    caption = message.caption if message.caption else ""
    caption_lower = caption.lower()
    
    # Require "ai" or "/ai" in caption for group image processing
    # This logic was originally in extract_text_res, now it's a prerequisite in the handler.
    if not ("ai" in caption_lower or "/ai" in caption_lower):
        # logger.info(f"Image in group {message.chat.id} ignored - caption lacks AI trigger: {caption}")
        return # Silently ignore if no trigger, or send a helper message if desired.

    # bot_stats update (similar considerations as above)
    # dispatcher = Dispatcher.get_current()
    # if dispatcher and 'bot_stats' in dispatcher.workflow_data:
    #     dispatcher.workflow_data['bot_stats']["active_users"].add(user_id)
    # logger.info(f"Processing group photo with AI trigger from user {user_id} in chat {message.chat.id}")
    
    # The caption_prompt passed to extract_text_from_image_and_respond might need to be cleaned
    # of the "ai" or "/ai" trigger if the function doesn't do it itself.
    # For now, passing the full message, assuming the function handles it or uses it as context.
    await extract_text_from_image_and_respond(bot, message)

    # Logging the event (optional)
    # if channel_log: await channel_log(bot, message, "GroupPhotoReceived_AITrigger")
