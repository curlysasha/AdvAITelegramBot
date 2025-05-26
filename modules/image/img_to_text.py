import os
import requests # For OCR API
import json
import asyncio
import tempfile
import logging

from aiogram import types, F, Router, Bot
from aiogram.enums import ChatAction
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import OCR_KEY, DATABASE_URL, LOG_CHANNEL # Assuming LOG_CHANNEL is int/str chat_id
from pymongo import MongoClient

# Assuming these are or will be Aiogram-compatible
from modules.models.ai_res import get_response #, get_streaming_response # get_streaming_response not used here
from modules.chatlogs import user_log, error_log # error_log was not explicitly used but good for future

logger = logging.getLogger(__name__)
img_to_text_router = Router()

# MongoDB Client (Consider centralizing DB client initialization)
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
history_collection = db['history']

# OCR using OCR.space API (largely unchanged, as it uses 'requests')
async def ocr_space_extract(image_path: str, ocr_key: str = OCR_KEY, language: str = "eng") -> tuple[str | None, str | None]:
    """
    Extract text from an image using OCR.space API.
    Args:
        image_path: Path to the image file.
        ocr_key: OCR.space API key.
        language: Language code for OCR.
    Returns:
        Tuple of (extracted_text, error_message).
    """
    if not ocr_key or ocr_key == "OCR_KEY": # Check if placeholder OCR_KEY is used
        logger.warning("OCR_KEY is not configured. Skipping OCR.")
        return None, "OCR service is not configured by the bot admin."
    try:
        logger.info(f"Attempting OCR on image: {image_path} with language: {language}")
        
        url = "https://api.ocr.space/parse/image"
        payload = {"isOverlayRequired": False, "language": language, "detectOrientation": True}
        headers = {"apikey": ocr_key}

        def _ocr_request_sync():
            with open(image_path, "rb") as image_f:
                files_data = {"image": image_f}
                # The requests.post call is blocking
                return requests.post(url, headers=headers, data=payload, files=files_data, timeout=30)

        logger.info("Sending request to OCR API (via asyncio.to_thread)")
        response = await asyncio.to_thread(_ocr_request_sync)
        
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        response_data = response.json() # This is fine as response object is already available
        logger.info(f"OCR API response status: {response.status_code}")
        
        if not response_data.get("IsErroredOnProcessing") and response_data.get("ParsedResults"):
            extracted_text = response_data["ParsedResults"][0]["ParsedText"].strip()
            if not extracted_text: # Handle cases where OCR result is empty
                 logger.warning(f"OCR successful but no text detected for {image_path}")
                 return None, "No text could be detected in the image."
            logger.info(f"Text successfully extracted, length: {len(extracted_text)}")
            return extracted_text, None
        else:
            error_message = response_data.get("ErrorMessage", ["Unknown OCR error"])[0] # ErrorMessage can be a list
            logger.error(f"OCR API Error: {error_message}")
            # Provide more user-friendly messages for common errors
            if "Filetypecouldnotbeautodetected" in error_message:
                 return None, "The image format is not supported by the OCR service."
            if "sizeexceedsthelimit" in error_message.lower():
                 return None, "The image file is too large for the OCR service."
            return None, "The OCR service could not process the image. Please try a different image."
            
    except requests.exceptions.Timeout:
        logger.error("OCR API request timed out")
        return None, "The OCR service is taking too long. Please try again later."
    except requests.exceptions.RequestException as e: # Catch other request-related errors
        logger.error(f"OCR API request error: {e}")
        return None, "Could not connect to the OCR service. Check your internet or try later."
    except Exception as e:
        logger.exception(f"Exception during OCR API processing: {e}")
        return None, "An unexpected error occurred while processing the image."

