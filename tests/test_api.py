def test_upload_csv(client, sample_csv_bytes):
    # TODO: Upload the sample CSV to POST /upload.
    # Assert status 200, six rows, two columns,
    # and a positive integer dataset ID..
    response = client.post(
        "/upload",
        files={"file": ("sample_data.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["rows"] == 6
    assert data["columns"] == 2
    assert data["id"] > 0


def test_process_and_retrieve(
    client, uploaded_dataset_id, processing_body
):
    # TODO 1: Send a POST request to
    # /datasets/{uploaded_dataset_id}/process
    # using json=processing_body.
    # Assert status 200, one validation removal,
    # and a cleaning report showing 5 → 3 rows.

    response = client.post(f"/datasets/{uploaded_dataset_id}/process", json=processing_body)
    assert response.status_code == 200

    data = response.json()
    cleaning_report = data["cleaning_report"]
    assert data["validation_rows_removed"] == 1
    assert cleaning_report["rows_before"] == 5
    assert cleaning_report["rows_after"] == 3

    # TODO 2: GET /datasets/{uploaded_dataset_id}.
    # Assert status 200 and total_rows == 3.
    # Check that the returned records contain student IDs
    # 1, 2, and 5 with scores 80, 90, and 85.
    
    response2 = client.get(f"/datasets/{uploaded_dataset_id}")
    assert response2.status_code == 200
    data = response2.json()
    assert data["total_rows"] == 3
    ids = [row["student_id"] for row in data["data"]]
    scores = [row["score"] for row in data["data"]]
    x = [1,2,5]
    y = [80, 90, 85]
    for z in x:
        assert z in ids
    for z in y:
        assert z in scores


def test_retrieve_missing_dataset(client):
    # TODO: Retrieve a dataset ID that does not exist.
    # Assert status 404.
    response = client.get(f"/datasets/{999999}")
    assert response.status_code == 404
