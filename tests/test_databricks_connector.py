from unittest.mock import MagicMock, patch
import pandas as pd
import pyarrow as pa

from validator.connectors.databricks_connector import DatabricksConnector


def make_connector():
    return DatabricksConnector(
        server_hostname="test-workspace.cloud.databricks.com",
        http_path="/sql/1.0/warehouses/abc123",
        access_token="fake-token",
    )


def _mock_cursor_context(mock_cursor):
    """Helper to build a mock connection whose cursor() returns mock_cursor as a context manager."""
    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__enter__.return_value = mock_cursor
    mock_cursor_cm.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = False
    mock_conn.cursor.return_value = mock_cursor_cm

    return mock_conn


@patch("validator.connectors.databricks_connector.databricks_sql.connect")
def test_connection_succeeds(mock_connect):
    mock_cursor = MagicMock()
    mock_connect.return_value = _mock_cursor_context(mock_cursor)

    connector = make_connector()
    assert connector.test_connection() is True
    mock_cursor.execute.assert_called_once_with("SELECT 1")


@patch("validator.connectors.databricks_connector.databricks_sql.connect")
def test_connection_fails_gracefully(mock_connect):
    mock_connect.side_effect = Exception("connection refused")

    connector = make_connector()
    assert connector.test_connection() is False


@patch("validator.connectors.databricks_connector.databricks_sql.connect")
def test_get_schema_parses_describe_table_output(mock_connect):
    mock_cursor = MagicMock()
    # Simulate typical `DESCRIBE TABLE` output: (col_name, data_type, comment)
    mock_cursor.fetchall.return_value = [
        ("id", "bigint", None),
        ("name", "string", None),
        ("amount", "double", None),
        ("", "", ""),  # blank separator row Databricks sometimes includes
        ("# Partition Information", "", ""),  # partition metadata row to be filtered out
    ]
    mock_connect.return_value = _mock_cursor_context(mock_cursor)

    connector = make_connector()
    schema = connector.get_schema("main.default.customers")

    column_names = [c.name for c in schema.columns]
    assert "id" in column_names
    assert "name" in column_names
    assert "amount" in column_names
    assert "# Partition Information" not in column_names
    mock_cursor.execute.assert_called_once_with("DESCRIBE TABLE main.default.customers")


@patch("validator.connectors.databricks_connector.databricks_sql.connect")
def test_read_data_converts_arrow_to_pandas(mock_connect):
    mock_cursor = MagicMock()

    # Build a real small Arrow table to simulate fetchall_arrow()'s return value
    arrow_table = pa.table({"id": [1, 2], "name": ["Alice", "Bob"]})
    mock_cursor.fetchall_arrow.return_value = arrow_table

    mock_connect.return_value = _mock_cursor_context(mock_cursor)

    connector = make_connector()
    df = connector.read_data("main.default.customers")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["id", "name"]
    assert df.iloc[0]["name"] == "Alice"


@patch("validator.connectors.databricks_connector.databricks_sql.connect")
def test_read_data_with_specific_columns_builds_correct_query(mock_connect):
    mock_cursor = MagicMock()
    arrow_table = pa.table({"id": [1], "name": ["Alice"]})
    mock_cursor.fetchall_arrow.return_value = arrow_table
    mock_connect.return_value = _mock_cursor_context(mock_cursor)

    connector = make_connector()
    connector.read_data("main.default.customers", columns=["id", "name"])

    mock_cursor.execute.assert_called_once_with("SELECT id, name FROM main.default.customers")