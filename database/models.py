import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    ig_user_id = Column(String, unique=True, index=True)
    username = Column(String, unique=True)
    points = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    level = Column(Integer, default=1)
    last_task_date = Column(Date, default=None)
    streak = Column(Integer, default=0)
    referral_code = Column(String, unique=True, index=True, nullable=True)
    referred_by_user_id = Column(String, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_banned = Column(Boolean, default=False) # <<-- ✨ الحقل الجديد

    # --- ✨ علاقات جديدة لعرض البيانات ---
    orders = relationship("Order", back_populates="owner")
    point_logs = relationship("PointLog", back_populates="user", cascade="all, delete-orphan")

class Code(Base):
    # ... (لا تغيير هنا)
    __tablename__ = "codes"
    id = Column(Integer, primary_key=True, index=True)
    code_value = Column(String, unique=True, index=True)
    is_used = Column(Boolean, default=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    username_to_follow = Column(String)
    amount = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_completed = Column(Boolean, default=False)

    # --- ✨ تعديل لربط الطلب بصاحبه ---
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="orders")

# --- ✨ جدول جديد بالكامل لتسجيل حركة النقاط ---
class PointLog(Base):
    __tablename__ = "point_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points_change = Column(Integer, nullable=False)
    reason = Column(String, nullable=False) # e.g., "مهمة ناجحة", "هدية من المدير"
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="point_logs")