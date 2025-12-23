
# =====================================================
# FILE: app/api/api_v1/experts/websocket.py (OPTIONAL)
# WebSocket support for real-time chat
# =====================================================

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
import json
import logging

from app.core.database import get_db
from app.models.consultation import ExpertSessionMessage

logger = logging.getLogger(__name__)
router = APIRouter()

# Connection manager for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f" Client connected to session: {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f" Client disconnected from session: {session_id}")
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """Broadcast message to all clients in a session"""
        if session_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for conn in disconnected:
                self.disconnect(conn, session_id)

manager = ConnectionManager()

@router.websocket("/ws/consultation/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time consultation
    Handles:
    - Real-time messaging
    - Typing indicators
    - Session updates
    - Document sharing notifications
    """
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get('type')
            
            if message_type == 'message':
                # Handle chat message
                message_data = data.get('data', {})
                
                # Save to database
                new_message = ExpertSessionMessage(
                    session_id=session_id,
                    sender_id=message_data.get('sender_id'),
                    sender_type=message_data.get('sender_type', 'user'),
                    message_type='text',
                    message_content=message_data.get('content')
                )
                db.add(new_message)
                db.commit()
                db.refresh(new_message)
                
                # Broadcast to all clients in session
                await manager.broadcast_to_session(session_id, {
                    'type': 'message',
                    'data': {
                        'id': new_message.id,
                        'sender_id': new_message.sender_id,
                        'sender_name': message_data.get('sender_name'),
                        'content': new_message.message_content,
                        'timestamp': new_message.created_at.isoformat()
                    }
                })
            
            elif message_type == 'typing':
                # Handle typing indicator
                typing_data = data.get('data', {})
                await manager.broadcast_to_session(session_id, {
                    'type': 'typing',
                    'data': {
                        'user_id': typing_data.get('user_id'),
                        'user_name': typing_data.get('user_name'),
                        'is_typing': typing_data.get('is_typing', False)
                    }
                })
            
            elif message_type == 'session_update':
                # Handle session status updates
                update_data = data.get('data', {})
                await manager.broadcast_to_session(session_id, {
                    'type': 'session_update',
                    'data': update_data
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        await manager.broadcast_to_session(session_id, {
            'type': 'user_disconnected',
            'data': {'session_id': session_id}
        })
    except Exception as e:
        logger.error(f" WebSocket error: {str(e)}")
        manager.disconnect(websocket, session_id)
