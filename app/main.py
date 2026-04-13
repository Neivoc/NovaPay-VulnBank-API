"""
╔═══════════════════════════════════════════════════════════════╗
║                   NovaPay Bank API v2.3.1                     ║
║          ⚠️  DELIBERATELY VULNERABLE — FOR EDUCATION ONLY     ║
║                                                               ║
║  OWASP API Security Top 10 2023 — Full Coverage Lab          ║
║  - Swagger UI:  /docs                                        ║
║  - ReDoc:       /redoc                                       ║
║  - OpenAPI:     /openapi.json (for OWASP ZAP import)         ║
╚═══════════════════════════════════════════════════════════════╝
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base, SessionLocal
from app.seed import seed_database


# ─── Lifespan: create tables & seed on startup ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


# ─── FastAPI App ───
app = FastAPI(
    title="NovaPay Bank API",
    description="""
🏦 **NovaPay Bank** — Digital Banking REST API

RESTful API for NovaPay Bank's digital banking platform.
Provides endpoints for account management, transactions, user management, and notifications.

---
**API Version:** 2.3.1  
**Contact:** api-support@novapay.com  
**Documentation:** [NovaPay Developer Portal](https://developers.novapay.com)

> 📥 **Download OpenAPI spec** from `/openapi.json` for use with OWASP ZAP or Postman.
    """,
    version="2.3.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Authentication", "description": "User login and registration"},
        {"name": "Accounts", "description": "Bank account operations"},
        {"name": "Users", "description": "User profile management"},
        {"name": "Transactions", "description": "Fund transfers and transaction search"},
        {"name": "Search", "description": "User directory search (NoSQL backend)"},
        {"name": "Admin", "description": "Administrative operations"},
        {"name": "Notifications", "description": "Webhook and notification management"},
        {"name": "External Payments", "description": "Third-party payment processing"},
        {"name": "Legacy API v1", "description": "Deprecated v1 endpoints (maintained for backward compatibility)"},
    ],
)


# ─── CORS (wide open — intentional) ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Insecure Response Headers Middleware ───
# VULN API8:2023 — Sensitive Data in Response Headers
@app.middleware("http")
async def add_insecure_headers(request: Request, call_next):
    response: Response = await call_next(request)

    # VULN: Exposes server technology stack
    response.headers["X-Powered-By"] = "FastAPI/0.104.1 Python/3.11"
    response.headers["Server"] = "NovaPay-Internal/2.3.1 Ubuntu"

    # VULN: Exposes internal version and debug mode
    response.headers["X-Internal-Version"] = "2.3.1-build-4892"
    response.headers["X-Debug-Mode"] = "enabled"
    response.headers["X-Request-ID"] = "npay-" + str(id(request))

    # VULN: Exposes backend infrastructure
    response.headers["X-Backend-Server"] = "api-node-03.internal.novapay.com"
    response.headers["X-Database"] = "SQLite-3.42.0"

    return response


# ─── Include all route modules ───
from app.routes import auth, accounts, users, transactions, search, admin, webhooks, payments, legacy

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(users.router)
app.include_router(transactions.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(webhooks.router)
app.include_router(payments.router)
app.include_router(legacy.router)


# ─── Root endpoint ───
@app.get("/", tags=["Status"])
def root():
    return {
        "name": "NovaPay Bank API",
        "version": "2.3.1",
        "status": "operational",
        "documentation": "/docs",
        "openapi_spec": "/openapi.json",
    }


@app.get("/health", tags=["Status"])
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "uptime": "operational",
    }
