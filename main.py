import time
import random
import logging
import sys
import os # <-- ✨ إضافة جديدة

# استيراد المكونات الرئيسية من ملفات المشروع
import config
from database.database import engine, Base
from bot.instagram_client import InstagramClient
from bot.bot_logic import BotLogic

# --- ✨ تعديل إعدادات التسجيل ---
# إعداد المسار لملف السجل
LOG_FILE_PATH = os.path.join(config.BASE_DIR, "bot.log")

# إعداد نظام التسجيل الأساسي للكتابة إلى الملف وإلى الطرفية
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'), # <-- ✨ للكتابة في ملف
        logging.StreamHandler(sys.stdout)                  # <-- ✨ للعرض في الطرفية
    ]
)
# --- نهاية التعديل ---

def initialize_database():
    """
    تتأكد من إنشاء جميع الجداول في قاعدة البيانات بناءً على النماذج (Models).
    """
    logging.info("Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables are ready.")
    except Exception as e:
        logging.critical(f"FATAL: Could not initialize database: {e}")
        sys.exit(1)

def main():
    """
    الوظيفة الرئيسية لتشغيل البوت.
    """
    if not (config.IG_USERNAME and config.IG_PASSWORD):
        logging.critical("FATAL: Instagram username or password not set in .env file.")
        sys.exit(1)

    initialize_database()

    try:
        client = InstagramClient(config.IG_USERNAME, config.IG_PASSWORD)
        logic = BotLogic()

        logging.info("Bot is now running and listening for messages...")
        
        while True:
            try:
                unread_threads = client.get_unread_threads()
                for thread in unread_threads:
                    last_message = thread.messages[0]
                    
                    if not last_message.user_id == client.cl.user_id:
                        sender = next((user for user in thread.users if user.pk == last_message.user_id), None)
                        if sender:
                            logging.info(f"New message received from user: {sender.username} (ID: {sender.pk})")
                            logic.handle_message(last_message, sender, client)
                            client.mark_thread_as_read(thread.id)
                
                sleep_time = random.randint(15, 30)
                logging.debug(f"Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)

            except Exception as e:
                logging.error(f"An error occurred in the main loop: {e}", exc_info=True)
                time.sleep(60)

    except Exception as e:
        logging.critical(f"FATAL: Bot failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()