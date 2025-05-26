import os
import asyncio
import tempfile
import soundfile as sf
import speech_recognition as sr

from aiogram import Bot, types
from aiogram.enums import ChatAction # For chat actions

from config import LOG_CHANNEL # Assuming LOG_CHANNEL is an int/str chat_id

# Assuming these are or will be Aiogram-compatible
from modules.speech.text_to_voice import handle_text_message 
from modules.models.ai_res import get_response, get_streaming_response # AI response functions
from modules.chatlogs import user_log, error_log # Logging functions
from modules.core.database import db_service # Database service

# Get collections from the database service (assuming this works as is)
user_voice_setting_collection = db_service.get_collection('user_voice_setting')
history_collection = db_service.get_collection('history')

# No router needed in this file if it only contains utility functions.
# Handlers will be in a separate handlers.py file.

# Enhanced audio processing to support multiple formats and languages (largely unchanged)
async def process_audio_file(input_path: str, output_path: str = None, language: str = "en-US"):
    """Process audio file to extract text with enhanced language support"""
    try:
        if not output_path:
            # Create a temporary path for the WAV file if not provided
            # This tempfile should be handled by the caller or be in a context manager
            # For now, creating it next to the input, which might not be ideal.
            # It's better if the caller provides a writable output_path in a temp directory.
            temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            output_path = temp_wav_file.name
            temp_wav_file.close() # Close it so sf.write can use it

        # Convert to WAV format if not already
        # Ensure input_path exists and is readable
        audio, sample_rate = sf.read(input_path)
        sf.write(output_path, audio, sample_rate, format="WAV")
        
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.energy_threshold = 300 
        
        with sr.AudioFile(output_path) as source:
            audio_data = recognizer.record(source)
            
        try:
            text = recognizer.recognize_google(audio_data, language=language)
            return text, None
        except sr.UnknownValueError:
            return None, "Could not understand the audio. Please try speaking clearly."
        except sr.RequestError as e:
            return None, f"Speech recognition service unavailable: {e}"
        finally:
            # Clean up temporary WAV file if created by this function
            if output_path.endswith(".wav") and 'temp_wav_file' in locals():
                 if os.path.exists(output_path):
                    os.remove(output_path)
            
    except Exception as e:
        return None, f"Audio processing error: {str(e)}"

