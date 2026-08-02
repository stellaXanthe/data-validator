import pytest
from validator.connectors.base import SchemaInfo, ColumnInfo


@pytest.fixture
def source_schema():
    return SchemaInfo(
        table_name="source_table",
        columns=[
            ColumnInfo(name="id", dtype="int64"),
            ColumnInfo(name="first_name", dtype="object"),
            ColumnInfo(name="last_name", dtype="object"),
            ColumnInfo(name="amount", dtype="float64"),
        ],
    )


@pytest.fixture
def target_schema_exact_match():
    """Identical column names to source_schema."""
    return SchemaInfo(
        table_name="target_table",
        columns=[
            ColumnInfo(name="id", dtype="int64"),
            ColumnInfo(name="first_name", dtype="object"),
            ColumnInfo(name="last_name", dtype="object"),
            ColumnInfo(name="amount", dtype="float64"),
        ],
    )


@pytest.fixture
def target_schema_renamed():
    """Slightly renamed columns to test fuzzy matching."""
    return SchemaInfo(
        table_name="target_table",
        columns=[
            ColumnInfo(name="ID", dtype="int64"),        # case difference
            ColumnInfo(name="firstname", dtype="object"),  # missing underscore
            ColumnInfo(name="lastname", dtype="object"),   # missing underscore
            ColumnInfo(name="amount", dtype="float64"),
        ],
    )


@pytest.fixture
def target_schema_type_mismatch():
    return SchemaInfo(
        table_name="target_table",
        columns=[
            ColumnInfo(name="id", dtype="varchar"),   # was int64 in source
            ColumnInfo(name="first_name", dtype="object"),
            ColumnInfo(name="last_name", dtype="object"),
            ColumnInfo(name="amount", dtype="float64"),
        ],
    )