# --- ✨ إضافات للتحكم الكامل ---
import eventlet
eventlet.monkey_patch() # ضروري لـ SocketIO

import os
import sys
import random
import string
import json
import base64
import subprocess
import threading
import time
import logging
from io import BytesIO
from urllib.parse import urlparse # <-- ✨✨✨ (1) الإضافة الأولى: نحتاج هذا للتحقق من الرابط
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort
from flask_socketio import SocketIO, emit
from functools import wraps
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv, set_key
# --- نهاية الإضافات ---

# --- تعديل المسار (لا تغيير هنا) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- استيرادات ---
from database.database import SessionLocal
from database.models import User, Order, Code, PointLog
from bot.instagram_client import InstagramClient
from config import IG_USERNAME, IG_PASSWORD, ADMIN_PASSWORD, BASE_DIR, DATABASE_URL

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

# --- إعدادات Flask و SocketIO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-that-you-should-change")
socketio = SocketIO(app) # ✨ إضافة SocketIO

# --- ✨ متغيرات جديدة للميزات ---
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
LOG_FILE = os.path.join(BASE_DIR, "bot.log") # ملف السجل الذي يكتبه main.py
ENV_FILE = find_dotenv(os.path.join(BASE_DIR, '.env')) # مسار ملف .env
DB_FILE = DATABASE_URL.replace("sqlite:///", "") # مسار ملف قاعدة البيانات


# --- ✨✨✨ (2) الإضافة الثانية: أضف هنا دومين موقع اختصار الروابط الخاص بك ✨✨✨ ---
# هذا هو أهم سطر لإصلاح الثغرة. استبدل "YOUR_SHORTENER_DOMAIN.COM" بالدومين الفعلي.
# مثال: ["ouo.io", "ouo.press"] أو ["adf.ly"]
ALLOWED_REFERERS = ["bestcash2020.com"] 
# --- نهاية الإضافة ---


# --- ✨ إضافة جديدة: فلتر لتنسيق الوقت ---
@app.template_filter('format_datetime')
def _jinja_filter_format_datetime(dt, fmt="%Y-%m-%d %H:%M"):
    if not isinstance(dt, datetime):
        try:
            # محاولة تحويل النص إلى تاريخ إذا أمكن
            dt = datetime.fromisoformat(str(dt))
        except:
            return dt # إذا فشل، أعد النص الأصلي (مثل "الآن")
    return dt.strftime(fmt)
# --- نهاية الإضافة ---


# --- ✨ وظيفة لقراءة ملف .env ---
def read_env_file():
    env_vars = {}
    try:
        if ENV_FILE:
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
    except Exception as e:
        flash(f"Error reading .env file: {e}", "danger")
    return env_vars

# --- ✨ وظيفة لمراقبة ملف السجل في الخلفية ---
def tail_log_file():
    """يراقب ملف السجل ويرسل أي سطور جديدة إلى المتصفح عبر SocketIO."""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            f.seek(0, 2) # اذهب إلى نهاية الملف
            while True:
                line = f.readline()
                if line:
                    socketio.emit('new_log', {'log_line': line.strip()})
                else:
                    eventlet.sleep(0.5) # استخدم eventlet.sleep بدلاً من time.sleep
    except FileNotFoundError:
        print(f"Log file not found at {LOG_FILE}, live logging will not work.")
    except Exception as e:
        print(f"Error in log tailing thread: {e}")

# --- (لا تغيير في login_required, login, logout, create_chart) ---

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

def create_chart(data, title, x_label, y_label):
    if not data: return None
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


