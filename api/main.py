import logging
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from validator.matcher import match_fields
from validator.schema import compare_schemas
from validator.comparator import compare_data

from .models import (
    ValidationRequest,
    ValidationResponse,
    SchemaDiffResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
)
from .connector_factory import build_connector
from .auth import get_current_user
from .database import get_db
from .db_models import User, ValidationRun
from .limits import get_plan_limits

logger = logging.getLogger("data_validator")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Data Validator API",
    description="Validates data flow between source and target systems — schema matching, row comparison, duplicate detection. No source/target data or credentials are stored or logged.",
    version="1.0.0",
)

# ↓↓↓ THIS is the part that changed — your real Vercel frontend URL ↓↓↓
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://data-validator-ui.vercel.app"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
# ↑↑↑ ---------------------------------------------------------- ↑↑↑


def get_or_create_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, plan="free")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/connections/test", response_model=ConnectionTestResponse)
def test_connection(request: ConnectionTestRequest, user_id: str = Depends(get_current_user)):
    logger.info(f"Connection test requested by user={user_id}: type={request.connection.type}")

    try:
        connector, _ = build_connector(request.connection)
        success = connector.test_connection()
        return ConnectionTestResponse(
            success=success,
            message="Connection successful" if success else "Connection failed",
        )
    except Exception as e:
        logger.error(f"Connection test failed with error type: {type(e).__name__}")
        return ConnectionTestResponse(success=False, message="Connection failed. Please check your details.")


@app.post("/validate", response_model=ValidationResponse)
def validate(
    request: ValidationRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info(f"Validation requested by user={user_id}: source_type={request.source.type}, target_type={request.target.type}")

    user = get_or_create_user(db, user_id)
    limits = get_plan_limits(user.plan)

    if request.source.type not in limits["connectors"] or request.target.type not in limits["connectors"]:
        raise HTTPException(
            status_code=403,
            detail=f"Your current plan ({user.plan}) doesn't include this connector type. Please upgrade.",
        )

    try:
        source_connector, source_table = build_connector(request.source)
        target_connector, target_table = build_connector(request.target)

        source_schema = source_connector.get_schema(source_table)
        target_schema = target_connector.get_schema(target_table)

        field_map = match_fields(source_schema, target_schema, fuzzy_threshold=request.fuzzy_threshold)

        if not field_map:
            raise HTTPException(status_code=400, detail="No matching fields found between source and target.")

        missing_keys = [k for k in request.key_columns if k not in field_map]
        if missing_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Key column(s) not found in matched fields: {missing_keys}",
            )

        schema_diff = compare_schemas(source_schema, target_schema, field_map)

        source_df = source_connector.read_data(source_table)
        target_df = target_connector.read_data(target_table)

        max_rows = limits["max_rows_per_validation"]
        if max_rows is not None and (len(source_df) > max_rows or len(target_df) > max_rows):
            raise HTTPException(
                status_code=403,
                detail=f"Your current plan ({user.plan}) supports up to {max_rows:,} rows per validation. Please upgrade for larger datasets.",
            )

        result = compare_data(
            source_df,
            target_df,
            field_map,
            key_columns=request.key_columns,
            sample_limit=request.sample_limit,
        )

        # Log usage metadata ONLY — no actual data, no credentials, no file paths
        usage_record = ValidationRun(
            user_id=user_id,
            source_type=request.source.type,
            target_type=request.target.type,
            source_row_count=result.source_row_count,
            target_row_count=result.target_row_count,
            matched_rows=result.matched_rows,
            value_mismatches=result.value_mismatches,
        )
        db.add(usage_record)
        db.commit()

        logger.info(
            f"Validation complete for user={user_id}: matched={result.matched_rows}, "
            f"mismatches={result.value_mismatches}, "
            f"missing_in_target={result.missing_in_target}, "
            f"missing_in_source={result.missing_in_source}"
        )

        return ValidationResponse(
            field_map=field_map,
            schema_diff=SchemaDiffResponse(
                missing_in_target=schema_diff.missing_in_target,
                missing_in_source=schema_diff.missing_in_source,
                type_mismatches=schema_diff.type_mismatches,
            ),
            source_row_count=result.source_row_count,
            target_row_count=result.target_row_count,
            matched_rows=result.matched_rows,
            missing_in_target=result.missing_in_target,
            missing_in_source=result.missing_in_source,
            value_mismatches=result.value_mismatches,
            duplicate_keys_source=result.duplicate_keys_source,
            duplicate_keys_target=result.duplicate_keys_target,
            mismatch_samples=[
                {"key": str(m["key"]), "source": m["source"], "target": m["target"]}
                for m in result.mismatch_samples
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed with error type: {type(e).__name__}")
        raise HTTPException(
            status_code=500,
            detail="Validation failed. Please check your connection details and try again.",
        )


class ValidationRunSummary(BaseModel):
    id: int
    source_type: str
    target_type: str
    source_row_count: int
    target_row_count: int
    matched_rows: int
    value_mismatches: int
    created_at: str


@app.get("/usage/history", response_model=List[ValidationRunSummary])
def usage_history(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    runs = (
        db.query(ValidationRun)
        .filter(ValidationRun.user_id == user_id)
        .order_by(ValidationRun.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        ValidationRunSummary(
            id=r.id,
            source_type=r.source_type,
            target_type=r.target_type,
            source_row_count=r.source_row_count,
            target_row_count=r.target_row_count,
            matched_rows=r.matched_rows,
            value_mismatches=r.value_mismatches,
            created_at=r.created_at.isoformat(),
        )
        for r in runs
    ]


@app.get("/me")
def get_me(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_or_create_user(db, user_id)
    return {"id": user.id, "plan": user.plan, "created_at": user.created_at.isoformat()}