"""NovaPay Bank API — External Payments Routes
VULN: Unsafe Consumption of APIs (API10)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models import Account
from app.schemas import ExternalPaymentRequest
from app.auth import get_current_user

router = APIRouter(prefix="/api/payments", tags=["External Payments"])


@router.post("/external")
async def process_external_payment(
    req: ExternalPaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Process a payment through an external payment provider.

    VULN API10:2023 — Unsafe Consumption of APIs:
    - Makes request to user-supplied provider URL without SSL verification
    - Trusts and processes the external API's response without validation
    - Does not sanitize response data before applying to account

    Try: Set up a malicious server that returns {"approved": true, "amount_credited": 999999}
    The API will blindly trust and apply the response.
    """
    account = db.query(Account).filter(Account.id == req.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        # VULN: No SSL verification, no URL allowlist, user controls destination
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            response = await client.post(
                req.provider_url,
                json={
                    "account": account.account_number,
                    "amount": req.amount,
                    "currency": req.currency,
                },
            )

            # VULN: Blindly trusts the external response
            provider_data = response.json()

            # VULN: Applies provider's amount_credited without validation
            if provider_data.get("approved", False):
                credited = provider_data.get("amount_credited", req.amount)
                account.balance += credited  # Trusts external amount
                db.commit()
                return {
                    "status": "completed",
                    "provider_response": provider_data,
                    "amount_credited": credited,
                    "new_balance": account.balance,
                }
            else:
                return {
                    "status": "declined",
                    "provider_response": provider_data,
                }

    except httpx.ConnectError:
        return {"status": "error", "message": f"Cannot connect to provider: {req.provider_url}"}
    except Exception as e:
        # VULN: Leaks stack trace
        return {"status": "error", "message": str(e), "provider_url": req.provider_url}
