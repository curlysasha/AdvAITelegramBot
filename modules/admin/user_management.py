"""
Admin User Management Module - Manage and view bot users

Provides functionality to view user lists, user details, and perform
administrative actions on users.
"""

import datetime
from typing import Dict, Any, List, Tuple
import logging
import asyncio # For asyncio.to_thread
from aiogram import Bot, types # For Aiogram types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton # For Aiogram
from modules.core.database import get_user_collection
from modules.ui.theme import Theme, Colors
from modules.lang import async_translate_to_lang
from config import ADMINS

# Configure logger
logger = logging.getLogger(__name__)

# User list cache
_user_cache = {}
_user_cache_time = 0
CACHE_VALIDITY = 180  # 3 minutes

# Additional user categories
USER_CATEGORIES = {
    "all": "All Users",
    "recent": "Recently Active",
    "active": "Most Active Users",
    "new": "New Users",
    "inactive": "Inactive Users",
    "groups": "Groups"
}

async def get_users_list(limit: int = 10, offset: int = 0, filter_type: str = "recent") -> List[Dict[str, Any]]:
    """
    Get a list of users with pagination and improved categorization
    
    Args:
        limit: Number of users to return
        offset: Pagination offset
        filter_type: Filter type ('all', 'recent', 'active', 'new', 'inactive', 'groups')
        
    Returns:
        List of user dictionaries
    """
    global _user_cache, _user_cache_time
    
    # Cache key based on parameters
    cache_key = f"{filter_type}_{offset}_{limit}"
    
    # Force refresh for most accurate data
    _user_cache = {}
    _user_cache_time = 0
    
    # Return from cache if valid
    current_time = datetime.datetime.now().timestamp()
    if cache_key in _user_cache and current_time - _user_cache_time < CACHE_VALIDITY:
        return _user_cache[cache_key]
    
    # Get user collection
    user_collection = get_user_collection()
    
    # Define time thresholds
    one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    inactive_threshold = datetime.datetime.now() - datetime.timedelta(days=60)
    
    # Prepare filter and sort based on filter_type
    query_filter = {}
    sort_config = []
    
    if filter_type == "all":
        # All users (excluding groups)
        query_filter = {'is_group': {'$ne': True}}
        sort_config = [('last_activity', -1)]
    
    elif filter_type == "active":
        # Most active users - recent and frequent activity
        query_filter = {
            'is_group': {'$ne': True},
            'last_activity': {'$gt': seven_days_ago}
        }
        # Sort by activity count if available, otherwise last_activity
        sort_config = [
            ('activity_count', -1),  # Primary sort: activity count descending
            ('last_activity', -1)    # Secondary sort: last activity descending
        ]
    
    elif filter_type == "new":
        # New users - joined recently
        query_filter = {
            'is_group': {'$ne': True},
            '$or': [
                {'created_at': {'$gt': thirty_days_ago}},
                {'join_date': {'$gt': thirty_days_ago}}
            ]
        }
        # Sort by creation/join date
        sort_config = [('created_at', -1), ('join_date', -1)]
    
    elif filter_type == "inactive":
        # Inactive users - no activity in last 60 days
        query_filter = {
            'is_group': {'$ne': True},
            'last_activity': {'$lt': inactive_threshold}
        }
        sort_config = [('last_activity', -1)]
    
    elif filter_type == "groups":
        # Only groups
        query_filter = {'is_group': True}
        sort_config = [('member_count', -1), ('last_activity', -1)]
    
    else:  # "recent" default
        # Recently active users
        query_filter = {
            'is_group': {'$ne': True},
            'last_activity': {'$gt': thirty_days_ago}
        }
        sort_config = [('last_activity', -1)]
    
    try:
        # Query users with proper error handling, wrapped for async
        def _find_users_sync():
            if not sort_config:
                # Default sort if none specified
                return list(user_collection.find(
                    query_filter,
                    skip=offset,
                    limit=limit
                ))
            else:
                return list(user_collection.find(
                    query_filter,
                    sort=sort_config,
                    skip=offset,
                    limit=limit
                ))
        users = await asyncio.to_thread(_find_users_sync)
        
        # Enhance user data with additional info if available
        for user in users:
            # Calculate relative activity metric
            if 'activity_count' not in user and 'message_count' in user:
                user['activity_count'] = user['message_count']
            
            # Set user type
            if user.get('is_group', False):
                user['user_type'] = 'Group'
            else:
                user['user_type'] = 'Regular'
                
            # Calculate days since last activity
            last_activity = user.get('last_activity')
            if isinstance(last_activity, datetime.datetime):
                delta = datetime.datetime.now() - last_activity
                user['days_since_activity'] = delta.days
        
        # Cache the result
        _user_cache[cache_key] = users
        _user_cache_time = current_time
        
        return users
        
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        return []

