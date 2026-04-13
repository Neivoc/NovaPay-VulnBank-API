"""NovaPay Bank API — Auth Routes
VULNS: Broken Authentication (API2), Rate Limiting (API4)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.auth import create_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.

    VULN API2:2023 — Broken Authentication: JWT uses weak secret 'secret', no expiration.
    VULN API4:2023 — Unrestricted Resource Consumption: No rate limiting, no account lockout.
    """
    user = db.query(User).filter(User.username == req.username).first()
    if not user or user.password != req.password:
        # VULN: No rate limit, no lockout, no delay — brute force friendly
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.

    VULN API3:2023 — Mass Assignment: Accepts 'role' field in registration body.
    """
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        username=req.username,
        password=req.password,  # VULN: stored in plain text
        password_hash=f"fakehash_{req.password}_sha256",
        email=req.email,
        full_name=req.full_name,
        role=req.role or "user",  # VULN: Mass Assignment — user controls their role
        is_admin=(req.role == "admin") if req.role else False,
        ssn=f"XXX-XX-{1000 + db.query(User).count():04d}",
        pin=f"{1234 + db.query(User).count():04d}",
        credit_score=650,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )
