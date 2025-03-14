from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import context
from models import Base, CategoryModel, CountryModel, BrandModel, ProductModel, SubCategoryModel

config = context.config

# Устанавливаем метаданные моделей для автогенерации миграций
target_metadata = Base.metadata

print("Target Metadata:", target_metadata)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Убедитесь, что здесь НЕ происходит переопределение target_metadata на None!
# target_metadata = None  <-- удалите или закомментируйте эту строку

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
