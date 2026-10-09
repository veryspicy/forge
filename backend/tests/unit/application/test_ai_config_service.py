"""Unit tests for ai_config_service（多供应商 AI 配置服务）。

覆盖：密钥加解密与脱敏、模型清洗、payload 校验、store 规范化、
供应商 CRUD / 排序 / 启用、连通性测试、模型拉取、文本导入、LLM 端点加载。
"""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from forge.application.services import ai_config_service as svc
from forge.infrastructure.persistence.models import ORMSystemConfig
from forge.infrastructure.services.crypto_service import encrypt_str

# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class _Result:
    """仿 SQLAlchemy Result 的最小实现。"""

    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDB:
    """极简 AsyncSession 替身：按 key 返回预置行。"""

    def __init__(self, providers_row=None, legacy_row=None):
        self.providers_row = providers_row
        self.legacy_row = legacy_row
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        text = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        if "'ai.llm'" in text:
            return _Result(self.legacy_row)
        return _Result(self.providers_row)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return None


def make_row(value, secrets=None, updated_by=None, updated_at=datetime(2026, 1, 1, 0, 0, 0)):
    secret_value = svc._dump_secrets(secrets or {})
    row = ORMSystemConfig(
        key=svc.AI_PROVIDERS_KEY,
        value=value,
        secret_value=secret_value,
        is_secret=bool(secret_value),
        updated_by=updated_by,
    )
    row.updated_at = updated_at
    return row


