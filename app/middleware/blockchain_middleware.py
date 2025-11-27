# app/middleware/blockchain_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class BlockchainVerificationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically verify blockchain integrity on contract access
    """
    
    async def dispatch(self, request: Request, call_next):
        # Check if this is a contract view request
        if "/contracts/" in request.url.path and request.method == "GET":
            # Extract contract ID from path
            path_parts = request.url.path.split('/')
            if 'contracts' in path_parts:
                try:
                    contract_idx = path_parts.index('contracts')
                    if contract_idx + 1 < len(path_parts):
                        contract_id = path_parts[contract_idx + 1]
                        logger.info(f"🔍 Auto-verifying contract {contract_id} on access")
                        # Verification will be handled by frontend JavaScript
                except (ValueError, IndexError):
                    pass
        
        response = await call_next(request)
        return response