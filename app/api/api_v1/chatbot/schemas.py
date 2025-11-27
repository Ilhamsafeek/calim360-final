# =====================================================
# FILE: app/api/api_v1/chatbot/schemas.py
# Pydantic Schemas for Chatbot API
# =====================================================

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime


class ChatQueryRequest(BaseModel):
    """Request schema for chatbot query"""
    query: str = Field(..., min_length=1, max_length=5000, description="User's question or message")
    tone: str = Field(default="formal", description="Response tone")
    language: str = Field(default="en", description="Response language (en, ar)")
    contract_id: Optional[str] = Field(None, description="Optional contract ID for context")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation continuity")
    
    @validator('tone')
    def validate_tone(cls, v):
        allowed_tones = [
            'formal', 'conciliatory', 'friendly', 'assertive',
            'analytical', 'empathetic', 'consultative', 'instructive',
            'neutral', 'persuasive', 'technical', 'simplified'
        ]
        if v not in allowed_tones:
            raise ValueError(f'Tone must be one of: {", ".join(allowed_tones)}')
        return v
    
    @validator('language')
    def validate_language(cls, v):
        if v not in ['en', 'ar']:
            raise ValueError('Language must be either "en" or "ar"')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the key risks in this NDA?",
                "tone": "formal",
                "language": "en",
                "contract_id": "contract-uuid-here",
                "session_id": "session-uuid-here"
            }
        }


class ResponseVariant(BaseModel):
    """Response variant with different approach"""
    variant_id: int
    approach: str
    response: str
    confidence: float
    best_for: str


class ClauseReference(BaseModel):
    """Reference to a contract clause"""
    clause_id: str
    clause_number: str
    clause_title: str
    relevance: str


class ChatQueryResponse(BaseModel):
    """Response schema for chatbot query"""
    success: bool
    message: str
    response: str
    variants: List[ResponseVariant] = []
    clause_references: List[ClauseReference] = []
    confidence_score: float
    session_id: Optional[str] = None
    timestamp: datetime
    tokens_used: int = 0
    processing_time_ms: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Response generated successfully",
                "response": "Based on the contract terms...",
                "variants": [
                    {
                        "variant_id": 1,
                        "approach": "detailed",
                        "response": "Comprehensive analysis...",
                        "confidence": 0.95,
                        "best_for": "Users seeking comprehensive information"
                    }
                ],
                "clause_references": [
                    {
                        "clause_id": "uuid",
                        "clause_number": "5.1",
                        "clause_title": "Confidentiality",
                        "relevance": "referenced"
                    }
                ],
                "confidence_score": 0.95,
                "session_id": "session-uuid",
                "timestamp": "2025-01-30T10:30:00"
            }
        }


class ChatSessionCreate(BaseModel):
    """Request schema for creating a chat session"""
    contract_id: Optional[str] = None
    subject: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "contract_id": "contract-uuid-here",
                "subject": "Contract Review Assistance"
            }
        }


class ChatSessionResponse(BaseModel):
    """Response schema for chat session"""
    success: bool
    message: str
    session_id: str
    session_code: str
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Chat session created successfully",
                "session_id": "session-uuid",
                "session_code": "CHAT-20250130103000-123",
                "created_at": "2025-01-30T10:30:00"
            }
        }


class ChatMessage(BaseModel):
    """Individual chat message"""
    id: str
    sender_type: str  # user, system, expert
    message_content: str
    message_type: str  # text, document, annotation, system
    is_ai_generated: bool
    confidence: Optional[float] = None
    created_at: str


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history"""
    success: bool
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "session-uuid",
                "messages": [
                    {
                        "id": "msg-uuid",
                        "sender_type": "user",
                        "message_content": "What is a force majeure clause?",
                        "message_type": "text",
                        "is_ai_generated": False,
                        "confidence": None,
                        "created_at": "2025-01-30T10:30:00"
                    },
                    {
                        "id": "msg-uuid-2",
                        "sender_type": "system",
                        "message_content": "A force majeure clause is...",
                        "message_type": "text",
                        "is_ai_generated": True,
                        "confidence": 0.95,
                        "created_at": "2025-01-30T10:30:05"
                    }
                ],
                "total_messages": 2
            }
        }


class EscalateRequest(BaseModel):
    """Request to escalate to expert"""
    session_id: str
    reason: str = Field(..., min_length=10, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-uuid",
                "reason": "Need specialized legal expertise on Qatar QFCRA compliance"
            }
        }


class QuickAction(BaseModel):
    """Quick action button for chatbot"""
    id: str
    label: str
    query: str
    icon: str


class ChatbotConfig(BaseModel):
    """Chatbot configuration"""
    available_tones: List[str]
    available_languages: List[str]
    quick_actions: List[QuickAction]
    max_message_length: int
    support_file_upload: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "available_tones": ["formal", "friendly", "technical"],
                "available_languages": ["en", "ar"],
                "quick_actions": [
                    {
                        "id": "1",
                        "label": "Analyze Contract Risk",
                        "query": "Can you analyze the risks in this contract?",
                        "icon": "ti-alert-triangle"
                    }
                ],
                "max_message_length": 5000,
                "support_file_upload": True
            }
        }