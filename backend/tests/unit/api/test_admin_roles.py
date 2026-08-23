"""Unit tests for Admin Roles API (DB-backed RBAC)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from forge.main import dependencies

ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"
PERM_ID = uuid4()
ROLE_ID = uuid4()


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID(ADMIN_ID), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


def _setup_session(test_client, side_effect=None):
    session = AsyncMock()
    if side_effect is not None:
        session.execute.side_effect = side_effect

    async def _fake_get_db():
        yield session

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    return session


def _perm(**kw):
    p = MagicMock()
    p.id = kw.get("id", PERM_ID)
    p.code = kw.get("code", "pricing:view")
    p.display_name = kw.get("display_name", "查看定价")
    p.module = kw.get("module", "pricing")
    return p


def _role(**kw):
    r = MagicMock()
    r.id = kw.get("id", ROLE_ID)
    r.name = kw.get("name", "editor")
    r.display_name = kw.get("display_name", "编辑")
    r.description = kw.get("description", "")
    r.is_system = kw.get("is_system", False)
    r.created_at = None
    r.permissions = kw.get("permissions", [])
    return r


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalar_one_result(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _scalars_result(items):
    r = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = items
    r.scalars.return_value = scalars
    return r


class TestRolesAPI:
    def test_list_permissions(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalars_result([_perm()])])
        try:
            resp = test_client.get("/api/admin/v1/roles/permissions")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["permissions"][0]["code"] == "pricing:view"

    def test_list_roles(self, test_client):
        _setup_auth(test_client)
        _setup_session(
            test_client,
            [_scalar_one_result(1), _scalars_result([_role()])],
        )
        try:
            resp = test_client.get("/api/admin/v1/roles/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "editor"

    def test_create_role_success(self, test_client):
        _setup_auth(test_client)
        role = _role()
        _setup_session(
            test_client,
            [
                _scalar_result(None),  # name exists check
                _scalars_result([_perm()]),  # load permissions
                _scalar_one_result(role),  # fresh role
            ],
        )
        try:
            resp = test_client.post(
                "/api/admin/v1/roles/",
                json={"name": "editor", "display_name": "编辑", "permission_ids": [str(PERM_ID)]},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["name"] == "editor"

    def test_create_role_name_exists(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(_role())])
        try:
            resp = test_client.post(
                "/api/admin/v1/roles/",
                json={"name": "editor", "display_name": "编辑"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400
        assert resp.json()["detail"] == "ROLE_NAME_EXISTS"

    def test_create_role_invalid_permissions(self, test_client):
        _setup_auth(test_client)
        _setup_session(
            test_client,
            [
                _scalar_result(None),
                _scalars_result([]),  # requested perm ids not found
            ],
        )
        try:
            resp = test_client.post(
                "/api/admin/v1/roles/",
                json={"name": "editor", "display_name": "编辑", "permission_ids": [str(uuid4())]},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400
        assert resp.json()["detail"] == "INVALID_PERMISSION_IDS"

    def test_update_role_success(self, test_client):
        _setup_auth(test_client)
        role = _role(display_name="旧名")
        _setup_session(
            test_client,
            [
                _scalar_result(role),  # fetch role with permissions
            ],
        )
        try:
            resp = test_client.put(
                f"/api/admin/v1/roles/{ROLE_ID}",
                json={"display_name": "新名"},
            )
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "新名"

    def test_update_role_not_found(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(None)])
        try:
            resp = test_client.put(f"/api/admin/v1/roles/{ROLE_ID}", json={"display_name": "x"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404
        assert resp.json()["detail"] == "ROLE_NOT_FOUND"

    def test_update_super_admin_fixed(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(_role(name="super_admin"))])
        try:
            resp = test_client.put(f"/api/admin/v1/roles/{ROLE_ID}", json={"display_name": "x"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400
        assert resp.json()["detail"] == "SUPER_ADMIN_ROLE_FIXED"

    def test_delete_role_success(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(_role())])
        try:
            resp = test_client.delete(f"/api/admin/v1/roles/{ROLE_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_role_not_found(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(None)])
        try:
            resp = test_client.delete(f"/api/admin/v1/roles/{ROLE_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_delete_system_role_protected(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client, [_scalar_result(_role(is_system=True))])
        try:
            resp = test_client.delete(f"/api/admin/v1/roles/{ROLE_ID}")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 400
        assert resp.json()["detail"] == "SYSTEM_ROLE_PROTECTED"

    def test_roles_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/roles/")
        assert resp.status_code == 401

    def test_roles_forbidden(self, test_client):
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            resp = test_client.get("/api/admin/v1/roles/")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 403
