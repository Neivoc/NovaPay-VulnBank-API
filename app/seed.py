"""NovaPay Bank API — Seed Data
Pre-loads the database with realistic users, accounts, and transactions for class.
"""
from sqlalchemy.orm import Session
from app.models import User, Account, Transaction
from app.database import engine, Base, nosql_seed


def seed_database(db: Session):
    """Populate database with default data for the lab."""
    # Check if already seeded
    if db.query(User).count() > 0:
        return

    # ─────────────────────── USERS ───────────────────────
    users_data = [
        {
            "username": "admin",
            "password": "admin123",
            "password_hash": "fakehash_admin123_sha256",
            "email": "admin@novapay.com",
            "full_name": "System Administrator",
            "role": "admin",
            "is_admin": True,
            "ssn": "123-45-6789",
            "pin": "0000",
            "credit_score": 850,
        },
        {
            "username": "alice",
            "password": "password123",
            "password_hash": "fakehash_password123_sha256",
            "email": "alice.johnson@novapay.com",
            "full_name": "Alice Johnson",
            "role": "user",
            "is_admin": False,
            "ssn": "234-56-7890",
            "pin": "4821",
            "credit_score": 720,
        },
        {
            "username": "bob",
            "password": "bob2024",
            "password_hash": "fakehash_bob2024_sha256",
            "email": "bob.martinez@novapay.com",
            "full_name": "Bob Martinez",
            "role": "user",
            "is_admin": False,
            "ssn": "345-67-8901",
            "pin": "9173",
            "credit_score": 680,
        },
        {
            "username": "carlos",
            "password": "qwerty",
            "password_hash": "fakehash_qwerty_sha256",
            "email": "carlos.rivera@novapay.com",
            "full_name": "Carlos Rivera",
            "role": "user",
            "is_admin": False,
            "ssn": "456-78-9012",
            "pin": "5500",
            "credit_score": 790,
        },
        {
            "username": "diana",
            "password": "letmein",
            "password_hash": "fakehash_letmein_sha256",
            "email": "diana.chen@novapay.com",
            "full_name": "Diana Chen",
            "role": "auditor",
            "is_admin": False,
            "ssn": "567-89-0123",
            "pin": "7734",
            "credit_score": 810,
        },
    ]

    users = []
    for data in users_data:
        user = User(**data)
        db.add(user)
        users.append(user)
    db.flush()

    # ─────────────────────── ACCOUNTS ───────────────────────
    accounts_data = [
        # Admin accounts
        {"account_number": "NP-ADMIN-001", "account_type": "checking", "balance": 1000000.00, "currency": "USD", "owner_id": users[0].id},
        # Alice's accounts
        {"account_number": "NP-2024-1001", "account_type": "savings", "balance": 15420.50, "currency": "USD", "owner_id": users[1].id},
        {"account_number": "NP-2024-1002", "account_type": "checking", "balance": 3200.75, "currency": "USD", "owner_id": users[1].id},
        # Bob's accounts
        {"account_number": "NP-2024-2001", "account_type": "savings", "balance": 8750.00, "currency": "USD", "owner_id": users[2].id},
        {"account_number": "NP-2024-2002", "account_type": "checking", "balance": 1100.25, "currency": "USD", "owner_id": users[2].id},
        # Carlos's account
        {"account_number": "NP-2024-3001", "account_type": "savings", "balance": 52300.00, "currency": "USD", "owner_id": users[3].id},
        # Diana's account
        {"account_number": "NP-2024-4001", "account_type": "checking", "balance": 28900.00, "currency": "USD", "owner_id": users[4].id},
    ]

    accounts = []
    for data in accounts_data:
        account = Account(**data)
        db.add(account)
        accounts.append(account)
    db.flush()

    # ─────────────────────── TRANSACTIONS ───────────────────────
    transactions_data = [
        {"from_account_id": accounts[1].id, "to_account_id": accounts[3].id, "amount": 500.00, "description": "Monthly rent payment", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[3].id, "to_account_id": accounts[1].id, "amount": 250.00, "description": "Freelance web development", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[2].id, "to_account_id": accounts[5].id, "amount": 1200.00, "description": "Investment deposit quarterly", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[5].id, "to_account_id": accounts[6].id, "amount": 3500.00, "description": "Corporate consulting fee", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[1].id, "to_account_id": accounts[6].id, "amount": 150.00, "description": "Dinner at restaurant", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[4].id, "to_account_id": accounts[2].id, "amount": 75.50, "description": "Shared grocery expenses", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[0].id, "to_account_id": accounts[1].id, "amount": 10000.00, "description": "Salary deposit April 2024", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[0].id, "to_account_id": accounts[3].id, "amount": 8500.00, "description": "Salary deposit April 2024", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[6].id, "to_account_id": accounts[5].id, "amount": 2000.00, "description": "Audit compliance payment", "transaction_type": "transfer", "status": "completed"},
        {"from_account_id": accounts[3].id, "to_account_id": accounts[4].id, "amount": 420.00, "description": "Utility bill payment", "transaction_type": "transfer", "status": "completed"},
    ]

    for data in transactions_data:
        tx = Transaction(**data)
        db.add(tx)

    db.commit()

    # Seed the fake NoSQL store
    nosql_seed()

    print("✅ Database seeded with 5 users, 7 accounts, and 10 transactions")
    print("───────────────────────────────────────────────────────")
    print("  Default credentials:")
    print("    admin   / admin123   (role: admin)")
    print("    alice   / password123 (role: user)")
    print("    bob     / bob2024    (role: user)")
    print("    carlos  / qwerty    (role: user)")
    print("    diana   / letmein   (role: auditor)")
    print("───────────────────────────────────────────────────────")
