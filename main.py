import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import DatasetStorage, DatasetInfo, HealthResponse, ValidationSettings, MissingSettings, OutlierSettings
from src import ProcessingSettings, ProcessConfig, ProcessingReport, HealthResponse, setup_logging, log_requests
from data_pipeline import create_cleaning_report, process_data, validate_dataframe

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = DatasetStorage()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}

@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    if Path(file.filename or "").suffix.lower() != ".csv" or not file.filename:
        logger.warning(f"Bad file type: {Path(file.filename or "").suffix.lower()}")
        raise HTTPException(status_code=400, detail="wrong filename extension/ file type")
    contents = await file.read()

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except(pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(f"Cannot read CSV: {error}")
        raise HTTPException(status_code=400, detail="Cannot read the uploaded csv")

    # Save the DataFrame and return its metadata as DatasetInfo
    storage.save(df, filename=file.filename)
    logger.info(f"Dataset uploaded with ID: {storage._counter}, filename: {file.filename}, and {len(df)} rows.")
    return DatasetInfo(id=storage._counter, filename=file.filename, rows=len(df),
                       columns = len(df.columns), column_names= df.columns.to_list())

@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    if dataset_id not in storage._store:
        logger.warning(f"ID {dataset_id} not found in storage.")
        raise HTTPException(status_code=404, detail="Dataset not found")

    df = storage._store[dataset_id][0].copy()
    records = json.loads(df.head(limit).to_json(orient="records"))
    dataset_values = {"id": dataset_id, "data": records, "total_rows": len(df)}
    logger.info(f"Dataset located with ID {dataset_id} and row count {len(df)}")
    return dataset_values

@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # TODO: retrieve, validate, process, report, update, and return.
    
    # retrieve
    if dataset_id not in storage._store:
        logger.warning(f"ID {dataset_id} not found in storage.")
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = storage._store[dataset_id][0].copy()

    # prepare to validate
    validation_settings = config.validation.model_dump()
    required_columns = validation_settings["required_columns"]
    numeric_columns = validation_settings["numeric_columns"]
    for column in numeric_columns:
        if column not in df:
            logger.error(f"Necessary numeric column: {column} not found DataFrame")
            raise HTTPException(status_code=400, detail=f"{column} not found in DataFrame")
    df_original = df.copy()

    # validate data
    try:
        df = validate_dataframe(df, required_columns=required_columns, numeric_columns=numeric_columns)
    except(ValueError) as error:
        logger.error(f"ValueError raised by validate_dataframe: missing column required by required_columns")
        raise HTTPException(status_code=400, detail=str(error))
    validate_rows_removed = len(df_original)-len(df)
    logger.info(f"DataFrame validated. {validate_rows_removed} rows removed.")
    
    # process
    try:
        df_processed = process_data(df, config=config.model_dump())
    except(ValueError) as error:
            logger.error(f"ValueError raised by process_data")
            raise HTTPException(status_code=400, detail=str(error))
    processed_rows_removed = len(df) - len(df_processed)
    cleaning_report = create_cleaning_report(df, df_processed)
    
    # update storage and return ProcessingReport
    storage.update(dataset_id=dataset_id, df=df_processed)
    logger.info(f"DataFrame processed with ID {dataset_id}. {validate_rows_removed} rows removed during validation and {processed_rows_removed} rows removed during processing.")
    return ProcessingReport(id=dataset_id, validation_rows_removed=len(df_original)-len(df), cleaning_report=cleaning_report)
