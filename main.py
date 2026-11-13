import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import DatasetInfo, HealthResponse, ValidationSettings, MissingSettings, OutlierSettings
from src import ProcessingSettings, ProcessConfig, ProcessingReport, HealthResponse, setup_logging, log_requests
from src import MovieStorage, MovieUploadInfo, MovieDataResponse, MovieProcessingReport
from src import MovieCache
from src.storage import MOVIE_COLUMNS
from data_pipeline import create_cleaning_report, process_data, validate_dataframe

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()
cache = MovieCache()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    # TODO 1: Keep MP2's .csv check, await file.read(), and CSV parsing.
    # Raise HTTPException with status 400 for an unsupported extension or an expected parsing failure.
    if Path(file.filename or "").suffix.lower() != ".csv" or not file.filename:
        logger.warning(f"Bad file type: {Path(file.filename or "").suffix.lower()}")
        raise HTTPException(status_code=400, detail="wrong filename extension/ file type")
    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except(pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(f"Cannot read CSV: {error}")
        raise HTTPException(status_code=400, detail="Cannot read the uploaded csv")

    # TODO 2: Quick validation before saving:
    # Require exactly MOVIE_COLUMNS
    # Require at least one data row (hint: Use if df.empty: to check for an empty DataFrame).
    # Raise HTTPException with status 400 if these checks fail.
    # Reorder the columns to match MOVIE_COLUMNS.

    for col in MOVIE_COLUMNS:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"{col} missing from uploaded file")
    if len(df.columns) != 4:
        raise HTTPException(status_code=400, detail="Too many columns in uploaded file (need 4)")
    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded file has no rows")
    df = df[MOVIE_COLUMNS]

    # TODO 3: Call storage.save(df) to replace the current collection.
    # Log the filename and saved row count at INFO.
    # Return filename, rows, columns, and column_names for this upload.
    storage.save(df)
    cache.invalidate()
    logger.debug(f"File saved with filename {file.filename}, and {len(df)} rows")
    return MovieUploadInfo(filename=file.filename, rows=len(df), columns=len(df.columns), column_names=df.columns.to_list())

@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    # TODO 1: Look up the response using cache.get(limit).
    # If it is not None, log the cache hit at INFO and return it.

    # Keep Part 1's SQL retrieval, total count, and response construction here.

    # TODO 2: Before the existing return, cache the complete response
    # using cache.set(limit, response).
    # Keep the existing row-count log and return.
    cached = cache.get(limit)
    if cached is not None:
        logger.info(f"Cache hit! Listed movies: rows={len(cached["data"])}")
        return cached
    data = storage.select_columns(MOVIE_COLUMNS, limit = limit)
    stored_movies = storage.count_movies()
    logger.info(f"{len(data)} rows retrieved")
    response = MovieDataResponse(data=data, total_rows=stored_movies)
    cache.set(limit=limit, response=response.model_dump())
    return response


@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    # TODO: Call storage.query_movies(columns, min_rating, limit).
    # Catch ValueError and raise HTTPException with status 400.
    # Return id plus the selected fields, or [] if there are no matches.
    # Log the selected columns and returned row count at INFO.
    try:
        data = storage.query_movies(columns=columns, min_rating=min_rating, limit=limit)
    except(ValueError):
        raise HTTPException(status_code=400, detail="Query failed")
    logger.info(f"{columns} selected with {len(data)} rows")
    return data


@app.post(
    "/movies/process",
    response_model=MovieProcessingReport
)
def process_dataset(config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # TODO 1: Retrieve data using storage.get().
    # Raise HTTPException with status 400 if empty.

    # TODO 2: Reuse MP2's configuration, validation, processing,
    # cleaning report, logging, and ValueError handling.

    # TODO 3: Save the processed DataFrame using storage.save().
    # Return validation_rows_removed and cleaning_report without a dataset ID.

    # TODO: retrieve, validate, process, report, update, and return.
    
    # retrieve
    data = storage.get()
    if data.empty:
        raise HTTPException(status_code=400, detail="Dataset empty")

    # validation prep
    validation_settings = config.validation.model_dump()
    required_columns = validation_settings["required_columns"]
    numeric_columns = validation_settings["numeric_columns"]
    for column in numeric_columns:
        if column not in data:
            logger.error(f"Necessary numeric column: {column} not found DataFrame")
            raise HTTPException(status_code=400, detail=f"{column} not found in DataFrame")
    data_original = data.copy()

    # validate data
    try:
        data = validate_dataframe(data, required_columns=required_columns, numeric_columns=numeric_columns)
    except(ValueError) as error:
        logger.error(f"ValueError raised by validate_dataframe: missing column required by required_columns")
        raise HTTPException(status_code=400, detail=str(error))
    validate_rows_removed = len(data_original)-len(data)
    logger.info(f"DataFrame validated. {validate_rows_removed} rows removed.")
    
    # process
    try:
        data_processed = process_data(data, config=config.model_dump())
    except(ValueError) as error:
            logger.error(f"ValueError raised by process_data")
            raise HTTPException(status_code=400, detail=str(error))
    processed_rows_removed = len(data) - len(data_processed)
    cleaning_report = create_cleaning_report(data, data_processed)
    
    # update storage and return MovieProcessingReport
    storage.save(df=data_processed)
    cache.invalidate()
    logger.info(f"DataFrame processed . {validate_rows_removed} rows removed during validation and {processed_rows_removed} rows removed during processing.")
    return MovieProcessingReport(validation_rows_removed=len(data)-len(data), cleaning_report=cleaning_report)
