import json
from app.domain.models import PolymarketEvent
from app.helpers.time_utils import generate_polymarket_slug
from app.infrastructure.polymarket_api import PolymarketRESTClient

class FetchPolymarketEventUseCase:
    def __init__(self):
        self.api_client = PolymarketRESTClient()

    async def execute(self, asset: str, timeframe: str) -> PolymarketEvent:
        # 1. Generate Slug (Metode C)
        slug = generate_polymarket_slug(asset, timeframe)
        print(f"[SYSTEM] Mencari event dengan metode Slug: {slug}")
        
        event_data = await self.api_client.fetch_event_by_slug(slug)

        # 2. Validasi (Metode B)
        # PERBAIKAN: Kita mengecek apakah ticker (misal 'btc') ada di dalam string slug, bukan di judul.
        if not event_data or asset.lower() not in event_data.get('slug', '').lower():
            print("[SYSTEM] Event tidak ditemukan via Slug. Beralih ke Fallback (Metode A & B)...")
            event_data = await self._run_fallback(asset, timeframe)

        if not event_data:
            raise Exception(f"Gagal menemukan event aktif untuk {asset.upper()} ({timeframe})")

        # 3. Ekstraksi Data 
        try:
            market = event_data['markets'][0]
            market_name = event_data.get('title', 'Unknown Market')
            
            clob_token_string = market.get('clobTokenIds', '[]')
            token_ids = json.loads(clob_token_string)
            
            if len(token_ids) < 2:
                token_ids = ["Token_Yes_Not_Found", "Token_No_Not_Found"] 
                
            token_id_yes = token_ids[0]
            token_id_no = token_ids[1]

            # AMBIL STATUS MARKET DARI JSON
            is_active = event_data.get('active', False)
            is_closed = event_data.get('closed', False)

            return PolymarketEvent(
                name=market_name,
                slug=event_data.get('slug', slug),
                token_id_yes=token_id_yes,
                token_id_no=token_id_no,
                end_date=event_data.get('endDate'),
                is_active=is_active,
                is_closed=is_closed
            )
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise Exception(f"Gagal memparsing struktur JSON Polymarket: {e}")

    async def _run_fallback(self, asset: str, timeframe: str):
        """Menjalankan Metode A (Time-Window) dan Metode B (Slug Validation)"""
        active_events = await self.api_client.fetch_active_events()
        
        # Target slug format: "btc-updown-15m"
        target_slug_pattern = f"{asset.lower()}-updown-{timeframe.lower()}"
        
        for event in active_events:
            event_slug = event.get('slug', '').lower()
            
            # PERBAIKAN: Cek kecocokan pola slug langsung
            if target_slug_pattern in event_slug:
                return event
                
        return None