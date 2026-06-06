import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate


async def create_tag(
    db: AsyncSession, tag_data: TagCreate, user_id: uuid.UUID
) -> Tag:
    """Create a new tag for a user."""
    # Check for duplicate tag name (case-insensitive)
    existing = await db.execute(
        select(Tag).where(
            Tag.user_id == user_id,
            func.lower(Tag.name) == tag_data.name.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Tag name already exists")

    tag = Tag(
        user_id=user_id,
        name=tag_data.name,
        color=tag_data.color,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def get_tags(db: AsyncSession, user_id: uuid.UUID) -> tuple[list[Tag], int]:
    """Get all tags for a specific user."""
    query = select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
    result = await db.execute(query)
    tags = list(result.scalars().all())

    # Count total
    count_query = select(func.count()).select_from(Tag).where(Tag.user_id == user_id)
    total = await db.execute(count_query)

    return tags, total.scalar_one()


async def get_tag_by_id(db: AsyncSession, tag_id: uuid.UUID) -> Tag | None:
    """Get a tag by ID."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    return result.scalar_one_or_none()


async def update_tag(
    db: AsyncSession, tag: Tag, update_data: TagUpdate
) -> Tag:
    """Update a tag."""
    # Check for duplicate name if name is being updated
    if update_data.name is not None:
        existing = await db.execute(
            select(Tag).where(
                Tag.user_id == tag.user_id,
                Tag.id != tag.id,
                func.lower(Tag.name) == update_data.name.lower(),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Tag name already exists")
        tag.name = update_data.name

    if update_data.color is not None:
        tag.color = update_data.color

    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    """Delete a tag and all its associations."""
    await db.delete(tag)
    await db.commit()
