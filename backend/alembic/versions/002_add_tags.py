"""Add tags and todo_tags tables

Revision ID: 002_add_tags
Revises: a0790c76a129
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_tags"
down_revision: Union[str, None] = "a0790c76a129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Create index on user_id for better query performance
    op.create_index("ix_tags_user_id", "tags", ["user_id"])
    
    # Create unique constraint for case-insensitive tag names per user
    # Using expression index for case-insensitive uniqueness
    op.create_index(
        "ix_tags_user_id_name_lower",
        "tags",
        [sa.text("user_id"), sa.text("LOWER(name)")],
        unique=True,
    )

    # Create todo_tags association table
    op.create_table(
        "todo_tags",
        sa.Column("todo_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["todos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("todo_id", "tag_id"),
    )
    # Create indexes for better query performance
    op.create_index("ix_todo_tags_todo_id", "todo_tags", ["todo_id"])
    op.create_index("ix_todo_tags_tag_id", "todo_tags", ["tag_id"])

    # Create composite index on todos for filtering
    op.create_index(
        "ix_todos_user_id_completed_created_at",
        "todos",
        ["user_id", "completed", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_todos_user_id_completed_created_at", table_name="todos")
    op.drop_index("ix_todo_tags_tag_id", table_name="todo_tags")
    op.drop_index("ix_todo_tags_todo_id", table_name="todo_tags")
    op.drop_table("todo_tags")
    op.drop_index("ix_tags_user_id_name_lower", table_name="tags")
    op.drop_index("ix_tags_user_id", table_name="tags")
    op.drop_table("tags")
