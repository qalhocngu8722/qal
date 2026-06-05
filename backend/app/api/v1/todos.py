import hashlib
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis
from app.core.redis import RedisClient
from app.db.session import get_db
from app.models.user import User
from app.schemas.todo import BulkStatusUpdate, TodoCreate, TodoListResponse, TodoResponse, TodoUpdate
from app.services.todo_service import (
    attach_tag_to_todo,
    bulk_update_status,
    create_todo,
    delete_todo,
    detach_tag_from_todo,
    get_todo_by_id,
    get_todos,
    update_todo,
)
from app.services.tag_service import get_tag_by_id

router = APIRouter()

CACHE_TTL = 300  # 5 minutes


@router.get("", response_model=TodoListResponse)
async def list_todos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=10000),
    status: str | None = Query(None, pattern="^(completed|active)$"),
    tag_id: uuid.UUID | None = Query(None),
    keyword: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Get paginated list of todos with filtering for the current user."""
    skip = (page - 1) * size

    # Build cache key with all filter parameters
    filter_params = {
        "user_id": str(current_user.id),
        "page": page,
        "size": size,
        "status": status,
        "tag_id": str(tag_id) if tag_id else None,
        "keyword": keyword,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }
    # Create a hash of filter params for consistent cache key
    filter_hash = hashlib.md5(
        json.dumps(filter_params, sort_keys=True).encode()
    ).hexdigest()
    cache_key = f"todos:user:{current_user.id}:filters:{filter_hash}"

    # Try to get from cache
    cached = await redis.get(cache_key)
    if cached:
        cached_data = json.loads(cached)
        return TodoListResponse(**cached_data)

    todos, total = await get_todos(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=size,
        status=status,
        tag_id=tag_id,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )

    # Build response items with user_email
    items = []
    for todo in todos:
        # Access tags before creating response (while in async context)
        tags_list = todo.tags  # This triggers the eager-loaded relationship
        
        user_result = await db.execute(select(User).where(User.id == todo.user_id))
        user = user_result.scalar_one_or_none()
        
        items.append(
            TodoResponse(
                id=todo.id,
                title=todo.title,
                description=todo.description,
                completed=todo.completed,
                user_id=todo.user_id,
                created_at=todo.created_at,
                updated_at=todo.updated_at,
                user_email=user.email if user else None,
                tags=tags_list,
            )
        )

    response = TodoListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
    )

    # Cache the response
    await redis.set(cache_key, response.model_dump_json(), ex=CACHE_TTL)

    return response


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_new_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Create a new todo item for the current user."""
    todo = await create_todo(db, todo_data, current_user.id)
    
    # Invalidate all cache keys for this user
    await invalidate_user_cache(redis, current_user.id)
    
    # Get user email for response
    user_result = await db.execute(select(User).where(User.id == todo.user_id))
    user = user_result.scalar_one_or_none()
    
    # Build response with user_email and tags
    return TodoResponse(
        id=todo.id,
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        user_id=todo.user_id,
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        user_email=user.email if user else None,
        tags=todo.tags,
    )


async def invalidate_user_cache(redis: RedisClient, user_id: uuid.UUID):
    """Invalidate all cached todo lists for a specific user."""
    if not redis.is_available or not redis.client:
        return
    
    try:
        # Redis SCAN to find all keys matching pattern
        cursor = 0
        pattern = f"todos:user:{user_id}:*"
        keys_to_delete = []
        
        while True:
            cursor, keys = await redis.client.scan(cursor, match=pattern, count=100)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break
        
        if keys_to_delete:
            await redis.client.delete(*keys_to_delete)
    except Exception:
        # Silently fail if cache invalidation fails
        pass


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific todo by ID. Only owner can access."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    
    # Authorization check: verify owner
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this todo",
        )

    return todo


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_existing_todo(
    todo_id: uuid.UUID,
    todo_data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Update a todo item. Only owner can update."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    
    # Authorization check: verify owner
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this todo",
        )

    # Build update dict with only provided fields
    update_data = {}
    if todo_data.title is not None:
        update_data["title"] = todo_data.title
    if todo_data.description is not None:
        update_data["description"] = todo_data.description
    if todo_data.completed is not None:
        update_data["completed"] = todo_data.completed

    updated_todo = await update_todo(db, todo, update_data)
    
    # Invalidate cache for this user
    await invalidate_user_cache(redis, current_user.id)

    return updated_todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Delete a todo item. Only owner can delete."""
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    
    # Authorization check: verify owner
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this todo",
        )

    await delete_todo(db, todo)
    
    # Invalidate cache for this user
    await invalidate_user_cache(redis, current_user.id)

    return None


@router.post("/{todo_id}/tags", status_code=status.HTTP_204_NO_CONTENT)
async def attach_tag(
    todo_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Attach a tag to a todo. Only owner can attach tags."""
    # Get and verify todo ownership
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this todo",
        )

    # Get and verify tag ownership
    tag = await get_tag_by_id(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to use this tag",
        )

    await attach_tag_to_todo(db, todo, tag)

    # Invalidate cache for this user
    await invalidate_user_cache(redis, current_user.id)

    return None


@router.delete("/{todo_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_tag(
    todo_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Detach a tag from a todo. Only owner can detach tags."""
    # Get and verify todo ownership
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found",
        )
    if todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this todo",
        )

    # Get and verify tag ownership
    tag = await get_tag_by_id(db, tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    if tag.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to use this tag",
        )

    await detach_tag_from_todo(db, todo, tag)

    # Invalidate cache for this user
    await invalidate_user_cache(redis, current_user.id)

    return None


@router.patch("/bulk-status", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_update_todo_status(
    bulk_data: BulkStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """Bulk update todo status. Only owner can update their todos."""
    try:
        await bulk_update_status(db, bulk_data, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Invalidate cache for this user
    await invalidate_user_cache(redis, current_user.id)

    return None
