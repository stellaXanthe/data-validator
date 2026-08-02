import pandas as pd
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_validate_identical_csvs(tmp_path):
    df = pd.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Carla"], "amount": [10.0, 20.0, 30.0]})
    source_path = tmp_path / "source.csv"
    target_path = tmp_path / "target.csv"
    df.to_csv(source_path, index=False)
    df.to_csv(target_path, index=False)

    response = client.post("/validate", json={
        "source": {"type": "file", "path": str(source_path)},
        "target": {"type": "file", "path": str(target_path)},
        "key_columns": ["id"],
    })

    assert response.status_code == 200
    data = response.json()
    assert data["matched_rows"] == 3
    assert data["value_mismatches"] == 0
    assert data["missing_in_target"] == 0


def test_validate_detects_mismatches(tmp_path):
    source_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"], "amount": [10.0, 20.0]})
    target_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"], "amount": [10.0, 999.0]})

    source_path = tmp_path / "source.csv"
    target_path = tmp_path / "target.csv"
    source_df.to_csv(source_path, index=False)
    target_df.to_csv(target_path, index=False)

    response = client.post("/validate", json={
        "source": {"type": "file", "path": str(source_path)},
        "target": {"type": "file", "path": str(target_path)},
        "key_columns": ["id"],
    })

    assert response.status_code == 200
    data = response.json()
    assert data["value_mismatches"] == 1
    assert len(data["mismatch_samples"]) == 1


def test_validate_rejects_invalid_key_column(tmp_path):
    df = pd.DataFrame({"id": [1], "name": ["Alice"]})
    source_path = tmp_path / "source.csv"
    target_path = tmp_path / "target.csv"
    df.to_csv(source_path, index=False)
    df.to_csv(target_path, index=False)

    response = client.post("/validate", json={
        "source": {"type": "file", "path": str(source_path)},
        "target": {"type": "file", "path": str(target_path)},
        "key_columns": ["nonexistent_column"],
    })

    assert response.status_code == 400


def test_validate_handles_missing_file_gracefully():
    response = client.post("/validate", json={
        "source": {"type": "file", "path": "does_not_exist.csv"},
        "target": {"type": "file", "path": "does_not_exist.csv"},
        "key_columns": ["id"],
    })

    assert response.status_code == 500


def test_connection_test_endpoint_for_file(tmp_path):
    df = pd.DataFrame({"id": [1]})
    file_path = tmp_path / "test.csv"
    df.to_csv(file_path, index=False)

    response = client.post("/connections/test", json={
        "connection": {"type": "file", "path": str(file_path)}
    })

    assert response.status_code == 200
    assert response.json()["success"] is True