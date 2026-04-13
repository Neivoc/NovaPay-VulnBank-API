"""NovaPay Bank API — Legacy v1 Routes
VULN: Improper Inventory Management (API9)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Account

router = APIRouter(tags=["Legacy API v1"])


# ─── Legacy v1 endpoints — NO AUTHENTICATION REQUIRED ───
@router.get("/api/v1/users/{user_id}")
def legacy_get_user(user_id: int, db: Session = Depends(get_db)):
    """
    [LEGACY] Get user by ID — v1 endpoint.

    VULN API9:2023 — Improper Inventory Management:
    This is an old API version that was never decommissioned.
    It has NO authentication and returns full user data including passwords.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}
    return {
        "id": user.id,
        "username": user.username,
        "password": user.password,  # VULN: Returns password in plain text!
        "email": user.email,
        "role": user.role,
        "ssn": user.ssn,
        "pin": user.pin,
    }


@router.get("/api/v1/users")
def legacy_list_users(db: Session = Depends(get_db)):
    """
    [LEGACY] List all users — v1 endpoint with no auth.

    VULN API9:2023 — No authentication, returns everything.
    """
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "password": u.password,
            "email": u.email,
            "role": u.role,
        }
        for u in users
    ]


@router.get("/api/v1/accounts/{account_id}")
def legacy_get_account(account_id: int, db: Session = Depends(get_db)):
    """
    [LEGACY] Get account by ID — no auth required.

    VULN API9:2023 — Legacy endpoint with full account exposure.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        return {"error": "Account not found"}
    return {
        "id": account.id,
        "account_number": account.account_number,
        "balance": account.balance,
        "owner_id": account.owner_id,
    }


# ─── Old Swagger docs still accessible ───
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

legacy_app = FastAPI(
    title="NovaPay API v1 (DEPRECATED)",
    description="⚠️ This is a deprecated version of the API. Do not use in production.",
    version="1.0.0-legacy",
)


@router.get("/api-old/docs")
def old_api_docs():
    """
    VULN API9:2023 — Old Swagger documentation still accessible.
    Reveals deprecated endpoints and internal structure.
    """
    return {
        "message": "NovaPay API v1 — DEPRECATED",
        "warning": "This API version is no longer maintained",
        "endpoints": [
            {"method": "GET", "path": "/api/v1/users", "auth": "none"},
            {"method": "GET", "path": "/api/v1/users/{id}", "auth": "none"},
            {"method": "GET", "path": "/api/v1/accounts/{id}", "auth": "none"},
            {"method": "POST", "path": "/api/v1/transfer", "auth": "basic", "status": "disabled"},
        ],
        "internal_notes": "Migration to v2 completed 2024-03-15. v1 kept for backward compatibility with mobile app v3.x",
    }
