# =====================================================
# FILE: app/models/contract_clause.py
# Contract Clause Model
# =====================================================

from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class ContractClause(Base):
    __tablename__ = "contract_clauses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    clause_library_id = Column(Integer, ForeignKey("clause_library.id"))
    clause_number = Column(String(50))
    clause_title = Column(String(255), nullable=False)
    clause_text = Column(Text, nullable=False)
    clause_text_ar = Column(Text)
    position = Column(Integer, nullable=False)
    is_mandatory = Column(Boolean, default=False)
    is_negotiable = Column(Boolean, default=True)
    status = Column(String(50), default='active')
    
    # AI-specific fields
    ai_generated = Column(Boolean, default=False)  # NEW
    ai_model = Column(String(50))  # NEW: "gpt-4", "claude-3", etc.
    ai_prompt = Column(Text)  # NEW: Store the prompt used
    ai_confidence_score = Column(Float)  # NEW: 0.0-1.0
    ai_suggestions = Column(JSON)  # NEW: Store AI suggestions
    
    added_by = Column(Integer, ForeignKey("users.id"))
    added_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, onupdate=datetime.utcnow)