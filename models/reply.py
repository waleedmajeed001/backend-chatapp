from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReplyCreate(BaseModel):
    message_id: str
    reply_to_id: str
    user_id: int

class ReplyResponse(BaseModel):
    id: int
    message_id: str
    reply_to_id: str
    user_id: int
    created_at: datetime
    reply_to_message: dict

class ReplyInDB(BaseModel):
    id: int
    message_id: str
    reply_to_id: str
    user_id: int
    created_at: datetime
