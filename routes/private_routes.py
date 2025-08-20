from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth_service import AuthService
from services.private_message_service import PrivateMessageService
from models.private_message import (
    PrivateConversationCreate,
    PrivateConversationResponse,
    PrivateMessageCreate,
    PrivateMessageResponse,
    ConversationWithMessages
)
from typing import List

router = APIRouter(prefix="/private", tags=["Private Messages"])
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    email = AuthService.verify_token(token)
    user = await AuthService.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@router.post("/conversations", response_model=PrivateConversationResponse)
async def create_conversation(
    conversation: PrivateConversationCreate,
    current_user = Depends(get_current_user)
):
    """Create a new conversation between two users"""
    # Ensure current user is one of the participants
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(status_code=403, detail="You can only create conversations you're part of")
    
    # Ensure users exist
    user1 = await AuthService.get_user_by_id(conversation.user1_id)
    user2 = await AuthService.get_user_by_id(conversation.user2_id)
    
    if not user1 or not user2:
        raise HTTPException(status_code=404, detail="One or both users not found")
    
    return await PrivateMessageService.create_or_get_conversation(conversation.user1_id, conversation.user2_id)

@router.get("/conversations", response_model=List[ConversationWithMessages])
async def get_user_conversations(current_user = Depends(get_current_user)):
    """Get all conversations for the current user"""
    return await PrivateMessageService.get_user_conversations(current_user.id)

@router.get("/conversations/{conversation_id}/messages", response_model=List[PrivateMessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """Get messages for a specific conversation"""
    if limit <= 0:
        limit = 1
    if limit > 200:
        limit = 200
    
    # Verify user is part of this conversation
    conversation = await PrivateMessageService.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")
    
    return await PrivateMessageService.get_conversation_messages(conversation_id, limit)

@router.post("/conversations/{conversation_id}/messages", response_model=PrivateMessageResponse)
async def send_private_message(
    conversation_id: int,
    message: PrivateMessageCreate,
    current_user = Depends(get_current_user)
):
    """Send a private message in a conversation"""
    # Verify user is part of this conversation
    conversation = await PrivateMessageService.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if current_user.id not in [conversation.user1_id, conversation.user2_id]:
        raise HTTPException(status_code=403, detail="You don't have access to this conversation")
    
    # Ensure the sender is the current user
    if message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only send messages as yourself")
    
    # Ensure the conversation_id matches
    if message.conversation_id != conversation_id:
        raise HTTPException(status_code=400, detail="Conversation ID mismatch")
    
    return await PrivateMessageService.create_private_message(message)

@router.get("/conversations/with/{other_user_id}", response_model=PrivateConversationResponse)
async def get_or_create_conversation_with_user(
    other_user_id: int,
    current_user = Depends(get_current_user)
):
    """Get or create a conversation with a specific user"""
    if other_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")
    
    # Ensure the other user exists
    other_user = await AuthService.get_user_by_id(other_user_id)
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await PrivateMessageService.create_or_get_conversation(current_user.id, other_user_id)
