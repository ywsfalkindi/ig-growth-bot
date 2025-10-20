import os
from dotenv import load_dotenv

# يقوم هذا السطر بتحميل المتغيرات من ملف .env إلى بيئة التشغيل
load_dotenv()

# --- إعدادات انستجرام ---
# نقوم بقراءة اسم المستخدم وكلمة المرور من المتغيرات التي تم تحميلها
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

# --- إعدادات تليجرام للإشعارات ---
# نقوم بقراءة توكن البوت ومعرف الدردشة الخاص بك
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- إعدادات قاعدة البيانات ---
# نقوم بقراءة رابط الاتصال بقاعدة البيانات
DATABASE_URL = os.getenv("DATABASE_URL")