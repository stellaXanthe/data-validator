import logging
import pandas as pd
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_validate_does_not_write_any_files(tmp_path, monkeypatch):
    """
    Confirms that running a validation does not create any new files
    on disk beyond the source/target files the user explicitly provided.
    """
    source_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"], "amount": [10.0, 20.0]})
    target_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"], "amount": [10.0, 999.0]})

    source_path = tmp_path / "source.csv"
    target_path = tmp_path / "target.csv"
    source_df.to_csv(source_path, index=False)
    target_df.to_csv(target_path, index=False)

    files_before = set(tmp_path.iterdir())

    response = client.post("/validate", json={
        "source": {"type": "file", "path": str(source_path)},
        "target": {"type": "file", "path": str(target_path)},
        "key_columns": ["id"],
    })

    assert response.status_code == 200

    files_after = set(tmp_path.iterdir())
    assert files_before == files_after, "Validation should not create any new files on disk"


def test_error_messages_never_leak_connection_strings():
    """
    Confirms that a failed SQL connection does not echo the connection
    string (which may contain a password) back in the API response.
    """
    secret_password = "SuperSecretPassword123"
    bad_connection_string = f"postgresql://baduser:{secret_password}@localhost:1/nonexistent"

    response = client.post("/validate", json={
        "source": {"type": "sql", "connection_string": bad_connection_string, "table": "customers"},
        "target": {"type": "sql", "connection_string": bad_connection_string, "table": "customers"},
        "key_columns": ["id"],
    })

    assert response.status_code == 500
    response_text = response.text
    assert secret_password not in response_text, "Password must never appear in API responses"


def test_connection_test_error_does_not_leak_credentials():
    secret_token = "dapi_secret_token_abc123"

    response = client.post("/connections/test", json={
        "connection": {
            "type": "databricks",
            "server_hostname": "fake-host.cloud.databricks.com",
            "http_path": "/sql/1.0/warehouses/fake",
            "access_token": secret_token,
            "table": "main.default.customers",
        }
    })

    response_text = response.text
    assert secret_token not in response_text, "Access token must never appear in API responses"


def test_logging_never_includes_raw_credentials(caplog):
    """
    Confirms that server-side logs capture only connection type metadata,
    never the actual connection string or access token.
    """
    secret_password = "AnotherSecretPassword456"
    bad_connection_string = f"postgresql://baduser:{secret_password}@localhost:1/nonexistent"

    with caplog.at_level(logging.INFO):
        client.post("/validate", json={
            "source": {"type": "sql", "connection_string": bad_connection_string, "table": "customers"},
            "target": {"type": "sql", "connection_string": bad_connection_string, "table": "customers"},
            "key_columns": ["id"],
        })

    all_log_text = " ".join(record.message for record in caplog.records)
    assert secret_password not in all_log_text, "Password must never appear in server logs"


def test_logging_never_includes_actual_data_values(tmp_path, caplog):
    """
    Confirms that server-side logs capture only row counts/summary stats,
    never the actual data values being compared.
    """
    sensitive_value = "PatientSSN-987-65-4321"
    source_df = pd.DataFrame({"id": [1], "note": [sensitive_value]})
    target_df = pd.DataFrame({"id": [1], "note": [sensitive_value]})

    source_path = tmp_path / "source.csv"
    target_path = tmp_path / "target.csv"
    source_df.to_csv(source_path, index=False)
    target_df.to_csv(target_path, index=False)

    with caplog.at_level(logging.INFO):
        client.post("/validate", json={
            "source": {"type": "file", "path": str(source_path)},
            "target": {"type": "file", "path": str(target_path)},
            "key_columns": ["id"],
        })

    all_log_text = " ".join(record.message for record in caplog.records)
    assert sensitive_value not in all_log_text, "Actual data values must never appear in server logs"