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
    is_banned = Column(Boolean, default=False) 

    orders = relationship("Order", back_populates="owner")
    point_logs = relationship("PointLog", back_populates="user", cascade="all, delete-orphan")

class Code(Base):
    __tablename__ = "codes"
    id = Column(Integer, primary_key=True, index=True)
    code_value = Column(String, unique=True, index=True)
    is_used = Column(Boolean, default=False)
    
    # --- ✨✨✨ هذا هو السطر الجديد ✨✨✨ ---
    is_claimed = Column(Boolean, default=False, index=True)
    # --- نهاية الإضافة ---

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    username_to_follow = Column(String)
    amount = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_completed = Column(Boolean, default=False)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="orders")

class PointLog(Base):
    __tablename__ = "point_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points_change = Column(Integer, nullable=False)
    reason = Column(String, nullable=False) 
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="point_logs")