async def get_user_count(filter_type: str = "all") -> int:
    """
    Get count of users based on filter with improved categorization
    
    Args:
        filter_type: Filter type ('all', 'active_24h', 'active_7d', 'new_24h', 'inactive', 'groups')
        
    Returns:
        User count
    """
    # Get user collection
    user_collection = get_user_collection()
    
    # Define time thresholds
    one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    inactive_threshold = datetime.datetime.now() - datetime.timedelta(days=60)
    
    try:
        # Create filter based on filter_type
        user_filter_dict = {} # Renamed to avoid conflict with filter_type parameter
        if filter_type == "active_24h":
            user_filter_dict = {'is_group': {'$ne': True}, 'last_activity': {'$gt': one_day_ago}}
        elif filter_type == "active_7d":
            user_filter_dict = {'is_group': {'$ne': True}, 'last_activity': {'$gt': seven_days_ago}}
        elif filter_type == "new_24h":
            user_filter_dict = {'is_group': {'$ne': True}, '$or': [{'created_at': {'$gt': one_day_ago}}, {'join_date': {'$gt': one_day_ago}}]}
        elif filter_type == "inactive":
            user_filter_dict = {'is_group': {'$ne': True}, 'last_activity': {'$lt': inactive_threshold}}
        elif filter_type == "groups":
            user_filter_dict = {'is_group': True}
        else:  # "all" default - only count users, not groups
            user_filter_dict = {'is_group': {'$ne': True}}
        
        # Count users, wrapped for async
        def _count_users_sync():
            return user_collection.count_documents(user_filter_dict)
        return await asyncio.to_thread(_count_users_sync)
    except Exception as e:
        logger.error(f"Error counting users: {str(e)}")
        return 0

