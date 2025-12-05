# # =====================================================
# # FILE: app/core/auth.py (ADD THIS FUNCTION)
# # =====================================================

# from typing import Optional
# from fastapi import Request
# from sqlalchemy.orm import Session
# from app.models.user import User

# async def get_current_user(
#     request: Request,
#     db: Session
# ) -> Optional[User]:
#     """
#     Get current user if authenticated, return None if not
#     Used for pages that work both with and without authentication
#     """
#     try:
#         # Try to get user from session
#         user_id = request.session.get("user_id")
        
#         if not user_id:
#             return None
        
#         # Get user from database
#         user = db.query(User).filter(User.id == user_id).first()
        
#         if not user or not user.is_active:
#             return None
        
#         return user
        
#     except Exception as e:
#         logger.error(f"Optional auth error: {str(e)}")
#         return None