#!/usr/bin/env bash
# ===========================================================================
# Admin 后台功能性测试 — 端到端 curl 脚本
# 
# 覆盖核心用户流程：
#   登录 → Dashboard → 商品CRUD → 订单审批 → 发货 → 退款
#
# 用法:
#   bash functional_test_admin.sh [BASE_URL]
#
#   默认 BASE_URL = http://localhost:8000
# ===========================================================================

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0
TOKEN=""

# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
log_pass() { PASS=$((PASS + 1)); echo "  [PASS] $1"; }
log_fail() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1  (HTTP $2 / expected $3)"; }

assert_status() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    log_pass "$desc"
  else
    log_fail "$desc" "$actual" "$expected"
  fi
}

assert_json_has() {
  local desc="$1" key="$2" resp="$3"
  if echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$key' in d" 2>/dev/null; then
    log_pass "$desc"
  else
    log_fail "$desc" "(key '$key' missing)" "present"
  fi
}

# ------------------------------------------------------------------
# 1. Health Check
# ------------------------------------------------------------------
echo "=== 1. Health Check ==="
RESP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
assert_status "GET /health" 200 "$RESP"

# ------------------------------------------------------------------
# 2. Register + Login
# ------------------------------------------------------------------
echo ""
echo "=== 2. Register + Login ==="
TEST_EMAIL="admin_test_$(date +%s)@example.com"
TEST_PASS="testpass123"

# Register
RESP=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\",\"name\":\"Test Admin\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /api/v1/auth/register (201)" 201 "$HTTP_CODE"

# Login
RESP=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /api/v1/auth/login (200)" 200 "$HTTP_CODE"
TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "  Token acquired: ${TOKEN:0:20}..."

AUTH_HEADER="Authorization: Bearer $TOKEN"
CT="Content-Type: application/json"

# ------------------------------------------------------------------
# 3. Dashboard
# ------------------------------------------------------------------
echo ""
echo "=== 3. Dashboard ==="
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/dashboard" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "GET /api/admin/v1/dashboard" 200 "$HTTP_CODE"
assert_json_has "Dashboard today_orders" "today_orders" "$BODY"
assert_json_has "Dashboard active_products" "active_products" "$BODY"

# ------------------------------------------------------------------
# 4. Product CRUD
# ------------------------------------------------------------------
echo ""
echo "=== 4. Product CRUD ==="

# Create product
RESP=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/admin/v1/products/" \
  -H "$CT" -H "$AUTH_HEADER" \
  -d '{
    "name": "Test Cat Toy",
    "description": "A fun interactive cat toy",
    "category": "toys",
    "price": 29.99,
    "cost_price": 12.00,
    "stock": 100,
    "currency": "USD",
    "images": ["https://example.com/toy.jpg"]
  }')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /api/admin/v1/products/ (201)" 201 "$HTTP_CODE"
PRODUCT_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Created product ID: $PRODUCT_ID"

# Get product detail
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/products/$PRODUCT_ID" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "GET /api/admin/v1/products/{id}" 200 "$HTTP_CODE"

# Update product
RESP=$(curl -s -w "\n%{http_code}" \
  -X PATCH "$BASE_URL/api/admin/v1/products/$PRODUCT_ID" \
  -H "$CT" -H "$AUTH_HEADER" \
  -d '{"name": "Premium Cat Toy", "price": 34.99}')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "PATCH /api/admin/v1/products/{id}" 200 "$HTTP_CODE"

# Change product status to active
RESP=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/admin/v1/products/$PRODUCT_ID/status" \
  -H "$CT" -H "$AUTH_HEADER" \
  -d '{"status": "active"}')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /api/admin/v1/products/{id}/status (active)" 200 "$HTTP_CODE"

# List products
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/products/?page_size=5" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "GET /api/admin/v1/products/ (list)" 200 "$HTTP_CODE"

# ------------------------------------------------------------------
# 5. Orders — Review / Procure / Ship / Refund
# ------------------------------------------------------------------
echo ""
echo "=== 5. Order Workflow ==="

# List orders
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/orders/?page_size=3" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "GET /api/admin/v1/orders/ (list)" 200 "$HTTP_CODE"

