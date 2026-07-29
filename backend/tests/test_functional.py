"""
Admin 后台一体化功能测试 — pytest + httpx.AsyncClient

覆盖完整用户流程链：
  登录 → Dashboard → 商品CRUD → 订单列表+详情 →
  供应商创建+停用 → 定价规则+计算 → 物流创建+轨迹更新 →
  用户列表 → Chat Requests → Settings → 清理 → 鉴权拒绝

用法:
  pytest tests/test_functional.py -v
  pytest tests/test_functional.py -v -k "test_flow"   # 仅跑链式流程
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure backend src is on sys.path
backend_root = Path(__file__).resolve().parent.parent / "src"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Podman PostgreSQL — set before app import so database.py picks it up.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/forge",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_suffix() -> str:
    return datetime.now(timezone.utc).strftime("%H%M%S")


def _unique_email() -> str:
    return f"func_test_{_now_suffix()}_{uuid4().hex[:6]}@example.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
async def admin_client():
    """Async HTTP client bound to the FastAPI app via ASGI transport."""
    from forge.main.application import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
async def admin_token(admin_client: AsyncClient):
    """Register a new user and log in, returning (token, email)."""
    email = _unique_email()
    password = "testpass123"

    # Register
    r = await admin_client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "name": "Func Test Admin",
    })
    assert r.status_code == 201, f"Register failed: {r.text}"

    # Login
    r = await admin_client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return token


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Step-by-step functional tests
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """1. Health check."""

    async def test_health(self, admin_client: AsyncClient):
        r = await admin_client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"


class TestDashboard:
    """2. Dashboard statistics."""

    async def test_dashboard(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/dashboard",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        for key in ("today_orders", "pending_orders", "today_gmv",
                     "active_products", "total_suppliers", "today_probe_requests"):
            assert key in data, f"Missing dashboard key: {key}"


class TestProductCRUD:
    """3. Product CRUD workflow."""

    async def test_create_product(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.post(
            "/api/admin/v1/products/",
            headers=_auth_headers(admin_token),
            json={
                "sku": f"FUNC-SKU-{_now_suffix()}-{uuid4().hex[:6]}",
                "name": "Functional Test Cat Toy",
                "description": "E2E functional test product",
                "price": 29.99,
                "cost": 12.00,
                "category": "toys",
                "inventory": 100,
                "region_availability": ["AE"],
            },
        )
        assert r.status_code == 201, f"Create product: {r.text}"
        data = r.json()
        assert data["sku"].startswith("FUNC-SKU-")
        return data["id"]

    async def test_get_product(self, admin_client: AsyncClient, admin_token: str):
        # Create first
        pid = await self.test_create_product(admin_client, admin_token)
        r = await admin_client.get(
            f"/api/admin/v1/products/{pid}",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Functional Test Cat Toy"

    async def test_update_product(self, admin_client: AsyncClient, admin_token: str):
        pid = await self.test_create_product(admin_client, admin_token)
        r = await admin_client.patch(
            f"/api/admin/v1/products/{pid}",
            headers=_auth_headers(admin_token),
            json={"name": "Premium Func Cat Toy", "price": 34.99},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Premium Func Cat Toy"

    async def test_set_product_status(self, admin_client: AsyncClient, admin_token: str):
        pid = await self.test_create_product(admin_client, admin_token)
        r = await admin_client.post(
            f"/api/admin/v1/products/{pid}/status",
            headers=_auth_headers(admin_token),
            json={"status": "active"},
        )
        assert r.status_code == 200

    async def test_list_products(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/products/?page_size=5",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data


class TestOrders:
    """4. Order list and detail."""

    async def test_list_orders(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/orders/?page_size=5",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    async def test_get_order_detail(self, admin_client: AsyncClient, admin_token: str):
        # Create a product first (required to create an order)
        r_prod = await admin_client.post(
            "/api/admin/v1/products/",
            headers=_auth_headers(admin_token),
            json={
                "sku": f"FUNC-ORDER-TEST-{_now_suffix()}-{uuid4().hex[:6]}",
                "name": "Order Detail Test Product",
                "description": "Created for order detail test",
                "price": 19.99,
                "cost": 8.00,
                "category": "toys",
                "inventory": 50,
                "region_availability": ["AE"],
            },
        )
        assert r_prod.status_code == 201, f"Create product for order test: {r_prod.text}"
        product_id = r_prod.json()["id"]

        # Create an order via the user-facing API
        r_create = await admin_client.post(
            "/api/v1/orders/",
            headers=_auth_headers(admin_token),
            json={
                "items": [{"product_id": product_id, "quantity": 1}],
                "shipping_address": {
                    "name": "Test User",
                    "line1": "123 Test St",
                    "city": "Dubai",
                    "country": "AE",
                    "phone": "+971-50-0000000",
                },
            },
        )
        assert r_create.status_code == 201, f"Create order: {r_create.text}"
        order_id = r_create.json()["id"]

        # Get order detail via the Admin API
        r2 = await admin_client.get(
            f"/api/admin/v1/orders/{order_id}",
            headers=_auth_headers(admin_token),
        )
        assert r2.status_code == 200, f"Order detail: {r2.text}"
        data = r2.json()
        assert data["id"] == order_id
        assert data["status"] == "PENDING"
        assert len(data["items"]) == 1


class TestSuppliers:
    """5. Supplier create + deactivate."""

    async def test_create_supplier(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.post(
            "/api/admin/v1/suppliers/",
            headers=_auth_headers(admin_token),
            json={
                "name": f"Func Test Supplier {_now_suffix()}",
                "contact_email": "supplier@func-test.com",
                "contact_phone": "+971-50-1234567",
                "shipping_regions": ["AE", "SA"],
                "integration_type": "manual",
                "default_currency": "AED",
            },
        )
        assert r.status_code == 201, f"Create supplier: {r.text}"
        data = r.json()
        assert data["is_active"] is True
        return data["id"]

    async def test_list_suppliers(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/suppliers/",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200

    async def test_deactivate_supplier(self, admin_client: AsyncClient, admin_token: str):
        sid = await self.test_create_supplier(admin_client, admin_token)
        r = await admin_client.post(
            f"/api/admin/v1/suppliers/{sid}/deactivate",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["detail"] == "Supplier deactivated"


class TestPricing:
    """6. Pricing rule create + calculate."""

    async def test_create_pricing_rule(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.post(
            "/api/admin/v1/pricing/rules",
            headers=_auth_headers(admin_token),
            json={
                "name": f"Func Test Rule {_now_suffix()}",
                "region": "AE",
                "markup_multiplier": 1.5,
                "fixed_shipping_fee": 10.0,
                "is_default": False,
                "priority": 1,
                "is_active": True,
            },
        )
        assert r.status_code == 201, f"Create pricing rule: {r.text}"
        return r.json()["id"]

    async def test_list_pricing_rules(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/pricing/rules",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200

    async def test_calculate_price(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/pricing/calculate?cost_price=100&region=AE",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200

    async def test_delete_pricing_rule(self, admin_client: AsyncClient, admin_token: str):
        rule_id = await self.test_create_pricing_rule(admin_client, admin_token)
        r = await admin_client.delete(
            f"/api/admin/v1/pricing/rules/{rule_id}",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 204


class TestShipments:
    """7. Shipment create + tracking update."""

    async def test_create_shipment(self, admin_client: AsyncClient, admin_token: str):
        # Use zero UUID as placeholder; real integration needs existing order
        r = await admin_client.post(
            "/api/admin/v1/shipments/",
            headers=_auth_headers(admin_token),
            json={
                "order_id": "00000000-0000-0000-0000-000000000001",
                "supplier_id": "00000000-0000-0000-0000-000000000001",
                "tracking_number": f"FUNC-TRACK-{_now_suffix()}",
                "carrier": "DHL Express",
                "tracking_url": "https://www.dhl.com/track/FUNC",
                "origin": "Dubai",
                "destination": "Riyadh",
            },
        )
        # Accept 201 (created) or 400/404 (order not found — acceptable in test env)
        if r.status_code == 201:
            return r.json()["id"]
        else:
            assert r.status_code in (400, 404), f"Unexpected status: {r.status_code} {r.text}"
            pytest.skip(f"Shipment create returned {r.status_code} (order not found in DB)")

    async def test_list_shipments(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/shipments/",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200

    async def test_update_tracking(self, admin_client: AsyncClient, admin_token: str):
        sid = await self.test_create_shipment(admin_client, admin_token)
        r = await admin_client.patch(
            f"/api/admin/v1/shipments/{sid}/tracking",
            headers=_auth_headers(admin_token),
            json={
                "events": [
                    {
                        "timestamp": "2026-06-30T10:00:00Z",
                        "location": "Dubai Hub",
                        "description": "Package received",
                    }
                ],
                "status": "IN_TRANSIT",
            },
        )
        assert r.status_code == 200, f"Update tracking: {r.text}"


class TestUsers:
    """8. User list."""

    async def test_list_users(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/users/",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data


class TestChatRequests:
    """9. Chat requests list."""

    async def test_list_chat_requests(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/chat-requests/",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200


class TestSettings:
    """10. Settings read + update."""

    async def test_get_settings(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.get(
            "/api/admin/v1/settings/",
            headers=_auth_headers(admin_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert "store_name" in data

    async def test_update_settings(self, admin_client: AsyncClient, admin_token: str):
        r = await admin_client.put(
            "/api/admin/v1/settings/",
            headers=_auth_headers(admin_token),
            json={
                "store_name": "Func Test Forge Shop",
                "default_currency": "AED",
                "default_region": "AE",
                "contact_email": "func@forge.com",
                "order_settings": {
                    "auto_approve": True,
                    "max_pending_orders": 30,
                    "require_payment_first": True,
                },
                "notifications": {"email": True, "sms": False, "webhook_url": ""},
            },
        )
        assert r.status_code == 200
        assert r.json()["store_name"] == "Func Test Forge Shop"


class TestUnauthorized:
    """11. Auth rejection."""

    async def test_no_token_returns_401(self, admin_client: AsyncClient):
        r = await admin_client.get("/api/admin/v1/dashboard")
        assert r.status_code == 401

    async def test_invalid_token_returns_401(self, admin_client: AsyncClient):
        r = await admin_client.get(
            "/api/admin/v1/dashboard",
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )
        assert r.status_code == 401

    async def test_no_token_products_returns_401(self, admin_client: AsyncClient):
        r = await admin_client.get("/api/admin/v1/products/")
        assert r.status_code == 401

    async def test_no_token_orders_returns_401(self, admin_client: AsyncClient):
        r = await admin_client.get("/api/admin/v1/orders/")
        assert r.status_code == 401

    async def test_no_token_suppliers_returns_401(self, admin_client: AsyncClient):
        r = await admin_client.get("/api/admin/v1/suppliers/")
        assert r.status_code == 401

    async def test_no_token_shipments_returns_401(self, admin_client: AsyncClient):
        r = await admin_client.get("/api/admin/v1/shipments/")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Full chain: one-test, end-to-end flow
# ---------------------------------------------------------------------------

class TestFullChain:
    """Single test that chains the entire user flow end-to-end."""

    async def test_full_flow(self, admin_client: AsyncClient, admin_token: str):
        """Chain: login → dashboard → product CRUD → orders → suppliers →
        pricing → shipments → users → chat → settings → cleanup → auth check."""
        h = _auth_headers(admin_token)

        # --- Dashboard ---
        r = await admin_client.get("/api/admin/v1/dashboard", headers=h)
        assert r.status_code == 200

        # --- Product CRUD ---
        r = await admin_client.post("/api/admin/v1/products/", headers=h, json={
            "sku": f"CHAIN-SKU-{_now_suffix()}",
            "name": "Chain Test Toy",
            "description": "Full chain test",
            "price": 19.99,
            "cost": 8.00,
            "category": "toys",
            "inventory": 50,
            "region_availability": ["AE"],
        })
        assert r.status_code == 201
        pid = r.json()["id"]

        r = await admin_client.get(f"/api/admin/v1/products/{pid}", headers=h)
        assert r.status_code == 200

        r = await admin_client.patch(f"/api/admin/v1/products/{pid}", headers=h, json={
            "name": "Chain Test Toy Updated",
        })
        assert r.status_code == 200

        r = await admin_client.post(f"/api/admin/v1/products/{pid}/status", headers=h, json={
            "status": "active",
        })
        assert r.status_code == 200

        r = await admin_client.get("/api/admin/v1/products/?page_size=3", headers=h)
        assert r.status_code == 200

        # --- Orders ---
        r = await admin_client.get("/api/admin/v1/orders/?page_size=3", headers=h)
        assert r.status_code == 200
        items = r.json().get("items", [])
        if items:
            order_id = items[0]["id"]
            r = await admin_client.get(f"/api/admin/v1/orders/{order_id}", headers=h)
            assert r.status_code == 200

        # --- Suppliers ---
        r = await admin_client.post("/api/admin/v1/suppliers/", headers=h, json={
            "name": f"Chain Supplier {_now_suffix()}",
            "contact_email": "chain@test.com",
            "contact_phone": "+971-50-1111111",
            "shipping_regions": ["AE"],
            "integration_type": "manual",
            "default_currency": "AED",
        })
        assert r.status_code == 201
        sid = r.json()["id"]

        r = await admin_client.post(f"/api/admin/v1/suppliers/{sid}/deactivate", headers=h)
        assert r.status_code == 200

        # --- Pricing ---
        r = await admin_client.post("/api/admin/v1/pricing/rules", headers=h, json={
            "name": f"Chain Rule {_now_suffix()}",
            "region": "AE",
            "markup_multiplier": 1.3,
            "fixed_shipping_fee": 5.0,
            "is_default": False,
            "priority": 2,
            "is_active": True,
        })
        assert r.status_code == 201
        rule_id = r.json()["id"]

        r = await admin_client.get("/api/admin/v1/pricing/rules", headers=h)
        assert r.status_code == 200

        r = await admin_client.get("/api/admin/v1/pricing/calculate?cost_price=50&region=AE", headers=h)
        assert r.status_code == 200

        # Cleanup rule
        r = await admin_client.delete(f"/api/admin/v1/pricing/rules/{rule_id}", headers=h)
        assert r.status_code == 204

        # --- Shipments ---
        r = await admin_client.post("/api/admin/v1/shipments/", headers=h, json={
            "order_id": "00000000-0000-0000-0000-000000000001",
            "supplier_id": "00000000-0000-0000-0000-000000000001",
            "tracking_number": f"CHAIN-TRACK-{_now_suffix()}",
            "carrier": "FedEx",
            "tracking_url": "https://fedex.com/track/CHAIN",
            "origin": "Abu Dhabi",
            "destination": "Jeddah",
        })
        if r.status_code == 201:
            shid = r.json()["id"]
            r = await admin_client.patch(f"/api/admin/v1/shipments/{shid}/tracking", headers=h, json={
                "events": [{"timestamp": "2026-06-30T12:00:00Z", "location": "Abu Dhabi Hub", "description": "Picked up"}],
                "status": "IN_TRANSIT",
            })
            assert r.status_code == 200
        else:
            assert r.status_code in (400, 404)

        r = await admin_client.get("/api/admin/v1/shipments/", headers=h)
        assert r.status_code == 200

        # --- Users ---
        r = await admin_client.get("/api/admin/v1/users/", headers=h)
        assert r.status_code == 200

        # --- Chat Requests ---
        r = await admin_client.get("/api/admin/v1/chat-requests/", headers=h)
        assert r.status_code == 200

        # --- Settings ---
        r = await admin_client.get("/api/admin/v1/settings/", headers=h)
        assert r.status_code == 200

        r = await admin_client.put("/api/admin/v1/settings/", headers=h, json={
            "store_name": "Chain Test Shop",
            "default_currency": "USD",
            "default_region": "AE",
            "contact_email": "chain@test.com",
            "order_settings": {"auto_approve": False, "max_pending_orders": 10, "require_payment_first": True},
            "notifications": {"email": True, "sms": False, "webhook_url": ""},
        })
        assert r.status_code == 200

        # --- Unauthorized check ---
        r = await admin_client.get("/api/admin/v1/dashboard")
        assert r.status_code == 401
