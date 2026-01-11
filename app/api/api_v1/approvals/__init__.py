"""
Approvals Module Init
File: app/api/api_v1/approvals/__init__.py
"""

from fastapi import APIRouter
from . import pending_actions

router = APIRouter()

# Include pending actions router
router.include_router(pending_actions.router)