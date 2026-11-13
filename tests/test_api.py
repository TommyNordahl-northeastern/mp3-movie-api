import pytest

from src import MovieStorage
from src.storage import MOVIE_COLUMNS
import main
import pandas as pd

def test_movies_persist(client, test_storage, uploaded_movies):
    # TODO: create another MovieStorage pointing to test_storage.db_path.
    # Use that object to get the movies and count them.
    # Check 20 rows, all four DataFrame columns, and the original title order.
    # Compare IDs from that object's select_columns() with GET /movies?limit=100.
    # Both should return IDs 1 through 20 in row order.
    storage = MovieStorage(test_storage.db_path)
    movies = storage.get()
    count = storage.count_movies()
    assert count == 20
    assert MOVIE_COLUMNS == movies.columns.to_list()
    expected_titles = pd.read_csv("fixtures/sample_movies.csv")["title"].to_list()
    assert movies["title"].to_list() == expected_titles

    db_ids = [row["id"] for row in storage.select_columns(MOVIE_COLUMNS, limit=100)]

    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    api_ids = [row["id"] for row in response.json()["data"]]
    assert db_ids == api_ids


def test_cache_and_processing(client, uploaded_movies, processing_body):
    # TODO 1: GET /movies with limits 100 and 1.
    # Check 200 and that main.cache.get(limit) equals each response body.

    # TODO 2: repeat limit=100 and check the same response.

    # TODO 3: POST /movies/process using json=processing_body.
    # Check 200, zero validation removals, and the 20 -> 16 cleaning report.
    # Confirm both old cache entries are None.

    # TODO 4: retrieve again; check total_rows=16 and titles Movie A through Movie P, in order.
    # Check IDs 1 through 16 in the retrieved records.
    # Check that the new response is cached.
    pass


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    # TODO 1: GET /movies with limit=100 to populate the cache.
    # Assert 200 and keep the response for comparison.

    # TODO 2: Use monkeypatch to replace main.storage.select_columns()
    # and main.storage.count_movies() with a function that fails the test
    # if either method is called. 

    # TODO 3: Repeat the same GET request.
    # Assert 200 and the same response body as the first request.
    pass




# def test_process_and_retrieve(
#     client, uploaded_dataset_id, processing_body
# ):
#     # TODO 1: Send a POST request to
#     # /datasets/{uploaded_dataset_id}/process
#     # using json=processing_body.
#     # Assert status 200, one validation removal,
#     # and a cleaning report showing 5 → 3 rows.

#     response = client.post(f"/datasets/{uploaded_dataset_id}/process", json=processing_body)
#     assert response.status_code == 200

#     data = response.json()
#     cleaning_report = data["cleaning_report"]
#     assert data["validation_rows_removed"] == 1
#     assert cleaning_report["rows_before"] == 5
#     assert cleaning_report["rows_after"] == 3

#     # TODO 2: GET /datasets/{uploaded_dataset_id}.
#     # Assert status 200 and total_rows == 3.
#     # Check that the returned records contain student IDs
#     # 1, 2, and 5 with scores 80, 90, and 85.
    
#     response2 = client.get(f"/datasets/{uploaded_dataset_id}")
#     assert response2.status_code == 200
#     data = response2.json()
#     assert data["total_rows"] == 3
#     ids = [row["student_id"] for row in data["data"]]
#     scores = [row["score"] for row in data["data"]]
#     x = [1,2,5]
#     y = [80, 90, 85]
#     for z in x:
#         assert z in ids
#     for z in y:
#         assert z in scores


# def test_retrieve_missing_dataset(client):
#     # TODO: Retrieve a dataset ID that does not exist.
#     # Assert status 404.
#     response = client.get(f"/datasets/{999999}")
#     assert response.status_code == 404
