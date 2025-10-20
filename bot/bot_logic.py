import logging
import telegram
import random
import string
from datetime import date, timedelta

from database.database import SessionLocal
from database.models import User, Code, Order
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# --- ✍️ تعريفات ورسائل جديدة ---
LEVELS = {1: "مبتدئ 🥉", 2: "نشيط 🥈", 3: "محترف 🥇", 4: "خبير 🎖️", 5: "أسطورة ✨"}
TASKS_FOR_LEVEL_UP = 5
MYSTERY_BOX_COST = 2 # تكلفة صندوق الغموض

# القائمة الرئيسية التفاعلية الجديدة
MAIN_MENU_MESSAGE = """👋 مرحباً بك مجدداً {username}!

{daily_bonus_message}
--- 🌟 ملفك الشخصي 🌟 ---
▫️ اللقب: {level_title} (المستوى {level})
▫️ النقاط: {points} نقطة 🪙
▫️ سلسلة الإنجاز: {streak} أيام متتالية 🔥
▫️ المهام المتبقية للترقية: {tasks_left}

--- 👇 اختر ما تريد 👇 ---
1️⃣ - مهمة جديدة 🚀
2️⃣ - استبدال النقاط 🎁
3️⃣ - صندوق الغموض 🎲 (التكلفة: {box_cost} نقاط)
4️⃣ - دعوة صديق 🤝"""

# --- ✨ التعريفات المفقودة التي تم إضافتها ---
REFERRAL_INFO_MESSAGE = """🤝 نظام الدعوات 🤝

شارك الكود الخاص بك مع أصدقائك، وعندما يستخدمه صديقك عند انضمامه، ستحصل أنت وهو على مكافأة قدرها 3 نقاط!

🔗 الكود الخاص بك هو: `{referral_code}`"""

MYSTERY_BOX_RESULTS = {
    "jackpot": "🎉🎉 الجائزة الكبرى! 🎉🎉 لقد ربحت 25 نقطة! حظ أسطوري!",
    "big_win": "🎊 ضربة حظ! لقد ربحت 5 نقاط!",
    "win_back": "👌 استعدت نقاطك! لقد ربحت نقطتين.",
    "small_win": "😅 أفضل حظًا المرة القادمة! لقد ربحت نقطة واحدة."
}

