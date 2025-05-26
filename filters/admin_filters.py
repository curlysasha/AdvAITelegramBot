from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union

from config import ADMINS # Assuming ADMINS is a list of integer admin IDs

class IsAdminFilter(Filter):
    """
    Custom filter to check if the user is an admin.
    ADMINS should be a list of user IDs.
    """
    async def __call__(self, update: Union[Message, CallbackQuery]) -> bool:
        user_id = update.from_user.id
        # Ensure ADMINS contains integers if user_id is an integer
        # Convert ADMINS elements to int if they are strings from environment variables
        try:
            admin_ids_int = {int(admin_id) for admin_id in ADMINS}
            return user_id in admin_ids_int
        except ValueError:
            # Handle case where ADMINS might not be all integers
            # You might want to log this error
            print(f"Warning: ADMINS list in config contains non-integer values or is improperly formatted.")
            return False

# To make it available for import in __init__.py
__all__ = ["IsAdminFilter"]
