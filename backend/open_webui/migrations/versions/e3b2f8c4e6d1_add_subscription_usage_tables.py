"""Add subscription and usage tracking tables

Revision ID: e3b2f8c4e6d1
Revises: d31026856c01
Create Date: 2025-12-11 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "e3b2f8c4e6d1"
down_revision = "3e0e00844bb0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscription_plan",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("tokens_per_seat", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "client",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("subscription_plan_id", sa.Integer(), sa.ForeignKey("subscription_plan.id"), nullable=True),
        sa.Column("seats_purchased", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_reset_date", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "usage_per_user",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("client.id"), nullable=True),
        sa.Column("used_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", name="uq_usage_per_user_user_id"),
    )


def downgrade():
    op.drop_table("usage_per_user")
    op.drop_table("client")
    op.drop_table("subscription_plan")


