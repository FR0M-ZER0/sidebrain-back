"""une migracoes de memoria e jobs

Revision ID: ba45c6d0fcbd
Revises: a92b8c9d0e1f, sdb109jobupdates
Create Date: 2026-11-19 00:18:44.417885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba45c6d0fcbd'
down_revision: Union[str, Sequence[str], None] = ('a92b8c9d0e1f', 'sdb109jobupdates')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
