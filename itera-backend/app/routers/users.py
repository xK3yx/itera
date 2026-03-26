import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = Field(default=None, max_length=500)
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    education: Optional[str] = None
    current_role: Optional[str] = None
    primary_domain: Optional[str] = None
    experience_years: Optional[int] = Field(default=None, ge=0, le=50)
    tech_stack: Optional[list[str]] = None


def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "full_name": user.full_name,
        "bio": user.bio,
        "github_url": user.github_url,
        "linkedin_url": user.linkedin_url,
        "education": user.education,
        "current_role": user.current_role,
        "primary_domain": user.primary_domain,
        "experience_years": user.experience_years,
        "tech_stack": user.tech_stack or [],
        "profile_completed": user.profile_completed,
    }


async def _apply_update(current_user: User, payload: UserUpdateRequest, db: AsyncSession) -> dict:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    current_user.profile_completed = bool(
        current_user.full_name
        and current_user.bio
        and len(current_user.bio) >= 50
        and current_user.primary_domain
        and current_user.primary_domain != "general"
        and current_user.tech_stack
        and len(current_user.tech_stack) >= 1
    )

    await db.flush()
    await db.refresh(current_user)
    logger.info("[Profile] Updated user=%s profile_completed=%s", current_user.id, current_user.profile_completed)
    return {"data": _user_to_dict(current_user)}


@router.put("/me")
async def update_user_put(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _apply_update(current_user, payload, db)


@router.patch("/me")
async def update_user_patch(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _apply_update(current_user, payload, db)


@router.patch("/{user_id}")
async def update_user_by_id(
    user_id: str,
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify user can only update their own profile
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Cannot update another user's profile")
    return await _apply_update(current_user, payload, db)
