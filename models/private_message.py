from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class PrivateConversationCreate(BaseModel):
    user1_id: int
    user2_id: int

class PrivateConversationResponse(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    created_at: datetime

class PrivateMessageCreate(BaseModel):
    conversation_id: int
    sender_id: int
    content: str

class PrivateMessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_username: str
    sender_email: str
    content: str
    created_at: datetime

class PrivateMessageInDB(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    created_at: datetime

class ConversationWithMessages(BaseModel):
    conversation: PrivateConversationResponse
    messages: List[PrivateMessageResponse]
    other_user: dict  # Contains id, username, email of the other user

class PrivateMessageWebSocket(BaseModel):
    conversation_id: int
    sender_id: int
    sender_username: str
    sender_email: str
    content: str
    created_at: datetime
