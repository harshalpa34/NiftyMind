import httpx
import json

BASE = "http://localhost:8000/api/v1"


def pretty(label, data):
    """Print formatted JSON output"""
    print(f"\n{'='*50}")
    print(f"  {label}")
    print('='*50)
    print(json.dumps(data, indent=2, default=str))


def check(resp, label):
    """Check response status and return JSON"""
    if resp.status_code not in (200, 201):
        print(f"[ERROR] {label} returned {resp.status_code}")
        print(f"Response: {resp.text}")
        exit(1)
    return resp.json()


# Authentication setup
def get_auth_headers():
    import uuid
    # Use a unique email per test run so registration always succeeds
    unique_id = uuid.uuid4().hex[:8]
    email = f"testuser_{unique_id}@niftymind.com"
    password = "password123"
    
    # 1. Try to register
    r = httpx.post(
        f"{BASE}/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User"
        }
    )
    print(f"Register status: {r.status_code}, Response: {r.text}")
    if r.status_code == 201:
        data = r.json()
        return {"Authorization": f"Bearer {data['access_token']}"}
        
    # 2. Fallback to login in case of registration issues (using a generic email)
    r = httpx.post(
        f"{BASE}/auth/login",
        json={
            "email": "testuser@niftymind.com",
            "password": password
        }
    )
    if r.status_code == 200:
        data = r.json()
        return {"Authorization": f"Bearer {data['access_token']}"}
        
    print("[ERROR] Authentication failed.")
    print(r.text)
    exit(1)


# Acquire auth headers
print("\nAuthenticating...")
headers = get_auth_headers()
print("Authentication successful!")


# STEP 1 — Create session
print("\n" + "="*50)
print("  STEP 1 - CREATE SESSION")
print("="*50)

r = httpx.post(f"{BASE}/sessions", headers=headers)
session = check(r, "Create session")
session_id = session["session_id"]
pretty("SESSION CREATED", session)
print(f"\n>>> Session ID: {session_id}")


# STEP 2 — Add 3 trades and close each at loss
for i in range(1, 4):
    print("\n" + "="*50)
    print(f"  TRADE {i}")
    print("="*50)
    
    # Open trade
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/trades",
        headers=headers,
        json={
            "symbol": "NIFTY",
            "direction": "LONG",
            "entry_price": 24500,
            "quantity": 50,
            "notes": f"Trade {i} - test"
        }
    )
    trade_data = check(r, f"Open trade {i}")
    print(f"  total_trades: {trade_data.get('total_trades')}")
    print(f"  last_analysis: {trade_data.get('last_analysis')}")
    
    # Extract trade_id from open_trade_ids
    open_trade_ids = trade_data.get("open_trade_ids", [])
    if not open_trade_ids:
        print(f"[ERROR] No open_trade_ids in response for trade {i}")
        exit(1)
    
    trade_id = open_trade_ids[-1]  # Last item
    print(f"  >>> trade_id: {trade_id}")
    
    # Close trade at loss
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/trades/close",
        headers=headers,
        json={
            "trade_id": trade_id,
            "exit_price": 24300  # Loss — exit below entry for LONG
        }
    )
    state = check(r, f"Close trade {i}")
    print(f"  total_pnl: {state.get('total_pnl')}")
    print(f"  consecutive_losses: {state.get('consecutive_losses')}")
    print(f"  guardrail_active: {state.get('guardrail_active')}")
    
    # Print behavior flags
    flags = state.get("behavior_flags", [])
    if flags:
        flag_types = [f.get("flag_type") for f in flags]
        print(f"  behavior_flags: {flag_types}")


# STEP 3 — Get final session state
print("\n" + "="*50)
print("  STEP 3 - GET FINAL SESSION STATE")
print("="*50)

r = httpx.get(f"{BASE}/sessions/{session_id}", headers=headers)
final_state = check(r, "Get final session state")

pretty("FINAL SESSION STATE", {
    "session_id": final_state.get("session_id"),
    "total_trades": final_state.get("total_trades"),
    "total_pnl": final_state.get("total_pnl"),
    "consecutive_losses": final_state.get("consecutive_losses"),
    "guardrail_active": final_state.get("guardrail_active"),
    "last_analysis": final_state.get("last_analysis"),
    "behavior_flags": final_state.get("behavior_flags")
})


# STEP 4 — Verification results
print("\n" + "="*50)
print("  VERIFICATION RESULTS")
print("="*50)

checks = [
    ("total_trades == 3", final_state.get("total_trades") == 3),
    ("consecutive_losses == 3", final_state.get("consecutive_losses") == 3),
    ("total_pnl < 0", final_state.get("total_pnl", 0) < 0),
    ("guardrail_active == True", final_state.get("guardrail_active") is True),
    ("REVENGE_TRADE flag present", any(
        f.get("flag_type") == "REVENGE_TRADE" 
        for f in final_state.get("behavior_flags", [])
    ))
]

for check_name, passed in checks:
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"{status_str} {check_name}")

all_passed = all(passed for _, passed in checks)
if all_passed:
    print("\nAll checks passed!")
else:
    print("\nSome checks failed!")
    exit(1)