# app/domain/models.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class PolymarketEvent:
    name: str
    slug: str
    token_id_yes: str
    token_id_no: str
    end_date: Optional[str] = None
    is_active: bool = False
    is_closed: bool = False