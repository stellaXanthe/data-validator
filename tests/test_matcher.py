from validator.matcher import match_fields
from validator.connectors.base import SchemaInfo, ColumnInfo


def test_exact_match(source_schema, target_schema_exact_match):
    field_map = match_fields(source_schema, target_schema_exact_match)

    assert field_map == {
        "id": "id",
        "first_name": "first_name",
        "last_name": "last_name",
        "amount": "amount",
    }


def test_case_insensitive_exact_match():
    source = SchemaInfo(table_name="s", columns=[ColumnInfo(name="ID", dtype="int64")])
    target = SchemaInfo(table_name="t", columns=[ColumnInfo(name="id", dtype="int64")])

    field_map = match_fields(source, target)

    assert field_map == {"ID": "id"}


def test_fuzzy_match_for_renamed_columns(source_schema, target_schema_renamed):
    field_map = match_fields(source_schema, target_schema_renamed, fuzzy_threshold=0.7)

    # id -> ID should match via case-insensitive exact match
    assert field_map["id"] == "ID"
    # first_name -> firstname should match via fuzzy (high similarity)
    assert field_map["first_name"] == "firstname"
    assert field_map["last_name"] == "lastname"
    assert field_map["amount"] == "amount"


def test_no_match_below_threshold():
    source = SchemaInfo(table_name="s", columns=[ColumnInfo(name="customer_identifier", dtype="int64")])
    target = SchemaInfo(table_name="t", columns=[ColumnInfo(name="x", dtype="int64")])

    field_map = match_fields(source, target, fuzzy_threshold=0.9)

    # Completely dissimilar names should not be matched
    assert "customer_identifier" not in field_map


def test_unmatched_source_column_excluded():
    source = SchemaInfo(
        table_name="s",
        columns=[ColumnInfo(name="id", dtype="int64"), ColumnInfo(name="extra_field", dtype="object")],
    )
    target = SchemaInfo(table_name="t", columns=[ColumnInfo(name="id", dtype="int64")])

    field_map = match_fields(source, target)

    assert "id" in field_map
    assert "extra_field" not in field_map


def test_each_target_column_used_at_most_once():
    """Two similarly-named source columns shouldn't both map to the same target column."""
    source = SchemaInfo(
        table_name="s",
        columns=[ColumnInfo(name="amount", dtype="float64"), ColumnInfo(name="amout", dtype="float64")],
    )
    target = SchemaInfo(table_name="t", columns=[ColumnInfo(name="amount", dtype="float64")])

    field_map = match_fields(source, target, fuzzy_threshold=0.7)

    mapped_targets = list(field_map.values())
    assert len(mapped_targets) == len(set(mapped_targets))  # no duplicates