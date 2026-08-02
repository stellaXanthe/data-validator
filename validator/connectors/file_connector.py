import pandas as pd
from pathlib import Path

from .base import BaseConnector, SchemaInfo, ColumnInfo


class FileConnector(BaseConnector):
    """Connector for CSV / Parquet / JSON files."""

    def get_schema(self, table_or_path: str) -> SchemaInfo:
        df = self._read(table_or_path, nrows=1000)  # sample for type inference
        return SchemaInfo(
            table_name=table_or_path,
            columns=[ColumnInfo(name=col, dtype=str(dtype)) for col, dtype in df.dtypes.items()],
        )

    def read_data(self, table_or_path: str, columns: list[str] | None = None) -> pd.DataFrame:
        df = self._read(table_or_path)
        if columns:
            df = df[columns]
        return df

    def _read(self, path: str, nrows: int | None = None) -> pd.DataFrame:
        suffix = Path(path).suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path, nrows=nrows)
        elif suffix == ".parquet":
            df = pd.read_parquet(path)
            return df.head(nrows) if nrows else df
        elif suffix == ".json":
            df = pd.read_json(path)
            return df.head(nrows) if nrows else df
        else:
            raise ValueError(f"Unsupported file type: {suffix}")