# This function is now a utility called by handlers in handlers.py
async def extract_text_from_image_and_respond(bot: Bot, message: types.Message):
    """
    Core logic to extract text from an image and generate an AI response.
    Called by message handlers for photos.
    """
    user_id = message.from_user.id
    processing_msg = None # Initialize to None

    try:
        # Determine if caption contains AI trigger for group chats (logic moved to handler)
        # Here, we assume this function is called *after* such checks.
        
        processing_msg = await message.answer(
            "🔍 **Processing Image**\n\nExtracting and analyzing text content...\nThis may take a moment.",
            parse_mode="Markdown"
        )
        
        caption_prompt = message.caption if message.caption else ""
        # If called from group handler, caption_prompt might already be processed (e.g., trigger removed)
        
        photo_file_id = message.photo[-1].file_id # Get largest photo

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path_on_disk = os.path.join(temp_dir, f"image_{user_id}_{message.message_id}.jpg")
            
            logger.info(f"Downloading image to {file_path_on_disk}")
            try:
                file_info = await bot.get_file(photo_file_id)
                await bot.download_file(file_path=file_info.file_path, destination=file_path_on_disk)
                logger.info(f"Image downloaded to {file_path_on_disk}")
            except Exception as e:
                logger.exception(f"Error downloading image: {e}")
                await processing_msg.edit_text(f"❌ **Download Failed**\n\nCould not download the image: {str(e)}")
                return
            
            await processing_msg.edit_text(
                "🔍 **Processing Image**\n\nExtracting text... (This might take up to 30 seconds)",
                parse_mode="Markdown"
            )
            
            extracted_text, error = await ocr_space_extract(file_path_on_disk)
            
            if error:
                await processing_msg.edit_text(
                    f"❌ **Text Extraction Failed**\n\n{error}\n\n"
                    "Try these alternatives:\n"
                    "• Send a clearer image with better lighting\n"
                    "• Ensure text is well-focused and not blurry\n"
                    "• Type the text manually with your question\n"
                    "• Try again in a few minutes",
                    parse_mode="Markdown"
                )
                if LOG_CHANNEL:
                    try:
                        await bot.send_photo(chat_id=int(LOG_CHANNEL), photo=types.FSInputFile(file_path_on_disk), caption=f"#OCRFailed\nUser: {message.from_user.mention_html()}\nError: {error}", parse_mode="HTML")
                    except Exception as log_e: logger.error(f"Error sending OCR failure log: {log_e}")
                return
            
            if not extracted_text: # Handles case where OCR is successful but no text found
                await processing_msg.edit_text(
                    "⚠️ **No Text Detected**\n\n"
                    "I couldn't find any readable text in this image.\n"
                    "Please try with a clearer image or one containing visible text.",
                    parse_mode="Markdown"
                )
                if LOG_CHANNEL:
                    try:
                        await bot.send_photo(chat_id=int(LOG_CHANNEL), photo=types.FSInputFile(file_path_on_disk), caption=f"#NoTextDetected\nUser: {message.from_user.mention_html()}", parse_mode="HTML")
                    except Exception as log_e: logger.error(f"Error sending no text log: {log_e}")
                return

            full_prompt_for_ai = extracted_text
            if caption_prompt: # Append caption if it exists (handler should ensure it's relevant)
                full_prompt_for_ai = f"{extracted_text}\n\n[User's question/context from caption: {caption_prompt}]"
            
            await processing_msg.edit_text(
                "✅ **Text Extracted**\n\nGenerating AI response based on the image content...",
                parse_mode="Markdown"
            )

            def _get_history_sync():
                return history_collection.find_one({"user_id": user_id})
            user_history_doc = await asyncio.to_thread(_get_history_sync)

            history = user_history_doc['history'] if user_history_doc and 'history' in user_history_doc else [{
                "role": "assistant", 
                "content": "I'm your advanced AI assistant. I can help analyze text from images."
            }]
            history.append({"role": "user", "content": full_prompt_for_ai})
                
            await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
                
            # Assuming get_response from ai_res.py already wrapped its g4f call if it was blocking
            ai_response = await get_response(history) 
            if not ai_response:
                ai_response = "I analyzed the text but couldn't generate a specific response. Is there anything particular you'd like to know?"

            await processing_msg.edit_text(
                f"📝 **Image Text Analysis**\n\n{ai_response}",
                parse_mode="Markdown" # Assuming AI response might have markdown
            )
                
            action_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Show Extracted Text", callback_data=f"imgtxt_show_{message.message_id}")], # message_id as unique part
                [InlineKeyboardButton(text="❓ Ask Follow-up", callback_data=f"imgtxt_followup_{message.message_id}")]
            ])
                
            await message.answer( # Use message.answer to send a new message for actions
                "**Need anything else with this image?**",
                reply_markup=action_markup,
                parse_mode="Markdown"
            )
                
            history.append({"role": "assistant", "content": ai_response})
            
            def _update_history_sync():
                history_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"history": history, f"last_extracted_text_{message.message_id}": extracted_text}}, # Store text with message_id
                    upsert=True
                )
            await asyncio.to_thread(_update_history_sync)

            if LOG_CHANNEL:
                try:
                    await bot.send_photo(chat_id=int(LOG_CHANNEL), photo=types.FSInputFile(file_path_on_disk), caption=f"#ImageProcessed\nUser: {message.from_user.mention_html()}\nExtracted (first 100char): {extracted_text[:100]}...\nAI Response (first 100char): {ai_response[:100]}...", parse_mode="HTML")
                except Exception as log_e: logger.error(f"Error logging processed image: {log_e}")
                
    except Exception as e:
        logger.exception(f"Error in extract_text_from_image_and_respond: {e}")
        if processing_msg:
            await processing_msg.edit_text(f"An error occurred during image analysis: {str(e)}")
        else:
            await message.answer(f"An error occurred during image analysis: {str(e)}")
        await error_log(bot, "ImgToTextError", str(e), user_id)


