"""add receive_notifications field

Revision ID: add_receive_notifications_field
Revises: ba2c679c3a48
Create Date: 2023-05-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_receive_notifications_field'
down_revision = 'ba2c679c3a48'  # Указываем ID предыдущей миграции
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем новую колонку в таблицу orders
    op.add_column('orders', sa.Column('receive_notifications', sa.Boolean(), nullable=True))


def downgrade():
    # Удаляем колонку при откате миграции
    op.drop_column('orders', 'receive_notifications')