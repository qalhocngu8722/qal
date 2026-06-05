"""Security tests for JWT and authorization."""

import pytest
from httpx import AsyncClient
from app.core.security import create_access_token, create_refresh_token
from datetime import datetime, timedelta, timezone


async def create_two_users(client: AsyncClient) -> tuple[str, str, str, str]:
    """Helper to create two users and return their tokens."""
    # User 1
    response1 = await client.post(
        "/api/v1/auth/register",
        json={"email": "user1@test.com", "password": "password123"},
    )
    user1_token = response1.json()["access_token"]
    user1_id = response1.json()["access_token"]  # We'll decode if needed
    
    # User 2
    response2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "user2@test.com", "password": "password123"},
    )
    user2_token = response2.json()["access_token"]
    user2_id = response2.json()["access_token"]
    
    return user1_token, user1_id, user2_token, user2_id


@pytest.mark.asyncio
async def test_jwt_expiration_is_verified(client: AsyncClient):
    """Test that expired tokens are rejected."""
    # Create an expired token
    expired_token = create_access_token(
        data={"sub": "00000000-0000-0000-0000-000000000001"},
        expires_delta=timedelta(seconds=-10)  # Already expired
    )
    
    # Try to use the expired token
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_type_verification(client: AsyncClient):
    """Test that access tokens cannot be used as refresh tokens."""
    # Register and get access token
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "token@test.com", "password": "password123"},
    )
    access_token = reg_response.json()["access_token"]
    
    # Try to use access token for refresh (should fail)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_validates_user_exists(client: AsyncClient):
    """Test that refresh token checks if user still exists."""
    # Create a valid refresh token for non-existent user
    fake_refresh = create_refresh_token(
        data={"sub": "99999999-9999-9999-9999-999999999999"}
    )
    
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": fake_refresh},
    )
    assert response.status_code == 401
    assert "User not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_cannot_access_other_user_todo(client: AsyncClient):
    """Test data isolation: User A cannot access User B's todos."""
    user1_token, _, user2_token, _ = await create_two_users(client)
    
    # User 1 creates a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "User 1's secret todo"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    todo_id = create_response.json()["id"]
    
    # User 2 tries to access User 1's todo
    response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_cannot_update_other_user_todo(client: AsyncClient):
    """Test data isolation: User A cannot update User B's todos."""
    user1_token, _, user2_token, _ = await create_two_users(client)
    
    # User 1 creates a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Original title"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    todo_id = create_response.json()["id"]
    
    # User 2 tries to update User 1's todo
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Hacked title"},
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_delete_other_user_todo(client: AsyncClient):
    """Test data isolation: User A cannot delete User B's todos."""
    user1_token, _, user2_token, _ = await create_two_users(client)
    
    # User 1 creates a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Don't delete me"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    todo_id = create_response.json()["id"]
    
    # User 2 tries to delete User 1's todo
    response = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    assert response.status_code == 403
    
    # Verify todo still exists for user 1
    get_response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    assert get_response.status_code == 200


@pytest.mark.asyncio
async def test_user_only_sees_own_todos_in_list(client: AsyncClient):
    """Test data isolation: Users only see their own todos in list."""
    user1_token, _, user2_token, _ = await create_two_users(client)
    
    # User 1 creates a todo
    await client.post(
        "/api/v1/todos",
        json={"title": "User 1's todo"},
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    
    # User 2 creates a todo
    await client.post(
        "/api/v1/todos",
        json={"title": "User 2's todo"},
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    
    # User 1 gets their todos
    response1 = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {user1_token}"},
    )
    todos1 = response1.json()["items"]
    assert len(todos1) == 1
    assert todos1[0]["title"] == "User 1's todo"
    
    # User 2 gets their todos
    response2 = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {user2_token}"},
    )
    todos2 = response2.json()["items"]
    assert len(todos2) == 1
    assert todos2[0]["title"] == "User 2's todo"


@pytest.mark.asyncio
async def test_duplicate_email_registration(client: AsyncClient):
    """Test that duplicate email registration is rejected."""
    # Register first user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@test.com", "password": "password123"},
    )
    
    # Try to register with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@test.com", "password": "different456"},
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_weak_password_rejected(client: AsyncClient):
    """Test that weak passwords are rejected."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@test.com", "password": "123"},  # Too short
    )
    assert response.status_code == 422  # Validation error