def provider(**overrides):
    base = {
        "id": "p_1",
        "name": "NIM",
        "type": "api",
        "enabled": True,
        "protocol": "chat",
        "base_url": "https://api.example.com/v1",
        "model": "m1",
        "temperature": 0.7,
        "max_tokens": 1024,
        "models": [],
        "upstreams": [],
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
        "last_test": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# crypto helpers
# ---------------------------------------------------------------------------


class TestCryptoHelpers:
    def test_roundtrip_and_mask(self):
        token = encrypt_str("nvapi-abcdef1234567890")
        assert token and token != "nvapi-abcdef1234567890"
        assert svc.decrypt_str(token) == "nvapi-abcdef1234567890"
        assert svc.decrypt_str(None) == ""
        assert svc.decrypt_str("not-a-token") == ""
        assert svc.mask_secret("") == ""
        assert svc.mask_secret("short") == "*****"
        assert svc.mask_secret("nvapi-abcdef1234567890") == "nvapi-***7890"

    def test_secret_payload_helpers(self):
        assert svc._read_secrets(None) == {}
        row = make_row({"items": [], "active_id": None, "enabled": True})
        assert svc._read_secrets(row) == {}
        row.secret_value = encrypt_str("not-json")
        assert svc._read_secrets(row) == {}
        row.secret_value = encrypt_str(json.dumps({"p_1": "k"}))
        assert svc._read_secrets(row) == {"p_1": "k"}
        assert svc._dump_secrets({"p_1": "k"}) is not None
        assert svc._dump_secrets({}) is None


# ---------------------------------------------------------------------------
# model cleaning / payload validation
# ---------------------------------------------------------------------------


class TestCleanModels:
    def test_variants_and_dedup(self):
        models = svc._clean_models(
            [
                "a",
                {"id": "b", "context_window": "8000", "capabilities": ["chat", ""]},
                {"id": "a"},
                {"no_id": 1},
                "   ",
                42,
            ]
        )
        assert models == [
            {"id": "a", "context_window": None, "capabilities": []},
            {"id": "b", "context_window": 8000, "capabilities": ["chat"]},
        ]

    def test_limits_and_non_list(self):
        assert svc._clean_models(None) == []
        assert svc._clean_models("nope") == []
        many = [{"id": f"m{i}"} for i in range(svc.MAX_MODELS + 5)]
        assert len(svc._clean_models(many)) == svc.MAX_MODELS


class TestApplyPayload:
    def test_api_provider_normalized(self):
        secrets: dict[str, str] = {}
        result = svc._apply_payload(
            "p_1",
            {
                "name": " NIM ",
                "type": "API",
                "protocol": "CHAT",
                "base_url": "https://api.example.com/v1/",
                "model": "m1",
                "temperature": "0.3",
                "max_tokens": "2048",
                "api_key": "  key-1234567890  ",
                "models": ["m1"],
            },
            None,
            secrets,
        )
        assert result["name"] == "NIM"
        assert result["type"] == "api"
        assert result["base_url"] == "https://api.example.com/v1"
        assert result["temperature"] == 0.3
        assert result["max_tokens"] == 2048
        assert secrets == {"p_1": "key-1234567890"}
        assert result["models"] == [{"id": "m1", "context_window": None, "capabilities": []}]

    def test_blank_api_key_keeps_existing(self):
        secrets = {"p_1": "old-key"}
        result = svc._apply_payload("p_1", {"api_key": "   "}, provider(id="p_1"), secrets)
        assert secrets["p_1"] == "old-key"
        assert result["name"] == "NIM"
        assert result["base_url"] == "https://api.example.com/v1"

    def test_api_provider_drops_stale_upstream_secrets(self):
        secrets = {"p_1#u_old": "x"}
        result = svc._apply_payload("p_1", {"name": "n", "base_url": "https://x.example.com/v1"}, None, secrets)
        assert secrets == {}
        assert result["upstreams"] == []

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": "", "base_url": "https://x.example.com/v1"},
            {"name": "n", "type": "weird"},
            {"name": "n", "protocol": "grpc"},
            {"name": "n", "base_url": ""},
            {"name": "n", "base_url": "ftp://x.example.com"},
            {"name": "n"},
        ],
    )
    def test_invalid_payloads(self, payload):
        with pytest.raises(ValueError):
            svc._apply_payload("p_1", payload, None, {})

    def test_aggregate_requires_upstream(self):
        with pytest.raises(ValueError):
            svc._apply_payload("p_1", {"name": "agg", "type": "aggregate", "upstreams": []}, None, {})

    def test_aggregate_upstreams_not_list(self):
        with pytest.raises(ValueError):
            svc._apply_payload("p_1", {"name": "agg", "type": "aggregate", "upstreams": "x"}, None, {})

    def test_aggregate_too_many_upstreams(self):
        ups = [{"base_url": f"https://u{i}.example.com/v1"} for i in range(svc.MAX_UPSTREAMS + 1)]
        with pytest.raises(ValueError):
            svc._apply_payload("p_1", {"name": "agg", "type": "aggregate", "upstreams": ups}, None, {})

    def test_aggregate_upstream_bad_url(self):
        with pytest.raises(ValueError):
            svc._apply_payload(
                "p_1",
                {"name": "agg", "type": "aggregate", "upstreams": [{"base_url": "ftp://u.example.com"}]},
                None,
                {},
            )

    def test_aggregate_skips_blank_and_non_dict_upstream(self):
        result = svc._apply_payload(
            "p_1",
            {
                "name": "agg",
                "type": "aggregate",
                "upstreams": [1, {"base_url": "   "}, {"base_url": "https://u.example.com/v1", "protocol": "bogus"}],
            },
            None,
            {},
        )
        assert len(result["upstreams"]) == 1
        assert result["upstreams"][0]["protocol"] == "chat"
        assert result["upstreams"][0]["name"] == "上游 1"

    def test_aggregate_rewrites_secrets(self):
        secrets = {"p_1": "k", "p_1#u_old": "stale"}
        result = svc._apply_payload(
            "p_1",
            {
                "name": "agg",
                "type": "aggregate",
                "api_key": "new-key",
                "upstreams": [{"id": "u_new", "base_url": "https://u.example.com/v1", "api_key": "up-key"}],
            },
            None,
            secrets,
        )
        assert "p_1#u_old" not in secrets
        assert secrets["p_1#u_new"] == "up-key"
        assert result["upstreams"][0]["name"] == "上游 1"
        assert result["upstreams"][0]["protocol"] == "chat"

    def test_protocol_responses_kept(self):
        result = svc._apply_payload(
            "p_1",
            {"name": "n", "protocol": "responses", "base_url": "https://x.example.com/v1"},
            None,
            {},
        )
        assert result["type"] == "api"
        assert result["protocol"] == "responses"


