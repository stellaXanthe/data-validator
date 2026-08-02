from validator.schema import compare_schemas, _normalize_type


def test_identical_schemas_no_diff(source_schema, target_schema_exact_match):
    field_map = {"id": "id", "first_name": "first_name", "last_name": "last_name", "amount": "amount"}

    diff = compare_schemas(source_schema, target_schema_exact_match, field_map)

    assert diff.missing_in_target == []
    assert diff.missing_in_source == []
    assert diff.type_mismatches == []


def test_detects_type_mismatch(source_schema, target_schema_type_mismatch):
    field_map = {"id": "id", "first_name": "first_name", "last_name": "last_name", "amount": "amount"}

    diff = compare_schemas(source_schema, target_schema_type_mismatch, field_map)

    assert len(diff.type_mismatches) == 1
    assert diff.type_mismatches[0][0] == "id"


def test_detects_unmapped_source_column(source_schema, target_schema_exact_match):
    # Deliberately leave "amount" out of the field map
    field_map = {"id": "id", "first_name": "first_name", "last_name": "last_name"}

    diff = compare_schemas(source_schema, target_schema_exact_match, field_map)

    assert "amount" in diff.missing_in_target


def test_normalize_type_groups_equivalent_types():
    assert _normalize_type("INT") == _normalize_type("bigint")
    assert _normalize_type("VARCHAR(255)") == _normalize_type("object")
    assert _normalize_type("DECIMAL(10,2)") == _normalize_type("float64")
    assert _normalize_type("TIMESTAMP") == _normalize_type("datetime64[ns]")