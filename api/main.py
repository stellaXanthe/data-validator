import logging
from fastapi import Depends
from .auth import get_current_user
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

logger = logging.getLogger("data_validator")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Data Validator API",
    description="Validates data flow between source and target systems — schema matching, row comparison, duplicate detection. No data or credentials are stored or logged.",
    version="1.0.0",
)

# In production, replace "*" with your actual frontend domain, e.g.
# allow_origins=["https://data-validator-ui.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/connections/test", response_model=ConnectionTestResponse)
def test_connection(request: ConnectionTestRequest):
    # Log only the connection TYPE — never the credentials/connection string
    logger.info(f"Connection test requested: type={request.connection.type}")

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
def validate(request: ValidationRequest, user_id: str = Depends(get_current_user)):
    logger.info(f"Validation requested by user={user_id}: source_type={request.source.type}, target_type={request.target.type}")
    # ...rest unchanged...
    # Log only non-sensitive metadata — NEVER the full request body,
    # which may contain connection strings, access tokens, or file paths.
    logger.info(f"Validation requested: source_type={request.source.type}, target_type={request.target.type}")

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

        # Data is loaded into memory only for the duration of this request.
        # It is never written to disk, logged, or persisted anywhere.
        source_df = source_connector.read_data(source_table)
        target_df = target_connector.read_data(target_table)

        result = compare_data(
            source_df,
            target_df,
            field_map,
            key_columns=request.key_columns,
            sample_limit=request.sample_limit,
        )

        logger.info(
            f"Validation complete: matched={result.matched_rows}, "
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
        # Log only the error TYPE, never the full message — some database
        # drivers embed the connection string/credentials in error text.
        logger.error(f"Validation failed with error type: {type(e).__name__}")
        raise HTTPException(
            status_code=500,
            detail="Validation failed. Please check your connection details and try again.",
        )
   