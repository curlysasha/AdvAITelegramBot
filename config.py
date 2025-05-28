import os
import sys
import time
import datetime
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

# Bot start time for uptime tracking
START_TIME = time.time()

#Preferences os >> env >> default

API_KEY = os.environ.get('API_ID') or os.getenv('API_ID') or "API_KEY"
API_HASH = os.environ.get('API_HASH') or os.getenv("API_HASH")   or "API_HASH"
BOT_TOKEN = os.environ.get('BOT_TOKEN') or os.getenv("BOT_TOKEN") or   "BOT_TOKEN"
ADMINS = os.environ.get('ADMINS') or os.getenv('ADMINS') or os.environ.get('ADMIN_IDS') or os.getenv('ADMIN_IDS') or "123456789"
ADMINS = [x.strip() for x in ADMINS.split(",") if x.strip()]
OWNER_ID = os.environ.get('OWNER_ID') or os.getenv('OWNER_ID') or "123456789" # Owner ID
if str(OWNER_ID) not in ADMINS:
    ADMINS.append(str(OWNER_ID))
LOG_CHANNEL = os.environ.get('LOG_CHANNEL') or os.getenv("LOG_CHANNEL") or "advchatgptlogs" # Log Channel username preferance
DATABASE_URL=os.environ.get('DATABASE_URL') or os.getenv("DATABASE_URL") or "DATABASE_URL"
BING_COOKIE = os.environ.get('BING_COOKIE') or os.getenv("BING_COOKIE") or "BING_COOKIE"
OCR_KEY = os.environ.get('OCR_KEY') or os.getenv("OCR_KEY") or "OCR_KEY"


#check if all ids are int or not
for x in ADMINS:
    if not str(x).isdigit():
        sys.exit("Please enter a valid integer ID value, Check your ADMINS list")

ADMINS = list(map(int, ADMINS))
OWNER_ID = int(OWNER_ID)
BOT_NAME = os.environ.get('BOT_NAME') or os.getenv("BOT_NAME") or "Adance AI ChatBot"

