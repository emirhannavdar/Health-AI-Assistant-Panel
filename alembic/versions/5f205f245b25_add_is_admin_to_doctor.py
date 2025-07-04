"""add is_admin to doctor

Revision ID: 5f205f245b25
Revises: 93fbcd41a341
Create Date: 2025-07-04 12:46:56.861996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f205f245b25'
down_revision: Union[str, Sequence[str], None] = '93fbcd41a341'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('doctors', sa.Column('is_admin', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('doctors', 'is_admin')
    # ### end Alembic commands ###
