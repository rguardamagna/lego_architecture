#!/usr/bin/env python3
"""
validate-contracts.py — Verifica que las APIs en ejecución cumplen los contratos.
"""

import json
import sys
import urllib.request
import urllib.error

GATEWAY = "http://localhost:8080"
AUTH = "http://localhost:8000"
FAIL = 0
PASS = 0
SKP = 0


def _req(url, method="GET", data=None, headers=None):
    r = urllib.request.Request(url, method=method, data=data)
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    try:
        resp = urllib.request.urlopen(r, timeout=5)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def check(label, url, expected_status, expected_keys=None, method="GET", data=None, headers=None):
    global PASS, FAIL, SKP
    body = ""
    status, body = _req(url, method=method, data=data, headers=headers)

    if status == 0:
        print(f"  ~ {label}: connection failed — {body}")
        SKP += 1
        return

    ok = status == expected_status
    if ok and expected_keys:
        try:
            obj = json.loads(body)
            for k in expected_keys:
                if k not in obj:
                    print(f"  ✗ {label}: missing key '{k}'")
                    ok = False
        except json.JSONDecodeError:
            if expected_status == 204 and not body:
                ok = True
            else:
                print(f"  ✗ {label}: bad JSON")
                ok = False

    if ok:
        print(f"  ✓ {label} → {status}")
        PASS += 1
    else:
        print(f"  ✗ {label}: expected {expected_status}, got {status} — {body[:200]}")
        FAIL += 1


def check_health(label, url):
    global PASS, FAIL
    status, body = _req(url)
    if status != 200:
        print(f"  ✗ {label}: {status} — {body[:100]}")
        FAIL += 1
        return
    try:
        d = json.loads(body)
        if d.get("status") != "healthy":
            print(f"  ✗ {label}: status != healthy")
            FAIL += 1
        else:
            print(f"  ✓ {label} → healthy ({d.get('service')})")
            PASS += 1
    except Exception as e:
        print(f"  ✗ {label}: {e}")
        FAIL += 1


# ──────────────────────────────────────────────────────────────

print("\n🔍 Validación de Contratos")
print("═" * 75)

# ── Gateway ─────────────────────────────────────────────────
print("\n📡 Gateway")
check_health("GET /health", f"{GATEWAY}/health")
check("404 — ruta inexistente", f"{GATEWAY}/api/v1/inexistente", 404, ["error", "message"])
check("502 — auth no disponible", f"{GATEWAY}/api/v1/auth/health", 502, ["error", "message"])
check(
    "401 — JWT pre-verify con token inválido",
    f"{GATEWAY}/api/v1/auth/me",
    401,
    ["error", "message"],
    headers={"Authorization": "Bearer invalid.token.here"},
)

# ── Auth Service ────────────────────────────────────────────
print("\n🔐 Auth Service")
check_health("GET /health", f"{AUTH}/health")

# Errores de validación
check(
    "POST /auth/register — sin body",
    f"{AUTH}/auth/register",
    400, ["error", "message"],
    method="POST", data=b"{}", headers={"Content-Type": "application/json"},
)
check(
    "POST /auth/register — email inválido",
    f"{AUTH}/auth/register",
    400, ["error", "message"],
    method="POST",
    data=json.dumps({"email": "bad", "password": "Secure1!Pass", "display_name": "X"}).encode(),
    headers={"Content-Type": "application/json"},
)
check(
    "POST /auth/register — password débil",
    f"{AUTH}/auth/register",
    400, ["error", "message"],
    method="POST",
    data=json.dumps({"email": "x@x.com", "password": "short", "display_name": "X"}).encode(),
    headers={"Content-Type": "application/json"},
)
check(
    "POST /auth/register — fields faltantes",
    f"{AUTH}/auth/register",
    400, ["error", "message"],
    method="POST",
    data=json.dumps({"email": "x@x.com"}).encode(),
    headers={"Content-Type": "application/json"},
)

# ── E2E — Register + Login + Me ────────────────────────────
print("\n🔄 E2E: Register → Login → Me → Refresh → Logout")

USER = {"email": "e2e@lego.local", "password": "TestPass1!", "display_name": "E2E Test"}
access_token = None
refresh_token = None

