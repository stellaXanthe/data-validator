from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # Clerk user ID (the "sub" claim)
    email = Column(String, nullable=True)
    plan = Column(String, default="free", nullable=False)  # "free" | "pro" | "team"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ValidationRun(Base):
    """
    Stores ONLY metadata about a validation run — never the actual
    source/target data, connection strings, or credentials. This exists
    purely for usage tracking and billing enforcement.
    """
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)  # "file" | "sql" | "databricks"
    target_type = Column(String, nullable=False)
    source_row_count = Column(Integer, nullable=False)
    target_row_count = Column(Integer, nullable=False)
    matched_rows = Column(Integer, nullable=False)
    value_mismatches = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)