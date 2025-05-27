from deep_translator import GoogleTranslator
from pymongo import MongoClient
from config import DATABASE_URL
import time
import asyncio
import re
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List, Tuple, Any, Set
from modules.lang_resources.translation_cache import (
    get_cached_translation,
    add_to_translation_cache,
    preload_all_caches,
    batch_cache_translations
)

# Initialize MongoDB client
mongo_client = MongoClient(DATABASE_URL)
db = mongo_client['aibotdb']
user_lang_collection = db['user_lang']
translation_cache = db['translation_cache']  # Keep for backward compatibility

# Thread pool for parallel processing of translations
_translation_executor = ThreadPoolExecutor(max_workers=4)

# Language code mapping (deep_translator uses some different codes than our system)
LANGUAGE_CODE_MAP = {
    'zh': 'zh-CN',  # Convert our 'zh' code to what deep_translator expects
    'ar': 'ar',
    'fr': 'fr',
    'ru': 'ru',
    'hi': 'hi',
    'en': 'en'
}

# Simple in-memory cache for translations to avoid repeated API calls
_translation_cache: Dict[str, str] = {}
_mention_cache: Dict[str, Dict[str, str]] = {}  # Special cache for user mentions

# Maximum retries for translation attempts
MAX_RETRIES = 3

# Special tokens that should not be translated
SPECIAL_TOKENS = ['@', 'http://', 'https://', '.com', '.org', '.net', '(', ')', '[', ']']

# Preload translation caches during module initialization
try:
    preload_all_caches()
except Exception as e:
    print(f"Error preloading translation caches: {e}")

def get_user_language(user_id):
    """Get user's preferred language from database"""
    user_lang_doc = user_lang_collection.find_one({"user_id": user_id})
    if user_lang_doc:
        return user_lang_doc['language']
    return 'ru'  # Default to English if not set

def get_target_language_code(lang):
    """Convert our language code to deep_translator format if needed"""
    return LANGUAGE_CODE_MAP.get(lang, lang)

def extract_placeholders(text: str) -> List[Tuple[str, str]]:
    """
    Extract placeholders from text like {user_id}, {mention}, etc.
    Returns a list of (placeholder, placeholder_text) tuples.
    """
    placeholder_pattern = r'\{([^{}]+)\}'
    placeholders = re.findall(placeholder_pattern, text)
    return [(p, '{' + p + '}') for p in placeholders]

def translate_sync(text, lang):
    return text

async def async_translate_to_lang(text, user_id=None, lang=None) -> str:
    return text

def _translate_with_retries(text, target_lang):
    """Helper function for translating with retries in a thread"""
    for attempt in range(MAX_RETRIES):
        try:
            translator = GoogleTranslator(source='en', target=target_lang)
            result = translator.translate(text)
            if result:
                return result
        except Exception as e:
            print(f"Translation attempt {attempt + 1} failed: {e}")
            time.sleep(0.5)  # Small delay before retry
    
    return text  # Return original text if all attempts fail

# Legacy function for backward compatibility
def translate_to_lang(text, user_id=None, lang=None):
    return text

# Deprecated - Use async_translate_to_lang instead
async def async_translate(text, user_id=None, lang=None):
    return text

# Batch translation function for efficiently translating multiple strings at once
async def batch_translate(texts, user_id=None, lang=None):
    """
    Translate multiple texts at once.
    Returns a list of translated texts in the same order.
    """
    if not texts:
        return []
        
    # Get language if not provided
    if lang is None and user_id is not None:
        lang = get_user_language(user_id)
    
    # No need to translate if target is English
    if lang == 'en':
        return texts.copy()  # Return copy of original texts
    
    # First check cache for all texts
    cache_hits = batch_cache_translations(texts, lang)
    
    # If all texts were in cache, return immediately
    if len(cache_hits) == len(texts):
        return [cache_hits[text] for text in texts]
    
    # For texts not in cache, translate them in parallel
    missing_texts = [text for text in texts if text not in cache_hits]
    tasks = []
    
    # Create async tasks for all missing translations
    for text in missing_texts:
        tasks.append(asyncio.create_task(async_translate_to_lang(text, user_id, lang)))
    
    # Wait for all translations to complete
    missing_translations = await asyncio.gather(*tasks)
    
    # Combine cache hits with new translations in original order
    results = []
    missing_idx = 0
    
    for text in texts:
        if text in cache_hits:
            results.append(cache_hits[text])
        else:
            results.append(missing_translations[missing_idx])
            missing_idx += 1
            
    return results

# Optimized function for translating UI elements like buttons
async def translate_ui_element(text, user_id=None, lang=None):
    """
    Optimized translation for UI elements (buttons, labels)
    Uses multi-level caching with special handling for short texts
    """
    if not text or text.isspace():
        return text
        
    # Get language if not provided
    if lang is None and user_id is not None:
        lang = get_user_language(user_id)
        
    # Skip translation for English
    if lang == 'en':
        return text
        
    # Create cache key
    cache_key = f"ui_{text}_{lang}"
    
    # Check memory cache first (fastest)
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]
        
    # Use standard translation
    translated = await async_translate_to_lang(text, user_id, lang)
    
    # Cache result
    _translation_cache[cache_key] = translated
    
    return translated

# Add this function to handle mentions properly

def preserve_mention(text, mention):
    """
    Special helper to preserve user mentions in any language
    Returns the text with the mention properly encoded for preservation
    """
    if not mention or not text:
        return text
        
    # Use a special token format that won't be translated
    mention_token = f"__MENTION_TOKEN_{hash(mention) & 0xFFFFFF}__"
    
    # Replace the mention in the text with the token
    tokenized_text = text.replace(mention, mention_token)
    
    return tokenized_text, mention_token, mention

async def format_with_mention(text, mention, user_id=None, lang=None):
    """
    Format text with mentions safely across all languages
    This ensures mentions are preserved during translation
    """
    if not mention or not text:
        return text
        
    # If English, just do normal formatting
    if lang == 'en' or (lang is None and user_id is not None and get_user_language(user_id) == 'en'):
        return text.replace("{mention}", mention)
    
    # First, preserve the mention by tokenizing it
    tokenized_text, mention_token, _ = preserve_mention(text, "{mention}")
    
    # Translate the tokenized text
    translated = await async_translate_to_lang(tokenized_text, user_id, lang)
    
    # Replace the token back with the actual mention
    result = translated.replace(mention_token, mention)
    
    return result

# Create a translation object for testing
if __name__ == "__main__":
    pass