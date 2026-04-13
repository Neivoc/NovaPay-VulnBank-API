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


@router.get("")
@router.get("/")
def admin_root(current_user: dict = Depends(get_current_user)):
    """
    Admin root dashboard.
    This endpoint is SECURE. It correctly verifies the admin role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    return {
        "message": "Welcome to the Admin Dashboard",
        "endpoints": ["/api/admin/users", "/api/admin/stats"]
    }


@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all users (admin endpoint).

    This endpoint is SECURE. It correctly verifies the admin role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")

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

    This endpoint is SECURE. It correctly verifies the admin role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")

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

    VULN API5:2023 — Broken Function Level Authorization:
    The developer properly secured the /users endpoints but FORGOT to add
    the role check here. Any authenticated user can access this!
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
