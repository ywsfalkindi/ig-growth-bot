import logging
import telegram
from datetime import date, timedelta

# (استيراد المكتبات الأخرى يبقى كما هو)
from database.database import SessionLocal
from database.models import User, Code, Order
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


# --- ✍️ رسائل جديدة ومحسنة ---
LEVELS = {
    1: "مبتدئ 🥉", 2: "نشيط 🥈", 3: "محترف 🥇", 4: "خبير 🎖️", 5: "أسطورة ✨"
}
TASKS_FOR_LEVEL_UP = 5 # عدد المهام اللازمة لكل مستوى جديد

# القائمة الرئيسية التفاعلية
MAIN_MENU_MESSAGE = """👋 مرحباً بك مجدداً {username}!

{daily_bonus_message}

--- 🌟 ملفك الشخصي 🌟 ---
▫️ اللقب: {level_title} (المستوى {level})
▫️ النقاط: {points} نقطة 🪙
▫️ سلسلة الإنجاز: {streak} أيام متتالية 🔥
▫️ المهام المتبقية للترقية: {tasks_left}

--- 👇 اختر ما تريد 👇 ---
1️⃣ - مهمة جديدة 🚀
2️⃣ - استبدال النقاط 🎁"""

# رسائل أخرى
TASK_MESSAGE = "أهلاً بك في مهمتك الجديدة! 🚀\n\n1. اذهب إلى الرابط في البايو.\n2. أكمل المهمة المطلوبة.\n3. ستحصل على كود من 5 أرقام.\n4. أرسل الكود هنا لتربح نقطة!\n\nبالتوفيق يا بطل!"
REDEEM_PROMPT_MESSAGE = "لديك {points} نقطة. يمكنك استبدال كل نقطة بـ 50 متابع.\n\nللبدء، أرسل يوزر حسابك الذي تريد إرسال المتابعين إليه (بدون علامة @)."
CODE_VERIFIED_MESSAGE = "رائع! 🎉 كود صحيح.\nتمت إضافة نقطة إلى رصيدك.\n\n{streak_message}"
LEVEL_UP_MESSAGE = "🥳 تهانينا! لقد ارتفع مستواك!\n\nلقبك الجديد هو: {level_title} (المستوى {level}).\nاستمر في التقدم يا بطل! 🚀"
# ... (بقية الرسائل تبقى كما هي)
ORDER_CONFIRMED_MESSAGE = "✅ تم استلام طلبك بنجاح!\nسيتم إرسال {amount} متابع إلى حسابك {username} خلال 24 ساعة."
NO_POINTS_MESSAGE = "عفواً، رصيدك لا يسمح بالاستبدال حالياً. أرسل '1' للحصول على مهمة جديدة."
INVALID_CODE_MESSAGE = "عفواً، هذا الكود غير صحيح. تأكد من كتابته بشكل سليم."
USED_CODE_MESSAGE = "عفواً، هذا الكود تم استخدامه من قبل. كل كود صالح لمرة واحدة فقط."


