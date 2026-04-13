"""NovaPay Bank API — Database Configuration"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./bank.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ─── Fake NoSQL Store (simulates MongoDB for NoSQL Injection demo) ───
# In-memory dict store that accepts MongoDB-like operators
nosql_users_collection = []


def nosql_seed():
    """Seed the fake NoSQL store with user documents."""
    global nosql_users_collection
    nosql_users_collection = [
        {"username": "alice", "email": "alice@novapay.com", "department": "retail", "clearance": "low"},
        {"username": "bob", "email": "bob@novapay.com", "department": "corporate", "clearance": "medium"},
        {"username": "carlos", "email": "carlos@novapay.com", "department": "treasury", "clearance": "high"},
        {"username": "admin", "email": "admin@novapay.com", "department": "IT", "clearance": "critical"},
        {"username": "diana", "email": "diana@novapay.com", "department": "compliance", "clearance": "high"},
    ]


def nosql_query(filter_dict: dict) -> list:
    """
    VULNERABLE: Simulates MongoDB query with operator support.
    Accepts $gt, $gte, $lt, $lte, $ne, $regex, $exists operators.
    """
    results = []
    for doc in nosql_users_collection:
        match = True
        for key, value in filter_dict.items():
            if key not in doc:
                match = False
                break
            if isinstance(value, dict):
                # Process MongoDB-like operators — THIS IS THE VULNERABILITY
                for op, op_val in value.items():
                    if op == "$gt":
                        if not (doc[key] > op_val):
                            match = False
                    elif op == "$gte":
                        if not (doc[key] >= op_val):
                            match = False
                    elif op == "$lt":
                        if not (doc[key] < op_val):
                            match = False
                    elif op == "$ne":
                        if not (doc[key] != op_val):
                            match = False
                    elif op == "$regex":
                        import re
                        if not re.search(op_val, doc[key]):
                            match = False
                    elif op == "$exists":
                        if op_val and key not in doc:
                            match = False
            else:
                if doc[key] != value:
                    match = False
                    break
        if match:
            results.append(doc)
    return results


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
