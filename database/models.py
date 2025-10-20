import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date

# نستورد الفئة الأساسية التي أنشأناها في الملف السابق
# النقطة في البداية تعني "من نفس المجلد الحالي"
from .database import Base

# Model for Users Table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    ig_user_id = Column(String, unique=True, index=True) # ID المستخدم الفريد من انستجرام
    username = Column(String, unique=True)
    points = Column(Integer, default=0)
    
    # --- التحسينات الأسطورية تبدأ هنا ---
    tasks_completed = Column(Integer, default=0) # عداد للمهام المكتملة
    level = Column(Integer, default=1) # مستوى المستخدم
    last_task_date = Column(Date, default=None) # لتتبع تاريخ آخر مهمة (للمكافآت اليومية)
    streak = Column(Integer, default=0) # لتتبع سلسلة الإنجازات اليومية


# Model for Codes Table
class Code(Base):
    __tablename__ = "codes"

    id = Column(Integer, primary_key=True, index=True)
    code_value = Column(String, unique=True, index=True) # الكود المكون من 5 أرقام
    is_used = Column(Boolean, default=False) # لتحديد ما إذا كان الكود قد استُخدم


# Model for Orders Table
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    username_to_follow = Column(String) # الحساب المطلوب إرسال المتابعين إليه
    amount = Column(Integer) # عدد المتابعين المطلوب
    ordered_by_user_id = Column(String, index=True) # ID المستخدم الذي قدم الطلب
    created_at = Column(DateTime, default=datetime.datetime.utcnow) # تاريخ إنشاء الطلب
    is_completed = Column(Boolean, default=False) # لتحديد ما إذا كنت قد نفذت الطلب