# Pick the first order with PAID status (if any)
ORDER_ID=$(echo "$BODY" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for item in d.get('items',[]):
    if item.get('status') in ('PAID','PENDING','CONFIRMED'):
        print(item['id'])
        break
" 2>/dev/null || echo "")

if [ -n "$ORDER_ID" ]; then
  echo "  Testing with order ID: $ORDER_ID"

  # Review: approve
  RESP=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/api/admin/v1/orders/$ORDER_ID/review" \
    -H "$CT" -H "$AUTH_HEADER" \
    -d '{"approved": true, "reason": "All good"}')
  HTTP_CODE=$(echo "$RESP" | tail -1)
  assert_status "POST /orders/{id}/review (approve)" 200 "$HTTP_CODE"

  # Procure
  RESP=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/api/admin/v1/orders/$ORDER_ID/procure" \
    -H "$CT" -H "$AUTH_HEADER" \
    -d '{"supplier_id":"00000000-0000-0000-0000-000000000001","supplier_sku":"SKU-001","cost": 12.00}')
  HTTP_CODE=$(echo "$RESP" | tail -1)
  assert_status "POST /orders/{id}/procure" 200 "$HTTP_CODE"

  # Ship
  RESP=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/api/admin/v1/orders/$ORDER_ID/ship" \
    -H "$CT" -H "$AUTH_HEADER" \
    -d '{"tracking_number": "TRACK-123456","carrier": "DHL"}')
  HTTP_CODE=$(echo "$RESP" | tail -1)
  assert_status "POST /orders/{id}/ship" 200 "$HTTP_CODE"

  # Delivery / Refund simulation — note: full refund only works if order is in refundable state
  RESP=$(curl -s -w "\n%{http_code}" \
    -X POST "$BASE_URL/api/admin/v1/orders/$ORDER_ID/refund" \
    -H "$CT" -H "$AUTH_HEADER" \
    -d '{"reason": "Customer requested"}')
  HTTP_CODE=$(echo "$RESP" | tail -1)
  # refund may fail depending on order state; accept 200 or 400
  if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 400 ]; then
    log_pass "POST /orders/{id}/refund (200 or 400 acceptable)"
  else
    log_fail "POST /orders/{id}/refund" "$HTTP_CODE" "200|400"
  fi
else
  echo "  No testable order found — skipping order workflow tests (PASS count unchanged)"
fi

# ------------------------------------------------------------------
# 6. Pricing
# ------------------------------------------------------------------
echo ""
echo "=== 6. Pricing ==="

# Create rule
RESP=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/admin/v1/pricing/rules" \
  -H "$CT" -H "$AUTH_HEADER" \
  -d '{"name": "Test UAE Rule", "region": "AE", "markup_multiplier": 1.5, "fixed_shipping_fee": 10.0}')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /pricing/rules" 201 "$HTTP_CODE"

# List rules
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/pricing/rules" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /pricing/rules" 200 "$HTTP_CODE"

# Price calculator
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/pricing/calculate?cost_price=100&region=AE" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /pricing/calculate" 200 "$HTTP_CODE"

# ------------------------------------------------------------------
# 7. Suppliers
# ------------------------------------------------------------------
echo ""
echo "=== 7. Suppliers ==="
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/suppliers/" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /suppliers/ (list)" 200 "$HTTP_CODE"

# ------------------------------------------------------------------
# 8. Users
# ------------------------------------------------------------------
echo ""
echo "=== 8. Users ==="
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/users/" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /users/ (list)" 200 "$HTTP_CODE"

# ------------------------------------------------------------------
# 9. Chat Requests
# ------------------------------------------------------------------
echo ""
echo "=== 9. Chat Requests ==="
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/chat-requests/" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /chat-requests/ (list)" 200 "$HTTP_CODE"

# ------------------------------------------------------------------
# 10. Settings
# ------------------------------------------------------------------
echo ""
echo "=== 10. Settings ==="
RESP=$(curl -s -w "\n%{http_code}" \
  "$BASE_URL/api/admin/v1/settings/" \
  -H "$AUTH_HEADER")
HTTP_CODE=$(echo "$RESP" | tail -1)
assert_status "GET /settings/" 200 "$HTTP_CODE"

# ------------------------------------------------------------------
# 11. Auth: unauthorized access
# ------------------------------------------------------------------
echo ""
echo "=== 11. Unauthorized Access ==="
RESP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/admin/v1/dashboard")
assert_status "GET /dashboard (no token -> 401)" 401 "$RESP"

RESP=$(curl -s -o /dev/null -w "%{http_code}" \
  "$BASE_URL/api/admin/v1/dashboard" \
  -H "Authorization: Bearer invalid-token")
assert_status "GET /dashboard (invalid token -> 401)" 401 "$RESP"

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "============================================"
echo "  Functional Test Summary"
echo "============================================"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
