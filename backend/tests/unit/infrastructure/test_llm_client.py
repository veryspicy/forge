"""Unit tests for the OpenAI-compatible LLM client（httpx 直连实现）。"""

from __future__ import annotations

import httpx
import pytest

from forge.infrastructure.services import llm_client as lc

# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class FakeResponse:
    """仿 httpx.Response：可控状态码 / JSON / 文本。"""

    def __init__(self, status_code: int = 200, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.request = httpx.Request("GET", "https://upstream.example.com/v1/models")

    def json(self):
        if self._payload is None:
            raise ValueError("no json payload")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=self.request, response=self)


class FakeAsyncClient:
    """替身 httpx.AsyncClient：get / post 返回预置响应，或抛预置异常。"""

    def __init__(self, get_result=None, post_result=None):
        self.get_result = get_result
        self.post_result = post_result
        self.requests: list[tuple] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, headers=None):
        self.requests.append(("GET", url, headers))
        if isinstance(self.get_result, Exception):
            raise self.get_result
        return self.get_result

    async def post(self, url, headers=None, json=None):
        self.requests.append(("POST", url, headers, json))
        if isinstance(self.post_result, Exception):
            raise self.post_result
        return self.post_result


def install_client(monkeypatch, client: FakeAsyncClient) -> FakeAsyncClient:
    """把 llm_client 内部的 httpx.AsyncClient 替换为替身。"""
    monkeypatch.setattr(lc.httpx, "AsyncClient", lambda *args, **kwargs: client)
    return client


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------


def test_normalize_base_url():
    assert lc.normalize_base_url("https://x.example.com/v1/") == "https://x.example.com/v1"
    assert lc.normalize_base_url("") == ""


def test_headers_include_bearer_token():
    assert lc._headers("k")["Authorization"] == "Bearer k"


def test_llm_config_public_dict_hides_api_key():
    cfg = lc.LLMConfig(base_url="https://x.example.com/v1", api_key="secret")
    public = cfg.to_public_dict()
    assert "api_key" not in public
    assert public["base_url"] == "https://x.example.com/v1"


def test_error_detail_variants():
    nested = FakeResponse(429, payload={"error": {"message": "rate limited"}})
    assert lc._error_detail(httpx.HTTPStatusError("e", request=nested.request, response=nested)) == "rate limited"

    plain = FakeResponse(500, payload={"error": "boom"})
    assert lc._error_detail(httpx.HTTPStatusError("e", request=plain.request, response=plain)) == "boom"

    detail = FakeResponse(500, payload={"detail": "oops"})
    assert lc._error_detail(httpx.HTTPStatusError("e", request=detail.request, response=detail)) == "oops"

    raw = FakeResponse(500, payload=None, text="upstream exploded")
    assert lc._error_detail(httpx.HTTPStatusError("e", request=raw.request, response=raw)) == "upstream exploded"


def test_extract_responses_text_variants():
    assert lc._extract_responses_text(None) == ""
    assert lc._extract_responses_text({"output_text": "  x  "}) == "  x  "
    assert lc._extract_responses_text({"output": [{"content": [{"text": "y"}, {}]}, "bad"]}) == "y"
    assert lc._extract_responses_text({"output_text": "   ", "output": [{"content": [{"text": "z"}]}]}) == "z"


# ---------------------------------------------------------------------------
# low level calls
# ---------------------------------------------------------------------------


async def test_list_models_sorted_and_deduped(monkeypatch):
    payload = {"data": [{"id": "b"}, {"id": "a"}, {"id": "a"}, {"no_id": 1}, "x"]}
    client = install_client(monkeypatch, FakeAsyncClient(get_result=FakeResponse(200, payload)))
    models = await lc.list_models("https://x.example.com/v1/", "k")
    assert models == ["a", "b"]
    assert client.requests[0][1] == "https://x.example.com/v1/models"


async def test_list_models_non_list_payload(monkeypatch):
    install_client(monkeypatch, FakeAsyncClient(get_result=FakeResponse(200, {"data": "nope"})))
    assert await lc.list_models("https://x.example.com/v1", "k") == []


