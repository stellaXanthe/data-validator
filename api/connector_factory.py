from validator.connectors.base import BaseConnector
from validator.connectors.file_connector import FileConnector
from validator.connectors.sql_connector import SqlConnector
from validator.connectors.databricks_connector import DatabricksConnector

from .models import ConnectionConfig, FileConnectionConfig, SqlConnectionConfig, DatabricksConnectionConfig


def build_connector(config: ConnectionConfig) -> tuple[BaseConnector, str]:
    """
    Returns (connector_instance, table_or_path) — the second value is what
    gets passed to get_schema()/read_data() on the connector.
    """
    if isinstance(config, FileConnectionConfig):
        return FileConnector(), config.path

    if isinstance(config, SqlConnectionConfig):
        return SqlConnector(config.connection_string), config.table

    if isinstance(config, DatabricksConnectionConfig):
        return DatabricksConnector(
            server_hostname=config.server_hostname,
            http_path=config.http_path,
            access_token=config.access_token,
        ), config.table

    raise ValueError(f"Unsupported connector type: {config}")