# --- ✨✨✨ تم تعديل هذه الدالة ✨✨✨ ---
@app.route('/')
@login_required
def dashboard():
    db = SessionLocal()
    
    # --- إحصائيات ---
    total_users = db.query(User).count()
    total_points = db.query(func.sum(User.points)).scalar() or 0
    today_date = datetime.utcnow().date()
    
    # --- ✨ تعديل لإصلاح خطأ DISTINCT على SQLite ---
    # هذا يحل تحذير SADeprecationWarning ويعطي النتيجة الصحيحة
    active_users_today = db.query(PointLog.user_id).filter(func.date(PointLog.timestamp) == today_date).distinct().count()
    # --- نهاية التعديل ---
    
    avg_points_per_user = round(total_points / total_users if total_users > 0 else 0, 2)
    pending_orders = db.query(Order).filter(Order.is_completed == False).count()
    completed_orders = db.query(Order).filter(Order.is_completed == True).count()
    unused_codes = db.query(Code).filter(Code.is_used == False).count()
    
    # --- رسوم بيانية ---
    seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
    orders_data = db.query(func.date(Order.created_at), func.count(Order.id)).filter(func.date(Order.created_at) >= seven_days_ago).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()
    orders_chart = create_chart(orders_data, 'الطلبات الجديدة في آخر 7 أيام', 'التاريخ', 'عدد الطلبات')
    users_data = db.query(func.date(User.created_at), func.count(User.id)).filter(func.date(User.created_at) >= seven_days_ago).group_by(func.date(User.created_at)).order_by(func.date(User.created_at)).all()
    users_chart = create_chart(users_data, 'المستخدمون الجدد في آخر 7 أيام', 'التاريخ', 'عدد المستخدمين')
    
    latest_logs = db.query(PointLog).options(joinedload(PointLog.user)).order_by(PointLog.timestamp.desc()).limit(10).all()
    
    db.close()
    return render_template('dashboard.html', 
                           total_users=total_users, 
                           total_points=total_points, 
                           active_users_today=active_users_today, 
                           avg_points_per_user=avg_points_per_user,
                           pending_orders=pending_orders,
                           completed_orders=completed_orders,
                           unused_codes=unused_codes,
                           bot_username=IG_USERNAME,
                           orders_chart=orders_chart,
                           users_chart=users_chart,
                           latest_logs=latest_logs,
                           current_time=datetime.utcnow() # <-- ✨ إضافة جديدة لتمرير الوقت
                           )
# --- نهاية التعديل ---

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        settings_data['BOT_PAUSED'] = 'BOT_PAUSED' in request.form
        settings_data['POINTS_PER_TASK'] = int(request.form.get('POINTS_PER_TASK', 1))
        settings_data['FOLLOWERS_PER_POINT'] = int(request.form.get('FOLLOWERS_PER_POINT', 50))
        settings_data['MYSTERY_BOX_COST'] = int(request.form.get('MYSTERY_BOX_COST', 2))
        settings_data['TASKS_FOR_LEVEL_UP'] = int(request.form.get('TASKS_FOR_LEVEL_UP', 5))
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
        flash("تم حفظ الإعدادات العامة بنجاح!", "success")
        return redirect(url_for('settings'))
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        current_settings = json.load(f)
    return render_template('settings.html', settings=current_settings)

@app.route('/messages', methods=['GET', 'POST'])
@login_required
def bot_messages():
    if request.method == 'POST':
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        
        for key in settings_data.get("MESSAGES", {}):
            if key in request.form:
                settings_data["MESSAGES"][key] = request.form[key]

        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
        
        flash("تم حفظ رسائل البوت بنجاح!", "success")
        return redirect(url_for('bot_messages'))

    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        current_messages = json.load(f).get("MESSAGES", {})
    
    return render_template('bot_messages.html', messages=current_messages)

@app.route('/users')
@login_required
def manage_users():
    db = SessionLocal()
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'all')
    
    query = db.query(User)
    
    if search_query:
        query = query.filter(User.username.ilike(f'%{search_query}%'))
    
    if status_filter == 'banned':
        query = query.filter(User.is_banned == True)
    elif status_filter == 'active':
        query = query.filter(User.is_banned == False)
        
    users = query.order_by(User.points.desc()).all()
    user_count = len(users)
    db.close()
    return render_template('users.html', 
                           users=users, 
                           user_count=user_count,
                           search_query=search_query, 
                           status_filter=status_filter)

@app.route('/user/ban/<int:user_id>', methods=['POST'])
@login_required
def ban_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_banned = True
        db.commit()
        flash(f"تم حظر المستخدم {user.username} بنجاح.", "warning")
    db.close()
    return redirect(request.referrer or url_for('manage_users'))