# ---------------------------------------------------------------------------
# endpoint specs
# ---------------------------------------------------------------------------


class TestEndpointSpecs:
    def test_api_spec(self):
        specs = svc.provider_endpoint_specs(provider(id="p_1"), {"p_1": "k"})
        assert len(specs) == 1
        label, cfg = specs[0]
        assert label == "NIM"
        assert cfg.base_url == "https://api.example.com/v1"
        assert cfg.api_key == "k"
        assert cfg.model == "m1"

    def test_aggregate_skips_disabled_and_blank(self):
        item = provider(
            id="p_1",
            type="aggregate",
            upstreams=[
                {
                    "id": "u1",
                    "name": "A",
                    "base_url": "https://a.example.com/v1",
                    "model": "ma",
                    "enabled": True,
                    "protocol": "responses",
                },
                {"id": "u2", "name": "B", "base_url": "https://b.example.com/v1", "enabled": False},
                {"id": "u3", "name": "C", "base_url": "", "enabled": True},
            ],
        )
        specs = svc.provider_endpoint_specs(item, {"p_1#u1": "k1"})
        assert [label for label, _ in specs] == ["A"]
        assert specs[0][1].api_key == "k1"
        assert specs[0][1].protocol == "responses"
        assert len(svc.provider_endpoints(item, {})) == 1


# ---------------------------------------------------------------------------
# store normalisation & views
# ---------------------------------------------------------------------------


class TestNormalizeStore:
    def test_fixes_active_and_drops_bad_items(self):
        store = svc._normalize_store({"items": [{"id": "p1"}, "bad", {"noid": 1}], "active_id": "ghost"})
        assert store["active_id"] == "p1"
        assert len(store["items"]) == 1

    def test_empty_defaults(self):
        assert svc._normalize_store({}) == {"items": [], "active_id": None, "enabled": True}


