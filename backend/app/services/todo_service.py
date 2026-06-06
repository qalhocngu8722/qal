import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.todo import Todo
from app.models.tag import Tag
from app.schemas.todo import TodoCreate, BulkStatusUpdate


async def create_todo(
    db: AsyncSession, todo_data: TodoCreate, user_id: uuid.UUID
) -> Todo:
    todo = Todo(
        title=todo_data.title,
        description=todo_data.description,
        user_id=user_id,
    )
    db.add(todo)
    await db.flush()
    await db.refresh(todo)
    return todo


async def get_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    tag_id: uuid.UUID | None = None,
    keyword: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[Todo], int]:
    """Get all todos with pagination and filtering for a specific user."""
    # Build query with filters
    conditions = [Todo.user_id == user_id]

    # Status filter
    if status == "completed":
        conditions.append(Todo.completed == True)  # noqa: E712
    elif status == "active":
        conditions.append(Todo.completed == False)  # noqa: E712

    # Tag filter
    if tag_id:
        conditions.append(Todo.tags.any(Tag.id == tag_id))

    # Keyword filter (search in title and description)
    if keyword:
        keyword_pattern = f"%{keyword}%"
        conditions.append(
            or_(
                Todo.title.ilike(keyword_pattern),
                Todo.description.ilike(keyword_pattern),
            )
        )

    # Date range filter
    if date_from:
        conditions.append(Todo.created_at >= date_from)
    if date_to:
        conditions.append(Todo.created_at <= date_to)

    # Query with filters, ordering, and pagination
    query = (
        select(Todo)
        .where(and_(*conditions))
        .options(selectinload(Todo.tags))
        .order_by(Todo.created_at.desc(), Todo.id.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    todos = list(result.scalars().all())

    # Count total with same filters
    count_query = (
        select(func.count()).select_from(Todo).where(and_(*conditions))
    )
    total = await db.execute(count_query)

    return todos, total.scalar_one()


async def get_todo_by_id(db: AsyncSession, todo_id: uuid.UUID) -> Todo | None:
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id).options(selectinload(Todo.tags))
    )
    return result.scalar_one_or_none()


async def update_todo(db: AsyncSession, todo: Todo, update_data: dict) -> Todo:
    for key, value in update_data.items():
        setattr(todo, key, value)
    await db.flush()
    await db.refresh(todo, attribute_names=["tags"])
    return todo


async def delete_todo(db: AsyncSession, todo: Todo) -> None:
    await db.delete(todo)
    await db.flush()


async def attach_tag_to_todo(
    db: AsyncSession, todo: Todo, tag: Tag
) -> None:
    """Attach a tag to a todo."""
    if tag not in todo.tags:
        todo.tags.append(tag)
        await db.flush()


async def detach_tag_from_todo(
    db: AsyncSession, todo: Todo, tag: Tag
) -> None:
    """Detach a tag from a todo."""
    if tag in todo.tags:
        todo.tags.remove(tag)
        await db.flush()


async def bulk_update_status(
    db: AsyncSession, bulk_data: BulkStatusUpdate, user_id: uuid.UUID
) -> list[Todo]:
    """Bulk update todo status with ownership verification."""
    # Fetch all todos and verify ownership
    result = await db.execute(
        select(Todo)
        .where(
            and_(
                Todo.id.in_(bulk_data.todo_ids),
                Todo.user_id == user_id,
            )
        )
    )
    todos = list(result.scalars().all())

    # Verify all todos exist and belong to user
    if len(todos) != len(bulk_data.todo_ids):
        raise ValueError("Some todos not found or not owned by user")

    # Update all todos
    for todo in todos:
        todo.completed = bulk_data.completed

    await db.flush()
    return todos

