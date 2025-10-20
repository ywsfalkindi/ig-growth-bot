import time
import random
import logging
import sys

# استيراد المكونات الرئيسية من ملفات المشروع
import config
from database.database import engine, Base
from bot.instagram_client import InstagramClient
from bot.bot_logic import BotLogic

# إعداد نظام التسجيل الأساسي
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
                        # --- التعديل هنا ---
                        # نجد معلومات المرسل من قائمة المستخدمين في المحادثة
                        sender = next((user for user in thread.users if user.pk == last_message.user_id), None)
                        if sender:
                            logging.info(f"New message received from user: {sender.username}")
                            # نمرر معلومات المرسل إلى منطق البوت
                            logic.handle_message(last_message, sender, client)
                            client.mark_thread_as_read(thread.id)
                
                sleep_time = random.randint(15, 30)
                time.sleep(sleep_time)

            except Exception as e:
                logging.error(f"An error occurred in the main loop: {e}")
                time.sleep(60)

    except Exception as e:
        logging.critical(f"FATAL: Bot failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()