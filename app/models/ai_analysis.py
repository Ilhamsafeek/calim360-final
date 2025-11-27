# =====================================================
# FILE: app/models/ai_analysis.py
# AI Analysis Models for Claude Integration
# =====================================================

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class AIAnalysisResult(Base):
    """Store AI analysis results from Claude API"""
    __tablename__ = "ai_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    analysis_type = Column(String(100), nullable=False)  # 'risk_analysis', 'generation', 'review', etc.
    
    # Analysis results stored as JSON
    analysis_data = Column(JSON, nullable=False)
    
    # Metadata
    confidence_score = Column(Float, default=0.0)
    model_version = Column(String(50), default="claude-sonnet-4-20250514")
    tokens_used = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)
    
    # Status tracking
    status = Column(String(50), default="completed")  # 'processing', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="ai_analyses")
    created_by_user = relationship("User")

class AIQueryHistory(Base):
    """Track AI queries and responses for contracts"""
    __tablename__ = "ai_query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_type = Column(String(100), default="general")  # 'question', 'analysis', 'suggestion'
    
    # Response details
    response_text = Column(Text, nullable=False)
    response_data = Column(JSON, nullable=True)  # Structured response data
    
    # Metadata
    confidence_score = Column(Float, default=0.0)
    tokens_used = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)
    
    # Context
    context_data = Column(JSON, nullable=True)  # Additional context provided
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract")
    user = relationship("User")

class AITemplate(Base):
    """AI-generated contract templates"""
    __tablename__ = "ai_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    
    # Template details
    template_name = Column(String(255), nullable=False)
    template_type = Column(String(100), nullable=False)
    template_category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # AI-generated content
    template_content = Column(Text, nullable=False)
    template_content_ar = Column(Text, nullable=True)
    
    # Generation metadata
    generation_prompt = Column(Text, nullable=True)
    generation_parameters = Column(JSON, nullable=True)
    confidence_score = Column(Float, default=0.0)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])

class AIClauseSuggestion(Base):
    """AI-suggested clause improvements"""
    __tablename__ = "ai_clause_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    clause_id = Column(Integer, ForeignKey("contract_clauses.id"), nullable=True)
    
    # Original clause
    original_clause_text = Column(Text, nullable=False)
    clause_type = Column(String(100), nullable=False)
    
    # AI suggestion
    suggested_clause_text = Column(Text, nullable=False)
    improvement_type = Column(String(100), nullable=False)  # 'clarity', 'risk_mitigation', 'compliance'
    suggestion_rationale = Column(Text, nullable=False)
    
    # Risk assessment
    risk_reduction_score = Column(Float, default=0.0)
    compliance_improvement = Column(Float, default=0.0)
    clarity_improvement = Column(Float, default=0.0)
    
    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 rating
    is_accepted = Column(Boolean, default=False)
    feedback_notes = Column(Text, nullable=True)
    
    # Metadata
    confidence_score = Column(Float, default=0.0)
    priority_level = Column(String(20), default="medium")  # 'high', 'medium', 'low'
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    contract = relationship("Contract")
    clause = relationship("ContractClause")
    created_by_user = relationship("User")

# =====================================================
# Update existing Contract model to include AI relationships
# =====================================================

# Add this to your existing Contract model in app/models/contract.py:
"""
# Add these relationships to the Contract model:

# AI Analysis relationship
ai_analyses = relationship("AIAnalysisResult", back_populates="contract", cascade="all, delete-orphan")

# AI Suggestions relationship
ai_suggestions = relationship("AIClauseSuggestion", back_populates="contract", cascade="all, delete-orphan")

# AI Queries relationship
ai_queries = relationship("AIQueryHistory", back_populates="contract")

# Helper methods for AI integration
def get_latest_risk_analysis(self):
    \"\"\"Get the most recent risk analysis for this contract\"\"\"
    return self.ai_analyses.filter_by(analysis_type='risk_analysis').order_by(AIAnalysisResult.created_at.desc()).first()

def get_ai_risk_score(self):
    \"\"\"Get the current AI risk score\"\"\"
    latest_analysis = self.get_latest_risk_analysis()
    if latest_analysis and latest_analysis.analysis_data:
        return latest_analysis.analysis_data.get('overall_risk_score', 0.5)
    return 0.5

def has_pending_ai_suggestions(self):
    \"\"\"Check if contract has pending AI suggestions\"\"\"
    return self.ai_suggestions.filter_by(is_accepted=False).count() > 0

def get_ai_confidence_score(self):
    \"\"\"Get average AI confidence score for this contract\"\"\"
    analyses = self.ai_analyses.all()
    if not analyses:
        return 0.0
    
    total_confidence = sum(a.confidence_score for a in analyses)
    return total_confidence / len(analyses)
"""

# =====================================================
# Environment Configuration Update
# =====================================================

"""
Add these to your .env file:

# Claude AI Configuration
CLAUDE_API_KEY=your_claude_api_key_here
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4000
CLAUDE_API_BASE_URL=https://api.anthropic.com/v1/messages

# AI Feature Flags
ENABLE_AI_RISK_ANALYSIS=true
ENABLE_AI_CONTRACT_GENERATION=true
ENABLE_AI_CLAUSE_SUGGESTIONS=true
ENABLE_AI_COMPLIANCE_CHECK=true

# AI Rate Limiting
AI_REQUESTS_PER_MINUTE=10
AI_REQUESTS_PER_HOUR=100
AI_REQUESTS_PER_DAY=500

# AI Cache Settings
AI_CACHE_ENABLED=true
AI_CACHE_TTL_HOURS=24
"""