# app/infrastructure/polymarket_api.py
import aiohttp
from typing import Optional, List, Dict

class PolymarketRESTClient:
    BASE_URL = "https://gamma-api.polymarket.com"

    async def fetch_event_by_slug(self, slug: str) -> Optional[Dict]:
        """Metode C: Mencari event berdasarkan slug spesifik"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/events?slug={slug}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Gamma API mengembalikan list event, kita ambil index 0 jika ada
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
        return None

    async def fetch_active_events(self) -> List[Dict]:
        """Metode A Fallback: Mengambil data market yang sedang aktif"""
        async with aiohttp.ClientSession() as session:
            # Dibatasi 100 agar tidak terlalu berat, bisa disesuaikan
            url = f"{self.BASE_URL}/events?active=true&closed=false&limit=100" 
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
        return []