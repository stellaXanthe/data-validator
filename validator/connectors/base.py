from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import pandas as pd


@dataclass
class ColumnInfo:
    name: str
    dtype: str


@dataclass
class SchemaInfo:
    table_name: str
    columns: list[ColumnInfo]


class BaseConnector(ABC):
    """All source/target connectors implement this interface."""

    @abstractmethod
    def get_schema(self, table_or_path: str) -> SchemaInfo:
        """Return the schema (column names + types) for a table/file."""
        raise NotImplementedError

    @abstractmethod
    def read_data(self, table_or_path: str, columns: list[str] | None = None) -> pd.DataFrame:
        """Return the actual data as a pandas DataFrame."""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """Optional: override to verify connectivity before running a job."""
        return True