import asyncio
import websockets
import json
from datetime import datetime

async def watch():
    async with websockets.connect("ws://localhost:8000/ws/feed") as ws:
        print("CLIENT A connected")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            time = datetime.now().strftime("%H:%M:%S")
            print(f"CLIENT A [{time}] {data['snapshot_id']} | Spot: {data['spot_price']}")

asyncio.run(watch())
