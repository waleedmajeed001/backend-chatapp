from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Any
from services.auth_service import AuthService
from services.message_service import MessageService
from models.message import MessageCreate


router = APIRouter(prefix="", tags=["Chat"])


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
    await self.broadcast_online_users()

  def disconnect(self, websocket: WebSocket) -> None:
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)
    user = self.websocket_to_user.pop(websocket, None)
    if user and user.get("email") in self.online_users:
      self.online_users.pop(user["email"], None)

  async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
    await websocket.send_text(message)

  async def broadcast(self, message: str) -> None:
    for connection in list(self.active_connections):
      try:
        await connection.send_text(message)
      except Exception:
        # Best-effort: drop broken connections
        self.disconnect(connection)

  async def broadcast_online_users(self) -> None:
    payload = {
      "type": "online_users",
      "data": list(self.online_users.values()),
    }
    import json
    await self.broadcast(json.dumps(payload))

  async def add_and_broadcast_message(self, message: Dict[str, Any]) -> None:
    import json
    await self.broadcast(json.dumps({"type": "message", "data": message}))


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
    
    await websocket.send_text(json.dumps({"type": "boot", "data": {
      "messages": messages_data,
      "online_users": list(manager.online_users.values()),
    }}))

    while True:
      text = await websocket.receive_text()
      if text.strip():
        # Save message to database
        message_create = MessageCreate(content=text.strip(), user_id=user["id"])
        saved_message = await MessageService.create_message(message_create)
        
        # Prepare message for broadcasting
        message = {
          "id": saved_message.id,
          "user": {"id": saved_message.user_id, "username": saved_message.username, "email": saved_message.email},
          "content": saved_message.content,
          "created_at": saved_message.created_at.isoformat() + "Z",
        }
        await manager.add_and_broadcast_message(message)
  except WebSocketDisconnect:
    manager.disconnect(websocket)
  except Exception:
    # In case of unexpected errors, ensure cleanup and close
    manager.disconnect(websocket)
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