@app.route('/user/unban/<int:user_id>', methods=['POST'])
@login_required
def unban_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_banned = False
        db.commit()
        flash(f"تم إلغاء حظر المستخدم {user.username} بنجاح.", "success")
    db.close()
    return redirect(request.referrer or url_for('manage_users'))

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
            user.points += points
            log = PointLog(user_id=user.id, points_change=points, reason=reason)
            db.add(log)
            db.commit()
            flash(f"تم إرسال {points} نقطة بنجاح إلى المستخدم {username}.", "success")
            try:
                client = InstagramClient(IG_USERNAME, IG_PASSWORD)
                gift_message = f"🎁 هدية من المدير!\n\nلقد حصلت على {points} نقاط.\nالسبب: {reason}"
                client.send_direct_message(user.ig_user_id, gift_message)
                flash("تم إعلام المستخدم بالهدية عبر رسالة خاصة.", "info")
            except Exception as e:
                flash(f"حدث خطأ أثناء إعلام المستخدم: {e}", "danger")
        else:
            flash("لم يتم العثور على مستخدم بهذا اليوزر.", "danger")
        db.close()
        return redirect(url_for('gift_points'))
    users = db.query(User).all()
    db.close()
    return render_template('gift.html', users=users)

@app.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    db = SessionLocal()

    # --- ✨ هذا هو السطر الذي تم تعديله ---
    user = db.query(User).options(joinedload(User.point_logs)).filter(User.id == user_id).first()
    if not user:
        abort(404) # إذا لم يتم العثور على المستخدم، اعرض صفحة 404
    # --- نهاية التعديل ---

    referrer = None
    if user.referred_by_user_id:
        referrer = db.query(User).filter(User.ig_user_id == user.referred_by_user_id).first()

    referees = db.query(User).filter(User.referred_by_user_id == user.ig_user_id).all()

    db.close()
    return render_template('user_profile.html', user=user, referrer=referrer, referees=referees)

@app.route('/orders')
@login_required
def manage_orders():
    db = SessionLocal()
    status_filter = request.args.get('status', 'all')
    
    query = db.query(Order).options(joinedload(Order.owner))
    
    if status_filter == 'pending':
        query = query.filter(Order.is_completed == False)
    elif status_filter == 'completed':
        query = query.filter(Order.is_completed == True)
        
    orders = query.order_by(Order.created_at.desc()).all()
    db.close()
    return render_template('orders.html', orders=orders, status_filter=status_filter)

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
            users = db.query(User).filter(User.is_banned == False).all() 
            user_ids = [user.ig_user_id for user in users]
            client.cl.direct_send(message, user_ids=user_ids)
            db.close()
            flash(f"تم إرسال الرسالة بنجاح إلى {len(user_ids)} مستخدم.", "success")
        except Exception as e:
            flash(f"حدث خطأ أثناء إرسال الرسالة: {e}", "danger")
        return redirect(url_for('broadcast_message'))
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
    return redirect(request.referrer or url_for('manage_users'))

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
    return redirect(request.referrer or url_for('manage_orders'))


# --- ✨ مسارات جديدة لإدارة الأكواد ---

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
        return redirect(url_for('manage_codes'))
        
    codes = db.query(Code).order_by(Code.id.desc()).all()
    db.close()
    return render_template('codes.html', codes=codes)

@app.route('/code/delete/<int:code_id>', methods=['POST'])
@login_required
def delete_code(code_id):
    db = SessionLocal()
    code = db.query(Code).filter(Code.id == code_id).first()
    if code:
        db.delete(code)
        db.commit()
        flash(f"تم حذف الكود {code.code_value} بنجاح.", "success")
    db.close()
    return redirect(url_for('manage_codes'))

@app.route('/code/reactivate/<int:code_id>', methods=['POST'])
@login_required
def reactivate_code(code_id):
    db = SessionLocal()
    code = db.query(Code).filter(Code.id == code_id).first()
    if code and code.is_used:
        code.is_used = False
        db.commit()
        flash(f"تم إعادة تفعيل الكود {code.code_value} بنجاح.", "success")
    db.close()
    return redirect(url_for('manage_codes'))