async def handle_user_management(bot: Bot, callback_query: types.CallbackQuery, page: int = 0, filter_type: str = "recent"): # Aiogram types
    """Handle user management panel with improved categorization"""
    user_id = callback_query.from_user.id # Use callback_query
    
    # Check if user is admin
    if user_id not in ADMINS: # ADMINS should be list of int
        await callback_query.answer("You don't have permission to access user management", show_alert=True) # Use callback_query
        return
    
    # Show loading message
    loading_message = await async_translate_to_lang("⏳ Loading user management...", user_id)
    try:
        await callback_query.message.edit_text( # Use edit_text
            text=loading_message,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error showing loading message: {str(e)}")
        await callback_query.answer("Loading user management...", show_alert=True) # Use callback_query
        return
    
    try:
        # Get users with pagination (10 per page)
        limit = 10
        offset = page * limit
        users = await get_users_list(limit=limit, offset=offset, filter_type=filter_type)
        
        # Get user counts
        total_users = await get_user_count("all")
        active_24h = await get_user_count("active_24h")
        active_7d = await get_user_count("active_7d")
        new_24h = await get_user_count("new_24h")
        inactive_users = await get_user_count("inactive")
        group_count = await get_user_count("groups")
        
        # Translate UI elements
        title = await async_translate_to_lang("👥 User Management", user_id)
        back_text = await async_translate_to_lang("🔙 Back", user_id)
        next_text = await async_translate_to_lang("Next ➡️", user_id)
        prev_text = await async_translate_to_lang("⬅️ Previous", user_id)
        refresh_text = await async_translate_to_lang("🔄 Refresh", user_id)
        
        # Create message text
        message = f"**{title}**\n\n"
        message += f"📊 **User Statistics:**\n"
        message += f"• Total Users: {total_users:,}\n"
        message += f"• Active Today: {active_24h:,}\n"
        message += f"• Active (7d): {active_7d:,}\n"
        message += f"• New Today: {new_24h:,}\n"
        message += f"• Groups: {group_count:,}\n\n"
        
        # User list header
        list_title = await async_translate_to_lang(USER_CATEGORIES.get(filter_type, "Users"), user_id)
        message += f"**{list_title}** (Page {page+1}):\n"
        
        # Format user list with improved details
        if users:
            for i, user in enumerate(users, 1):
                # Extract user info safely
                user_name = user.get('name', 'Unknown')
                username = user.get('username', 'No username')
                user_id_str = str(user.get('user_id', 'No ID'))
                
                # User type indicator
                user_type = user.get('user_type', 'Regular')
                type_indicator = "👤"
                if user_type == 'Group':
                    type_indicator = "👥"
                
                # Metadata line
                meta_line = []
                
                # Time info formatting
                last_active = user.get('last_activity')
                if isinstance(last_active, datetime.datetime):
                    # Show relative time if recent
                    days_ago = user.get('days_since_activity', 0)
                    if days_ago == 0:
                        meta_line.append("Today")
                    elif days_ago == 1:
                        meta_line.append("Yesterday")
                    else:
                        meta_line.append(f"{days_ago}d ago")
                else:
                    meta_line.append("Unknown")
                
                # Activity count if available
                if 'activity_count' in user and user['activity_count']:
                    meta_line.append(f"{user['activity_count']} msgs")
                elif 'message_count' in user and user['message_count']:
                    meta_line.append(f"{user['message_count']} msgs")
                
                # Group members if it's a group
                if user.get('is_group') and 'member_count' in user:
                    meta_line.append(f"{user['member_count']} members")
                
                # Join date for new users
                if filter_type == "new" and 'created_at' in user:
                    join_date = user['created_at']
                    if isinstance(join_date, datetime.datetime):
                        meta_line.append(f"Joined: {join_date.strftime('%Y-%m-%d')}")
                
                # Add user entry to message
                message += f"{i+offset}. {type_indicator} **{user_name}** (@{username})\n"
                message += f"   ID: `{user_id_str}` • {' • '.join(meta_line)}\n"
        else:
            no_users_text = await async_translate_to_lang("No users found", user_id)
            message += f"*{no_users_text}*\n"
        
        # Create keyboard - ensure proper structure
        keyboard = []
        
        # Category filter buttons (2 rows)
        cat_row1 = []
        cat_row1.append(InlineKeyboardButton(
            f"{'✅' if filter_type == 'all' else ''} All",
            callback_data="admin_users_filter_all_0"
        ))
        cat_row1.append(InlineKeyboardButton(
            f"{'✅' if filter_type == 'recent' else ''} Recent",
            callback_data="admin_users_filter_recent_0"
        ))
        cat_row1.append(InlineKeyboardButton(
            f"{'✅' if filter_type == 'active' else ''} Active",
            callback_data="admin_users_filter_active_0"
        ))
        keyboard.append(cat_row1)
        
        cat_row2 = []
        cat_row2.append(InlineKeyboardButton(
            f"{'✅' if filter_type == 'new' else ''} New",
            callback_data="admin_users_filter_new_0"
        ))
        cat_row2.append(InlineKeyboardButton(
            f"{'✅' if filter_type == 'groups' else ''} Groups",
            callback_data="admin_users_filter_groups_0"
        ))
        cat_row2.append(InlineKeyboardButton(
            f"{'✅' if filter_type == 'inactive' else ''} Inactive",
            callback_data="admin_users_filter_inactive_0"
        ))
        keyboard.append(cat_row2)
        
        # Navigation buttons
        nav_row = []
        if page > 0:
            nav_row.append(Theme.primary_button(
                prev_text, f"admin_users_filter_{filter_type}_{page-1}"
            ))
        
        if len(users) == limit:  # More pages available
            nav_row.append(Theme.primary_button(
                next_text, f"admin_users_filter_{filter_type}_{page+1}"
            ))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Refresh and back buttons
        action_row = []
        action_row.append(Theme.primary_button(refresh_text, f"admin_users_filter_{filter_type}_{page}"))
        action_row.append(Theme.back_button("admin_panel"))
        keyboard.append(action_row)
        
        # Show user list
        await callback_query.message.edit_text( # Use edit_text
            text=message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), # Pass inline_keyboard
            parse_mode="Markdown" # Ensure Markdown is parsed for bolding etc.
        )
    except Exception as e:
        logger.error(f"Error in user management panel: {str(e)}")
        await callback_query.answer(f"Error: {str(e)[:150]}...", show_alert=True) # Use callback_query, longer alert
        # Try to recover by going back to admin panel
        # show_admin_panel_handler is the new name in maintenance.py
        try:
            from modules.maintenance import show_admin_panel_handler 
            await show_admin_panel_handler(callback_query, bot) # Pass Aiogram types
        except Exception as e_recovery:
            logger.error(f"Error recovering to admin panel: {e_recovery}")
            await callback_query.answer("Failed to load user management. Try again later.", show_alert=True)

# Update __init__.py to export this function 