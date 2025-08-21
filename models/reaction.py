from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReactionCreate(BaseModel):
    message_id: str
    user_id: int
    emoji: str

class ReactionResponse(BaseModel):
    id: int
    message_id: str
    user_id: int
    emoji: str
    created_at: datetime
    username: str
    email: str

class ReactionInDB(BaseModel):
    id: int
    message_id: str
    user_id: int
    emoji: str
    created_at: datetime
