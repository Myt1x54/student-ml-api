"""Automated tests for student-ml-api.

Run with:  pytest

Covers the four required cases:
  1. /health returns a healthy status
  2. /predict returns a correct prediction for valid input
  3. /predict rejects a request with missing input
  4. /predict rejects a request with invalid (non-numeric) input
"""

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health():
    """The health endpoint reports the service as healthy with version metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["application"] == "student-ml-api"
    # v1.1.0 reports the application and model versions separately.
    assert data["application_version"] == "1.1.0"
    assert data["model_version"] == "model-1"


def test_predict_valid():
    """A valid numeric input returns prediction = value * 2."""
    response = client.post("/predict", json={"value": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["input"] == 10
    assert data["prediction"] == 20


def test_predict_missing_input():
    """A request with no 'value' field is rejected with 422."""
    response = client.post("/predict", json={})
    assert response.status_code == 422


def test_predict_invalid_input():
    """A request with a non-numeric 'value' is rejected with 422."""
    response = client.post("/predict", json={"value": "not-a-number"})
    assert response.status_code == 422
