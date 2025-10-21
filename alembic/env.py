import os
import sys

from logging.config import fileConfig

# --- ✨✨✨ 1. التعديل الأول: استيراد create_engine ✨✨✨ ---
from sqlalchemy import create_engine
from sqlalchemy import pool
# (لم نعد بحاجة إلى engine_from_config)

from alembic import context

# --- ✨✨✨ 2. الإضافة الخاصة بك (صحيحة) ✨✨✨ ---
# (هذا الكود صحيح لإضافة مجلدك للمسار)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import DATABASE_URL  # استيراد رابط قاعدة البيانات
from database.models import Base # استيراد النماذج (Models)
# --- نهاية الإضافة ---


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# --- ✨✨✨ 3. الإضافة الخاصة بك (صحيحة) ✨✨✨ ---
target_metadata = Base.metadata
# --- نهاية الإضافة ---


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    ...
    """
    
    # --- ✨✨✨ 4. تعديل بسيط (اختياري ولكنه أفضل) ✨✨✨ ---
    # نستخدم الرابط الصحيح مباشرة بدلاً من الاعتماد على ملف .ini
    url = DATABASE_URL 
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    ...
    """

    # --- ✨✨✨ 5. التعديل الأهم (لحل المشكلة) ✨✨✨ ---
    
    # (هذا هو الكود القديم الذي سبب المشكلة)
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    # (هذا هو الكود الجديد الصحيح)
    connectable = create_engine(DATABASE_URL)
    # --- نهاية التعديل ---


    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()