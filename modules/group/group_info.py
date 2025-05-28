import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMINS, OWNER_ID
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled

logger = logging.getLogger(__name__)

#user info
async def info_command(client: Client, message: Message) -> None:
    """
    Handle information about a user
    
    Args:
        client: Telegram client
        message: Message with command
    """
    # Check maintenance mode and admin status
    if await maintenance_check(message.from_user.id) and message.from_user.id not in ADMINS:
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return
        
    user_id = message.from_user.id
    
    if user_id in ADMINS or user_id == OWNER_ID:
        try:
            # Get target user ID from command or replied message
            target_user_id = None
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user_id = message.reply_to_message.from_user.id
                target_user = message.reply_to_message.from_user
            else:
                # Check if a user ID is provided in the command
                parts = message.text.split()
                if len(parts) > 1:
                    try:
                        target_user_id = int(parts[1])
                        target_user = await client.get_users(target_user_id)
                    except ValueError:
                        # Check if username is provided
                        username = parts[1].strip('@')
                        try:
                            target_user = await client.get_users(username)
                            target_user_id = target_user.id
                        except Exception:
                            await message.reply_text("Не удалось найти пользователя с таким именем.")
                            return
                    except Exception as e:
                        await message.reply_text(f"Ошибка при поиске пользователя: {e}")
                        return
                else:
                    await message.reply_text(
                        "Пожалуйста, укажите ID или имя пользователя, или ответьте на сообщение от пользователя."
                    )
                    return
            
            if not target_user_id:
                await message.reply_text("Не удалось определить целевого пользователя.")
                return
            
            # Get user info
            try:
                # Format user information
                user_info = f"👤 **Информация о пользователе**\n\n"
                user_info += f"• **ID пользователя:** `{target_user_id}`\n"
                user_info += f"• **Имя:** {target_user.first_name}\n"
                
                if target_user.last_name:
                    user_info += f"• **Фамилия:** {target_user.last_name}\n"
                
                if target_user.username:
                    user_info += f"• **Имя пользователя:** @{target_user.username}\n"
                
                user_info += f"• **Это бот:** {'Да' if target_user.is_bot else 'Нет'}\n"
                user_info += f"• **Премиум:** {'Да' if target_user.is_premium else 'Нет'}\n"
                
                # Add when the bot can contact this user
                user_info += f"• **С ботом можно связаться:** {'Да' if not target_user.is_bot and not target_user.is_deleted else 'Нет'}\n"
                
                # Add user link
                user_info += f"\n[Прямая ссылка на пользователя](tg://user?id={target_user_id})"
                
                # Create keyboard for additional actions
                keyboard = [
                    [
                        InlineKeyboardButton("Написать пользователю", url=f"tg://user?id={target_user_id}"),
                        InlineKeyboardButton("Профиль пользователя", url=f"tg://user?id={target_user_id}")
                    ]
                ]
                
                await message.reply_text(
                    user_info,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            except Exception as e:
                await message.reply_text(f"Ошибка при получении информации о пользователе: {e}")
                logger.error(f"Ошибка при получении информации о пользователе: {e}")
        
        except Exception as e:
            await message.reply_text(f"Ошибка при обработке команды: {e}")
            logger.error(f"Ошибка в info команде: {e}")
    else:
        await message.reply_text("Только администраторы могут использовать эту команду.")