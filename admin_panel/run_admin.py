# admin_panel/run_admin.py

import os
import sys
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

# --- تعديل المسار للسماح باستيراد مكونات البوت ---
# هذا السطر مهم جدًا ليتمكن الفلاسك من العثور على ملفات قاعدة البيانات والبوت
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.database import SessionLocal
from database.models import User, Order, Code
from bot.instagram_client import InstagramClient # <<-- استيراد جديد لأداة البث
from config import IG_USERNAME, IG_PASSWORD, ADMIN_PASSWORD

# --- إعدادات Flask ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-that-you-should-change")

# --- نظام الحماية (لا تغيير هنا) ---
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

# --- صفحات لوحة التحكم (مع الصفحات الجديدة) ---

@app.route('/')
@login_required
def dashboard():
    db = SessionLocal()
    total_users = db.query(User).count()
    pending_orders = db.query(Order).filter(Order.is_completed == False).count()
    completed_orders = db.query(Order).filter(Order.is_completed == True).count()
    unused_codes = db.query(Code).filter(Code.is_used == False).count()
    db.close()
    return render_template('dashboard.html', 
                           total_users=total_users, 
                           pending_orders=pending_orders,
                           completed_orders=completed_orders,
                           unused_codes=unused_codes,
                           bot_username=IG_USERNAME)

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

# --- ✨ صفحة إدارة الأكواد الجديدة ---
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

# --- ✨ صفحة البث الشامل الجديدة ---
@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast_message():
    if request.method == 'POST':
        message = request.form.get('message')
        if not message:
            flash("لا يمكن إرسال رسالة فارغة.", "danger")
            return render_template('broadcast.html')

        try:
            # نقوم بتسجيل الدخول كبوت لإرسال الرسائل
            client = InstagramClient(IG_USERNAME, IG_PASSWORD)
            db = SessionLocal()
            users = db.query(User).all()
            user_ids = [user.ig_user_id for user in users]
            
            # ملاحظة: إرسال الرسائل لعدد كبير من المستخدمين قد يستغرق وقتاً
            # وقد يعرض حسابك للخطر إذا تم بشكل متكرر. استخدم بحذر.
            client.cl.direct_send(message, user_ids=user_ids)

            db.close()
            flash(f"تم إرسال الرسالة بنجاح إلى {len(user_ids)} مستخدم.", "success")
        except Exception as e:
            flash(f"حدث خطأ أثناء إرسال الرسالة: {e}", "danger")

    return render_template('broadcast.html')


# --- إجراءات التحكم المطورة (Actions) ---

# --- ✨ تعديل لإضافة أو خصم النقاط ---
@app.route('/user/edit', methods=['POST'])
@login_required
def edit_user():
    db = SessionLocal()
    user_id = request.form.get('user_id')
    points_to_add = request.form.get('add_points', '0')
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        try:
            user.points += int(points_to_add)
            if user.points < 0: user.points = 0 # منع النقاط السالبة
            db.commit()
            flash(f"تم تحديث نقاط المستخدم {user.username} بنجاح.", "success")
        except ValueError:
            flash("الرجاء إدخال رقم صحيح للنقاط.", "danger")
    db.close()
    return redirect(url_for('manage_users'))

# --- ✨ إجراء لحذف المستخدم ---
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