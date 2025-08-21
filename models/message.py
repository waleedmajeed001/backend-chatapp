from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class MessageCreate(BaseModel):
    content: str
    user_id: int
    recipient_id: Optional[int] = None
    message_type: Optional[str] = "text"
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    reply_to_id: Optional[str] = None

class MessageResponse(BaseModel):
    id: int
    content: str
    user_id: int
    username: str
    email: str
    recipient_id: Optional[int] = None
    recipient_username: Optional[str] = None
    recipient_email: Optional[str] = None
    created_at: datetime
    message_type: Optional[str] = "text"
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    reply_to_message: Optional[dict] = None
    reactions: Optional[List[dict]] = []

class MessageInDB(BaseModel):
    id: int
    content: str
    user_id: int
    recipient_id: Optional[int] = None
    created_at: datetime
    message_type: Optional[str] = "text"
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    reply_to_id: Optional[str] = None
