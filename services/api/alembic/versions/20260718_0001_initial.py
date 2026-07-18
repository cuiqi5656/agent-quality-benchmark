"""Initial AQB persistence model."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260718_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep migration creation deterministic and in sync with SQLAlchemy metadata.
    from aqb_api import tables  # noqa: F401
    from aqb_api.db import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from aqb_api import tables  # noqa: F401
    from aqb_api.db import Base

    Base.metadata.drop_all(bind=op.get_bind())
