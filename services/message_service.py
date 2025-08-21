from database.connection import get_db_connection
from models.message import MessageCreate, MessageResponse
from models.reaction import ReactionCreate, ReactionResponse
from models.reply import ReplyCreate, ReplyResponse
from typing import List, Optional
import json

class MessageService:
    @staticmethod
    async def create_message(message: MessageCreate) -> MessageResponse:
        """Create a new message in the database"""
        conn = await get_db_connection()
        try:
            # Insert the message
            query = """
                INSERT INTO messages (content, user_id, recipient_id, message_type, file_url, file_name, file_size, reply_to_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
                RETURNING id, content, user_id, recipient_id, message_type, file_url, file_name, file_size, reply_to_id, created_at
            """
            row = await conn.fetchrow(
                query, 
                message.content, 
                message.user_id,
                message.recipient_id,
                message.message_type,
                message.file_url,
                message.file_name,
                message.file_size,
                message.reply_to_id
            )
            
            # Get user details for the response
            user_query = "SELECT username, email FROM users WHERE id = $1"
            user_row = await conn.fetchrow(user_query, message.user_id)
            
            # Get reply message details if this is a reply
            reply_to_message = None
            if message.reply_to_id:
                reply_query = """
                    SELECT m.id, m.content, m.message_type, u.username, u.email, u.id as user_id
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    WHERE m.id = $1
                """
                reply_row = await conn.fetchrow(reply_query, message.reply_to_id)
                if reply_row:
                    reply_to_message = {
                        "id": reply_row['id'],
                        "content": reply_row['content'],
                        "messageType": reply_row['message_type'],
                        "user": {
                            "id": reply_row['user_id'],
                            "username": reply_row['username'],
                            "email": reply_row['email']
                        }
                    }
            
            # Get recipient details if this is a direct message
            recipient_username = None
            recipient_email = None
            if row['recipient_id']:
                recipient_query = "SELECT username, email FROM users WHERE id = $1"
                recipient_row = await conn.fetchrow(recipient_query, row['recipient_id'])
                if recipient_row:
                    recipient_username = recipient_row['username']
                    recipient_email = recipient_row['email']
            
            return MessageResponse(
                id=row['id'],
                content=row['content'],
                user_id=row['user_id'],
                username=user_row['username'],
                email=user_row['email'],
                recipient_id=row['recipient_id'],
                recipient_username=recipient_username,
                recipient_email=recipient_email,
                created_at=row['created_at'],
                message_type=row['message_type'],
                file_url=row['file_url'],
                file_name=row['file_name'],
                file_size=row['file_size'],
                reply_to_message=reply_to_message,
                reactions=[]
            )
        finally:
            await conn.close()

    @staticmethod
    async def get_recent_messages(limit: int = 50) -> List[MessageResponse]:
        """Get recent messages with user details"""
        conn = await get_db_connection()
        try:
            query = """
                SELECT m.id, m.content, m.user_id, m.recipient_id, m.message_type, m.file_url, m.file_name, m.file_size, m.reply_to_id, m.created_at, u.username, u.email
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.recipient_id IS NULL
                ORDER BY m.created_at DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            
            messages = []
            for row in reversed(rows):  # Reverse to get chronological order
                # Get reply message details if this is a reply
                reply_to_message = None
                if row['reply_to_id']:
                    reply_query = """
                        SELECT m.id, m.content, m.message_type, u.username, u.email, u.id as user_id
                        FROM messages m
                        JOIN users u ON m.user_id = u.id
                        WHERE m.id = $1
                    """
                    reply_row = await conn.fetchrow(reply_query, row['reply_to_id'])
                    if reply_row:
                        reply_to_message = {
                            "id": reply_row['id'],
                            "content": reply_row['content'],
                            "messageType": reply_row['message_type'],
                            "user": {
                                "id": reply_row['user_id'],
                                "username": reply_row['username'],
                                "email": reply_row['email']
                            }
                        }
                
                # Get recipient details if this is a direct message
                recipient_username = None
                recipient_email = None
                if row['recipient_id']:
                    recipient_query = "SELECT username, email FROM users WHERE id = $1"
                    recipient_row = await conn.fetchrow(recipient_query, row['recipient_id'])
                    if recipient_row:
                        recipient_username = recipient_row['username']
                        recipient_email = recipient_row['email']
                
                messages.append(MessageResponse(
                    id=row['id'],
                    content=row['content'],
                    user_id=row['user_id'],
                    username=row['username'],
                    email=row['email'],
                    recipient_id=row['recipient_id'],
                    recipient_username=recipient_username,
                    recipient_email=recipient_email,
                    created_at=row['created_at'],
                    message_type=row['message_type'],
                    file_url=row['file_url'],
                    file_name=row['file_name'],
                    file_size=row['file_size'],
                    reply_to_message=reply_to_message,
                    reactions=[]
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
                SELECT m.id, m.content, m.user_id, m.message_type, m.file_url, m.file_name, m.file_size, m.reply_to_id, m.created_at, u.username, u.email
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.user_id = $1
                ORDER BY m.created_at DESC
                LIMIT $2
            """
            rows = await conn.fetch(query, user_id, limit)
            
            messages = []
            for row in reversed(rows):
                # Get reply message details if this is a reply
                reply_to_message = None
                if row['reply_to_id']:
                    reply_query = """
                        SELECT m.id, m.content, m.message_type, u.username, u.email, u.id as user_id
                        FROM messages m
                        JOIN users u ON m.user_id = u.id
                        WHERE m.id = $1
                    """
                    reply_row = await conn.fetchrow(reply_query, row['reply_to_id'])
                    if reply_row:
                        reply_to_message = {
                            "id": reply_row['id'],
                            "content": reply_row['content'],
                            "messageType": reply_row['message_type'],
                            "user": {
                                "id": reply_row['user_id'],
                                "username": reply_row['username'],
                                "email": reply_row['email']
                            }
                        }
                
                messages.append(MessageResponse(
                    id=row['id'],
                    content=row['content'],
                    user_id=row['user_id'],
                    username=row['username'],
                    email=row['email'],
                    created_at=row['created_at'],
                    message_type=row['message_type'],
                    file_url=row['file_url'],
                    file_name=row['file_name'],
                    file_size=row['file_size'],
                    reply_to_message=reply_to_message,
                    reactions=[]
                ))
            
            return messages
        finally:
            await conn.close()

    @staticmethod
    async def get_direct_messages(user_id: int, other_user_id: int, limit: int = 50) -> List[MessageResponse]:
        """Get direct messages between two users"""
        conn = await get_db_connection()
        try:
            query = """
                SELECT m.id, m.content, m.user_id, m.recipient_id, m.message_type, m.file_url, m.file_name, m.file_size, m.reply_to_id, m.created_at, u.username, u.email
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE (m.user_id = $1 AND m.recipient_id = $2) OR (m.user_id = $2 AND m.recipient_id = $1)
                ORDER BY m.created_at DESC
                LIMIT $3
            """
            rows = await conn.fetch(query, user_id, other_user_id, limit)
            
            messages = []
            for row in reversed(rows):
                # Get reply message details if this is a reply
                reply_to_message = None
                if row['reply_to_id']:
                    reply_query = """
                        SELECT m.id, m.content, m.message_type, u.username, u.email, u.id as user_id
                        FROM messages m
                        JOIN users u ON m.user_id = u.id
                        WHERE m.id = $1
                    """
                    reply_row = await conn.fetchrow(reply_query, row['reply_to_id'])
                    if reply_row:
                        reply_to_message = {
                            "id": reply_row['id'],
                            "content": reply_row['content'],
                            "messageType": reply_row['message_type'],
                            "user": {
                                "id": reply_row['user_id'],
                                "username": reply_row['username'],
                                "email": reply_row['email']
                            }
                        }
                
                # Get recipient details if this is a direct message
                recipient_username = None
                recipient_email = None
                if row['recipient_id']:
                    recipient_query = "SELECT username, email FROM users WHERE id = $1"
                    recipient_row = await conn.fetchrow(recipient_query, row['recipient_id'])
                    if recipient_row:
                        recipient_username = recipient_row['username']
                        recipient_email = recipient_row['email']
                
                messages.append(MessageResponse(
                    id=row['id'],
                    content=row['content'],
                    user_id=row['user_id'],
                    username=row['username'],
                    email=row['email'],
                    recipient_id=row['recipient_id'],
                    recipient_username=recipient_username,
                    recipient_email=recipient_email,
                    created_at=row['created_at'],
                    message_type=row['message_type'],
                    file_url=row['file_url'],
                    file_name=row['file_name'],
                    file_size=row['file_size'],
                    reply_to_message=reply_to_message,
                    reactions=[]
                ))
            
            return messages
        finally:
            await conn.close()

    @staticmethod
    async def get_message_by_id(message_id: str) -> Optional[MessageResponse]:
        """Get a specific message by ID"""
        conn = await get_db_connection()
        try:
            query = """
                SELECT m.id, m.content, m.user_id, m.recipient_id, m.message_type, m.file_url, m.file_name, m.file_size, m.reply_to_id, m.created_at, u.username, u.email
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.id = $1
            """
            row = await conn.fetchrow(query, message_id)
            
            if not row:
                return None
            
            # Get reply message details if this is a reply
            reply_to_message = None
            if row['reply_to_id']:
                reply_query = """
                    SELECT m.id, m.content, m.message_type, u.username, u.email, u.id as user_id
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    WHERE m.id = $1
                """
                reply_row = await conn.fetchrow(reply_query, row['reply_to_id'])
                if reply_row:
                    reply_to_message = {
                        "id": reply_row['id'],
                        "content": reply_row['content'],
                        "messageType": reply_row['message_type'],
                        "user": {
                            "id": reply_row['user_id'],
                            "username": reply_row['username'],
                            "email": reply_row['email']
                        }
                    }
            
            # Get recipient details if this is a direct message
            recipient_username = None
            recipient_email = None
            if row['recipient_id']:
                recipient_query = "SELECT username, email FROM users WHERE id = $1"
                recipient_row = await conn.fetchrow(recipient_query, row['recipient_id'])
                if recipient_row:
                    recipient_username = recipient_row['username']
                    recipient_email = recipient_row['email']
            
            return MessageResponse(
                id=row['id'],
                content=row['content'],
                user_id=row['user_id'],
                username=row['username'],
                email=row['email'],
                recipient_id=row['recipient_id'],
                recipient_username=recipient_username,
                recipient_email=recipient_email,
                created_at=row['created_at'],
                message_type=row['message_type'],
                file_url=row['file_url'],
                file_name=row['file_name'],
                file_size=row['file_size'],
                reply_to_message=reply_to_message,
                reactions=[]
            )
        finally:
            await conn.close()

    @staticmethod
    async def delete_message(message_id: str) -> bool:
        """Delete a message by ID"""
        conn = await get_db_connection()
        try:
            # First delete reactions
            await conn.execute("DELETE FROM reactions WHERE message_id = $1", message_id)
            
            # Then delete the message
            result = await conn.execute("DELETE FROM messages WHERE id = $1", message_id)
            return result == "DELETE 1"
        finally:
            await conn.close()

    @staticmethod
    async def add_reaction(reaction: ReactionCreate) -> ReactionResponse:
        """Add a reaction to a message"""
        conn = await get_db_connection()
        try:
            # Check if reaction already exists
            existing_query = """
                SELECT id FROM reactions 
                WHERE message_id = $1 AND user_id = $2 AND emoji = $3
            """
            existing = await conn.fetchrow(existing_query, reaction.message_id, reaction.user_id, reaction.emoji)
            
            if existing:
                # Return existing reaction
                query = """
                    SELECT r.id, r.message_id, r.user_id, r.emoji, r.created_at, u.username, u.email
                    FROM reactions r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.id = $1
                """
                row = await conn.fetchrow(query, existing['id'])
                return ReactionResponse(
                    id=row['id'],
                    message_id=row['message_id'],
                    user_id=row['user_id'],
                    emoji=row['emoji'],
                    created_at=row['created_at'],
                    username=row['username'],
                    email=row['email']
                )
            
            # Insert new reaction
            query = """
                INSERT INTO reactions (message_id, user_id, emoji, created_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                RETURNING id, message_id, user_id, emoji, created_at
            """
            row = await conn.fetchrow(query, reaction.message_id, reaction.user_id, reaction.emoji)
            
            # Get user details
            user_query = "SELECT username, email FROM users WHERE id = $1"
            user_row = await conn.fetchrow(user_query, reaction.user_id)
            
            return ReactionResponse(
                id=row['id'],
                message_id=row['message_id'],
                user_id=row['user_id'],
                emoji=row['emoji'],
                created_at=row['created_at'],
                username=user_row['username'],
                email=user_row['email']
            )
        finally:
            await conn.close()

    @staticmethod
    async def get_message_reactions(message_id: str) -> List[dict]:
        """Get all reactions for a message"""
        conn = await get_db_connection()
        try:
            query = """
                SELECT r.emoji, u.email
                FROM reactions r
                JOIN users u ON r.user_id = u.id
                WHERE r.message_id = $1
                ORDER BY r.created_at
            """
            rows = await conn.fetch(query, message_id)
            
            # Group reactions by emoji
            reactions = {}
            for row in rows:
                emoji = row['emoji']
                if emoji not in reactions:
                    reactions[emoji] = []
                reactions[emoji].append(row['email'])
            
            # Convert to list format
            return [{"emoji": emoji, "users": users} for emoji, users in reactions.items()]
        finally:
            await conn.close()
