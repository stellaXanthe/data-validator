import pandas as pd
from validator.comparator import compare_data


def make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_identical_data_all_matched():
    source_df = make_df([
        {"id": 1, "name": "Alice", "amount": 100.0},
        {"id": 2, "name": "Bob", "amount": 200.0},
    ])
    target_df = source_df.copy()
    field_map = {"id": "id", "name": "name", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"])

    assert result.matched_rows == 2
    assert result.missing_in_target == 0
    assert result.missing_in_source == 0
    assert result.value_mismatches == 0
    assert result.duplicate_keys_source == 0
    assert result.duplicate_keys_target == 0


def test_detects_missing_in_target():
    source_df = make_df([
        {"id": 1, "name": "Alice", "amount": 100.0},
        {"id": 2, "name": "Bob", "amount": 200.0},
    ])
    target_df = make_df([
        {"id": 1, "name": "Alice", "amount": 100.0},
    ])
    field_map = {"id": "id", "name": "name", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"])

    assert result.missing_in_target == 1
    assert result.matched_rows == 1


def test_detects_missing_in_source():
    source_df = make_df([{"id": 1, "name": "Alice", "amount": 100.0}])
    target_df = make_df([
        {"id": 1, "name": "Alice", "amount": 100.0},
        {"id": 2, "name": "Bob", "amount": 200.0},
    ])
    field_map = {"id": "id", "name": "name", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"])

    assert result.missing_in_source == 1


def test_detects_value_mismatch():
    source_df = make_df([{"id": 1, "name": "Alice", "amount": 100.0}])
    target_df = make_df([{"id": 1, "name": "Alice", "amount": 999.0}])  # different amount
    field_map = {"id": "id", "name": "name", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"])

    assert result.value_mismatches == 1
    assert result.matched_rows == 0
    assert len(result.mismatch_samples) == 1
    assert result.mismatch_samples[0]["key"] == 1


def test_detects_duplicates_in_source():
    source_df = make_df([
        {"id": 1, "name": "Alice", "amount": 100.0},
        {"id": 1, "name": "Alice", "amount": 100.0},  # duplicate id
        {"id": 2, "name": "Bob", "amount": 200.0},
    ])
    target_df = make_df([
        {"id": 1, "name": "Alice", "amount": 100.0},
        {"id": 2, "name": "Bob", "amount": 200.0},
    ])
    field_map = {"id": "id", "name": "name", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"])

    assert result.duplicate_keys_source == 1


def test_detects_duplicates_in_target():
    source_df = make_df([{"id": 1, "name": "Alice", "amount": 100.0}])
    target_df = make_df([
        {"id": 1, "name": "Alice", "amount": 100.0},
        {"id": 1, "name": "Alice", "amount": 100.0},
    ])
    field_map = {"id": "id", "name": "name", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"])

    assert result.duplicate_keys_target == 1


def test_renamed_target_columns_are_compared_correctly():
    """Target column names differ from source but field_map handles the translation."""
    source_df = make_df([{"id": 1, "customer_name": "Alice", "amount": 100.0}])
    target_df = make_df([{"id": 1, "cust_name": "Alice", "amount": 100.0}])
    field_map = {"id": "id", "customer_name": "cust_name", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"])

    assert result.matched_rows == 1
    assert result.value_mismatches == 0


def test_composite_key_columns():
    source_df = make_df([
        {"region": "North", "id": 1, "amount": 100.0},
        {"region": "South", "id": 1, "amount": 200.0},  # same id, different region
    ])
    target_df = source_df.copy()
    field_map = {"region": "region", "id": "id", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["region", "id"])

    assert result.matched_rows == 2
    assert result.missing_in_target == 0


def test_mismatch_sample_limit_respected():
    rows_source = [{"id": i, "amount": float(i)} for i in range(100)]
    rows_target = [{"id": i, "amount": float(i) + 1} for i in range(100)]  # all mismatched
    source_df = make_df(rows_source)
    target_df = make_df(rows_target)
    field_map = {"id": "id", "amount": "amount"}

    result = compare_data(source_df, target_df, field_map, key_columns=["id"], sample_limit=10)

    assert result.value_mismatches == 100
    assert len(result.mismatch_samples) == 10  # capped at sample_limit