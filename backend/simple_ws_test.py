"""
Simple Direct WebSocket Test
This bypasses the simulator to test just the connection manager
"""

import asyncio
import json
import websockets


async def simple_test():
    """Connect, listen for 20 seconds, watch server console"""
    print("\n" + "="*70)
    print("SIMPLE WEBSOCKET TEST")
    print("="*70)
    print("\nConnecting to ws://localhost:8000/ws/feed...")
    print("Watch the SERVER CONSOLE for these messages:\n")
    print("  ✓ WS ROUTE - client connected, calling manager.connect()")
    print("  ✓ MANAGER CONNECT called - total now: 1")
    print("  ✓ WS ROUTE connection_manager id: <ID>")
    print("  ✓ SIMULATOR connection_manager id: <ID>   (should match)")
    print("  ✓ SIMULATOR TICK - connections: 1")
    print("  ✓ SIMULATOR BROADCASTING to 1 clients")
    print("\n" + "-"*70 + "\n")
    
    try:
        async with websockets.connect("ws://localhost:8000/ws/feed") as ws:
            print("✓ CONNECTED to WebSocket\n")
            
            print("Listening for 20 seconds...")
            received_count = 0
            
            try:
                while received_count < 5:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)
                    received_count += 1
                    print(f"  [{received_count}] ✓ Received: {data['snapshot_id']} | PCR: {data['metrics']['pcr']:.4f}")
                    
            except asyncio.TimeoutError:
                if received_count == 0:
                    print("\n❌ TIMEOUT: No messages received")
                    print("\nThis means:")
                    print("  1. Check server console - does it show 'SIMULATOR TICK - connections: 1'?")
                    print("  2. If YES → Simulator running but not broadcasting")
                    print("  3. If NO → Connection not registered in manager")
                    print("  4. Compare connection_manager IDs - should be identical")
                else:
                    print(f"\n✓ Received {received_count} messages before timeout")
                    
    except ConnectionRefusedError:
        print("❌ CONNECTION REFUSED")
        print("   Server not running on localhost:8000")
        print("   Start server with: python main.py")


if __name__ == "__main__":
    asyncio.run(simple_test())
