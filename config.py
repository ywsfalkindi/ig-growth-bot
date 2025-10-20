import os
from dotenv import load_dotenv

# --- المسار الأساسي للمشروع ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 

# يقوم هذا السطر بتحميل المتغيرات من ملف .env الموجود في المجلد الرئيسي
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- إعدادات انستجرام ---
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

# --- إعدادات تليجرام للإشعارات ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- إعدادات لوحة التحكم ---
# ✨ --- هذا هو السطر الجديد الذي أضفناه --- ✨
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# --- إعدادات قاعدة البيانات (مع المسار المطلق) ---
DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "bot_data.db")