@img_to_text_router.callback_query(F.data.startswith("imgtxt_show_"))
async def show_extracted_text_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    try:
        original_message_id_str = callback_query.data.split("_")[-1]
        user_id = callback_query.from_user.id # User who clicked the button

        def _get_user_data_sync():
            return history_collection.find_one({"user_id": user_id})
        user_data = await asyncio.to_thread(_get_user_data_sync)
        
        # Retrieve text using the message_id stored in callback_data
        extracted_text_key = f"last_extracted_text_{original_message_id_str}"
        
        if user_data and extracted_text_key in user_data:
            extracted_text = user_data[extracted_text_key]
            
            await callback_query.answer("Showing extracted text")
            # Edit the message that contained the buttons
            await callback_query.message.edit_text(
                f"📋 **Extracted Text** (from image in message ID {original_message_id_str})\n\n```\n{extracted_text}\n```\n\n"
                "This is the raw text that was extracted from the image.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Back to Actions", callback_data=f"imgtxt_back_actions_{original_message_id_str}")]
                ]),
                parse_mode="Markdown"
            )
        else:
            await callback_query.answer("Extracted text no longer available or not found for this message.", show_alert=True)
    except Exception as e:
        logger.exception(f"Error in show_extracted_text_callback: {e}")
        await callback_query.answer("An error occurred.", show_alert=True)

@img_to_text_router.callback_query(F.data.startswith("imgtxt_followup_"))
async def followup_question_prompt_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    try:
        original_message_id_str = callback_query.data.split("_")[-1]
        await callback_query.answer("Please send your follow-up question regarding the image.", show_alert=True)
        # Edit the message with buttons to prompt for text input
        await callback_query.message.edit_text(
            f"❓ **Ask a Follow-up Question** (regarding image in message ID {original_message_id_str})\n\n"
            "Please type your question about the image or the extracted text. Your next message will be considered as follow-up.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[ # Provide a way to cancel or go back
                 [InlineKeyboardButton(text="◀️ Back to Actions", callback_data=f"imgtxt_back_actions_{original_message_id_str}")]
            ]),
            parse_mode="Markdown"
        )
        # Here, you might want to set a state for the user to capture their next message as a follow-up
        # e.g., using Aiogram's FSMContext. For now, it's just a prompt.
    except Exception as e:
        logger.exception(f"Error in followup_question_prompt_callback: {e}")
        await callback_query.answer("An error occurred.", show_alert=True)

@img_to_text_router.callback_query(F.data.startswith("imgtxt_back_actions_"))
async def back_to_image_actions_callback(callback_query: types.CallbackQuery, bot: Bot): # bot: Bot might not be needed
    try:
        original_message_id_str = callback_query.data.split("_")[-1]
        
        action_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Show Extracted Text", callback_data=f"imgtxt_show_{original_message_id_str}")],
            [InlineKeyboardButton(text="❓ Ask Follow-up", callback_data=f"imgtxt_followup_{original_message_id_str}")]
        ])
        await callback_query.message.edit_text(
            f"**Need anything else with this image?** (Actions for image in message ID {original_message_id_str})",
            reply_markup=action_markup,
            parse_mode="Markdown"
        )
        await callback_query.answer()
    except Exception as e:
        logger.exception(f"Error in back_to_image_actions_callback: {e}")
        await callback_query.answer("An error occurred.", show_alert=True)

# The original extract_text_from_image was renamed to ocr_space_extract to avoid confusion
# with the main orchestrator function extract_text_from_image_and_respond.
# The original `extract_text_res` is now `extract_text_from_image_and_respond` and is a utility, not a direct handler.
# Actual photo message handlers will be in `modules/image/handlers.py`.
