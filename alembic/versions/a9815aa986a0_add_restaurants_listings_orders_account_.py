"""add restaurants, listings, orders; account_type/is_admin on users; order_id on payments

Revision ID: a9815aa986a0
Revises: 663b3dda8d27
Create Date: 2026-07-16 21:51:18.605120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9815aa986a0'
down_revision: Union[str, Sequence[str], None] = '663b3dda8d27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("account_type", sa.String(length=20), nullable=False, server_default="customer"),
    )
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("restaurant_id", sa.Integer(), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("original_price", sa.Integer(), nullable=False),
        sa.Column("discounted_price", sa.Integer(), nullable=False),
        sa.Column("quantity_available", sa.Integer(), nullable=False),
        sa.Column("pickup_window", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_listings_restaurant_id", "listings", ["restaurant_id"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("customer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending_payment"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_listing_id", "orders", ["listing_id"])
    op.create_index("ix_orders_customer_user_id", "orders", ["customer_user_id"])

    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("order_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_payments_order_id", "orders", ["order_id"], ["id"])
    op.create_index("ix_payments_order_id", "payments", ["order_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_payments_order_id", table_name="payments")
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint("fk_payments_order_id", type_="foreignkey")
        batch_op.drop_column("order_id")

    op.drop_index("ix_orders_customer_user_id", table_name="orders")
    op.drop_index("ix_orders_listing_id", table_name="orders")
    op.drop_table("orders")

    op.drop_index("ix_listings_restaurant_id", table_name="listings")
    op.drop_table("listings")

    op.drop_table("restaurants")

    op.drop_column("users", "is_admin")
    op.drop_column("users", "account_type")
