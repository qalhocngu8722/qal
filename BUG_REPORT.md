# Bug Report & Fix Documentation

## Overview

This document details all bugs found in the Todo application codebase, along with their fixes and security implications.

---

## 🔴 CRITICAL SECURITY BUGS (Backend)

### 1. JWT Token Expiration Not Verified
**Location**: `backend/app/core/security.py:58`

**Severity**: CRITICAL

**Description**: The `verify_token()` function explicitly disabled expiration checking with `options={"verify_exp": False}`, allowing expired tokens to be accepted. This is a major security vulnerability that allows attackers to use old, potentially compromised tokens indefinitely.

**Impact**:
- Expired access tokens remain valid forever
- Users cannot effectively be logged out
- Stolen tokens can be used indefinitely
- Violates JWT security best practices

**Fix Applied**:
```python
# BEFORE (VULNERABLE):
def verify_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},  # ❌ DISABLED EXPIRATION CHECK
        )
        return payload
    except JWTError:
        return None

# AFTER (SECURE):
def verify_token(token: str, token_type: str | None = None) -> dict[str, Any] | None:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],  # ✅ EXPIRATION NOW CHECKED
        )
        
        # Verify token type if specified
        if token_type and payload.get("type") != token_type:
            return None
            
        return payload
    except JWTError:
        return None
```

**Test Coverage**: Added `test_jwt_expiration_is_verified()` in `tests/test_security.py`

---

### 2. No Token Type Verification in Authentication
**Location**: `backend/app/api/deps.py:14` and `backend/app/api/v1/auth.py:84`

**Severity**: CRITICAL

**Description**: Access tokens and refresh tokens were not differentiated. An attacker could use an access token where a refresh token is expected, or vice versa.

**Impact**:
- Token type confusion attacks
- Refresh tokens could be used for regular API access (longer lifetime)
- Access tokens could be used to generate new tokens

**Fix Applied**:
- Added `token_type` parameter to `verify_token()`
- In `get_current_user()`: verify with `token_type="access"`
- In `/refresh` endpoint: verify with `token_type="refresh"`

**Test Coverage**: Added `test_refresh_token_type_verification()` in `tests/test_security.py`

---

### 3. Refresh Token Does Not Validate User Existence
**Location**: `backend/app/api/v1/auth.py:69-90`

**Severity**: HIGH

**Description**: The refresh token endpoint didn't verify that the user still exists in the database. Deleted users could continue to refresh tokens.

**Impact**:
- Deleted user accounts can still access the system
- No way to revoke access for deleted users
- Zombie accounts remain active

**Fix Applied**:
```python
# BEFORE (VULNERABLE):
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, ...):
    payload = verify_token(request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(...)
    
    user_id = payload.get("sub")
    # ❌ NO USER VALIDATION
    access_token = create_access_token(data={"sub": user_id})
    ...

# AFTER (SECURE):
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db, ...):
    payload = verify_token(request.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(...)
    
    user_id = payload.get("sub")
    # ✅ VALIDATE USER EXISTS
    user = await get_user_by_id(db, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    ...
```

**Test Coverage**: Added `test_refresh_token_validates_user_exists()` in `tests/test_security.py`

---

### 4. No Email Unique Constraint in Database
**Location**: `backend/alembic/versions/001_initial.py`

**Severity**: CRITICAL

**Description**: The database schema didn't enforce email uniqueness at the database level, only at application level. This creates a race condition where duplicate emails can be created.

**Impact**:
- Multiple users can register with the same email
- Login becomes ambiguous
- Data integrity violations
- Race condition vulnerabilities

**Fix Applied**:
```python
# Added to migration:
sa.UniqueConstraint("email", name="uq_users_email"),
op.create_index("ix_users_email", "users", ["email"])
```

**Test Coverage**: Added `test_duplicate_email_registration()` in `tests/test_security.py`

---

### 5. Missing Data Isolation - Cross-User Access
**Location**: `backend/app/api/v1/todos.py` (all CRUD endpoints)

**Severity**: CRITICAL

**Description**: Todo GET, UPDATE, and DELETE endpoints didn't verify that the current user owns the todo. User A could access, modify, or delete User B's todos.

**Impact**:
- Complete data breach - users can read all todos
- Users can modify others' data
- Users can delete others' data
- Violates data isolation principle

**Fix Applied**:
```python
# Example for GET endpoint:
@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: uuid.UUID, current_user: User, ...):
    todo = await get_todo_by_id(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    # ✅ VERIFY OWNERSHIP
    if todo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this todo")
    
    return todo
```

Applied similar checks to:
- `PUT /todos/{todo_id}` - update endpoint
- `DELETE /todos/{todo_id}` - delete endpoint

**Test Coverage**: Added comprehensive cross-user access tests:
- `test_user_cannot_access_other_user_todo()`
- `test_user_cannot_update_other_user_todo()`
- `test_user_cannot_delete_other_user_todo()`
- `test_user_only_sees_own_todos_in_list()`

---

### 6. Cache Key Not User-Scoped
**Location**: `backend/app/api/v1/todos.py:30`

