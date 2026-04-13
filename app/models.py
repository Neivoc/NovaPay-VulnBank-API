"""NovaPay Bank API — SQLAlchemy ORM Models"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Stored in plain text — intentionally insecure
    password_hash = Column(String, nullable=True)  # Fake hash for Excessive Data Exposure
    email = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")  # user | admin — Mass Assignment target
    is_admin = Column(Boolean, default=False)  # Mass Assignment target
    ssn = Column(String, nullable=True)  # Sensitive — Excessive Data Exposure
    pin = Column(String, nullable=True)  # Sensitive — Excessive Data Exposure
    credit_score = Column(Integer, nullable=True)  # Sensitive — Excessive Data Exposure
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship("Account", back_populates="owner")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, nullable=False)
    account_type = Column(String, default="savings")  # savings | checking
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="accounts")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    transaction_type = Column(String, default="transfer")  # transfer | deposit | withdrawal
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
