from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# نستورد رابط قاعدة البيانات من ملف الإعدادات الرئيسي
from config import DATABASE_URL

# الخطوة 1: إنشاء "محرك" الاتصال بقاعدة البيانات
# هذا المحرك هو نقطة الدخول الأساسية لقاعدة البيانات
# connect_args مهم بشكل خاص لـ SQLite للسماح بالاتصال من مسارات متعددة
engine = create_engine(
    DATABASE_URL
)

# الخطوة 2: إنشاء "صانع جلسات"
# الجلسة (Session) هي محادثتك الفردية مع قاعدة البيانات (لإرسال استعلامات أو حفظ بيانات)
# هذا السطر ينشئ "مصنعًا" يمكننا من خلاله طلب جلسة جديدة كلما احتجنا إليها
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# الخطوة 3: إنشاء "الفئة الأساسية" للنماذج
# كل جداولنا في قاعدة البيانات (مثل جدول المستخدمين أو الطلبات) سترث من هذه الفئة
# هذه هي الطريقة التي يعرف بها SQLAlchemy أن هذه الفئات يجب أن ترتبط بجداول في قاعدة البيانات
Base = declarative_base()