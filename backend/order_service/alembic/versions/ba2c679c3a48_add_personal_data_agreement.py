"""add_personal_data_agreement

Revision ID: ba2c679c3a48
Revises: bb31dbb22417
Create Date: 2024-03-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba2c679c3a48'
down_revision: Union[str, None] = 'bb31dbb22417'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку personal_data_agreement с значением по умолчанию True для существующих записей
    op.add_column('orders', sa.Column('personal_data_agreement', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    # Удаляем колонку при откате миграции
    op.drop_column('orders', 'personal_data_agreement') 