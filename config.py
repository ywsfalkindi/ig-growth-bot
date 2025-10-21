# ywsfalkindi/ig-growth-bot/ig-growth-bot-1f127715a447e44d35648cc8be36c13d5a81d53b/config.py
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
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


# --- ✨✨✨ تعديل لإعدادات قاعدة البيانات (متوافق مع Render PostgreSQL) ✨✨✨ ---

# Render ستقوم بتوفير متغير بيئة يسمى DATABASE_URL تلقائيًا
# عند ربط قاعدة البيانات بالخدمات.
# إذا لم تجده (أي أننا نشغل الكود محلياً)، سنستخدم ملف SQLite المحلي كالمعتاد.
IS_ON_RENDER = os.getenv('RENDER') == 'true'

if IS_ON_RENDER:
    # على سيرفر Render، استخدم الرابط الذي يوفره السيرفر
    DATABASE_URL = os.getenv("DATABASE_URL")
    print("Running on Render. Using PostgreSQL.")
else:
    # على الجهاز المحلي، استخدم ملف SQLite
    DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "bot_data.db")
    print(f"Running locally. Using local SQLite DB.")

# --- نهاية التعديل ---