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

app = FastAPI(
    title="Data Validator API",
    description="Validates data flow between source and target systems — schema matching, row comparison, duplicate detection.",
    version="1.0.0",
)

# Adjust allowed origins once you know where the frontend will be hosted
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before production use
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/connections/test", response_model=ConnectionTestResponse)
def test_connection(request: ConnectionTestRequest):
    try:
        connector, _ = build_connector(request.connection)
        success = connector.test_connection()
        return ConnectionTestResponse(
            success=success,
            message="Connection successful" if success else "Connection failed",
        )
    except Exception as e:
        return ConnectionTestResponse(success=False, message=str(e))


@app.post("/validate", response_model=ValidationResponse)
def validate(request: ValidationRequest):
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

        result = compare_data(
            source_df,
            target_df,
            field_map,
            key_columns=request.key_columns,
            sample_limit=request.sample_limit,
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
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")