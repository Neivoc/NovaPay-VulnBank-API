"""NovaPay Bank API — User Routes
VULNS: Excessive Data Exposure + Mass Assignment (API3)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserUpdateRequest
from app.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user profile.

    VULN API3:2023 — Excessive Data Exposure:
    Returns ALL user fields including ssn, pin, password, password_hash, credit_score.
    """
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    updates: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user profile.

    VULN API3:2023 — Mass Assignment:
    Accepts and applies 'role', 'is_admin', 'credit_score', 'pin' from the request body.
    A secure version would only allow email and full_name.
    """
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # VULN: Apply ALL provided fields without filtering
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user
