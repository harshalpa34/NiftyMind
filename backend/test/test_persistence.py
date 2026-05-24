import httpx
import json
import os
import sys

BASE = "http://localhost:8000/api/v1"


def check(resp, label):
    """Check response status and return JSON"""
    if resp.status_code not in (200, 201):
        print(f"❌ ERROR: {label} returned {resp.status_code}")
        print(f"Response: {resp.text}")
        exit(1)
    return resp.json()


def test_create_and_persist():
    """STEP 1 & 2: Create session and add 2 trades, save session_id"""
    print("\n" + "="*60)
    print("  STEP 1: Creating session and adding 2 trades...")
    print("="*60)
    
    
    
    # Create session
    r = httpx.post(f"{BASE}/sessions?user_id=harshal")
    session = check(r, "Create session")
    session_id = session["session_id"]
    print(f"\n✅ Session created: {session_id}")
    
    # Trade 1: LONG entry=24500, close at 24300 (loss)
    print("\n>>> Trade 1 (LONG):")
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/trades",
        json={
            "symbol": "NIFTY",
            "direction": "LONG",
            "entry_price": 24500,
            "quantity": 50,
            "notes": "Trade 1"
        }
    )
    trade_data = check(r, "Open trade 1")
    open_trade_ids = trade_data.get("open_trade_ids", [])
    if not open_trade_ids:
        print("❌ No trade_id in response")
        exit(1)
    
    trade_id = open_trade_ids[-1]
    print(f"   ✅ Trade opened: {trade_id}")
    
    # Close trade 1
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/trades/close",
        json={
            "trade_id": trade_id,
            "exit_price": 24300
        }
    )
    state1 = check(r, "Close trade 1")
    print(f"   ✅ Trade closed | PnL: {state1['total_pnl']}")
    
    # Trade 2: SHORT entry=24500, close at 24700 (loss)
    print("\n>>> Trade 2 (SHORT):")
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/trades",
        json={
            "symbol": "NIFTY",
            "direction": "SHORT",
            "entry_price": 24500,
            "quantity": 50,
            "notes": "Trade 2"
        }
    )
    trade_data = check(r, "Open trade 2")
    open_trade_ids = trade_data.get("open_trade_ids", [])
    if not open_trade_ids:
        print("❌ No trade_id in response")
        exit(1)
    
    trade_id = open_trade_ids[-1]
    print(f"   ✅ Trade opened: {trade_id}")
    
    # Close trade 2
    r = httpx.post(
        f"{BASE}/sessions/{session_id}/trades/close",
        json={
            "trade_id": trade_id,
            "exit_price": 24700
        }
    )
    state2 = check(r, "Close trade 2")
    print(f"   ✅ Trade closed | PnL: {state2['total_pnl']}")
    
    # Print state before saving
    print("\n" + "="*60)
    print("  Session State (Before Restart)")
    print("="*60)
    print(f"Total Trades: {state2['total_trades']}")
    print(f"Total PnL: {state2['total_pnl']}")
    print(f"Consecutive Losses: {state2['consecutive_losses']}")
    print(f"Guardrail Active: {state2['guardrail_active']}")
    
    # Save session_id to file
    os.makedirs("test", exist_ok=True)
    with open("test/last_session_id.txt", "w") as f:
        f.write(session_id)
    
    print("\n" + "="*60)
    print("  STEP 2: Saving session ID...")
    print("="*60)
    print(f"\n✅ Session ID saved to test/last_session_id.txt")
    print(f"   Session ID: {session_id}")
    print(f"\n📝 NEXT STEPS:")
    print(f"   1. Stop the server (Ctrl+C)")
    print(f"   2. Run: python test/test_persistence.py recover")
    print(f"   3. Verify session state persisted to SQLite")


def test_recover():
    """STEP 3, 4, 5: Recover session after restart"""
    print("\n" + "="*60)
    print("  STEP 3: Reading saved session ID...")
    print("="*60)
    
    # Read session_id
    if not os.path.exists("test/last_session_id.txt"):
        print("❌ ERROR: Session ID file not found")
        print("   Run: python test/test_persistence.py")
        exit(1)
    
    with open("test/last_session_id.txt", "r") as f:
        session_id = f.read().strip()
    
    print(f"\n✅ Session ID loaded: {session_id}")
    
    # STEP 4: Recover via endpoint
    print("\n" + "="*60)
    print("  STEP 4: Calling recover endpoint...")
    print("="*60)
    
    r = httpx.get(f"{BASE}/sessions/{session_id}/recover")
    recovered = check(r, "Recover session")
    
    print(f"\n✅ Session recovered successfully!")
    print(f"   Session ID: {recovered['session_id']}")
    print(f"   Total Trades: {recovered['total_trades']}")
    print(f"   Total PnL: {recovered['total_pnl']}")
    print(f"   Consecutive Losses: {recovered['consecutive_losses']}")
    print(f"   Guardrail Active: {recovered['guardrail_active']}")
    
    # STEP 5: Verify state
    print("\n" + "="*60)
    print("  STEP 5: Verification Results")
    print("="*60)
    
    checks = [
        ("total_trades == 2", recovered["total_trades"] == 2),
        ("total_pnl < 0", recovered["total_pnl"] < 0),
        ("consecutive_losses == 2", recovered["consecutive_losses"] == 2),
        ("session_id matches", recovered["session_id"] == session_id),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        emoji = "✅" if passed else "❌"
        print(f"{emoji} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 Session persistence test PASSED!")
        print("   All state survived the server restart.")
    else:
        print("\n⚠️  Some checks failed")
        exit(1)


# Main execution
if __name__ == "__main__":
    print("="*60)
    print("Session Persistence Test")
    print("Make sure the server is running: python main.py")
    print("="*60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "recover":
        # Recovery mode
        test_recover()
    else:
        # Initial creation mode
        test_create_and_persist()
