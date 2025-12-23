# =====================================================
# FILE: app/api/api_v1/experts/websocket_consultation.py
# WebSocket Support for Real-Time Consultation
# =====================================================

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from fastapi.websockets import WebSocketState
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

from app.core.database import get_db
from app.models.consultation import ExpertSessionMessage, ExpertSession
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Connection manager for WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[Dict]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: int, user_name: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        
        self.active_connections[session_id].append({
            'websocket': websocket,
            'user_id': user_id,
            'user_name': user_name
        })
        logger.info(f" User {user_name} connected to session: {session_id}")
        
        # Notify others that user joined
        await self.broadcast_to_session(session_id, {
            'type': 'user_joined',
            'data': {
                'user_id': user_id,
                'user_name': user_name,
                'timestamp': datetime.utcnow().isoformat()
            }
        }, exclude_user=user_id)
    
    def disconnect(self, websocket: WebSocket, session_id: str, user_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id] = [
                conn for conn in self.active_connections[session_id]
                if conn['websocket'] != websocket
            ]
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f" User {user_id} disconnected from session: {session_id}")
    
    async def broadcast_to_session(
        self, 
        session_id: str, 
        message: dict, 
        exclude_user: Optional[int] = None
    ):
        """Broadcast message to all clients in a session"""
        if session_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[session_id]:
            # Skip excluded user
            if exclude_user and connection['user_id'] == exclude_user:
                continue
            
            try:
                if connection['websocket'].client_state == WebSocketState.CONNECTED:
                    await connection['websocket'].send_json(message)
                else:
                    disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to user {connection['user_id']}: {str(e)}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn['websocket'], session_id, conn['user_id'])
    
    def get_session_users(self, session_id: str) -> List[Dict]:
        """Get list of users currently in session"""
        if session_id not in self.active_connections:
            return []
        
        return [
            {
                'user_id': conn['user_id'],
                'user_name': conn['user_name']
            }
            for conn in self.active_connections[session_id]
        ]

manager = ConnectionManager()

# =====================================================
# WebSocket Authentication
# =====================================================

async def get_current_user_ws(
    token: str = Query(...),
    db: Session = Depends(get_db)
) -> User:
    """Authenticate WebSocket connection via query parameter token"""
    from app.core.security import verify_token
    
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return user
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

# =====================================================
# WebSocket Endpoint
# =====================================================

@router.websocket("/ws/consultation/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time consultation
    URL: ws://localhost:8000/ws/consultation/{session_id}?token=YOUR_JWT_TOKEN
    
    Handles:
    - Real-time messaging
    - Typing indicators
    - Session updates
    - Document sharing notifications
    - User presence
    """
    
    try:
        # Authenticate user
        try:
            current_user = await get_current_user_ws(token, db)
        except HTTPException as e:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return
        
        # Verify session exists
        session = db.query(ExpertSession).filter(
            ExpertSession.id == session_id
        ).first()
        
        if not session:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session not found")
            return
        
        # Connect user
        user_name = f"{current_user.first_name} {current_user.last_name}"
        await manager.connect(websocket, session_id, current_user.id, user_name)
        
        # Send current session users
        await websocket.send_json({
            'type': 'connected',
            'data': {
                'session_id': session_id,
                'users': manager.get_session_users(session_id)
            }
        })
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get('type')
                
                if message_type == 'message':
                    # Handle chat message
                    await handle_chat_message(
                        session_id, 
                        current_user, 
                        data.get('data', {}), 
                        db
                    )
                
                elif message_type == 'typing':
                    # Handle typing indicator
                    await manager.broadcast_to_session(session_id, {
                        'type': 'typing',
                        'data': {
                            'user_id': current_user.id,
                            'user_name': user_name,
                            'is_typing': data.get('data', {}).get('is_typing', False)
                        }
                    }, exclude_user=current_user.id)
                
                elif message_type == 'session_update':
                    # Handle session status updates
                    await manager.broadcast_to_session(session_id, {
                        'type': 'session_update',
                        'data': data.get('data', {})
                    })
                
                elif message_type == 'document_shared':
                    # Handle document sharing notification
                    await manager.broadcast_to_session(session_id, {
                        'type': 'document_shared',
                        'data': {
                            'user_id': current_user.id,
                            'user_name': user_name,
                            'document': data.get('data', {})
                        }
                    }, exclude_user=current_user.id)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from user {current_user.id}")
                continue
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                continue
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
    
    finally:
        # Cleanup on disconnect
        manager.disconnect(websocket, session_id, current_user.id)
        
        # Notify others that user left
        await manager.broadcast_to_session(session_id, {
            'type': 'user_left',
            'data': {
                'user_id': current_user.id,
                'user_name': user_name,
                'timestamp': datetime.utcnow().isoformat()
            }
        })

# =====================================================
# Message Handler
# =====================================================

async def handle_chat_message(
    session_id: str,
    current_user: User,
    message_data: dict,
    db: Session
):
    """Handle incoming chat message"""
    try:
        content = message_data.get('content', '').strip()
        
        if not content:
            return
        
        # Save to database
        new_message = ExpertSessionMessage(
            session_id=session_id,
            sender_id=current_user.id,
            sender_type='user',
            message_type='text',
            message_content=content
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        # Broadcast to all users in session
        await manager.broadcast_to_session(session_id, {
            'type': 'message',
            'data': {
                'id': new_message.id,
                'sender_id': current_user.id,
                'sender_name': f"{current_user.first_name} {current_user.last_name}",
                'content': content,
                'timestamp': new_message.created_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error handling chat message: {str(e)}")
        db.rollback()