"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-28 10:53:15.888159

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fuel",
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuel")),
        sa.UniqueConstraint("name", name=op.f("uq_fuel_name")),
    )
    op.create_table(
        "users",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "fuel_prices",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("fuel_id", sa.Uuid(), nullable=False),
        sa.Column("price_per_liter", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "price_per_liter > 0", name=op.f("ck_fuel_prices_price_per_liter_positive")
        ),
        sa.ForeignKeyConstraint(["fuel_id"], ["fuel.id"], name=op.f("fk_fuel_prices_fuel_id_fuel")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_fuel_prices_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuel_prices")),
    )
    op.create_index(
        "ix_fuel_prices_user_fuel_valid_from",
        "fuel_prices",
        ["user_id", "fuel_id", "valid_from"],
        unique=False,
    )
    op.create_table(
        "vehicles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("fuel_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("declared_kml", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("displacement_cc", sa.Integer(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("declared_kml > 0", name=op.f("ck_vehicles_declared_kml_positive")),
        sa.CheckConstraint(
            "displacement_cc > 0", name=op.f("ck_vehicles_displacement_cc_positive")
        ),
        sa.ForeignKeyConstraint(["fuel_id"], ["fuel.id"], name=op.f("fk_vehicles_fuel_id_fuel")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_vehicles_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vehicles")),
    )
    op.create_index(op.f("ix_vehicles_user_id"), "vehicles", ["user_id"], unique=False)
    op.create_table(
        "shifts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("fuel_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", sa.Enum("in_progress", "finished", name="shift_status"), nullable=False
        ),
        sa.Column("price_per_liter_used", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("kml_used", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("distance_km", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("idle_minutes", sa.Integer(), nullable=True),
        sa.Column("fuel_cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("earnings_total", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("profit", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("profit_per_hour", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("profit_per_km", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["fuel_id"], ["fuel.id"], name=op.f("fk_shifts_fuel_id_fuel")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_shifts_user_id_users")),
        sa.ForeignKeyConstraint(
            ["vehicle_id"], ["vehicles.id"], name=op.f("fk_shifts_vehicle_id_vehicles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shifts")),
    )
    op.create_index("ix_shifts_user_started_at", "shifts", ["user_id", "started_at"], unique=False)
    op.create_index(op.f("ix_shifts_vehicle_id"), "shifts", ["vehicle_id"], unique=False)
    op.create_index(
        "uq_shifts_user_in_progress",
        "shifts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )
    op.create_table(
        "earnings",
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("ck_earnings_amount_positive")),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["shifts.id"],
            name=op.f("fk_earnings_shift_id_shifts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_earnings")),
    )
    op.create_index(
        "ix_earnings_shift_earned_at", "earnings", ["shift_id", "earned_at"], unique=False
    )
    op.create_table(
        "track_points",
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("accuracy_m", sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column("speed_ms", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90", name=op.f("ck_track_points_latitude_range")
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180", name=op.f("ck_track_points_longitude_range")
        ),
        sa.ForeignKeyConstraint(
            ["shift_id"],
            ["shifts.id"],
            name=op.f("fk_track_points_shift_id_shifts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_track_points")),
        sa.UniqueConstraint("shift_id", "recorded_at", name="uq_track_points_shift_recorded_at"),
    )

    fuel = sa.table("fuel", sa.column("id", sa.Uuid()), sa.column("name", sa.String()))
    op.bulk_insert(
        fuel,
        [
            {"id": uuid.UUID("00000000-0000-4000-8000-000000000001"), "name": "Gasolina"},
            {"id": uuid.UUID("00000000-0000-4000-8000-000000000002"), "name": "Etanol"},
            {"id": uuid.UUID("00000000-0000-4000-8000-000000000003"), "name": "Flex"},
        ],
    )


def downgrade() -> None:
    op.drop_table("track_points")
    op.drop_index("ix_earnings_shift_earned_at", table_name="earnings")
    op.drop_table("earnings")
    op.drop_index(
        "uq_shifts_user_in_progress",
        table_name="shifts",
        postgresql_where=sa.text("status = 'in_progress'"),
    )
    op.drop_index(op.f("ix_shifts_vehicle_id"), table_name="shifts")
    op.drop_index("ix_shifts_user_started_at", table_name="shifts")
    op.drop_table("shifts")
    op.drop_index(op.f("ix_vehicles_user_id"), table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_fuel_prices_user_fuel_valid_from", table_name="fuel_prices")
    op.drop_table("fuel_prices")
    op.drop_table("users")
    op.drop_table("fuel")
    sa.Enum(name="shift_status").drop(op.get_bind(), checkfirst=True)
