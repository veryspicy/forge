"""Verify Casbin enforcer + DB integration."""
import casbin
from forge.infrastructure.casbin_enforcer import create_enforcer

e = create_enforcer()

tests = [
    ("admin@forge.com", "products", "edit"),
    ("admin@forge.com", "products", "view"),
    ("admin@forge.com", "orders", "view"),
    ("admin@forge.com", "dashboards", "view"),
    ("nonexistent@test.com", "products", "edit"),
]

print("=== Casbin Enforcer Verification ===")
for sub, obj, act in tests:
    r = e.enforce(sub, obj, act)
    status = "ALLOW" if r else "DENY"
    print(f"  {sub} {obj}:{act} -> {status}")

# Count policies
policies = e.get_policy()
print(f"\nTotal policies in DB: {len(policies)}")
