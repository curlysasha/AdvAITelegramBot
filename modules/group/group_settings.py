from aiogram import Router, Bot
from aiogram.types import Message
from config import LOG_CHANNEL as STCLOG, DATABASE_URL, ADMINS, OWNER_ID
import logging
from pymongo import MongoClient
from datetime import datetime
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled

logger = logging.getLogger(__name__)

router = Router()

client = MongoClient(DATABASE_URL)
db = client['aibotdb']
groups_collection = db.groups

@router.message()
async def leave_group(message: Message):
    # Only respond to /gleave in group chats
    if not message.text or not message.text.startswith("/gleave"):
        return
    if await maintenance_check(message.from_user.id) and message.from_user.id not in ADMINS:
        maint_msg = await maintenance_message(message.from_user.id)
        await message.answer(maint_msg)
        return
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type not in ["group", "supergroup"]:
        await message.answer("This command can only be used in groups.")
        return
    if user_id in ADMINS or user_id == OWNER_ID or await is_group_admin(message.bot, chat_id, user_id):
        await message.answer("Leaving this group, goodbye!")
        try:
            groups_collection.update_one(
                {"chat_id": chat_id},
                {"$set": {
                    "left": True,
                    "left_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "left_by": user_id
                }},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating database when leaving group: {e}")
        try:
            await message.bot.leave_chat(chat_id)
        except Exception as e:
            logger.error(f"Error leaving group: {e}")
    else:
        await message.answer("Only admins can use this command.")

@router.message()
async def invite_command(message: Message):
    if not message.text or not message.text.startswith("/invite"):
        return
    if await maintenance_check(message.from_user.id) and message.from_user.id not in ADMINS:
        maint_msg = await maintenance_message(message.from_user.id)
        await message.answer(maint_msg)
        return
    user_id = message.from_user.id
    if user_id in ADMINS or user_id == OWNER_ID:
        try:
            parts = message.text.split()
            if len(parts) > 1:
                target_chat = parts[1]
                try:
                    if target_chat.startswith("@"):
                        chat = await message.bot.get_chat(target_chat)
                        chat_id = chat.id
                        chat_title = chat.title
                    else:
                        chat_id = int(target_chat)
                        chat = await message.bot.get_chat(chat_id)
                        chat_title = chat.title
                    invite_link = await message.bot.create_chat_invite_link(chat_id)
                    await message.answer(
                        f"\U0001F517 **Invite Link for {chat_title}**\n\n"
                        f"{invite_link.invite_link}\n\n"
                        f"Expires: {'Never' if not invite_link.expire_date else invite_link.expire_date}\n"
                        f"Created by: [You](tg://user?id={user_id})"
                    )
                except Exception as e:
                    await message.answer(f"Error getting invite link: {str(e)}")
                    logger.error(f"Error getting invite link: {e}")
            else:
                await message.answer(
                    "Please specify a chat ID or username.\n\n"
                    "Usage: `/invite @chatusername` or `/invite -1001234567890`"
                )
        except Exception as e:
            await message.answer(f"Error processing command: {str(e)}")
            logger.error(f"Error in invite command: {e}")
    else:
        await message.answer("Only admins can use this command.")

async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["creator", "administrator"]
    except Exception:
        return False

def register_group_settings_handlers(dp: Router):
    dp.include_router(router)