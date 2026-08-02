import pytest
import pandas as pd
from sqlalchemy import create_engine, text

from validator.connectors.sql_connector import SqlConnector


@pytest.fixture
def sqlite_db(tmp_path):
    """
    Creates a temporary SQLite database file with a sample table.
    SQLite is used here purely as a lightweight stand-in for exercising
    the same SQLAlchemy code path used by Postgres/MySQL — no real
    database server required for automated tests.
    """
    db_path = tmp_path / "test.db"
    connection_string = f"sqlite:///{db_path}"

    engine = create_engine(connection_string)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                amount REAL
            )
        """))
        conn.execute(text("INSERT INTO customers (id, name, amount) VALUES (1, 'Alice', 100.5)"))
        conn.execute(text("INSERT INTO customers (id, name, amount) VALUES (2, 'Bob', 200.75)"))

    return connection_string


def test_connection_succeeds(sqlite_db):
    connector = SqlConnector(sqlite_db)
    assert connector.test_connection() is True


def test_connection_fails_for_bad_string():
    # Malformed connection string / unreachable driver
    connector = SqlConnector("postgresql://baduser:badpass@localhost:1/nonexistent_db")
    assert connector.test_connection() is False


def test_get_schema_returns_correct_columns(sqlite_db):
    connector = SqlConnector(sqlite_db)
    schema = connector.get_schema("customers")

    column_names = [c.name for c in schema.columns]
    assert "id" in column_names
    assert "name" in column_names
    assert "amount" in column_names


def test_read_data_returns_all_rows(sqlite_db):
    connector = SqlConnector(sqlite_db)
    df = connector.read_data("customers")

    assert len(df) == 2
    assert set(df.columns) == {"id", "name", "amount"}
    assert df.iloc[0]["name"] == "Alice"


def test_read_data_with_specific_columns(sqlite_db):
    connector = SqlConnector(sqlite_db)
    df = connector.read_data("customers", columns=["id", "name"])

    assert list(df.columns) == ["id", "name"]
    assert "amount" not in df.columns


def test_read_data_empty_table(sqlite_db):
    engine = create_engine(sqlite_db)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE empty_table (id INTEGER, val TEXT)"))

    connector = SqlConnector(sqlite_db)
    df = connector.read_data("empty_table")

    assert len(df) == 0
    assert list(df.columns) == ["id", "val"]