"""add promo code tables

Revision ID: bb31dbb22417
Revises: 001
Create Date: 2023-11-15 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb31dbb22417'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Создаем таблицу промокодов
    op.create_table(
        'promo_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('discount_percent', sa.Integer(), nullable=True),
        sa.Column('discount_amount', sa.Integer(), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_promo_codes_id'), 'promo_codes', ['id'], unique=False)
    
    # Создаем таблицу использования промокодов
    op.create_table(
        'promo_code_usages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('promo_code_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['promo_code_id'], ['promo_codes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_promo_code_usages_id'), 'promo_code_usages', ['id'], unique=False)
    
    # Добавляем колонки в таблицу заказов
    op.add_column('orders', sa.Column('promo_code_id', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('discount_amount', sa.Integer(), nullable=True, server_default='0'))
    op.create_foreign_key(
        'fk_orders_promo_code_id', 
        'orders', 'promo_codes', 
        ['promo_code_id'], ['id'], 
        ondelete='SET NULL'
    )


def downgrade():
    # Удаляем внешний ключ и колонки из таблицы заказов
    op.drop_constraint('fk_orders_promo_code_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'discount_amount')
    op.drop_column('orders', 'promo_code_id')
    
    # Удаляем таблицу использования промокодов
    op.drop_index(op.f('ix_promo_code_usages_id'), table_name='promo_code_usages')
    op.drop_table('promo_code_usages')
    
    # Удаляем таблицу промокодов
    op.drop_index(op.f('ix_promo_codes_id'), table_name='promo_codes')
    op.drop_table('promo_codes') 