class TestProviderCrud:
    async def test_list_providers_masks_secrets(self):
        row = make_row(
            {"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True},
            {"p_1": "secret-key-123456"},
        )
        data = await svc.list_providers(FakeDB(providers_row=row))
        assert data["active_id"] == "p_1"
        assert data["items"][0]["api_key_masked"] == "secret***3456"
        assert data["items"][0]["api_key_set"] is True
        assert data["updated_at"] == "2026-01-01T00:00:00"

    async def test_create_first_provider_becomes_active(self):
        db = FakeDB(providers_row=make_row({"items": [], "active_id": None, "enabled": True}))
        data = await svc.create_provider(
            db,
            {"name": "NIM", "base_url": "https://api.example.com/v1", "api_key": "k1234567890"},
            "admin@example.com",
        )
        assert data["items"][0]["name"] == "NIM"
        assert data["active_id"] == data["items"][0]["id"]
        assert data["updated_by"] == "admin@example.com"
        assert db.commits == 1

    async def test_create_provider_limit(self):
        items = [provider(id=f"p{i}") for i in range(svc.MAX_PROVIDERS)]
        row = make_row({"items": items, "active_id": "p0", "enabled": True})
        with pytest.raises(ValueError, match="上限"):
            await svc.create_provider(FakeDB(providers_row=row), {"name": "x", "base_url": "https://x.example.com/v1"})

    async def test_update_keeps_blank_key(self):
        row = make_row(
            {"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True},
            {"p_1": "keep-me-key-123456"},
        )
        data = await svc.update_provider(FakeDB(providers_row=row), "p_1", {"name": "Renamed", "api_key": ""})
        assert data["items"][0]["name"] == "Renamed"
        assert data["items"][0]["api_key_set"] is True

    async def test_update_unknown_provider(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True})
        with pytest.raises(ValueError, match="不存在"):
            await svc.update_provider(FakeDB(providers_row=row), "ghost", {"name": "x"})

    async def test_delete_active_switches_and_drops_secrets(self):
        row = make_row(
            {"items": [provider(id="p_1"), provider(id="p_2")], "active_id": "p_1", "enabled": True},
            {"p_1": "k1-key-123456", "p_1#u1": "x", "p_2": "k2-key-123456"},
        )
        data = await svc.delete_provider(FakeDB(providers_row=row), "p_1")
        assert [item["id"] for item in data["items"]] == ["p_2"]
        assert data["active_id"] == "p_2"
        remaining = svc._read_secrets(row)
        assert "p_1" not in remaining
        assert "p_1#u1" not in remaining

    async def test_delete_last_provider_clears_active(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True})
        data = await svc.delete_provider(FakeDB(providers_row=row), "p_1")
        assert data["items"] == []
        assert data["active_id"] is None

    async def test_delete_unknown_provider(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True})
        with pytest.raises(ValueError, match="不存在"):
            await svc.delete_provider(FakeDB(providers_row=row), "ghost")

    async def test_duplicate_copies_secrets_and_upstreams(self):
        source = provider(
            id="p_1",
            upstreams=[{"id": "u1", "name": "U", "base_url": "https://u.example.com/v1", "enabled": True}],
        )
        row = make_row(
            {"items": [source], "active_id": "p_1", "enabled": True},
            {"p_1": "prov-key-123456", "p_1#u1": "up-key-123456"},
        )
        data = await svc.duplicate_provider(FakeDB(providers_row=row), "p_1", "Copy")
        assert len(data["items"]) == 2
        clone = data["items"][1]
        assert clone["name"] == "Copy"
        assert clone["id"] != "p_1"
        assert clone["upstreams"][0]["id"] != "u1"
        secrets = svc._read_secrets(row)
        assert secrets[clone["id"]] == "prov-key-123456"
        assert secrets[f"{clone['id']}#{clone['upstreams'][0]['id']}"] == "up-key-123456"

    async def test_duplicate_default_name(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True})
        data = await svc.duplicate_provider(FakeDB(providers_row=row), "p_1", None)
        assert data["items"][1]["name"] == "NIM 副本"

    async def test_duplicate_limit(self):
        items = [provider(id=f"p{i}") for i in range(svc.MAX_PROVIDERS)]
        row = make_row({"items": items, "active_id": "p0", "enabled": True})
        with pytest.raises(ValueError, match="上限"):
            await svc.duplicate_provider(FakeDB(providers_row=row), "p0", None)

    async def test_activate_enables_target(self):
        row = make_row(
            {"items": [provider(id="p_1"), provider(id="p_2", enabled=False)], "active_id": "p_1", "enabled": True}
        )
        data = await svc.activate_provider(FakeDB(providers_row=row), "p_2")
        assert data["active_id"] == "p_2"
        assert data["items"][1]["enabled"] is True

    async def test_reorder_success(self):
        row = make_row({"items": [provider(id="p_1"), provider(id="p_2")], "active_id": "p_1", "enabled": True})
        data = await svc.reorder_providers(FakeDB(providers_row=row), ["p_2", "p_1"])
        assert [item["id"] for item in data["items"]] == ["p_2", "p_1"]

    async def test_reorder_mismatch(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True})
        with pytest.raises(ValueError, match="不一致"):
            await svc.reorder_providers(FakeDB(providers_row=row), ["p_1", "p_2"])

    async def test_set_store_enabled(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True})
        data = await svc.set_store_enabled(FakeDB(providers_row=row), False)
        assert data["enabled"] is False


# ---------------------------------------------------------------------------
# connectivity / model list
# ---------------------------------------------------------------------------


