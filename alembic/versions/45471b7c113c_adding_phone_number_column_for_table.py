"""Adding phone number column for table

Revision ID: 45471b7c113c
Revises: 6abe7ee9f268
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "45471b7c113c"
down_revision: Union[str, Sequence[str], None] = "6abe7ee9f268"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("phone_number", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "phone_number")
