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


# --- ✨✨✨ تعديل لإعدادات قاعدة البيانات (متوافق مع Render) ✨✨✨ ---

# هذا هو المسار الذي قمت بإعداده في Render
RENDER_DISK_MOUNT_PATH = "/var/data" 
# سنضع قاعدة البيانات مباشرة في هذا المسار
DB_FILE_PATH = os.path.join(RENDER_DISK_MOUNT_PATH, "bot_data.db") 

# تحقق مما إذا كنا نعمل على Render (عن طريق وجود متغير RENDER)
IS_ON_RENDER = os.getenv('RENDER') == 'true'

if IS_ON_RENDER:
    # إذا كنا على Render، استخدم المسار الثابت في الـ Disk
    # لا نحتاج لإنشاء مجلدات، لأن /var/data موجود ومضمون من Render
    DATABASE_URL = "sqlite:///" + DB_FILE_PATH
    print(f"Running on Render. Using Persistent Disk DB: {DATABASE_URL}")
else:
    # إذا كنا على الجهاز المحلي، استخدم المسار القديم
    DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "bot_data.db")
    print(f"Running locally. Using local DB: {DATABASE_URL}")

# --- نهاية التعديل ---