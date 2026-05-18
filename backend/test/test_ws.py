import asyncio
import websockets
import json

async def watch():
    print("Connecting...")
    async with websockets.connect("ws://localhost:8000/ws/feed") as ws:
        print("Connected! Waiting for updates (Ctrl+C to stop)...")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(
                f"[{data['snapshot_id']}] "
                f"Spot: {data['spot_price']} | "
                f"PCR: {data['metrics']['pcr']} | "
                f"Signal: {data['metrics']['pcr_signal']} | "
                f"Narrative: {data['narrative']['sentiment_summary']}"
            )

asyncio.run(watch())