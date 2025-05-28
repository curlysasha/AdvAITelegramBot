import os
import asyncio
import time
import re
from typing import List, Dict, Any, Optional, Generator, Union
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from g4f.client import Client as GPTClient
from modules.core.database import get_history_collection
from modules.chatlogs import user_log
from modules.maintenance import maintenance_check, maintenance_message, is_feature_enabled


# Initialize the GPT client with a more efficient provider
gpt_client = GPTClient(provider="PollinationsAI")

def get_response(history: List[Dict[str, str]]) -> str:  
    """
    Get a non-streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        
    Returns:
        String response from the AI model
    """
    try:
        # Ensure history is a list
        if not isinstance(history, list):
            history = [history]
            
        # If history is empty, use the default system message
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()  # Create a copy to avoid modifying the original
            
        # Ensure each message in history is a dictionary
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
                
        response = gpt_client.chat.completions.create(
            model="gpt-4o",  # Using more capable model for higher quality responses
            messages=history
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm experiencing technical difficulties. Please try again in a moment."

def get_streaming_response(history: List[Dict[str, str]]) -> Optional[Generator]:
    """
    Get a streaming response from the AI model
    
    Args:
        history: Conversation history in the format expected by the AI model
        
    Returns:
        Generator yielding response chunks or None if there's an error
    """
    try:
        # Ensure history is a list
        if not isinstance(history, list):
            history = [history]
            
        # If history is empty, use the default system message
        if not history:
            history = DEFAULT_SYSTEM_MESSAGE.copy()  # Create a copy to avoid modifying the original
            
        # Ensure each message in history is a dictionary
        for i, msg in enumerate(history):
            if not isinstance(msg, dict):
                history[i] = {"role": "user", "content": str(msg)}
                
        # Stream parameter set to True to get response chunks
        response = gpt_client.chat.completions.create(
            model="gpt-4o",  # Using more capable model for higher quality responses
            messages=history,
            stream=True
        )
        return response
    except Exception as e:
        print(f"Error generating streaming response: {e}")
        return None

def sanitize_markdown(text: str) -> str:
    """
    Ensures proper markdown formatting in streaming responses
    
    Args:
        text: Raw text that may contain incomplete markdown
        
    Returns:
        Text with proper markdown formatting
    """
    # Count opening and closing backticks to handle code blocks
    backticks_opened = text.count('```')
    if backticks_opened % 2 != 0:
        text += '\n```'  # Close incomplete code block
    
    # Handle inline code (single backtick)
    single_backticks = text.count('`') - (backticks_opened * 3)
    if single_backticks % 2 != 0:
        text += '`'  # Close incomplete inline code
    
    # Handle markdown bold/italic
    asterisks_count = text.count('*')
    if asterisks_count % 2 != 0:
        text += '*'  # Close incomplete bold/italic
    
    # Handle incomplete links or formatting
    if text.count('[') > text.count(']'):
        text += ']'
    
    if text.count('(') > text.count(')'):
        text += ')'
    
    return text

# Default system message with modern, professional tone
DEFAULT_SYSTEM_MESSAGE: List[Dict[str, str]] = [
    {
        "role": "system",
        "content": (
            "Я ваш продвинутый AI-ассистент, созданный для предоставления полезных, точных и продуманных ответов. "
            "Я могу помочь с широким спектром задач: отвечать на вопросы, создавать контент, "
            "анализировать информацию и вести содержательные беседы. Я постоянно учусь "
            "и совершенствуюсь, чтобы лучше соответствовать вашим потребностям. "
        )
    },
    {
        "role": "assistant",
        "content": (
            "🎨 **Генерация изображений**\n"
            "Я могу помочь вам создать изображения с помощью команды /img. Вот примеры диалогов:\n\n"
            "Пример 1:\n"
            "Пользователь: Можешь создать изображение футуристического города?\n"
            "Ассистент: Я помогу вам с этим изображением. Вот команда:\n"
            "```\n/img a futuristic city with flying cars, neon lights, and towering skyscrapers, cyberpunk style\n```\n"
            "Просто скопируйте и вставьте эту команду, чтобы сгенерировать изображение.\n\n"
            "Пример 2:\n"
            "Пользователь: Хочу спокойный природный пейзаж\n"
            "Ассистент: Вот команда для создания спокойного природного пейзажа:\n"
            "```\n/img a serene forest landscape with a crystal clear lake, morning mist, and golden sunlight filtering through trees\n```\n\n"
            "Вы можете использовать эти команды напрямую:\n"
            "• `/img [prompt]` — Генерация изображений\n"
            "• `/generate [prompt]` — Альтернативная команда\n\n"
            "💡 **Советы для лучших изображений**:\n"
            "• Будьте конкретны в деталях, освещении и ракурсе\n"
            "• Указывайте художественный стиль\n"
            "• Описывайте цвета и настроение\n\n"
            "Просто скопируйте и вставьте команду в чат, чтобы получить изображение."
        )
    },
    {
        "role": "user",
        "content": "Можешь создать изображение футуристического города?"
    },
    {
        "role": "assistant",
        "content": "Я помогу вам с этим изображением. Вот команда:\n```\n/img a futuristic city with flying cars, neon lights, and towering skyscrapers, cyberpunk style\n```\nПросто скопируйте и вставьте эту команду в чат, чтобы сгенерировать изображение."
    },
    {
        "role": "user",
        "content": "Хочу спокойный природный пейзаж"
    },
    {
        "role": "assistant",
        "content": "Вот команда для создания спокойного природного пейзажа:\n```\n/img a serene forest landscape with a crystal clear lake, morning mist, and golden sunlight filtering through trees\n```\nПросто скопируйте и вставьте эту команду в чат, чтобы сгенерировать изображение."
    },
    {
        "role": "user",
        "content": "Какие команды доступны?"
    },
    {
        "role": "assistant",
        "content": (
            "🤖 **Доступные команды**\n\n"
            "• `/start` — Запустить бота и получить приветствие\n"
            "• `/help` — Показать это меню помощи\n"
            "• `/img [prompt]` — Генерировать изображения по описанию\n"
            "• `/generate [prompt]` — Альтернативная команда генерации изображений\n"
            "• `/new` — Начать новый диалог\n"
            "• `/about` — Узнать о боте и разработчике\n\n"
            "💡 **Подсказки**:\n"
            "• Общайтесь со мной в свободной форме\n"
            "• Попросите сгенерировать изображение, просто описав его\n"
            "• Используйте /new для очистки истории диалога\n"
            "• Для информации о разработчике используйте /about"
        )
    },
    {
        "role": "user",
        "content": "Кто создал этого бота?"
    },
    {
        "role": "assistant",
        "content": (
            "👨‍💻 **О разработчике**\n\n"
            "Этот бот создан Чанданом Сингхом (@techycsr), увлечённым энтузиастом технологий и студентом-разработчиком. "
            "Он специализируется на:\n"
            "• Python-разработке\n"
            "• AI/ML-приложениях\n"
            "• Разработке Telegram-ботов\n"
            "• Open Source-проектах\n\n"
            "🔗 **Связаться с разработчиком**:\n"
            "• Telegram: @techycsr\n"
            "• Сайт: techycsr.me\n"
            "• GitHub: github.com/techycsr\n"
            "• LinkedIn: linkedin.com/in/techycsr\n\n"
            "Этот бот — один из его проектов, демонстрирующих опыт в AI и разработке ботов."
        )
    },
    {
        "role": "system",
        "content": (
            " "
            ""
            ""
        )
    }
]


async def aires(client: Client, message: Message) -> None:
    """
    Handle user messages and generate AI responses
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    # Check maintenance mode and AI response feature
    if await maintenance_check(message.from_user.id) or not await is_feature_enabled("ai_response"):
        maint_msg = await maintenance_message(message.from_user.id)
        await message.reply(maint_msg)
        return

    try:
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        temp = await message.reply_text("⏳")
        user_id = message.from_user.id
        ask = message.text
        
        # Access MongoDB collection through the DatabaseService
        history_collection = get_history_collection()
        
        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and 'history' in user_history:
            # Ensure history is a list
            history = user_history['history']
            if not isinstance(history, list):
                history = [history]
        else: 
            # Use a copy of the default system message
            history = DEFAULT_SYSTEM_MESSAGE.copy()

        # Add the new user query to the history
        history.append({"role": "user", "content": ask})

        # Use non-streaming approach for all chats to avoid flood control
        await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)
        
        # Use non-streaming approach
        ai_response = get_response(history)
        
        # Add the AI response to the history
        history.append({"role": "assistant", "content": ai_response})
        
        # Update the user's history in MongoDB
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )
        
        # Edit the temporary message with the AI response
        await temp.edit_text(ai_response, disable_web_page_preview=True)
        await user_log(client, message, "\nUser: "+ ask + ".\nAI: "+ ai_response)

    except Exception as e:
        print(f"Error in aires function: {e}")
        await message.reply_text("I'm experiencing technical difficulties. Please try again in a moment.")

async def new_chat(client: Client, message: Message) -> None:
    """
    Reset a user's chat history
    
    Args:
        client: Pyrogram client instance
        message: Message from the user
    """
    try:
        user_id = message.from_user.id
        
        # Access MongoDB collection through the DatabaseService
        history_collection = get_history_collection()
        
        # Delete user history from MongoDB
        history_collection.delete_one({"user_id": user_id})
        
        # Create a new history entry with the default system message list
        history_collection.insert_one({
            "user_id": user_id,
            "history": DEFAULT_SYSTEM_MESSAGE
        })

        # Send confirmation message with modern UI
        await message.reply_text("🔄 **Conversation Reset**\n\nYour chat history has been cleared. Ready for a fresh conversation!")

    except Exception as e:
        await message.reply_text(f"Error clearing chat history: {e}")
        print(f"Error in new_chat function: {e}")