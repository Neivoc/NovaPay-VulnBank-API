"""NovaPay Bank API — Admin Routes
VULN: Broken Function Level Authorization (API5)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User
from app.schemas import UserResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all users (admin endpoint).

    VULN API5:2023 — Broken Function Level Authorization:
    Only checks that a valid token exists, does NOT verify user role is 'admin'.
    Any authenticated user can access this admin endpoint.
    """
    # VULN: No role check — should be: if current_user["role"] != "admin": raise 403
    users = db.query(User).all()
    return users


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a user (admin endpoint).

    VULN API5:2023 — Broken Function Level Authorization:
    Same as above — no admin role verification.
    """
    # VULN: No role check
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.username} (ID: {user_id}) deleted successfully"}


@router.get("/stats")
def get_system_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get system statistics (admin endpoint).

    VULN API5:2023 — No role check.
    """
    from app.models import Account, Transaction

    return {
        "total_users": db.query(User).count(),
        "total_accounts": db.query(Account).count(),
        "total_transactions": db.query(Transaction).count(),
        "system_version": "NovaPay API v2.3.1-internal",
        "database": "SQLite 3.x",
        "debug_mode": True,
        "jwt_secret": "secret",  # VULN: Leaking the JWT secret!
    }
