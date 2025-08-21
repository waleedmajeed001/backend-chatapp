from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from typing import Dict, List, Any, Optional
import json
import os
import uuid
from datetime import datetime
from services.auth_service import AuthService
from services.message_service import MessageService
from models.message import MessageCreate
from models.reaction import ReactionCreate
from models.reply import ReplyCreate

router = APIRouter(prefix="", tags=["Chat"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class ConnectionManager:
  def __init__(self) -> None:
    self.active_connections: List[WebSocket] = []
    self.websocket_to_user: Dict[WebSocket, Dict[str, Any]] = {}
    self.online_users: Dict[str, Dict[str, Any]] = {}

  async def connect(self, websocket: WebSocket, user: Dict[str, Any]) -> None:
    await websocket.accept()
    self.active_connections.append(websocket)
    self.websocket_to_user[websocket] = user
    self.online_users[user["email"]] = {"id": user["id"], "username": user["username"], "email": user["email"]}
    print(f"User {user['username']} ({user['email']}) connected. Total online: {len(self.online_users)}")
    print(f"Current online users: {list(self.online_users.keys())}")
    await self.broadcast_online_users()

  async def disconnect(self, websocket: WebSocket) -> None:
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)
    user = self.websocket_to_user.pop(websocket, None)
    if user and user.get("email") in self.online_users:
      self.online_users.pop(user["email"], None)
      print(f"User {user['username']} ({user['email']}) disconnected. Total online: {len(self.online_users)}")
      print(f"Remaining online users: {list(self.online_users.keys())}")

  async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
    try:
      await websocket.send_text(message)
    except Exception as e:
      print(f"Error sending personal message: {e}")
      await self.disconnect(websocket)

  async def broadcast(self, message: str) -> None:
    disconnected_websockets = []
    for connection in list(self.active_connections):
      try:
        await connection.send_text(message)
      except Exception as e:
        print(f"Error broadcasting to connection: {e}")
        disconnected_websockets.append(connection)
    
    # Clean up broken connections
    for ws in disconnected_websockets:
      await self.disconnect(ws)

  async def broadcast_online_users(self) -> None:
    payload = {
      "type": "online_users",
      "data": list(self.online_users.values()),
    }
    print(f"Broadcasting online users update: {len(self.online_users)} users")
    await self.broadcast(json.dumps(payload))

  async def add_and_broadcast_message(self, message: Dict[str, Any]) -> None:
    payload = {"type": "message", "data": message}
    await self.broadcast(json.dumps(payload))
    # Also broadcast online users after each message to keep everyone in sync
    await self.broadcast_online_users()

  async def broadcast_reaction(self, message_id: str, reaction: Dict[str, Any]) -> None:
    payload = {"type": "reaction", "data": {"messageId": message_id, "reaction": reaction}}
    await self.broadcast(json.dumps(payload))

  async def broadcast_delete(self, message_id: str) -> None:
    payload = {"type": "delete", "data": {"messageId": message_id}}
    await self.broadcast(json.dumps(payload))


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
  token = websocket.query_params.get("token")
  if not token:
    await websocket.close(code=4401)
    return

  try:
    # Verify JWT and fetch user
    email = AuthService.verify_token(token)
    user_model = await AuthService.get_user_by_email(email)
    user = {"id": user_model.id, "username": user_model.username, "email": user_model.email}
  except HTTPException:
    await websocket.close(code=4401)
    return
  except Exception:
    await websocket.close(code=1011)
    return

  await manager.connect(websocket, user)

  # Send initial state: recent messages and online users
  try:
    # Get recent messages from database
    recent_messages = await MessageService.get_recent_messages(50)
    messages_data = [{
      "id": msg.id,
      "user": {"id": msg.user_id, "username": msg.username, "email": msg.email},
      "content": msg.content,
      "created_at": msg.created_at.isoformat() + "Z",
      "messageType": msg.message_type or "text",
      "fileUrl": msg.file_url,
      "fileName": msg.file_name,
      "fileSize": msg.file_size,
      "replyTo": msg.reply_to_message,
      "reactions": await MessageService.get_message_reactions(msg.id) if msg.id else []
    } for msg in recent_messages]
    
    boot_data = {
      "messages": messages_data,
      "online_users": list(manager.online_users.values()),
    }
    
    print(f"Sending boot data to {user['username']}: {len(boot_data['online_users'])} online users")
    await websocket.send_text(json.dumps({"type": "boot", "data": boot_data}))

    while True:
      text = await websocket.receive_text()
      if text.strip():
        print(f"Received message from {user['username']}: {text.strip()}")
        try:
          # Parse the message data
          message_data = json.loads(text)
          
          if isinstance(message_data, str):
            # Handle plain text messages (backward compatibility)
            message_create = MessageCreate(
              content=message_data.strip(), 
              user_id=user["id"],
              message_type="text"
            )
          else:
            # Handle structured messages with file uploads, replies, etc.
            message_create = MessageCreate(
              content=message_data.get("content", ""),
              user_id=user["id"],
              recipient_id=message_data.get("recipientId"),
              message_type=message_data.get("messageType", "text"),
              file_url=message_data.get("fileUrl"),
              file_name=message_data.get("fileName"),
              file_size=message_data.get("fileSize"),
              reply_to_id=message_data.get("replyTo")
            )
          
          saved_message = await MessageService.create_message(message_create)
          
          # Prepare message for broadcasting
          message = {
            "id": saved_message.id,
            "user": {"id": saved_message.user_id, "username": saved_message.username, "email": saved_message.email},
            "content": saved_message.content,
            "created_at": saved_message.created_at.isoformat() + "Z",
            "messageType": saved_message.message_type or "text",
            "fileUrl": saved_message.file_url,
            "fileName": saved_message.file_name,
            "fileSize": saved_message.file_size,
            "replyTo": saved_message.reply_to_message,
            "recipientId": saved_message.recipient_id,
            "recipientUsername": saved_message.recipient_username,
            "recipientEmail": saved_message.recipient_email,
            "reactions": []
          }
          print(f"Broadcasting message to {len(manager.active_connections)} connections")
          await manager.add_and_broadcast_message(message)
        except json.JSONDecodeError:
          # Handle plain text messages
          message_create = MessageCreate(content=text.strip(), user_id=user["id"], message_type="text")
          saved_message = await MessageService.create_message(message_create)
          
          message = {
            "id": saved_message.id,
            "user": {"id": saved_message.user_id, "username": saved_message.username, "email": saved_message.email},
            "content": saved_message.content,
            "created_at": saved_message.created_at.isoformat() + "Z",
            "messageType": "text",
            "reactions": []
          }
          await manager.add_and_broadcast_message(message)
        except Exception as e:
          print(f"Error processing message: {e}")
          # Send error message back to sender
          error_message = {"type": "error", "data": "Failed to send message"}
          await websocket.send_text(json.dumps(error_message))
  except WebSocketDisconnect:
    await manager.disconnect(websocket)
  except Exception as e:
    print(f"WebSocket error: {e}")
    # In case of unexpected errors, ensure cleanup and close
    await manager.disconnect(websocket)
    try:
      await websocket.close(code=1011)
    except Exception:
      pass
  finally:
    # Notify others after disconnect
    await manager.broadcast_online_users()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str = Header(...)
):
    """Upload a file and return file information"""
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.replace("Bearer ", "")
        
        # Verify user
        email = AuthService.verify_token(token)
        user = await AuthService.get_user_by_email(email)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get file size
        file_size = len(content)
        
        # Determine file type
        if file.content_type and file.content_type.startswith('image/'):
            message_type = 'image'
        elif file.content_type and file.content_type.startswith('video/'):
            message_type = 'video'
        else:
            message_type = 'file'
        
        return {
            "fileUrl": f"/files/{unique_filename}",
            "fileName": file.filename,
            "fileSize": file_size,
            "messageType": message_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files/{filename}")
async def get_file(filename: str):
    """Serve uploaded files"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@router.post("/messages/{message_id}/reactions")
async def add_reaction(
    message_id: str,
    reaction_data: dict,
    authorization: str = Header(...)
):
    """Add a reaction to a message"""
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.replace("Bearer ", "")
        
        email = AuthService.verify_token(token)
        user = await AuthService.get_user_by_email(email)
        
        reaction_create = ReactionCreate(
            message_id=message_id,
            user_id=user.id,
            emoji=reaction_data["emoji"]
        )
        
        reaction = await MessageService.add_reaction(reaction_create)
        
        # Broadcast reaction to all connected clients
        reaction_payload = {
            "emoji": reaction.emoji,
            "users": [user.email]
        }
        await manager.broadcast_reaction(message_id, reaction_payload)
        
        return {"success": True, "reaction": reaction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add reaction: {str(e)}")


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    authorization: str = Header(...)
):
    """Delete a message (any user can delete any message)"""
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.replace("Bearer ", "")
        
        email = AuthService.verify_token(token)
        user = await AuthService.get_user_by_email(email)
        
        # Check if message exists
        message = await MessageService.get_message_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Delete the message
        await MessageService.delete_message(message_id)
        
        # Broadcast deletion to all connected clients
        await manager.broadcast_delete(message_id)
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")


@router.get("/messages")
async def get_recent_messages(limit: int = 50):
  if limit <= 0:
    limit = 1
  if limit > 200:
    limit = 200
  messages = await MessageService.get_recent_messages(limit)
  return [{
    "id": msg.id,
    "user": {"id": msg.user_id, "username": msg.username, "email": msg.email},
    "content": msg.content,
    "created_at": msg.created_at.isoformat() + "Z",
    "messageType": msg.message_type or "text",
    "fileUrl": msg.file_url,
    "fileName": msg.file_name,
    "fileSize": msg.file_size,
    "replyTo": msg.reply_to_message,
    "reactions": await MessageService.get_message_reactions(msg.id) if msg.id else []
  } for msg in messages]

@router.get("/messages/user/{user_id}")
async def get_messages_by_user(user_id: int, limit: int = 50):
  if limit <= 0:
    limit = 1
  if limit > 200:
    limit = 200
  messages = await MessageService.get_messages_by_user(user_id, limit)
  return [{
    "id": msg.id,
    "user": {"id": msg.user_id, "username": msg.username, "email": msg.email},
    "content": msg.content,
    "created_at": msg.created_at.isoformat() + "Z",
    "messageType": msg.message_type or "text",
    "fileUrl": msg.file_url,
    "fileName": msg.file_name,
    "fileSize": msg.file_size,
    "replyTo": msg.reply_to_message,
    "reactions": await MessageService.get_message_reactions(msg.id) if msg.id else []
  } for msg in messages]

@router.get("/messages/direct/{other_user_id}")
async def get_direct_messages(
    other_user_id: int, 
    limit: int = 50,
    authorization: str = Header(...)
):
    """Get direct messages between current user and another user"""
    try:
        # Extract token from Authorization header
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.replace("Bearer ", "")
        
        email = AuthService.verify_token(token)
        user = await AuthService.get_user_by_email(email)
        
        if limit <= 0:
            limit = 1
        if limit > 200:
            limit = 200
            
        messages = await MessageService.get_direct_messages(user.id, other_user_id, limit)
        return [{
            "id": msg.id,
            "user": {"id": msg.user_id, "username": msg.username, "email": msg.email},
            "content": msg.content,
            "created_at": msg.created_at.isoformat() + "Z",
            "messageType": msg.message_type or "text",
            "fileUrl": msg.file_url,
            "fileName": msg.file_name,
            "fileSize": msg.file_size,
            "replyTo": msg.reply_to_message,
            "recipientId": msg.recipient_id,
            "recipientUsername": msg.recipient_username,
            "recipientEmail": msg.recipient_email,
            "reactions": await MessageService.get_message_reactions(msg.id) if msg.id else []
        } for msg in messages]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get direct messages: {str(e)}")

@router.get("/debug/online-users")
async def get_online_users_debug():
  """Debug endpoint to check current online users"""
  return {
    "online_users": list(manager.online_users.values()),
    "total_connections": len(manager.active_connections),
    "connection_details": [
      {
        "user": user,
        "websocket_id": id(ws)
      }
      for ws, user in manager.websocket_to_user.items()
    ]
  }


