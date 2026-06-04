import aiohttp

class BinanceRESTClient:
    BASE_URL = "https://api.binance.com/api/v3"

    async def get_current_price(self, asset: str) -> float:
        symbol = f"{asset.upper()}USDT"
        url = f"{self.BASE_URL}/ticker/price?symbol={symbol}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get("price", 0.0))
        except Exception as e:
            print(f"[BINANCE ERROR] Gagal mengambil harga: {e}")
        return 0.0