# MP3 Movie API
This project was completed for my DS3500 course, Advanced Programming with Data, in November 2026. It is an extension of MP2, a Representational State Transfer (REST) Application Programming Interface (API). MP3 adds persistent storage and caching using an SQLite table with completely revamped endpoints. Clients can use it by sending HTTP requests to the application and will receive responses formatted with JSON. Caching is used to simplify repeated GET API calls with a an expiration time of 90 seconds, invalidating a cache with new uploads or changes to the data set.


This project is a FastAPI application that stores a movie collection in SQLite, cleans it with a data pipeline from an earlier project, and caches repeated retrievals. Uploading a CSV through `POST /upload` validates its columns and replaces the stored collection in the `movies` table, which `src/database.py` creates and `src/storage.py` (`MovieStorage`) reads and writes with SQL. `GET /movies` returns up to `limit` movies plus the total count. `GET /movies/search` uses a SQL `WHERE`/`ORDER BY` query to filter movies by minimum rating. `POST /movies/process` loads the stored movies and runs the validation and cleaning functions in `data_pipeline/` (duplicate removal, missing-value handling and IQR outlier removal), then saves the cleaned rows back to the database. `src/cache.py` (`MovieCache`) uses FakeRedis to cache `GET /movies` responses for 90 seconds per `limit`, so a repeated request skips the database. After every successful upload or processing step, the cache is cleared so outdated results are never returned. Request and response shapes are defined as Pydantic models in `src/models.py`, while `src/utils.py` and `src/middleware.py` set up logging and log each request.

## Setup

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

## Start the API

```bash
python -m uvicorn main:app --reload
```

Then open http://127.0.0.1:8000/docs.

## Run the Tests

```bash
python -m pytest tests -v
```

## Sample Processing Request

After uploading `fixtures/sample_movies.csv`, send `POST /movies/process` with:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

Expected response:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```

A following `GET /movies?limit=100` returns 16 movies with `total_rows: 16`.
