"""Clear resource_cache: entries from before the English-only, ranked resource rules

Cache keys now carry a rules version, so old rows would never be read again.
Deleting them keeps the table clean. Saved roadmaps keep their own copies of
their links; refresh those with `python -m app.scripts.refresh_resources`.

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2026-11-24 00:00:00.000000

"""
from typing import Union
from alembic import op

revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, None] = 'f2g3h4i5j6k7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM resource_cache")


def downgrade() -> None:
    # Deleted cache rows are regenerated on demand; nothing to restore.
    pass
