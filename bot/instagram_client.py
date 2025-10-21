import logging
import os # <-- إضافة جديدة
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from config import BASE_DIR # <-- إضافة جديدة

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- ✨ تعديل: تعريف مسار ملف الجلسة ---
SESSION_FILE = os.path.join(BASE_DIR, "session.json")
# --- نهاية التعديل ---

class InstagramClient:
    def __init__(self, username, password):
        self.cl = Client()
        self.username = username
        self.password = password
        self.login()

    def login(self):
        """
        تسجيل الدخول إلى حساب انستجرام.
        --- ✨ تم تعديل هذه الدالة بالكامل ✨ ---
        """
        try:
            if os.path.exists(SESSION_FILE):
                logging.info("Found existing session file. Attempting to load session...")
                self.cl.load_settings(SESSION_FILE)
                self.cl.login(self.username, self.password) # التحقق من الجلسة
                logging.info(f"Successfully logged in as {self.username} using saved session.")
            else:
                logging.info(f"No session file found. Attempting a fresh login as {self.username}...")
                self.cl.login(self.username, self.password)
                self.cl.dump_settings(SESSION_FILE) # حفظ الجلسة الجديدة
                logging.info(f"Successfully logged in and saved session to {SESSION_FILE}.")
                
        except LoginRequired:
            logging.warning("Session expired or invalid. Attempting a fresh login...")
            try:
                self.cl.login(self.username, self.password)
                self.cl.dump_settings(SESSION_FILE) # حفظ الجلسة الجديدة
                logging.info(f"Successfully logged in and saved new session to {SESSION_FILE}.")
            except Exception as e:
                logging.error(f"Fresh login failed after session load failed: {e}")
                raise
        except Exception as e:
            logging.error(f"An unexpected error occurred during login: {e}")
            raise
    
    # ... (باقي الدوال كما هي) ...

    def mark_thread_as_read(self, thread_id: str):
        """
        تحدد محادثة كاملة على أنها مقروءة.
        """
        try:
            # --- ✨✨ لا تنس إصلاح الخطأ المطبعي من المرة السابقة! ✨✨ ---
            self.cl.direct_thread_mark_as_read(thread_id)
        except Exception as e:
            logging.error(f"Could not mark thread {thread_id} as read: {e}")