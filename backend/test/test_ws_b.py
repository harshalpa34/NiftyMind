import asyncio
import websockets
import json
from datetime import datetime

async def watch():
    async with websockets.connect("ws://localhost:8000/ws/feed") as ws:
        print("CLIENT B connected")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            time = datetime.now().strftime("%H:%M:%S")
            print(f"CLIENT B [{time}] {data['snapshot_id']} | Spot: {data['spot_price']}")

asyncio.run(watch())