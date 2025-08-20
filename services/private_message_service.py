from database.connection import get_db_connection
from models.private_message import (
    PrivateConversationCreate,
    PrivateConversationResponse,
    PrivateMessageCreate,
    PrivateMessageResponse,
    PrivateMessageInDB,
    ConversationWithMessages
)
from typing import List, Optional

class PrivateMessageService:
    @staticmethod
    async def create_or_get_conversation(user1_id: int, user2_id: int) -> PrivateConversationResponse:
        """Create a new conversation or get existing one between two users"""
        conn = await get_db_connection()
        try:
            # Ensure user1_id is always the smaller ID for consistency
            if user1_id > user2_id:
                user1_id, user2_id = user2_id, user1_id
            
            # Try to get existing conversation
            conversation = await conn.fetchrow(
                "SELECT id, user1_id, user2_id, created_at FROM private_conversations WHERE user1_id = $1 AND user2_id = $2",
                user1_id, user2_id
            )
            
            if conversation:
                return PrivateConversationResponse(
                    id=conversation['id'],
                    user1_id=conversation['user1_id'],
                    user2_id=conversation['user2_id'],
                    created_at=conversation['created_at']
                )
            
            # Create new conversation
            conversation = await conn.fetchrow(
                "INSERT INTO private_conversations (user1_id, user2_id) VALUES ($1, $2) RETURNING id, user1_id, user2_id, created_at",
                user1_id, user2_id
            )
            
            return PrivateConversationResponse(
                id=conversation['id'],
                user1_id=conversation['user1_id'],
                user2_id=conversation['user2_id'],
                created_at=conversation['created_at']
            )
        finally:
            await conn.close()

    @staticmethod
    async def create_private_message(message: PrivateMessageCreate) -> PrivateMessageResponse:
        """Create a new private message"""
        conn = await get_db_connection()
        try:
            # Get sender info
            sender = await conn.fetchrow(
                "SELECT id, username, email FROM users WHERE id = $1",
                message.sender_id
            )
            
            if not sender:
                raise ValueError("Sender not found")
            
            # Insert message
            msg = await conn.fetchrow(
                "INSERT INTO private_messages (conversation_id, sender_id, content) VALUES ($1, $2, $3) RETURNING id, conversation_id, sender_id, content, created_at",
                message.conversation_id, message.sender_id, message.content
            )
            
            return PrivateMessageResponse(
                id=msg['id'],
                conversation_id=msg['conversation_id'],
                sender_id=msg['sender_id'],
                sender_username=sender['username'],
                sender_email=sender['email'],
                content=msg['content'],
                created_at=msg['created_at']
            )
        finally:
            await conn.close()

    @staticmethod
    async def get_conversation_messages(conversation_id: int, limit: int = 50) -> List[PrivateMessageResponse]:
        """Get messages for a specific conversation"""
        conn = await get_db_connection()
        try:
            messages = await conn.fetch(
                """
                SELECT pm.id, pm.conversation_id, pm.sender_id, pm.content, pm.created_at,
                       u.username as sender_username, u.email as sender_email
                FROM private_messages pm
                JOIN users u ON pm.sender_id = u.id
                WHERE pm.conversation_id = $1
                ORDER BY pm.created_at DESC
                LIMIT $2
                """,
                conversation_id, limit
            )
            
            return [
                PrivateMessageResponse(
                    id=msg['id'],
                    conversation_id=msg['conversation_id'],
                    sender_id=msg['sender_id'],
                    sender_username=msg['sender_username'],
                    sender_email=msg['sender_email'],
                    content=msg['content'],
                    created_at=msg['created_at']
                )
                for msg in messages
            ]
        finally:
            await conn.close()

    @staticmethod
    async def get_user_conversations(user_id: int) -> List[ConversationWithMessages]:
        """Get all conversations for a user with recent messages"""
        conn = await get_db_connection()
        try:
            # Get all conversations where user is involved
            conversations = await conn.fetch(
                """
                SELECT c.id, c.user1_id, c.user2_id, c.created_at,
                       CASE 
                           WHEN c.user1_id = $1 THEN c.user2_id 
                           ELSE c.user1_id 
                       END as other_user_id
                FROM private_conversations c
                WHERE c.user1_id = $1 OR c.user2_id = $1
                ORDER BY c.created_at DESC
                """,
                user_id
            )
            
            result = []
            for conv in conversations:
                # Get other user info
                other_user = await conn.fetchrow(
                    "SELECT id, username, email FROM users WHERE id = $1",
                    conv['other_user_id']
                )
                
                # Get recent messages for this conversation
                messages = await conn.fetch(
                    """
                    SELECT pm.id, pm.conversation_id, pm.sender_id, pm.content, pm.created_at,
                           u.username as sender_username, u.email as sender_email
                    FROM private_messages pm
                    JOIN users u ON pm.sender_id = u.id
                    WHERE pm.conversation_id = $1
                    ORDER BY pm.created_at DESC
                    LIMIT 10
                    """,
                    conv['id']
                )
                
                conversation_response = PrivateConversationResponse(
                    id=conv['id'],
                    user1_id=conv['user1_id'],
                    user2_id=conv['user2_id'],
                    created_at=conv['created_at']
                )
                
                messages_response = [
                    PrivateMessageResponse(
                        id=msg['id'],
                        conversation_id=msg['conversation_id'],
                        sender_id=msg['sender_id'],
                        sender_username=msg['sender_username'],
                        sender_email=msg['sender_email'],
                        content=msg['content'],
                        created_at=msg['created_at']
                    )
                    for msg in messages
                ]
                
                result.append(ConversationWithMessages(
                    conversation=conversation_response,
                    messages=messages_response,
                    other_user={
                        'id': other_user['id'],
                        'username': other_user['username'],
                        'email': other_user['email']
                    }
                ))
            
            return result
        finally:
            await conn.close()

    @staticmethod
    async def get_conversation_by_users(user1_id: int, user2_id: int) -> Optional[PrivateConversationResponse]:
        """Get conversation between two specific users"""
        conn = await get_db_connection()
        try:
            # Ensure consistent ordering
            if user1_id > user2_id:
                user1_id, user2_id = user2_id, user1_id
            
            conversation = await conn.fetchrow(
                "SELECT id, user1_id, user2_id, created_at FROM private_conversations WHERE user1_id = $1 AND user2_id = $2",
                user1_id, user2_id
            )
            
            if not conversation:
                return None
            
            return PrivateConversationResponse(
                id=conversation['id'],
                user1_id=conversation['user1_id'],
                user2_id=conversation['user2_id'],
                created_at=conversation['created_at']
            )
        finally:
            await conn.close()

    @staticmethod
    async def get_conversation_by_id(conversation_id: int) -> Optional[PrivateConversationResponse]:
        """Get conversation by ID"""
        conn = await get_db_connection()
        try:
            conversation = await conn.fetchrow(
                "SELECT id, user1_id, user2_id, created_at FROM private_conversations WHERE id = $1",
                conversation_id
            )
            
            if not conversation:
                return None
            
            return PrivateConversationResponse(
                id=conversation['id'],
                user1_id=conversation['user1_id'],
                user2_id=conversation['user2_id'],
                created_at=conversation['created_at']
            )
        finally:
            await conn.close()
