from sqlalchemy import create_engine, inspect, text
import pandas as pd

from .base import BaseConnector, SchemaInfo, ColumnInfo


class SqlConnector(BaseConnector):
    """Generic SQL connector using SQLAlchemy — works with Postgres, MySQL, SQL Server, SQLite, etc."""

    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_schema(self, table_or_path: str) -> SchemaInfo:
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_or_path)
        return SchemaInfo(
            table_name=table_or_path,
            columns=[ColumnInfo(name=c["name"], dtype=str(c["type"])) for c in columns],
        )

    def read_data(self, table_or_path: str, columns: list[str] | None = None) -> pd.DataFrame:
        col_clause = ", ".join(columns) if columns else "*"
        query = f"SELECT {col_clause} FROM {table_or_path}"
        return pd.read_sql(query, self.engine)