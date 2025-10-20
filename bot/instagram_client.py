import logging
from instagrapi import Client
from instagrapi.exceptions import LoginRequired

# إعداد نظام تسجيل بسيط لتتبع الأحداث والأخطاء
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InstagramClient:
    """
    هذه الفئة مسؤولة عن كل التفاعلات المباشرة مع واجهة انستجرام
    باستخدام مكتبة instagrapi.
    """
    def __init__(self, username, password):
        self.cl = Client()
        self.username = username
        self.password = password
        self.login()

    def login(self):
        """
        تسجيل الدخول إلى حساب انستجرام.
        """
        try:
            logging.info(f"Attempting to log in as {self.username}...")
            self.cl.login(self.username, self.password)
            logging.info(f"Successfully logged in as {self.username}.")
        except LoginRequired:
            logging.error("Login failed. Please check your username and password.")
            raise  # نوقف البرنامج إذا فشل تسجيل الدخول
        except Exception as e:
            logging.error(f"An unexpected error occurred during login: {e}")
            raise

    def get_unread_threads(self):
        """
        تجلب المحادثات غير المقروءة من صندوق الوارد الرئيسي فقط.
        """
        try:
            # سنقوم فقط بجلب الرسائل من صندوق الوارد الرئيسي
            inbox_threads = self.cl.direct_threads(amount=20, selected_filter='unread')
            return inbox_threads
        except Exception as e:
            logging.error(f"Could not fetch direct threads: {e}")
            return []

    def send_direct_message(self, user_id: str, text: str):
        """
        ترسل رسالة نصية مباشرة إلى مستخدم معين.
        """
        try:
            self.cl.direct_send(text, user_ids=[user_id])
            logging.info(f"Message sent to user_id: {user_id}")
        except Exception as e:
            logging.error(f"Could not send message to user_id {user_id}: {e}")

    def mark_thread_as_read(self, thread_id: str):
        """
        تحدد محادثة كاملة على أنها مقروءة.
        """
        try:
            self.cl.direct_mark_as_read(thread_id)
        except Exception as e:
            logging.error(f"Could not mark thread {thread_id} as read: {e}")