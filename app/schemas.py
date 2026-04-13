"""NovaPay Bank API — Pydantic Schemas"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─── Auth ───
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None  # VULN: Mass Assignment — should not be user-controllable


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


# ─── User ───
class UserResponse(BaseModel):
    """
    VULN: Excessive Data Exposure — returns ALL fields including sensitive ones.
    A secure version would exclude password, password_hash, ssn, pin, credit_score.
    """
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_admin: bool
    ssn: Optional[str] = None
    pin: Optional[str] = None
    credit_score: Optional[int] = None
    password: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """
    VULN: Mass Assignment — accepts role, is_admin, and any field.
    A secure version would only allow email, full_name.
    """
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_admin: Optional[bool] = None
    credit_score: Optional[int] = None
    pin: Optional[str] = None


# ─── Account ───
class AccountResponse(BaseModel):
    id: int
    account_number: str
    account_type: str
    balance: float
    currency: str
    owner_id: int
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Transaction ───
class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float
    description: Optional[str] = "Transfer"


class TransactionResponse(BaseModel):
    id: int
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    amount: float
    description: Optional[str] = None
    transaction_type: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Search ───
class NoSQLSearchRequest(BaseModel):
    """
    VULN: This accepts arbitrary dict values including MongoDB operators.
    """
    class Config:
        extra = "allow"


# ─── Webhook ───
class WebhookRequest(BaseModel):
    url: str
    event: Optional[str] = "payment_received"


# ─── External Payment ───
class ExternalPaymentRequest(BaseModel):
    provider_url: str
    account_id: int
    amount: float
    currency: str = "USD"
