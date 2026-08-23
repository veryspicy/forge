"""Unit tests for Admin Resources API (list / meta / check-name / check-names)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from forge.main import dependencies

ADMIN_ID = "d290f1ee-6c54-4b01-90e6-d701748f0851"


def _setup_auth(test_client):
    async def _fake_get_db():
        yield AsyncMock()

    async def _fake_admin():
        return {"id": UUID(ADMIN_ID), "role": "super_admin", "roles": ["super_admin"]}

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin


def _setup_session(test_client, execute_side_effect=None):
    session = AsyncMock()
    if execute_side_effect is not None:
        session.execute.side_effect = execute_side_effect

    async def _fake_get_db():
        yield session

    test_client.app.dependency_overrides[dependencies.get_db] = _fake_get_db
    return session


def _make_result_scalar(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _make_result_scalars(items):
    r = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = items
    r.scalars.return_value = scalars
    return r


def _make_resource(**overrides):
    res = MagicMock()
    res.id = uuid4()
    res.site_id = uuid4()
    res.bucket = "forge"
    res.object_key = "/resources/abc.png"
    res.url = "/uploads/site/abc.png"
    res.file_type = "image"
    res.mime = "image/png"
    res.file_size = 123
    res.sha256 = "x" * 64
    res.name = "pic.png"
    res.directory = "home"
    res.created_by = uuid4()
    res.created_at = None
    res.deleted_at = None
    for k, v in overrides.items():
        setattr(res, k, v)
    return res


class TestResourcesList:
    def test_list_empty(self, test_client):
        _setup_auth(test_client)
        _setup_session(
            test_client,
            [_make_result_scalar(0), _make_result_scalars([])],
        )
        try:
            resp = test_client.get("/api/admin/v1/resources")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["total"] == 0

    def test_list_with_items(self, test_client):
        _setup_auth(test_client)
        res = _make_resource()
        _setup_session(
            test_client,
            [
                _make_result_scalar(1),
                _make_result_scalars([res]),
                _make_result_scalars([]),  # ref counts
                _make_result_scalars([]),  # tags
            ],
        )
        try:
            resp = test_client.get("/api/admin/v1/resources")
        finally:
            test_client.app.dependency_overrides.clear()
        data = resp.json()
        assert resp.status_code == 200
        assert data["total"] == 1
        assert data["items"][0]["name"] == "pic.png"
        assert data["items"][0]["ref_count"] == 0
        assert data["items"][0]["tags"] == []

    def test_list_unauthorized(self, test_client):
        resp = test_client.get("/api/admin/v1/resources")
        assert resp.status_code == 401

    def test_list_forbidden(self, test_client):
        from fastapi import HTTPException

        async def _fake_admin_403():
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        test_client.app.dependency_overrides[dependencies.get_current_admin] = _fake_admin_403
        try:
            resp = test_client.get("/api/admin/v1/resources")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 403


class TestResourcesMeta:
    def test_list_directories(self, test_client):
        _setup_auth(test_client)
        row = MagicMock()
        row.__iter__ = MagicMock(return_value=iter((None, 3)))
        _setup_session(test_client, [MagicMock(all=MagicMock(return_value=[row]))])
        try:
            resp = test_client.get("/api/admin/v1/resources/meta/directories")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"] == [{"directory": "", "count": 3}]

    def test_list_tags(self, test_client):
        _setup_auth(test_client)
        row = MagicMock()
        row.__iter__ = MagicMock(return_value=iter(("sale", 2)))
        _setup_session(test_client, [MagicMock(all=MagicMock(return_value=[row]))])
        try:
            resp = test_client.get("/api/admin/v1/resources/meta/tags")
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"] == [{"name": "sale", "count": 2}]


class TestResourcesCheckName:
    def test_check_name_exists(self, test_client):
        _setup_auth(test_client)
        res = _make_resource()
        _setup_session(test_client, [_make_result_scalars([res])])
        try:
            resp = test_client.get("/api/admin/v1/resources/check-name", params={"name": "pic.png"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["exists"] is True
        assert resp.json()["data"]["active_count"] == 1
        assert resp.json()["data"]["trash_count"] == 0

    def test_check_name_trash_only(self, test_client):
        _setup_auth(test_client)
        res = _make_resource(deleted_at=MagicMock())
        _setup_session(test_client, [_make_result_scalars([res])])
        try:
            resp = test_client.get("/api/admin/v1/resources/check-name", params={"name": "old.png"})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.json()["data"]["exists"] is False
        assert resp.json()["data"]["trash_count"] == 1

    def test_check_names_empty(self, test_client):
        _setup_auth(test_client)
        _setup_session(test_client)
        try:
            resp = test_client.post("/api/admin/v1/resources/check-names", json={"names": ["", "  "]})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["existing"] == {}

    def test_check_names_with_existing(self, test_client):
        _setup_auth(test_client)
        a = _make_resource(name="a.png")
        b = _make_resource(name="b.png")
        b2 = _make_resource(name="b.png")
        _setup_session(test_client, [_make_result_scalars([a, b, b2])])
        try:
            resp = test_client.post("/api/admin/v1/resources/check-names", json={"names": ["a.png", "b.png", "c.png"]})
        finally:
            test_client.app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["data"]["existing"] == {"a.png": 1, "b.png": 2}
