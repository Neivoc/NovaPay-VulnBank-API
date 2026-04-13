"""NovaPay Bank API — Search Routes
VULN: NoSQL Injection (API8)
"""
from fastapi import APIRouter, Request

from app.database import nosql_query

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.post("/users")
async def search_users(request: Request):
    """
    Search users in the NoSQL directory.

    VULN API8:2023 — NoSQL Injection:
    Accepts MongoDB-like query operators in the JSON body.

    Try: {"username": {"$gt": ""}} — returns ALL users
    Try: {"clearance": {"$ne": "low"}} — returns high clearance users
    Try: {"username": {"$regex": "^a"}} — regex search
    """
    body = await request.json()

    # VULN: Passes user input directly to NoSQL query engine without sanitization
    results = nosql_query(body)
    return {
        "filter": body,
        "count": len(results),
        "results": results,
    }
