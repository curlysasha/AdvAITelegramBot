# This file makes the 'image' directory a Python package.

# Optionally, expose key functions or routers from this package:
from .img_to_text import img_to_text_router
from .image_generation import image_gen_router
# For inline_image_generation, handle_inline_query is often registered directly to the main dispatcher
# but if it were router-based, it would be imported here too.
# from .inline_image_generation import inline_image_router 
from .handlers import image_message_router

__all__ = [
    "img_to_text_router",
    "image_gen_router",
    "image_message_router", 
    # "inline_image_router", # if created
]