# ... (بقية الرسائل تبقى كما هي)
TASK_MESSAGE = "أهلاً بك في مهمتك الجديدة! 🚀\n\n1. اذهب إلى الرابط في البايو.\n2. أكمل المهمة المطلوبة.\n3. ستحصل على كود من 5 أرقام.\n4. أرسل الكود هنا لتربح نقطة!\n\nبالتوفيق يا بطل!"
REDEEM_PROMPT_MESSAGE = "لديك {points} نقطة. يمكنك استبدال كل نقطة بـ 50 متابع.\n\nللبدء، أرسل يوزر حسابك الذي تريد إرسال المتابعين إليه (بدون علامة @)."
CODE_VERIFIED_MESSAGE = "رائع! 🎉 كود صحيح.\nتمت إضافة نقطة إلى رصيدك.\n\n{streak_message}"
LEVEL_UP_MESSAGE = "🥳 تهانينا! لقد ارتفع مستواك!\n\nلقبك الجديد هو: {level_title} (المستوى {level}).\nاستمر في التقدم يا بطل! 🚀"
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
        
        if user.tasks_completed == 0 and len(text) == 6:
            self._handle_referral_code(user, text, client)

        daily_bonus_message = ""
        
        if self.user_state.get(user_id) == "awaiting_username":
            self._create_order(user, text, client)
            return

        if text == "1":
            client.send_direct_message(user_id, TASK_MESSAGE)
        elif text == "2":
            self._initiate_redemption(user_id, user, client)
        elif text == "3":
            self._play_mystery_box(user, client)
        elif text == "4":
            client.send_direct_message(user_id, REFERRAL_INFO_MESSAGE.format(referral_code=user.referral_code))
        elif len(text) == 5 and text.isdigit():
            self._verify_code(user, text, client)
        else:
            daily_bonus_message = self._check_daily_bonus_eligibility(user)
            tasks_left = TASKS_FOR_LEVEL_UP - (user.tasks_completed % TASKS_FOR_LEVEL_UP)
            level_title = LEVELS.get(user.level, "أسطورة ✨")
            client.send_direct_message(user_id, MAIN_MENU_MESSAGE.format(
                username=sender.full_name, daily_bonus_message=daily_bonus_message,
                level_title=level_title, level=user.level, points=user.points,
                streak=user.streak, tasks_left=tasks_left, box_cost=MYSTERY_BOX_COST
            ))
    
    def _generate_referral_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not self.db.query(User).filter(User.referral_code == code).first():
                return code

    def _get_or_create_user(self, sender):
        user_id = str(sender.pk)
        user = self.db.query(User).filter(User.ig_user_id == user_id).first()
        if not user:
            user = User(
                ig_user_id=user_id, 
                username=sender.username,
                referral_code=self._generate_referral_code()
            )
            self.db.add(user)
            self.db.commit()
            logging.info(f"New user created: {user.username} with referral code {user.referral_code}")
        return user

    def _handle_referral_code(self, new_user, code, client):
        if new_user.referred_by_user_id:
            return

        referrer = self.db.query(User).filter(User.referral_code == code.upper()).first()
        if referrer and referrer.ig_user_id != new_user.ig_user_id:
            referrer.points += 3
            new_user.points += 3
            new_user.referred_by_user_id = referrer.ig_user_id
            self.db.commit()
            
            client.send_direct_message(new_user.ig_user_id, "✅ تم تفعيل كود الدعوة! لقد حصلت على 3 نقاط هدية.")
            client.send_direct_message(referrer.ig_user_id, f"🎉 أخبار رائعة! لقد استخدم المستخدم {new_user.username} كود الدعوة الخاص بك وحصلت على 3 نقاط!")
            logging.info(f"User {new_user.username} was referred by {referrer.username}")

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
                bonus_message = f"🔥 رائع! لقد حافظت على سلسلة إنجازك لـ {user.streak} أيام وحصلت على {user.streak} نقاط إضافية!"
                user.points += user.streak
            else:
                user.streak = 1
                bonus_message = "🎁 لقد حصلت على نقطة إضافية كمكافأة يومية!"
                user.points += 1
            user.last_task_date = today
            self.db.commit()
        return bonus_message

    def _play_mystery_box(self, user, client):
        if user.points < MYSTERY_BOX_COST:
            client.send_direct_message(user.ig_user_id, f"عفواً، تحتاج إلى {MYSTERY_BOX_COST} نقاط على الأقل لتجربة حظك.")
            return
        
        user.points -= MYSTERY_BOX_COST
        
        roll = random.randint(1, 100)
        if roll == 1:
            user.points += 25
            result_message = MYSTERY_BOX_RESULTS["jackpot"]
        elif 2 <= roll <= 10:
            user.points += 5
            result_message = MYSTERY_BOX_RESULTS["big_win"]
        elif 11 <= roll <= 40:
            user.points += 2
            result_message = MYSTERY_BOX_RESULTS["win_back"]
        else:
            user.points += 1
            result_message = MYSTERY_BOX_RESULTS["small_win"]
            
        self.db.commit()
        client.send_direct_message(user.ig_user_id, result_message)
        self.handle_message(type('obj', (object,), {'text': 'menu'})(), type('obj', (object,), {'pk': user.ig_user_id, 'full_name': user.username})(), client)

    def _verify_code(self, user, code_value, client):
        code_obj = self.db.query(Code).filter(Code.code_value == code_value).first()
        if not code_obj or code_obj.is_used:
            message = USED_CODE_MESSAGE if code_obj else INVALID_CODE_MESSAGE
            client.send_direct_message(user.ig_user_id, message)
            return

        code_obj.is_used = True
        user.points += 1
        user.tasks_completed += 1
        
        streak_message = self._apply_daily_bonus_and_streak(user)

        client.send_direct_message(user.ig_user_id, CODE_VERIFIED_MESSAGE.format(streak_message=streak_message))
        
        if user.tasks_completed % TASKS_FOR_LEVEL_UP == 0:
            user.level += 1
            new_title = LEVELS.get(user.level, "أسطورة ✨")
            client.send_direct_message(user.ig_user_id, LEVEL_UP_MESSAGE.format(level_title=new_title, level=user.level))
            
        self.db.commit()
        
        self.handle_message(type('obj', (object,), {'text': 'menu'})(), type('obj', (object,), {'pk': user.ig_user_id, 'full_name': user.username})(), client)

    def _initiate_redemption(self, user_id, user, client):
        if user.points > 0:
            client.send_direct_message(user_id, REDEEM_PROMPT_MESSAGE.format(points=user.points))
            self.user_state[user_id] = "awaiting_username"
        else:
            client.send_direct_message(user_id, NO_POINTS_MESSAGE)

    def _create_order(self, user, target_username, client):
        user_id = user.ig_user_id
        points_to_redeem = user.points
        followers_amount = points_to_redeem * 50
        new_order = Order(username_to_follow=target_username, amount=followers_amount, ordered_by_user_id=user_id)
        self.db.add(new_order)
        user.points = 0
        self.db.commit()
        logging.info(f"New order created for {target_username} by {user.username}")
        client.send_direct_message(user_id, ORDER_CONFIRMED_MESSAGE.format(amount=followers_amount, username=target_username))
        self._send_telegram_notification(new_order)
        self.user_state.pop(user_id, None)

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