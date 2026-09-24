"""create_users_table

Revision ID: 9a5a5ce827bb
Revises: a8b9498ede6a
Create Date: 2026-09-24 10:47:00.201452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a5a5ce827bb'
down_revision: Union[str, Sequence[str], None] = 'a8b9498ede6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False, comment='Full legal name of the user'),
            sa.Column('email', sa.String(length=255), nullable=False, comment='Authoritative email address used for authentication'),
            sa.Column('password_hash', sa.String(length=255), nullable=False, comment='Secure bcrypt hashed password'),
            sa.Column('role', sa.String(length=20), nullable=False, comment='User role: CITIZEN, OFFICIAL, ADMIN'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Flag indicating active account status'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table('users'):
        op.drop_index(op.f('ix_users_email'), table_name='users')
        op.drop_table('users')