**Severity**: CRITICAL

**Description**: The Redis cache key was `"todos:list"` for ALL users. This meant User A could see User B's cached todos.

**Impact**:
- Massive data leak - users see each other's todos
- Cache poisoning attacks
- Complete violation of data isolation
- Privacy breach

**Fix Applied**:
```python
# BEFORE (VULNERABLE):
cache_key = "todos:list"  # ❌ SHARED ACROSS ALL USERS

# AFTER (SECURE):
cache_key = f"todos:user:{current_user.id}:page:{page}:size:{size}"  # ✅ USER-SCOPED
```

Also added cache invalidation function:
```python
async def invalidate_user_cache(redis: RedisClient, user_id: uuid.UUID):
    """Invalidate all cached todo lists for a specific user."""
    pattern = f"todos:user:{user_id}:*"
    cursor = 0
    keys_to_delete = []
    
    while True:
        cursor, keys = await redis.client.scan(cursor, match=pattern, count=100)
        keys_to_delete.extend(keys)
        if cursor == 0:
            break
    
    if keys_to_delete:
        await redis.client.delete(*keys_to_delete)
```

**Test Coverage**: Existing tests now verify proper cache scoping

---

### 7. Weak Password Policy
**Location**: `backend/app/schemas/user.py`

**Severity**: MEDIUM-HIGH

**Description**: No minimum password length requirement, allowing weak passwords like "123".

**Impact**:
- Brute force attacks easier
- Dictionary attacks effective
- Poor security posture

**Fix Applied**:
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)  # ✅ MINIMUM 8 CHARS
```

**Test Coverage**: Added `test_weak_password_rejected()` in `tests/test_security.py`

---

## 🟠 HIGH PRIORITY BUGS (Backend)

### 8. Cache Not Invalidated After Mutations
**Location**: `backend/app/api/v1/todos.py`

**Severity**: HIGH

**Description**: CREATE, UPDATE, DELETE operations didn't invalidate the cache, causing stale data to be served.

**Impact**:
- Users see outdated todo lists
- Changes not reflected immediately
- Confusing UX
- Data consistency issues

**Fix Applied**: Added `await invalidate_user_cache(redis, current_user.id)` to:
- `POST /todos` - create endpoint
- `PUT /todos/{todo_id}` - update endpoint
- `DELETE /todos/{todo_id}` - delete endpoint

---

### 9. Update Todo Logic Broken
**Location**: `backend/app/api/v1/todos.py:108`

**Severity**: HIGH

**Description**: The update logic had multiple issues:
1. Used `todo_data.model_dump()` but then didn't use the dict properly
2. Manually set `completed` before building update dict
3. Called `update_todo(db, todo, {})` with empty dict!

**Impact**:
- Updates don't work correctly
- Partial updates fail
- Completed status may not update

**Fix Applied**:
```python
# BEFORE (BROKEN):
update_data = todo_data.model_dump()

if todo_data.completed:
    todo.completed = todo_data.completed

if update_data.get("title") is not None:
    todo.title = update_data["title"]
if "description" in update_data:
    todo.description = update_data["description"]

updated_todo = await update_todo(db, todo, {})  # ❌ EMPTY DICT!

# AFTER (FIXED):
update_data = {}
if todo_data.title is not None:
    update_data["title"] = todo_data.title
if todo_data.description is not None:
    update_data["description"] = todo_data.description
if todo_data.completed is not None:
    update_data["completed"] = todo_data.completed

updated_todo = await update_todo(db, todo, update_data)  # ✅ CORRECT
```

---

### 10. Missing Database Indexes
**Location**: `backend/alembic/versions/001_initial.py`

**Severity**: MEDIUM-HIGH

**Description**: No indexes on frequently queried columns, leading to slow queries as data grows.

**Impact**:
- Poor performance with many users/todos
- Slow user lookups by email
- Slow todo queries by user_id
- Not scalable

**Fix Applied**:
```python
# Added indexes:
op.create_index("ix_users_email", "users", ["email"])
op.create_index("ix_todos_user_id", "todos", ["user_id"])
op.create_index("ix_todos_user_id_completed", "todos", ["user_id", "completed"])
```

---

### 11. Missing CASCADE DELETE
**Location**: `backend/alembic/versions/001_initial.py`

**Severity**: MEDIUM

**Description**: Foreign key didn't have `ON DELETE CASCADE`, causing orphaned todos when users are deleted.

**Impact**:
- Database integrity issues
- Cannot delete users who have todos
- Orphaned records accumulate

**Fix Applied**:
```python
sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
```

---

## 🟡 MEDIUM PRIORITY BUGS (Frontend)

### 12. React Query Key Missing Pagination Parameters
**Location**: `frontend/src/features/todos/api/todos.ts:42`

**Severity**: MEDIUM

**Description**: Query key was `["todos"]` regardless of page/size, causing wrong data to be cached and served.

**Impact**:
- Pagination doesn't work correctly
- Changing page shows cached data from different page
- Cache invalidation affects wrong pages

**Fix Applied**:
```typescript
// BEFORE:
queryKey: ["todos"],

