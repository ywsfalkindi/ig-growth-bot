import logging
import os
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
# --- ✨ إضافة جديدة: نحتاج هذا الكلاس للأزرار ---
from instagrapi.types import QuickReply 
from config import BASE_DIR

# ... (إعدادات الـ logging وملف الجلسة) ...
SESSION_FILE = os.path.join(BASE_DIR, "session.json")


class InstagramClient:  # <--- المستوى 0 (لا توجد مسافة بادئة)

    def __init__(self, username, password):  # <--- المستوى 1 (مسافة بادئة واحدة)
        self.cl = Client()
        self.username = username
        self.password = password
        self.login()

    def login(self):  # <--- المستوى 1 (بنفس مستوى __init__)
        """
        تسجيل الدخول إلى حساب انستجرام.
        """
        try:  # <--- المستوى 2 (مسافة بادئة داخل login)
            if os.path.exists(SESSION_FILE):
                logging.info("Found existing session file...")
                self.cl.load_settings(SESSION_FILE)
                self.cl.login(self.username, self.password)
                logging.info(f"Successfully logged in as {self.username} using saved session.")
            else:
                logging.info(f"No session file found...")
                self.cl.login(self.username, self.password)
                self.cl.dump_settings(SESSION_FILE)
                logging.info(f"Successfully logged in and saved session.")
        # ... (باقي كود دالة login) ...
        except Exception as e:
            logging.error(f"An unexpected error occurred during login: {e}")
            raise

    # --- 👇👇 هذا هو المكان الصحيح للدالة 👇👇 ---
    
    def get_unread_threads(self):  # <--- المستوى 1 (يجب أن تكون بمحاذاة login)
        """
        تجلب المحادثات غير المقروءة من صندوق الوارد الرئيسي فقط.
        """
        try:  # <--- المستوى 2 (مسافة بادئة داخل الدالة)
            inbox_threads = self.cl.direct_threads(amount=20, selected_filter='unread')
            return inbox_threads
        except Exception as e:
            logging.error(f"Could not fetch direct threads: {e}")
            return []

    def send_direct_message(self, user_id: str, text: str):  # <--- المستوى 1
        """
        ترسل رسالة نصية مباشرة إلى مستخدم معين.
        """
        try:  # <--- المستوى 2
            self.cl.direct_send(text, user_ids=[user_id])
            logging.info(f"Message sent to user_id: {user_id}")
        except Exception as e:
            logging.error(f"Could not send message to user_id {user_id}: {e}")

    # --- ✨✨✨ (تم تصحيح هذا الكود) ✨✨✨ ---
    def send_direct_message_with_quick_replies(self, user_id: str, text: str, replies: list):
        """
        ترسل رسالة نصية مع أزرار رد سريع.
        Replies should be a list of tuples: [("Button Title", "payload_data"), ...]
        """
        try:
            # --- ✨ التصحيح هنا: يجب تحويل القائمة إلى كائنات QuickReply ---
            quick_replies_list = [QuickReply(title=title, payload=payload) for title, payload in replies]
            
            self.cl.direct_send(text, user_ids=[user_id], quick_replies=quick_replies_list)
            logging.info(f"Message with quick replies sent to user_id: {user_id}")
        except Exception as e:
            logging.error(f"Could not send quick replies to user_id {user_id}: {e}")
    # --- نهاية التصحيح ---

    def mark_thread_as_read(self, thread_id: str):  # <--- المستوى 1
        """
        تحدد محادثة كاملة على أنها مقروءة.
        """
        try:  # <--- المستوى 2
            # --- ✨ التصحيح هنا: كان الاسم خطأ ---
            self.cl.direct_mark_as_read(thread_id)
        except Exception as e:
            logging.error(f"Could not mark thread {thread_id} as read: {e}")