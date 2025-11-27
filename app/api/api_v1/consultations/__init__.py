"""
app/api/api_v1/consultations/__init__.py
Initialize consultations module
"""

from .consultations import router as consultations_router
from .schemas import (
    ConsultationListResponse,
    ConsultationDetailResponse,
    ConsultationStatsResponse,
    FeedbackCreateRequest,
    FeedbackResponse
)

__all__ = [
    "consultations_router",
    "ConsultationListResponse",
    "ConsultationDetailResponse",
    "ConsultationStatsResponse",
    "FeedbackCreateRequest",
    "FeedbackResponse"
]