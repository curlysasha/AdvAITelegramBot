# Importing required libraries
from aiogram import Router, Bot
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from config import LOG_CHANNEL as STCLOG
from modules.group.group_permissions import check_bot_permissions, update_group_stats, send_permissions_message, leave_group_if_no_permissions
import asyncio

router = Router()

@router.chat_member()
async def new_chat_members(event: ChatMemberUpdated):
    # Only handle when the bot is added to a group
    if event.new_chat_member.user.id != (await event.bot.me()).id:
        return
    user = event.from_user
    chat = event.chat
    bot = event.bot
    nam = user.mention if hasattr(user, 'mention') else user.first_name
    user_info = f"User: {nam}\nUsername: @{user.username}\nID: {user.id}"
    group_info = f"Group ID: `{chat.id}`"
    try:
        members_count = await bot.get_chat_members_count(chat.id)
        group_info += f"\nMembers: {members_count}"
    except Exception as e:
        print(f"Failed to get members count: {e}")
    await bot.send_message(
        chat_id=STCLOG,
        text=f"**\U0001F389#New_group! \U0001F389\nAdded by \n{user_info}\nGroup info\n{group_info}**",
    )
    message_text = f"\U0001F389 **Thank you {nam} for adding me to your group!** \U0001F389\n"
    message_text += """
\U0001F916 I'm here to assist your group with:

• \U0001F4AC Smart Conversation
• \U0001F5BC\uFE0F Image Generation
• \U0001F399\uFE0F Voice Recognition
• \U0001F4DD Text Analysis
"""
    message_text += """
To work correctly, I need the following permissions:

\u2705 Delete Messages - to keep the chat clean
\u2705 Invite Users - for group invite features

Let's make this group awesome! \U0001F680
"""
    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("\U0001F916 Start Using Bot", callback_data="group_start"),
                InlineKeyboardButton("\U0001F4DA Commands", callback_data="group_commands")
            ],
            [
                InlineKeyboardButton("\U0001F517 Support", url="https://t.me/AdvAIworld")
            ]
        ]
    )
    await bot.send_message(
        chat_id=chat.id,
        text=message_text,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    permissions = await check_bot_permissions(bot, chat.id)
    await update_group_stats(chat.id, permissions, user.id)
    await asyncio.sleep(2)
    await send_permissions_message(bot, chat.id, permissions)
    asyncio.create_task(delayed_permission_check(bot, chat.id))

async def delayed_permission_check(bot: Bot, chat_id: int, delay_seconds=300):
    try:
        await asyncio.sleep(delay_seconds)
        await leave_group_if_no_permissions(bot, chat_id)
    except Exception as e:
        print(f"Error in delayed permission check: {e}")

def register_new_group_handlers(dp: Router):
    dp.include_router(router)
