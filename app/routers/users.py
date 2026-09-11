from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.schema import User, UserRole
from app.schemas.validation import UserOut

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile", response_model=UserOut)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserOut)
async def update_profile(
    full_name: str,
    bio: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user.full_name = full_name
    if bio is not None:
        current_user.bio = bio
    await db.commit()
    await db.refresh(current_user)
    return current_user
