import logging
import telegram

from database.database import SessionLocal
from database.models import User, Code, Order
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# (الرسائل الجاهزة)
WELCOME_MESSAGE = "مرحباً بك {username}! 👋\nأنا مساعدك الآلي لنمو حسابك.\n\nأرسل كلمة 'مهمة' لبدء ربح النقاط."
TASK_MESSAGE = "أهلاً بك في مهمتك الجديدة! 🚀\n\n1. اذهب إلى الرابط في البايو.\n2. أكمل المهمة المطلوبة.\n3. ستحصل على كود من 5 أرقام.\n4. أرسل الكود هنا لتربح نقطة!\n\nبالتوفيق يا بطل!"
BALANCE_MESSAGE = "رصيدك الحالي هو: {points} نقطة 🪙"
REDEEM_PROMPT_MESSAGE = "لديك {points} نقطة. يمكنك استبدال كل نقطة بـ 50 متابع.\n\nللبدء، أرسل يوزر حسابك الذي تريد إرسال المتابعين إليه (بدون علامة @)."
CODE_VERIFIED_MESSAGE = "رائع! 🎉 كود صحيح.\nتمت إضافة نقطة إلى رصيدك.\n\nرصيدك الآن هو: {points} نقطة."
ORDER_CONFIRMED_MESSAGE = "✅ تم استلام طلبك بنجاح!\nسيتم إرسال {amount} متابع إلى حسابك {username} خلال 24 ساعة."
NO_POINTS_MESSAGE = "عفواً، رصيدك لا يسمح بالاستبدال حالياً. أرسل 'مهمة' لربح المزيد من النقاط."
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

        if self.user_state.get(user_id) == "awaiting_username":
            self._create_order(user, text, client)
            return

        if text in ["مهمة", "task", "ابدأ", "start"]:
            client.send_direct_message(user_id, TASK_MESSAGE)
        elif text in ["رصيدي", "نقاطي", "balance"]:
            client.send_direct_message(user_id, BALANCE_MESSAGE.format(points=user.points))
        elif text in ["استبدال", "redeem"]:
            self._initiate_redemption(user_id, user, client)
        elif len(text) == 5 and text.isdigit():
            self._verify_code(user, text, client)
        else:
            client.send_direct_message(user_id, WELCOME_MESSAGE.format(username=sender.full_name))
    
    def _get_or_create_user(self, sender):
        user_id = str(sender.pk)
        user = self.db.query(User).filter(User.ig_user_id == user_id).first()
        if not user:
            user = User(ig_user_id=user_id, username=sender.username, points=0)
            self.db.add(user)
            self.db.commit()
            logging.info(f"New user created: {user.username}")
        return user

    def _initiate_redemption(self, user_id, user, client):
        if user.points > 0:
            # --- هذا هو السطر الذي تم تصحيحه ---
            client.send_direct_message(user_id, REDEEM_PROMPT_MESSAGE.format(points=user.points))
            self.user_state[user_id] = "awaiting_username"
        else:
            client.send_direct_message(user_id, NO_POINTS_MESSAGE)

    def _create_order(self, user, target_username, client):
        user_id = user.ig_user_id
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

    def _verify_code(self, user, code_value, client):
        code_obj = self.db.query(Code).filter(Code.code_value == code_value).first()

        if not code_obj:
            client.send_direct_message(user.ig_user_id, INVALID_CODE_MESSAGE)
            return

        if code_obj.is_used:
            client.send_direct_message(user.ig_user_id, USED_CODE_MESSAGE)
            return

        code_obj.is_used = True
        user.points += 1
        self.db.commit()
        
        client.send_direct_message(user.ig_user_id, CODE_VERIFIED_MESSAGE.format(points=user.points))

    def _send_telegram_notification(self, order: Order):
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