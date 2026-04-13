"""NovaPay Bank API — Account Routes
VULN: Broken Object Level Authorization / BOLA (API1)
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models import Account
from app.schemas import AccountResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.get("/", response_model=List[AccountResponse])
def list_all_accounts(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all accounts in the system.

    VULN API1:2023 — Returns ALL accounts, not just the authenticated user's.
    """
    accounts = db.query(Account).all()
    return accounts


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get account details by ID.

    VULN API1:2023 — Broken Object Level Authorization (BOLA/IDOR):
    Does NOT verify that the account belongs to the authenticated user.
    Any authenticated user can access any account by changing the ID.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # VULN: No check like "if account.owner_id != current_user['user_id']"
    return account
