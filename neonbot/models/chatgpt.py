from typing import List

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Chat(BaseModel):
    thread_id: int
    token: int
    messages: List[Message]


class ChatGPT(BaseModel):
    chats: List[Chat]