async def handle_voice_message(bot: Bot, message: types.Message):
    processing_msg = await message.answer(
        "🎙️ **Processing Voice Message**\n\n"
        "Converting your audio to text...\n"
        "Please wait a moment.",
        parse_mode="Markdown"
    )
    
    file_id = None
    try:
        if message.voice:
            file_id = message.voice.file_id
        elif message.audio: # Also handle audio files if intended
            file_id = message.audio.file_id
        else:
            await processing_msg.edit_text("❌ Unsupported media type")
            return
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error processing media: {e}")
        await error_log(bot, "VoiceMsgError_Media", str(e), message.from_user.id)
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        voice_path_on_disk = os.path.join(temp_dir, f"{file_id}.oga") # Temporary file path
        wav_output_path = os.path.join(temp_dir, f"{file_id}_processed.wav")

        try:
            file_info = await bot.get_file(file_id)
            await bot.download_file(file_path=file_info.file_path, destination=voice_path_on_disk)
        except Exception as e:
            await processing_msg.edit_text(f"❌ Error downloading voice message: {str(e)}")
            await error_log(bot, "VoiceMsgError_Download", str(e), message.from_user.id)
            return
            
        recognized_text, error = await process_audio_file(voice_path_on_disk, output_path=wav_output_path)
        
        if error:
            await processing_msg.edit_text(
                f"❌ **Voice Recognition Failed**\n\n{error}\n\n"
                "Please try recording again with clearer audio.",
                parse_mode="Markdown"
            )
            return
        
        if not recognized_text or recognized_text.strip() == "":
            await processing_msg.edit_text(
                "⚠️ **No Speech Detected**\n\n"
                "I couldn't detect any speech in your audio.\n"
                "Please try recording again with clearer speech.",
                parse_mode="Markdown"
            )
            return
        
        await processing_msg.edit_text(
            f"✅ **Voice Recognized**\n\nI heard: *{recognized_text}*\n\nGenerating response...",
            parse_mode="Markdown"
        )
        
        user_id = message.from_user.id
        user_settings = user_voice_setting_collection.find_one({"user_id": user_id})
        # Default to "voice" if no setting found or key missing
        response_mode = user_settings.get("voice", "voice") if user_settings and "voice" in user_settings else "voice"
        
        try:
            user_history_doc = history_collection.find_one({"user_id": user_id})
            history = user_history_doc['history'] if user_history_doc and 'history' in user_history_doc else [{
                "role": "assistant", 
                "content": "I'm your advanced AI assistant. I can respond to your voice messages and help with various tasks."
            }]
            history.append({"role": "user", "content": recognized_text})
            
            chat_action = ChatAction.RECORD_AUDIO if response_mode == "voice" else ChatAction.TYPING
            await bot.send_chat_action(chat_id=message.chat.id, action=chat_action)
            
            # Using get_response as primary, assuming it handles streaming or is preferred.
            # The streaming logic from original code can be complex to directly migrate without full context of get_streaming_response
            # For simplicity, using get_response. If streaming is essential, get_streaming_response needs careful adaptation.

            ai_response = await get_response(history) # Assuming get_response is async and adapted
            # If get_response is not async, it needs to be run in an executor:
            # loop = asyncio.get_event_loop()
            # ai_response = await loop.run_in_executor(None, get_response, history)


            if not ai_response: # Check if AI response is empty or None
                 await processing_msg.edit_text(
                    f"🔊 **Voice Message**\n\n"
                    f"You said: *{recognized_text}*\n\n"
                    f"**Response:**\nI received your message but couldn't generate a response at this time.",
                    parse_mode="Markdown"
                )
                 history.append({"role": "assistant", "content": "No response generated."})
                 return # End processing if no AI response

            history.append({"role": "assistant", "content": ai_response})
            history_collection.update_one({"user_id": user_id}, {"$set": {"history": history}}, upsert=True)
                
            if response_mode == "voice":
                await processing_msg.edit_text(
                    f"🔊 **Voice Message**\n\n"
                    f"You said: *{recognized_text}*\n\n"
                    "Creating audio response...",
                    parse_mode="Markdown"
                )
                # Call adapted handle_text_message from text_to_voice.py
                await handle_text_message(bot, message, ai_response) # message object is passed for reply context
                
                # Update processing_msg after audio is sent
                await processing_msg.edit_text(
                    f"🔊 **Voice Conversation**\n\n"
                    f"You said: *{recognized_text}*\n\n"
                    f"**Response:** {ai_response}",
                    parse_mode="Markdown"
                )
            else: # Text response
                await processing_msg.edit_text(
                    f"🔊 **Voice Message**\n\n"
                    f"You said: *{recognized_text}*\n\n"
                    f"**Response:**\n{ai_response}",
                    parse_mode="Markdown"
                )
            
            # Response preferences buttons (assuming they are handled by other callback handlers)
            # For "toggle_voice_{user_id}" and "new_voice_{user_id}"
            # These callback data need to be handled by appropriate routers.
            toggle_button_text = "📝 Text Responses" if response_mode == "voice" else "🔊 Voice Responses"
            response_markup = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=toggle_button_text, callback_data=f"speech_toggle_voice_pref_{user_id}")], # Prefixed for clarity
             #  [types.InlineKeyboardButton(text="🎙️ New Voice Message", callback_data=f"speech_new_voice_msg_{user_id}")] # Example for new voice
            ])
            
            # Send the preference buttons as a new message, or edit processing_msg's reply_markup if preferred.
            # Sending as new message to avoid conflict if processing_msg was the final response.
            await message.answer(
                "**Response Preferences**",
                reply_markup=response_markup,
                parse_mode="Markdown"
            )
            
            # Log interaction (assuming user_log is Aiogram compatible)
            # The original code logged voice_path + ".wav", ensure wav_output_path is used if that's the actual file.
            if LOG_CHANNEL:
                try:
                    log_channel_id = int(LOG_CHANNEL)
                    await bot.send_audio(log_channel_id, types.FSInputFile(wav_output_path), caption=f"Processed voice from user {user_id}")
                except ValueError:
                     print(f"Invalid LOG_CHANNEL ID for voice log: {LOG_CHANNEL}")
                except Exception as log_e:
                    print(f"Error logging voice to channel: {log_e}")

            await user_log(bot, message, f"\nInput (Voice): {recognized_text}\n\nOutput (AI): {ai_response}")
            
        except Exception as e:
            await message.answer(f"An error occurred while generating AI response: {str(e)}")
            await error_log(bot, "VoiceMsgError_AI", str(e), message.from_user.id, context=recognized_text)
            print(f"Error in AI response part of handle_voice_message: {e}")

# The handle_voice_toggle function will be moved to handlers.py as it's a callback handler.
