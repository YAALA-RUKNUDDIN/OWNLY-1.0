"""Live smoke test against a running OWNLY API (run: python smoke_test.py [base_url])."""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"


def call(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


failures = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name} {detail if not condition else ''}")
    if not condition:
        failures.append(name)


# 1. Register
email = f"smoke_{__import__('random').randint(1000,9999)}@ownly.local"
s, r = call("POST", "/auth/register", {"name": "Smoke User", "email": email, "password": "smokepassword1"})
check("register returns 201", s == 201, f"got {s}: {r}")
token = r.get("tokens", {}).get("access_token", "")

# 2. Wrong password rejected
s, r = call("POST", "/auth/login", {"email": email, "password": "wrong"})
check("wrong password rejected 401", s == 401, f"got {s}")

# 3. Login
s, r = call("POST", "/auth/login", {"email": email, "password": "smokepassword1"})
check("login returns 200", s == 200, f"got {s}")
token = r.get("tokens", {}).get("access_token", token)

# 4. Create product
s, p = call("POST", "/products", {
    "name": "Smoke Laptop", "brand": "TestBrand", "category": "laptops",
    "purchase_date": "2026-09-01T10:00:00", "purchase_price": 999.0,
    "return_days": 30,
}, token)
check("create product 201", s == 201, f"got {s}: {r if s != 201 else ''}")
pid = p.get("id", "")
check("return window tracked", p.get("return_window", {}).get("tracked") is True)

# 5. Add warranty
s, w = call("POST", f"/products/{pid}/warranty", {
    "warranty_type": "manufacturer", "start_date": "2026-09-01T00:00:00", "duration_months": 12,
}, token)
check("create warranty 201", s == 201, f"got {s}: {r if s != 201 else ''}")
check("warranty ends 2027-09-01", w.get("end_date", "").startswith("2027-09-01"), w.get("end_date", ""))
check("warranty active", w.get("status") == "active", w.get("status"))

# 6. Timeline has events
s, t = call("GET", f"/products/{pid}/timeline", token=token)
types = [e["event_type"] for e in t.get("events", [])]
check("timeline has product_added + warranty_started",
      "product_added" in types and "warranty_started" in types, str(types))

# 7. Dashboard
s, d = call("GET", "/dashboard/today", token=token)
check("dashboard 200", s == 200)
check("dashboard counts product", d.get("stats", {}).get("total_products", 0) >= 1, str(d.get("stats")))

# 8. Create reminder
s, rem = call("POST", "/reminders", {
    "title": "Smoke reminder", "scheduled_date": "2026-10-01", "product_id": pid,
}, token)
check("create reminder 201", s == 201, f"got {s}")

# 9. Export
s, ex = call("GET", "/users/me/export", token=token)
check("export 200 with 1 product", s == 200 and len(ex.get("products", [])) >= 1, f"got {s}")

# 10. Refresh rotation
s2, rr = call("POST", "/auth/refresh", body=None)  # placeholder, need refresh token
# Re-login to get a fresh refresh token
s, r2 = call("POST", "/auth/login", {"email": email, "password": "smokepassword1"})
refresh = r2.get("tokens", {}).get("refresh_token", "")
s, rr = call("POST", "/auth/refresh", {"refresh_token": refresh})
check("refresh rotation 200", s == 200, f"got {s}")
s, rr2 = call("POST", "/auth/refresh", {"refresh_token": refresh})
check("refresh reuse rejected 401", s == 401, f"got {s}")

# 11. Unauthenticated access denied
s, _ = call("GET", "/products")
check("unauthenticated 401", s == 401, f"got {s}")

print()
if failures:
    print(f"SMOKE TEST FAILED: {len(failures)} failures: {failures}")
    sys.exit(1)
print("SMOKE TEST PASSED: all checks green.")