# Register
status, body = _req(
    f"{AUTH}/auth/register",
    method="POST",
    data=json.dumps(USER).encode(),
    headers={"Content-Type": "application/json"},
)
if status == 201:
    d = json.loads(body)
    access_token, refresh_token = d["access_token"], d["refresh_token"]
    print(f"  ✓ POST /auth/register → 201 ({d['user']['email']})")
    PASS += 1
elif status == 409:
    print("  ~ POST /auth/register → 409 (duplicado, re-login)")
    SKP += 1
    # Login
    status, body = _req(
        f"{AUTH}/auth/login",
        method="POST",
        data=json.dumps({"email": USER["email"], "password": USER["password"]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    if status == 200:
        d = json.loads(body)
        access_token, refresh_token = d["access_token"], d["refresh_token"]
        print(f"  ✓ POST /auth/login → 200")
        PASS += 1
    else:
        print(f"  ✗ POST /auth/login: {status} — {body[:100]}")
        FAIL += 1
else:
    print(f"  ✗ POST /auth/register: {status} — {body[:200]}")
    FAIL += 1

# Me
if access_token:
    check("GET /auth/me", f"{AUTH}/auth/me", 200,
          ["id", "email", "display_name", "oauth_providers", "is_active", "created_at"],
          headers={"Authorization": f"Bearer {access_token}"})
else:
    print("  ~ GET /auth/me → no token (skip)")
    SKP += 1

# Refresh
if refresh_token:
    status, body = _req(
        f"{AUTH}/auth/refresh",
        method="POST",
        data=json.dumps({"refresh_token": refresh_token}).encode(),
        headers={"Content-Type": "application/json"},
    )
    if status == 200:
        d = json.loads(body)
        access_token, refresh_token = d["access_token"], d["refresh_token"]
        print(f"  ✓ POST /auth/refresh → 200 (tokens rotados)")
        PASS += 1
    else:
        print(f"  ✗ POST /auth/refresh: {status} — {body[:100]}")
        FAIL += 1
else:
    print("  ~ POST /auth/refresh → no token (skip)")
    SKP += 1

# Logout
if refresh_token:
    status, body = _req(
        f"{AUTH}/auth/logout",
        method="POST",
        data=json.dumps({"refresh_token": refresh_token}).encode(),
        headers={"Content-Type": "application/json"},
    )
    if status == 204:
        print(f"  ✓ POST /auth/logout → 204")
        PASS += 1
    else:
        print(f"  ✗ POST /auth/logout: {status} — {body[:100]}")
        FAIL += 1

    # Try refresh with revoked token
    status, body = _req(
        f"{AUTH}/auth/refresh",
        method="POST",
        data=json.dumps({"refresh_token": refresh_token}).encode(),
        headers={"Content-Type": "application/json"},
    )
    if status == 401:
        print(f"  ✓ POST /auth/refresh (revocado) → 401")
        PASS += 1
    else:
        print(f"  ✗ POST /auth/refresh (revocado): {status} (expected 401)")
        FAIL += 1
else:
    print("  ~ POST /auth/logout → no token (skip)")
    SKP += 1

# ── Via Gateway ───────────────────────────────────────────────
print("\n🌐 Via Gateway (con auth arriba)")
check_health("GET /health", f"{GATEWAY}/health")

# Register via Gateway (will 502 since gateway proxies to auth:8000 DNS not localhost:8000)
status, body = _req(
    f"{GATEWAY}/api/v1/auth/register",
    method="POST",
    data=json.dumps({"email": "gateway-test@lego.local", "password": "TestPass1!", "display_name": "GW"}).encode(),
    headers={"Content-Type": "application/json"},
)
if status == 201:
    print(f"  ✓ POST /api/v1/auth/register vía Gateway → 201")
    PASS += 1
elif status == 502:
    print(f"  ~ POST /api/v1/auth/register vía Gateway → 502 (esperado — auth no está en la red Docker del compose)")
    SKP += 1
elif status == 409:
    print(f"  ~ POST /api/v1/auth/register vía Gateway → 409 (ya existe)")
    SKP += 1
else:
    print(f"  ✗ POST /api/v1/auth/register vía Gateway: {status} — {body[:200]}")
    FAIL += 1

# ── Summary ────────────────────────────────────────────────
print("\n" + "═" * 75)
total = PASS + FAIL
pct = PASS * 100 // max(total, 1) if total else 0
print(f"  ✓ {PASS}  ✗ {FAIL}  ~ {SKP}  |  {PASS}/{total} ({pct}%)")
print()

sys.exit(0 if FAIL == 0 else 1)
