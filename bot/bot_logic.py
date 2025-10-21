# bot/bot_logic.py
import logging
import telegram
import random
import string
import json
import os
from datetime import date, timedelta

from database.database import SessionLocal
# --- ✨ تعديل: إضافة Achievement ---
from database.models import User, Code, Order, PointLog, Achievement
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BASE_DIR

LEVELS = {1: "مبتدئ 🥉", 2: "نشيط 🥈", 3: "محترف 🥇", 4: "خبير 🎖️", 5: "أسطورة ✨"}
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

def load_settings():
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

class BotLogic:
    def __init__(self):
        self.db = SessionLocal()
        self.user_state = {}
        self.settings = load_settings()
        self.messages = self.settings.get("MESSAGES", {})

    def _add_points(self, user, points, reason):
        user.points += points
        log = PointLog(user_id=user.id, points_change=points, reason=reason)
        self.db.add(log)
    
    def handle_message(self, message, sender, client):
        self.settings = load_settings()
        self.messages = self.settings.get("MESSAGES", {})
        if self.settings.get("BOT_PAUSED", False):
            return

        user_id = str(sender.pk)
        text = message.text.lower().strip()
        
        # --- ✨ تعديل: استقبال المستخدم الجديد ---
        user, is_new_user = self._get_or_create_user(sender)

        if is_new_user:
            welcome_msg = self.messages.get("WELCOME_MESSAGE", 
                "👋 أهلاً بك يا {username} في بوت تجميع النقاط!\n\n"
                "أكمل المهام، اجمع النقاط، واستبدلها بمتابعين.\n\n"
                "🎁 إذا كان لديك كود دعوة من صديق (من 6 أحرف)، أرسله الآن لتحصل أنت وهو على هدية!")
            client.send_direct_message(user_id, welcome_msg.format(username=sender.full_name))
            # لا نوقف التنفيذ، للسماح بمعالجة كود الدعوة لو أرسله مباشرة
        # --- نهاية التعديل ---

        if user.is_banned:
            client.send_direct_message(user_id, self.messages.get("USER_BANNED_MESSAGE", "أنت محظور."))
            return
        
        if user.tasks_completed == 0 and len(text) == 6:
            self._handle_referral_code(user, text, client)

        daily_bonus_message = ""
        
        if self.user_state.get(user_id) == "awaiting_username":
            self._create_order(user, text, client)
            return

        # --- ✨ تعديل: إضافة فهم اللغة الطبيعية ---
        if text == "1" or "مهمة" in text or "task" in text:
            client.send_direct_message(user_id, self.messages.get("TASK_MESSAGE"))
        elif text == "2" or "استبدال" in text or "redeem" in text or "متابعين" in text:
            self._initiate_redemption(user_id, user, client)
        elif text == "3" or "صندوق" in text or "mystery" in text or "حظ" in text:
            self._play_mystery_box(user, client)
        elif text == "4" or "دعوة" in text or "referral" in text or "صديق" in text:
            client.send_direct_message(user_id, self.messages.get("REFERRAL_INFO_MESSAGE").format(referral_code=user.referral_code))
        # --- ✨ إضافة جديدة: قائمة المتصدرين ---
        elif text == "5" or "متصدر" in text or "leaderboard" in text or "ترتيب" in text:
             self._show_leaderboard(user, client)
        elif len(text) == 5 and text.isdigit():
            self._verify_code(user, text, client)
        else:
            daily_bonus_message = self._check_daily_bonus_eligibility(user)
            tasks_for_level_up = self.settings.get("TASKS_FOR_LEVEL_UP", 5)
            tasks_left = tasks_for_level_up - (user.tasks_completed % tasks_for_level_up)
            level_title = LEVELS.get(user.level, "أسطورة ✨")
            
            message_text = self.messages.get("MAIN_MENU_MESSAGE").format(
                username=sender.full_name, daily_bonus_message=daily_bonus_message,
                level_title=level_title, level=user.level, points=user.points,
                streak=user.streak, tasks_left=tasks_left, box_cost=self.settings.get("MYSTERY_BOX_COST", 2)
            )

            # --- ✨ تعديل: استخدام الأزرار السريعة بدلاً من النص ---
            replies_list = [
                ("🚀 مهمة جديدة", "1"),
                ("🎁 استبدال النقاط", "2"),
                ("🎲 صندوق الغموض", ("3")),
                ("🤝 دعوة صديق", "4"),
                ("🏆 المتصدرون", "5") # <-- إضافة زر المتصدرين
            ]
            client.send_direct_message_with_quick_replies(user_id, message_text, replies_list)
            # --- نهاية التعديل ---

    def _generate_referral_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not self.db.query(User).filter(User.referral_code == code).first():
                return code

    # --- ✨ تعديل: إرجاع علامة المستخدم الجديد ---
    def _get_or_create_user(self, sender):
        user_id = str(sender.pk)
        is_new_user = False # <-- إضافة
        user = self.db.query(User).filter(User.ig_user_id == user_id).first()
        if not user:
            is_new_user = True # <-- إضافة
            user = User(
                ig_user_id=user_id, 
                username=sender.username,
                referral_code=self._generate_referral_code()
            )
            self.db.add(user)
            self.db.commit()
            logging.info(f"New user created: {user.username} with referral code {user.referral_code}")
        return user, is_new_user # <-- تعديل
    # --- نهاية التعديل ---

    def _handle_referral_code(self, new_user, code, client):
        if new_user.referred_by_user_id:
            return
        referrer = self.db.query(User).filter(User.referral_code == code.upper()).first()
        if referrer and referrer.ig_user_id != new_user.ig_user_id:
            self._add_points(referrer, 3, f"دعوة المستخدم {new_user.username}")
            self._add_points(new_user, 3, f"استخدام كود الدعوة من {referrer.username}")
            new_user.referred_by_user_id = referrer.ig_user_id
            self.db.commit()
            client.send_direct_message(new_user.ig_user_id, "✅ تم تفعيل كود الدعوة! لقد حصلت على 3 نقاط هدية.")
            client.send_direct_message(referrer.ig_user_id, f"🎉 أخبار رائعة! لقد استخدم المستخدم {new_user.username} كود الدعوة الخاص بك وحصلت على 3 نقاط!")
            logging.info(f"User {new_user.username} was referred by {referrer.username}")
            
            # --- ✨ إضافة: منح إنجاز الدعوة ---
            self._check_and_grant_achievement(referrer, "first_referral", "لقد قمت بدعوة صديقك الأول!", client)
            # --- نهاية الإضافة ---
    
    def _check_daily_bonus_eligibility(self, user):
        today = date.today()
        if user.last_task_date is None or user.last_task_date < today:
            return "🎁 لديك مكافأة يومية بانتظارك! أكمل مهمتك الأولى اليوم لتحصل عليها."
        return ""

    def _apply_daily_bonus_and_streak(self, user):
        today = date.today()
        bonus_message = ""
        if user.last_task_date is None or user.last_task_date < today:
            if user.last_task_date == today - timedelta(days=1):
                user.streak += 1
                bonus_points = user.streak
                bonus_message = f"🔥 رائع! لقد حافظت على سلسلة إنجازك لـ {user.streak} أيام وحصلت على {bonus_points} نقاط إضافية!"
                self._add_points(user, bonus_points, f"سلسلة إنجاز - يوم {user.streak}")
            else:
                user.streak = 1
                bonus_message = "🎁 لقد حصلت على نقطة إضافية كمكافأة يومية!"
                self._add_points(user, 1, "مكافأة يومية")
            user.last_task_date = today
        return bonus_message

    def _play_mystery_box(self, user, client):
        mystery_box_cost = self.settings.get("MYSTERY_BOX_COST", 2)
        if user.points < mystery_box_cost:
            client.send_direct_message(user.ig_user_id, f"عفواً، تحتاج إلى {mystery_box_cost} نقاط على الأقل لتجربة حظك.")
            return
        
        self._add_points(user, -mystery_box_cost, "لعب صندوق الغموض")
        
        roll = random.randint(1, 100)
        points_won = 0
        if roll == 1:
            points_won = 25
            result_message = self.messages.get("MYSTERY_BOX_JACKPOT")
        elif 2 <= roll <= 10:
            points_won = 5
            result_message = self.messages.get("MYSTERY_BOX_BIG_WIN")
        elif 11 <= roll <= 40:
            points_won = 2
            result_message = self.messages.get("MYSTERY_BOX_WIN_BACK")
        else:
            points_won = 1
            result_message = self.messages.get("MYSTERY_BOX_SMALL_WIN")

        if points_won > 0:
            self._add_points(user, points_won, f"الفوز في صندوق الغموض")
            
        self.db.commit()
        client.send_direct_message(user.ig_user_id, result_message)
        self.handle_message(type('obj', (object,), {'text': 'menu'})(), type('obj', (object,), {'pk': user.ig_user_id, 'full_name': user.username})(), client)

    def _verify_code(self, user, code_value, client):
        code_obj = self.db.query(Code).filter(Code.code_value == code_value).first()
        
        # 1. هل الكود موجود أصلاً؟
        if not code_obj:
            client.send_direct_message(user.ig_user_id, self.messages.get("INVALID_CODE_MESSAGE"))
            return

        # 2. هل تم استخدام هذا الكود من قبل؟
        if code_obj.is_used:
            client.send_direct_message(user.ig_user_id, self.messages.get("USED_CODE_MESSAGE"))
            return

        # 3. هل هذا الكود تم "حجزه" (عرضه) من صفحة المهام؟
        if not code_obj.is_claimed:
            client.send_direct_message(user.ig_user_id, self.messages.get("INVALID_CODE_MESSAGE"))
            return
        
        points_per_task = self.settings.get("POINTS_PER_TASK", 1)
        code_obj.is_used = True # <-- اجعله مستخدماً الآن
        self._add_points(user, points_per_task, f"إكمال مهمة - كود {code_value}")
        user.tasks_completed += 1
        
        streak_message = self._apply_daily_bonus_and_streak(user)

        client.send_direct_message(user.ig_user_id, self.messages.get("CODE_VERIFIED_MESSAGE").format(points_earned=points_per_task, streak_message=streak_message))
        
        tasks_for_level_up = self.settings.get("TASKS_FOR_LEVEL_UP", 5)
        if user.tasks_completed > 0 and user.tasks_completed % tasks_for_level_up == 0:
            user.level += 1
            new_title = LEVELS.get(user.level, "أسطورة ✨")
            client.send_direct_message(user.ig_user_id, self.messages.get("LEVEL_UP_MESSAGE").format(level_title=new_title, level=user.level))

        # --- ✨ إضافة: منح إنجازات المهام ---
        if user.tasks_completed == 1:
            self._check_and_grant_achievement(user, "first_task", "لقد أكملت مهمتك الأولى!", client)
        elif user.tasks_completed == 10:
            self._check_and_grant_achievement(user, "ten_tasks", "وصلت إلى 10 مهام مكتملة! استمر!", client)
        # --- نهاية الإضافة ---
            
        self.db.commit()
        self.handle_message(type('obj', (object,), {'text': 'menu'})(), type('obj', (object,), {'pk': user.ig_user_id, 'full_name': user.username})(), client)

    def _initiate_redemption(self, user_id, user, client):
        followers_per_point = self.settings.get("FOLLOWERS_PER_POINT", 50)
        if user.points > 0:
            client.send_direct_message(user_id, self.messages.get("REDEEM_PROMPT_MESSAGE").format(points=user.points, followers_per_point=followers_per_point))
            self.user_state[user_id] = "awaiting_username"
        else:
            client.send_direct_message(user_id, self.messages.get("NO_POINTS_MESSAGE"))

    def _create_order(self, user, target_username, client):
        followers_per_point = self.settings.get("FOLLOWERS_PER_POINT", 50)
        points_to_redeem = user.points
        followers_amount = points_to_redeem * followers_per_point
        
        self._add_points(user, -points_to_redeem, f"استبدال {followers_amount} متابع")
        
        new_order = Order(username_to_follow=target_username, amount=followers_amount, owner_id=user.id)
        self.db.add(new_order)
        self.db.commit()
        
        logging.info(f"New order created for {target_username} by {user.username}")
        client.send_direct_message(user.ig_user_id, self.messages.get("ORDER_CONFIRMED_MESSAGE").format(amount=followers_amount, username=target_username))
        self._send_telegram_notification(new_order)
        self.user_state.pop(user.ig_user_id, None)

    def _send_telegram_notification(self, order: Order):
        if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
            return
        try:
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            message_text = (f"🔔 طلب جديد!\n\n👤 اليوزر: {order.username_to_follow}\n📈 الكمية: {order.amount} متابع\n⏰ الوقت: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)
            logging.info(f"Telegram notification sent for order {order.id}")
        except Exception as e:
            logging.error(f"Failed to send Telegram notification: {e}")

    # --- ✨✨✨ إضافة جديدة: قائمة المتصدرين ✨✨✨ ---
    def _show_leaderboard(self, user, client):
        """يعرض قائمة أعلى 5 مستخدمين وترتيب المستخدم الحالي."""
        try:
            top_users = self.db.query(User).filter(User.is_banned == False).order_by(User.points.desc()).limit(5).all()
            message = "🏆 قائمة المتصدرين 🏆\n\n"
            
            for i, top_user in enumerate(top_users):
                message += f"{i+1}. {top_user.username} - {top_user.points} نقطة 🪙\n"
            
            message += "\n------------------\n"
            
            # حساب ترتيب المستخدم الحالي
            user_rank = self.db.query(User).filter(User.points > user.points, User.is_banned == False).count() + 1
            message += f"موقعك الحالي: #{user_rank} برصيد {user.points} نقطة 🪙\n\nاستمر في العمل!"
            
            client.send_direct_message(user.ig_user_id, message)
        except Exception as e:
            logging.error(f"Error showing leaderboard: {e}")
            client.send_direct_message(user.ig_user_id, "حدث خطأ أثناء جلب قائمة المتصدرين.")
    # --- نهاية الإضافة ---
    
    # --- ✨✨✨ إضافة جديدة: نظام الإنجازات ✨✨✨ ---
    def _check_and_grant_achievement(self, user, achievement_name, message_to_send, client):
        """يتحقق إذا كان المستخدم يملك الإنجاز، ويمنحه إياه إذا لم يكن كذلك."""
        try:
            has_achievement = self.db.query(Achievement).filter_by(user_id=user.id, achievement_name=achievement_name).first()
            if not has_achievement:
                new_achievement = Achievement(user_id=user.id, achievement_name=achievement_name)
                self.db.add(new_achievement)
                # لا نحتاج commit هنا، سيتم عمل commit من الدالة الأصلية (مثل _verify_code)
                client.send_direct_message(user.ig_user_id, f"🏆 إنجاز جديد! 🏆\n\n{message_to_send}")
        except Exception as e:
            logging.error(f"Error granting achievement {achievement_name} to user {user.id}: {e}")
    # --- نهاية الإضافة ---