class TestConnectivity:
    async def test_test_provider_records_last_test(self, monkeypatch):
        async def fake_test_endpoints(cfgs, labels):
            return {"status": "ok", "latency_ms": 12, "detail": "fine", "endpoints": []}

        monkeypatch.setattr(svc, "test_endpoints", fake_test_endpoints)
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True}, {"p_1": "k"})
        result = await svc.test_provider(FakeDB(providers_row=row), "p_1")
        assert result["status"] == "ok"
        assert row.value["items"][0]["last_test"]["status"] == "ok"
        assert row.value["items"][0]["last_test"]["latency_ms"] == 12

    async def test_test_provider_uses_draft_overrides(self, monkeypatch):
        captured = {}

        async def fake_test_endpoints(cfgs, labels):
            captured["cfg"] = cfgs[0]
            return {"status": "ok", "latency_ms": 1, "detail": "", "endpoints": []}

        monkeypatch.setattr(svc, "test_endpoints", fake_test_endpoints)
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True})
        await svc.test_provider(
            FakeDB(providers_row=row),
            "p_1",
            {"base_url": "https://draft.example.com/v1", "api_key": "draft-key-123456"},
        )
        assert captured["cfg"].base_url == "https://draft.example.com/v1"
        assert captured["cfg"].api_key == "draft-key-123456"

    async def test_test_provider_unknown(self):
        row = make_row({"items": [], "active_id": None, "enabled": True})
        with pytest.raises(ValueError, match="不存在"):
            await svc.test_provider(FakeDB(providers_row=row), "ghost")

    async def test_test_draft(self, monkeypatch):
        async def fake_test_endpoints(cfgs, labels):
            assert labels == ["草稿供应商"]
            return {"status": "fail", "latency_ms": 0, "detail": "x", "endpoints": []}

        monkeypatch.setattr(svc, "test_endpoints", fake_test_endpoints)
        result = await svc.test_draft({"name": "", "base_url": "https://draft.example.com/v1"})
        assert result["status"] == "fail"

    async def test_test_draft_invalid(self):
        with pytest.raises(ValueError):
            await svc.test_draft({"name": "x"})


