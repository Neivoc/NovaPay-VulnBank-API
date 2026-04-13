"""NovaPay Bank API — Transaction Routes
VULNS: SQL Injection (API8), SQL Injection with WAF Bypass, Business Logic Flaws (API6)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from urllib.parse import unquote

from app.database import get_db
from app.models import Account, Transaction
from app.schemas import TransferRequest, TransactionResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("/search")
def search_transactions(
    q: str = "",
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search transactions by description.

    VULN API8:2023 — SQL Injection:
    The query parameter is concatenated directly into the SQL query.
    Try: ?q=' OR '1'='1
    Try: ?q=' UNION SELECT id,username,password,email,role,ssn FROM users--
    """
    # VULN: Direct string concatenation — SQL Injection
    query = f"SELECT * FROM transactions WHERE description LIKE '%{q}%'"
    try:
        result = db.execute(text(query))
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"query": q, "count": len(rows), "results": rows}
    except Exception as e:
        # VULN: Also returns the SQL error to the client (information disclosure)
        return {"error": str(e), "query": query}


@router.get("/search-secure")
def search_transactions_waf(
    q: str = "",
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search transactions with a 'WAF' filter — can be bypassed with encoding.

    🔥 BONUS SCENARIO: WAF Bypass via Encoding.

    This endpoint has a basic WAF that blocks common SQL keywords.
    However, it can be bypassed using:
      - Mixed case: uNiOn SeLeCt
      - Comment injection: UN/**/ION SEL/**/ECT

    Blocked (direct):  ?q=' UNION SELECT username,password FROM users--
    Bypass (mixed):    ?q=' uNiOn SeLeCt id,username,password,email,role,ssn,pin FrOm users--
    Bypass (comments): ?q=' UN/**/ION SEL/**/ECT id,username,password,email,role,ssn,pin FR/**/OM users--
    """
    # "WAF" — only blocks if the EXACT uppercase keyword appears in the original input
    blocked_keywords = ["UNION", "SELECT", "DROP", "DELETE", "INSERT", "UPDATE"]

    for keyword in blocked_keywords:
        # VULN: Only checks if the keyword appears in EXACT UPPERCASE in the original input.
        # Mixed case like "uNiOn" or "SeLeCt" will NOT match "UNION" or "SELECT".
        if keyword in q:
            return {
                "error": "Potential SQL injection detected",
                "blocked_keyword": keyword,
                "message": "Your request has been blocked by NovaPay WAF™",
            }

    # If WAF doesn't catch it, same vulnerable query as /search
    query = f"SELECT * FROM transactions WHERE description LIKE '%{q}%'"
    try:
        result = db.execute(text(query))
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"query": q, "count": len(rows), "results": rows}
    except Exception as e:
        return {"error": str(e), "query": query}


@router.get("/search-b64")
def search_transactions_b64(
    q: str = "",
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search transactions — input is Base64 decoded before processing.

    🔥 ENCODING BYPASS SCENARIO:
    The WAF inspects the raw (encoded) input for SQL keywords, but then the
    server Base64-decodes it before building the SQL query.
    The student must Base64-encode their payload to bypass the WAF.

    Step 1: Build payload:   ' UNION SELECT id,username,password,email,role,ssn,pin,credit_score FROM users--
    Step 2: Encode in Base64: echo -n "' UNION SELECT ..." | base64
    Step 3: Send encoded:    ?q=<base64_string>
    """
    import base64

    # "WAF" inspects the RAW (still encoded) input — of course it won't find SQL keywords
    blocked_keywords = ["UNION", "SELECT", "DROP", "DELETE", "'", ";", "--"]
    for keyword in blocked_keywords:
        if keyword in q:
            return {
                "error": "Potential SQL injection detected",
                "blocked_keyword": keyword,
                "message": "Your request has been blocked by NovaPay WAF™ v2 (Advanced)",
            }

    # Server Base64-decodes AFTER the WAF check — this is the vulnerability
    try:
        decoded_q = base64.b64decode(q).decode("utf-8")
    except Exception:
        decoded_q = q  # If not valid base64, use as-is

    # Then uses the decoded value directly in SQL — SQLi!
    query = f"SELECT * FROM transactions WHERE description LIKE '%{decoded_q}%'"
    try:
        result = db.execute(text(query))
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"decoded_input": decoded_q, "count": len(rows), "results": rows}
    except Exception as e:
        return {"error": str(e), "decoded_input": decoded_q, "query": query}


@router.post("/transfer", response_model=TransactionResponse)
def transfer_funds(
    req: TransferRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Transfer funds between accounts.

    VULN API6:2023 — Business Logic Flaws:
    - Does NOT verify the from_account belongs to the authenticated user
    - Does NOT check if balance is sufficient
    - Accepts negative amounts (reverse transfer attack)
    - Allows transfer to self
    """
    from_account = db.query(Account).filter(Account.id == req.from_account_id).first()
    to_account = db.query(Account).filter(Account.id == req.to_account_id).first()

    if not from_account:
        raise HTTPException(status_code=404, detail="Source account not found")
    if not to_account:
        raise HTTPException(status_code=404, detail="Destination account not found")

    # VULN: No ownership check — any user can transfer from any account
    # VULN: No balance check — can overdraft
    # VULN: No negative amount check — can steal with negative values
    # VULN: No self-transfer check

    from_account.balance -= req.amount
    to_account.balance += req.amount

    transaction = Transaction(
        from_account_id=req.from_account_id,
        to_account_id=req.to_account_id,
        amount=req.amount,
        description=req.description,
        transaction_type="transfer",
        status="completed",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=list)
def list_transactions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all transactions in the system."""
    transactions = db.query(Transaction).all()
    return [
        {
            "id": t.id,
            "from_account_id": t.from_account_id,
            "to_account_id": t.to_account_id,
            "amount": t.amount,
            "description": t.description,
            "transaction_type": t.transaction_type,
            "status": t.status,
            "created_at": str(t.created_at) if t.created_at else None,
        }
        for t in transactions
    ]
