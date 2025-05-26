import os
import tempfile
from gtts import gTTS
import pydub
import asyncio # Keep, as pydub/gTTS might be used in async contexts by handlers

from aiogram import Bot, types # Aiogram imports
from config import LOG_CHANNEL # Assuming LOG_CHANNEL is an int/str chat_id
# from modules.chatlogs import user_log # user_log was not used in the original snippet for this file

# No router needed here if it only contains utility functions called by handlers elsewhere.

async def handle_text_message(bot: Bot, message: types.Message, text: str, language: str = 'en', voice_speed: bool = False):    
    """
    Convert text to voice with enhanced quality and language support using Aiogram.
    
    Parameters:
    - bot: Aiogram Bot instance
    - message: Aiogram Message object (to reply to)
    - text: Text to convert to speech
    - language: Language code (default: 'en')
    - voice_speed: Whether to use slow voice (default: False)
    
    Returns:
    - Path to the generated audio file, or None if error.
    """
    try:
        # Create a temporary directory that cleans itself up
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "response_audio_raw.mp3")
            enhanced_path = os.path.join(temp_dir, "response_audio_enhanced.mp3")
            
            # Generate speech using gTTS
            tts = gTTS(text=text, lang=language, tld='com', slow=voice_speed)
            tts.save(temp_path)
            
            final_audio_path = temp_path # Default to raw if enhancement fails
            
            # Enhance audio quality using pydub if available
            try:
                audio = pydub.AudioSegment.from_mp3(temp_path)
                normalized_audio = audio.normalize()
                compressed_audio = normalized_audio.compress_dynamic_range()
                compressed_audio.export(enhanced_path, format="mp3", bitrate="192k")
                final_audio_path = enhanced_path
            except Exception as e:
                print(f"Audio enhancement error (using original): {e}")
                # final_audio_path remains temp_path
            
            caption = "🎙️ **Voice Response**" # Markdown for Aiogram
            
            # Send the audio file as a reply
            # Aiogram uses FSInputFile for local files
            audio_file_input = types.FSInputFile(final_audio_path)
            await message.answer_audio(
                audio=audio_file_input, 
                caption=caption,
                title="AI Voice Response", # This title is for the audio file metadata
                performer="Advanced AI Bot", # Also metadata
                parse_mode="Markdown" # For the caption
            )
            
            # Log the audio file to LOG_CHANNEL
            if LOG_CHANNEL:
                try:
                    log_channel_id = int(LOG_CHANNEL) # Ensure it's an int for bot.send_audio
                    await bot.send_audio(
                        chat_id=log_channel_id, 
                        audio=types.FSInputFile(final_audio_path),
                        caption=f"Voice response generated for user {message.from_user.id}"
                        )
                except ValueError:
                    print(f"Invalid LOG_CHANNEL ID: {LOG_CHANNEL}. Must be an integer.")
                except Exception as log_e:
                    print(f"Error sending audio to LOG_CHANNEL: {log_e}")
            
            # Return the path of the sent audio (might not be needed by caller if directly sent)
            # The file is in a temporary directory, so it will be deleted after this function.
            # If the path is needed externally, the file should be saved to a persistent location.
            # For now, returning the path, but be aware of its temporary nature.
            return final_audio_path 
            
    except Exception as e:
        error_message = f"❌ Error generating audio: {str(e)}"
        try:
            await message.answer(error_message)
        except Exception as reply_e: # Fallback if replying fails
            print(f"Failed to send error message to user: {reply_e}")
        return None


async def generate_expressive_voice(bot: Bot, message: types.Message, text: str, style: str = "neutral", language: str = 'en'):
    """
    Generate more expressive voice based on text content and style using Aiogram.
    
    Parameters:
    - bot: Aiogram Bot instance
    - message: Aiogram Message object
    - text: Text to convert to speech
    - style: Voice style (neutral, formal, friendly)
    - language: Language code
    
    Returns:
    - Path to generated audio, or None if error.
    """
    voice_speed = False # Default speed
    
    if style == "formal":
        voice_speed = True  # Slower for formal
    elif style == "friendly":
        # Could add more customization here if gTTS supported it directly,
        # or use different TTS engines for more expressiveness.
        pass # Keep default for friendly
    
    # Call the adapted handle_text_message function
    return await handle_text_message(bot, message, text, language, voice_speed)