// AFTER:
queryKey: ["todos", page, size],
```

---

### 13. TodoList Using Array Index as Key
**Location**: `frontend/src/features/todos/components/TodoList.tsx:38`

**Severity**: MEDIUM

**Description**: React list used `index` as key instead of `todo.id`, causing rendering bugs when todos change order.

**Impact**:
- React reconciliation issues
- Wrong todos get updated in UI
- Checkboxes toggle wrong items
- Poor performance

**Fix Applied**:
```tsx
// BEFORE:
{todos.map((todo, index) => (
  <TodoItem key={index} ... />
))}

// AFTER:
{todos.map((todo) => (
  <TodoItem key={todo.id} ... />
))}
```

---

### 14. Logout Doesn't Clear Query Cache
**Location**: `frontend/src/features/auth/api/auth.ts`

**Severity**: MEDIUM

**Description**: Logout removed tokens but didn't clear React Query cache, potentially exposing previous user's data.

**Impact**:
- Previous user's data visible briefly after login as different user
- Memory leak
- Privacy concern

**Fix Applied**:
```typescript
onSuccess: () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  queryClient.clear();  // ✅ CLEAR ALL CACHED DATA
},
```

---

### 15. Optimistic Update Rollback Not Working
**Location**: `frontend/src/features/todos/api/todos.ts:73`

**Severity**: MEDIUM

**Description**: The `onError` callback didn't receive the context, so optimistic updates couldn't be rolled back on error.

**Impact**:
- Failed updates still show as successful in UI
- Confusing UX
- Data inconsistency

**Fix Applied**:
```typescript
onError: (_error, _variables, context) => {
  // Rollback on error
  if (context?.previousTodos) {
    queryClient.setQueryData(["todos"], context.previousTodos);
  }
  toast.error("Failed to update todo");
},
```

---

## 🔵 LOW PRIORITY ISSUES (Infrastructure)

### 16. Docker Port Mapping Mismatch
**Location**: `docker-compose.yml`

**Severity**: LOW

**Description**: Postgres mapped to host port 5433 instead of 5432, inconsistent with `.env.example`.

**Impact**:
- Confusing for developers
- Local setup doesn't match Docker setup
- Connection errors

**Fix Applied**:
```yaml
# BEFORE:
ports:
  - "5433:5432"

# AFTER:
ports:
  - "5432:5432"
```

---

## Summary Statistics

- **Total Bugs Found**: 16
- **Critical Security Bugs**: 7
- **High Priority Bugs**: 4
- **Medium Priority Bugs**: 4
- **Low Priority Issues**: 1

### Bugs Fixed
- **Backend**: 11 bugs
- **Frontend**: 4 bugs
- **Infrastructure**: 1 bug

### Test Coverage Added
- Created `tests/test_security.py` with 10 comprehensive security tests
- All tests verify critical security fixes
- Tests include:
  - JWT expiration validation
  - Token type verification
  - User existence validation
  - Cross-user access prevention (4 tests)
  - Duplicate email prevention
  - Weak password rejection

---

## Verification Instructions

### Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

Expected: All tests pass, including new security tests.

### Manual Security Testing

1. **Test JWT Expiration**:
   - Register and get token
   - Wait for token to expire (30 minutes)
   - Try to access `/api/v1/auth/me`
   - Expected: 401 Unauthorized

2. **Test Cross-User Access**:
   - Register as user1, create todo1
   - Register as user2
   - Try to GET user1's todo1 using user2's token
   - Expected: 403 Forbidden

3. **Test Cache Isolation**:
   - Login as user1, create todos
   - Login as user2 (different browser/incognito)
   - Check todo list
   - Expected: Empty list, not user1's todos

---

## AI Assistance Disclosure

This code review and bug fix was performed with assistance from Claude AI (Anthropic). The AI was used for:
- Systematic code analysis across backend and frontend
- Identifying security vulnerabilities
- Implementing fixes following security best practices
- Writing comprehensive test cases
- Generating this documentation

All code changes were reviewed and validated to ensure correctness and security.

---

## Recommendations for Future Improvements

### Security Enhancements
1. **Add Rate Limiting**: Prevent brute force attacks on login/register
2. **Add CSRF Protection**: For additional security in browser contexts
3. **Add Token Blacklist**: For immediate token revocation (use Redis)
4. **Add Audit Logging**: Log all authentication and data access events
5. **Add Account Lockout**: After N failed login attempts

### Performance Improvements
1. **Add Pagination Cursor**: More efficient than offset-based pagination
2. **Add Database Connection Pooling**: Already configured but monitor
3. **Add Redis Cluster**: For high availability caching
4. **Add Database Read Replicas**: For scaling read operations

### Code Quality
1. **Add API Documentation**: Use FastAPI's built-in OpenAPI docs
2. **Add Input Sanitization**: Prevent XSS in text fields
3. **Add Request/Response Logging**: For debugging and monitoring
4. **Add Health Check Endpoints**: For monitoring and load balancers
5. **Add Metrics Collection**: Using Prometheus or similar

---

*Generated: June 5, 2026*
*Author: Senior Software Engineer Review*
