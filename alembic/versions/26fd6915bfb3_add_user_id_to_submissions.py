"""add user_id to submissions

Revision ID: 26fd6915bfb3
Revises: 75c65d934e72
Create Date: 2026-10-15 22:23:08.316603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26fd6915bfb3'
down_revision: Union[str, Sequence[str], None] = '75c65d934e72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_submissions_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_submissions_user_id_users',   # ★ 显式命名
            'users',
            ['user_id'],
            ['id'],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_submissions_user_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_submissions_user_id'))
        batch_op.drop_column('user_id')
