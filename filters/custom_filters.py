from aiogram.filters import Filter
from aiogram.types import Message
from aiogram import Bot

class IsChatTextFilter(Filter):
    """
    Checks if a message is a text message and not a command.
    Equivalent to Pyrogram's:
    def is_chat_text_filter():
        async def funcc(_, __, update):
            if bool(update.text):
                return not update.text.startswith("/")
            return False
        return filters.create(funcc)
    """
    async def __call__(self, message: Message) -> bool:
        return bool(message.text) and not message.text.startswith("/")

class IsNotCommandFilter(Filter):
    """
    Checks if a message is not a command.
    If it's a text message, it must not start with '/'.
    If it's not a text message (e.g., photo, sticker), it passes.
    Equivalent to Pyrogram's:
    def is_not_command_filter():
        async def func(_, __, message):
            if message.text:
                return not message.text.startswith('/')
            return True  # Non-text messages are not commands
        return filters.create(func)
    """
    async def __call__(self, message: Message) -> bool:
        if message.text:
            return not message.text.startswith('/')
        return True # Pass for non-text messages

class IsReplyToBotFilter(Filter):
    """
    Checks if a message is a reply to the bot itself.
    Needs the Bot instance to compare IDs.
    Equivalent to Pyrogram's:
    def is_reply_to_bot_filter():
        async def func(_, __, message):
            if message.reply_to_message and message.reply_to_message.from_user:
                return message.reply_to_message.from_user.id == advAiBot.me.id
            return False
        return filters.create(func)
    """
    async def __call__(self, message: Message, bot: Bot) -> bool:
        if message.reply_to_message and message.reply_to_message.from_user:
            return message.reply_to_message.from_user.id == bot.id
        return False
