"""
Server Diagnostics Script
Run this in another terminal to monitor what the server is doing
"""

import subprocess
import sys
import time

print("=" * 70)
print("NiftyMind WebSocket Debugging Guide")
print("=" * 70)

print("\n📋 STEP 1: Check if server is running")
print("-" * 70)
print("In a NEW terminal, run:")
print("  cd backend")
print("  python main.py")
print("\n✓ Server should print:")
print("  - SIMULATOR FUNCTION ENTERED")
print("  - SIMULATOR FIRST SLEEP DONE - ENTERING LOOP")
print("  - SIMULATOR connection_manager id: <ID_NUMBER>")

print("\n📋 STEP 2: Run the test client")
print("-" * 70)
print("In ANOTHER terminal, run:")
print("  cd backend")
print("  python test_ws.py")
print("\n✓ You should see:")
print("  - TEST CLIENT connecting...")
print("  - TEST CLIENT connected")
print("  - THEN on server console: MANAGER CONNECT called - total now: 1")
print("  - THEN: SIMULATOR TICK - connections: 1")
print("  - THEN: SIMULATOR BROADCASTING to 1 clients")
print("  - THEN on client: ✓ TEST CLIENT received: syn_NIFTY_000001")

print("\n🔍 STEP 3: What to check if it hangs")
print("-" * 70)

checks = [
    ("Server prints 'SIMULATOR FUNCTION ENTERED'?", 
     "If NO → Simulator task not running"),
    ("Client prints 'TEST CLIENT connected'?",
     "If YES but no messages → Connection not registered"),
    ("Server prints 'MANAGER CONNECT called'?",
     "If NO → Client connection not reaching manager"),
    ("Server prints 'SIMULATOR TICK - connections: 1'?",
     "If NO → Connection count still 0"),
    ("Check singleton IDs match?",
     "Both should print same ID, if different → import bug"),
]

for i, (check, action) in enumerate(checks, 1):
    print(f"\n{i}. {check}")
    print(f"   {action}")

print("\n" + "=" * 70)
print("🚨 COMMON ISSUES:")
print("=" * 70)
print("""
1. HANG on "waiting for messages..."
   → Server not running OR
   → Simulator not broadcasting (check connection_count in server output)

2. Client prints "connected" but no server output
   → Connection accepted but manager.connect() not called
   → Check ws_feed.py imports

3. Server prints "SIMULATOR TICK - connections: 0"
   → Client connected but not registered
   → Check connection_manager singleton ID mismatch

4. "CONNECTION REFUSED"
   → Server not running
   → Start with: python main.py

5. Different singleton IDs
   → Both imports not from same module
   → Check line: from app.websockets.connection_manager import connection_manager
""")

print("=" * 70)
