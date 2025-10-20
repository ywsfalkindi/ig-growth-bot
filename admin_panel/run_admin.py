import os
import sys
import random
import string
import json
import base64
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime, timedelta

# --- تعديل المسار (لا تغيير هنا) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- استيرادات ---
from database.database import SessionLocal
from database.models import User, Order, Code, PointLog
from bot.instagram_client import InstagramClient # <<-- هذا الاستيراد مهم جدًا
from config import IG_USERNAME, IG_PASSWORD, ADMIN_PASSWORD, BASE_DIR

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sqlalchemy import func

# --- إعدادات Flask (لا تغيير هنا) ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-that-you-should-change")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# ... (نظام الحماية وتسجيل الدخول والخروج لا يتغير)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash("كلمة المرور غير صحيحة!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ... (دالة إنشاء الرسوم البيانية لا تتغير)
def create_chart(data, title, x_label, y_label):
    dates = [item[0] for item in data]
    counts = [item[1] for item in data]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, counts, marker='o', linestyle='-', color='b')
    ax.set_title(title, fontsize=16)
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel(y_label, fontsize=12)
    ax.grid(True)
    fig.autofmt_xdate()
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# --- ✨ دالة إرسال الهدية المطورة ---
@app.route('/gift', methods=['GET', 'POST'])
@login_required
def gift_points():
    db = SessionLocal()
    if request.method == 'POST':
        username = request.form.get('username')
        points = int(request.form.get('points', 0))
        reason = request.form.get('reason', 'هدية من المدير')
        
        user = db.query(User).filter(User.username == username).first()
        if user:
            # تحديث قاعدة البيانات
            user.points += points
            log = PointLog(user_id=user.id, points_change=points, reason=reason)
            db.add(log)
            db.commit()
            flash(f"تم إرسال {points} نقطة بنجاح إلى المستخدم {username}.", "success")

            # --- 🎁 الجزء الجديد: إرسال رسالة للمستخدم ---
            try:
                # نقوم بتسجيل الدخول كبوت لإرسال الرسالة
                client = InstagramClient(IG_USERNAME, IG_PASSWORD)
                gift_message = f"🎁 هدية من المدير!\n\nلقد حصلت على {points} نقاط.\nالسبب: {reason}"
                client.send_direct_message(user.ig_user_id, gift_message)
                flash("تم إعلام المستخدم بالهدية عبر رسالة خاصة.", "info")
            except Exception as e:
                flash(f"حدث خطأ أثناء إعلام المستخدم: {e}", "danger")
            # --- نهاية الجزء الجديد ---

        else:
            flash("لم يتم العثور على مستخدم بهذا اليوزر.", "danger")
        
        db.close() # تأكد من إغلاق الاتصال بقاعدة البيانات
        return redirect(url_for('gift_points'))
        
    users = db.query(User).all()
    db.close()
    return render_template('gift.html', users=users)

# ... (بقية الصفحات والإجراءات تبقى كما هي دون أي تغيير)
@app.route('/')
@login_required
def dashboard():
    db = SessionLocal()
    total_users = db.query(User).count()
    pending_orders = db.query(Order).filter(Order.is_completed == False).count()
    completed_orders = db.query(Order).filter(Order.is_completed == True).count()
    unused_codes = db.query(Code).filter(Code.is_used == False).count()
    seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
    orders_data = db.query(func.date(Order.created_at), func.count(Order.id)).filter(func.date(Order.created_at) >= seven_days_ago).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()
    orders_chart = create_chart(orders_data, 'الطلبات الجديدة في آخر 7 أيام', 'التاريخ', 'عدد الطلبات')
    users_data = db.query(func.date(User.created_at), func.count(User.id)).filter(func.date(User.created_at) >= seven_days_ago).group_by(func.date(User.created_at)).order_by(func.date(User.created_at)).all()
    users_chart = create_chart(users_data, 'المستخدمون الجدد في آخر 7 أيام', 'التاريخ', 'عدد المستخدمين')
    latest_logs = db.query(PointLog).order_by(PointLog.timestamp.desc()).limit(10).all()
    db.close()
    return render_template('dashboard.html', 
                           total_users=total_users, 
                           pending_orders=pending_orders,
                           completed_orders=completed_orders,
                           unused_codes=unused_codes,
                           bot_username=IG_USERNAME,
                           orders_chart=orders_chart,
                           users_chart=users_chart,
                           latest_logs=latest_logs)

