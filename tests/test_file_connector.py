import pandas as pd
from validator.connectors.file_connector import FileConnector


def test_reads_csv_schema(tmp_path):
    csv_path = tmp_path / "test.csv"
    pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"], "amount": [10.5, 20.5]}).to_csv(csv_path, index=False)

    connector = FileConnector()
    schema = connector.get_schema(str(csv_path))

    column_names = [c.name for c in schema.columns]
    assert column_names == ["id", "name", "amount"]


def test_reads_csv_data(tmp_path):
    csv_path = tmp_path / "test.csv"
    pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]}).to_csv(csv_path, index=False)

    connector = FileConnector()
    df = connector.read_data(str(csv_path))

    assert len(df) == 2
    assert list(df.columns) == ["id", "name"]
    assert df.iloc[0]["name"] == "Alice"


def test_reads_specific_columns_only(tmp_path):
    csv_path = tmp_path / "test.csv"
    pd.DataFrame({"id": [1], "name": ["Alice"], "amount": [10.0]}).to_csv(csv_path, index=False)

    connector = FileConnector()
    df = connector.read_data(str(csv_path), columns=["id", "name"])

    assert list(df.columns) == ["id", "name"]


def test_reads_parquet(tmp_path):
    parquet_path = tmp_path / "test.parquet"
    pd.DataFrame({"id": [1, 2], "value": [1.1, 2.2]}).to_parquet(parquet_path)

    connector = FileConnector()
    df = connector.read_data(str(parquet_path))

    assert len(df) == 2


def test_reads_json(tmp_path):
    json_path = tmp_path / "test.json"
    pd.DataFrame({"id": [1, 2], "value": ["a", "b"]}).to_json(json_path, orient="records")

    connector = FileConnector()
    df = connector.read_data(str(json_path))

    assert len(df) == 2


def test_unsupported_file_type_raises(tmp_path):
    bad_path = tmp_path / "test.txt"
    bad_path.write_text("not a real data file")

    connector = FileConnector()
    try:
        connector.read_data(str(bad_path))
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert "Unsupported file type" in str(e)