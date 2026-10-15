"""enable row level security

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 15:00:00.000000

RLS ligado sem nenhuma política: papéis que não são donos das tabelas (no Supabase,
`anon` e `authenticated`, usados pela Data API) não enxergam nem alteram nada. A API
conecta como dona das tabelas e não é afetada.

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "alembic_version",
    "fuel",
    "users",
    "fuel_prices",
    "vehicles",
    "shifts",
    "earnings",
    "track_points",
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