class BotLogic:
    def __init__(self):
        self.db = SessionLocal()
        self.user_state = {}

    def handle_message(self, message, sender, client):
        user_id = str(sender.pk)
        text = message.text.lower().strip()

        user = self._get_or_create_user(sender)
        
        # --- ✨ نظام المكافأة اليومية وسلسلة الإنجاز ---
        daily_bonus_message = self._handle_daily_bonus(user)

        if self.user_state.get(user_id) == "awaiting_username":
            self._create_order(user, text, client)
            return

        # --- 🎮 القائمة الرئيسية التفاعلية ---
        if text == "1":
            client.send_direct_message(user_id, TASK_MESSAGE)
        elif text == "2":
            self._initiate_redemption(user_id, user, client)
        elif len(text) == 5 and text.isdigit():
            self._verify_code(user, text, client)
        else: # أي رسالة أخرى ستعرض القائمة الرئيسية
            tasks_left = TASKS_FOR_LEVEL_UP - (user.tasks_completed % TASKS_FOR_LEVEL_UP)
            level_title = LEVELS.get(user.level, "أسطورة ✨")
            
            client.send_direct_message(user_id, MAIN_MENU_MESSAGE.format(
                username=sender.full_name,
                daily_bonus_message=daily_bonus_message,
                level_title=level_title,
                level=user.level,
                points=user.points,
                streak=user.streak,
                tasks_left=tasks_left
            ))
    
    def _get_or_create_user(self, sender):
        user_id = str(sender.pk)
        user = self.db.query(User).filter(User.ig_user_id == user_id).first()
        if not user:
            user = User(ig_user_id=user_id, username=sender.username)
            self.db.add(user)
            self.db.commit()
            logging.info(f"New user created: {user.username}")
        return user

    def _handle_daily_bonus(self, user):
        """يعالج المكافآت اليومية وسلسلة الإنجاز."""
        today = date.today()
        bonus_message = ""
        
        if user.last_task_date is None: # أول مهمة له على الإطلاق
            user.streak = 1
            bonus_message = "🎁 لقد حصلت على نقطة إضافية كـ مكافأة المهمة الأولى!"
            user.points += 1
        elif user.last_task_date < today:
            if user.last_task_date == today - timedelta(days=1): # يوم متتالي
                user.streak += 1
                bonus_message = f"🔥 رائع! لقد حافظت على سلسلة إنجازك لـ {user.streak} أيام وحصلت على {user.streak} نقاط إضافية!"
                user.points += user.streak # مكافأة تزداد كل يوم
            else: # انقطعت السلسلة
                user.streak = 1
                bonus_message = "🎁 لقد حصلت على نقطة إضافية كمكافأة يومية! حاول الحفاظ على السلسلة غداً."
                user.points += 1
        
        if bonus_message: # فقط نحدث التاريخ إذا كانت هناك مكافأة (أي أول مهمة في اليوم)
            user.last_task_date = today
            self.db.commit()
            
        return bonus_message

    def _verify_code(self, user, code_value, client):
        """يتحقق من الكود ويضيف النقاط والمستوى."""
        code_obj = self.db.query(Code).filter(Code.code_value == code_value).first()

        if not code_obj or code_obj.is_used:
            message = USED_CODE_MESSAGE if code_obj else INVALID_CODE_MESSAGE
            client.send_direct_message(user.ig_user_id, message)
            return

        # الكود صحيح، لنبدأ التحديثات
        code_obj.is_used = True
        user.points += 1
        user.tasks_completed += 1
        
        streak_message = self._handle_daily_bonus(user)

        client.send_direct_message(user.ig_user_id, CODE_VERIFIED_MESSAGE.format(streak_message=streak_message))
        
        # --- 🏅 نظام المستويات ---
        if user.tasks_completed % TASKS_FOR_LEVEL_UP == 0:
            user.level += 1
            new_title = LEVELS.get(user.level, "أسطورة ✨")
            client.send_direct_message(user.ig_user_id, LEVEL_UP_MESSAGE.format(level_title=new_title, level=user.level))
            
        self.db.commit()
        
        # بعد كل شيء، نعرض له القائمة الرئيسية المحدثة
        self.handle_message(type('obj', (object,), {'text': 'menu'})(), type('obj', (object,), {'pk': user.ig_user_id, 'full_name': user.username})(), client)


    # (بقية الدوال مثل _initiate_redemption و _create_order تبقى كما هي)
    def _initiate_redemption(self, user_id, user, client):
        if user.points > 0:
            client.send_direct_message(user_id, REDEEM_PROMPT_MESSAGE.format(points=user.points))
            self.user_state[user_id] = "awaiting_username"
        else:
            client.send_direct_message(user_id, NO_POINTS_MESSAGE)

    def _create_order(self, user, target_username, client):
        user_id = user.ig_user_id
        # ... (بقية الكود هنا لا يتغير)
        points_to_redeem = user.points
        followers_amount = points_to_redeem * 50

        new_order = Order(
            username_to_follow=target_username,
            amount=followers_amount,
            ordered_by_user_id=user_id
        )
        self.db.add(new_order)
        
        user.points = 0
        self.db.commit()
        
        logging.info(f"New order created for {target_username} by {user.username}")
        client.send_direct_message(user_id, ORDER_CONFIRMED_MESSAGE.format(amount=followers_amount, username=target_username))
        
        self._send_telegram_notification(new_order)
        self.user_state.pop(user_id, None)

    def _send_telegram_notification(self, order: Order):
        # ... (الكود هنا لا يتغير)
        if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
            logging.warning("Telegram credentials not set. Skipping notification.")
            return
        try:
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            message_text = (
                f"🔔 طلب جديد!\n\n"
                f"👤 اليوزر: {order.username_to_follow}\n"
                f"📈 الكمية: {order.amount} متابع\n"
                f"⏰ الوقت: {order.created_at.strftime('%Y-%m-%d %H:%M')}"
            )
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)
            logging.info(f"Telegram notification sent for order {order.id}")
        except Exception as e:
            logging.error(f"Failed to send Telegram notification: {e}")