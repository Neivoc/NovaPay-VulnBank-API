"""NovaPay Bank API — JWT Authentication (DELIBERATELY WEAK)"""
import jwt
from fastapi import HTTPException, Header
from typing import Optional


JWT_SECRET = "secret"  # VULN: Weak secret, easily brute-forced
JWT_ALGORITHM = "HS256"


def create_token(user_id: int, username: str, role: str) -> str:
    """Create a JWT token — no expiration, weak secret."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        # VULN: No "exp" claim — token never expires
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    VULN: Broken Authentication — JWT Signature Bypass
    A secure implementation would reject tokens with invalid signatures.
    """
    try:
        # First try normal decode
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.InvalidSignatureError:
        # VULN: Signature is invalid, but the server ignores the error
        # and decodes the token anyway (Signature Bypass).
        try:
            payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256", "none"])
            return payload
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.DecodeError:
        # Try without any verification at all
        try:
            payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256", "none"])
            return payload
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or malformed token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token error: {str(e)}")


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract user from Authorization header. Only checks token presence, not role."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    # Accept "Bearer <token>" or just "<token>"
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token is empty")

    return decode_token(token)