async def test_chat_completions_parses_reply(monkeypatch):
    payload = {"model": "m-returned", "choices": [{"message": {"content": "hello"}}], "usage": {"total_tokens": 5}}
    client = install_client(monkeypatch, FakeAsyncClient(post_result=FakeResponse(200, payload)))
    result = await lc.chat_completions(
        lc.LLMConfig(base_url="https://x.example.com/v1/", api_key="k", model="m"),
        [{"role": "user", "content": "hi"}],
    )
    assert result.content == "hello"
    assert result.model == "m-returned"
    assert result.usage == {"total_tokens": 5}
    assert client.requests[0][1] == "https://x.example.com/v1/chat/completions"


async def test_chat_completions_empty_choices(monkeypatch):
    install_client(monkeypatch, FakeAsyncClient(post_result=FakeResponse(200, {"choices": []})))
    result = await lc.chat_completions(lc.LLMConfig(base_url="https://x.example.com/v1", model="m"), [])
    assert result.content == ""
    assert result.model == "m"
    assert result.usage == {}


async def test_responses_completion_extracts_text(monkeypatch):
    payload = {"model": "m2", "output_text": "direct", "usage": {"input_tokens": 1}}
    install_client(monkeypatch, FakeAsyncClient(post_result=FakeResponse(200, payload)))
    result = await lc.responses_completion(
        lc.LLMConfig(base_url="https://x.example.com/v1", model="m", protocol=lc.PROTOCOL_RESPONSES),
        [{"role": "user", "content": "hi"}],
    )
    assert result.content == "direct"
    assert result.model == "m2"
    assert result.usage == {"input_tokens": 1}


async def test_chat_completion_dispatches_by_protocol(monkeypatch):
    payload = {"output": [{"content": [{"text": "a"}, {"text": "b"}]}]}
    install_client(monkeypatch, FakeAsyncClient(post_result=FakeResponse(200, payload)))
    result = await lc.chat_completion(
        lc.LLMConfig(base_url="https://x.example.com/v1", model="m", protocol=lc.PROTOCOL_RESPONSES),
        [],
    )
    assert result.content == "ab"
    assert result.model == "m"


# ---------------------------------------------------------------------------
# connection probing
# ---------------------------------------------------------------------------


