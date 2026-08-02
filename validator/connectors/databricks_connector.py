from databricks import sql as databricks_sql
import pandas as pd

from .base import BaseConnector, SchemaInfo, ColumnInfo


class DatabricksConnector(BaseConnector):
    """
    Connector for Databricks SQL Warehouses (works for Unity Catalog tables,
    Delta tables, etc. accessible via a SQL endpoint).

    Requires a SQL Warehouse (not a general-purpose cluster) for the
    databricks-sql-connector to work efficiently.
    """

    def __init__(self, server_hostname: str, http_path: str, access_token: str):
        self.server_hostname = server_hostname
        self.http_path = http_path
        self.access_token = access_token

    def _connect(self):
        return databricks_sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token,
        )

    def test_connection(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def get_schema(self, table_or_path: str) -> SchemaInfo:
        """
        table_or_path should be a fully qualified table name, e.g.
        'catalog.schema.table_name'
        """
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"DESCRIBE TABLE {table_or_path}")
                rows = cursor.fetchall()

        columns = [
            ColumnInfo(name=row[0], dtype=row[1])
            for row in rows
            if row[0] and not row[0].startswith("#")  # skip partition/comment separator rows
        ]

        return SchemaInfo(table_name=table_or_path, columns=columns)

    def read_data(self, table_or_path: str, columns: list[str] | None = None) -> pd.DataFrame:
        col_clause = ", ".join(columns) if columns else "*"
        query = f"SELECT {col_clause} FROM {table_or_path}"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall_arrow()

        return result.to_pandas()