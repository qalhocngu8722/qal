import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_attach_tag_to_todo(client: AsyncClient, user_token: str):
    """Test attaching a tag to a todo."""
    # Create tag
    tag_response = await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tag_id = tag_response.json()["id"]

    # Create todo
    todo_response = await client.post(
        "/api/v1/todos",
        json={"title": "Test task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todo_id = todo_response.json()["id"]

    # Attach tag
    response = await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        params={"tag_id": tag_id},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 204

    # Verify tag attached
    get_response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todo = get_response.json()
    assert len(todo["tags"]) == 1
    assert todo["tags"][0]["id"] == tag_id


@pytest.mark.asyncio
async def test_prevent_attaching_another_users_tag(
    client: AsyncClient, user_token: str, another_user_token: str
):
    """Test that users cannot attach another user's tag to their todo."""
    # User 1 creates a tag
    tag_response = await client.post(
        "/api/v1/tags",
        json={"name": "Private"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tag_id = tag_response.json()["id"]

    # User 2 creates a todo
    todo_response = await client.post(
        "/api/v1/todos",
        json={"title": "Test task"},
        headers={"Authorization": f"Bearer {another_user_token}"},
    )
    todo_id = todo_response.json()["id"]

    # User 2 tries to attach User 1's tag
    response = await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        params={"tag_id": tag_id},
        headers={"Authorization": f"Bearer {another_user_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_detach_tag_from_todo(client: AsyncClient, user_token: str):
    """Test detaching a tag from a todo."""
    # Create tag and todo
    tag_response = await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tag_id = tag_response.json()["id"]

    todo_response = await client.post(
        "/api/v1/todos",
        json={"title": "Test task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todo_id = todo_response.json()["id"]

    # Attach tag
    await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        params={"tag_id": tag_id},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Detach tag
    response = await client.delete(
        f"/api/v1/todos/{todo_id}/tags/{tag_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 204

    # Verify tag detached
    get_response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todo = get_response.json()
    assert len(todo["tags"]) == 0


@pytest.mark.asyncio
async def test_filter_todos_by_tag(client: AsyncClient, user_token: str):
    """Test filtering todos by tag."""
    # Create tags
    work_tag_response = await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    work_tag_id = work_tag_response.json()["id"]

    personal_tag_response = await client.post(
        "/api/v1/tags",
        json={"name": "Personal"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    personal_tag_id = personal_tag_response.json()["id"]

    # Create todos
    work_todo_response = await client.post(
        "/api/v1/todos",
        json={"title": "Work task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    work_todo_id = work_todo_response.json()["id"]

    personal_todo_response = await client.post(
        "/api/v1/todos",
        json={"title": "Personal task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    personal_todo_id = personal_todo_response.json()["id"]

    # Attach tags
    await client.post(
        f"/api/v1/todos/{work_todo_id}/tags",
        params={"tag_id": work_tag_id},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    await client.post(
        f"/api/v1/todos/{personal_todo_id}/tags",
        params={"tag_id": personal_tag_id},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Filter by work tag
    response = await client.get(
        "/api/v1/todos",
        params={"tag_id": work_tag_id},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    todos = response.json()["items"]
    assert len(todos) == 1
    assert todos[0]["title"] == "Work task"


@pytest.mark.asyncio
async def test_filter_todos_by_status(client: AsyncClient, user_token: str):
    """Test filtering todos by completion status."""
    # Create todos
    await client.post(
        "/api/v1/todos",
        json={"title": "Active task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    
    completed_response = await client.post(
        "/api/v1/todos",
        json={"title": "Completed task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    completed_id = completed_response.json()["id"]

    # Mark second todo as completed
    await client.put(
        f"/api/v1/todos/{completed_id}",
        json={"completed": True},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Filter by active status
    response = await client.get(
        "/api/v1/todos",
        params={"status": "active"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todos = response.json()["items"]
    assert all(not todo["completed"] for todo in todos)

    # Filter by completed status
    response = await client.get(
        "/api/v1/todos",
        params={"status": "completed"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todos = response.json()["items"]
    assert all(todo["completed"] for todo in todos)


@pytest.mark.asyncio
async def test_filter_todos_by_keyword(client: AsyncClient, user_token: str):
    """Test filtering todos by keyword."""
    # Create todos
    await client.post(
        "/api/v1/todos",
        json={"title": "Buy groceries", "description": "milk and eggs"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    await client.post(
        "/api/v1/todos",
        json={"title": "Fix bug", "description": "resolve issue #123"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Search for "groceries"
    response = await client.get(
        "/api/v1/todos",
        params={"keyword": "groceries"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todos = response.json()["items"]
    assert len(todos) >= 1
    assert any("groceries" in todo["title"].lower() for todo in todos)


@pytest.mark.asyncio
async def test_bulk_update_status(client: AsyncClient, user_token: str):
    """Test bulk updating todo status."""
    # Create multiple todos
    todo_ids = []
    for i in range(3):
        response = await client.post(
            "/api/v1/todos",
            json={"title": f"Task {i}"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        todo_ids.append(response.json()["id"])

    # Bulk update to completed
    response = await client.patch(
        "/api/v1/todos/bulk-status",
        json={"todo_ids": todo_ids, "completed": True},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 204

    # Verify all todos are completed
    for todo_id in todo_ids:
        get_response = await client.get(
            f"/api/v1/todos/{todo_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert get_response.json()["completed"] is True


@pytest.mark.asyncio
async def test_bulk_update_ownership_check(
    client: AsyncClient, user_token: str, another_user_token: str
):
    """Test that bulk update verifies ownership of all todos."""
    # User 1 creates a todo
    user1_response = await client.post(
        "/api/v1/todos",
        json={"title": "User 1 task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    user1_todo_id = user1_response.json()["id"]

    # User 2 creates a todo
    user2_response = await client.post(
        "/api/v1/todos",
        json={"title": "User 2 task"},
        headers={"Authorization": f"Bearer {another_user_token}"},
    )
    user2_todo_id = user2_response.json()["id"]

    # User 2 tries to bulk update including User 1's todo
    response = await client.patch(
        "/api/v1/todos/bulk-status",
        json={"todo_ids": [user1_todo_id, user2_todo_id], "completed": True},
        headers={"Authorization": f"Bearer {another_user_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cache_invalidation_after_tag_attachment(
    client: AsyncClient, user_token: str
):
    """Test that cache is invalidated after tag attachment."""
    # Create tag and todo
    tag_response = await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tag_id = tag_response.json()["id"]

    todo_response = await client.post(
        "/api/v1/todos",
        json={"title": "Test task"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todo_id = todo_response.json()["id"]

    # Fetch todos (populate cache)
    await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Attach tag
    await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        params={"tag_id": tag_id},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Fetch todos again (should get fresh data with tags)
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    todos = response.json()["items"]
    todo = next(t for t in todos if t["id"] == todo_id)
    assert len(todo["tags"]) == 1
