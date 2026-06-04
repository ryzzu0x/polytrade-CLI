import json
import websockets
import asyncio

class PolymarketWebSocketClient:
    WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    def __init__(self):
        self.connection = None

    async def connect(self):
        # PERBAIKAN: Tambahkan ping_interval agar koneksi dipertahankan (Keep-Alive) oleh server
        self.connection = await websockets.connect(self.WS_URL, ping_interval=20, ping_timeout=20)

    async def subscribe(self, token_ids: list[str]):
        payload = {
            "assets_ids": token_ids,
            "type": "market",
            "initial_dump": True,
            "level": 2,
            "custom_feature_enabled": True
        }
        await self.connection.send(json.dumps(payload))

    async def listen(self):
        try:
            while True:
                try:
                    message = await asyncio.wait_for(self.connection.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if isinstance(data, list):
                        for item in data:
                            yield item
                    elif isinstance(data, dict):
                        yield data
                        
                except asyncio.TimeoutError:
                    yield {"event_type": "TICK"}
                    
        except (websockets.ConnectionClosed, ConnectionError, Exception) as e:
            # Mengirimkan sinyal jika koneksi putus tiba-tiba
            yield {"event_type": "SYSTEM_DISCONNECT"}