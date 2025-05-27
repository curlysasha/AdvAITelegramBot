from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
import asyncio
import logging
from modules.user.start import register_start_handlers
from modules.user.help import register_help_handlers
from modules.user.commands import register_command_handlers
from modules.user.settings import register_settings_handlers
from modules.user.assistant import register_assistant_handlers
from modules.user.user_support import register_support_handlers
from modules.user.dev_support import register_dev_support_handlers
from modules.image.inline_image_generation import register_inline_image_handlers
from modules.image.image_generation import register_image_generation_handlers
from modules.models.inline_ai_response import register_inline_ai_handlers
from config import BOT_TOKEN
from modules.group.group_info import register_group_info_handlers
from modules.group.group_settings import register_group_settings_handlers
from modules.group.new_group import register_new_group_handlers

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register handlers
    register_start_handlers(dp)
    register_help_handlers(dp)
    register_command_handlers(dp)
    register_settings_handlers(dp)
    register_assistant_handlers(dp)
    register_support_handlers(dp)
    register_dev_support_handlers(dp)
    register_inline_image_handlers(dp)
    register_image_generation_handlers(dp)
    register_inline_ai_handlers(dp)
    register_group_info_handlers(dp)
    register_group_settings_handlers(dp)
    register_new_group_handlers(dp)

    # Set bot commands (optional)
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="settings", description="Bot settings"),
    ])

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
