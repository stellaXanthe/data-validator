from typing import Literal, Union
from pydantic import BaseModel, Field


class FileConnectionConfig(BaseModel):
    type: Literal["file"]
    path: str = Field(..., description="Path to CSV/Parquet/JSON file")


class SqlConnectionConfig(BaseModel):
    type: Literal["sql"]
    connection_string: str = Field(..., description="SQLAlchemy connection string")
    table: str = Field(..., description="Table name to validate")


class DatabricksConnectionConfig(BaseModel):
    type: Literal["databricks"]
    server_hostname: str
    http_path: str
    access_token: str
    table: str = Field(..., description="Fully qualified table, e.g. catalog.schema.table")


ConnectionConfig = Union[FileConnectionConfig, SqlConnectionConfig, DatabricksConnectionConfig]


class ValidationRequest(BaseModel):
    source: ConnectionConfig
    target: ConnectionConfig
    key_columns: list[str] = Field(..., description="Column(s) that uniquely identify a row")
    fuzzy_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Field name matching sensitivity")
    sample_limit: int = Field(50, ge=1, le=1000, description="Max mismatch samples to return")


class SchemaDiffResponse(BaseModel):
    missing_in_target: list[str]
    missing_in_source: list[str]
    type_mismatches: list[tuple[str, str, str]]


class ValidationResponse(BaseModel):
    field_map: dict[str, str]
    schema_diff: SchemaDiffResponse
    source_row_count: int
    target_row_count: int
    matched_rows: int
    missing_in_target: int
    missing_in_source: int
    value_mismatches: int
    duplicate_keys_source: int
    duplicate_keys_target: int
    mismatch_samples: list[dict]


class ConnectionTestRequest(BaseModel):
    connection: ConnectionConfig


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str