# --- ✨ مسارات جديدة للتعديل الشامل للمستخدم ---

@app.route('/user/edit_full/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user_full(user_id):
    db = SessionLocal()

    # --- ✨ هذا هو السطر الذي تم تعديله ---
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        abort(404)
    # --- نهاية التعديل ---

    if request.method == 'POST':
        try:
            # تحديث الحقول
            user.username = request.form.get('username')
            user.points = int(request.form.get('points'))
            user.level = int(request.form.get('level'))
            user.tasks_completed = int(request.form.get('tasks_completed'))
            user.streak = int(request.form.get('streak'))
            user.referral_code = request.form.get('referral_code')
            user.referred_by_user_id = request.form.get('referred_by_user_id') or None
            user.is_banned = 'is_banned' in request.form

            db.commit()
            flash(f"تم تحديث بيانات {user.username} بنجاح!", "success")
            db.close()
            return redirect(url_for('user_profile', user_id=user.id))

        except Exception as e:
            db.rollback()
            flash(f"حدث خطأ أثناء التحديث: {e}", "danger")

    db.close()
    return render_template('edit_user_profile.html', user=user)

# --- ✨ مسارات جديدة لإدارة "قاع" البوت ---

@app.route('/core_settings', methods=['GET', 'POST'])
@login_required
def core_settings():
    if not ENV_FILE:
        flash("ملف .env غير موجود أو لا يمكن العثور عليه!", "danger")
        return render_template('core_settings.html', env_vars={}, service_name="ig_bot.service")

    if request.method == 'POST':
        try:
            # قراءة الإعدادات الحالية
            current_vars = read_env_file()
            for key in current_vars:
                if key in request.form:
                    new_value = request.form[key]
                    set_key(ENV_FILE, key, new_value)
            
            flash("تم حفظ الإعدادات الأساسية. يتطلب تفعيلها إعادة تشغيل البوت.", "success")
        except Exception as e:
            flash(f"خطأ أثناء حفظ ملف .env: {e}. تأكد من صلاحيات الكتابة.", "danger")
        return redirect(url_for('core_settings'))

    env_vars = read_env_file()
    return render_template('core_settings.html', env_vars=env_vars, service_name="ig_bot.service")

@app.route('/process/restart', methods=['POST'])
@login_required
def process_restart():
    try:
        # ملاحظة: هذا يتطلب صلاحيات sudo بدون كلمة سر للمستخدم الذي يشغل Flask
        result = subprocess.run(["sudo", "systemctl", "restart", "ig_bot.service"], capture_output=True, text=True)
        if result.returncode == 0:
            flash("تم إرسال أمر إعادة تشغيل البوت بنجاح.", "success")
        else:
            flash(f"فشل أمر إعادة التشغيل: {result.stderr}", "danger")
    except Exception as e:
        flash(f"خطأ أثناء محاولة إعادة التشغيل: {e}", "danger")
    return redirect(url_for('core_settings'))

@app.route('/process/stop', methods=['POST'])
@login_required
def process_stop():
    try:
        result = subprocess.run(["sudo", "systemctl", "stop", "ig_bot.service"], capture_output=True, text=True)
        if result.returncode == 0:
            flash("تم إرسال أمر إيقاف البوت بنجاح.", "warning")
        else:
            flash(f"فشل أمر الإيقاف: {result.stderr}", "danger")
    except Exception as e:
        flash(f"خطأ أثناء محاولة الإيقاف: {e}", "danger")
    return redirect(url_for('core_settings'))

# --- ✨ مسارات جديدة للصيانة والنسخ الاحتياطي ---

@app.route('/maintenance')
@login_required
def maintenance():
    return render_template('maintenance.html', db_path=DB_FILE)

@app.route('/maintenance/backup_db')
@login_required
def backup_db():
    try:
        return send_file(DB_FILE, as_attachment=True, download_name=f"backup_bot_data_{datetime.now().strftime('%Y-%m-%d')}.db")
    except FileNotFoundError:
        flash("ملف قاعدة البيانات غير موجود!", "danger")
        return redirect(url_for('maintenance'))
    except Exception as e:
        flash(f"خطأ أثناء إنشاء النسخة الاحتياطية: {e}", "danger")
        return redirect(url_for('maintenance'))

# --- ✨ مسارات جديدة للسجل المباشر ---

@app.route('/live_logs')
@login_required
def live_logs():
    return render_template('live_logs.html')

@socketio.on('connect')
def handle_connect():
    emit('status', {'msg': 'Connected to server logs.'})

# --- ✨✨✨ (3) الإضافة الثالثة: تم تعديل هذا المسار بالكامل ✨✨✨ ---
@app.route('/task/get_code')
def get_task_code():
    """
    هذه هي "الصفحة السرية" الديناميكية.
    يقوم هذا المسار بالبحث عن كود غير مستخدم وغير محجوز،
    "يحجزه" للمستخدم، ثم يعرضه.
    """
    
    # --- بداية التعديل الأمني ---
    referer = request.headers.get("Referer")
    
    # 1. تحقق من وجود الـ Referer
    if not referer:
        logging.warning(f"Blocked request to /task/get_code. Reason: Missing Referer.")
        # 403 Forbidden
        return "<h1><center>Direct access is not allowed.</center></h1>", 403 

    # 2. تحقق مما إذا كان الـ Referer من الدومينات المسموحة
    try:
        referer_domain = urlparse(referer).netloc
        
        # .endswith() أفضل من 'in' للتحقق من الدومينات (مثل sub.shortener.com)
        if not any(referer_domain.endswith(allowed_domain) for allowed_domain in ALLOWED_REFERERS):
            logging.warning(f"Blocked request to /task/get_code. Reason: Invalid Referer: {referer}")
            return "<h1><center>Invalid referer. Access denied.</center></h1>", 403
    except Exception as e:
        logging.error(f"Error parsing referer: {e}")
        return "<h1><center>An error occurred.</center></h1>", 500
    
    # --- نهاية التعديل الأمني ---

    # إذا نجح التحقق، استمر كالمعتاد
    db = SessionLocal()
    try:
        # 1. ابحث عن كود متاح (غير مستخدم وغير محجوز)
        code = db.query(Code).filter(
            Code.is_used == False,
            Code.is_claimed == False
        ).order_by(func.random()).first()

        if code:
            # 2. "احجز" هذا الكود فوراً
            code.is_claimed = True
            db.commit()
            
            # 3. اعرض الكود للمستخدم في صفحة بسيطة جداً
            return f"""
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="utf-8">
                <title>الكود الخاص بك</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: grid; place-items: center; min-height: 100vh; background-color: #f4f4f4; margin: 0; }}
                    .card {{ background: #fff; padding: 2rem 3rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; }}
                    h1 {{ margin: 0; font-size: 1.25rem; color: #333; }}
                    code {{ display: block; font-size: 3rem; font-weight: bold; color: #d90429; margin-top: 1rem; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>هذا هو الكود الخاص بك لإكمال المهمة:</h1>
                    <code>{code.code_value}</code>
                </div>
            </body>
            </html>
            """
        else:
            # 4. في حال نفاد الأكواد المتاحة
            return "<h1>عذراً، لا توجد مهام متاحة حالياً. يرجى المحاولة لاحقاً أو إبلاغ مدير النظام.</h1>"
            
    except Exception as e:
        db.rollback()
        logging.error(f"Error in get_task_code: {e}")
        return "<h1>حدث خطأ. الرجاء إغلاق الصفحة والمحاولة مرة أخرى.</h1>"
    finally:
        db.close()
# --- نهاية الإضافة ---


# --- ✨ تشغيل الخادم ---
if __name__ == '__main__':
    print("Starting log tailing thread...")
    eventlet.spawn(tail_log_file) # بدء مراقبة السجل في خيط أخضر
    print("Starting Flask-SocketIO server on port 5001...")
    socketio.run(app, debug=True, port=5001, host='0.0.0.0')