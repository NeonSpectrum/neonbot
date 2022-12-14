from typing import List, Optional

from pydantic import BaseModel


class ExchangeGiftMember(BaseModel):
    user_id: int
    wishlist: Optional[str]
    chosen: Optional[int]


class ExchangeGift(BaseModel):
    message_id: Optional[int]
    members: List[ExchangeGiftMember]
    budget: Optional[int]
