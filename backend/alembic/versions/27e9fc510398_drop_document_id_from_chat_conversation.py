"""drop document_id from chat_conversation

Revision ID: 27e9fc510398
Revises: c921367f43a3
Create Date: 2026-06-21 14:47:05.629595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '27e9fc510398'
down_revision: Union[str, Sequence[str], None] = 'c921367f43a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        'chat_conversation_ibfk_1',   
        'chat_conversation',
        type_='foreignkey'
    )

    op.drop_index(
        'ix_chat_conversation_document_id',
        table_name='chat_conversation'
    )

    op.drop_column('chat_conversation', 'document_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('chat_conversation',
        sa.Column('document_id', sa.String(36), nullable=True)
    )
    op.create_index(
        'ix_chat_conversation_document_id',
        'chat_conversation', ['document_id']
    )
    op.create_foreign_key(
        'chat_conversation_ibfk_1',
        'chat_conversation', 'document',
        ['document_id'], ['id'],
        ondelete='CASCADE'
    )