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
    if r.status_code == 201:
        data = r.json()
        return {"Authorization": f"Bearer {data['access_token']}"}
        
    print("[ERROR] Authentication failed.")
    print(r.text)
    exit(1)


# Acquire auth headers
print("\nAuthenticating...")
headers = get_auth_headers()
print("Authentication successful!")


# STEP 1 — Create a Portfolio
print("\n" + "="*50)
print("  STEP 1 - CREATE PORTFOLIO")
print("="*50)

r = httpx.post(f"{BASE}/portfolios", headers=headers, json={"name": "My Growth Portfolio"})
portfolio = check(r, "Create portfolio")
portfolio_id = portfolio["id"]
pretty("PORTFOLIO CREATED", portfolio)
print(f"\n>>> Portfolio ID: {portfolio_id}")


# STEP 2 — Add Transactions (to build holdings)
print("\n" + "="*50)
print("  STEP 2 - ADD TRANSACTIONS")
print("="*50)

# Transaction 1: BUY INFY
r1 = httpx.post(
    f"{BASE}/portfolios/{portfolio_id}/transactions",
    headers=headers,
    json={
        "symbol": "INFY",
        "quantity": 10,
        "price": 1500.0,
        "transaction_type": "BUY"
    }
)
tx1 = check(r1, "BUY INFY transaction")
pretty("TRANSACTION 1 (BUY INFY)", tx1)

# Transaction 2: BUY TCS
r2 = httpx.post(
    f"{BASE}/portfolios/{portfolio_id}/transactions",
    headers=headers,
    json={
        "symbol": "TCS",
        "quantity": 5,
        "price": 3000.0,
        "transaction_type": "BUY"
    }
)
tx2 = check(r2, "BUY TCS transaction")
pretty("TRANSACTION 2 (BUY TCS)", tx2)


# STEP 3 — Retrieve Portfolio Details & Holdings
print("\n" + "="*50)
print("  STEP 3 - GET PORTFOLIO DETAILS")
print("="*50)

r3 = httpx.get(f"{BASE}/portfolios/{portfolio_id}", headers=headers)
details = check(r3, "Get portfolio details")
pretty("PORTFOLIO DETAILS WITH HOLDINGS", details)


# STEP 4 — Run Behavioral Analysis
print("\n" + "="*50)
print("  STEP 4 - BEHAVIORAL ANALYSIS")
print("="*50)

r4 = httpx.get(f"{BASE}/behavioral-analysis/{portfolio_id}", headers=headers)
flags = check(r4, "Get behavioral analysis")
pretty("BEHAVIORAL FLAGS", flags)


# STEP 5 — Run Risk Analysis
print("\n" + "="*50)
print("  STEP 5 - RISK ANALYSIS")
print("="*50)

r5 = httpx.get(f"{BASE}/risk-analysis/{portfolio_id}", headers=headers)
risk = check(r5, "Get risk analysis")
pretty("RISK ENGINE METRICS", risk)


# STEP 6 — Run AI Recommendations / Portfolio Summary
print("\n" + "="*50)
print("  STEP 6 - AI PORTFOLIO ADVISOR")
print("="*50)

r6 = httpx.get(f"{BASE}/portfolio-summary/{portfolio_id}", headers=headers, timeout=60.0)
summary = check(r6, "Get AI portfolio summary")
pretty("AI PORTFOLIO ADVISOR SUMMARY", summary)


# STEP 7 — Verification results
print("\n" + "="*50)
print("  VERIFICATION RESULTS")
print("="*50)

holdings = details.get("holdings", [])
symbols = {h.get("symbol").upper() for h in holdings}

checks = [
    ("portfolio name matches", details.get("portfolio", {}).get("name") == "My Growth Portfolio"),
    ("holdings contains INFY", "INFY" in symbols),
    ("holdings contains TCS", "TCS" in symbols),
    ("EXCESSIVE_CONCENTRATION flag detected", any(
        f.get("flag_type") == "EXCESSIVE_CONCENTRATION"
        for f in flags
    )),
    ("risk metrics contains HHI score", "diversification_score" in risk),
    ("AI advisor contains observations", "ai_observations" in summary)
]

for check_name, passed in checks:
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"{status_str} {check_name}")

all_passed = all(passed for _, passed in checks)
if all_passed:
    print("\nAll portfolio, risk, and recommendation checks passed successfully!")
else:
    print("\nSome checks failed!")
    exit(1)