@app.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first_or_404()
    db.close()
    return render_template('user_profile.html', user=user)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        with open(SETTINGS_FILE, 'r') as f:
            settings_data = json.load(f)
        settings_data['BOT_PAUSED'] = 'BOT_PAUSED' in request.form
        settings_data['POINTS_PER_TASK'] = int(request.form.get('POINTS_PER_TASK', 1))
        settings_data['FOLLOWERS_PER_POINT'] = int(request.form.get('FOLLOWERS_PER_POINT', 50))
        settings_data['MYSTERY_BOX_COST'] = int(request.form.get('MYSTERY_BOX_COST', 2))
        settings_data['TASKS_FOR_LEVEL_UP'] = int(request.form.get('TASKS_FOR_LEVEL_UP', 5))
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=4)
        flash("تم حفظ الإعدادات بنجاح!", "success")
        return redirect(url_for('settings'))
    with open(SETTINGS_FILE, 'r') as f:
        current_settings = json.load(f)
    return render_template('settings.html', settings=current_settings)

@app.route('/users')
@login_required
def manage_users():
    db = SessionLocal()
    users = db.query(User).order_by(User.points.desc()).all()
    db.close()
    return render_template('users.html', users=users)

@app.route('/orders')
@login_required
def manage_orders():
    db = SessionLocal()
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    db.close()
    return render_template('orders.html', orders=orders)

@app.route('/codes', methods=['GET', 'POST'])
@login_required
def manage_codes():
    db = SessionLocal()
    if request.method == 'POST':
        try:
            count = int(request.form.get('count', 50))
            existing_codes = {c.code_value for c in db.query(Code.code_value).all()}
            new_codes_to_add = []
            generated_in_this_run = set()
            while len(new_codes_to_add) < count:
                new_code_val = str(random.randint(10000, 99999))
                if new_code_val not in existing_codes and new_code_val not in generated_in_this_run:
                    generated_in_this_run.add(new_code_val)
                    new_codes_to_add.append(Code(code_value=new_code_val))
            db.add_all(new_codes_to_add)
            db.commit()
            flash(f"تم إنشاء {len(new_codes_to_add)} كود جديد بنجاح!", "success")
        except ValueError:
            flash("الرجاء إدخال رقم صحيح.", "danger")
    codes = db.query(Code).order_by(Code.id.desc()).all()
    db.close()
    return render_template('codes.html', codes=codes)

@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast_message():
    if request.method == 'POST':
        message = request.form.get('message')
        if not message:
            flash("لا يمكن إرسال رسالة فارغة.", "danger")
            return render_template('broadcast.html')
        try:
            client = InstagramClient(IG_USERNAME, IG_PASSWORD)
            db = SessionLocal()
            users = db.query(User).all()
            user_ids = [user.ig_user_id for user in users]
            client.cl.direct_send(message, user_ids=user_ids)
            db.close()
            flash(f"تم إرسال الرسالة بنجاح إلى {len(user_ids)} مستخدم.", "success")
        except Exception as e:
            flash(f"حدث خطأ أثناء إرسال الرسالة: {e}", "danger")
    return render_template('broadcast.html')

@app.route('/user/edit', methods=['POST'])
@login_required
def edit_user():
    db = SessionLocal()
    user_id = request.form.get('user_id')
    points_to_add = int(request.form.get('add_points', '0'))
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        try:
            user.points += points_to_add
            if user.points < 0: user.points = 0
            reason = f"تعديل يدوي من المدير: {'إضافة' if points_to_add >= 0 else 'خصم'} {abs(points_to_add)} نقاط"
            log = PointLog(user_id=user.id, points_change=points_to_add, reason=reason)
            db.add(log)
            db.commit()
            flash(f"تم تحديث نقاط المستخدم {user.username} بنجاح.", "success")
        except ValueError:
            flash("الرجاء إدخال رقم صحيح للنقاط.", "danger")
    db.close()
    return redirect(url_for('manage_users'))

@app.route('/user/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        flash(f"تم حذف المستخدم {user.username} وكل بياناته بنجاح.", "success")
    db.close()
    return redirect(url_for('manage_users'))

@app.route('/order/complete/<int:order_id>', methods=['POST'])
@login_required
def complete_order(order_id):
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.is_completed = True
        db.commit()
        flash(f"تم تحديد طلب المستخدم {order.username_to_follow} كمكتمل.", "success")
    db.close()
    return redirect(url_for('manage_orders'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)