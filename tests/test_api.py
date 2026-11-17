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
    assert db_ids == list(range(1,21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    # TODO 1: GET /movies with limits 100 and 1.
    # Check 200 and that main.cache.get(limit) equals each response body.
    response1 = client.get("/movies", params={"limit": 100})
    assert response1.status_code == 200
    assert main.cache.get(100) == response1.json()

    response2 = client.get("/movies", params={"limit": 1})
    assert response2.status_code == 200
    assert main.cache.get(1) == response2.json()


    # TODO 2: repeat limit=100 and check the same response.

    response3 = client.get("/movies", params={"limit": 100})
    assert response3.status_code == 200
    assert response3.json() == response1.json()

    # TODO 3: POST /movies/process using json=processing_body.
    # Check 200, zero validation removals, and the 20 -> 16 cleaning report.
    # Confirm both old cache entries are None.

    post = client.post("/movies/process", json=processing_body)
    assert post.status_code == 200
    report = post.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 16
    assert report["cleaning_report"]["rows_removed"] == 4
    assert main.cache.get(100) == None
    assert main.cache.get(1) == None

    # TODO 4: retrieve again; check total_rows=16 and titles Movie A through Movie P, in order.
    # Check IDs 1 through 16 in the retrieved records.
    # Check that the new response is cached.

    response4 = client.get("/movies", params={"limit": 100})
    assert response4.status_code == 200
    body = response4.json()
    assert body["total_rows"] == 16

    actual_titles = []
    expected_titles = [f"Movie {letter}" for letter in "ABCDEFGHIJKLMNOP"]
    for movie in body["data"]:
        actual_titles.append(movie["title"])

    assert actual_titles == expected_titles

    actual_ids = []
    expected_ids = [val + 1 for val in range(16)]
    for movie in body["data"]:
        actual_ids.append(movie["id"])

    assert actual_ids == expected_ids
    assert main.cache.get(100) == body

    
def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    # TODO 1: GET /movies with limit=100 to populate the cache.
    # Assert 200 and keep the response for comparison.

    # TODO 2: Use monkeypatch to replace main.storage.select_columns()
    # and main.storage.count_movies() with a function that fails the test
    # if either method is called. 

    # TODO 3: Repeat the same GET request.
    # Assert 200 and the same response body as the first request.
    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200

    def fail_if_called(*args, **kwargs):
        pytest.fail("A cache hit should not query the database")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    response2 = client.get("/movies", params={"limit": 100})
    assert response2.status_code == 200
    assert response.json() == response2.json()
