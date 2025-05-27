from aiogram import Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from config import ADMINS, OWNER_ID
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(Command("info"))
async def info_command(message: Message):
    # Check maintenance mode and admin status
    if await maintenance_check(message.from_user.id) and message.from_user.id not in ADMINS:
        maint_msg = await maintenance_message(message.from_user.id)
        await message.answer(maint_msg)
        return

    user_id = message.from_user.id

    if user_id in ADMINS or user_id == OWNER_ID:
        try:
            # Get target user ID from command or replied message
            target_user_id = None
            target_user = None
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user_id = message.reply_to_message.from_user.id
                target_user = message.reply_to_message.from_user
            else:
                parts = message.text.split()
                if len(parts) > 1:
                    try:
                        target_user_id = int(parts[1])
                        # aiogram does not provide get_users, so we use get_chat
                        target_user = await message.bot.get_chat(target_user_id)
                    except ValueError:
                        username = parts[1].strip('@')
                        try:
                            target_user = await message.bot.get_chat(username)
                            target_user_id = target_user.id
                        except Exception:
                            await message.answer("Could not find user with that username.")
                            return
                    except Exception as e:
                        await message.answer(f"Error finding user: {e}")
                        return
                else:
                    await message.answer(
                        "Please specify a user ID or username, or reply to a message from the user."
                    )
                    return

            if not target_user_id:
                await message.answer("Could not determine target user.")
                return

            try:
                user_info = f"\U0001F464 **User Information**\n\n"
                user_info += f"• **User ID:** `{target_user_id}`\n"
                user_info += f"• **First Name:** {target_user.first_name}\n"
                if getattr(target_user, 'last_name', None):
                    user_info += f"• **Last Name:** {target_user.last_name}\n"
                if getattr(target_user, 'username', None):
                    user_info += f"• **Username:** @{target_user.username}\n"
                user_info += f"• **Is Bot:** {'Yes' if getattr(target_user, 'is_bot', False) else 'No'}\n"
                user_info += f"• **Is Premium:** {'Yes' if getattr(target_user, 'is_premium', False) else 'No'}\n"
                user_info += f"• **Can be contacted:** {'Yes' if not getattr(target_user, 'is_bot', False) and not getattr(target_user, 'is_deleted', False) else 'No'}\n"
                user_info += f"\n[Direct Link to User](tg://user?id={target_user_id})"
                keyboard = [
                    [
                        InlineKeyboardButton(text="Message User", url=f"tg://user?id={target_user_id}"),
                        InlineKeyboardButton(text="User Profile", url=f"tg://user?id={target_user_id}")
                    ]
                ]
                await message.answer(user_info, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), disable_web_page_preview=True)
            except Exception as e:
                await message.answer(f"Error getting user info: {e}")
                logger.error(f"Error getting user info: {e}")
        except Exception as e:
            await message.answer(f"Error processing command: {e}")
            logger.error(f"Error in info command: {e}")
    else:
        await message.answer("Only admins can use this command.")

def register_group_info_handlers(dp: Router):
    dp.include_router(router)