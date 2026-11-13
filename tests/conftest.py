from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, storage
import main
from src import MovieCache, MovieStorage


@pytest.fixture
def test_storage(tmp_path):
    return MovieStorage(tmp_path / "test_movies.db")

@pytest.fixture
def client(test_storage, monkeypatch):
    monkeypatch.setattr(main, "storage", test_storage)
    monkeypatch.setattr(main, "cache", MovieCache())
    with TestClient(main.app) as test_client:
        yield test_client

@pytest.fixture
def sample_csv_bytes():
    return (Path("fixtures") / "sample_movies.csv").read_bytes()

@pytest.fixture
def uploaded_movies(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={"file": ("sample_movies.csv", sample_csv_bytes, "text/csv")}
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def uploaded_dataset_id(client, sample_csv_bytes):
    response = client.post(
        "/upload",
        files={
            "file": (
                "sample_data.csv",
                sample_csv_bytes,
                "text/csv"
            )
        }
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture
def processing_body():
    return {
        "validation": {
            "required_columns": ["student_id", "score"],
            "numeric_columns": ["score"]
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {
                "enabled": True,
                "axis": "rows"
            },
            "outliers": {
                "enabled": False,
                "columns": [],
                "method": "iqr",
                "threshold": 1.5
            }
        }
    }