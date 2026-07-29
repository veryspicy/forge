# STAGE1-BACKEND-DONE — Account System Phase 1 Summary

## Date
2026-06-26

## Files Changed

### 1. Added: `src/forge/application/services/auth_service.py`
- **AuthService** class with:
  - `register(email, password, name)` — checks email uniqueness, hashes password with bcrypt, creates user, returns JWT
  - `login(email, password)` — looks up user, verifies password, checks is_active, returns JWT
  - `get_me(user_id)` — returns user dict via `ORMUser.to_dict()`
  - `_create_jwt(user_id)` — HS256 JWT with 7-day expiry
  - `_hash_password(password)` / `_verify_password(plain, hashed)` — passlib bcrypt
- Standalone helper: `decode_jwt_token(token)` for use outside the service

### 2. Rewritten: `src/forge/api/v1/auth.py`
- `POST /register` → AuthService.register
- `POST /login` → AuthService.login
- `GET /me` → AuthService.get_me
- Pydantic schemas: RegisterRequest, LoginRequest, TokenResponse, UserResponse

### 3. Rewritten: `src/forge/main/dependencies.py`
- `get_current_user_id` now:
  - Extracts Bearer token from `Authorization` header
  - Decodes JWT via python-jose (HS256, secret from `settings.secret_key`)
  - Validates user exists and `is_active=True` via DB query (AsyncSession injected)
  - Raises `401` for missing/invalid token, `403` for missing user or deactivated account

### 4. Already present: `src/forge/infrastructure/persistence/models.py`
- `ORMUser` table (`users`) was already defined at end of file
- Columns: id (UUID PK), email (unique, indexed), password_hash, name, role, is_active, created_at, updated_at

### 5. Verified: `src/forge/infrastructure/persistence/database.py`
- `Base` (DeclarativeBase) is imported by models.py via `.database`
- `ORMUser(Base)` is auto-discovered when `models` module is imported
- `init_db()` calls `Base.metadata.create_all()` which will include `users` table

## Dependencies
- `passlib[bcrypt]` — already installed
- `python-jose[cryptography]` — already installed

## Notes
- JWT secret is read from `Settings.secret_key` (default: `"change-me-in-production"` — override via `.env`)
- All async DB operations use `await session.execute(select(...))`
- After first run, `init_db()` will auto-create the `users` table via Alembic or `Base.metadata.create_all()`
- No frontend files were modified
