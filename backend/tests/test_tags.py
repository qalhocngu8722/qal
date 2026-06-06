import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_tag_success(client: AsyncClient, user_token: str):
    """Test successful tag creation."""
    response = await client.post(
        "/api/v1/tags",
        json={"name": "Work", "color": "#FF0000"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Work"
    assert data["color"] == "#FF0000"
    assert "id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_create_duplicate_tag_case_insensitive(
    client: AsyncClient, user_token: str
):
    """Test that duplicate tag names are rejected (case-insensitive)."""
    # Create first tag
    await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Try to create duplicate with different casing
    response = await client.post(
        "/api/v1/tags",
        json={"name": "WORK"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_tags(client: AsyncClient, user_token: str):
    """Test listing tags."""
    # Create some tags
    await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    await client.post(
        "/api/v1/tags",
        json={"name": "Personal"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    response = await client.get(
        "/api/v1/tags",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_update_tag(client: AsyncClient, user_token: str):
    """Test updating a tag."""
    # Create tag
    create_response = await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tag_id = create_response.json()["id"]

    # Update tag
    response = await client.patch(
        f"/api/v1/tags/{tag_id}",
        json={"name": "Business", "color": "#00FF00"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Business"
    assert data["color"] == "#00FF00"


@pytest.mark.asyncio
async def test_delete_tag(client: AsyncClient, user_token: str):
    """Test deleting a tag."""
    # Create tag
    create_response = await client.post(
        "/api/v1/tags",
        json={"name": "Work"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tag_id = create_response.json()["id"]

    # Delete tag
    response = await client.delete(
        f"/api/v1/tags/{tag_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 204

    # Verify deletion
    get_response = await client.get(
        "/api/v1/tags",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tags = get_response.json()["items"]
    assert not any(tag["id"] == tag_id for tag in tags)


@pytest.mark.asyncio
async def test_cross_user_tag_access_prevention(
    client: AsyncClient, user_token: str, another_user_token: str
):
    """Test that users cannot access other users' tags."""
    # User 1 creates a tag
    create_response = await client.post(
        "/api/v1/tags",
        json={"name": "Private"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    tag_id = create_response.json()["id"]

    # User 2 tries to update it
    response = await client.patch(
        f"/api/v1/tags/{tag_id}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {another_user_token}"},
    )
    assert response.status_code == 403

    # User 2 tries to delete it
    response = await client.delete(
        f"/api/v1/tags/{tag_id}",
        headers={"Authorization": f"Bearer {another_user_token}"},
    )
    assert response.status_code == 403
