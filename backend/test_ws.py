import asyncio
import json
import websockets


async def watch():
    print("TEST CLIENT connecting...")
    try:
        async with websockets.connect("ws://localhost:8000/ws/feed") as ws:
            print("TEST CLIENT connected - waiting for messages with 15s timeout...")
            try:
                for i in range(3):
                    print(f"TEST CLIENT waiting for message {i+1}...")
                    msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    data = json.loads(msg)
                    print(f"✓ TEST CLIENT received: {data['snapshot_id']} | PCR: {data['metrics']['pcr']:.4f}")
            except asyncio.TimeoutError:
                print("❌ TIMEOUT: No message received from server in 15 seconds")
                print("   → Check if server is running: python main.py")
                print("   → Check server console for diagnostic output")
    except ConnectionRefusedError:
        print("❌ CONNECTION REFUSED: Server not running on localhost:8000")
        print("   → Start server with: python main.py")
    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(watch())
