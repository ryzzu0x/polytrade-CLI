import json
import asyncio
from datetime import datetime, timezone, timedelta # PERBAIKAN: Tambahan timedelta
from app.domain.models import PolymarketEvent, OrderBookUpdate, PriceLevel, MarketHistoryDB
from app.helpers.time_utils import generate_polymarket_slug
from app.infrastructure.polymarket_api import PolymarketRESTClient
from app.infrastructure.polymarket_ws import PolymarketWebSocketClient
from app.infrastructure.db_repository import PostgresRepository

class FetchPolymarketEventUseCase:
    def __init__(self):
        self.api_client = PolymarketRESTClient()

    async def execute(self, asset: str, timeframe: str) -> PolymarketEvent:
        slug = generate_polymarket_slug(asset, timeframe)
        event_data = await self.api_client.fetch_event_by_slug(slug)

        if not event_data or asset.lower() not in event_data.get('slug', '').lower():
            event_data = await self._run_fallback(asset, timeframe)

        if not event_data:
            raise Exception(f"Gagal menemukan event aktif untuk {asset.upper()} ({timeframe})")

        try:
            market = event_data['markets'][0]
            
            clob_token_string = market.get('clobTokenIds', '[]')
            token_ids = json.loads(clob_token_string)
            if len(token_ids) < 2:
                token_ids = ["", ""] 

            # --- PERBAIKAN PERHITUNGAN START TIME YANG PRESISI ---
            end_date_str = event_data.get('endDate')
            start_date_str = event_data.get('startDate') # Fallback bawaan API
            
            if end_date_str:
                try:
                    # Ambil End Date yang valid dari API
                    end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                        
                    # Ekstrak durasi dari string timeframe (contoh: "5m" -> angka 5)
                    minutes_dur = int(''.join(filter(str.isdigit, timeframe)))
                    
                    # START DATE ASLI = END DATE dikurangi Durasi Market
                    start_dt = end_dt - timedelta(minutes=minutes_dur)
                    start_date_str = start_dt.isoformat()
                except Exception:
                    pass

            return PolymarketEvent(
                name=event_data.get('title', 'Unknown Market'),
                slug=event_data.get('slug', slug),
                condition_id=market.get('conditionId', ''),
                token_id_yes=token_ids[0],
                token_id_no=token_ids[1],
                start_date=start_date_str, # Menggunakan waktu yang sudah dikoreksi
                end_date=end_date_str,
                is_active=event_data.get('active', False),
                is_closed=event_data.get('closed', False)
            )
        except Exception as e:
            raise Exception(f"Gagal memparsing JSON Polymarket: {e}")

    async def _run_fallback(self, asset: str, timeframe: str):
        active_events = await self.api_client.fetch_active_events()
        target_slug_pattern = f"{asset.lower()}-updown-{timeframe.lower()}"
        for event in active_events:
            if target_slug_pattern in event.get('slug', '').lower():
                return event
        return None


