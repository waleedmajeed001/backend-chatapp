from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Any
from services.auth_service import AuthService
from services.message_service import MessageService
from services.private_message_service import PrivateMessageService
from models.message import MessageCreate
from models.private_message import PrivateMessageCreate


router = APIRouter(prefix="", tags=["Chat"])


class ConnectionManager:
  def __init__(self) -> None:
    self.active_connections: List[WebSocket] = []
    self.websocket_to_user: Dict[WebSocket, Dict[str, Any]] = {}
    self.online_users: Dict[str, Dict[str, Any]] = {}
    self.private_rooms: Dict[int, List[WebSocket]] = {}  # conversation_id -> list of websockets
    self.user_to_conversations: Dict[int, List[int]] = {}  # user_id -> list of conversation_ids

  async def connect(self, websocket: WebSocket, user: Dict[str, Any]) -> None:
    await websocket.accept()
    self.active_connections.append(websocket)
    self.websocket_to_user[websocket] = user
    self.online_users[user["email"]] = {"id": user["id"], "username": user["username"], "email": user["email"]}
    
    # Initialize user's conversation list
    if user["id"] not in self.user_to_conversations:
      self.user_to_conversations[user["id"]] = []
    
    print(f"User {user['username']} ({user['email']}) connected. Total online: {len(self.online_users)}")
    print(f"Current online users: {list(self.online_users.keys())}")
    await self.broadcast_online_users()

  async def disconnect(self, websocket: WebSocket) -> None:
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)
    user = self.websocket_to_user.pop(websocket, None)
    if user and user.get("email") in self.online_users:
      self.online_users.pop(user["email"], None)
      
      # Remove user from all private rooms
      if user["id"] in self.user_to_conversations:
        for conversation_id in self.user_to_conversations[user["id"]]:
          if conversation_id in self.private_rooms and websocket in self.private_rooms[conversation_id]:
            self.private_rooms[conversation_id].remove(websocket)
            if not self.private_rooms[conversation_id]:  # If room is empty, remove it
              self.private_rooms.pop(conversation_id, None)
        self.user_to_conversations.pop(user["id"], None)
      
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
    import json
    print(f"Broadcasting online users update: {len(self.online_users)} users")
    await self.broadcast(json.dumps(payload))

  async def add_and_broadcast_message(self, message: Dict[str, Any]) -> None:
    import json
    payload = {"type": "message", "data": message}
    await self.broadcast(json.dumps(payload))
    # Also broadcast online users after each message to keep everyone in sync
    await self.broadcast_online_users()

  async def join_private_room(self, websocket: WebSocket, conversation_id: int) -> None:
    """Join a private conversation room"""
    if conversation_id not in self.private_rooms:
      self.private_rooms[conversation_id] = []
    
    if websocket not in self.private_rooms[conversation_id]:
      self.private_rooms[conversation_id].append(websocket)
    
    user = self.websocket_to_user.get(websocket)
    if user and user["id"] not in self.user_to_conversations:
      self.user_to_conversations[user["id"]] = []
    
    if user and conversation_id not in self.user_to_conversations[user["id"]]:
      self.user_to_conversations[user["id"]].append(conversation_id)
    
    print(f"User {user['username'] if user else 'Unknown'} joined private room {conversation_id}")

  async def leave_private_room(self, websocket: WebSocket, conversation_id: int) -> None:
    """Leave a private conversation room"""
    if conversation_id in self.private_rooms and websocket in self.private_rooms[conversation_id]:
      self.private_rooms[conversation_id].remove(websocket)
      if not self.private_rooms[conversation_id]:
        self.private_rooms.pop(conversation_id, None)
    
    user = self.websocket_to_user.get(websocket)
    if user and user["id"] in self.user_to_conversations:
      if conversation_id in self.user_to_conversations[user["id"]]:
        self.user_to_conversations[user["id"]].remove(conversation_id)
    
    print(f"User {user['username'] if user else 'Unknown'} left private room {conversation_id}")

  async def send_private_message(self, message: Dict[str, Any], conversation_id: int) -> None:
    """Send a message to a specific private conversation"""
    import json
    payload = {"type": "private_message", "data": message}
    
    if conversation_id not in self.private_rooms:
      return
    
    disconnected_websockets = []
    for websocket in list(self.private_rooms[conversation_id]):
      try:
        await websocket.send_text(json.dumps(payload))
      except Exception as e:
        print(f"Error sending private message to connection: {e}")
        disconnected_websockets.append(websocket)
    
    # Clean up broken connections
    for ws in disconnected_websockets:
      await self.disconnect(ws)


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
    import json
    # Get recent messages from database
    recent_messages = await MessageService.get_recent_messages(50)
    messages_data = [{
      "id": msg.id,
      "user": {"id": msg.user_id, "username": msg.username, "email": msg.email},
      "content": msg.content,
      "created_at": msg.created_at.isoformat() + "Z"
    } for msg in recent_messages]
    
    boot_data = {
      "messages": messages_data,
      "online_users": list(manager.online_users.values()),
    }
    
    print(f"Sending boot data to {user['username']}: {len(boot_data['online_users'])} online users")
    await websocket.send_text(json.dumps({"type": "boot", "data": boot_data}))

    while True:
      data = await websocket.receive_text()
      try:
        import json
        message_data = json.loads(data)
        
        if message_data.get("type") == "public_message":
          # Handle public message
          text = message_data.get("content", "").strip()
          if text:
            print(f"Received public message from {user['username']}: {text}")
            try:
              # Save message to database
              message_create = MessageCreate(content=text, user_id=user["id"])
              saved_message = await MessageService.create_message(message_create)
              
              # Prepare message for broadcasting
              message = {
                "id": saved_message.id,
                "user": {"id": saved_message.user_id, "username": saved_message.username, "email": saved_message.email},
                "content": saved_message.content,
                "created_at": saved_message.created_at.isoformat() + "Z",
              }
              print(f"Broadcasting public message to {len(manager.active_connections)} connections")
              await manager.add_and_broadcast_message(message)
            except Exception as e:
              print(f"Error processing public message: {e}")
              error_message = {"type": "error", "data": "Failed to send public message"}
              await websocket.send_text(json.dumps(error_message))
        
        elif message_data.get("type") == "private_message":
          # Handle private message
          conversation_id = message_data.get("conversation_id")
          text = message_data.get("content", "").strip()
          
          if not conversation_id or not text:
            error_message = {"type": "error", "data": "Missing conversation_id or content"}
            await websocket.send_text(json.dumps(error_message))
            continue
          
          print(f"Received private message from {user['username']} in conversation {conversation_id}: {text}")
          try:
            # Verify user is part of this conversation
            conversation = await PrivateMessageService.get_conversation_by_id(conversation_id)
            if not conversation or user["id"] not in [conversation.user1_id, conversation.user2_id]:
              error_message = {"type": "error", "data": "You don't have access to this conversation"}
              await websocket.send_text(json.dumps(error_message))
              continue
            
            # Save private message to database
            private_message_create = PrivateMessageCreate(
              conversation_id=conversation_id,
              sender_id=user["id"],
              content=text
            )
            saved_message = await PrivateMessageService.create_private_message(private_message_create)
            
            # Prepare message for broadcasting
            message = {
              "id": saved_message.id,
              "conversation_id": saved_message.conversation_id,
              "user": {"id": saved_message.sender_id, "username": saved_message.sender_username, "email": saved_message.sender_email},
              "content": saved_message.content,
              "created_at": saved_message.created_at.isoformat() + "Z",
            }
            print(f"Broadcasting private message to conversation {conversation_id}")
            await manager.send_private_message(message, conversation_id)
          except Exception as e:
            print(f"Error processing private message: {e}")
            error_message = {"type": "error", "data": "Failed to send private message"}
            await websocket.send_text(json.dumps(error_message))
        
        elif message_data.get("type") == "join_private_room":
          # Handle joining private room
          conversation_id = message_data.get("conversation_id")
          if conversation_id:
            await manager.join_private_room(websocket, conversation_id)
            # Send confirmation
            await websocket.send_text(json.dumps({
              "type": "joined_private_room",
              "data": {"conversation_id": conversation_id}
            }))
        
        elif message_data.get("type") == "leave_private_room":
          # Handle leaving private room
          conversation_id = message_data.get("conversation_id")
          if conversation_id:
            await manager.leave_private_room(websocket, conversation_id)
            # Send confirmation
            await websocket.send_text(json.dumps({
              "type": "left_private_room",
              "data": {"conversation_id": conversation_id}
            }))
        
        else:
          # Handle legacy text-only messages as public messages
          text = data.strip()
          if text:
            print(f"Received legacy message from {user['username']}: {text}")
            try:
              message_create = MessageCreate(content=text, user_id=user["id"])
              saved_message = await MessageService.create_message(message_create)
              
              message = {
                "id": saved_message.id,
                "user": {"id": saved_message.user_id, "username": saved_message.username, "email": saved_message.email},
                "content": saved_message.content,
                "created_at": saved_message.created_at.isoformat() + "Z",
              }
              print(f"Broadcasting legacy message to {len(manager.active_connections)} connections")
              await manager.add_and_broadcast_message(message)
            except Exception as e:
              print(f"Error processing legacy message: {e}")
              error_message = {"type": "error", "data": "Failed to send message"}
              await websocket.send_text(json.dumps(error_message))
      except json.JSONDecodeError:
        # Handle non-JSON messages as public messages
        text = data.strip()
        if text:
          print(f"Received non-JSON message from {user['username']}: {text}")
          try:
            message_create = MessageCreate(content=text, user_id=user["id"])
            saved_message = await MessageService.create_message(message_create)
            
            message = {
              "id": saved_message.id,
              "user": {"id": saved_message.user_id, "username": saved_message.username, "email": saved_message.email},
              "content": saved_message.content,
              "created_at": saved_message.created_at.isoformat() + "Z",
            }
            print(f"Broadcasting non-JSON message to {len(manager.active_connections)} connections")
            await manager.add_and_broadcast_message(message)
          except Exception as e:
            print(f"Error processing non-JSON message: {e}")
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
    "created_at": msg.created_at.isoformat() + "Z"
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
    "created_at": msg.created_at.isoformat() + "Z"
  } for msg in messages]

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


