from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PolymarketEvent:
    name: str
    slug: str
    condition_id: str
    token_id_yes: str
    token_id_no: str
    start_date: Optional[str] = None # TAMBAHAN BARU
    end_date: Optional[str] = None
    is_active: bool = False
    is_closed: bool = False

@dataclass
class PriceLevel:
    price: float
    size: float

@dataclass
class OrderBookUpdate:
    asset_name: str
    token_id: str
    bids: List[PriceLevel]
    asks: List[PriceLevel]
    timestamp: int
    current_volume: float

@dataclass
class MarketHistoryDB:
    condition_id: str
    asset: str
    timeframe: str
    start_time: str
    end_time: str
    winning_outcome: str
    total_volume: float
    asset_price_start: float
    asset_price_end: float