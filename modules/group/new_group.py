import asyncio
import logging

from aiogram import types, F, Router, Bot
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, MEMBER, KICKED, LEFT, RESTRICTED, ADMIN, CREATOR
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hitalic, hlink # For HTML mention if needed

from config import LOG_CHANNEL as STCLOG
# Assuming these functions from group_permissions will be adapted for Aiogram
from modules.group.group_permissions import (
    check_bot_permissions_utility, # Renamed for clarity if it's a utility
    update_group_stats_utility, 
    send_permissions_message_utility, 
    leave_group_if_no_permissions_utility
)

logger = logging.getLogger(__name__)
group_events_router = Router()

WELCOME_MESSAGE_TEXT_TEMPLATE = """
🎉 {user_mention} **ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴀᴅᴅɪɴɢ ᴍᴇ ᴛᴏ {chat_title}!** 🎉

🤖 ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ᴀꜱꜱɪꜱᴛ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴡɪᴛʜ:
• 💬 ꜱᴍᴀʀᴛ ᴄᴏɴᴠᴇʀꜱᴀᴛɪᴏɴꜱ
• 🖼️ ɪᴍᴀɢᴇ ɢᴇɴᴇʀᴀᴛɪᴏɴ
• 🎙️ ᴠᴏɪᴄᴇ ʀᴇᴄᴏɢɴɪᴛɪᴏɴ
• 📝 ᴛᴇxᴛ ᴀɴᴀʟʏꜱɪꜱ

ᴛᴏ ᴡᴏʀᴋ ᴄᴏʀʀᴇᴄᴛʟʏ, ɪ ɴᴇᴇᴅ ᴛʜᴇꜱᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴꜱ:
✅ Delete Messages - To keep the chat clean.
✅ Invite Users via Link - For group invite links (if I'm an admin).
✅ Manage Chat - To pin messages or edit group info (if admin).

ʟᴇᴛ'ꜱ ᴍᴀᴋᴇ ᴛʜɪꜱ ɢʀᴏᴜᴘ ᴀᴡᴇꜱᴏᴍᴇ ᴛᴏɢᴇᴛʜᴇʀ! 🚀
"""

# This handler triggers when the bot's status changes from not being a member to being a member.
# It covers being added directly or unbanned if it was previously kicked.
@group_events_router.chat_member(ChatMemberUpdatedFilter(member_status_changed=(KICKED | LEFT | RESTRICTED) >> (MEMBER | ADMIN | CREATOR)))
async def bot_added_to_group_handler(event: types.ChatMemberUpdated, bot: Bot):
    if event.new_chat_member.user.id != bot.id:
        return 

    chat = event.chat
    added_by_user = event.from_user

    logger.info(f"Bot @{(await bot.get_me()).username} was added to group '{chat.title}' (ID: {chat.id}) by user {added_by_user.id} ({added_by_user.full_name})")

    user_mention_html = added_by_user.mention_html(added_by_user.full_name if added_by_user.full_name else "User")
    
    user_info_log = (f"User: {user_mention_html}\n"
                     f"Username: @{added_by_user.username if added_by_user.username else 'N/A'}\n"
                     f"ID: `{added_by_user.id}`") # Markdown for ID
    
    group_info_log = f"Group Name: {hbold(chat.title if chat.title else 'Unknown Group')}\nGroup ID: `{chat.id}`"
    try:
        members_count = await bot.get_chat_member_count(chat.id)
        group_info_log += f"\nMembers: {members_count}"
    except Exception as e:
        logger.error(f"Failed to get members count for chat {chat.id}: {e}")

    if STCLOG:
        try:
            log_chat_id = int(STCLOG)
            await bot.send_message(
                chat_id=log_chat_id,
                text=f"**🎉#New_group! 🎉**\n\nAdded by:\n{user_info_log}\n\nGroup info:\n{group_info_log}",
                parse_mode="HTML"
            )
        except ValueError: logger.error(f"Invalid STCLOG ID: {STCLOG}")
        except Exception as e_log: logger.error(f"Error sending new group log to STCLOG: {e_log}")
            
    message_text = WELCOME_MESSAGE_TEXT_TEMPLATE.format(
        user_mention=user_mention_html,
        chat_title=hbold(chat.title if chat.title else "your group")
    )
            
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 ꜱᴛᴀʀᴛ ᴜꜱɪɴɢ ʙᴏᴛ", callback_data="group_start_intro"), # Differentiate from /start in group
            InlineKeyboardButton(text="📚 ᴄᴏᴍᴍᴀɴᴅꜱ", callback_data="group_commands_list") 
        ],
        [InlineKeyboardButton(text="🔗 ꜱᴜᴘᴘᴏʀᴛ", url="https://t.me/AdvAIworld")]
    ])
            
    try:
        await bot.send_message(
            chat_id=chat.id,
            text=message_text,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode="HTML"
        )
    except Exception as e_send_welcome:
        logger.error(f"Failed to send welcome message to group {chat.id}: {e_send_welcome}")
        try:
            await bot.send_message(added_by_user.id, f"I couldn't send a welcome message to the group '{chat.title or chat.id}'. Please check my permissions there.")
        except Exception: pass 
        return 

    try:
        current_permissions = await check_bot_permissions_utility(bot, chat.id) 
        await update_group_stats_utility(chat.id, current_permissions, added_by_user.id)
        await asyncio.sleep(2)
        await send_permissions_message_utility(bot, chat.id, current_permissions)
        asyncio.create_task(delayed_permission_check_task(bot, chat.id))
    except Exception as e_perm:
        logger.error(f"Error during initial permission processing for group {chat.id}: {e_perm}")

async def delayed_permission_check_task(bot: Bot, chat_id: int, delay_seconds: int = 300):
    try:
        await asyncio.sleep(delay_seconds)
        logger.info(f"Performing delayed permission check for chat ID: {chat_id}")
        await leave_group_if_no_permissions_utility(bot, chat_id)
    except Exception as e:
        logger.error(f"Error in delayed_permission_check_task for chat {chat_id}: {e}")

# Handler for other users joining (not the bot)
@group_events_router.message(F.new_chat_members)
async def regular_user_joins_handler(message: types.Message, bot: Bot):
    # This handler will catch any new members, including the bot.
    # We need to ensure we don't re-process if the bot_added_to_group_handler already did.
    # The ChatMemberUpdated handler is more specific for the bot joining.
    # This F.new_chat_members is broader.
    
    # Check if the bot is among the new members. If so, bot_added_to_group_handler should have handled it.
    # To avoid double processing, we can check if any of the new members is the bot.
    my_id = bot.id
    if any(member.id == my_id for member in message.new_chat_members):
        logger.debug(f"Bot joining event handled by chat_member_handler, skipping F.new_chat_members for bot in chat {message.chat.id}")
        return

    # If we reach here, it's other users joining. Implement desired logic.
    # For example, send a welcome message or log.
    for member in message.new_chat_members:
        logger.info(f"User {member.full_name} (ID: {member.id}) joined chat {message.chat.id} ({message.chat.title})")
        # Example: Send a simple welcome, but be mindful of spamming.
        # await message.answer(f"Welcome, {member.mention_html()}!")
    
    # For now, just log. Add specific welcome logic if needed.
    pass