async def test_test_connection_missing_fields():
    assert (await lc.test_connection(lc.LLMConfig()))["detail"] == "缺少 Base URL"
    assert (await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1")))["detail"] == "缺少 API Key"


async def test_test_connection_ok(monkeypatch):
    class Client(FakeAsyncClient):
        async def get(self, url, headers=None):
            return FakeResponse(200, {"data": [{"id": "m1"}, {"id": "m2"}]})

        async def post(self, url, headers=None, json=None):
            return FakeResponse(200, {"choices": [{"message": {"content": "hi there"}}]})

    install_client(monkeypatch, Client())
    result = await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1", api_key="k"))
    assert result["status"] == "ok"
    assert result["models_count"] == 2
    assert result["chat_ok"] is True
    assert result["reply"] == "hi there"
    assert "m1" in result["detail"]


async def test_test_connection_transport_error(monkeypatch):
    install_client(monkeypatch, FakeAsyncClient(get_result=httpx.ConnectError("boom")))
    result = await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1", api_key="k"))
    assert result["status"] == "fail"
    assert "无法连接上游" in result["detail"]


async def test_test_connection_http_status_error(monkeypatch):
    response = FakeResponse(401, payload={"error": {"message": "bad key"}})
    install_client(monkeypatch, FakeAsyncClient(get_result=response))
    result = await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1", api_key="k"))
    assert result["status"] == "fail"
    assert "HTTP 401" in result["detail"]
    assert "bad key" in result["detail"]


async def test_test_connection_invalid_json(monkeypatch):
    install_client(monkeypatch, FakeAsyncClient(get_result=FakeResponse(200, payload=None)))
    result = await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1", api_key="k"))
    assert "响应不是合法 JSON" in result["detail"]


async def test_test_connection_no_models(monkeypatch):
    install_client(monkeypatch, FakeAsyncClient(get_result=FakeResponse(200, {"data": []})))
    result = await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1", api_key="k"))
    assert "未返回可用模型" in result["detail"]


async def test_test_connection_chat_failure(monkeypatch):
    class Client(FakeAsyncClient):
        async def get(self, url, headers=None):
            return FakeResponse(200, {"data": [{"id": "m1"}]})

        async def post(self, url, headers=None, json=None):
            return FakeResponse(500, payload={"error": {"message": "server exploded"}})

    install_client(monkeypatch, Client())
    result = await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1", api_key="k"))
    assert result["status"] == "fail"
    assert "对话调用失败" in result["detail"]
    assert "server exploded" in result["detail"]


async def test_test_connection_chat_transport_error(monkeypatch):
    class Client(FakeAsyncClient):
        async def get(self, url, headers=None):
            return FakeResponse(200, {"data": [{"id": "m1"}]})

        async def post(self, url, headers=None, json=None):
            raise httpx.ReadTimeout("too slow")

    install_client(monkeypatch, Client())
    result = await lc.test_connection(lc.LLMConfig(base_url="https://x.example.com/v1", api_key="k"))
    assert "对话调用失败" in result["detail"]


async def test_test_endpoints_empty():
    result = await lc.test_endpoints([])
    assert result["status"] == "fail"
    assert result["endpoints"] == []


async def test_test_endpoints_skips_to_first_success(monkeypatch):
    async def fake_test_connection(cfg):
        if cfg.base_url.endswith("bad"):
            return {"status": "fail", "latency_ms": 0, "detail": "no", "models_count": 0, "chat_ok": False, "reply": ""}
        return {"status": "ok", "latency_ms": 5, "detail": "yes", "models_count": 3, "chat_ok": True, "reply": "hi"}

    monkeypatch.setattr(lc, "test_connection", fake_test_connection)
    cfgs = [lc.LLMConfig(base_url="https://bad"), lc.LLMConfig(base_url="https://good")]
    result = await lc.test_endpoints(cfgs, ["主", "备"])
    assert result["status"] == "ok"
    assert result["latency_ms"] == 5
    assert "主 失败" in result["detail"]
    assert "备 正常" in result["detail"]
    assert [item["label"] for item in result["endpoints"]] == ["主", "备"]


async def test_test_endpoints_default_labels(monkeypatch):
    async def fake_test_connection(cfg):
        return {"status": "fail", "latency_ms": 0, "detail": "no", "models_count": 0, "chat_ok": False, "reply": ""}

    monkeypatch.setattr(lc, "test_connection", fake_test_connection)
    result = await lc.test_endpoints([lc.LLMConfig(base_url="https://a"), lc.LLMConfig(base_url="https://b")])
    assert [item["label"] for item in result["endpoints"]] == ["端点 1", "端点 2"]


# ---------------------------------------------------------------------------
# failover
# ---------------------------------------------------------------------------


async def test_failover_without_endpoints():
    with pytest.raises(lc.LLMFailoverError):
        await lc.chat_completion_with_failover([], [])


async def test_failover_returns_first_success(monkeypatch):
    calls: list[str] = []

    async def fake_chat(cfg, messages, timeout=lc.CHAT_TIMEOUT):
        calls.append(cfg.base_url)
        if cfg.base_url.endswith("first"):
            raise httpx.ConnectError("down")
        return lc.LLMResult(content="ok", model=cfg.model, latency_ms=1)

    monkeypatch.setattr(lc, "chat_completion", fake_chat)
    result = await lc.chat_completion_with_failover(
        [lc.LLMConfig(base_url="https://first"), lc.LLMConfig(base_url="https://second")],
        [],
    )
    assert result.content == "ok"
    assert calls == ["https://first", "https://second"]


async def test_failover_all_failed(monkeypatch):
    async def fake_chat(cfg, messages, timeout=lc.CHAT_TIMEOUT):
        response = FakeResponse(500, payload={"error": "boom"})
        raise httpx.HTTPStatusError("e", request=response.request, response=response)

    monkeypatch.setattr(lc, "chat_completion", fake_chat)
    with pytest.raises(lc.LLMFailoverError) as excinfo:
        await lc.chat_completion_with_failover([lc.LLMConfig(base_url="https://x.example.com/v1")], [])
    assert "HTTP 500" in str(excinfo.value)
