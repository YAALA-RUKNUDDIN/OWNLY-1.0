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
email = f"smoke_{__import__('random').randint(1000,9999)}@ownlymail.com"
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

# 12. Subscription defaults to the free plan with a visible cap
s, sub = call("GET", "/subscription", token=token)
check("subscription 200", s == 200, f"got {s}")
check("default tier is free", sub.get("tier") == "free", str(sub))
check("free tier exposes product cap", sub.get("limits", {}).get("max_products") == 10, str(sub.get("limits")))
check("usage counts the created product", sub.get("usage", {}).get("products") == 1, str(sub.get("usage")))

# 13. Premium activation lifts the cap
s, sub2 = call("POST", "/subscription/activate", {"months": 12}, token)
check("activate premium 200", s == 200, f"got {s}: {sub2}")
check("tier is premium", sub2.get("tier") == "premium", str(sub2))
check("premium is unlimited", sub2.get("limits", {}).get("max_products") is None, str(sub2.get("limits")))
s, sub3 = call("POST", "/subscription/cancel", None, token)
check("cancel returns 200", s == 200, f"got {s}")
check("canceled but still entitled", sub3.get("tier") == "premium" and sub3.get("status") == "canceled", str(sub3))

# 14. `/today` alias matches the canonical dashboard path
s, today_alias = call("GET", "/today", token=token)
check("today alias 200", s == 200, f"got {s}")
check("today alias has stats", today_alias.get("stats", {}).get("total_products", 0) >= 1, str(today_alias.get("stats")))

# 15. Notification history endpoint
s, hist = call("GET", "/notifications", token=token)
check("notifications 200", s == 200, f"got {s}")
check("history has items/total/page shape",
      all(k in hist for k in ("items", "total", "page", "page_size")), str(hist))

# 17. Device token registration
smoke_fcm = f"smoke_fcm_{email[:8]}"
s, dev = call("POST", "/users/me/devices", {"fcm_token": smoke_fcm, "platform": "android"}, token)
check("register device 201", s == 201, f"got {s}: {dev}")

# 18. Test push notification dispatch with deep link routing
s, push_test = call("POST", "/notifications/test", {
    "title": "Smoke Push",
    "body": "Smoke test push verification",
    "route": f"/products/{pid}",
    "deep_link": f"ownly:///products/{pid}",
}, token)
check("test push dispatch 200", s == 200, f"got {s}: {push_test}")
check("push recipient count is 1", push_test.get("recipient_count") == 1, str(push_test))

# 19. Unregister device token
s, unreg = call("DELETE", f"/users/me/devices/{smoke_fcm}", None, token)
check("unregister device 204", s in (200, 204), f"got {s}")

# 20. Notification preferences
s, prefs = call("GET", "/users/me/prefs", token=token)
check("notification preferences 200", s == 200, f"got {s}")
check("prefs has categories", len(prefs.get("preferences", [])) >= 1, str(prefs))

print()
if failures:
    print(f"SMOKE TEST FAILED: {len(failures)} failures: {failures}")
    sys.exit(1)
print("SMOKE TEST PASSED: all checks green.")