def sample_payload():
    return {
        "recipients": [
            {
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "course": "Python Backend Development",
                "completion_date": "2026-10-07"
            },
            {
                "name": "Bob Smith",
                "email": "bob@example.com",
                "course": "Python Backend Development",
                "completion_date": "2026-10-07"
            }
        ]
    }

def test_create_generation_job(client):
    response = client.post("/jobs", json=sample_payload())
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] > 0
    assert body["status"] == "pending"
    assert body["total"] == 2

def test_input_validation(client):
    payload = sample_payload()
    payload["recipients"][0]["email"] = "not-an-email"
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422

def test_certificate_generation(client):
    response = client.post("/jobs", json=sample_payload())
    assert response.status_code == 202

    job_id = response.json()["job_id"]
    status = client.get(f"/jobs/{job_id}").json()

    assert status["status"] == "completed"
    assert status["completed"] == 2
    assert status["failed"] == 0
    assert all(r["certificate_url"] for r in status["results"])

def test_job_status_and_progress(client):
    response = client.post("/jobs", json=sample_payload())
    job_id = response.json()["job_id"]

    status = client.get(f"/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["progress_percent"] == 100.0

def test_individual_failure_does_not_stop_other_certificates(client):
    payload = {
        "recipients": [
            {
                "name": "FAIL_TEST",
                "email": "bad@example.com",
                "course": "Testing",
                "completion_date": "2026-10-07"
            },
            {
                "name": "Valid Person",
                "email": "valid@example.com",
                "course": "Testing",
                "completion_date": "2026-10-07"
            }
        ]
    }

    response = client.post("/jobs", json=payload)
    job_id = response.json()["job_id"]

    body = client.get(f"/jobs/{job_id}").json()
    assert body["status"] == "partial"
    assert body["completed"] == 1
    assert body["failed"] == 1

def test_retrieve_generated_certificate(client):
    response = client.post("/jobs", json=sample_payload())
    job_id = response.json()["job_id"]
    body = client.get(f"/jobs/{job_id}").json()

    recipient_id = next(
        r["id"] for r in body["results"] if r["status"] == "completed"
    )
    certificate = client.get(f"/certificates/{recipient_id}")

    assert certificate.status_code == 200
    assert certificate.headers["content-type"] == "application/pdf"
    assert certificate.content.startswith(b"%PDF")
