from typing import List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Chat(BaseModel):
    thread_id: int
    token: Optional[int] = None
    messages: List[Message]


class ChatGPTModel(BaseModel):
    channel_id: Optional[int] = None
    chats: List[Chat]