class StreamPolymarketDataUseCase:
    def __init__(self, db_repo: PostgresRepository):
        self.ws_client = PolymarketWebSocketClient()
        self.db_repo = db_repo
        self.api_client = PolymarketRESTClient()
        self.current_volume = 0.0
        self.current_asset = ""
        self.current_timeframe = ""

    async def _background_oracle_checker(self, slug: str, condition_id: str, token_yes: str, token_no: str):
        # Membersihkan baris LIVE sebelum mengeprint log
        print(f"\r{' ' * 80}\r[BACKGROUND] Agen ditugaskan mencari pemenang untuk {slug}...")
        for _ in range(10):
            await asyncio.sleep(60)
            try:
                event_data = await self.api_client.fetch_event_by_slug(slug)
                if event_data and event_data.get('closed'):
                    market = event_data['markets'][0]
                    winner = "UNKNOWN"
                    outcome_prices = json.loads(market.get('outcomePrices', '["0", "0"]'))
                    if float(outcome_prices[0]) >= 0.99:
                        winner = "YES"
                    elif float(outcome_prices[1]) >= 0.99:
                        winner = "NO"
                    
                    await self.db_repo.update_market_winner(condition_id, winner)
                    return
            except Exception:
                pass 
        print(f"\r{' ' * 80}\r[BACKGROUND] Waktu habis. {slug} tetap PENDING.")

    async def execute(self, event: PolymarketEvent, asset: str, timeframe: str, start_price: float):
        # Reset volume hanya saat fungsi ini dipanggil pertama kali oleh Rollover
        self.current_volume = 0.0 
        self.current_asset = asset
        self.current_timeframe = timeframe
        
        target_end_time = None
        if event.end_date:
            try:
                end_str = event.end_date.replace("Z", "+00:00")
                if "+" not in end_str:
                    end_str += "+00:00"
                target_end_time = datetime.fromisoformat(end_str)
            except ValueError:
                pass

        # --- LOOP RECONNECT INTERNAL ---
        while True:
            try:
                await self.ws_client.connect()
                tokens_to_subscribe = [event.token_id_yes, event.token_id_no]
                await self.ws_client.subscribe(tokens_to_subscribe)

                async for raw_data in self.ws_client.listen():
                    event_type = raw_data.get("event_type")

                    # JIKA PUTUS, HANYA BREAK LOOP LISTEN (BUKAN GENERATOR)
                    if event_type == "SYSTEM_DISCONNECT":
                        yield {"type": "system_log", "message": "⚠️ Jaringan terputus sementara. Melakukan reconnect internal..."}
                        await asyncio.sleep(2)
                        break 

                    # CEK KEDALUWARSA (FORCE SWITCH)
                    if target_end_time:
                        now_utc = datetime.now(timezone.utc)
                        if now_utc >= target_end_time:
                            yield {"type": "system_log", "message": "⏰ Waktu Market Habis! Melakukan Force Rollover..."}
                            
                            history_record = MarketHistoryDB(
                                condition_id=event.condition_id,
                                asset=self.current_asset,
                                timeframe=self.current_timeframe,
                                start_time=event.start_date,
                                end_time=event.end_date,
                                winning_outcome="PENDING", 
                                total_volume=self.current_volume,
                                asset_price_start=start_price, 
                                asset_price_end=0.0 
                            )
                            await self.db_repo.save_market_history(history_record)
                            
                            asyncio.create_task(
                                self._background_oracle_checker(
                                    slug=event.slug, 
                                    condition_id=event.condition_id,
                                    token_yes=event.token_id_yes,
                                    token_no=event.token_id_no
                                )
                            )
                            
                            yield {"type": "rollover"}
                            return # PERBAIKAN: Gunakan return agar keluar sepenuhnya dari execute!

                    if event_type == "TICK":
                        continue

                    if event_type in ["book", "price_change"]:
                        if event_type == "book":
                            token_id = raw_data.get("asset_id")
                            bids = [PriceLevel(float(b['price']), float(b['size'])) for b in raw_data.get('bids', [])]
                            asks = [PriceLevel(float(a['price']), float(a['size'])) for a in raw_data.get('asks', [])]
                            bids.sort(key=lambda x: x.price, reverse=True)
                            asks.sort(key=lambda x: x.price)
                            
                            yield {"type": "ui_update", "data": OrderBookUpdate(
                                asset_name="YES" if str(token_id) == event.token_id_yes else "NO",
                                token_id=str(token_id), bids=bids, asks=asks, timestamp=int(raw_data.get("timestamp", 0)), current_volume=self.current_volume
                            )}
                        
                        elif event_type == "price_change":
                            for change in raw_data.get("price_changes", []):
                                token_id = change.get("asset_id")
                                yield {"type": "ui_update", "data": OrderBookUpdate(
                                    asset_name="YES" if str(token_id) == event.token_id_yes else "NO",
                                    token_id=str(token_id),
                                    bids=[PriceLevel(float(change.get("best_bid", 0)), 0)],
                                    asks=[PriceLevel(float(change.get("best_ask", 0)), 0)],
                                    timestamp=int(raw_data.get("timestamp", 0)),
                                    current_volume=self.current_volume
                                )}

                    elif event_type == "last_trade_price":
                        size = float(raw_data.get("size", 0))
                        self.current_volume += size

            except Exception as e:
                yield {"type": "system_log", "message": f"⚠️ Gagal koneksi: {e}. Mencoba kembali..."}
                await asyncio.sleep(2)