class TestFetchModels:
    async def test_fetch_with_explicit_credentials(self, monkeypatch):
        async def fake_list_models(base_url, api_key):
            assert base_url == "https://api.example.com/v1"
            assert api_key == "k"
            return ["a", "b"]

        monkeypatch.setattr("forge.infrastructure.services.llm_client.list_models", fake_list_models)
        data = await svc.fetch_models(FakeDB(), {"base_url": "https://api.example.com/v1/", "api_key": "k"})
        assert data == {"models": ["a", "b"], "count": 2}

    async def test_fetch_reuses_saved_provider(self, monkeypatch):
        seen = {}

        async def fake_list_models(base_url, api_key):
            seen["base_url"] = base_url
            seen["api_key"] = api_key
            return []

        monkeypatch.setattr("forge.infrastructure.services.llm_client.list_models", fake_list_models)
        row = make_row(
            {"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True},
            {"p_1": "saved-key-123456"},
        )
        data = await svc.fetch_models(FakeDB(providers_row=row), {"provider_id": "p_1"})
        assert data["count"] == 0
        assert seen["api_key"] == "saved-key-123456"
        assert seen["base_url"] == "https://api.example.com/v1"

    async def test_fetch_validation_errors(self):
        with pytest.raises(ValueError, match="Base URL"):
            await svc.fetch_models(FakeDB(), {})
        with pytest.raises(ValueError, match="http"):
            await svc.fetch_models(FakeDB(), {"base_url": "api.example.com", "api_key": "k"})
        with pytest.raises(ValueError, match="API Key"):
            await svc.fetch_models(FakeDB(), {"base_url": "https://api.example.com/v1"})

    async def test_fetch_unknown_provider(self):
        row = make_row({"items": [], "active_id": None, "enabled": True})
        with pytest.raises(ValueError, match="不存在"):
            await svc.fetch_models(FakeDB(providers_row=row), {"provider_id": "ghost"})


# ---------------------------------------------------------------------------
# import parsing
# ---------------------------------------------------------------------------


class TestImportParsing:
    def test_empty_raises(self):
        with pytest.raises(ValueError, match="为空"):
            svc.parse_import_text("   ")

    def test_json_single_object(self):
        drafts = svc.parse_import_text(
            json.dumps({"base_url": "https://api.example.com/v1", "api_key": "k1234567890", "model": "m1"})
        )
        assert drafts[0]["name"] == "api.example.com"
        assert drafts[0]["base_url"] == "https://api.example.com/v1"
        assert drafts[0]["protocol"] == "chat"
        assert drafts[0]["model"] == "m1"

    def test_json_list_and_nested(self):
        drafts = svc.parse_import_text(
            json.dumps(
                [{"base_url": "https://a.example.com/v1", "api_key": "k1"}, {"base_url": "https://b.example.com/v1"}]
            )
        )
        assert len(drafts) == 2
        nested = svc.parse_import_text(json.dumps({"providers": [{"base_url": "https://c.example.com/v1"}]}))
        assert nested[0]["base_url"] == "https://c.example.com/v1"
        grouped = svc.parse_import_text(
            json.dumps({"openai": {"base_url": "https://d.example.com/v1", "api_key": "k2"}})
        )
        assert grouped[0]["name"] == "openai"
        single = svc.parse_import_text(json.dumps({"provider": {"base_url": "https://e.example.com/v1"}}))
        assert single[0]["name"] == "e.example.com"

    def test_json_unparsable(self):
        with pytest.raises(ValueError, match="未能解析"):
            svc.parse_import_text(json.dumps({"note": "hello"}))

    def test_json_url_without_scheme(self):
        drafts = svc.parse_import_text(json.dumps({"base_url": "api.example.com/v1", "api_key": "k1234567890"}))
        assert drafts[0]["base_url"] == "https://api.example.com/v1"

    def test_curl_chat(self):
        text = (
            "curl https://api.example.com/v1/chat/completions "
            "-H 'Authorization: Bearer sk-abcdef123456' -d '{\"model\":\"m1\"}'"
        )
        drafts = svc.parse_import_text(text)
        assert drafts[0]["base_url"] == "https://api.example.com/v1"
        assert drafts[0]["api_key"] == "sk-abcdef123456"
        assert drafts[0]["model"] == "m1"
        assert drafts[0]["protocol"] == "chat"

    def test_curl_responses(self):
        drafts = svc.parse_import_text("curl https://api.example.com/v1/responses -H 'x-api-key: abcdef1234567890'")
        assert drafts[0]["protocol"] == "responses"
        assert drafts[0]["base_url"] == "https://api.example.com/v1"

    def test_curl_without_url(self):
        with pytest.raises(ValueError):
            svc.parse_import_text("curl -X POST")

    def test_key_value_line(self):
        drafts = svc.parse_import_text("base_url=https://api.example.com/v1 api_key=k1234567890 model=m1")
        assert drafts[0]["base_url"] == "https://api.example.com/v1"
        assert drafts[0]["api_key"] == "k1234567890"
        assert drafts[0]["model"] == "m1"

    def test_positional_line(self):
        drafts = svc.parse_import_text("我的供应商 https://api.example.com/v1 sk-abcdef1234567890 m1")
        assert drafts[0]["base_url"] == "https://api.example.com/v1"
        assert drafts[0]["api_key"] == "sk-abcdef1234567890"
        assert drafts[0]["name"] == "我的供应商"
        assert drafts[0]["model"] == "m1"

    def test_line_without_url(self):
        with pytest.raises(ValueError):
            svc.parse_import_text("name=foo api_key=k1234567890")


class TestImportProviders:
    async def test_import_creates_and_reports(self):
        row = make_row({"items": [], "active_id": None, "enabled": True})
        text = json.dumps(
            [
                {"name": "A", "base_url": "https://a.example.com/v1", "api_key": "k1"},
                {"name": "B", "base_url": "https://b.example.com/v1"},
            ]
        )
        data = await svc.import_providers(FakeDB(providers_row=row), text, "admin@example.com")
        assert data["created_count"] == 2
        assert data["created_names"] == ["A", "B"]
        assert data["active_id"] == data["items"][0]["id"]

    async def test_import_skips_invalid_entry(self):
        row = make_row({"items": [], "active_id": None, "enabled": True})
        text = json.dumps([{"api_key": "k1234567890"}, {"name": "B", "base_url": "https://b.example.com/v1"}])
        data = await svc.import_providers(FakeDB(providers_row=row), text)
        assert data["created_count"] == 1
        assert data["skipped"] and "Base URL" in data["skipped"][0]

    async def test_import_all_invalid_raises(self):
        row = make_row({"items": [], "active_id": None, "enabled": True})
        with pytest.raises(ValueError, match="Base URL"):
            await svc.import_providers(FakeDB(providers_row=row), json.dumps([{"api_key": "k1234567890"}]))

    async def test_import_limit_reached(self):
        items = [provider(id=f"p{i}") for i in range(svc.MAX_PROVIDERS)]
        row = make_row({"items": items, "active_id": "p0", "enabled": True})
        with pytest.raises(ValueError, match="上限"):
            await svc.import_providers(
                FakeDB(providers_row=row), json.dumps([{"name": "B", "base_url": "https://b/v1"}])
            )


# ---------------------------------------------------------------------------
# legacy migration / llm endpoint loading
# ---------------------------------------------------------------------------


class TestLegacyMigration:
    async def test_migrates_legacy_row(self):
        legacy = ORMSystemConfig(
            key=svc.LEGACY_AI_CONFIG_KEY,
            value={"base_url": "https://legacy.example.com/v1", "model": "lm"},
            secret_value=encrypt_str("legacy-key"),
            is_secret=True,
        )
        legacy.updated_at = datetime(2026, 1, 1)
        db = FakeDB(providers_row=None, legacy_row=legacy)
        store, row = await svc._load_store(db)
        assert store["items"][0]["name"] == "默认供应商"
        assert store["items"][0]["base_url"] == "https://legacy.example.com/v1"
        assert db.added
        assert db.commits == 1

    async def test_legacy_row_without_config_ignored(self, monkeypatch):
        monkeypatch.setattr(
            svc,
            "settings",
            SimpleNamespace(
                ai_llm_base_url="",
                ai_llm_model="",
                ai_llm_api_key="",
                openai_api_key="sk-placeholder",
                ai_llm_temperature=0.7,
                ai_llm_max_tokens=1024,
            ),
        )
        legacy = ORMSystemConfig(key=svc.LEGACY_AI_CONFIG_KEY, value={}, secret_value=None, is_secret=False)
        legacy.updated_at = datetime(2026, 1, 1)
        store, row = await svc._load_store(FakeDB(providers_row=None, legacy_row=legacy))
        assert store["items"] == []
        assert row is None

    async def test_no_rows_returns_empty(self):
        store, row = await svc._load_store(FakeDB())
        assert store["items"] == []
        assert row is None


class TestLoadLlmEndpoints:
    async def test_disabled_returns_empty(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": False})
        assert await svc.load_llm_endpoints(FakeDB(providers_row=row)) == []

    async def test_active_provider_endpoints(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True}, {"p_1": "k"})
        endpoints = await svc.load_llm_endpoints(FakeDB(providers_row=row))
        assert len(endpoints) == 1
        assert endpoints[0].api_key == "k"
        assert endpoints[0].enabled is True

    async def test_env_fallback(self, monkeypatch):
        monkeypatch.setattr(
            svc,
            "settings",
            SimpleNamespace(
                ai_llm_base_url="https://env.example.com/v1",
                ai_llm_api_key="env-key-12345",
                openai_api_key="sk-placeholder",
                ai_llm_model="em",
                ai_llm_temperature=0.5,
                ai_llm_max_tokens=64,
            ),
        )
        endpoints = await svc.load_llm_endpoints(FakeDB())
        assert endpoints[0].base_url == "https://env.example.com/v1"
        assert endpoints[0].api_key == "env-key-12345"

    async def test_env_fallback_uses_openai_key(self, monkeypatch):
        monkeypatch.setattr(
            svc,
            "settings",
            SimpleNamespace(
                ai_llm_base_url="https://env.example.com/v1",
                ai_llm_api_key="",
                openai_api_key="sk-real",
                ai_llm_model="em",
                ai_llm_temperature=0.5,
                ai_llm_max_tokens=64,
            ),
        )
        endpoints = await svc.load_llm_endpoints(FakeDB())
        assert endpoints[0].api_key == "sk-real"

    async def test_load_llm_config_disabled(self):
        row = make_row({"items": [], "active_id": None, "enabled": False})
        cfg = await svc.load_llm_config(FakeDB(providers_row=row))
        assert cfg.enabled is False

    async def test_load_llm_config_from_active_provider(self):
        row = make_row({"items": [provider(id="p_1")], "active_id": "p_1", "enabled": True}, {"p_1": "k"})
        cfg = await svc.load_llm_config(FakeDB(providers_row=row))
        assert cfg.enabled is True
        assert cfg.base_url == "https://api.example.com/v1"
        assert cfg.api_key == "k"
        assert cfg.model == "m1"
