from typing import List, Optional

from pydantic import BaseModel


class ExchangeGiftMember(BaseModel):
    user_id: int
    wishlist: Optional[str] = None
    chosen: Optional[int] = None


class ExchangeGift(BaseModel):
    message_id: Optional[int] = None
    members: List[ExchangeGiftMember]
    budget: Optional[int] = None
    finish: Optional[bool] = None
