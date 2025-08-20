from database.connection import get_db_connection
from models.message import MessageCreate, MessageResponse
from typing import List
import json

class MessageService:
    @staticmethod
    async def create_message(message: MessageCreate) -> MessageResponse:
        """Create a new message in the database"""
        conn = await get_db_connection()
        try:
            # Insert the message
            query = """
                INSERT INTO messages (content, user_id, created_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                RETURNING id, content, user_id, created_at
            """
            row = await conn.fetchrow(query, message.content, message.user_id)
            
            # Get user details for the response
            user_query = "SELECT username, email FROM users WHERE id = $1"
            user_row = await conn.fetchrow(user_query, message.user_id)
            
            return MessageResponse(
                id=row['id'],
                content=row['content'],
                user_id=row['user_id'],
                username=user_row['username'],
                email=user_row['email'],
                created_at=row['created_at']
            )
        finally:
            await conn.close()

    @staticmethod
    async def get_recent_messages(limit: int = 50) -> List[MessageResponse]:
        """Get recent messages with user details"""
        conn = await get_db_connection()
        try:
            query = """
                SELECT m.id, m.content, m.user_id, m.created_at, u.username, u.email
                FROM messages m
                JOIN users u ON m.user_id = u.id
                ORDER BY m.created_at DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            
            messages = []
            for row in reversed(rows):  # Reverse to get chronological order
                messages.append(MessageResponse(
                    id=row['id'],
                    content=row['content'],
                    user_id=row['user_id'],
                    username=row['username'],
                    email=row['email'],
                    created_at=row['created_at']
                ))
            
            return messages
        finally:
            await conn.close()

    @staticmethod
    async def get_messages_by_user(user_id: int, limit: int = 50) -> List[MessageResponse]:
        """Get messages by a specific user"""
        conn = await get_db_connection()
        try:
            query = """
                SELECT m.id, m.content, m.user_id, m.created_at, u.username, u.email
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.user_id = $1
                ORDER BY m.created_at DESC
                LIMIT $2
            """
            rows = await conn.fetch(query, user_id, limit)
            
            messages = []
            for row in reversed(rows):
                messages.append(MessageResponse(
                    id=row['id'],
                    content=row['content'],
                    user_id=row['user_id'],
                    username=row['username'],
                    email=row['email'],
                    created_at=row['created_at']
                ))
            
            return messages
        finally:
            await conn.close()
