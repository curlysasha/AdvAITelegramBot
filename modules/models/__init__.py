# This file makes the 'models' directory a Python package.

from .ai_res import aires, new_chat_utility, DEFAULT_SYSTEM_MESSAGE, get_response_from_model, get_streaming_response_from_model
from .inline_ai_response import handle_inline_ai_query, get_inline_ai_cleanup_scheduler_task_coro
from .handlers import ai_models_router
from .image_service import ImageService

__all__ = [
    "aires",
    "new_chat_utility", # Renamed from new_chat to avoid conflict if imported directly
    "DEFAULT_SYSTEM_MESSAGE",
    "get_response_from_model", # Renamed from get_response
    "get_streaming_response_from_model", # Renamed from get_streaming_response
    "handle_inline_ai_query", 
    "get_inline_ai_cleanup_scheduler_task_coro", # For run.py
    "ai_models_router",
    "ImageService",
]
