from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageCreate(BaseModel):
    content: str
    user_id: int

class MessageResponse(BaseModel):
    id: int
    content: str
    user_id: int
    username: str
    email: str
    created_at: datetime

class MessageInDB(BaseModel):
    id: int
    content: str
    user_id: int
    created_at: datetime
