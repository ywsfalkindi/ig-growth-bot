import random
from sqlalchemy import update

# سنقوم بإنشاء هذه الملفات لاحقاً، لذلك تجاهل أي خطأ مؤقت في الاستيراد
from database.database import SessionLocal
from database.models import Order, Code

def show_and_complete_orders():
    """يعرض الطلبات المعلقة ويتيح للمدير تحديث حالتها."""
    db = SessionLocal()
    try:
        # جلب كل الطلبات التي لم تكتمل بعد
        pending_orders = db.query(Order).filter(Order.is_completed == False).order_by(Order.created_at).all()

        if not pending_orders:
            print("\n✅ لا توجد طلبات معلقة حاليًا. عمل رائع!")
            return

        print("\n--- 🚧 قائمة الطلبات المعلقة 🚧 ---\n")
        for i, order in enumerate(pending_orders):
            print(f"  {i+1}. | اليوزر: {order.username_to_follow:<20} | الكمية: {order.amount} | تاريخ الطلب: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
        print("\n------------------------------------\n")
        
        choice = input("أدخل رقم الطلب الذي قمت بتنفيذه (أو أدخل '0' للعودة للقائمة الرئيسية): ")
        if choice == '0':
            return
            
        order_to_complete = pending_orders[int(choice)-1]
        
        # تحديث حالة الطلب في قاعدة البيانات
        stmt = update(Order).where(Order.id == order_to_complete.id).values(is_completed=True)
        db.execute(stmt)
        db.commit()

        print(f"\n✅ تم تحديث طلب '{order_to_complete.username_to_follow}' بنجاح.")

    except (ValueError, IndexError):
        print("\n❌ إدخال غير صالح. الرجاء إدخال رقم من القائمة.")
    finally:
        db.close()

def add_new_codes():
    """يضيف أكوادًا عشوائية فريدة إلى قاعدة البيانات بكفاءة."""
    db = SessionLocal()
    try:
        count = int(input("كم عدد الأكواد الجديدة التي تريد إنشاؤها؟ "))

        # الخطوة 1: جلب كل الأكواد الموجودة مرة واحدة لتجنب البحث المتكرر
        existing_codes = {c.code_value for c in db.query(Code.code_value).all()}

        new_codes_to_add = []
        generated_in_this_run = set() # لتتبع الأكواد المولدة في هذه الجلسة

        while len(new_codes_to_add) < count:
            new_code_val = str(random.randint(10000, 99999))

            # التحقق من أن الكود ليس موجوداً في قاعدة البيانات أو في الدفعة الحالية
            if new_code_val not in existing_codes and new_code_val not in generated_in_this_run:
                generated_in_this_run.add(new_code_val)
                new_code_obj = Code(code_value=new_code_val)
                new_codes_to_add.append(new_code_obj)

        db.add_all(new_codes_to_add)
        db.commit()
        print(f"\n✅ تم إضافة {len(new_codes_to_add)} كود جديد بنجاح إلى قاعدة البيانات.")

    except ValueError:
        print("\n❌ إدخال غير صالح. الرجاء إدخال رقم صحيح.")
    finally:
        db.close()


def main_menu():
    """يعرض القائمة الرئيسية لمدير النظام."""
    while True:
        print("\n===== لوحة تحكم المدير =====")
        print("1. عرض الطلبات المعلقة وتحديثها")
        print("2. إضافة أكواد جديدة للنظام")
        print("3. خروج")
        print("=============================")
        
        choice = input("اختر الإجراء المطلوب: ")
        
        if choice == '1':
            show_and_complete_orders()
        elif choice == '2':
            add_new_codes()
        elif choice == '3':
            print("\n👋 إلى اللقاء!")
            break
        else:
            print("\n❌ خيار غير صالح. الرجاء المحاولة مرة أخرى.")


if __name__ == "__main__":
    main_menu()